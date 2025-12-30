from typing import Optional
from sqlmodel import Field, SQLModel
from datetime import datetime

class Machine(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ip: str
    port: int = 22
    username: str
    password: str
    
    # 监控数据
    status: str = "Unknown" # Online, Offline, Error
    os_info: Optional[str] = None
    arch: Optional[str] = None # x86_64, aarch64
    accelerator_type: Optional[str] = None # NVIDIA, Huawei, AMD, None
    accelerator_count: int = 0
    idle_count: int = 0
    busy_count: int = 0
    warning_count: int = 0
    accelerator_status: Optional[str] = None # JSON string or detailed text
    last_updated: Optional[datetime] = None
    error_message: Optional[str] = None
    remark: Optional[str] = None

class Settings(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    interval_seconds: int = 60 # 默认60秒检测一次
