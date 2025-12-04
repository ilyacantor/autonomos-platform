"""
Database configuration - Compatibility shim.
All database access now goes through shared.database module.
This file maintained for backward compatibility with existing imports.
"""
from shared.database import (
    Base,
    sync_engine as engine,  # Alias for compatibility
    async_engine,
    SessionLocal,
    AsyncSessionLocal,
    get_db,
    get_async_db,
    get_database_url,
)

__all__ = [
    "Base",
    "engine",
    "async_engine",
    "SessionLocal",
    "AsyncSessionLocal",
    "get_db",
    "get_async_db",
    "get_database_url",
]
