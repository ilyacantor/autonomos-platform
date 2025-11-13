from fastapi import APIRouter, Request, Depends

from ..schemas.aam import AAMConnectorsRequest, AAMConnectorsResponse, Connector, ConnectorStatus, ConnectorType
from ..auth.middleware import get_current_tenant
from ..utils import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/aam", tags=["AAM"])


@router.post("/connectors", response_model=AAMConnectorsResponse)
async def list_connectors(
    request: Request,
    req: AAMConnectorsRequest
):
    """
    List AAM (Adaptive API Mesh) connectors and their status.
    
    Demo implementation returns synthetic connector data.
    Production: Query AAM service registry or database.
    """
    trace_id = request.state.trace_id
    logger.info(f"AAM connectors request: status={req.status}")
    
    demo_connectors = [
        Connector(
            name="Salesforce",
            type=ConnectorType.SAAS,
            status="Healthy",
            last_sync="2024-11-08T00:00:00Z"
        ),
        Connector(
            name="HubSpot",
            type=ConnectorType.SAAS,
            status="Healthy",
            last_sync="2024-11-07T23:45:00Z"
        ),
        Connector(
            name="PostgreSQL-Main",
            type=ConnectorType.DB,
            status="Healthy",
            last_sync="2024-11-08T00:05:00Z"
        ),
        Connector(
            name="MongoDB-Analytics",
            type=ConnectorType.DB,
            status="Drifted",
            last_sync="2024-11-07T18:30:00Z"
        ),
        Connector(
            name="S3-DataLake",
            type=ConnectorType.FILE,
            status="Healthy",
            last_sync="2024-11-08T00:00:00Z"
        ),
    ]
    
    if req.status != ConnectorStatus.ALL:
        demo_connectors = [
            c for c in demo_connectors if c.status == req.status.value
        ]
    
    status_counts = {
        "Healthy": sum(1 for c in demo_connectors if c.status == "Healthy"),
        "Drifted": sum(1 for c in demo_connectors if c.status == "Drifted"),
        "Error": sum(1 for c in demo_connectors if c.status == "Error"),
    }
    
    return AAMConnectorsResponse(
        trace_id=trace_id,
        status_counts=status_counts,
        connectors=demo_connectors
    )
