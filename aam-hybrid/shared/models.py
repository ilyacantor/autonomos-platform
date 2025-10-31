import uuid
from datetime import datetime
from enum import Enum
from typing import Optional
from sqlalchemy import Column, String, DateTime, Integer, Enum as SQLEnum, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship
from pydantic import BaseModel, Field


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
