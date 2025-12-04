"""
AAM database access - now uses unified shared.database module.
This breaks the circular dependency with app/database.py.
"""
import logging
from shared.database import AsyncSessionLocal, async_engine, Base
from sqlalchemy import text

logger = logging.getLogger(__name__)

logger.info("✅ AAM using shared database module (circular dependency broken)")


async def get_async_db():
    """
    Async database session for AAM endpoints with auto-commit/rollback
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


# Backward compatibility aliases
get_db = get_async_db  # Alias for backward compatibility
engine = async_engine  # Alias for backward compatibility


async def init_db():
    """
    Initialize database tables using shared engine
    """
    from .models import ConnectionStatus, JobStatus
    
    async with async_engine.begin() as conn:
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


__all__ = ["AsyncSessionLocal", "async_engine", "get_async_db", "get_db", "engine", "Base", "init_db"]
