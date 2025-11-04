"""
Canonical Event Schema for AutonomOS AAM

This module defines the canonical event structure used throughout the
Adaptive API Mesh for normalizing heterogeneous data from multiple connectors.

Canonical events provide:
- Unified schema across all data sources
- Schema fingerprinting for drift detection
- Version tracking for backward compatibility
- Rich metadata for observability
"""

from typing import Dict, List, Optional, Any, Literal, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum


class EventSchemaVersion(str, Enum):
    """Canonical event schema versions"""
    V1_0 = "1.0"
    V2_0 = "2.0"


class EventType(str, Enum):
    """Types of canonical events"""
    ENTITY_CREATED = "entity_created"
    ENTITY_UPDATED = "entity_updated"
    ENTITY_DELETED = "entity_deleted"
    SCHEMA_DRIFT_DETECTED = "schema_drift_detected"
    REPAIR_COMPLETED = "repair_completed"
    HEALTH_CHECK = "health_check"


class CanonicalEntityType(str, Enum):
    """Supported canonical entity types"""
    OPPORTUNITY = "opportunity"
    ACCOUNT = "account"
    CONTACT = "contact"
    CUSTOM = "custom"


class DriftType(str, Enum):
    """Types of schema drift"""
    FIELD_ADDED = "field_added"
    FIELD_REMOVED = "field_removed"
    FIELD_RENAMED = "field_renamed"
    TYPE_CHANGED = "type_changed"
    CONSTRAINT_CHANGED = "constraint_changed"


class SchemaFingerprint(BaseModel):
    """
    Cryptographic fingerprint of a schema for drift detection.
    
    Uses field names, types, and constraints to generate a unique hash.
    """
    fingerprint_hash: str = Field(..., description="SHA-256 hash of schema structure")
    field_count: int = Field(..., ge=0)
    field_names: List[str] = Field(..., description="Sorted list of field names")
    
    schema_version: str = Field(..., description="Connector-specific schema version")
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    
    connector_name: str = Field(..., description="Source connector (e.g., 'salesforce')")
    entity_type: str = Field(..., description="Entity type in source system")


class DriftEvent(BaseModel):
    """Details of detected schema drift"""
    drift_type: DriftType
    field_affected: Optional[str] = Field(None, description="Field that changed")
    
    old_value: Optional[str] = Field(None, description="Previous field name/type")
    new_value: Optional[str] = Field(None, description="Current field name/type")
    
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    severity: Literal["critical", "warning", "info"] = Field("warning")


class FieldMapping(BaseModel):
    """
    Mapping between source field and canonical field.
    
    Tracks the transformation logic and confidence.
    """
    source_field: str = Field(..., description="Original field name from connector")
    canonical_field: str = Field(..., description="Mapped canonical field name")
    
    source_type: str = Field(..., description="Source data type")
    canonical_type: str = Field(..., description="Canonical data type")
    
    mapping_method: Literal["exact", "rag", "llm", "heuristic", "manual"] = Field(
        ..., description="How this mapping was determined"
    )
    
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    
    transformation_function: Optional[str] = Field(
        None, description="Python function to transform data (e.g., 'datetime.fromisoformat')"
    )
    
    semantic_similarity: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="RAG similarity score"
    )
    
    human_verified: bool = Field(False, description="Whether a human verified this mapping")
    verified_at: Optional[datetime] = None


class CanonicalEvent(BaseModel):
    """
    Base canonical event structure.
    
    All events flowing through AAM conform to this schema.
    """
    schema_version: EventSchemaVersion = Field(
        EventSchemaVersion.V1_0, description="Event schema version"
    )
    
    event_id: str = Field(..., description="Unique event identifier")
    event_type: EventType = Field(..., description="Type of event")
    
    connector_name: str = Field(..., description="Source connector (e.g., 'salesforce')")
    connector_id: str = Field(..., description="Unique connector instance ID")
    
    entity_type: CanonicalEntityType = Field(..., description="Canonical entity type")
    entity_id: str = Field(..., description="Unique entity identifier from source")
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    tenant_id: str = Field(..., description="Multi-tenant isolation")
    
    schema_fingerprint: SchemaFingerprint = Field(..., description="Schema version tracking")
    
    payload: Dict[str, Any] = Field(..., description="Event-specific data")
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class EntityEvent(CanonicalEvent):
    """
    Canonical event for entity operations (create/update/delete).
    
    Extends base CanonicalEvent with entity-specific fields.
    """
    event_type: Literal[
        EventType.ENTITY_CREATED,
        EventType.ENTITY_UPDATED,
        EventType.ENTITY_DELETED
    ] = Field(..., description="Must be an entity operation")
    
    field_mappings: List[FieldMapping] = Field(
        default_factory=list, description="Field-level mapping details"
    )
    
    overall_confidence: float = Field(..., ge=0.0, le=1.0)
    
    raw_data: Optional[Dict[str, Any]] = Field(
        None, description="Original raw data from connector (for debugging)"
    )


