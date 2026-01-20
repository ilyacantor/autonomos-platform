"""
Agent Orchestration Schemas

Pydantic schemas for the Agentic Orchestration Platform:
- Agent configuration CRUD
- Agent run execution
- Human-in-the-loop approvals
- WebSocket streaming events
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID
from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================

class AgentType(str, Enum):
    """Types of agents supported by the platform."""
    GENERAL = "general"
    DATA_ANALYST = "data_analyst"
    CONNECTOR = "connector"
    DISCOVERY = "discovery"
    CUSTOM = "custom"


class AgentStatus(str, Enum):
    """Agent configuration status."""
    ACTIVE = "active"
    DISABLED = "disabled"
    ARCHIVED = "archived"


class RunStatus(str, Enum):
    """Agent run execution status."""
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class TriggerType(str, Enum):
    """How the agent run was triggered."""
    API = "api"
    WEBHOOK = "webhook"
    SCHEDULE = "schedule"
    MANUAL = "manual"


class ApprovalStatus(str, Enum):
    """Human-in-the-loop approval status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ApprovalAutoAction(str, Enum):
    """What happens when approval times out."""
    REJECT = "reject"
    APPROVE = "approve"
    ESCALATE = "escalate"


class StreamEventType(str, Enum):
    """WebSocket stream event types."""
    RUN_STARTED = "run_started"
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    APPROVAL_REQUIRED = "approval_required"
    APPROVAL_RESOLVED = "approval_resolved"
    TOKEN_REFRESHED = "token_refreshed"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"
    ERROR = "error"


# =============================================================================
# MCP Server Configuration
# =============================================================================

class MCPServerConfig(BaseModel):
    """Configuration for an MCP server connection."""
    name: str = Field(..., description="Unique name for this MCP server")
    url: str = Field(..., description="MCP server endpoint URL")
    transport: str = Field(default="stdio", description="Transport: stdio, http, websocket")
    enabled: bool = Field(default=True)
    auth_type: Optional[str] = Field(default=None, description="Auth type: bearer, api_key, oauth")
    timeout_ms: int = Field(default=30000, ge=1000, le=300000)


# =============================================================================
# Agent Configuration Schemas
# =============================================================================

class AgentBase(BaseModel):
    """Base agent configuration fields."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    agent_type: AgentType = Field(default=AgentType.GENERAL)
    system_prompt: Optional[str] = Field(default=None, max_length=50000)
    model: str = Field(default="claude-sonnet-4-20250514", max_length=100)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=100, le=32000)
    max_steps: int = Field(default=20, ge=1, le=100)
    max_cost_usd: float = Field(default=1.0, ge=0.01, le=100.0)


class AgentCreate(AgentBase):
    """Schema for creating a new agent."""
    graph_definition: Optional[dict[str, Any]] = Field(
        default=None,
        description="LangGraph workflow definition (optional for simple agents)"
    )
    mcp_servers: list[MCPServerConfig] = Field(
        default_factory=list,
        description="MCP servers this agent can access"
    )
    require_approval_for: list[str] = Field(
        default_factory=list,
        description="Tool patterns requiring human approval (glob patterns)"
    )
    forbidden_actions: list[str] = Field(
        default_factory=list,
        description="Tools/actions this agent cannot use"
    )


class AgentUpdate(BaseModel):
    """Schema for updating an existing agent (all fields optional)."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    agent_type: Optional[AgentType] = None
    graph_definition: Optional[dict[str, Any]] = None
    system_prompt: Optional[str] = Field(default=None, max_length=50000)
    mcp_servers: Optional[list[MCPServerConfig]] = None
    model: Optional[str] = Field(default=None, max_length=100)
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=100, le=32000)
    max_steps: Optional[int] = Field(default=None, ge=1, le=100)
    max_cost_usd: Optional[float] = Field(default=None, ge=0.01, le=100.0)
    require_approval_for: Optional[list[str]] = None
    forbidden_actions: Optional[list[str]] = None
    status: Optional[AgentStatus] = None


class AgentResponse(AgentBase):
    """Agent response with all fields."""
    id: UUID
    tenant_id: UUID
    graph_definition: Optional[dict[str, Any]] = None
    mcp_servers: list[MCPServerConfig] = Field(default_factory=list)
    require_approval_for: list[str] = Field(default_factory=list)
    forbidden_actions: list[str] = Field(default_factory=list)
    version: int
    status: AgentStatus
    created_at: datetime
    created_by: Optional[UUID] = None
    updated_at: datetime

    class Config:
        from_attributes = True


