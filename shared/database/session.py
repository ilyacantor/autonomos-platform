from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from .engine import sync_engine, async_engine

# Sync session factory (psycopg2)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine
)

# Async session factory (psycopg3)
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# FastAPI dependencies (for backward compatibility)
def get_db():
    """Sync database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_async_db():
    """Async database session dependency"""
    async with AsyncSessionLocal() as session:
        yield session
