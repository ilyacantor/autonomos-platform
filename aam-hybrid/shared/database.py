from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from .config import settings
import logging

logger = logging.getLogger(__name__)


def get_database_url():
    """
    Get database URL with PgBouncer pooling (port 6543) for Supabase.
    
    Supabase provides two modes:
    - Port 5432: Session Mode (direct connection, strict limits)
    - Port 6543: Transaction/Pooling Mode (via PgBouncer, higher limits)
    
    We use port 6543 to avoid "MaxClientsInSessionMode" errors.
    """
    db_url = settings.SUPABASE_DB_URL
    
    # If using Supabase pooler with port 5432, switch to port 6543
    if "pooler.supabase.com:5432" in db_url:
        db_url = db_url.replace(":5432", ":6543")
        logger.info("🔄 Switched to PgBouncer pooling mode (port 6543)")
    
    return db_url.replace("postgresql://", "postgresql+asyncpg://")


engine = create_async_engine(
    get_database_url(),
    echo=False,
    future=True,
    pool_pre_ping=True,
    pool_size=2,
    max_overflow=2,
    pool_recycle=300,
    connect_args={"statement_cache_size": 0}
)


AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


async def get_db():
    """
    Dependency for getting async database sessions
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


async def init_db():
    """
    Initialize database tables
    """
    from .models import Base, ConnectionStatus, JobStatus
    from sqlalchemy import text
    
    async with engine.begin() as conn:
        logger.info("Creating database tables...")
        
        # Create enum types if they don't exist
        await conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE connectionstatus AS ENUM ('PENDING', 'ACTIVE', 'FAILED', 'HEALING', 'INACTIVE');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """))
        
        await conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE jobstatus AS ENUM ('pending', 'running', 'succeeded', 'failed', 'cancelled');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """))
        
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
