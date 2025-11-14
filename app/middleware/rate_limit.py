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

logger = logging.getLogger(__name__)

# Initialize rate limiter
# Key function determines what to rate limit by (IP address in this case)
limiter = Limiter(key_func=get_remote_address)


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
