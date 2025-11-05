"""
Data Contract: AAM → DCL Interface

This module defines the canonical data structure for transferring data from the
Adaptive API Mesh (AAM) layer to the Data Connection Layer (DCL) engine.

The contract ensures:
- Type safety between AAM and DCL
- Schema versioning for backward compatibility
- Clear data lineage and provenance tracking
- Quality metadata (confidence scores, repair history)
"""

from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum


class SchemaVersion(str, Enum):
    """Supported schema versions for AAM→DCL data transfer"""
    V1_0 = "1.0"
    V1_1 = "1.1"


class DataQuality(str, Enum):
    """Data quality assessment levels"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class RepairAction(BaseModel):
    """Record of a single repair action performed by AAM"""
    field_name: str = Field(..., description="Field that was repaired")
    original_value: Optional[str] = Field(None, description="Original field name/value")
    repaired_value: str = Field(..., description="Repaired field name/value")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Repair confidence (0-1)")
    repair_method: Literal["llm", "rag", "heuristic", "manual"] = Field(
        ..., description="Method used for repair"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    human_verified: bool = Field(False, description="Whether a human verified this repair")


class DataLineage(BaseModel):
    """Tracks the origin and transformations of data"""
    source_connector: str = Field(..., description="AAM connector name (e.g., 'salesforce')")
    source_entity: str = Field(..., description="Original entity name in source system")
    source_schema_version: str = Field(..., description="Schema fingerprint/version")
    
    normalization_timestamp: datetime = Field(default_factory=datetime.utcnow)
    drift_detected: bool = Field(False, description="Whether schema drift was detected")
    repair_history: List[RepairAction] = Field(default_factory=list)
    
    canonical_entity_type: str = Field(..., description="Canonical entity type (e.g., 'opportunity')")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Overall mapping confidence")


class FieldMetadata(BaseModel):
    """Metadata for a single field in the normalized data"""
    source_field_name: str = Field(..., description="Original field name from source")
    canonical_field_name: str = Field(..., description="Mapped canonical field name")
    
    data_type: str = Field(..., description="Field data type")
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    
    transformation_applied: Optional[str] = Field(
        None, description="Transformation function applied (e.g., 'date_normalize')"
    )
    repair_method: Optional[str] = Field(None, description="Repair method if field was repaired")
    
    semantic_similarity: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="RAG similarity score if available"
    )


class NormalizedRecord(BaseModel):
    """
    A single normalized record ready for DCL consumption.
    
    This is the canonical format that AAM produces and DCL consumes.
    """
    schema_version: SchemaVersion = Field(
        SchemaVersion.V1_0, description="Contract version for backward compatibility"
    )
    
    record_id: str = Field(..., description="Unique record ID from source system")
    entity_type: Literal["opportunity", "account", "contact"] = Field(
        ..., description="Canonical entity type"
    )
    
    data: Dict[str, Any] = Field(..., description="Normalized field data")
    
    lineage: DataLineage = Field(..., description="Data provenance and transformation history")
    
    field_metadata: Dict[str, FieldMetadata] = Field(
        default_factory=dict, description="Per-field quality and transformation metadata"
    )
    
    quality_assessment: DataQuality = Field(
        DataQuality.UNKNOWN, description="Overall data quality assessment"
    )
    
    @validator('quality_assessment', pre=True, always=True)
    def assess_quality(cls, v, values):
        """Automatically assess quality based on confidence scores"""
        if 'lineage' in values:
            confidence = values['lineage'].confidence_score
            if confidence >= 0.9:
                return DataQuality.HIGH
            elif confidence >= 0.7:
                return DataQuality.MEDIUM
            else:
                return DataQuality.LOW
        return DataQuality.UNKNOWN


class AAMDataBatch(BaseModel):
    """
    Batch of normalized records from AAM to DCL.
    
    This is the top-level data structure for AAM→DCL transfers.
    """
    schema_version: SchemaVersion = Field(
        SchemaVersion.V1_0, description="Batch schema version"
    )
    
    batch_id: str = Field(..., description="Unique batch identifier")
    connector_name: str = Field(..., description="AAM connector that produced this batch")
    
    records: List[NormalizedRecord] = Field(..., description="Normalized records in this batch")
    
    batch_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional batch-level metadata"
    )
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    total_records: int = Field(..., ge=0)
    successful_normalizations: int = Field(..., ge=0)
    failed_normalizations: int = Field(0, ge=0)
    
    @validator('total_records', pre=True, always=True)
    def validate_total(cls, v, values):
        """Ensure total matches record count"""
        if 'records' in values:
            return len(values['records'])
        return v


class DCLIngestionRequest(BaseModel):
    """
    Request format for DCL to ingest AAM-normalized data.
    
    Used by DCL when USE_AAM_AS_SOURCE feature flag is enabled.
    """
    schema_version: SchemaVersion = Field(SchemaVersion.V1_0)
    
    tenant_id: str = Field(..., description="Multi-tenant isolation")
    source_type: Literal["aam_normalized"] = Field(
        "aam_normalized", description="Indicates data comes from AAM"
    )
    
    data_batch: AAMDataBatch = Field(..., description="Normalized data from AAM")
    
    force_refresh: bool = Field(
        False, description="Force DCL to rebuild materialized views"
    )


class DCLIngestionResponse(BaseModel):
    """Response from DCL after ingesting AAM data"""
    success: bool
    batch_id: str
    
    records_ingested: int
    materialized_views_updated: List[str] = Field(default_factory=list)
    
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    
    ingestion_timestamp: datetime = Field(default_factory=datetime.utcnow)
    processing_time_seconds: float


if __name__ == "__main__":
    example_lineage = DataLineage(
        source_connector="salesforce",
        source_entity="Opportunity",
        source_schema_version="sf_opp_v2.3",
        canonical_entity_type="opportunity",
        confidence_score=0.95,
        drift_detected=False
    )
    
    example_record = NormalizedRecord(
        record_id="SF-OPP-001",
        entity_type="opportunity",
        data={
            "opportunity_id": "SF-OPP-001",
            "name": "Enterprise Deal",
            "amount": 100000.0,
            "stage": "Proposal",
            "close_date": "2025-12-31"
        },
        lineage=example_lineage,
        field_metadata={
            "amount": FieldMetadata(
                source_field_name="Amount",
                canonical_field_name="amount",
                data_type="float",
                confidence_score=1.0,
                semantic_similarity=0.98
            )
        }
    )
    
    print("AAM→DCL Data Contract Example:")
    print("=" * 60)
    print(example_record.json(indent=2))
