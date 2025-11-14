import os
import sys
import asyncio
from contextlib import asynccontextmanager
from uuid import UUID
from datetime import timedelta
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
# OAUTH DISABLED - from fastapi.security import OAuth2PasswordRequestForm
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

# Add aam_hybrid to Python path for AAM service imports
sys.path.insert(0, 'aam_hybrid')

# Import AAM orchestration components
AAM_AVAILABLE = False
background_tasks = []
try:
    from aam_hybrid.services.schema_observer.service import SchemaObserver
    from aam_hybrid.services.rag_engine.service import RAGEngine as AAMRAGEngine
    from aam_hybrid.services.drift_repair_agent.service import DriftRepairAgent
    from aam_hybrid.services.orchestrator.service import handle_status_update, manager
    from aam_hybrid.shared.event_bus import event_bus
    AAM_AVAILABLE = True
    print("✅ AAM Hybrid orchestration modules imported successfully")
except ImportError as e:
    print(f"⚠️ AAM Hybrid orchestration not available: {e}")
except Exception as e:
    print(f"⚠️ AAM Hybrid orchestration initialization error: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage AAM background services lifecycle and application startup"""
    # STARTUP PHASE
    logger.info("🚀 Starting AutonomOS application...")
    
    # Initialize AAM database (create tables and enums)
    try:
        from aam_hybrid.shared.database import init_db
        await asyncio.wait_for(init_db(), timeout=5.0)
        logger.info("✅ AAM database initialized successfully")
    except asyncio.TimeoutError:
        logger.warning("⚠️ AAM database initialization timed out (PgBouncer conflict). Some AAM features may not work.")
    except Exception as e:
        logger.warning(f"⚠️ AAM database initialization failed: {e}. Some AAM features may not work.")
    
    # Initialize DCL RAG engine
    global dcl_app
    if dcl_app:
        from app.dcl_engine.rag_engine import RAGEngine as DCLRAGEngine
        try:
            dcl_app.rag_engine = DCLRAGEngine()
            logger.info("✅ DCL RAG Engine initialized successfully")
        except Exception as e:
            logger.warning(f"⚠️ DCL RAG Engine initialization failed: {e}. Continuing without RAG.")
    
    # Initialize DCL Agent Executor
    if dcl_app and redis_conn:
        from app.dcl_engine.agent_executor import AgentExecutor
        from app.dcl_engine.app import AGENT_RESULTS_CACHE, load_agents_config, DB_PATH
        import app.dcl_engine.app as dcl_app_module
        try:
            agents_config = load_agents_config()
            dcl_app.agent_executor = AgentExecutor(DB_PATH, agents_config, AGENT_RESULTS_CACHE, redis_conn)
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
            
            funnel_tracker = FunnelMetricsTracker(redis_conn)
            onboarding_module.funnel_tracker = funnel_tracker
            
            onboarding_service = OnboardingService(funnel_tracker)
            onboarding_module.onboarding_service = onboarding_service
            
            logger.info("✅ AAM Auto-Onboarding services initialized (Safe Mode enabled, 90% SLO target)")
        except Exception as e:
            logger.warning(f"⚠️ AAM Auto-Onboarding initialization failed: {e}. Auto-onboarding disabled.")
    else:
        logger.warning("⚠️ Redis not available - AAM Auto-Onboarding disabled")
    
    # Initialize production-grade feature flags with Redis persistence
    if redis_conn:
        try:
            from app.config.feature_flags import FeatureFlagConfig, FeatureFlag
            from app.dcl_engine.app import RedisDecodeWrapper
            
            # Wrap Redis client for decode_responses=True behavior
            redis_wrapper = RedisDecodeWrapper(redis_conn)
            FeatureFlagConfig.set_redis_client(redis_wrapper)
            
            # Log current flag states (hydrated from Redis)
            use_aam = FeatureFlagConfig.is_enabled(FeatureFlag.USE_AAM_AS_SOURCE)
            mode_name = "AAM Connectors" if use_aam else "Legacy File Sources"
            logger.info(f"✅ Feature flags initialized - USE_AAM_AS_SOURCE: {mode_name} (survives restarts)")
            
            # CRITICAL FIX: Start pub/sub listener in main app (Issue #1 & #2)
            # This ensures ALL workers (not just DCL engine) receive flag changes
            from app.config.redis_pubsub import ensure_pubsub_listener
            
            async def on_flag_change_callback(flag_name: str, flag_value: bool):
                """Handle flag changes in main app worker"""
                logger.info(f"🔄 Main App: Flag changed {flag_name}={flag_value}")
                
                # Clear DCL cache if USE_AAM_AS_SOURCE changes
                if flag_name == FeatureFlag.USE_AAM_AS_SOURCE.value and dcl_app:
                    try:
                        import app.dcl_engine.app as dcl_app_module
                        dcl_app_module.GRAPH_STATE = {
                            "nodes": [], "edges": [], 
                            "confidence": None, "last_updated": None
                        }
                        dcl_app_module.SOURCES_ADDED = []
                        mode_name = "AAM Connectors" if flag_value else "Legacy File Sources"
                        logger.info(f"🔄 Main App: DCL cache cleared - now using {mode_name}")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to clear DCL cache: {e}")
            
            await ensure_pubsub_listener(on_flag_change=on_flag_change_callback)
            logger.info("✅ Main App: Feature flag pub/sub listener started (production-ready)")
            
        except Exception as e:
            logger.warning(f"⚠️ Feature flag initialization failed: {e}. Using in-memory fallback.")
    else:
        logger.warning("⚠️ Redis not available - feature flags will use in-memory storage only")
    
    # Start AAM Hybrid Orchestration Services
    if AAM_AVAILABLE:
        logger.info("🚀 Starting AAM Hybrid orchestration services...")
        try:
            # Initialize Event Bus
            await event_bus.connect()
            logger.info("✅ Event Bus connected")
            
            # Initialize services
            schema_observer = SchemaObserver()
            aam_rag_engine = AAMRAGEngine()
            drift_repair_agent = DriftRepairAgent()
            
            # Subscribe to channels
            await event_bus.subscribe("aam:drift_detected", aam_rag_engine.handle_drift_detected)
            await event_bus.subscribe("aam:repair_proposed", drift_repair_agent.handle_repair_proposed)
            await event_bus.subscribe("aam:status_update", handle_status_update)
            
            # Start background tasks
            tasks = [
                asyncio.create_task(event_bus.listen(), name="event_bus_listener"),
                asyncio.create_task(schema_observer.polling_loop(), name="schema_observer"),
            ]
            background_tasks.extend(tasks)
            logger.info(f"✅ Started {len(tasks)} AAM orchestration background tasks")
            
        except Exception as e:
            logger.error(f"⚠️ Failed to start AAM orchestration services: {e}")
    else:
        logger.warning("⚠️ AAM orchestration services disabled - imports not available")
    
    logger.info("✅ AutonomOS startup complete")
    
    yield  # Application runs here
    
    # SHUTDOWN PHASE
    logger.info("🛑 Shutting down AutonomOS application...")
    
    # Stop feature flag pub/sub listener
    if redis_conn:
        try:
            from app.config.redis_pubsub import stop_pubsub_listener
            await stop_pubsub_listener()
            logger.info("✅ Feature flag pub/sub listener stopped")
        except Exception as e:
            logger.warning(f"⚠️ Error stopping pub/sub listener: {e}")
    
    # Cancel AAM background tasks
    for task in background_tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            logger.debug(f"Task {task.get_name()} cancelled successfully")
    
    # Disconnect event bus
    if AAM_AVAILABLE:
        try:
            await event_bus.disconnect()
            logger.info("✅ AAM orchestration services stopped")
        except Exception as e:
            logger.warning(f"⚠️ Error during AAM shutdown: {e}")
    
    logger.info("✅ AutonomOS shutdown complete")

app = FastAPI(
    title="AutonomOS", 
    description="AI Orchestration Platform - Multi-Tenant Edition", 
    version="2.0.0",
    lifespan=lifespan
)

# PRODUCTION FIX: Global exception handler to ensure JSON responses in production
# Without this, Replit's production proxy returns plain text "Internal Server Error"
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions and return JSON (not plain text)"""
    logger.error(f"Unhandled exception on {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc), "path": str(request.url.path)}
    )

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
    import ssl as ssl_module
    REDIS_URL = os.getenv("REDIS_URL")
    if REDIS_URL:
        # Fix for Upstash Redis: Change redis:// to rediss:// to enable TLS/SSL
        # Upstash requires TLS connections, and rediss:// protocol enables this
        if REDIS_URL.startswith("redis://"):
            REDIS_URL = "rediss://" + REDIS_URL[8:]
            print("🔒 Using TLS/SSL for Redis connection (rediss:// protocol)")

        # Add SSL parameters for rediss:// connections (Redis Cloud/Upstash)
        # Disable certificate verification for compatibility with managed Redis services
        if REDIS_URL.startswith("rediss://"):
            redis_conn = Redis.from_url(REDIS_URL, decode_responses=False, ssl_cert_reqs=ssl_module.CERT_NONE)
        else:
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

# OAUTH ENDPOINT DISABLED PER USER REQUEST
# @app.post("/token", response_model=schemas.Token)
# def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
#     """
#     Login endpoint to get a JWT access token.
#     Use email as username and provide password.
#     """
#     user = authenticate_user(db, form_data.username, form_data.password)
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Incorrect email or password",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
# 
#     access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
#     access_token = create_access_token(
#         data={"user_id": str(user.id), "tenant_id": str(user.tenant_id)},
#         expires_delta=access_token_expires
#     )
# 
#     return {"access_token": access_token, "token_type": "bearer"}

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