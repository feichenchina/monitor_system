import paramiko
import time
import json
import re
from datetime import datetime
from sqlmodel import Session, select
from concurrent.futures import ThreadPoolExecutor

from models import Machine
from logger import logger, check_log_rotation
from database import engine

def create_ssh_client(ip, port, username, password):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(ip, port=port, username=username, password=password, timeout=5)
        return client
    except Exception as e:
        logger.error(f"Connection failed to {ip}: {e}")
        return None

def execute_command(client, command):
    try:
        # Increased timeout to 10s to handle combined command execution
        stdin, stdout, stderr = client.exec_command(command, timeout=10)
        return stdout.read().decode('utf-8').strip(), stderr.read().decode('utf-8').strip()
    except Exception as e:
        return "", str(e)

def _take_number(text: str) -> float:
    if not text:
        return 0.0
    num_extract = re.compile(r"(\d+(?:\.\d+)?)")
    m = num_extract.search(str(text))
    return float(m.group(1)) if m else 0.0

def parse_nvidia_output(nvidia_out: str) -> dict:
    if not nvidia_out:
        return None

    gpus = [line for line in nvidia_out.split('\n') if line.strip()]
    details = []
    acc_names = set()
    
    idle_count = 0
    busy_count = 0
    warning_count = 0

    for gpu in gpus:
        parts = [p.strip() for p in gpu.split(',')]
        if len(parts) < 5:
            continue

        card_id = parts[0]
        name = parts[1]
        short_name = (
            name.replace("NVIDIA ", "")
            .replace("GeForce ", "")
            .replace("Tesla ", "")
        )
        acc_names.add(short_name)

        # Use regex extraction to handle units like MiB and possible trailing 'C'
        total_mem = _take_number(parts[2])
        used_mem = _take_number(parts[3])
        temp = _take_number(parts[4])

        mem_usage_percent = (used_mem / total_mem) * 100 if total_mem > 0 else 0

        if temp > 85:
            warning_count += 1
            health_label = "Warning"
        else:
            health_label = "OK"
            if mem_usage_percent > 10:
                busy_count += 1
            else:
                idle_count += 1

        details.append(
            {
                "id": card_id,
                "name": name,
                "memory_total": int(total_mem) if total_mem else 0,
                "memory_used": int(used_mem) if used_mem else 0,
                "temp": f"{int(temp)}C" if temp else "N/A",
                "health": health_label,
            }
        )

    return {
        "accelerator_count": len(details),
        "idle_count": idle_count,
        "busy_count": busy_count,
        "warning_count": warning_count,
        "accelerator_type": ", ".join(sorted(acc_names)) if acc_names else None,
        "accelerator_status": details
    }

