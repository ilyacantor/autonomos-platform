"""Main API Farm application - Synthetic API simulator."""
import os
import json
import yaml
import asyncio
import random
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import JSONResponse
import uvicorn

from models import (
    ServiceConfig, TokenInfo, APICallMetrics,
    AuthType, ErrorProfile, NetworkProfile
)
from auth import TokenManager, AuthValidator, security
from rate_limiter import AdaptiveRateLimiter
from chaos import ChaosEngine, DriftSimulator


# Global instances
token_manager = TokenManager()
chaos_engine = ChaosEngine()
drift_simulator = DriftSimulator()
rate_limiter = AdaptiveRateLimiter(chaos_engine)
auth_validator = AuthValidator(token_manager)

# Service configurations
service_configs: Dict[str, ServiceConfig] = {}

# Metrics storage
api_metrics: List[APICallMetrics] = []


def load_service_configs():
    """Load all service configurations from YAML files."""
    config_dir = Path(__file__).parent / "configs"
    config_dir.mkdir(exist_ok=True)
    
    for config_file in config_dir.glob("*.yaml"):
        with open(config_file, "r") as f:
            config_data = yaml.safe_load(f)
            service = ServiceConfig(**config_data)
            service_configs[service.id] = service
            print(f"Loaded service config: {service.id}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    # Startup
    load_service_configs()
    print(f"API Farm started with {len(service_configs)} services")
    
    yield
    
    # Shutdown
    print("API Farm shutting down")


app = FastAPI(
    title="AAM Gauntlet - API Farm",
    description="Synthetic API simulator for AAM stress testing",
    version="1.0.0",
    lifespan=lifespan
)


def generate_mock_data(schema_fields: List[Dict]) -> Dict[str, Any]:
    """Generate mock data based on schema fields."""
    data = {}
    for field in schema_fields:
        field_name = field.get("name", field["name"])
        field_type = field.get("type", field["type"])
        
        if field_type == "string":
            data[field_name] = f"mock_{field_name}_{random.randint(1000, 9999)}"
        elif field_type == "integer":
            data[field_name] = random.randint(1, 1000)
        elif field_type == "number":
            data[field_name] = round(random.uniform(0, 1000), 2)
        elif field_type == "boolean":
            data[field_name] = random.choice([True, False])
        elif field_type == "array":
            data[field_name] = []
        elif field_type == "object":
            data[field_name] = {}
    
    return data


async def handle_api_request(
    service_id: str,
    endpoint_path: str,
    method: str,
    tenant_id: Optional[str] = None,
    auth_creds: Optional[HTTPAuthorizationCredentials] = None
) -> Response:
    """Generic handler for all synthetic API requests."""
    
    # Get service config
    if service_id not in service_configs:
        raise HTTPException(status_code=404, detail="Service not found")
    
    service = service_configs[service_id]
    
    # Validate authentication
    try:
        auth_info = auth_validator.validate_request(
            service.auth.type,
            auth_creds,
            service_id
        )
        tenant_id = auth_info.get("tenant_id", tenant_id)
    except HTTPException as e:
        # Log auth failure
        metric = APICallMetrics(
            service_id=service_id,
            tenant_id=tenant_id,
            endpoint=endpoint_path,
            method=method,
            status_code=e.status_code,
            error_type="auth_failed",
            timestamp=datetime.utcnow(),
            latency_ms=0.1,
            retries=0
        )
        api_metrics.append(metric)
        raise e
    
    # Check rate limit
    rate_config = service.rate_limit
    if tenant_id:
        # Check for tenant override
        for tenant in service.tenants:
            if tenant.id == tenant_id and tenant.rate_limit_override:
                rate_config = tenant.rate_limit_override
                break
    
    allowed, retry_after = await rate_limiter.check_rate_limit(
        service_id,
        tenant_id,
        rate_config.max_rps,
        rate_config.burst
    )
    
    if not allowed:
        # Rate limit exceeded
        metric = APICallMetrics(
            service_id=service_id,
            tenant_id=tenant_id,
            endpoint=endpoint_path,
            method=method,
            status_code=429,
            error_type="rate_limit",
            timestamp=datetime.utcnow(),
            latency_ms=0.1,
            retries=0
        )
        api_metrics.append(metric)
        
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded", "retry_after": retry_after},
            headers={"Retry-After": str(int(retry_after))}
        )
    
    # Inject network delay
    await chaos_engine.inject_network_delay(service.network_profile)
    
    # Check if we should inject an error
    if chaos_engine.should_inject_error(service.error_profile):
        error_response = chaos_engine.get_error_response(service.error_profile)
        
        metric = APICallMetrics(
            service_id=service_id,
            tenant_id=tenant_id,
            endpoint=endpoint_path,
            method=method,
            status_code=error_response["status_code"],
            error_type=error_response["error"],
            timestamp=datetime.utcnow(),
            latency_ms=random.uniform(10, 100),
            retries=0
        )
        api_metrics.append(metric)
        
        return JSONResponse(
            status_code=error_response["status_code"],
            content=error_response
        )
    
    # Generate successful response
    response_data = generate_mock_data(service.schema.fields)
    
    # Apply drift if applicable
    drift_simulator.record_call(service_id)
    for drift_action in service.drift_schedule:
        if drift_simulator.should_drift(service_id, drift_action.dict()):
            response_data = drift_simulator.apply_drift(
                response_data,
                drift_action.dict()
            )
    
    # Record successful metric
    metric = APICallMetrics(
        service_id=service_id,
        tenant_id=tenant_id,
        endpoint=endpoint_path,
        method=method,
        status_code=200,
        error_type=None,
        timestamp=datetime.utcnow(),
        latency_ms=random.uniform(10, 50),
        retries=0
    )
    api_metrics.append(metric)
    
    return JSONResponse(status_code=200, content=response_data)