class SchemaEvent(CanonicalEvent):
    """
    Canonical event for schema changes (drift detection).
    """
    event_type: Literal[EventType.SCHEMA_DRIFT_DETECTED] = Field(
        EventType.SCHEMA_DRIFT_DETECTED
    )
    
    previous_fingerprint: SchemaFingerprint = Field(..., description="Previous schema state")
    current_fingerprint: SchemaFingerprint = Field(..., description="Current schema state")
    
    drift_details: List[DriftEvent] = Field(..., description="Specific changes detected")
    
    auto_repair_attempted: bool = Field(False)
    repair_job_id: Optional[str] = Field(None, description="ID of repair job if triggered")


class RepairEvent(CanonicalEvent):
    """
    Canonical event for repair operations.
    """
    event_type: Literal[EventType.REPAIR_COMPLETED] = Field(EventType.REPAIR_COMPLETED)
    
    repair_job_id: str = Field(..., description="Unique repair job identifier")
    
    fields_repaired: List[FieldMapping] = Field(..., description="Fields that were repaired")
    
    repair_confidence: float = Field(..., ge=0.0, le=1.0)
    repair_method: Literal["llm", "rag", "heuristic", "manual"]
    
    human_review_required: bool = Field(
        False, description="Whether human review is needed"
    )
    human_reviewed: bool = Field(False)
    reviewer_id: Optional[str] = None
    
    success: bool = Field(..., description="Whether repair succeeded")
    error_message: Optional[str] = None


class HealthCheckEvent(CanonicalEvent):
    """
    Canonical event for connector health checks.
    """
    event_type: Literal[EventType.HEALTH_CHECK] = Field(EventType.HEALTH_CHECK)
    
    connector_status: Literal["healthy", "degraded", "down"] = Field(...)
    
    response_time_ms: float = Field(..., ge=0.0)
    error_rate: float = Field(0.0, ge=0.0, le=1.0)
    
    details: Dict[str, Any] = Field(default_factory=dict)


class EventStream(BaseModel):
    """
    Stream of canonical events for batch processing.
    """
    stream_id: str = Field(..., description="Unique stream identifier")
    
    events: List[Union[EntityEvent, SchemaEvent, RepairEvent, HealthCheckEvent]] = Field(
        ..., description="Events in this stream"
    )
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    total_events: int = Field(..., ge=0)
    
    @validator('total_events', pre=True, always=True)
    def validate_total(cls, v, values):
        """Ensure total matches event count"""
        if 'events' in values:
            return len(values['events'])
        return v


if __name__ == "__main__":
    fingerprint = SchemaFingerprint(
        fingerprint_hash="abc123def456",
        field_count=5,
        field_names=["id", "name", "amount", "stage", "close_date"],
        schema_version="v2.3",
        connector_name="salesforce",
        entity_type="Opportunity"
    )
    
    field_mapping = FieldMapping(
        source_field="Amount",
        canonical_field="amount",
        source_type="decimal",
        canonical_type="float",
        mapping_method="exact",
        confidence_score=1.0
    )
    
    entity_event = EntityEvent(
        event_id="evt-001",
        event_type=EventType.ENTITY_CREATED,
        connector_name="salesforce",
        connector_id="sf-conn-001",
        entity_type=CanonicalEntityType.OPPORTUNITY,
        entity_id="SF-OPP-001",
        tenant_id="tenant-123",
        schema_fingerprint=fingerprint,
        payload={
            "opportunity_id": "SF-OPP-001",
            "name": "Enterprise Deal",
            "amount": 100000.0
        },
        field_mappings=[field_mapping],
        overall_confidence=0.95
    )
    
    print("Canonical Event Example:")
    print("=" * 60)
    print(entity_event.json(indent=2))
