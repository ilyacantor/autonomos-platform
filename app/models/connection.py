"""
Connection models - Data connectors, mappings, schemas, and materialized views.

Includes connector definitions, field mappings, schema management, drift detection,
canonical streams, materialized entities, and DCL unified contacts.
"""
from app.models.base import (
    uuid, datetime, Column, String, JSON, DateTime, Integer, Float, ForeignKey, func, Index, UUID, relationship, Base
)


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
    tenant_id = Column(String, index=True)  # Multi-tenant isolation, not FK relationship
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

    repair_proposal_id = Column(UUID(as_uuid=True), ForeignKey("mapping_proposals.id"), nullable=True, index=True)
    repair_status = Column(String(20), nullable=True)

    __table_args__ = (
        Index('idx_drift_tenant_created', 'tenant_id', 'created_at'),
        Index('idx_drift_repair', 'repair_proposal_id'),
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


class MappingProposal(Base):
    """
    Phase 2: Mapping Proposals from DCL Intelligence Layer

    Stores LLM/RAG-generated mapping suggestions for schema drift repairs.
    Confidence-based routing: auto-apply (>=0.85), HITL queue (0.6-0.85), reject (<0.6)
    """
    __tablename__ = "mapping_proposals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)

    connector = Column(String(100), nullable=False)
    source_table = Column(String(255), nullable=False)
    source_field = Column(String(255), nullable=False)

    canonical_entity = Column(String(100), nullable=False)
    canonical_field = Column(String(100), nullable=False)

    confidence = Column(Float, nullable=False)
    reasoning = Column(String, nullable=True)
    alternatives = Column(JSON, nullable=True)

    action = Column(String(20), nullable=False)
    source = Column(String(50), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    applied_at = Column(DateTime(timezone=True), nullable=True)

    approval_workflows = relationship("ApprovalWorkflow", back_populates="proposal")

    __table_args__ = (
        Index('idx_proposals_lookup', 'tenant_id', 'connector', 'source_table', 'source_field'),
        Index('idx_proposals_action', 'tenant_id', 'action', 'created_at'),
    )


class ConfidenceScore(Base):
    """
    Phase 2: Confidence Scoring History

    Historical tracking of multi-factor confidence calculations for mappings.
    Factors: source_quality, usage_frequency, validation_success, human_approval, rag_similarity
    """
    __tablename__ = "confidence_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)

    mapping_id = Column(UUID(as_uuid=True), ForeignKey("field_mappings.id"), nullable=True, index=True)
    proposal_id = Column(UUID(as_uuid=True), ForeignKey("mapping_proposals.id"), nullable=True, index=True)

    score = Column(Float, nullable=False)
    factors = Column(JSON, nullable=False)

    calculated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index('idx_confidence_mapping', 'mapping_id'),
        Index('idx_confidence_tenant', 'tenant_id', 'calculated_at'),
    )


class ConnectorDefinition(Base):
    __tablename__ = "connector_definitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    connector_name = Column(String(255), nullable=False)
    connector_type = Column(String(50), nullable=False)
    description = Column(String, nullable=True)
    metadata_json = Column('metadata', JSON, nullable=False, server_default='{}')
    status = Column(String(50), nullable=False, server_default='active')
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index('idx_connector_tenant_status', 'tenant_id', 'status'),
    )


class EntitySchema(Base):
    __tablename__ = "entity_schemas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_name = Column(String(255), nullable=False)
    entity_version = Column(String(50), nullable=False, server_default='1.0.0')
    schema_definition = Column(JSON, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class FieldMapping(Base):
    __tablename__ = "field_mappings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    connection_id = Column(UUID(as_uuid=True), nullable=True)
    connector_id = Column(UUID(as_uuid=True), ForeignKey("connector_definitions.id"), nullable=False)
    entity_schema_id = Column(UUID(as_uuid=True), ForeignKey("entity_schemas.id"), nullable=False)

    source_table = Column(String(255), nullable=False)
    source_field = Column(String(255), nullable=False)
    source_data_type = Column(String(100), nullable=True)

    canonical_entity = Column(String(255), nullable=False)
    canonical_field = Column(String(255), nullable=False)
    canonical_data_type = Column(String(100), nullable=True)

    mapping_type = Column(String(50), nullable=False, server_default='direct')
    transformation_rule = Column(JSON, nullable=True)
    coercion_function = Column(String(255), nullable=True)

    confidence_score = Column(Float, nullable=False, server_default='1.0')
    validation_status = Column(String(50), nullable=False, server_default='pending')
    success_rate = Column(Float, nullable=True)
    avg_processing_time_ms = Column(Integer, nullable=True)
    error_count = Column(Integer, nullable=False, server_default='0')
    last_validated_at = Column(DateTime(timezone=True), nullable=True)

    mapping_source = Column(String(50), nullable=False, server_default='manual')
    version = Column(Integer, nullable=False, server_default='1')
    status = Column(String(50), nullable=False, server_default='active')
    notes = Column(String, nullable=True)

    # COMMENTED OUT: These columns don't exist in database schema yet
    # suggested_canonical_field = Column(String(255), nullable=True)
    # llm_reasoning = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        Index('idx_mapping_tenant_connector', 'tenant_id', 'connector_id'),
        Index('idx_mapping_entity', 'canonical_entity'),
        Index('idx_mapping_status', 'status'),
        Index('idx_mapping_confidence', 'confidence_score'),
    )
