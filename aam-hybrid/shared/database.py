from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from .config import settings
import logging

logger = logging.getLogger(__name__)


engine = create_async_engine(
    settings.SUPABASE_DB_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=True,
    future=True,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10
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
