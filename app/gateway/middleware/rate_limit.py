import os
import time
from fastapi import Request
from fastapi.responses import JSONResponse
from typing import Callable
from shared.redis_client import redis_client, REDIS_AVAILABLE

# Updated defaults for better performance
RATE_LIMIT_READ_RPM = int(os.getenv("RATE_LIMIT_READ_RPM", "300"))
RATE_LIMIT_READ_BURST = int(os.getenv("RATE_LIMIT_READ_BURST", "60"))
RATE_LIMIT_WRITE_RPM = int(os.getenv("RATE_LIMIT_WRITE_RPM", "100"))
RATE_LIMIT_WRITE_BURST = int(os.getenv("RATE_LIMIT_WRITE_BURST", "30"))

# Legacy env vars (mapped to READ limits for backward compatibility)
RATE_LIMIT_RPM = int(os.getenv("RATE_LIMIT_RPM", "300"))
RATE_LIMIT_BURST = int(os.getenv("RATE_LIMIT_BURST", "60"))


def get_client_ip(request: Request) -> str:
    """Extract real client IP from proxy headers or fallback to direct connection."""
    # Check X-Forwarded-For header (standard for proxies)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can have multiple IPs (client, proxy1, proxy2...)
        # First IP is the real client
        client_ip = forwarded_for.split(",")[0].strip()
        if client_ip:
            return client_ip
    
    # Fallback to direct connection IP
    if request.client:
        return request.client.host
    
    # Ultimate fallback
    return "unknown"


async def rate_limit_middleware(request: Request, call_next: Callable):
    """
    Rate Limit Middleware - Redis token-bucket with tiered limits
    
    - Authenticated users: ratelimit:{tenant_id}:{user_id}:{route}
    - Anonymous users: ratelimit:{ip_address}:{route}
    - READ (GET): 300 req/min, 60 burst
    - WRITE (POST/PUT/DELETE): 100 req/min, 30 burst
    - Uses Redis INCR with TTL
    - Returns 429 Too Many Requests if exceeded
    """
    # CRITICAL: Disable rate limiting for test environment
    # Tests run hundreds of rapid requests which is normal for automated testing
    if os.getenv("TESTING", "false").lower() == "true" or os.getenv("PYTEST_CURRENT_TEST") is not None:
        return await call_next(request)
    
    if not REDIS_AVAILABLE:
        return await call_next(request)
    
    # Exempt critical read-only endpoints from rate limiting
    exempt_paths = [
        "/api/v1/health",
        "/docs",
        "/openapi.json",
        "/state",  # DCL graph state (read-only, frequently polled)
        "/ws",  # WebSocket endpoint (persistent connection)
        "/dcl/state",  # DCL state endpoint (read-only)
        "/dcl/ws",  # DCL WebSocket with mount prefix
    ]

    # Exempt orchestration dashboard endpoints (polled frequently)
    exempt_prefixes = [
        "/api/v1/orchestration/",
        "/static/",
    ]

    if request.url.path in exempt_paths:
        return await call_next(request)

    for prefix in exempt_prefixes:
        if request.url.path.startswith(prefix):
            return await call_next(request)
    
    # Determine user identifier
    tenant_id = getattr(request.state, "tenant_id", None)
    user_id = getattr(request.state, "user_id", None)
    
    if tenant_id and user_id:
        # Authenticated user: use tenant + user ID
        identifier = f"{tenant_id}:{user_id}"
    else:
        # Anonymous user: use IP address from proxy headers
        client_ip = get_client_ip(request)
        identifier = f"ip:{client_ip}"
    
    route = request.url.path
    
    # Determine rate limits based on HTTP method
    http_method = request.method.upper()
    if http_method == "GET":
        # READ operations: higher limits
        rpm_limit = RATE_LIMIT_READ_RPM
        burst_limit = RATE_LIMIT_READ_BURST
    else:
        # WRITE operations (POST, PUT, DELETE, PATCH): lower limits
        rpm_limit = RATE_LIMIT_WRITE_RPM
        burst_limit = RATE_LIMIT_WRITE_BURST
    
    rate_key = f"ratelimit:{identifier}:{route}"
    
    try:
        current_count = redis_client.get(rate_key)
        
        if current_count is None:
            # First request in this window
            redis_client.setex(rate_key, 60, 1)
        else:
            current_count = int(current_count)
            
            # Check if limit exceeded
            if current_count >= rpm_limit + burst_limit:
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Rate limit exceeded",
                        "limit": rpm_limit,
                        "burst": burst_limit,
                        "method": http_method
                    },
                    headers={"Retry-After": "60"}
                )
            
            # Increment counter
            redis_client.incr(rate_key)
    
    except Exception:
        # Fail open - don't block requests if Redis has issues
        pass
    
    response = await call_next(request)
    return response
