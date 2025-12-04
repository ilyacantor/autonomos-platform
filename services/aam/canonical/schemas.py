"""
Canonical v1 Schemas for AAM
Strict typing for account and opportunity entities
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, Literal, Union
from pydantic import BaseModel, Field, validator, model_validator


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


class CanonicalAWSResource(BaseModel):
    """Canonical AWS resource entity schema for FinOps"""
    resource_id: str = Field(..., description="AWS resource identifier")
    resource_type: str = Field(..., description="Resource type (EC2, RDS, S3)")
    region: str = Field(..., description="AWS region")
    instance_type: Optional[str] = Field(None, description="EC2/RDS instance type")
    vcpus: Optional[int] = Field(None, description="Virtual CPUs")
    memory: Optional[int] = Field(None, description="Memory in GB")
    storage: Optional[int] = Field(None, description="Storage in GB")
    db_engine: Optional[str] = Field(None, description="Database engine (RDS)")
    instance_class: Optional[str] = Field(None, description="RDS instance class")
    allocated_storage: Optional[int] = Field(None, description="RDS allocated storage")
    storage_type: Optional[str] = Field(None, description="Storage type (gp2, gp3, io1)")
    storage_class: Optional[str] = Field(None, description="S3 storage class")
    size_gb: Optional[float] = Field(None, description="S3 bucket size in GB")
    object_count: Optional[int] = Field(None, description="S3 object count")
    versioning: Optional[str] = Field(None, description="S3 versioning enabled/disabled")
    cpu_utilization: Optional[float] = Field(None, description="CPU utilization %")
    memory_utilization: Optional[float] = Field(None, description="Memory utilization %")
    network_in: Optional[float] = Field(None, description="Network in bytes")
    network_out: Optional[float] = Field(None, description="Network out bytes")
    db_connections: Optional[int] = Field(None, description="Database connections")
    read_latency: Optional[float] = Field(None, description="Read latency ms")
    write_latency: Optional[float] = Field(None, description="Write latency ms")
    get_requests: Optional[int] = Field(None, description="S3 GET requests")
    put_requests: Optional[int] = Field(None, description="S3 PUT requests")
    data_transfer_out: Optional[float] = Field(None, description="Data transfer out bytes")
    monthly_cost: Optional[Decimal] = Field(None, description="Monthly cost USD")
    extras: Dict[str, Any] = Field(default_factory=dict, description="Additional unmapped fields")


class CanonicalCostReport(BaseModel):
    """Canonical AWS cost report entity schema for FinOps"""
    service_category: str = Field(..., description="AWS service category")
    resource_id: Optional[str] = Field(None, description="Associated resource ID")
    region: str = Field(..., description="AWS region")
    cost: Decimal = Field(..., description="Cost amount")
    usage: Optional[float] = Field(None, description="Usage amount")
    usage_type: str = Field(..., description="AWS usage type")
    monthly_cost: Optional[Decimal] = Field(None, description="Monthly cost USD")
    extras: Dict[str, Any] = Field(default_factory=dict, description="Additional unmapped fields")


class CanonicalEvent(BaseModel):
    """Complete canonical event envelope with strict typing"""
    meta: CanonicalMeta
    source: CanonicalSource
    entity: Literal["account", "opportunity", "contact", "aws_resources", "cost_reports"] = Field(..., description="Entity type")
    op: Literal["upsert", "delete"] = Field("upsert", description="Operation type")
    data: Union[CanonicalAccount, CanonicalOpportunity, CanonicalContact, CanonicalAWSResource, CanonicalCostReport] = Field(..., description="Canonical entity data (strictly typed)")
    unknown_fields: List[str] = Field(default_factory=list, description="Fields that couldn't be mapped")
    
    @model_validator(mode='after')
    def validate_entity_matches_data(self):
        """Ensure entity type matches data model type"""
        if self.entity == 'account' and not isinstance(self.data, CanonicalAccount):
            raise ValueError(f"Entity type 'account' requires CanonicalAccount data, got {type(self.data)}")
        elif self.entity == 'opportunity' and not isinstance(self.data, CanonicalOpportunity):
            raise ValueError(f"Entity type 'opportunity' requires CanonicalOpportunity data, got {type(self.data)}")
        elif self.entity == 'contact' and not isinstance(self.data, CanonicalContact):
            raise ValueError(f"Entity type 'contact' requires CanonicalContact data, got {type(self.data)}")
        elif self.entity == 'aws_resources' and not isinstance(self.data, CanonicalAWSResource):
            raise ValueError(f"Entity type 'aws_resources' requires CanonicalAWSResource data, got {type(self.data)}")
        elif self.entity == 'cost_reports' and not isinstance(self.data, CanonicalCostReport):
            raise ValueError(f"Entity type 'cost_reports' requires CanonicalCostReport data, got {type(self.data)}")
        
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        result = self.dict(exclude_none=False)
        # Convert nested Pydantic model to dict
        if isinstance(result['data'], dict):
            return result
        return {
            **result,
            'data': result['data'] if isinstance(result['data'], dict) else self.data.dict()
        }
