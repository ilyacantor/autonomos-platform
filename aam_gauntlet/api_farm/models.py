"""Data models for API Farm configuration and runtime."""
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel
from datetime import datetime
from enum import Enum


class AuthType(str, Enum):
    OAUTH2_CLIENT_CREDENTIALS = "oauth2_client_credentials"
    API_KEY = "api_key"
    BASIC_AUTH = "basic_auth"
    NONE = "none"


class ErrorProfile(str, Enum):
    AGGRESSIVE_RATE_LIMIT = "aggressive_rate_limit"
    FLAKY_5XX = "flaky_5xx"
    MOSTLY_OK = "mostly_ok"
    SPIKY_RATE_LIMIT = "spiky_rate_limit"


class NetworkProfile(str, Enum):
    NORMAL = "normal"
    DNS_FLAKINESS = "dns_flakiness"
    TLS_FLAKINESS = "tls_flakiness"
    TIMEOUT_PROBABILITY = "timeout_probability"


class Endpoint(BaseModel):
    method: str
    path: str
    paginated: bool = False
    response_schema: Optional[Dict[str, Any]] = None


class Resource(BaseModel):
    name: str
    endpoints: List[Endpoint]


class RateLimit(BaseModel):
    max_rps: int = 10
    burst: int = 20


class AuthConfig(BaseModel):
    type: AuthType
    token_ttl_seconds: int = 3600
    rotate_token_every_calls: Optional[int] = None


class SchemaField(BaseModel):
    name: str
    type: str
    required: bool = True


class SchemaVersion(BaseModel):
    version: int
    fields: List[SchemaField]


class DriftAction(BaseModel):
    trigger: str  # "calls_count" or "time_elapsed"
    threshold: int
    action: str  # "rename_field", "add_field", "remove_field"
    from_field: Optional[str] = None
    to_field: Optional[str] = None
    new_field: Optional[SchemaField] = None


class TenantConfig(BaseModel):
    id: str
    rate_limit_override: Optional[RateLimit] = None
    auth_override: Optional[Dict[str, Any]] = None


class ServiceConfig(BaseModel):
    id: str
    protocol: str = "rest"
    base_path: str
    resources: List[Resource]
    auth: AuthConfig
    rate_limit: RateLimit
    error_profile: ErrorProfile = ErrorProfile.MOSTLY_OK
    network_profile: NetworkProfile = NetworkProfile.NORMAL
    schema: SchemaVersion
    drift_schedule: List[DriftAction] = []
    tenants: List[TenantConfig] = []


class TokenInfo(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    expires_at: datetime
    refresh_token: Optional[str] = None


class APICallMetrics(BaseModel):
    service_id: str
    tenant_id: Optional[str] = None
    endpoint: str
    method: str
    status_code: int
    error_type: Optional[str] = None
    timestamp: datetime
    latency_ms: float
    retries: int = 0