class AgentListResponse(BaseModel):
    """Paginated list of agents."""
    items: list[AgentResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


# =============================================================================
# Agent Run Schemas
# =============================================================================

class AgentRunCreate(BaseModel):
    """Schema for starting a new agent run."""
    input: str = Field(..., min_length=1, max_length=50000, description="User input/query")
    context: Optional[dict[str, Any]] = Field(
        default=None,
        description="Additional context for the run"
    )
    stream: bool = Field(default=True, description="Whether to stream events via WebSocket")
    trigger_type: TriggerType = Field(default=TriggerType.API)


class AgentRunResponse(BaseModel):
    """Agent run response."""
    id: UUID
    agent_id: UUID
    tenant_id: UUID
    status: RunStatus
    input_data: Optional[dict[str, Any]] = None
    output_data: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    triggered_by: Optional[UUID] = None
    trigger_type: TriggerType
    tokens_input: int = 0
    tokens_output: int = 0
    cost_usd: float = 0.0
    steps_executed: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AgentRunListResponse(BaseModel):
    """Paginated list of agent runs."""
    items: list[AgentRunResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


# =============================================================================
# Approval Schemas
# =============================================================================

class AgentApprovalResponse(BaseModel):
    """Approval request response."""
    id: UUID
    run_id: UUID
    tenant_id: UUID
    action_type: str
    action_details: dict[str, Any]
    step_number: int
    status: ApprovalStatus
    requested_at: datetime
    expires_at: datetime
    responded_at: Optional[datetime] = None
    responded_by: Optional[UUID] = None
    approval_notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    auto_action: ApprovalAutoAction

    class Config:
        from_attributes = True


class ApprovalAction(BaseModel):
    """Schema for approving or rejecting an action."""
    approved: bool = Field(..., description="True to approve, False to reject")
    notes: Optional[str] = Field(default=None, max_length=2000)
    rejection_reason: Optional[str] = Field(default=None, max_length=2000)


class PendingApprovalsResponse(BaseModel):
    """List of pending approvals for a tenant."""
    items: list[AgentApprovalResponse]
    total: int


# =============================================================================
# WebSocket Streaming Schemas
# =============================================================================

class StreamEvent(BaseModel):
    """Base WebSocket stream event."""
    event_type: StreamEventType
    run_id: UUID
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: dict[str, Any] = Field(default_factory=dict)


class ToolCallEvent(StreamEvent):
    """Event emitted when agent calls a tool."""
    event_type: StreamEventType = StreamEventType.TOOL_CALL
    tool_name: str
    tool_server: str
    arguments: dict[str, Any]
    step_number: int


class ToolResultEvent(StreamEvent):
    """Event emitted when tool returns result."""
    event_type: StreamEventType = StreamEventType.TOOL_RESULT
    tool_name: str
    result: Any
    duration_ms: int
    step_number: int


class ApprovalRequiredEvent(StreamEvent):
    """Event emitted when human approval is needed."""
    event_type: StreamEventType = StreamEventType.APPROVAL_REQUIRED
    approval_id: UUID
    action_type: str
    action_details: dict[str, Any]
    expires_at: datetime
    step_number: int


class RunCompletedEvent(StreamEvent):
    """Event emitted when run completes successfully."""
    event_type: StreamEventType = StreamEventType.RUN_COMPLETED
    output: Any
    tokens_input: int
    tokens_output: int
    cost_usd: float
    steps_executed: int
    duration_ms: int


class RunFailedEvent(StreamEvent):
    """Event emitted when run fails."""
    event_type: StreamEventType = StreamEventType.RUN_FAILED
    error: str
    error_type: str
    step_number: int


# =============================================================================
# Evaluation Schemas (TDAD - Test-Driven Agent Development)
# =============================================================================

class EvalTestCase(BaseModel):
    """A single evaluation test case from the golden dataset."""
    id: str = Field(..., description="Unique test case ID")
    input: str = Field(..., description="User query/input")
    expected_tools: list[str] = Field(
        default_factory=list,
        description="Expected tool calls (in order)"
    )
    expected_output_contains: list[str] = Field(
        default_factory=list,
        description="Strings that should appear in output"
    )
    max_steps: int = Field(default=10, description="Max steps allowed")
    max_cost_usd: float = Field(default=0.50, description="Max cost allowed")
    category: str = Field(default="general", description="Test category")
    difficulty: str = Field(default="medium", description="easy, medium, hard")


class EvalResult(BaseModel):
    """Result of running a single eval test case."""
    test_case_id: str
    passed: bool
    actual_tools: list[str]
    actual_output: Optional[str] = None
    steps_used: int
    cost_usd: float
    duration_ms: int
    error: Optional[str] = None
    failure_reason: Optional[str] = None


class EvalRunResponse(BaseModel):
    """Summary of an evaluation run."""
    id: UUID
    agent_id: UUID
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_cases: int
    passed_cases: int
    failed_cases: int
    pass_rate: float
    total_cost_usd: float
    results: list[EvalResult]
