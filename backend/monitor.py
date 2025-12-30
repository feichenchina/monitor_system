import paramiko
import time
import json
from models import Machine
from datetime import datetime

def create_ssh_client(ip, port, username, password):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(ip, port=port, username=username, password=password, timeout=5)
        return client
    except Exception as e:
        print(f"Connection failed: {e}")
        return None

def execute_command(client, command):
    try:
        stdin, stdout, stderr = client.exec_command(command, timeout=5)
        return stdout.read().decode('utf-8').strip(), stderr.read().decode('utf-8').strip()
    except Exception as e:
        return "", str(e)

def check_machine1(machine: Machine) -> Machine:
    client = create_ssh_client(machine.ip, machine.port, machine.username, machine.password)
    
    if not client:
        machine.status = "Offline"
        machine.error_message = "Connection failed"
        machine.last_updated = datetime.now()
        return machine

    try:
        # 1. Check Arch
        arch, _ = execute_command(client, "uname -m")
        machine.arch = arch

        # 2. Check OS
        # Try to get pretty name
        os_info, _ = execute_command(client, "grep PRETTY_NAME /etc/os-release | cut -d'=' -f2 | tr -d '\"'")
        if not os_info:
             os_info, _ = execute_command(client, "uname -sr")
        machine.os_info = os_info

        # 3. Check Accelerators
        # Try NVIDIA
        nvidia_out, _ = execute_command(client, "nvidia-smi --query-gpu=name,memory.total,memory.used,temperature.gpu --format=csv,noheader")
        
        if nvidia_out:
            import re as _re

            gpus = [line for line in nvidia_out.split('\n') if line.strip()]
            machine.accelerator_count = len(gpus)
            machine.idle_count = 0
            machine.busy_count = 0
            machine.warning_count = 0

            details = []
            acc_names = set()
            num_extract = _re.compile(r"(\d+(?:\.\d+)?)")

            for gpu in gpus:
                parts = [p.strip() for p in gpu.split(',')]
                if len(parts) < 4:
                    continue

                name = parts[0]
                short_name = (
                    name.replace("NVIDIA ", "")
                    .replace("GeForce ", "")
                    .replace("Tesla ", "")
                )
                acc_names.add(short_name)

                def _take_number(text):
                    match = num_extract.search(text)
                    return float(match.group(1)) if match else 0.0

                total_mem = _take_number(parts[1])
                used_mem = _take_number(parts[2])
                temp = _take_number(parts[3])

                if temp > 85:
                    machine.warning_count += 1
                    health_label = "Warning"
                else:
                    health_label = "OK"
                    if total_mem > 0 and (used_mem / total_mem) > 0.1:
                        machine.busy_count += 1
                    else:
                        machine.idle_count += 1

                details.append(
                    {
                        "name": name,
                        "memory_total": int(total_mem),
                        "memory_used": int(used_mem),
                        "temp": f"{int(temp)}C",
                        "health": health_label,
                    }
                )

            machine.accelerator_count = (
                machine.idle_count + machine.busy_count + machine.warning_count
            )
            machine.accelerator_type = ", ".join(sorted(acc_names)) if acc_names else "NVIDIA GPU"
            machine.accelerator_status = json.dumps(details)
        else:
            # Try Huawei NPU
            npu_out, _ = execute_command(client, "npu-smi info")
            if npu_out and "command not found" not in npu_out:
                import re

                machine.idle_count = 0
                machine.busy_count = 0
                machine.warning_count = 0

                # Parse model name for display
                model_match = re.search(r"\|\s+\d+\s+((?:910|310)[A-Z0-9-]*)", npu_out)
                if model_match:
                    machine.accelerator_type = f"Ascend {model_match.group(1).strip()}"
                else:
                    machine.accelerator_type = "Huawei Ascend"

                lines = npu_out.split('\n')
                npu_cards = []
                current_card = None

                health_pattern = re.compile(
                    r"\|\s+(\d+)\s+([A-Za-z0-9-]+)\s+\|.*(OK|WARNING|ALARM|CRITICAL|OFFLINE)\s+\|",
                    re.IGNORECASE,
                )
                mem_pattern = re.compile(r"(\d+)\s*/\s*(\d+)")

                def finalize_card(card):
                    if not card:
                        return
                    candidates = card.get("mem_candidates", [])
                    if candidates:
                        used, total = max(candidates, key=lambda x: x[1])
                        card["mem_used"] = used
                        card["mem_total"] = total
                    card.pop("mem_candidates", None)

                for line in lines:
                    health_match = health_pattern.search(line)
                    if health_match:
                        if current_card is not None:
                            finalize_card(current_card)

                        card_id = health_match.group(1)
                        card_name = health_match.group(2).strip()
                        health_status = health_match.group(3).upper()

                        current_card = {
                            "name": f"{card_name} (ID:{card_id})",
                            "health": health_status,
                            "mem_used": 0,
                            "mem_total": 0,
                            "temp": "N/A",
                            "mem_candidates": [],
                        }
                        npu_cards.append(current_card)

                        parts = line.split("|")
                        if len(parts) >= 4:
                            info_part = parts[3].strip()
                            sub_parts = info_part.split()
                            if len(sub_parts) >= 2 and sub_parts[1].isdigit():
                                current_card["temp"] = f"{sub_parts[1]}C"

                        for u, t in mem_pattern.findall(line):
                            try:
                                current_card["mem_candidates"].append((int(u), int(t)))
                            except ValueError:
                                continue
                    elif current_card and "|" in line:
                        for u, t in mem_pattern.findall(line):
                            try:
                                current_card["mem_candidates"].append((int(u), int(t)))
                            except ValueError:
                                continue

                if current_card is not None:
                    finalize_card(current_card)

                machine.accelerator_count = len(npu_cards)
                machine.accelerator_status = json.dumps(npu_cards)

                for card in npu_cards:
                    if card["health"] != "OK":
                        machine.warning_count += 1
                        continue

                    if card["mem_total"] > 0 and (card["mem_used"] / card["mem_total"]) > 0.1:
                        machine.busy_count += 1
                    else:
                        machine.idle_count += 1

                if machine.accelerator_count == 0 and "910" in npu_out:
                    machine.accelerator_count = npu_out.count("910")
                    machine.idle_count = machine.accelerator_count
            else:
                machine.accelerator_type = "None"
                machine.accelerator_count = 0
                machine.accelerator_status = "No accelerators found"

        machine.status = "Online"
        machine.error_message = None
        
    except Exception as e:
        machine.status = "Error"
        machine.error_message = str(e)
    finally:
        client.close()
        machine.last_updated = datetime.now()
    
    return machine


