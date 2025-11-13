import sys
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.database import AsyncSessionLocal as AppAsyncSessionLocal, async_engine

AsyncSessionLocal = AppAsyncSessionLocal
engine = async_engine

logger.info("✅ AAM using shared PgBouncer-safe async session factory from app.database")


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
    Initialize database tables using shared PgBouncer-safe engine
    """
    from .models import Base, ConnectionStatus, JobStatus
    from sqlalchemy import text
    
    async with engine.begin() as conn:
        logger.info("Creating AAM database tables using shared engine...")
        
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
        logger.info("✅ AAM database tables created successfully (shared engine)")
