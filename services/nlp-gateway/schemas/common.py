from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class Environment(str, Enum):
    DEV = "dev"
    STAGE = "stage"
    PROD = "prod"


class ObjectRef(BaseModel):
    """Cross-environment object reference: obj://aos/{kind}/{name}?tenant={tenant_id}&env={env}"""
    kind: str = Field(..., description="Object kind (service, connector, etc.)")
    name: str = Field(..., description="Object name")
    tenant_id: str = Field(..., description="Tenant ID")
    env: Environment = Field(Environment.PROD, description="Environment")

    def to_uri(self) -> str:
        return f"obj://aos/{self.kind}/{self.name}?tenant={self.tenant_id}&env={self.env.value}"

    @classmethod
    def from_uri(cls, uri: str) -> "ObjectRef":
        """Parse object reference URI"""
        import re
        pattern = r"obj://aos/([^/]+)/([^?]+)\?tenant=([^&]+)&env=(\w+)"
        match = re.match(pattern, uri)
        if not match:
            raise ValueError(f"Invalid ObjectRef URI: {uri}")
        kind, name, tenant_id, env = match.groups()
        return cls(kind=kind, name=name, tenant_id=tenant_id, env=Environment(env))


class BaseResponse(BaseModel):
    """Base response with trace_id for all endpoints"""
    trace_id: str = Field(..., description="Unique trace ID for observability")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
