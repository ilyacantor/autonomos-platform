from fastapi import APIRouter, Request, Depends

from ..schemas.aod import AODDependenciesRequest, AODDependenciesResponse, Dependency, ServiceStatus
from ..auth.middleware import get_current_tenant
from ..utils import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/aod", tags=["AOD"])


@router.post("/dependencies", response_model=AODDependenciesResponse)
async def get_service_dependencies(
    request: Request,
    req: AODDependenciesRequest
):
    """
    Get service dependency map and health status.
    
    Demo implementation returns synthetic dependency data.
    Production: Query service mesh or observability platform.
    """
    trace_id = request.state.trace_id
    logger.info(f"AOD dependencies request: service={req.service}")
    
    demo_dependencies = {
        "checkout": [
            Dependency(name="payment-gateway", status=ServiceStatus.OPERATIONAL),
            Dependency(name="inventory-service", status=ServiceStatus.OPERATIONAL),
            Dependency(name="user-service", status=ServiceStatus.OPERATIONAL),
            Dependency(name="postgres-primary", status=ServiceStatus.OPERATIONAL),
            Dependency(name="redis-cache", status=ServiceStatus.DEGRADED),
        ],
        "api-gateway": [
            Dependency(name="auth-service", status=ServiceStatus.OPERATIONAL),
            Dependency(name="rate-limiter", status=ServiceStatus.OPERATIONAL),
            Dependency(name="analytics-collector", status=ServiceStatus.OPERATIONAL),
        ],
        "data-pipeline": [
            Dependency(name="kafka-cluster", status=ServiceStatus.OPERATIONAL),
            Dependency(name="elasticsearch", status=ServiceStatus.DEGRADED),
            Dependency(name="s3-storage", status=ServiceStatus.OPERATIONAL),
        ]
    }
    
    dependencies = demo_dependencies.get(req.service, [])
    
    return AODDependenciesResponse(
        trace_id=trace_id,
        service=req.service,
        dependencies=dependencies,
        last_observed="2024-11-08T00:00:00Z"
    )
