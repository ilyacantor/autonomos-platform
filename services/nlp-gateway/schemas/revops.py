from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
from .common import Environment, BaseResponse


class IncidentStatus(str, Enum):
    OPEN = "Open"
    RESOLVED = "Resolved"
    MITIGATED = "Mitigated"


class TimelineEvent(BaseModel):
    ts: str = Field(..., description="ISO-8601 timestamp")
    event: str = Field(..., description="Event description")


class IncidentImpact(BaseModel):
    records: int = Field(..., description="Number of records affected")
    pipeline_value: float = Field(..., description="Pipeline value impacted")


class RevOpsIncidentRequest(BaseModel):
    tenant_id: str = Field(..., description="Tenant identifier")
    env: Environment = Field(Environment.PROD, description="Environment")
    incident_id: str = Field(..., description="Incident identifier")


class RevOpsIncidentResponse(BaseResponse):
    incident_id: str = Field(..., description="Incident identifier")
    service: str = Field(..., description="Service name")
    status: IncidentStatus = Field(..., description="Incident status")
    diagnosis: str = Field(..., description="Root cause diagnosis")
    resolution: str = Field(..., description="Resolution description")
    impact: IncidentImpact = Field(..., description="Impact metrics")
    timeline: List[TimelineEvent] = Field(default_factory=list, description="Event timeline")
