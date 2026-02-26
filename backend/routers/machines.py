from fastapi import APIRouter, HTTPException, Depends, Query
from sqlmodel import Session, select, func
from typing import List
import threading

from database import get_session, engine
from models import Machine, MachineUpdate
from services.monitor_service import check_machine, update_single_machine_sync, update_all_machines, create_ssh_client, execute_command

router = APIRouter(prefix="/machines", tags=["machines"])

@router.get("")
def read_machines(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1),
    search: str = Query(None),
    arch: str = Query(None),
    status: str = Query(None),
    acc_type: str = Query(None),
    session: Session = Depends(get_session)
):
    # Base statement
    statement = select(Machine)
    
    if search:
        statement = statement.where(
            (Machine.ip.contains(search)) | 
            (Machine.username.contains(search)) |
            (Machine.accelerator_type.contains(search))
        )
    
    if arch:
        statement = statement.where(Machine.arch == arch)
    if status:
        statement = statement.where(Machine.status == status)
    if acc_type:
        if acc_type == "HasAcc":
            statement = statement.where(Machine.accelerator_count > 0)
        elif acc_type == "NoAcc":
            statement = statement.where(Machine.accelerator_count == 0)
        elif acc_type == "Idle":
            statement = statement.where(Machine.idle_count > 0)
        elif acc_type == "Busy":
            statement = statement.where(Machine.busy_count > 0)
        elif acc_type == "Warning":
            statement = statement.where(Machine.warning_count > 0)
    
    # Get total count with filter
    total_statement = select(func.count()).select_from(statement.subquery())
    total = session.exec(total_statement).one()
    
    # Get paginated results
    statement = statement.order_by(Machine.ip).offset((page - 1) * size).limit(size)
    machines = session.exec(statement).all()
    
    return {
        "items": machines,
        "total": total,
        "page": page,
        "size": size
    }

@router.post("", response_model=Machine)
def create_machine(machine: Machine, session: Session = Depends(get_session)):
    # Check for duplicate IP
    existing = session.exec(select(Machine).where(Machine.ip == machine.ip)).first()
    if existing:
        raise HTTPException(status_code=400, detail="该 IP 已存在")
    
    session.add(machine)
    session.commit()
    session.refresh(machine)
    # Trigger a check in background or immediately? Let's do immediately for better UX
    threading.Thread(target=lambda: update_single_machine_sync(machine.id)).start()
    return machine

@router.put("/{machine_id}", response_model=Machine)
def update_machine(machine_id: int, machine_update: MachineUpdate, session: Session = Depends(get_session)):
    db_machine = session.get(Machine, machine_id)
    if not db_machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    machine_data = machine_update.model_dump(exclude_unset=True)
    for key, value in machine_data.items():
        setattr(db_machine, key, value)
        
    session.add(db_machine)
    session.commit()
    session.refresh(db_machine)
    return db_machine

@router.delete("/{machine_id}")
def delete_machine(machine_id: int, session: Session = Depends(get_session)):
    machine = session.get(Machine, machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    session.delete(machine)
    session.commit()
    return {"ok": True}

@router.post("/{machine_id}/refresh")
def refresh_machine(machine_id: int, session: Session = Depends(get_session)):
    machine = session.get(Machine, machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    # Run check synchronously for manual refresh
    check_machine(machine)
    session.add(machine)
    session.commit()
    session.refresh(machine)
    return machine

@router.post("/refresh_all")
def refresh_all_machines_endpoint(session: Session = Depends(get_session)):
    update_all_machines()
    return {"message": "All machines updated"}

@router.get("/{machine_id}/raw_monitor")
def get_raw_monitor(machine_id: int, session: Session = Depends(get_session)):
    machine = session.get(Machine, machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    # Run the same command as check_machine to get raw output
    client = create_ssh_client(machine.ip, machine.port, machine.username, machine.password)
    if not client:
        return {"output": "Connection failed"}
        
    try:
        # Use the same combined command as check_machine
        DELIM = "|||SECTION|||"
        
        cmd = (
            f"uname -m; echo '{DELIM}';"
            f"(grep PRETTY_NAME /etc/os-release | cut -d'=' -f2 | tr -d '\"') || uname -sr; echo '{DELIM}';"
            f"nvidia-smi --query-gpu=index,name,memory.total,memory.used,temperature.gpu --format=csv,noheader 2>/dev/null || echo 'NVIDIA_NOT_FOUND'; echo '{DELIM}';"
            f"npu-smi info 2>/dev/null || echo 'HUAWEI_NOT_FOUND'"
        )
        
        stdout, stderr = execute_command(client, cmd)
        
        # Format the output for better readability
        parts = stdout.split(DELIM)
        
        formatted_output = f"=== System Info ===\n"
        if len(parts) > 0:
            formatted_output += f"Arch: {parts[0].strip()}\n"
        if len(parts) > 1:
            formatted_output += f"OS: {parts[1].strip()}\n"
            
        formatted_output += f"\n=== NVIDIA GPU Status ===\n"
        if len(parts) > 2:
            nvidia_out = parts[2].strip()
            if nvidia_out == "NVIDIA_NOT_FOUND":
                formatted_output += "No NVIDIA GPU found or nvidia-smi not available.\n"
            else:
                formatted_output += nvidia_out + "\n"
                
        formatted_output += f"\n=== Huawei NPU Status ===\n"
        if len(parts) > 3:
            npu_out = parts[3].strip()
            if npu_out == "HUAWEI_NOT_FOUND":
                formatted_output += "No Huawei NPU found or npu-smi not available.\n"
            else:
                formatted_output += npu_out + "\n"

        if stderr:
             formatted_output += f"\n=== STDERR ===\n{stderr}\n"
             
        return {"output": formatted_output}
        
    except Exception as e:
        return {"output": f"Error executing command: {e}"}
    finally:
        client.close()
