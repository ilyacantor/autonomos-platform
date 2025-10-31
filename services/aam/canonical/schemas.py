"""
Canonical v1 Schemas for AAM
Strict typing for account and opportunity entities
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, validator


class CanonicalMeta(BaseModel):
    """Metadata envelope for canonical events"""
    version: str = "1.0.0"
    tenant: str = Field(..., description="Tenant identifier")
    trace_id: str = Field(..., description="UUID trace ID")
    emitted_at: datetime = Field(default_factory=datetime.utcnow, description="ISO8601 timestamp")


class CanonicalSource(BaseModel):
    """Source system metadata"""
    system: str = Field(..., description="Source system name (filesource, postgres, etc.)")
    connection_id: str = Field(..., description="Connection identifier")
    schema_version: str = "v1"


class CanonicalAccount(BaseModel):
    """Canonical account entity schema"""
    account_id: str = Field(..., description="Primary account identifier")
    external_ids: List[str] = Field(default_factory=list, description="External system IDs")
    name: str = Field(..., description="Account name")
    type: Optional[str] = Field(None, description="Account type (Enterprise, SMB, etc.)")
    industry: Optional[str] = Field(None, description="Industry classification")
    owner_id: Optional[str] = Field(None, description="Account owner identifier")
    status: Optional[str] = Field(None, description="Account status (active, prospect, etc.)")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    extras: Dict[str, Any] = Field(default_factory=dict, description="Additional unmapped fields")


class CanonicalOpportunity(BaseModel):
    """Canonical opportunity entity schema"""
    opportunity_id: str = Field(..., description="Primary opportunity identifier")
    account_id: Optional[str] = Field(None, description="Associated account ID")
    name: str = Field(..., description="Opportunity name")
    stage: Optional[str] = Field(None, description="Sales stage")
    amount: Optional[Decimal] = Field(None, description="Deal amount")
    currency: Optional[str] = Field("USD", description="Currency code")
    close_date: Optional[datetime] = Field(None, description="Expected close date")
    owner_id: Optional[str] = Field(None, description="Opportunity owner identifier")
    probability: Optional[float] = Field(None, ge=0, le=100, description="Win probability (0-100)")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    extras: Dict[str, Any] = Field(default_factory=dict, description="Additional unmapped fields")
    
    @validator('probability')
    def validate_probability(cls, v):
        if v is not None and not (0 <= v <= 100):
            return None
        return v


class CanonicalContact(BaseModel):
    """Canonical contact entity schema"""
    contact_id: str = Field(..., description="Primary contact identifier")
    account_id: Optional[str] = Field(None, description="Associated account/organization ID")
    first_name: Optional[str] = Field(None, description="Contact first name")
    last_name: Optional[str] = Field(None, description="Contact last name")
    name: Optional[str] = Field(None, description="Full name (if first/last not separate)")
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    title: Optional[str] = Field(None, description="Job title")
    department: Optional[str] = Field(None, description="Department")
    role: Optional[str] = Field(None, description="Role or position")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    extras: Dict[str, Any] = Field(default_factory=dict, description="Additional unmapped fields")


class CanonicalEvent(BaseModel):
    """Complete canonical event envelope"""
    meta: CanonicalMeta
    source: CanonicalSource
    entity: Literal["account", "opportunity", "contact"] = Field(..., description="Entity type")
    op: Literal["upsert", "delete"] = Field("upsert", description="Operation type")
    data: Dict[str, Any] = Field(..., description="Canonical entity data")
    unknown_fields: List[str] = Field(default_factory=list, description="Fields that couldn't be mapped")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return self.dict(exclude_none=False)
