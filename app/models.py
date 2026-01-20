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
    is_admin = Column(String, default='false', nullable=False)
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


class ApprovalWorkflow(Base):
    """
    Phase 2: Human-in-the-Loop Approval Workflow
    
    Manages approval process for medium-confidence mapping proposals (0.6-0.85).
    7-day TTL for review with Slack/email notifications.
    """
    __tablename__ = "approval_workflows"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    proposal_id = Column(UUID(as_uuid=True), ForeignKey("mapping_proposals.id"), nullable=False, index=True)
    
    status = Column(String(20), nullable=False, server_default='pending')
    priority = Column(String(20), server_default='normal')
    
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    approver_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    approval_notes = Column(String, nullable=True)
    rejection_reason = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    proposal = relationship("MappingProposal", back_populates="approval_workflows")
    
    __table_args__ = (
        Index('idx_workflows_status', 'tenant_id', 'status', 'created_at'),
        Index('idx_workflows_assigned', 'assigned_to', 'status'),
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


# =============================================================================
# AGENTIC ORCHESTRATION MODELS (Phase 1)
# =============================================================================

class Agent(Base):
    """
    Agent configuration - defines what an agent can do.

    Stores LangGraph workflow definition, MCP server access, and guardrails.
    """
    __tablename__ = "agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)

    # Identity
    name = Column(String(255), nullable=False)
    description = Column(String, nullable=True)
    agent_type = Column(String(50), nullable=False, server_default='general')  # general, specialist, orchestrator

    # LangGraph configuration
    graph_definition = Column(JSON, nullable=True)  # Serialized StateGraph nodes/edges
    system_prompt = Column(String, nullable=True)

    # MCP servers this agent can access
    mcp_servers = Column(JSON, server_default='[]')  # ["aos-dcl", "aos-aam", "slack"]

    # LLM configuration
    model = Column(String(100), server_default='claude-sonnet-4-20250514')
    temperature = Column(Float, server_default='0.7')
    max_tokens = Column(Integer, server_default='4096')

    # Guardrails (ARB Condition compliance)
    max_steps = Column(Integer, server_default='20')
    max_cost_usd = Column(Float, server_default='1.0')
    require_approval_for = Column(JSON, server_default='[]')  # ["write_operations", "external_calls"]
    forbidden_actions = Column(JSON, server_default='[]')  # ["delete_data", "modify_schema"]

    # Versioning
    version = Column(Integer, server_default='1')
    status = Column(String(20), server_default='active')  # active, archived, draft

    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    runs = relationship("AgentRun", back_populates="agent")

    __table_args__ = (
        Index('idx_agent_tenant_name', 'tenant_id', 'name'),
        Index('idx_agent_tenant_status', 'tenant_id', 'status'),
    )


class AgentRun(Base):
    """
    Agent execution record - tracks a single run of an agent.

    The run_id matches LangGraph's thread_id for checkpoint correlation.
    Actual execution state is stored in LangGraph checkpoints table.
    """
    __tablename__ = "agent_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # Same as LangGraph thread_id
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)

    # Status tracking
    status = Column(String(20), nullable=False, server_default='pending')  # pending, running, paused, completed, failed, cancelled

    # Input/Output
    input_data = Column(JSON, nullable=True)  # Initial input to the agent
    output_data = Column(JSON, nullable=True)  # Final output (if completed)
    error = Column(String, nullable=True)  # Error message (if failed)

    # Trigger context
    triggered_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    trigger_type = Column(String(20), server_default='api')  # api, chat, schedule, webhook

    # Cost tracking (ARB compliance)
    tokens_input = Column(Integer, server_default='0')
    tokens_output = Column(Integer, server_default='0')
    cost_usd = Column(Float, server_default='0.0')
    steps_executed = Column(Integer, server_default='0')

    # OBO token tracking (ARB Condition 1)
    obo_token_issued_at = Column(DateTime(timezone=True), nullable=True)
    obo_token_expires_at = Column(DateTime(timezone=True), nullable=True)

    # Timing
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    agent = relationship("Agent", back_populates="runs")
    approvals = relationship("AgentApproval", back_populates="run")

    __table_args__ = (
        Index('idx_run_tenant_status', 'tenant_id', 'status'),
        Index('idx_run_agent_created', 'agent_id', 'created_at'),
        Index('idx_run_triggered_by', 'triggered_by', 'created_at'),
    )


