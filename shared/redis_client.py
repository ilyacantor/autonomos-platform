"""
Shared Redis client for AutonomOS.
Provides a singleton Redis connection with automatic fallback and TLS/SSL support.
"""
import os
import ssl as ssl_module
from redis import Redis
from typing import Optional
import logging

logger = logging.getLogger(__name__)

_redis_client: Optional[Redis] = None
_redis_available: bool = False


def get_redis_client() -> Optional[Redis]:
    """
    Get or create the shared Redis client instance with TLS/SSL support.
    Returns None if Redis is unavailable.
    """
    global _redis_client, _redis_available
    
    if _redis_client is not None:
        return _redis_client
    
    REDIS_URL = os.getenv("REDIS_URL")
    
    try:
        if REDIS_URL:
            if REDIS_URL.startswith("rediss://"):
                # TLS/SSL connection - FAIL FAST if cert missing
                CA_CERT_PATH = os.path.join(
                    os.path.dirname(__file__), 
                    "..", 
                    "certs", 
                    "redis_ca.pem"
                )
                
                # ✅ FIX: Fail fast if cert required but missing
                if not os.path.exists(CA_CERT_PATH):
                    raise RuntimeError(
                        f"Redis TLS requires CA certificate at {CA_CERT_PATH} but file not found. "
                        "Cannot establish secure connection."
                    )
                
                _redis_client = Redis.from_url(
                    REDIS_URL,
                    decode_responses=True,
                    ssl_cert_reqs=ssl_module.CERT_REQUIRED,
                    ssl_ca_certs=CA_CERT_PATH  # Now guaranteed to exist
                )
                logger.info("Redis client initialized with TLS/SSL")
            else:
                _redis_client = Redis.from_url(REDIS_URL, decode_responses=True)
                logger.info("Redis client initialized (non-TLS)")
        else:
            _redis_client = Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                db=int(os.getenv("REDIS_DB", "0")),
                decode_responses=True
            )
            logger.info("Redis client initialized with default settings")
        
        _redis_client.ping()
        _redis_available = True
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
