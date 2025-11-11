from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config import settings
import logging

logger = logging.getLogger(__name__)


def get_database_url():
    """
    Get database URL with PgBouncer pooling (port 6543) for Supabase.
    
    Supabase provides two modes:
    - Port 5432: Session Mode (direct connection, strict limits)
    - Port 6543: Transaction/Pooling Mode (via PgBouncer, higher limits)
    """
    db_url = settings.DATABASE_URL
    
    # If using Supabase pooler with port 5432, switch to port 6543
    if "pooler.supabase.com:5432" in db_url:
        db_url = db_url.replace(":5432", ":6543")
        logger.info("🔄 Main app: Switched to PgBouncer pooling mode (port 6543)")
    
    return db_url


engine = create_engine(
    get_database_url(),
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=5,
    pool_recycle=300
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

async_db_url = get_database_url().replace("postgresql://", "postgresql+asyncpg://")
async_engine = create_async_engine(
    async_db_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_recycle=300,
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0
    }
)
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

def get_db():
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_async_db():
    """Async database session dependency"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
