from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config import settings
import logging

logger = logging.getLogger(__name__)


def get_database_url(for_async=False):
    """
    Get database URL with PgBouncer pooling (port 6543) for Supabase.
    
    Supabase provides two modes:
    - Port 5432: Session Mode (direct connection, strict limits)
    - Port 6543: Transaction/Pooling Mode (via PgBouncer, higher limits)
    
    Args:
        for_async: If True, keeps prepare_threshold parameter for psycopg3.
                   If False, strips it for psycopg2 compatibility.
    """
    db_url = settings.DATABASE_URL
    
    # If using Supabase pooler with port 5432, switch to port 6543
    if "pooler.supabase.com:5432" in db_url:
        db_url = db_url.replace(":5432", ":6543")
        logger.info("🔄 Main app: Switched to PgBouncer pooling mode (port 6543)")
    
    # Remove prepare_threshold for sync connections (psycopg2 doesn't support it)
    if not for_async and "prepare_threshold" in db_url:
        # Strip prepare_threshold parameter from query string
        import re
        db_url = re.sub(r'[&?]prepare_threshold=\d+', '', db_url)
        # Clean up any remaining ? or & at the end
        db_url = re.sub(r'[?&]$', '', db_url)
        logger.info("🔧 Removed prepare_threshold for psycopg2 compatibility")
    
    return db_url


engine = create_engine(
    get_database_url(for_async=False),  # Strip prepare_threshold for psycopg2
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=5,
    pool_recycle=300
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

async_db_url = get_database_url(for_async=True).replace("postgresql://", "postgresql+psycopg://")  # Keep prepare_threshold for psycopg3
async_engine = create_async_engine(
    async_db_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_recycle=300,
    pool_use_lifo=True
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
