"""
Agent models - Agentic Orchestration (Phase 1).

Includes agent configuration, execution tracking, approvals, checkpoints, and evaluation.
"""
from app.models.base import (
    uuid, Column, String, JSON, DateTime, Integer, Float, ForeignKey, func, Index, UUID, relationship, Base
)


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
