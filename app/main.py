import os
from uuid import UUID
from datetime import timedelta
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from redis import Redis
from rq import Queue, Retry
import httpx

from app import crud, schemas, models
from app.database import get_db, engine
from app.config import settings
from app.security import (
    authenticate_user, 
    create_access_token, 
    get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from app.api.v1 import auth, aoa

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="AutonomOS", description="AI Orchestration Platform - Multi-Tenant Edition", version="2.0.0")

# Import and mount the DCL engine
try:
    from app.dcl_engine import dcl_app
    app.mount("/dcl", dcl_app)
    print("✅ DCL Engine mounted successfully at /dcl")
except Exception as e:
    print(f"⚠️ Failed to mount DCL Engine: {e}")

# Configure CORS to allow both dev and production origins
allowed_origins = [
    settings.ALLOWED_WEB_ORIGIN,  # Configured origin (localhost in dev)
    "http://localhost:5173",      # Vite dev server
    "http://localhost:5000",      # Backend dev
]

# In production, also allow the current domain
if os.getenv("REPL_SLUG"):  # Running on Replit
    # Allow all Replit domains (dev and production)
    allowed_origins.append("*")  # Simplest for Replit deployments
    
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if "*" not in allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Use REDIS_URL if available (production), otherwise use host/port (development)
# Redis is optional - if not available, task queue features will be disabled
redis_conn = None
task_queue = None
try:
    REDIS_URL = os.getenv("REDIS_URL")
    if REDIS_URL:
        redis_conn = Redis.from_url(REDIS_URL, decode_responses=False)
    else:
        redis_conn = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB)
    
    task_queue = Queue(connection=redis_conn)
    print("✅ Redis connected successfully")
except Exception as e:
    print(f"⚠️ Redis not available: {e}. Task queue features disabled.")
    redis_conn = None
    task_queue = None

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(aoa.router, prefix="/api/v1/aoa", tags=["AOA Orchestration"])

STATIC_DIR = "static"
if os.path.exists(STATIC_DIR) and os.path.isdir(STATIC_DIR):
    assets_dir = os.path.join(STATIC_DIR, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    
    @app.get("/")
    def serve_frontend():
        """Serve the frontend index.html"""
        index_path = os.path.join(STATIC_DIR, "index.html")
        if os.path.exists(index_path):
            return FileResponse(
                index_path,
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0"
                }
            )
        return {"message": "AutonomOS - Frontend not deployed yet. API available at /api/v1/*"}
    
    @app.get("/favicon.png")
    def serve_favicon():
        """Serve the favicon"""
        favicon_path = os.path.join(STATIC_DIR, "favicon.png")
        if os.path.exists(favicon_path):
            return FileResponse(favicon_path, media_type="image/png")
        raise HTTPException(status_code=404, detail="Favicon not found")
    
    @app.get("/image.png")
    def serve_image():
        """Serve the image file"""
        image_path = os.path.join(STATIC_DIR, "image.png")
        if os.path.exists(image_path):
            return FileResponse(image_path)
        raise HTTPException(status_code=404, detail="Image not found")
    
    @app.get("/dcl-bridge.js")
    def serve_dcl_bridge():
        """Serve the DCL bridge script"""
        script_path = os.path.join(STATIC_DIR, "dcl-bridge.js")
        if os.path.exists(script_path):
            return FileResponse(script_path, media_type="application/javascript")
        raise HTTPException(status_code=404, detail="DCL bridge script not found")
    
    @app.get("/__version")
    def version_info():
        """Debug endpoint for build verification"""
        import glob
        js_files = glob.glob(os.path.join(STATIC_DIR, "assets", "index-*.js"))
        css_files = glob.glob(os.path.join(STATIC_DIR, "assets", "index-*.css"))
        return {
            "buildId": os.path.getmtime(STATIC_DIR) if os.path.exists(STATIC_DIR) else None,
            "appRoot": os.path.abspath("."),
            "staticRoot": os.path.abspath(STATIC_DIR),
            "timestamp": os.path.getmtime(js_files[0]) if js_files else None,
            "currentAssets": {
                "js": [os.path.basename(f) for f in js_files],
                "css": [os.path.basename(f) for f in css_files]
            }
        }
