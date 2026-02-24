from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from database import get_session
from models import Settings
from services.monitor_service import update_all_machines
from scheduler import scheduler

router = APIRouter(prefix="/settings", tags=["settings"])

@router.get("", response_model=Settings)
def get_settings(session: Session = Depends(get_session)):
    settings = session.exec(select(Settings)).first()
    return settings

@router.post("", response_model=Settings)
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