# OAuth2 Token Endpoint
@app.post("/oauth2/token")
async def get_oauth_token(
    grant_type: str,
    client_id: str,
    client_secret: str,
    scope: Optional[str] = None
):
    """OAuth2 token endpoint for client credentials flow."""
    if grant_type != "client_credentials":
        raise HTTPException(
            status_code=400,
            detail="Only client_credentials grant type is supported"
        )
    
    # Parse client_id to get service and tenant
    # Format: service_id:tenant_id
    parts = client_id.split(":")
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="Invalid client_id format")
    
    service_id, tenant_id = parts
    
    if service_id not in service_configs:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    service = service_configs[service_id]
    
    # Create token
    token_info = token_manager.create_access_token(
        service_id=service_id,
        tenant_id=tenant_id,
        expires_delta=timedelta(seconds=service.auth.token_ttl_seconds)
    )
    
    return {
        "access_token": token_info.access_token,
        "token_type": token_info.token_type,
        "expires_in": token_info.expires_in,
        "refresh_token": token_info.refresh_token
    }


# Admin Endpoints
@app.get("/admin/status")
async def get_admin_status():
    """Get current system status and metrics."""
    # Calculate metrics summary
    metrics_summary = {
        "total_requests": len(api_metrics),
        "by_service": {},
        "by_status": {},
        "error_types": {},
        "recent_errors": []
    }
    
    for metric in api_metrics:
        # By service
        if metric.service_id not in metrics_summary["by_service"]:
            metrics_summary["by_service"][metric.service_id] = {
                "total": 0,
                "success": 0,
                "errors": 0,
                "avg_latency": 0
            }
        
        service_stats = metrics_summary["by_service"][metric.service_id]
        service_stats["total"] += 1
        
        if 200 <= metric.status_code < 300:
            service_stats["success"] += 1
        else:
            service_stats["errors"] += 1
        
        # By status code
        status_key = str(metric.status_code)
        metrics_summary["by_status"][status_key] = \
            metrics_summary["by_status"].get(status_key, 0) + 1
        
        # Error types
        if metric.error_type:
            metrics_summary["error_types"][metric.error_type] = \
                metrics_summary["error_types"].get(metric.error_type, 0) + 1
            
            # Recent errors (last 10)
            if len(metrics_summary["recent_errors"]) < 10:
                metrics_summary["recent_errors"].append({
                    "service": metric.service_id,
                    "endpoint": metric.endpoint,
                    "status": metric.status_code,
                    "error": metric.error_type,
                    "timestamp": metric.timestamp.isoformat()
                })
    
    return {
        "status": "running",
        "chaos_level": chaos_engine.chaos_level,
        "services": list(service_configs.keys()),
        "metrics": metrics_summary,
        "token_metrics": token_manager.get_token_metrics(),
        "drift_states": drift_simulator.call_counts
    }


@app.post("/admin/chaos")
async def set_chaos_level(level: str):
    """Set the global chaos level."""
    if level not in ["mild", "storm", "hell"]:
        raise HTTPException(status_code=400, detail="Invalid chaos level")
    
    chaos_engine.set_chaos_level(level)
    return {"message": f"Chaos level set to {level}"}


@app.post("/admin/reset")
async def reset_metrics():
    """Reset all metrics and state."""
    global api_metrics
    api_metrics = []
    drift_simulator.call_counts = {}
    drift_simulator.drift_states = {}
    
    return {"message": "Metrics reset successfully"}


# Dynamic route registration for each service
@app.api_route("/{service_base_path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def dynamic_service_handler(
    request: Request,
    service_base_path: str,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    """Handle all dynamic service endpoints."""
    # Extract service_id from path
    # Format: /api/{service_id}/...
    path_parts = service_base_path.split("/")
    if len(path_parts) < 2 or path_parts[0] != "api":
        raise HTTPException(status_code=404, detail="Invalid path")
    
    service_id = path_parts[1]
    endpoint_path = "/" + "/".join(path_parts[2:]) if len(path_parts) > 2 else "/"
    
    # Extract tenant_id from header if present
    tenant_id = request.headers.get("X-Tenant-ID")
    
    response = await handle_api_request(
        service_id=service_id,
        endpoint_path=endpoint_path,
        method=request.method,
        tenant_id=tenant_id,
        auth_creds=credentials
    )
    
    return response


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)