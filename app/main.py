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
import logging

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

from app import crud, schemas, models
from app.database import get_db, engine
from app.config import settings
from app.security import (
    authenticate_user,
    create_access_token,
    get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from app.api.v1 import auth, aoa, aam_monitoring, aam_mesh, aam_connections, platform_stubs, filesource, dcl_views, debug, mesh_test, events, dcl_unify, aod_mock, aam_onboarding
from app import nlp_simple

# Initialize database tables - with error handling for resilience
try:
    models.Base.metadata.create_all(bind=engine)
    print("✅ Database tables initialized successfully")
except Exception as e:
    print(f"⚠️ Database initialization failed: {e}. Continuing without database...")

app = FastAPI(title="AutonomOS", description="AI Orchestration Platform - Multi-Tenant Edition", version="2.0.0")

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

# Add Gateway Middleware (Platform Infrastructure)
try:
    from app.gateway.middleware.auth import tenant_auth_middleware
    from app.gateway.middleware.tracing import tracing_middleware
    from app.gateway.middleware.rate_limit import rate_limit_middleware
    from app.gateway.middleware.idempotency import idempotency_middleware
    from app.gateway.middleware.audit import audit_middleware

    # Register middleware in correct order (FIRST = outermost, LAST = innermost)
    # Order: Tracing → Auth → RateLimit → Idempotency → Audit
    app.middleware("http")(tracing_middleware)
    app.middleware("http")(tenant_auth_middleware)
    app.middleware("http")(rate_limit_middleware)
    app.middleware("http")(idempotency_middleware)
    app.middleware("http")(audit_middleware)

    print("✅ Gateway middleware registered successfully")
except Exception as e:
    print(f"⚠️ Gateway middleware not available: {e}")

# Use REDIS_URL if available (production), otherwise use host/port (development)
# Redis is optional - if not available, task queue features will be disabled
redis_conn = None
task_queue = None
try:
    REDIS_URL = os.getenv("REDIS_URL")
    if REDIS_URL:
        # Fix for Upstash Redis: Change redis:// to rediss:// to enable TLS/SSL
        # Upstash requires TLS connections, and rediss:// protocol enables this
        if REDIS_URL.startswith("redis://"):
            REDIS_URL = "rediss://" + REDIS_URL[8:]
            print("🔒 Using TLS/SSL for Redis connection (rediss:// protocol)")

        redis_conn = Redis.from_url(REDIS_URL, decode_responses=False)
    else:
        redis_conn = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB)

    task_queue = Queue(connection=redis_conn)
    print("✅ Redis connected successfully")
except Exception as e:
    print(f"⚠️ Redis not available: {e}. Task queue features disabled.")
    redis_conn = None
    task_queue = None

# Import and mount the DCL engine AFTER Redis initialization
# This allows us to share the Redis client with DCL engine to avoid connection limit issues
try:
    from app.dcl_engine import dcl_app, set_redis_client

    # Share Redis client with DCL engine (avoids hitting Upstash 20 connection limit)
    if redis_conn:
        set_redis_client(redis_conn)

    app.mount("/dcl", dcl_app)
    print("✅ DCL Engine mounted successfully at /dcl")
except Exception as e:
    print(f"⚠️ Failed to mount DCL Engine: {e}")
    import traceback
    traceback.print_exc()

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    # Initialize AAM database (create tables and enums)
    try:
        import sys
        # Insert 'aam_hybrid' directory into sys.path to allow importing from it
        sys.path.insert(0, 'aam_hybrid')
        from shared.database import init_db
        await init_db()
        logger.info("✅ AAM database initialized successfully")
    except Exception as e:
        logger.warning(f"⚠️ AAM database initialization failed: {e}. Some AAM features may not work.")

    # Initialize DCL RAG engine
    global dcl_app
    if dcl_app:
        from app.dcl_engine.rag_engine import RAGEngine
        try:
            dcl_app.rag_engine = RAGEngine()
            logger.info("✅ DCL RAG Engine initialized successfully")
        except Exception as e:
            logger.warning(f"⚠️ DCL RAG Engine initialization failed: {e}. Continuing without RAG.")

    # Initialize DCL Agent Executor
    if dcl_app:
        from app.dcl_engine.agent_executor import AgentExecutor
        from app.dcl_engine.app import AGENT_RESULTS_CACHE, load_agents_config, DB_PATH
        import app.dcl_engine.app as dcl_app_module
        try:
            agents_config = load_agents_config()
            # Pass redis_conn for Phase 4 metadata support
            dcl_app.agent_executor = AgentExecutor(DB_PATH, agents_config, AGENT_RESULTS_CACHE, redis_conn)
            
            # Set the global variable in dcl_app module (CRITICAL FIX)
            dcl_app_module.agent_executor = dcl_app.agent_executor
            
            logger.info("✅ DCL Agent Executor initialized successfully with Phase 4 metadata support")
        except Exception as e:
            logger.warning(f"⚠️ DCL Agent Executor initialization failed: {e}. Continuing without agent execution.")
    
    # Initialize AAM Auto-Onboarding Services
    if redis_conn:
        try:
            from aam_hybrid.core.funnel_metrics import FunnelMetricsTracker
            from aam_hybrid.core.onboarding_service import OnboardingService
            import app.api.v1.aam_onboarding as onboarding_module
            
            # Create funnel metrics tracker
            funnel_tracker = FunnelMetricsTracker(redis_conn)
            onboarding_module.funnel_tracker = funnel_tracker
            
            # Create onboarding service
            onboarding_service = OnboardingService(funnel_tracker)
            onboarding_module.onboarding_service = onboarding_service
            
            logger.info("✅ AAM Auto-Onboarding services initialized (Safe Mode enabled, 90% SLO target)")
        except Exception as e:
            logger.warning(f"⚠️ AAM Auto-Onboarding initialization failed: {e}. Auto-onboarding disabled.")
    else:
        logger.warning("⚠️ Redis not available - AAM Auto-Onboarding disabled")


