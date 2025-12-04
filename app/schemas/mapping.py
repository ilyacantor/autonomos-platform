"""
Pydantic schemas for DCL Mapping Registry API
RACI Phase 1 - Mapping registry access with Redis caching
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


class MappingResponse(BaseModel):
    """Single mapping response"""
    mapping_id: UUID = Field(..., description="Unique mapping identifier")
    connector_id: str = Field(..., description="Connector name (e.g., 'salesforce')")
    source_table: str = Field(..., description="Source table/entity name")
    source_field: str = Field(..., description="Source field name")
    canonical_entity: str = Field(..., description="Target canonical entity")
    canonical_field: str = Field(..., description="Target canonical field")
    confidence: float = Field(..., description="Mapping confidence score (0.0-1.0)")
    mapping_type: str = Field(..., description="Mapping type (e.g., 'direct', 'transform')")
    transform_expr: Optional[Dict[str, Any]] = Field(None, description="Transformation rule (JSON)")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class MappingSummary(BaseModel):
    """Summary mapping for list responses"""
    mapping_id: UUID
    source_table: str
    source_field: str
    canonical_entity: str
    canonical_field: str
    confidence: float
    mapping_type: str

    class Config:
        from_attributes = True


class MappingListResponse(BaseModel):
    """List of mappings response"""
    connector_id: str = Field(..., description="Connector name")
    total_count: int = Field(..., description="Total number of mappings")
    mappings: List[MappingSummary] = Field(..., description="List of mappings")


class MappingCreateRequest(BaseModel):
    """Request body for creating/updating mapping"""
    connector_id: str = Field(..., description="Connector name (e.g., 'salesforce')")
    source_table: str = Field(..., min_length=1, max_length=255, description="Source table name")
    source_field: str = Field(..., min_length=1, max_length=255, description="Source field name")
    canonical_entity: str = Field(..., min_length=1, max_length=255, description="Canonical entity")
    canonical_field: str = Field(..., min_length=1, max_length=255, description="Canonical field")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Confidence score")
    mapping_type: str = Field("direct", description="Mapping type")
    transform_expr: Optional[Dict[str, Any]] = Field(None, description="Transformation rule")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class MappingCreateResponse(BaseModel):
    """Response after creating/updating mapping"""
    mapping_id: UUID = Field(..., description="Created/updated mapping ID")
    status: str = Field(..., description="Status (created/updated)")
    cache_invalidated: bool = Field(..., description="Whether cache was invalidated")
