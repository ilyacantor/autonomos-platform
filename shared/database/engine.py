from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine
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
        logger.info("🔄 Shared database: Switched to PgBouncer pooling mode (port 6543)")
    
    return db_url


# Get database URLs
DATABASE_URL = get_database_url()
ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://")

# Sync engine (psycopg2) - for compatibility with existing code
# Reduced pool sizes for Supabase compatibility (Session mode has ~15 connection limit)
sync_engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=2,
    max_overflow=3,
    pool_recycle=300
)

# Async engine (psycopg3) - for async endpoints
# Reduced pool sizes for Supabase compatibility (Session mode has ~15 connection limit)
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=2,
    max_overflow=3,
    pool_recycle=300,
    pool_use_lifo=True
)

logger.info(f"✅ Shared database engines initialized")
