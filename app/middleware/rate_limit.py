"""
Rate limiting middleware for AutonomOS API endpoints.
Uses slowapi (wrapper around SlowAPI/limits) for request rate limiting.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from fastapi.responses import JSONResponse
import logging
import os

logger = logging.getLogger(__name__)

# Check if running in test mode
# CRITICAL: Disable rate limiting for automated tests to prevent 429 errors
TESTING_MODE = os.getenv("TESTING", "false").lower() == "true" or \
               os.getenv("PYTEST_CURRENT_TEST") is not None

if TESTING_MODE:
    # Disable rate limiting during tests by setting extremely high limits
    # This prevents test suite from hitting 429 errors during rapid automated requests
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["999999999/minute"]  # Effectively unlimited for tests
    )
    logger.info("⚠️ Rate limiting DISABLED for test environment")
else:
    # Production rate limiting (normal behavior)
    limiter = Limiter(key_func=get_remote_address)
    logger.info("✅ Rate limiting ENABLED for production")


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """
    Custom handler for rate limit exceeded errors.
    Returns JSON response with retry-after header.
    """
    logger.warning(
        f"Rate limit exceeded for {request.client.host} on {request.url.path}"
    )
    
    return JSONResponse(
        status_code=429,
        content={
            "error": "Too many requests",
            "detail": f"Rate limit exceeded. {exc.detail}",
            "retry_after": getattr(exc, 'retry_after', 60)
        },
        headers={
            "Retry-After": str(getattr(exc, 'retry_after', 60))
        }
    )
