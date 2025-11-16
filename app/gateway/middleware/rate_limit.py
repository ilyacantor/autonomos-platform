import os
import time
from fastapi import Request
from fastapi.responses import JSONResponse
from typing import Callable
from redis import Redis

RATE_LIMIT_RPM = int(os.getenv("RATE_LIMIT_RPM", "60"))
RATE_LIMIT_BURST = int(os.getenv("RATE_LIMIT_BURST", "10"))

REDIS_URL = os.getenv("REDIS_URL")
try:
    if REDIS_URL:
        redis_client = Redis.from_url(REDIS_URL, decode_responses=True)
    else:
        redis_client = Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            db=int(os.getenv("REDIS_DB", "0")),
            decode_responses=True
        )
    redis_client.ping()
    REDIS_AVAILABLE = True
except Exception:
    redis_client = None
    REDIS_AVAILABLE = False


async def rate_limit_middleware(request: Request, call_next: Callable):
    """
    Rate Limit Middleware - Redis token-bucket
    - Key: f"ratelimit:{tenant_id}:{agent_id}:{route}"
    - 60 requests per minute, burst 10
    - Use Redis INCR with TTL
    - Return 429 Too Many Requests if exceeded
    """
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
    if (request.url.path in exempt_paths or 
        request.url.path.startswith("/static/") or 
        request.url.path.startswith("/nlp/")):
        return await call_next(request)
    
    tenant_id = getattr(request.state, "tenant_id", "anonymous")
    agent_id = getattr(request.state, "agent_id", "unknown")
    route = request.url.path
    
    rate_key = f"ratelimit:{tenant_id}:{agent_id}:{route}"
    window_key = f"{rate_key}:window"
    
    try:
        current_count = redis_client.get(rate_key)
        
        if current_count is None:
            redis_client.setex(rate_key, 60, 1)
            redis_client.setex(window_key, 60, int(time.time()))
        else:
            current_count = int(current_count)
            
            if current_count >= RATE_LIMIT_RPM + RATE_LIMIT_BURST:
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Rate limit exceeded",
                        "limit": RATE_LIMIT_RPM,
                        "burst": RATE_LIMIT_BURST
                    },
                    headers={"Retry-After": "60"}
                )
            
            redis_client.incr(rate_key)
    
    except Exception:
        pass
    
    response = await call_next(request)
    return response
