import uuid
from datetime import datetime
from enum import Enum
from typing import Optional
from sqlalchemy import Column, String, DateTime, Integer, Float, Enum as SQLEnum, ForeignKey, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship
from pydantic import BaseModel, Field
try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    Vector = None


Base = declarative_base()


class ConnectionStatus(str, Enum):
    """Connection lifecycle status"""
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    FAILED = "FAILED"
    HEALING = "HEALING"
    INACTIVE = "INACTIVE"


class JobStatus(str, Enum):
    """Job execution status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Connection(Base):
    """
    AAM Connection Registry
    Tracks all connections managed by the Adaptive API Mesh
    
    Phase 1 Enhancements:
    - connector_config: JSONB storage for connector-specific configuration
    - last_health_check: Timestamp of most recent health check
    - schema_fingerprint: Hash for drift detection
    - normalized_output_path: Redis Stream or file path for DCL consumption
    
    Auto-Onboarding Enhancements (Nov 2025):
    - namespace: Scope connections to 'autonomy' (auto-onboarded) or 'demo' (manual)
    - first_sync_rows: Row count from initial tiny sync (≤20 items)
    - latency_ms: Response time for first sync in milliseconds
    - credential_locator: Reference to credential source (vault:/env:/consent:/sp:)
    - risk_level: Risk assessment from AOD (low/med/high)
    - evidence: Sanctioning evidence (status, source, timestamp)
    - owner: Ownership metadata (user, confidence, why)
    """
    __tablename__ = "connections"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    source_type = Column(String, nullable=False)
    airbyte_source_id = Column(UUID(as_uuid=True), nullable=True)
    airbyte_connection_id = Column(UUID(as_uuid=True), nullable=True)
    status = Column(SQLEnum(ConnectionStatus), default=ConnectionStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    connector_config = Column(JSON, nullable=True)
    last_health_check = Column(DateTime, nullable=True)
    schema_fingerprint = Column(String, nullable=True)
    normalized_output_path = Column(String, nullable=True)
    
    namespace = Column(String, nullable=False, default='demo')
    first_sync_rows = Column(Integer, nullable=True)
    latency_ms = Column(Float, nullable=True)
    credential_locator = Column(String, nullable=True)
    risk_level = Column(String, nullable=True)
    evidence = Column(JSON, nullable=True)
    owner = Column(JSON, nullable=True)
    
    catalog_versions = relationship("SyncCatalogVersion", back_populates="connection", cascade="all, delete-orphan")
    job_history = relationship("JobHistory", back_populates="connection", cascade="all, delete-orphan")


class SyncCatalogVersion(Base):
    """
    Versioned catalog schema tracking
    Maintains history of all schema changes for drift detection and repair
    """
    __tablename__ = "sync_catalog_versions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connection_id = Column(UUID(as_uuid=True), ForeignKey("connections.id", ondelete="CASCADE"), nullable=False)
    sync_catalog = Column(JSON, nullable=False)
    version_number = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    connection = relationship("Connection", back_populates="catalog_versions")


class JobHistory(Base):
    """
    Job execution tracking
    Records all sync jobs and their outcomes
    """
    __tablename__ = "job_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connection_id = Column(UUID(as_uuid=True), ForeignKey("connections.id", ondelete="CASCADE"), nullable=False)
    airbyte_job_id = Column(String, nullable=True)
    status = Column(SQLEnum(JobStatus), default=JobStatus.PENDING, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(String, nullable=True)
    
    connection = relationship("Connection", back_populates="job_history")


class ConnectionCreate(BaseModel):
    """Pydantic model for connection creation"""
    source_type: str = Field(..., description="Source type (e.g., 'Salesforce')")
    connection_name: str = Field(..., description="Human-readable connection name")
    credential_id: str = Field(..., description="Credential identifier for auth")


class ConnectionResponse(BaseModel):
    """Pydantic model for connection response"""
    id: uuid.UUID
    name: str
    source_type: str
    status: ConnectionStatus
    airbyte_source_id: Optional[uuid.UUID] = None
    airbyte_connection_id: Optional[uuid.UUID] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class CatalogUpdate(BaseModel):
    """Pydantic model for catalog updates"""
    connection_id: uuid.UUID
    new_sync_catalog: dict = Field(..., description="New syncCatalog JSON structure")


class SyncTrigger(BaseModel):
    """Pydantic model for triggering sync"""
    connection_id: uuid.UUID


class HealthResponse(BaseModel):
    """Health check response"""
    service: str
    status: str = "healthy"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class RepairKnowledgeBase(Base):
    """
    Knowledge base for successful schema repairs
    Stores historical repairs for RAG-based healing
    Uses pgvector for semantic similarity search
    """
    __tablename__ = "repair_knowledge_base"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_type = Column(String, nullable=False)
    error_signature = Column(Text, nullable=False)
    error_signature_embedding = Column(Vector(1536) if Vector else JSON, nullable=True)
    successful_mapping = Column(JSON, nullable=False)
    confidence_score = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DriftEvent(BaseModel):
    """Event model for schema drift detection"""
    connection_id: uuid.UUID
    error_signature: str
    last_good_catalog: dict
    
    class Config:
        from_attributes = True


class RepairProposal(BaseModel):
    """Event model for repair proposals from RAG Engine"""
    connection_id: uuid.UUID
    proposed_catalog: dict
    confidence_score: float
    original_error_signature: str
    
    class Config:
        from_attributes = True


class StatusUpdate(BaseModel):
    """Event model for status updates"""
    connection_id: uuid.UUID
    status: ConnectionStatus
    message: Optional[str] = None
    
    class Config:
        from_attributes = True
