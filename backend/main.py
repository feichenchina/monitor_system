from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.responses import FileResponse
from sqlmodel import SQLModel, Session, create_engine, select, func
from models import Machine, Settings
from monitor import check_machine
from logger import setup_logging, check_log_rotation, logger
from apscheduler.schedulers.background import BackgroundScheduler
from typing import List
import threading
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

scheduler = BackgroundScheduler()

def update_all_machines():
    # Check for log rotation first
    check_log_rotation()
    
    with Session(engine) as session:
        machines = session.exec(select(Machine)).all()
        for machine in machines:
            logger.info(f"Checking machine: {machine.ip}")
            updated_machine = check_machine(machine)
            session.add(updated_machine)
        session.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    create_db_and_tables()
    
    # Load settings and start scheduler
    with Session(engine) as session:
        settings = session.exec(select(Settings)).first()
        if not settings:
            settings = Settings(interval_seconds=60)
            session.add(settings)
            session.commit()
        
        scheduler.add_job(update_all_machines, 'interval', seconds=settings.interval_seconds, id='monitor_job')
        scheduler.start()
    
    yield
    
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routes
@app.get("/machines")
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

@app.post("/machines", response_model=Machine)
def create_machine(machine: Machine, session: Session = Depends(get_session)):
    # Check for duplicate IP
    existing = session.exec(select(Machine).where(Machine.ip == machine.ip)).first()
    if existing:
        raise HTTPException(status_code=400, detail="该 IP 已存在")
    
    session.add(machine)
    session.commit()
    session.refresh(machine)
    # Trigger a check in background or immediately? Let's do immediately for better UX
    threading.Thread(target=lambda: update_single_machine(machine.id)).start()
    return machine

def update_single_machine(machine_id):
    with Session(engine) as session:
        machine = session.get(Machine, machine_id)
        if machine:
            check_machine(machine)
            session.add(machine)
            session.commit()

@app.delete("/machines/{machine_id}")
def delete_machine(machine_id: int, session: Session = Depends(get_session)):
    machine = session.get(Machine, machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    session.delete(machine)
    session.commit()
    return {"ok": True}

@app.get("/settings", response_model=Settings)
def get_settings(session: Session = Depends(get_session)):
    settings = session.exec(select(Settings)).first()
    return settings

@app.post("/settings", response_model=Settings)
def update_settings(new_settings: Settings, session: Session = Depends(get_session)):
    settings = session.exec(select(Settings)).first()
    if not settings:
        settings = Settings()
    
    settings.interval_seconds = new_settings.interval_seconds
    session.add(settings)
    session.commit()
    session.refresh(settings)
    
    # Reschedule job
    try:
        scheduler.reschedule_job('monitor_job', trigger='interval', seconds=settings.interval_seconds)
    except:
        scheduler.add_job(update_all_machines, 'interval', seconds=settings.interval_seconds, id='monitor_job')
        
    return settings

@app.post("/machines/{machine_id}/refresh")
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

@app.post("/machines/refresh_all")
def refresh_all_machines(session: Session = Depends(get_session)):
    machines = session.exec(select(Machine)).all()
    for machine in machines:
        check_machine(machine)
        session.add(machine)
    session.commit()
    return {"count": len(machines)}

@app.get("/machines/{machine_id}/raw_monitor")
def get_raw_monitor_output(machine_id: int, session: Session = Depends(get_session)):
    """
    Connects to the machine via SSH and returns the raw output of the monitoring command.
    """
    machine = session.get(Machine, machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    # We need to import the SSH logic from monitor.py or duplicate it.
    # Since monitor.py has execute_command and create_ssh_client, let's import them.
    # Note: monitor.py is in the same directory.
    from monitor import create_ssh_client, execute_command
    
    client = create_ssh_client(machine.ip, machine.port, machine.username, machine.password)
    if not client:
        raise HTTPException(status_code=500, detail="Could not connect to machine via SSH")
    
    try:
        # Try npu-smi first
        npu_out, npu_err = execute_command(client, "npu-smi info")
        if npu_out and "command not found" not in npu_out:
            return {"output": npu_out}
            
        # Try nvidia-smi
        nvidia_out, nvidia_err = execute_command(client, "nvidia-smi")
        if nvidia_out and "command not found" not in nvidia_out:
            return {"output": nvidia_out}
            
        return {"output": "No accelerator monitoring tool found (npu-smi or nvidia-smi)."}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing command: {str(e)}")
    finally:
        client.close()

@app.put("/machines/{machine_id}", response_model=Machine)
def update_machine(machine_id: int, updated_data: dict, session: Session = Depends(get_session)):
    db_machine = session.get(Machine, machine_id)
    if not db_machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    # 只更新提供的字段
    if "username" in updated_data:
        db_machine.username = updated_data["username"]
    if "password" in updated_data:
        db_machine.password = updated_data["password"]
    if "remark" in updated_data:
        db_machine.remark = updated_data["remark"]
    
    session.add(db_machine)
    session.commit()
    session.refresh(db_machine)
    return db_machine

# Mount static files
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="static")

    # SPA Fallback: Serve index.html for any 404 on the root mount
    @app.exception_handler(404)
    async def custom_404_handler(request, __):
        if not request.url.path.startswith("/machines") and not request.url.path.startswith("/settings"):
            return FileResponse(os.path.join(frontend_path, "index.html"))
        raise HTTPException(status_code=404, detail="Not Found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