app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(nlp_simple.router, tags=["NLP Gateway"])
app.include_router(aoa.router, prefix="/api/v1/aoa", tags=["AOA Orchestration"])
app.include_router(aam_monitoring.router, prefix="/api/v1/aam", tags=["AAM Monitoring"])
app.include_router(aam_connections.router, prefix="/api/v1/aam", tags=["AAM Connections"])
app.include_router(aam_onboarding.router, prefix="/api/v1/aam", tags=["AAM Auto-Onboarding"])
app.include_router(aam_mesh.router, prefix="/api/v1/mesh", tags=["AAM Mesh"])
app.include_router(mesh_test.router, prefix="/api/v1", tags=["Mesh Test (Dev-Only)"])
app.include_router(filesource.router, prefix="/api/v1/filesource", tags=["FileSource Connector"])
app.include_router(dcl_views.router, prefix="/api/v1/dcl/views", tags=["DCL Views"])
app.include_router(dcl_unify.router, prefix="/api/v1/dcl", tags=["DCL Unification"])
app.include_router(debug.router, prefix="/api/v1", tags=["Debug (Dev-Only)"])
app.include_router(events.router, prefix="/api/v1/events", tags=["Event Stream"])
app.include_router(platform_stubs.router, prefix="/api/v1", tags=["Platform Stubs"])
app.include_router(aod_mock.router, prefix="", tags=["AOD Mock (Testing)"])

STATIC_DIR = "static"
if os.path.exists(STATIC_DIR) and os.path.isdir(STATIC_DIR):
    assets_dir = os.path.join(STATIC_DIR, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/")
    def serve_frontend(request: Request):
        """Serve the frontend index.html"""
        index_path = os.path.join(STATIC_DIR, "index.html")
        abs_index = os.path.abspath(index_path)
        abs_static = os.path.abspath(STATIC_DIR)
        host = request.headers.get("host", "unknown")
        print(f"[INDEX] host={host} index={abs_index} static={abs_static}")
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

    @app.get("/architecture.html")
    def serve_architecture():
        """Serve the architecture visualization page"""
        arch_path = os.path.join(STATIC_DIR, "architecture.html")
        if os.path.exists(arch_path):
            return FileResponse(arch_path, media_type="text/html")
        raise HTTPException(status_code=404, detail="Architecture page not found")

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

    @app.get("/__whoami")
    def whoami(request: Request):
        """Environment and deployment info"""
        import glob
        import subprocess
        js_files = glob.glob(os.path.join(STATIC_DIR, "assets", "index-*.js"))
        index_path = os.path.join(STATIC_DIR, "index.html")

        try:
            git_sha = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'],
                                             stderr=subprocess.DEVNULL).decode().strip()
        except:
            git_sha = 'unknown'

        return {
            "host": request.headers.get("host", "unknown"),
            "staticRoot": os.path.abspath(STATIC_DIR),
            "indexServedFrom": os.path.abspath(index_path),
            "buildId": "2025-10-25T12:10:00Z",
            "commit": git_sha,
            "currentJS": os.path.basename(js_files[0]) if js_files else None
        }

    @app.get("/aam-monitor")
    def serve_aam_monitor(request: Request):
        """Serve AAM Monitor frontend page"""
        index_path = os.path.join(STATIC_DIR, "index.html")
        host = request.headers.get("host", "unknown")
        print(f"[AAM MONITOR] host={host} -> serving index.html")
        if os.path.exists(index_path):
            return FileResponse(
                index_path,
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0"
                }
            )
        raise HTTPException(status_code=404, detail="Frontend not found")

    @app.get("/dashboard")
    def serve_dashboard(request: Request):
        """Serve Dashboard frontend page"""
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
        raise HTTPException(status_code=404, detail="Frontend not found")

    @app.get("/connections")
    def serve_connections(request: Request):
        """Serve Connections frontend page"""
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
        raise HTTPException(status_code=404, detail="Frontend not found")

    @app.get("/ontology")
    def serve_ontology(request: Request):
        """Serve Ontology frontend page"""
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
        raise HTTPException(status_code=404, detail="Frontend not found")

    @app.get("/live-flow")
    def serve_live_flow(request: Request):
        """Serve Live Flow frontend page"""
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
        raise HTTPException(status_code=404, detail="Frontend not found")
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

@app.get("/health")
async def health_check():
    """Primary health check endpoint for Autoscale deployment"""
    return {"status": "ok"}

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