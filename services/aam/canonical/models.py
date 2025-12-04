from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal


class CanonicalMeta(BaseModel):
    version: str = "1.0.0"
    tenant: str
    trace_id: str
    emitted_at: datetime


class CanonicalSource(BaseModel):
    system: str
    connection_id: str
    schema_version: str


class CanonicalAccount(BaseModel):
    account_id: str
    external_ids: List[str] = []
    name: str
    type: Optional[str] = None
    industry: Optional[str] = None
    owner_id: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    extras: Dict[str, Any] = {}


class CanonicalOpportunity(BaseModel):
    opportunity_id: str
    account_id: str
    name: str
    stage: str
    amount: Optional[Decimal] = None
    currency: str = "USD"
    close_date: Optional[date] = None
    owner_id: Optional[str] = None
    probability: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    extras: Dict[str, Any] = {}


class CanonicalEnvelope(BaseModel):
    meta: CanonicalMeta
    source: CanonicalSource
    entity: str
    op: str
    data: Dict[str, Any]
