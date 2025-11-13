from fastapi import APIRouter, Request, Depends, HTTPException

from ..schemas.revops import RevOpsIncidentRequest, RevOpsIncidentResponse, IncidentStatus, TimelineEvent, IncidentImpact
from ..auth.middleware import get_current_tenant
from ..utils import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/revops", tags=["RevOps"])


@router.post("/incident", response_model=RevOpsIncidentResponse)
async def get_incident_details(
    request: Request,
    req: RevOpsIncidentRequest
):
    """
    Get revenue operations incident details.
    
    Demo implementation returns synthetic incident data.
    Production: Query incident management system or database.
    """
    trace_id = request.state.trace_id
    logger.info(f"RevOps incident request: incident_id={req.incident_id}")
    
    demo_incidents = {
        "inc-001": {
            "service": "Salesforce Sync",
            "status": IncidentStatus.RESOLVED,
            "diagnosis": "OAuth token expired due to rotation policy",
            "resolution": "Refreshed OAuth credentials and updated token rotation schedule",
            "impact": IncidentImpact(records=1250, pipeline_value=875000.00),
            "timeline": [
                TimelineEvent(ts="2024-11-07T10:15:00Z", event="Incident detected: sync failures"),
                TimelineEvent(ts="2024-11-07T10:20:00Z", event="Root cause identified: expired token"),
                TimelineEvent(ts="2024-11-07T10:35:00Z", event="Token refreshed, sync resumed"),
                TimelineEvent(ts="2024-11-07T11:00:00Z", event="Incident resolved"),
            ]
        },
        "inc-002": {
            "service": "HubSpot Connector",
            "status": IncidentStatus.OPEN,
            "diagnosis": "API rate limit exceeded during bulk import",
            "resolution": "Implementing batching strategy with exponential backoff",
            "impact": IncidentImpact(records=450, pipeline_value=320000.00),
            "timeline": [
                TimelineEvent(ts="2024-11-08T08:00:00Z", event="Incident detected: import stalled"),
                TimelineEvent(ts="2024-11-08T08:15:00Z", event="Rate limit identified as cause"),
                TimelineEvent(ts="2024-11-08T08:30:00Z", event="Mitigation in progress"),
            ]
        }
    }
    
    incident = demo_incidents.get(req.incident_id)
    if not incident:
        raise HTTPException(
            status_code=404,
            detail=f"Incident {req.incident_id} not found"
        )
    
    return RevOpsIncidentResponse(
        trace_id=trace_id,
        incident_id=req.incident_id,
        **incident
    )
