from fastapi import APIRouter, HTTPException, Depends, Query
from sqlmodel import Session, select, func
from typing import List
import threading

from database import get_session, engine
from models import Machine, MachineUpdate
from services.monitor_service import check_machine, update_single_machine_sync, update_all_machines

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
    statement = statement.offset((page - 1) * size).limit(size)
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