else:
    @app.get("/")
    def read_root():
        return {"message": "Welcome to AutonomOS - Multi-Tenant AI Orchestration Platform"}

@app.post("/users/register", response_model=schemas.User)
def register_user(user_data: schemas.UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user and create their tenant.
    This endpoint creates both a tenant and the first user for that tenant.
    """
    existing_user = crud.get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    tenant = crud.create_tenant(db, schemas.TenantCreate(name=user_data.name))
    
    user = crud.create_user(
        db, 
        schemas.UserCreate(email=user_data.email, password=user_data.password),
        tenant.id
    )
    
    return user

@app.post("/token", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Login endpoint to get a JWT access token.
    Use email as username and provide password.
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"user_id": str(user.id), "tenant_id": str(user.tenant_id)},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=schemas.User)
def get_current_user_info(current_user: models.User = Depends(get_current_user)):
    """Get the currently authenticated user's information"""
    return current_user

@app.post("/api/v1/tasks", response_model=schemas.Task)
def create_task(
    task: schemas.TaskCreate, 
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new task and enqueue it for processing.
    The task is automatically associated with the authenticated user's tenant.
    """
    db_task = crud.create_task(db, task, current_user.tenant_id)
    
    # Only enqueue if Redis/task_queue is available
    if task_queue is None:
        raise HTTPException(
            status_code=503, 
            detail="Task queue not available. Redis connection required for background tasks."
        )
    
    try:
        from app.worker import execute_task
        
        retry_config = None
        if task.max_retries and task.max_retries > 0:
            retry_config = Retry(max=task.max_retries, interval=[10, 30, 60])
        
        task_queue.enqueue(
            execute_task, 
            str(db_task.id),
            job_timeout=task.timeout_seconds,
            retry=retry_config
        )
    except Exception as e:
        import logging
        logging.error(f"Failed to enqueue task {db_task.id}: {str(e)}")
        raise HTTPException(
            status_code=503, 
            detail="Task created but failed to enqueue for processing. Please check Redis connection."
        )
    
    return db_task

@app.get("/api/v1/tasks/{task_id}", response_model=schemas.Task)
def get_task(
    task_id: UUID, 
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve a task by its ID.
    Only returns tasks belonging to the authenticated user's tenant.
    Returns 404 if task not found or belongs to another tenant.
    """
    db_task = crud.get_task(db, task_id, current_user.tenant_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return db_task

@app.delete("/api/v1/tasks/{task_id}", response_model=schemas.Task)
def cancel_task(
    task_id: UUID, 
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cancel a scheduled or running task.
    Only allows canceling tasks belonging to the authenticated user's tenant.
    """
    db_task = crud.get_task(db, task_id, current_user.tenant_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if db_task.status in ["success", "failed", "canceled"]:
        raise HTTPException(status_code=400, detail=f"Cannot cancel task with status '{db_task.status}'")
    
    try:
        from rq.job import Job
        job = Job.fetch(str(task_id), connection=redis_conn)
        job.cancel()
        crud.update_task_status(db, task_id, "canceled", {"message": "Task canceled by user"}, current_user.tenant_id)
        crud.create_task_log(db, task_id, "Task canceled by user request")
    except Exception as e:
        import logging
        logging.warning(f"Could not cancel job in RQ: {str(e)}")
        crud.update_task_status(db, task_id, "canceled", {"message": "Task canceled by user"}, current_user.tenant_id)
        crud.create_task_log(db, task_id, "Task canceled by user request")
    
    db_task = crud.get_task(db, task_id, current_user.tenant_id)
    return db_task

@app.get("/health/api")
def health_api():
    """Health check for the API"""
    return {"status": "ok"}

@app.get("/health/worker")
def health_worker():
    """Health check for the worker - checks Redis connection"""
    try:
        redis_conn.ping()
        return {"status": "ok", "redis": "connected"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Redis connection failed: {str(e)}"
        )

