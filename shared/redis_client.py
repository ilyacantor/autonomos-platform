"""
Shared Redis client for AutonomOS.
Provides a singleton Redis connection with automatic fallback.
"""
import os
from redis import Redis
from typing import Optional
import logging

logger = logging.getLogger(__name__)

_redis_client: Optional[Redis] = None
_redis_available: bool = False


def get_redis_client() -> Optional[Redis]:
    """
    Get or create the shared Redis client instance.
    Returns None if Redis is unavailable.
    """
    global _redis_client, _redis_available
    
    if _redis_client is not None:
        return _redis_client
    
    REDIS_URL = os.getenv("REDIS_URL")
    
    try:
        if REDIS_URL:
            _redis_client = Redis.from_url(REDIS_URL, decode_responses=True)
        else:
            _redis_client = Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                db=int(os.getenv("REDIS_DB", "0")),
                decode_responses=True
            )
        
        _redis_client.ping()
        _redis_available = True
        logger.info("Redis client initialized successfully")
        return _redis_client
    
    except Exception as e:
        logger.warning(f"Redis unavailable: {e}")
        _redis_client = None
        _redis_available = False
        return None


def is_redis_available() -> bool:
    """Check if Redis is available."""
    global _redis_available
    
    if _redis_client is None:
        get_redis_client()
    
    return _redis_available


redis_client = get_redis_client()
REDIS_AVAILABLE = is_redis_available()
