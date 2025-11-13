import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

Base = declarative_base()


class KBDocument(Base):
    """
    KB Documents table: stores document metadata.
    
    Each document represents a source (file, URL, text) ingested into the KB.
    Documents are chunked into KBChunk records for embedding and retrieval.
    """
    __tablename__ = "kb_documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    env = Column(String(20), nullable=False, index=True)
    doc_id = Column(String(255), nullable=False, unique=True, index=True)
    title = Column(String(500), nullable=False)
    source_type = Column(String(50), nullable=False)
    source_location = Column(Text, nullable=False)
    tags = Column(JSONB, nullable=False, server_default="[]")
    metadata = Column(JSONB, nullable=False, server_default="{}")
    status = Column(String(50), nullable=False, server_default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    chunks = relationship("KBChunk", back_populates="document", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_kb_documents_tenant_env", "tenant_id", "env"),
    )


class KBChunk(Base):
    """
    KB Chunks table: stores document chunks with embeddings.
    
    Each chunk is a semantic section of a document with:
    - Text content (original and PII-redacted)
    - Vector embedding (384-dim via sentence-transformers)
    - Metadata for citation and retrieval
    """
    __tablename__ = "kb_chunks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("kb_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    env = Column(String(20), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    section = Column(String(500), nullable=False)
    text = Column(Text, nullable=False)
    text_redacted = Column(Text, nullable=True)
    embedding = Column(Vector(384), nullable=True)
    tokens = Column(Integer, nullable=False, server_default="0")
    metadata = Column(JSONB, nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    document = relationship("KBDocument", back_populates="chunks")
    
    __table_args__ = (
        Index("idx_kb_chunks_tenant_env", "tenant_id", "env"),
        Index("idx_kb_chunks_document", "document_id", "chunk_index"),
    )


class KBMetadata(Base):
    """
    KB Metadata table: stores key-value pairs for KB configuration.
    
    Examples:
    - embedding_model: "sentence-transformers/all-MiniLM-L6-v2"
    - last_reindex: "2024-11-08T00:00:00Z"
    - chunk_strategy: "auto"
    """
    __tablename__ = "kb_metadata"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    env = Column(String(20), nullable=False, index=True)
    key = Column(String(255), nullable=False)
    value = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    __table_args__ = (
        Index("idx_kb_metadata_tenant_env_key", "tenant_id", "env", "key", unique=True),
    )


class KBIngestJob(Base):
    """
    KB Ingest Jobs table: tracks background ingestion jobs.
    
    Jobs are processed via RQ (Redis Queue) and update status as they progress:
    - queued: Job created but not started
    - processing: Job in progress
    - completed: Job finished successfully
    - failed: Job failed with error
    """
    __tablename__ = "kb_ingest_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    env = Column(String(20), nullable=False, index=True)
    job_id = Column(String(255), nullable=False, unique=True, index=True)
    status = Column(String(50), nullable=False, server_default="queued")
    items_count = Column(Integer, nullable=False, server_default="0")
    items_processed = Column(Integer, nullable=False, server_default="0")
    policy = Column(JSONB, nullable=False)
    result = Column(JSONB, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    __table_args__ = (
        Index("idx_kb_ingest_jobs_tenant_env", "tenant_id", "env"),
        Index("idx_kb_ingest_jobs_status", "status", "created_at"),
    )


class KBFeedback(Base):
    """
    KB Feedback table: stores user feedback on responses.
    
    Captures thumbs up/down ratings and notes to improve retrieval quality.
    Used for:
    - Monitoring response quality
    - Training reranker models
    - Identifying knowledge gaps
    """
    __tablename__ = "kb_feedback"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    env = Column(String(20), nullable=False, index=True)
    turn_id = Column(String(255), nullable=False, index=True)
    trace_id = Column(String(255), nullable=False, index=True)
    rating = Column(String(10), nullable=False)
    notes = Column(Text, nullable=False, server_default="")
    metadata = Column(JSONB, nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    __table_args__ = (
        Index("idx_kb_feedback_tenant_env", "tenant_id", "env"),
        Index("idx_kb_feedback_rating", "rating", "created_at"),
    )