def parse_huawei_output(npu_out: str) -> dict:
    if not npu_out or "command not found" in npu_out or "HUAWEI_NOT_FOUND" in npu_out:
        return None

    idle_count = 0
    busy_count = 0
    warning_count = 0
    accelerator_type = "Huawei Ascend"

    # Parse model name for display
    model_match = re.search(r"\|\s+\d+\s+((?:910|310)[A-Z0-9-]*)", npu_out)
    if model_match:
        accelerator_type = f"Ascend {model_match.group(1).strip()}"

    # Parse Process Info first
    # Map npu_id -> has_process (bool)
    npu_has_process = {}
    
    # Check if Process table exists
    process_table_start = npu_out.find("| NPU     Chip")
    has_process_table = process_table_start != -1

    if has_process_table:
        process_lines = npu_out[process_table_start:].splitlines()
        for line in process_lines:
            # Match process line: | 0       0                 | 3801368       | ...
            proc_match = re.match(r"\|\s*(\d+)\s+.*\|\s*(\d+)\s+\|", line)
            if proc_match:
                npu_id = int(proc_match.group(1))
                npu_has_process[npu_id] = True
            
            # Match "No running processes found in NPU X"
            no_proc_match = re.search(r"No running processes found in NPU (\d+)", line)
            if no_proc_match:
                npu_id = int(no_proc_match.group(1))
                # Explicitly set to False (though default is False, this confirms we saw it)
                if npu_id not in npu_has_process:
                    npu_has_process[npu_id] = False

    # 逐行解析每个 NPU 条目，第一行包含 id/model/health/power/temp，后续行可能包含 HBM 使用率
    lines = npu_out.splitlines()
    entries = []  # list of (npu_id, model, health, temp, hbm_used, hbm_total)

    for idx, line in enumerate(lines):
        # Stop if we reach the Process table
        if "| NPU     Chip" in line:
            break

        # 匹配类似：| 0     910B2C              | OK            | 89.5        44                0    / 0             |
        m = re.match(r"\|\s*(\d+)\s+([A-Z0-9-]+)\s*\|\s*([A-Za-z]+)\s*\|\s*([\d.]+)\s+(\d+)\b", line)
        if m:
            npu_id_str, model, health, power_str, temp_str = m.groups()
            try:
                npu_id = int(npu_id_str)
                temp = int(temp_str)
            except:
                npu_id = int(npu_id_str) if npu_id_str.isdigit() else 0
                temp = 0

            # 在接下来的几行中查找 HBM 使用（形如 3632 / 65536 或 57356/ 65536）
            hbm_used = 0
            hbm_total = 0
            candidates = []
            # 扫描接下来的若干行，直到遇到分隔行或超过范围
            for j in range(idx + 1, min(idx + 8, len(lines))):
                nxt = lines[j]
                if nxt.strip().startswith('+') or "| NPU     Chip" in nxt:
                    break
                matches = re.findall(r"(\d{1,6})\s*/\s*(\d{1,6})", nxt)
                for used_s, total_s in matches:
                    try:
                        used_i = int(used_s)
                        total_i = int(total_s)
                    except:
                        continue
                    # 忽略完全无效的 0/0
                    if total_i == 0:
                        continue
                    candidates.append((used_i, total_i))

            # 优先选择 total >= 1000 的第一个匹配，否则选择 total 最大的匹配
            chosen = None
            for u, t in candidates:
                if t >= 1000:
                    chosen = (u, t)
                    break
            if not chosen and candidates:
                # 选 total 最大的
                chosen = max(candidates, key=lambda x: x[1])

            if chosen:
                hbm_used, hbm_total = chosen

            entries.append((npu_id, model.strip(), health.strip(), temp, hbm_used, hbm_total))

    # 统计数量
    accelerator_count = len(entries)
    details = []

    for npu_id, model, health, temp, hbm_used, hbm_total in entries:
        is_busy = False
        if health.lower() in ['warning', 'critical', 'error']:
            warning_count += 1
            health_label = "Warning"
        else:
            health_label = "OK"
            
            if has_process_table:
                 if npu_has_process.get(npu_id, False):
                    busy_count += 1
                    is_busy = True
                 else:
                    idle_count += 1
            else:
                usage_percent = (hbm_used / hbm_total * 100) if hbm_total > 0 else 0
                if usage_percent > 5: # Threshold for busy
                    busy_count += 1
                    is_busy = True
                else:
                    idle_count += 1
        
        details.append({
            "id": str(npu_id),
            "name": model,
            "memory_total": hbm_total,
            "memory_used": hbm_used,
            "temp": f"{temp}C",
            "health": health_label
        })

    return {
        "accelerator_count": accelerator_count,
        "idle_count": idle_count,
        "busy_count": busy_count,
        "warning_count": warning_count,
        "accelerator_type": accelerator_type,
        "accelerator_status": details
    }

