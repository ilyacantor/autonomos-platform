from pydantic import BaseModel, Field
from typing import List
from enum import Enum
from .common import Environment, BaseResponse


class ServiceStatus(str, Enum):
    OPERATIONAL = "Operational"
    DEGRADED = "Degraded"
    DOWN = "Down"


class Dependency(BaseModel):
    name: str = Field(..., description="Dependency name")
    status: ServiceStatus = Field(..., description="Dependency status")


class AODDependenciesRequest(BaseModel):
    tenant_id: str = Field(..., description="Tenant identifier")
    env: Environment = Field(Environment.PROD, description="Environment")
    service: str = Field(..., description="Service name")


class AODDependenciesResponse(BaseResponse):
    service: str = Field(..., description="Service name")
    dependencies: List[Dependency] = Field(default_factory=list, description="Service dependencies")
    last_observed: str = Field(..., description="ISO-8601 timestamp of last observation")
