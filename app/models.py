import uuid
from datetime import datetime
from sqlalchemy import Column, String, JSON, DateTime, Integer, Float, ForeignKey, func, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from shared.database import Base

class Tenant(Base):
    __tablename__ = "tenants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    users = relationship("User", back_populates="tenant")
    tasks = relationship("Task", back_populates="tenant")
    task_logs = relationship("TaskLog", back_populates="tenant")

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    tenant = relationship("Tenant", back_populates="users")

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    status = Column(String, default="queued", nullable=False)
    payload = Column(JSON, nullable=False)
    result = Column(JSON, nullable=True)
    callback_url = Column(String, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=0, nullable=False)
    on_success_next_task = Column(JSON, nullable=True)
    next_task_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    tenant = relationship("Tenant", back_populates="tasks")
    logs = relationship("TaskLog", back_populates="task")

class TaskLog(Base):
    __tablename__ = "task_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    message = Column(String, nullable=False)
    
    task = relationship("Task", back_populates="logs")
    tenant = relationship("Tenant", back_populates="task_logs")


class ApiJournal(Base):
    __tablename__ = "api_journal"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"))
    agent_id = Column(String, nullable=True)
    route = Column(String, nullable=False)
    method = Column(String, nullable=False)
    status = Column(Integer, nullable=False)
    latency_ms = Column(Integer)
    trace_id = Column(String)
    body_sha256 = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    
    key = Column(String, primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"))
    response_body = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)


class RateLimitCounter(Base):
    __tablename__ = "rate_limit_counters"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"))
    agent_id = Column(String)
    route = Column(String)
    tokens_remaining = Column(Integer)
    last_refill = Column(DateTime)
    window_start = Column(DateTime)


class CanonicalStream(Base):
    __tablename__ = "canonical_streams"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"))
    entity = Column(String)
    data = Column(JSON)
    meta = Column(JSON)
    source = Column(JSON)
    emitted_at = Column(DateTime, default=datetime.utcnow)


class MappingRegistry(Base):
    __tablename__ = "mapping_registry"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    connection_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    vendor = Column(String)
    canonical_field = Column(String)
    vendor_field = Column(String)
    coercion = Column(String, nullable=True)
    confidence = Column(Float)
    version = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_mapping_tenant_vendor', 'tenant_id', 'vendor'),
    )


class DriftEvent(Base):
    __tablename__ = "drift_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    connection_id = Column(UUID(as_uuid=True))
    event_type = Column(String)
    old_schema = Column(JSON)
    new_schema = Column(JSON)
    confidence = Column(Float)
    status = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_drift_tenant_created', 'tenant_id', 'created_at'),
    )


class SchemaChange(Base):
    __tablename__ = "schema_changes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    connection_id = Column(UUID(as_uuid=True))
    change_type = Column(String)
    details = Column(JSON)
    applied_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_schema_tenant_applied', 'tenant_id', 'applied_at'),
    )


class MaterializedAccount(Base):
    """Materialized view of canonical accounts"""
    __tablename__ = "materialized_accounts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    account_id = Column(String, nullable=False)
    external_ids = Column(JSON, default=list)
    name = Column(String)
    type = Column(String)
    industry = Column(String)
    owner_id = Column(String)
    status = Column(String)
    extras = Column(JSON, default=dict)
    source_system = Column(String)
    source_connection_id = Column(String)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    synced_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_mat_account_tenant_id', 'tenant_id', 'account_id'),
        Index('idx_mat_account_source', 'source_system', 'source_connection_id'),
    )


class MaterializedOpportunity(Base):
    """Materialized view of canonical opportunities"""
    __tablename__ = "materialized_opportunities"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    opportunity_id = Column(String, nullable=False)
    account_id = Column(String)
    name = Column(String)
    stage = Column(String)
    amount = Column(Float)
    currency = Column(String)
    close_date = Column(DateTime)
    owner_id = Column(String)
    probability = Column(Float)
    extras = Column(JSON, default=dict)
    source_system = Column(String)
    source_connection_id = Column(String)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    synced_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_mat_opp_tenant_id', 'tenant_id', 'opportunity_id'),
        Index('idx_mat_opp_account', 'account_id'),
        Index('idx_mat_opp_source', 'source_system', 'source_connection_id'),
    )


class MaterializedContact(Base):
    """Materialized view of canonical contacts"""
    __tablename__ = "materialized_contacts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    contact_id = Column(String, nullable=False)
    account_id = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    name = Column(String)
    email = Column(String)
    phone = Column(String)
    title = Column(String)
    department = Column(String)
    role = Column(String)
    extras = Column(JSON, default=dict)
    source_system = Column(String)
    source_connection_id = Column(String)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    synced_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_mat_contact_tenant_id', 'tenant_id', 'contact_id'),
        Index('idx_mat_contact_account', 'account_id'),
        Index('idx_mat_contact_source', 'source_system', 'source_connection_id'),
    )


class DCLUnifiedContact(Base):
    """DCL unified contact table - one record per unique email PER TENANT"""
    __tablename__ = "dcl_unified_contact"
    
    unified_contact_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    email = Column(String, nullable=False, index=True)
    first_name = Column(String)
    last_name = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    links = relationship("DCLUnifiedContactLink", back_populates="unified_contact")
    
    __table_args__ = (
        Index('idx_dcl_unified_tenant_email', 'tenant_id', 'email', unique=True),
    )


class DCLUnifiedContactLink(Base):
    """DCL unified contact link - maps source contacts to unified contact (tenant-scoped)"""
    __tablename__ = "dcl_unified_contact_link"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    unified_contact_id = Column(UUID(as_uuid=True), ForeignKey("dcl_unified_contact.unified_contact_id"), nullable=False, index=True)
    source_system = Column(String, nullable=False)
    source_contact_id = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    unified_contact = relationship("DCLUnifiedContact", back_populates="links")
    
    __table_args__ = (
        Index('idx_dcl_link_tenant_source', 'tenant_id', 'source_system', 'source_contact_id', unique=True),
    )


class HITLRepairAudit(Base):
    """
    HITL Repair Audit - persistent tracking of Human-In-The-Loop repair decisions.
    
    Complements Redis queue (7-day TTL) with permanent audit logging for:
    - Repair suggestions requiring human review (confidence 0.6-0.85)
    - Review decisions (approved/rejected)
    - Full audit trail for compliance and learning
    """
    __tablename__ = "hitl_repair_audit"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    
    drift_event_id = Column(String, nullable=False, index=True)
    field_name = Column(String, nullable=False)
    connector_name = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    
    suggested_mapping = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    confidence_reason = Column(String)
    transformation = Column(String)
    rag_similarity_count = Column(Integer, default=0)
    
    review_status = Column(String, default="pending", nullable=False)
    reviewed_by = Column(String, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(String, nullable=True)
    
    audit_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_hitl_tenant_status', 'tenant_id', 'review_status'),
        Index('idx_hitl_drift_event', 'drift_event_id'),
    )