def check_machine(machine: Machine) -> Machine:
    client = create_ssh_client(machine.ip, machine.port, machine.username, machine.password)
    
    if not client:
        machine.status = "Offline"
        machine.error_message = "Connection failed"
        machine.last_updated = datetime.now()
        return machine

    try:
        # Combine commands to reduce SSH overhead
        # Delimiters to separate sections
        DELIM = "|||SECTION|||"
        
        cmd = (
            f"uname -m; echo '{DELIM}';"
            f"(grep PRETTY_NAME /etc/os-release | cut -d'=' -f2 | tr -d '\"') || uname -sr; echo '{DELIM}';"
            f"nvidia-smi --query-gpu=index,name,memory.total,memory.used,temperature.gpu --format=csv,noheader 2>/dev/null || echo 'NVIDIA_NOT_FOUND'; echo '{DELIM}';"
            f"npu-smi info 2>/dev/null || echo 'HUAWEI_NOT_FOUND'"
        )
        
        stdout, stderr = execute_command(client, cmd)
        
        # Split output by delimiter
        parts = stdout.split(DELIM)
        
        # 1. Arch
        arch = parts[0].strip() if len(parts) > 0 else "Unknown"
        machine.arch = arch

        # 2. OS
        os_info = parts[1].strip() if len(parts) > 1 else "Unknown"
        machine.os_info = os_info

        # 3. Accelerators (Merge NVIDIA + Huawei)
        nvidia_out = parts[2].strip() if len(parts) > 2 else None
        npu_out = parts[3].strip() if len(parts) > 3 else None
        
        nvidia_data = parse_nvidia_output(nvidia_out)
        huawei_data = parse_huawei_output(npu_out)
        
        # Merge Logic
        merged_count = 0
        merged_idle = 0
        merged_busy = 0
        merged_warning = 0
        types = []
        details_list = []
        
        if nvidia_data:
            merged_count += nvidia_data["accelerator_count"]
            merged_idle += nvidia_data["idle_count"]
            merged_busy += nvidia_data["busy_count"]
            merged_warning += nvidia_data["warning_count"]
            if nvidia_data["accelerator_type"]:
                types.append(nvidia_data["accelerator_type"])
            if nvidia_data["accelerator_status"]:
                details_list.extend(nvidia_data["accelerator_status"])
                
        if huawei_data:
            merged_count += huawei_data["accelerator_count"]
            merged_idle += huawei_data["idle_count"]
            merged_busy += huawei_data["busy_count"]
            merged_warning += huawei_data["warning_count"]
            if huawei_data["accelerator_type"]:
                types.append(huawei_data["accelerator_type"])
            if huawei_data["accelerator_status"]:
                details_list.extend(huawei_data["accelerator_status"])
        
        if merged_count > 0:
            machine.accelerator_count = merged_count
            machine.idle_count = merged_idle
            machine.busy_count = merged_busy
            machine.warning_count = merged_warning
            machine.accelerator_type = ", ".join(types)
            machine.accelerator_status = json.dumps(details_list)
        else:
            # No accelerator found
            machine.accelerator_count = 0
            machine.idle_count = 0
            machine.busy_count = 0
            machine.warning_count = 0
            machine.accelerator_type = None
            machine.accelerator_status = None

        machine.status = "Online"
        machine.error_message = None
        machine.last_updated = datetime.now()

    except Exception as e:
        machine.status = "Error"
        machine.error_message = str(e)
        logger.error(f"Error checking machine {machine.ip}: {e}")
    finally:
        if client:
            client.close()
            
    return machine

def update_single_machine_sync(machine_id: int):
    with Session(engine) as session:
        machine = session.get(Machine, machine_id)
        if machine:
            check_machine(machine)
            session.add(machine)
            session.commit()

def update_all_machines():
    # Check for log rotation first
    check_log_rotation()

    with Session(engine) as session:
        machines = session.exec(select(Machine)).all()
        machine_ids = [m.id for m in machines]
    
    # Use ThreadPoolExecutor for parallel execution
    # Limit max_workers to avoid too many SSH connections at once
    with ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(update_single_machine_sync, machine_ids)
