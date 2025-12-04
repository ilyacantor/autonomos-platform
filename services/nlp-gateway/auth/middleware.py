import os
import jwt
from fastapi import Request, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from typing import Callable, Optional, Tuple
from ..schemas.common import Environment

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", os.getenv("SECRET_KEY", ""))
JWT_ALGORITHM = "HS256"


async def auth_middleware(request: Request, call_next: Callable):
    """
    JWT Auth Middleware for NLP Gateway
    - Verify HS256 JWT from Authorization header
    - Extract tenant_id, env, agent_id, user_id from claims
    - Set request.state.tenant_id, request.state.env, request.state.user_id
    - Return 401 if invalid
    
    Token claims expected:
        - tenant_id: Tenant identifier (required)
        - env: Environment (dev|stage|prod, defaults to prod if missing)
        - agent_id: Agent identifier (optional)
        - sub: User ID (optional)
    """
    public_paths = [
        "/docs",
        "/redoc",
        "/openapi.json",
        "/health",
    ]
    
    if request.url.path in public_paths or request.url.path.startswith("/static/"):
        return await call_next(request)
    
    auth_header = request.headers.get("Authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Missing or invalid Authorization header"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = auth_header.replace("Bearer ", "")
    
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        
        tenant_id = payload.get("tenant_id")
        if not tenant_id:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid token: missing tenant_id"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        env_str = payload.get("env", "prod")
        try:
            env = Environment(env_str)
        except ValueError:
            env = Environment.PROD
        
        request.state.tenant_id = tenant_id
        request.state.env = env
        request.state.agent_id = payload.get("agent_id")
        request.state.user_id = payload.get("sub")
        request.state.scopes = payload.get("scopes", [])
        
    except jwt.ExpiredSignatureError:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Token has expired"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": f"Invalid token: {str(e)}"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    response = await call_next(request)
    return response


def get_current_tenant(request: Request) -> Tuple[str, Environment]:
    """
    Dependency to extract tenant_id and env from request state.
    
    Use this as a dependency in route handlers:
        @router.get("/endpoint")
        async def endpoint(tenant_info: Tuple[str, Environment] = Depends(get_current_tenant)):
            tenant_id, env = tenant_info
            ...
    
    Returns:
        Tuple of (tenant_id, env)
        
    Raises:
        HTTPException: If tenant_id or env not found in request state
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    env = getattr(request.state, "env", None)
    
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: tenant_id not found"
        )
    
    if not env:
        env = Environment.PROD
    
    return tenant_id, env
