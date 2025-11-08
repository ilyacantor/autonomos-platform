import os
from typing import AsyncGenerator
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from .utils import generate_trace_id, get_logger, set_trace_id
from .auth.middleware import auth_middleware
from .api import (
    finops_router,
    revops_router,
    aod_router,
    aam_router,
    kb_search_router,
    kb_ingest_router,
    feedback_router
)

logger = get_logger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = None
async_session_maker = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Sets up database connection pool on startup and cleanup on shutdown.
    """
    global engine, async_session_maker
    
    try:
        engine = create_async_engine(
            DATABASE_URL,
            echo=False,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10
        )
        async_session_maker = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        logger.info("✅ NLP Gateway database connection initialized")
    except Exception as e:
        logger.error(f"⚠️ Database initialization failed: {e}")
        raise
    
    yield
    
    if engine:
        await engine.dispose()
        logger.info("✅ NLP Gateway database connection closed")


app = FastAPI(
    title="AOS NLP Gateway",
    description="Natural language interface over AutonomOS services",
    version="1.0.0",
    lifespan=lifespan
)

allowed_origins = [
    os.getenv("ALLOWED_WEB_ORIGIN", "http://localhost:5173"),
    "http://localhost:5173",
    "http://localhost:5000",
]

if os.getenv("REPL_SLUG"):
    allowed_origins.append("*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if "*" not in allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def trace_id_middleware(request: Request, call_next):
    """
    Inject trace_id into every request for observability.
    """
    trace_id = request.headers.get("X-Trace-ID") or generate_trace_id()
    set_trace_id(trace_id)
    
    request.state.trace_id = trace_id
    
    response = await call_next(request)
    response.headers["X-Trace-ID"] = trace_id
    
    return response


app.middleware("http")(auth_middleware)


app.include_router(finops_router)
app.include_router(revops_router)
app.include_router(aod_router)
app.include_router(aam_router)
app.include_router(kb_search_router)
app.include_router(kb_ingest_router)
app.include_router(feedback_router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler to ensure all errors return trace_id.
    """
    trace_id = getattr(request.state, "trace_id", "no-trace-id")
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "trace_id": trace_id
        }
    )


@app.get("/health")
async def health():
    """
    Health check endpoint (bypasses auth).
    """
    return {
        "status": "healthy",
        "service": "nlp-gateway",
        "version": "1.0.0"
    }


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session dependency for FastAPI.
    
    Usage in FastAPI routes:
        @router.post("/endpoint")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            # use db session
    """
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
