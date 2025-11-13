from pydantic import BaseModel, Field
from typing import List
from enum import Enum
from .common import Environment, BaseResponse


class ConnectorStatus(str, Enum):
    ALL = "All"
    HEALTHY = "Healthy"
    DRIFTED = "Drifted"
    ERROR = "Error"


class ConnectorType(str, Enum):
    SAAS = "SaaS"
    DB = "DB"
    FILE = "File"


class Connector(BaseModel):
    name: str = Field(..., description="Connector name")
    type: ConnectorType = Field(..., description="Connector type")
    status: str = Field(..., description="Connector status")
    last_sync: str = Field(..., description="ISO-8601 timestamp of last sync")


class AAMConnectorsRequest(BaseModel):
    tenant_id: str = Field(..., description="Tenant identifier")
    env: Environment = Field(Environment.PROD, description="Environment")
    status: ConnectorStatus = Field(ConnectorStatus.ALL, description="Filter by status")


class AAMConnectorsResponse(BaseResponse):
    status_counts: dict = Field(..., description="Count by status {Healthy, Drifted, Error}")
    connectors: List[Connector] = Field(default_factory=list, description="List of connectors")
