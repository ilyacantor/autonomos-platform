import os
import jwt
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Callable

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", os.getenv("SECRET_KEY", ""))
JWT_ALGORITHM = "HS256"


async def tenant_auth_middleware(request: Request, call_next: Callable):
    """
    TenantAuth Middleware
    - Verify HS256 JWT from Authorization header
    - Extract tenant_id, agent_id, scopes from claims
    - Set request.state.tenant_id, request.state.agent_id
    - Return 401 if invalid
    """
    # Bypass auth for public endpoints
    public_paths = [
        "/docs",
        "/redoc",
        "/openapi.json",
        "/health",
        "/token",                    # OAuth2 login endpoint - CRITICAL
        "/users/register",           # Legacy registration endpoint
        "/api/v1/auth/login",        # JSON-based login endpoint
        "/api/v1/auth/register",     # JSON-based registration endpoint
        "/api/v1/health",            # Platform health endpoint (dev)
        "/api/v1/dcl/views/opportunities",  # DCL views (dev)
        "/api/v1/dcl/views/accounts",       # DCL views (dev)
        "/api/v1/intents/revops/execute",   # Intent endpoints (dev)
        "/api/v1/intents/finops/execute",   # Intent endpoints (dev)
        "/dcl/state",                # DCL state endpoint (for frontend graph)
        "/dcl/connect",              # DCL connect endpoint (for frontend graph)
        "/dcl/ws",                   # DCL WebSocket (for real-time updates)
        "/dcl/ontology_schema",      # DCL ontology schema (for Ontology tab)
        "/api/v1/aam/",              # All AAM endpoints (for Monitor dashboard)
        "/api/v1/debug/",            # Debug endpoints (dev-only, feature-flagged)
        "/api/v1/mesh/test/",        # Mesh test endpoints (dev-only, for drift demos)
        "/architecture.html",        # Architecture visualization page
        "/aam-monitor",              # AAM Monitor frontend page (demo access)
    ]
    
    # Also bypass static frontend paths
    static_prefixes = ["/assets/", "/static/", "/favicon", "/robot"]
    
    # Check exact match for root path
    if request.url.path == "/":
        return await call_next(request)
    
    # Check if path starts with any public path or static prefix
    if any(request.url.path.startswith(path) for path in public_paths + static_prefixes):
        return await call_next(request)
    
    # Special handling for SSE endpoint - authenticate via query token
    # EventSource cannot send Authorization headers, so we use query params
    if request.url.path == "/api/v1/events/stream":
        token = request.query_params.get("token")
        
        if not token:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing token query parameter"}
            )
        
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            
            request.state.tenant_id = payload.get("tenant_id")
            request.state.agent_id = payload.get("agent_id")
            request.state.scopes = payload.get("scopes", [])
            request.state.user_id = payload.get("sub")
            
            if not request.state.tenant_id:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Invalid token: missing tenant_id"}
                )
            
            # Token validated, allow request to pass through
            response = await call_next(request)
            return response
            
        except jwt.ExpiredSignatureError:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Token has expired"}
            )
        except jwt.InvalidTokenError:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid token"}
            )
    
    auth_header = request.headers.get("Authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Missing or invalid Authorization header"}
        )
    
    token = auth_header.replace("Bearer ", "")
    
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        
        request.state.tenant_id = payload.get("tenant_id")
        request.state.agent_id = payload.get("agent_id")
        request.state.scopes = payload.get("scopes", [])
        request.state.user_id = payload.get("sub")
        
        if not request.state.tenant_id:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid token: missing tenant_id"}
            )
        
    except jwt.ExpiredSignatureError:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Token has expired"}
        )
    except jwt.InvalidTokenError:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Invalid token"}
        )
    
    response = await call_next(request)
    return response
