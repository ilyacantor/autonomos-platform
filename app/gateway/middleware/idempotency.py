import os
import json
import asyncio
from datetime import datetime, timedelta
from fastapi import Request
from fastapi.responses import JSONResponse
from typing import Callable
from redis import Redis

IDEMPOTENCY_CACHE_MINUTES = int(os.getenv("IDEMPOTENCY_CACHE_MINUTES", "10"))

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


async def idempotency_middleware(request: Request, call_next: Callable):
    """
    Idempotency-Key Middleware
    - Check "Idempotency-Key" header on POST
    - If exists, check Redis/DB for cached response
    - Return cached response if found (within 10min)
    - Store response after execution
    - NON-BLOCKING: Uses thread pool for sync Redis calls
    """
    if not REDIS_AVAILABLE or request.method != "POST":
        return await call_next(request)
    
    idempotency_key = request.headers.get("Idempotency-Key")
    
    if not idempotency_key:
        return await call_next(request)
    
    tenant_id = getattr(request.state, "tenant_id", "anonymous")
    cache_key = f"idempotency:{tenant_id}:{idempotency_key}"
    
    try:
        # Non-blocking: Run sync Redis GET in thread pool
        loop = asyncio.get_event_loop()
        cached_response = await loop.run_in_executor(None, redis_client.get, cache_key)
        
        if cached_response:
            cached_data = json.loads(cached_response)
            return JSONResponse(
                status_code=cached_data.get("status_code", 200),
                content=cached_data.get("body", {}),
                headers={"X-Idempotent-Replay": "true"}
            )
    
    except Exception:
        pass
    
    response = await call_next(request)
    
    try:
        if response.status_code < 400:
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk
            
            cached_data = {
                "status_code": response.status_code,
                "body": json.loads(response_body.decode()) if response_body else {}
            }
            
            # Non-blocking: Fire-and-forget Redis SET in thread pool
            loop = asyncio.get_event_loop()
            loop.run_in_executor(
                None,
                redis_client.setex,
                cache_key,
                IDEMPOTENCY_CACHE_MINUTES * 60,
                json.dumps(cached_data)
            )
            
            from fastapi.responses import Response
            return Response(
                content=response_body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type
            )
    
    except Exception:
        pass
    
    return response
