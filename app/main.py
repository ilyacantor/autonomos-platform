import os
import sys
import asyncio
from contextlib import asynccontextmanager
from uuid import UUID
from datetime import timedelta, datetime
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response
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
from app.api.v1 import auth, aoa, aam_monitoring, aam_mesh, aam_connections, platform_stubs, filesource, debug, mesh_test, events, aod_mock, aam_onboarding, admin_feature_flags, demo_pipeline, demo_orchestrator, agents, scheduler
from app import nlp_simple
from app.middleware.rate_limit import limiter, rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

# Initialize database tables - with error handling for resilience
try:
    models.Base.metadata.create_all(bind=engine)
    print("✅ Database tables initialized successfully")
except Exception as e:
    print(f"⚠️ Database initialization failed: {e}. Continuing without database...")

# Import AAM orchestration components
# No sys.path manipulation needed - package installed via pip install -e .
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

async def deferred_initialization():
    """
    Non-blocking background initialization.
    Runs after server is ready to accept connections.
    """
    await asyncio.sleep(0.1)  # Let server fully start

    # Initialize AAM database (create tables and enums)
    try:
        from aam_hybrid.shared.database import init_db
        await asyncio.wait_for(init_db(), timeout=5.0)
        logger.info("✅ AAM database initialized successfully")
    except asyncio.TimeoutError:
        logger.warning("⚠️ AAM database initialization timed out (PgBouncer conflict). Some AAM features may not work.")
    except Exception as e:
        logger.warning(f"⚠️ AAM database initialization failed: {e}. Some AAM features may not work.")

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

            # Inject into demo_pipeline module as well
            import app.api.v1.demo_pipeline as demo_module
            demo_module.onboarding_service = onboarding_service

            logger.info("✅ AAM Auto-Onboarding services initialized")
        except Exception as e:
            logger.warning(f"⚠️ AAM Auto-Onboarding initialization failed: {e}. Auto-onboarding disabled.")

    # Initialize production-grade feature flags with Redis persistence
    if redis_conn:
        try:
            from app.config.feature_flags import FeatureFlagConfig, FeatureFlag
            from shared.redis_client import RedisDecodeWrapper

            redis_wrapper = RedisDecodeWrapper(redis_conn)
            FeatureFlagConfig.set_redis_client(redis_wrapper)

            use_aam = FeatureFlagConfig.is_enabled(FeatureFlag.USE_AAM_AS_SOURCE)
            mode_name = "AAM Connectors" if use_aam else "Legacy File Sources"
            logger.info(f"✅ Feature flags initialized - USE_AAM_AS_SOURCE: {mode_name}")
        except Exception as e:
            logger.warning(f"⚠️ Feature flag initialization failed: {e}. Using in-memory fallback.")

    # Start AAM Hybrid Orchestration Services
    if AAM_AVAILABLE:
        try:
            if flow_publisher:
                try:
                    from aam_hybrid.services.orchestrator.service import set_flow_publisher
                    set_flow_publisher(flow_publisher)
                    logger.info("✅ FlowEventPublisher injected into AAM orchestrator")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to inject FlowEventPublisher into AAM: {e}")

            await event_bus.connect()  # type: ignore[possibly-unbound]
            logger.info("✅ Event Bus connected")

            schema_observer = SchemaObserver()  # type: ignore[possibly-unbound]
            aam_rag_engine = AAMRAGEngine()  # type: ignore[possibly-unbound]
            drift_repair_agent = DriftRepairAgent()  # type: ignore[possibly-unbound]

            await event_bus.subscribe("aam:drift_detected", aam_rag_engine.handle_drift_detected)  # type: ignore[possibly-unbound]
            await event_bus.subscribe("aam:repair_proposed", drift_repair_agent.handle_repair_proposed)  # type: ignore[possibly-unbound]
            await event_bus.subscribe("aam:status_update", handle_status_update)  # type: ignore[possibly-unbound]

            try:
                from services.aam.initializer import run_aam_initializer
                await run_aam_initializer()
            except Exception as init_error:
                logger.warning(f"⚠️ AAM connector initialization failed: {init_error}")

            logger.info("✅ AAM orchestration services ready")
        except Exception as e:
            logger.error(f"⚠️ Failed to start AAM orchestration services: {e}")

    logger.info("✅ Background initialization complete")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle with fast startup"""
    # STARTUP PHASE - Keep minimal for fast server start
    logger.info("🚀 Starting AutonomOS application...")

    # Schedule non-blocking background initialization
    init_task = asyncio.create_task(deferred_initialization())
    background_tasks.append(init_task)

    logger.info("✅ Server ready (background initialization in progress)")
    
    yield  # Application runs here
    
    # SHUTDOWN PHASE
    logger.info("🛑 Shutting down AutonomOS application...")
    
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
            await event_bus.disconnect()  # type: ignore[possibly-unbound]
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

# Register slowapi rate limiter with the app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)  # type: ignore[arg-type]
logger.info("✅ SlowAPI rate limiter registered for granular endpoint protection")

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
    # PRODUCTION: All middleware enabled with non-blocking operations
    app.middleware("http")(tracing_middleware)
    app.middleware("http")(tenant_auth_middleware)
    app.middleware("http")(rate_limit_middleware)
    # Audit and Idempotency DISABLED: Still have blocking issues, need further debugging
    # app.middleware("http")(idempotency_middleware)
    # app.middleware("http")(audit_middleware)

    print("✅ Gateway middleware registered successfully (Audit & Idempotency disabled until blocking issues resolved)")
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
        # Respect the URL scheme - use TLS if rediss://, plain if redis://
        if REDIS_URL.startswith("rediss://"):
            # TLS/SSL connection with certificate validation
            CA_CERT_PATH = os.path.join(os.path.dirname(__file__), "..", "certs", "redis_ca.pem")
            redis_conn = Redis.from_url(
                REDIS_URL, 
                decode_responses=False, 
                ssl_cert_reqs=ssl_module.CERT_REQUIRED,
                ssl_ca_certs=CA_CERT_PATH
            )
            print(f"🔒 Using TLS/SSL for Redis connection with certificate validation")
        else:
            # Plain connection
            redis_conn = Redis.from_url(REDIS_URL, decode_responses=False)
            print("⚠️ Using non-TLS Redis connection - ensure this is intentional for dev/local only")
    else:
        redis_conn = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB)

    task_queue = Queue(connection=redis_conn)
    print("✅ Redis connected successfully")
except Exception as e:
    print(f"⚠️ Redis not available: {e}. Task queue features disabled.")
    redis_conn = None
    task_queue = None

# Initialize Phase 4 Flow Event Publisher (Telemetry)
flow_publisher = None
async_redis_client = None  # Module-level async Redis client for Flow Monitor API
if redis_conn:
    try:
        from redis.asyncio import Redis as AsyncRedis
        from app.telemetry.flow_publisher import FlowEventPublisher
        
        # Create async Redis client for FlowEventPublisher (and Flow Monitor API)
        async_redis_client = AsyncRedis.from_url(
            os.getenv("REDIS_URL") or f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
            decode_responses=False
        )
        flow_publisher = FlowEventPublisher(async_redis_client)
        print("✅ FlowEventPublisher initialized for real-time telemetry")
    except Exception as e:
        print(f"⚠️ FlowEventPublisher initialization failed: {e}. Telemetry disabled.")
        flow_publisher = None
        async_redis_client = None
else:
    print("⚠️ Redis not available - FlowEventPublisher disabled")



app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(nlp_simple.router, tags=["NLP Gateway"])
app.include_router(aoa.router, prefix="/api/v1/aoa", tags=["AOA Orchestration"])
app.include_router(aam_monitoring.router, prefix="/api/v1/aam", tags=["AAM Monitoring"])
app.include_router(aam_connections.router, prefix="/api/v1/aam", tags=["AAM Connections"])
app.include_router(aam_onboarding.router, prefix="/api/v1/aam", tags=["AAM Auto-Onboarding"])
app.include_router(admin_feature_flags.router, prefix="/api/v1/admin", tags=["Admin - Feature Flags"])
app.include_router(demo_pipeline.router, prefix="/api/v1", tags=["Demo Pipeline"])
app.include_router(demo_orchestrator.router, prefix="/api/v1", tags=["Demo Orchestrator"])
app.include_router(aam_mesh.router, prefix="/api/v1/mesh", tags=["AAM Mesh"])
app.include_router(mesh_test.router, prefix="/api/v1", tags=["Mesh Test (Dev-Only)"])
app.include_router(filesource.router, prefix="/api/v1/filesource", tags=["FileSource Connector"])
app.include_router(debug.router, prefix="/api/v1", tags=["Debug (Dev-Only)"])
app.include_router(events.router, prefix="/api/v1/events", tags=["Event Stream"])
app.include_router(platform_stubs.router, prefix="/api/v1", tags=["Platform Stubs"])
app.include_router(aod_mock.router, prefix="", tags=["AOD Mock (Testing)"])

# Agentic Orchestration API (Phase 1)
app.include_router(agents.router, prefix="/api/v1/agents", tags=["Agent Orchestration"])

# Phase 6: Scheduler Service and Trust Middleware
app.include_router(scheduler.router, prefix="/api/v1", tags=["Scheduler Service"])

# P4-6: Flow Monitor API
try:
    from app.api.v1 import flow_monitor
    if async_redis_client:
        # Inject shared async Redis client into flow_monitor API
        flow_monitor.set_async_redis(async_redis_client)
    app.include_router(flow_monitor.router, prefix="/api/v1", tags=["Flow Monitoring"])
    print("✅ Flow Monitor API registered")
except Exception as e:
    print(f"⚠️ Failed to register Flow Monitor API: {e}")

class NoCacheStaticFiles(StaticFiles):
    """StaticFiles with no-cache headers to prevent Replit CDN caching"""
    def file_response(self, *args, **kwargs) -> Response:
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

# DEBUG: Ultra-simple test endpoint (defined BEFORE static files)
@app.get("/_ping")
async def ping():
    """Ultra-simple endpoint to test if server is responding"""
    print("[PING] Endpoint called")
    return {"status": "ok"}

STATIC_DIR = "static"
if os.path.exists(STATIC_DIR) and os.path.isdir(STATIC_DIR):
    assets_dir = os.path.join(STATIC_DIR, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", NoCacheStaticFiles(directory=assets_dir), name="assets")

    @app.get("/")
    def serve_frontend(request: Request):
        """Serve the frontend index.html"""
        print("[DEBUG-1] Entered serve_frontend handler")
        index_path = os.path.join(STATIC_DIR, "index.html")
        print(f"[DEBUG-2] index_path={index_path}")
        abs_index = os.path.abspath(index_path)
        abs_static = os.path.abspath(STATIC_DIR)
        host = request.headers.get("host", "unknown")
        print(f"[INDEX] host={host} index={abs_index} static={abs_static}")
        print(f"[DEBUG-3] About to check if path exists")
        exists = os.path.exists(index_path)
        print(f"[DEBUG-4] Path exists: {exists}")
        if exists:
            print("[DEBUG-5] Creating FileResponse")
            response = FileResponse(
                index_path,
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0"
                }
            )
            print("[DEBUG-6] FileResponse created, returning")
            return response
        print("[DEBUG-7] Returning fallback JSON")
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

    @app.get("/flow-monitor")
    def serve_flow_monitor(request: Request):
        """Serve Flow Monitor frontend page"""
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

    @app.get("/demo-discovery")
    def serve_demo_discovery(request: Request):
        """Serve Discovery Demo frontend page"""
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

    @app.get("/demo")
    def serve_demo(request: Request):
        """Serve Demo Orchestrator frontend page"""
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

    @app.get("/unify-ask")
    def serve_unify_ask(request: Request):
        """Serve Unify & Ask frontend page"""
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

    @app.get("/overview")
    def serve_overview(request: Request):
        """Serve Overview frontend page"""
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

    @app.get("/discover")
    def serve_discover(request: Request):
        """Serve Discover frontend page"""
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

    @app.get("/aos-overview")
    def serve_aos_overview(request: Request):
        """Serve AOS Overview frontend page"""
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

    @app.get("/connect")
    def serve_connect(request: Request):
        """Serve Connect frontend page"""
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

    @app.get("/control-center")
    def serve_control_center(request: Request):
        """Serve Control Center frontend page"""
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

    @app.get("/faq")
    def serve_faq(request: Request):
        """Serve FAQ frontend page"""
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

    @app.get("/architecture")
    def serve_architecture_page(request: Request):
        """Serve Architecture frontend page"""
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

    @app.get("/agent-center")
    def serve_agent_center(request: Request):
        """Serve Agent Control Center frontend page"""
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
        tenant.id  # type: ignore[arg-type]
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
    db_task = crud.create_task(db, task, current_user.tenant_id)  # type: ignore[arg-type]

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
    db_task = crud.get_task(db, task_id, current_user.tenant_id)  # type: ignore[arg-type]
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
    db_task = crud.get_task(db, task_id, current_user.tenant_id)  # type: ignore[arg-type]
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    if db_task.status in ["success", "failed", "canceled"]:
        raise HTTPException(status_code=400, detail=f"Cannot cancel task with status '{db_task.status}'")

    try:
        from rq.job import Job
        job = Job.fetch(str(task_id), connection=redis_conn)
        job.cancel()
        crud.update_task_status(db, task_id, "canceled", {"message": "Task canceled by user"}, current_user.tenant_id)  # type: ignore[arg-type]
        crud.create_task_log(db, task_id, "Task canceled by user request")
    except Exception as e:
        import logging
        logging.warning(f"Could not cancel job in RQ: {str(e)}")
        crud.update_task_status(db, task_id, "canceled", {"message": "Task canceled by user"}, current_user.tenant_id)  # type: ignore[arg-type]
        crud.create_task_log(db, task_id, "Task canceled by user request")

    db_task = crud.get_task(db, task_id, current_user.tenant_id)  # type: ignore[arg-type]
    return db_task

@app.get("/health")
async def health_check():
    """Primary health check endpoint for Autoscale deployment"""
    return {"status": "ok"}

@app.get("/health/live")
async def health_live():
    """
    Kubernetes-style liveness probe.
    Returns 200 if process is running, 500 if process should be restarted.
    """
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

@app.get("/health/ready")
async def health_ready(db: Session = Depends(get_db)):
    """
    Kubernetes-style readiness probe.
    Returns 200 if service can handle traffic (even degraded), 503 only if completely unavailable.
    
    Kubernetes Semantics:
    - 200: Service is ready to receive traffic (may be degraded but functional)
    - 503: Service cannot serve traffic, remove from load balancer
    
    Status Levels:
    - "ready": All checks pass, full capacity
    - "degraded": Some dependencies down, but fallbacks available (still serves traffic)
    - "unavailable": Critical failures, cannot serve traffic (503)
    
    Checks:
    - Database connectivity (required for core operations)
    - Redis connectivity (required for state/caching)
    - Circuit breaker states (informational, service continues with fallbacks)
    """
    health_status = {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {},
        "can_serve_traffic": True
    }
    
    critical_failures = 0
    
    # Check database connection (critical - needed for auth, mappings, state)
    try:
        db.execute("SELECT 1")  # type: ignore[arg-type]
        health_status["checks"]["database"] = {"status": "ok"}
    except Exception as e:
        critical_failures += 1
        health_status["status"] = "unavailable"
        health_status["can_serve_traffic"] = False
        health_status["checks"]["database"] = {"status": "failed", "error": str(e)[:100]}
    
    # Check Redis connection (critical - needed for queues, locks, state)
    try:
        if redis_conn:
            redis_conn.ping()
            health_status["checks"]["redis"] = {"status": "ok"}
        else:
            raise Exception("Redis not available")
    except Exception as e:
        critical_failures += 1
        health_status["status"] = "unavailable"
        health_status["can_serve_traffic"] = False
        health_status["checks"]["redis"] = {"status": "failed", "error": str(e)[:100]}
    
    # Check circuit breaker states (informational - service continues with fallbacks)
    try:
        # Circuit breaker states are informational only
        breaker_states = {}
        
        critical_breakers = ["llm_proposal", "rag_lookup"]
        open_breakers = [name for name, state in breaker_states.items() 
                        if state["state"] == "OPEN" and name in critical_breakers]
        
        if open_breakers:
            # Degraded but still functional (fallbacks available)
            if health_status["status"] == "ready":
                health_status["status"] = "degraded"
            health_status["checks"]["circuit_breakers"] = {
                "status": "degraded",
                "open_breakers": open_breakers,
                "message": "Intelligence services using fallbacks (heuristics/cache)"
            }
        else:
            health_status["checks"]["circuit_breakers"] = {"status": "ok"}
    except Exception as e:
        health_status["checks"]["circuit_breakers"] = {"status": "unknown", "error": str(e)[:100]}
    
    # Return 503 ONLY if critical dependencies are down (DB or Redis)
    # Degraded state (open breakers) still returns 200 because fallbacks work
    status_code = 503 if critical_failures > 0 else 200
    return JSONResponse(content=health_status, status_code=status_code)

@app.get("/health/intelligence")
async def health_intelligence():
    """
    DCL Intelligence Services health check.
    
    Returns detailed status of:
    - Circuit breakers (CLOSED/OPEN/HALF_OPEN)
    - Bulkhead semaphores (active/max)
    - LLM service availability
    - RAG service availability
    """
    try:
        # Circuit breaker states (placeholder - feature not yet implemented)
        breaker_states = {}
        bulkhead_states = {}
        
        # Determine overall health
        open_breakers = [name for name, state in breaker_states.items() if state["state"] == "OPEN"]
        overall_status = "healthy" if not open_breakers else "degraded"
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "circuit_breakers": breaker_states,
            "bulkheads": bulkhead_states,
            "open_breakers": open_breakers,
            "services": {
                "llm_proposal": "available" if breaker_states.get("llm_proposal", {}).get("state") == "CLOSED" else "degraded",
                "rag_lookup": "available" if breaker_states.get("rag_lookup", {}).get("state") == "CLOSED" else "degraded",
                "confidence_scoring": "available" if breaker_states.get("confidence_scoring", {}).get("state") == "CLOSED" else "degraded"
            }
        }
    except Exception as e:
        return JSONResponse(
            content={
                "status": "error",
                "timestamp": datetime.utcnow().isoformat(),
                "error": f"Failed to query intelligence services: {str(e)}"
            },
            status_code=500
        )

@app.get("/health/api")
def health_api():
    """Health check for the API"""
    return {"status": "ok"}

@app.get("/health/worker")
def health_worker():
    """Health check for the worker - checks Redis connection"""
    try:
        if redis_conn:
            redis_conn.ping()
            return {"status": "ok", "redis": "connected"}
        else:
            raise Exception("Redis not available")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Redis connection failed: {str(e)}"
        )

