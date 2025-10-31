import uuid
from fastapi import Request
from typing import Callable


async def tracing_middleware(request: Request, call_next: Callable):
    """
    X-Trace-Id Propagation Middleware
    - Generate UUID if no X-Trace-Id header
    - Add to request.state.trace_id
    - Include in response headers
    - Propagate to downstream services
    """
    trace_id = request.headers.get("X-Trace-Id")
    
    if not trace_id:
        trace_id = str(uuid.uuid4())
    
    request.state.trace_id = trace_id
    
    response = await call_next(request)
    
    response.headers["X-Trace-Id"] = trace_id
    
    return response
