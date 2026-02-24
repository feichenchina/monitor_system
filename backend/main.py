import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlmodel import SQLModel

from database import engine, create_db_and_tables
from routers import machines, settings
from scheduler import scheduler
from services.monitor_service import update_all_machines
from logger import setup_logging

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup logging
    setup_logging()
    
    # Initialize DB
    create_db_and_tables()
    
    # Start scheduler
    # Check if job already exists to avoid duplicate job error on reload
    if not scheduler.get_job('monitor_job'):
        scheduler.add_job(update_all_machines, 'interval', minutes=1, id='monitor_job')
    
    if not scheduler.running:
        scheduler.start()
    
    yield
    
    # Shutdown scheduler
    if scheduler.running:
        scheduler.shutdown()

app = FastAPI(lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(machines.router)
app.include_router(settings.router)

# Mount static files logic
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
frontend_dist = os.path.join(BASE_DIR, "frontend", "dist")

if os.path.exists(frontend_dist):
    assets_dir = os.path.join(frontend_dist, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # API routes are already handled above, so this catches everything else
        # Serve index.html for SPA routing
        if full_path.startswith("api"):
            return {"error": "API endpoint not found"}
            
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        
        return FileResponse(os.path.join(frontend_dist, "index.html"))
else:
    @app.get("/")
    def read_root():
        return {"message": "Backend is running. Frontend static files not found. Please build frontend first."}

if __name__ == "__main__":
    import uvicorn
    # Get port from environment variable or default to 8000
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