class AgentApproval(Base):
    """
    Human-in-the-loop approval for agent actions.

    When an agent hits a sensitive operation, it pauses and creates an approval request.
    Implements ARB Condition 1: Token refresh on approval resume.
    """
    __tablename__ = "agent_approvals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("agent_runs.id"), nullable=False, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)

    # What needs approval
    action_type = Column(String(50), nullable=False)  # write_data, external_call, trigger_sync, etc.
    action_details = Column(JSON, nullable=False)  # Tool name, arguments, context
    step_number = Column(Integer, nullable=False)  # Which step in the graph

    # State
    status = Column(String(20), nullable=False, server_default='pending')  # pending, approved, rejected, timeout, escalated

    # Timing
    requested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)  # Default 7 days from requested_at
    responded_at = Column(DateTime(timezone=True), nullable=True)

    # Response
    responded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approval_notes = Column(String, nullable=True)
    rejection_reason = Column(String, nullable=True)

    # Timeout handling
    auto_action = Column(String(20), server_default='reject')  # reject, approve, escalate
    escalate_to = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Relationships
    run = relationship("AgentRun", back_populates="approvals")

    __table_args__ = (
        Index('idx_approval_tenant_status', 'tenant_id', 'status'),
        Index('idx_approval_run', 'run_id'),
        Index('idx_approval_expires', 'expires_at', 'status'),
    )


class AgentCheckpoint(Base):
    """
    LangGraph checkpoint storage with blob offload support.

    Implements ARB Condition 3: Checkpoint blobs >100KB are offloaded to S3/MinIO.
    Small checkpoints are stored inline in checkpoint_data (JSONB).
    """
    __tablename__ = "agent_checkpoints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("agent_runs.id"), nullable=False, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)

    # LangGraph threading
    thread_id = Column(String(255), nullable=False, index=True)  # Run ID as string
    thread_ts = Column(String(255), nullable=False)  # Checkpoint timestamp
    parent_ts = Column(String(255), nullable=True)  # Parent checkpoint (for branching)

    # Checkpoint data - inline for small payloads
    checkpoint_data = Column(JSON, nullable=True)

    # Blob offload for large payloads (ARB Condition 3)
    blob_key = Column(String(500), nullable=True)  # S3/MinIO key if offloaded
    blob_size_bytes = Column(Integer, nullable=True)

    # Metadata
    step_number = Column(Integer, server_default='0')
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index('idx_checkpoint_thread', 'thread_id', 'thread_ts'),
        Index('idx_checkpoint_run', 'run_id', 'step_number'),
    )


class AgentEvalRun(Base):
    """
    TDAD (Test-Driven Agent Development) evaluation run.

    Tracks execution of the golden dataset against an agent version.
    Phase 1 requirement per ARB feedback.
    """
    __tablename__ = "agent_eval_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)

    # Timing
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Results
    total_cases = Column(Integer, server_default='0')
    passed_cases = Column(Integer, server_default='0')
    failed_cases = Column(Integer, server_default='0')
    pass_rate = Column(Float, server_default='0.0')
    total_cost_usd = Column(Float, server_default='0.0')
    results = Column(JSON, server_default='[]')  # Detailed per-case results

    # Trigger
    triggered_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        Index('idx_eval_agent', 'agent_id', 'started_at'),
        Index('idx_eval_tenant', 'tenant_id', 'started_at'),
    )