def check_machine(machine: Machine) -> Machine:
    client = create_ssh_client(machine.ip, machine.port, machine.username, machine.password)
    
    if not client:
        machine.status = "Offline"
        machine.error_message = "Connection failed"
        machine.last_updated = datetime.now()
        return machine

    try:
        # 1. Check Arch
        arch, _ = execute_command(client, "uname -m")
        machine.arch = arch

        # 2. Check OS
        # Try to get pretty name
        os_info, _ = execute_command(client, "grep PRETTY_NAME /etc/os-release | cut -d'=' -f2 | tr -d '\"'")
        if not os_info:
             os_info, _ = execute_command(client, "uname -sr")
        machine.os_info = os_info

        # 3. Check Accelerators
        # Try NVIDIA
        nvidia_out, _ = execute_command(client, "nvidia-smi --query-gpu=name,memory.total,memory.used,temperature.gpu --format=csv,noheader")
        
        if nvidia_out:
            gpus = [line for line in nvidia_out.split('\n') if line.strip()]
            machine.accelerator_count = len(gpus)
            machine.idle_count = 0
            machine.busy_count = 0
            machine.warning_count = 0
            # Format: Name, Total, Used, Temp
            details = []
            acc_names = set()
            for gpu in gpus:
                parts = gpu.split(',')
                if len(parts) >= 4:
                    name = parts[0].strip()
                    short_name = name.replace("NVIDIA ", "").replace("GeForce ", "").replace("Tesla ", "")
                    acc_names.add(short_name)
                    
                    used_mem_str = parts[2].strip().split()[0]
                    total_mem_str = parts[1].strip().split()[0]
                    try:
                        used_mem = float(used_mem_str)
                        total_mem = float(total_mem_str)
                        # Calculate memory usage percentage
                        mem_usage_percent = (used_mem / total_mem) * 100 if total_mem > 0 else 0
                    except:
                        used_mem = 0
                        total_mem = 0
                        mem_usage_percent = 0
                    
                    temp_str = parts[3].strip().split()[0]
                    try:
                        temp = float(temp_str)
                    except:
                        temp = 0
                        
                    # 1. Determine Health/Warning
                    is_warning = False
                    if temp > 85:
                        is_warning = True
                        machine.warning_count += 1

                    # 2. Determine Busy/Idle based on memory usage percentage
                    # 仅当不是警告/异常卡时才计入 busy/idle
                    if not is_warning:
                        if mem_usage_percent < 10: # < 10% memory usage is idle
                            machine.idle_count += 1
                        else:
                            machine.busy_count += 1
                    # 警告卡不计入 idle/busy

                    details.append({
                        "name": name,
                        "memory_total": parts[1].strip(),
                        "memory_used": parts[2].strip(),
                        "temp": parts[3].strip()
                    })
            
            machine.accelerator_type = ", ".join(sorted(list(acc_names)))
            machine.accelerator_status = json.dumps(details)
        else:
            # Try Huawei NPU - 修复解析逻辑
            npu_out, _ = execute_command(client, "npu-smi info")
            if npu_out and "command not found" not in npu_out:
                import re

                # 1. 尝试从整体文本中提取型号（用于类型描述）
                model_match = re.search(r'(910B2C|910B|310[A-Z0-9]*)', npu_out)
                if model_match:
                    machine.accelerator_type = f"Ascend {model_match.group(1)}"
                else:
                    machine.accelerator_type = "Huawei Ascend"

                # 逐行解析每个 NPU 条目，第一行包含 id/model/health/power/temp，后续行可能包含 HBM 使用率
                lines = npu_out.splitlines()
                entries = []  # list of (npu_id, model, health, temp, hbm_used, hbm_total)

                for idx, line in enumerate(lines):
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
                            if nxt.strip().startswith('+'):
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
                machine.accelerator_count = len(entries)

                # 先统计 warning
                machine.idle_count = 0
                machine.busy_count = 0
                machine.warning_count = 0
                for _, _, health, _, _, _ in entries:
                    if health.lower() == 'warning' or health == 'Warning':
                        machine.warning_count += 1

                # 解析进程表，判断哪些 NPU 有运行进程
                has_process_map = {}
                proc_section = False
                for line in lines:
                    # 进程表开始行通常包含 'Process id' 或 '| NPU     Chip' 等
                    if ('Process id' in line and 'Process name' in line) or (line.strip().startswith('| NPU') and 'Process' in line):
                        proc_section = True
                        continue
                    if not proc_section:
                        continue

                    # 跳过类似 "No running processes found in NPU 1" 的行
                    m_no = re.search(r'No running processes found in NPU\s*(\d+)', line)
                    if m_no:
                        # 明确标记该 NPU 无进程（可选）
                        continue

                    # 匹配进程行，例如：| 0       0                 | 1840146       | python                   | 255                     |
                    mproc = re.match(r"\|\s*(\d+)\s+", line)
                    if mproc:
                        try:
                            proc_npu = int(mproc.group(1))
                        except:
                            continue

                        # 进一步检查后续列是否包含 Process id（数字）来确认确有进程
                        cols = [c.strip() for c in line.split('|') if c.strip()]
                        # cols 示例： ['0       0', '1840146', 'python', '255']
                        if len(cols) >= 2 and re.match(r"^\d+$", cols[1].split()[0]):
                            has_process_map[proc_npu] = True

                # 构建详情并判断忙/空
                details = []
                for (npu_id, model, health, temp, hbm_used, hbm_total) in entries:
                    try:
                        hbm_usage_percent = (hbm_used / hbm_total) * 100 if hbm_total > 0 else 0
                    except:
                        hbm_usage_percent = 0

                    # 如果 health 非 OK（例如 Warning），将其视为异常卡，不计入 busy/idle
                    if str(health).strip().lower() != 'ok':
                        status = "异常"
                    else:
                        is_busy = hbm_usage_percent >= 10
                        has_process = has_process_map.get(npu_id, False)
                        if is_busy or has_process:
                            machine.busy_count += 1
                            status = "忙碌"
                        else:
                            machine.idle_count += 1
                            status = "空闲"

                    details.append({
                        "id": npu_id,
                        "name": f"Ascend {model}",
                        "model": model,
                        "health": health,
                        "temp": temp,
                        "memory_total": f"{hbm_total}",
                        "memory_used": f"{hbm_used}",
                        "hbm_total": hbm_total,
                        "hbm_used": hbm_used,
                        "hbm_usage_percent": round(hbm_usage_percent, 2),
                        "status": status
                    })

                machine.accelerator_status = json.dumps(details)
            else:
                machine.accelerator_type = "None"
                machine.accelerator_count = 0
                machine.accelerator_status = "No accelerators found"

        machine.status = "Online"
        machine.error_message = None
        
    except Exception as e:
        machine.status = "Error"
        machine.error_message = str(e)
    finally:
        client.close()
        machine.last_updated = datetime.now()
    
    return machine
