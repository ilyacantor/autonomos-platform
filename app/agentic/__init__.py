"""
Agentic Orchestration Platform (AOA)

LangGraph-based agent execution with MCP tool integration.

Core Modules:
- checkpointer: Durable checkpoint storage with blob offload
- workflow: LangGraph workflow builder and executor
- mcp_client: MCP protocol client for tool execution
- mcp_servers: AOS-specific MCP servers (DCL, AAM, AOD)
- gateway: AI Gateway with multi-provider support
- deep_data: Semantic field explainer and lineage tracer
- streaming: WebSocket event streaming
- eval: Test-Driven Agent Development (TDAD) framework

AOA Modules (RACI Components):
- registry: Agent discovery, inventory, and metadata management
- lifecycle: Agent health monitoring, versioning, and onboarding
- approval: Human-in-the-loop workflows and override tracking
- coordination: Multi-agent orchestration and conflict resolution
- observability: Traces, metrics, and vitals aggregation
- governance: Policy enforcement, autonomy bounds, and budget control
"""

# Checkpointer
from app.agentic.checkpointer import (
    AOSCheckpointer,
    BlobStore,
    LocalBlobStore,
    S3BlobStore,
    create_checkpointer,
)

# Workflow
from app.agentic.workflow import (
    WorkflowBuilder,
    WorkflowConfig,
    AgentWorkflow,
    ToolDefinition,
    AgentState,
)

# MCP Client
from app.agentic.mcp_client import (
    MCPClient,
    MCPClientPool,
    MCPServerConfig,
    MCPTool,
    MCPToolResult,
    MCPTransport,
    MCPAuthType,
    get_mcp_client_pool,
)

# MCP Servers
from app.agentic.mcp_servers import (
    DCLMCPServer,
    DCL_TOOLS,
    AAMMCPServer,
    AAM_TOOLS,
    AODMCPServer,
    AOD_TOOLS,
)

# Streaming
from app.agentic.streaming import (
    StreamManager,
    StreamEvent,
    EventType,
    get_stream_manager,
    create_run_started_event,
    create_run_completed_event,
    create_run_failed_event,
    create_tool_call_event,
    create_tool_result_event,
    create_approval_required_event,
)

# Evaluation
from app.agentic.eval import (
    EvalRunner,
    EvalConfig,
    GOLDEN_DATASET,
    load_golden_dataset,
)

# Gateway
from app.agentic.gateway import (
    AIGateway,
    LLMResponse,
    ReasoningRouter,
    RoutingPlan,
    SemanticCache,
    CostTracker,
    get_ai_gateway,
    get_reasoning_router,
    get_cost_tracker,
)

# Deep Data Tools
from app.agentic.deep_data import (
    SemanticFieldExplainer,
    FieldExplanation,
    CrossSystemLineageTracer,
    LineageGraph,
    LineageNode,
    LineageEdge,
)

# Agent Registry
from app.agentic.registry import (
    AgentRecord,
    AgentMetadata,
    AgentOwnership,
    TrustTier,
    AgentDomain,
    AgentStatus,
    AgentInventory,
    InventoryFilter,
    InventoryStats,
    get_agent_inventory,
    OwnershipManager,
    OwnershipTransfer,
    get_ownership_manager,
)

# Agent Lifecycle
from app.agentic.lifecycle import (
    HealthCheck,
    HealthStatus,
    AgentVersion,
    VersionStatus,
    AgentConfig,
    ConfigValidation,
    HealthMonitor,
    HealthCheckResult,
    get_health_monitor,
    VersionManager,
    VersionTransition,
    get_version_manager,
    OnboardingWorkflow,
    OnboardingStep,
    OnboardingStatus,
    get_onboarding_workflow,
)

# Approval Workflows
from app.agentic.approval import (
    ApprovalRequest,
    ApprovalDecision,
    ApprovalStatus,
    ApprovalPriority,
    ApprovalType,
    EscalationLevel,
    Override,
    ApprovalWorkflow,
    ApprovalRoute,
    get_approval_workflow,
    OverrideManager,
    OverridePolicy,
    get_override_manager,
)

# Coordination
from app.agentic.coordination import (
    CoordinationTask,
    TaskResult,
    ConflictType,
    ResolutionStrategy,
    WorkflowPattern,
    Arbitrator,
    Conflict,
    Resolution,
    get_arbitrator,
    MultiAgentOrchestrator,
    OrchestrationPlan,
    AgentAssignment,
    get_orchestrator,
)

# Observability
from app.agentic.observability import (
    Trace,
    Span,
    SpanKind,
    Metric,
    MetricType,
    Vital,
    VitalStatus,
    Tracer,
    TraceContext,
    get_tracer,
    MetricsCollector,
    MetricsSummary,
    get_metrics_collector,
    VitalsMonitor,
    VitalsSnapshot,
    get_vitals_monitor,
)

# Governance
from app.agentic.governance import (
    Policy,
    PolicyRule,
    PolicyDecision,
    PolicyScope,
    RuleAction,
    AutonomyLevel,
    EscalationTrigger,
    PolicyEngine,
    PolicyEvaluator,
    get_policy_engine,
    AutonomyManager,
    AutonomyBounds,
    get_autonomy_manager,
    BudgetEnforcer,
    Budget,
    BudgetAlert,
    get_budget_enforcer,
)

__all__ = [
    # Checkpointer
    'AOSCheckpointer',
    'BlobStore',
    'LocalBlobStore',
    'S3BlobStore',
    'create_checkpointer',
    # Workflow
    'WorkflowBuilder',
    'WorkflowConfig',
    'AgentWorkflow',
    'ToolDefinition',
    'AgentState',
    # MCP Client
    'MCPClient',
    'MCPClientPool',
    'MCPServerConfig',
    'MCPTool',
    'MCPToolResult',
    'MCPTransport',
    'MCPAuthType',
    'get_mcp_client_pool',
    # MCP Servers
    'DCLMCPServer',
    'DCL_TOOLS',
    'AAMMCPServer',
    'AAM_TOOLS',
    'AODMCPServer',
    'AOD_TOOLS',
    # Streaming
    'StreamManager',
    'StreamEvent',
    'EventType',
    'get_stream_manager',
    'create_run_started_event',
    'create_run_completed_event',
    'create_run_failed_event',
    'create_tool_call_event',
    'create_tool_result_event',
    'create_approval_required_event',
    # Evaluation
    'EvalRunner',
    'EvalConfig',
    'GOLDEN_DATASET',
    'load_golden_dataset',
    # Gateway
    'AIGateway',
    'LLMResponse',
    'ReasoningRouter',
    'RoutingPlan',
    'SemanticCache',
    'CostTracker',
    'get_ai_gateway',
    'get_reasoning_router',
    'get_cost_tracker',
    # Deep Data Tools
    'SemanticFieldExplainer',
    'FieldExplanation',
    'CrossSystemLineageTracer',
    'LineageGraph',
    'LineageNode',
    'LineageEdge',
    # Agent Registry
    'AgentRecord',
    'AgentMetadata',
    'AgentOwnership',
    'TrustTier',
    'AgentDomain',
    'AgentStatus',
    'AgentInventory',
    'InventoryFilter',
    'InventoryStats',
    'get_agent_inventory',
    'OwnershipManager',
    'OwnershipTransfer',
    'get_ownership_manager',
    # Agent Lifecycle
    'HealthCheck',
    'HealthStatus',
    'AgentVersion',
    'VersionStatus',
    'AgentConfig',
    'ConfigValidation',
    'HealthMonitor',
    'HealthCheckResult',
    'get_health_monitor',
    'VersionManager',
    'VersionTransition',
    'get_version_manager',
    'OnboardingWorkflow',
    'OnboardingStep',
    'OnboardingStatus',
    'get_onboarding_workflow',
    # Approval Workflows
    'ApprovalRequest',
    'ApprovalDecision',
    'ApprovalStatus',
    'ApprovalPriority',
    'ApprovalType',
    'EscalationLevel',
    'Override',
    'ApprovalWorkflow',
    'ApprovalRoute',
    'get_approval_workflow',
    'OverrideManager',
    'OverridePolicy',
    'get_override_manager',
    # Coordination
    'CoordinationTask',
    'TaskResult',
    'ConflictType',
    'ResolutionStrategy',
    'WorkflowPattern',
    'Arbitrator',
    'Conflict',
    'Resolution',
    'get_arbitrator',
    'MultiAgentOrchestrator',
    'OrchestrationPlan',
    'AgentAssignment',
    'get_orchestrator',
    # Observability
    'Trace',
    'Span',
    'SpanKind',
    'Metric',
    'MetricType',
    'Vital',
    'VitalStatus',
    'Tracer',
    'TraceContext',
    'get_tracer',
    'MetricsCollector',
    'MetricsSummary',
    'get_metrics_collector',
    'VitalsMonitor',
    'VitalsSnapshot',
    'get_vitals_monitor',
    # Governance
    'Policy',
    'PolicyRule',
    'PolicyDecision',
    'PolicyScope',
    'RuleAction',
    'AutonomyLevel',
    'EscalationTrigger',
    'PolicyEngine',
    'PolicyEvaluator',
    'get_policy_engine',
    'AutonomyManager',
    'AutonomyBounds',
    'get_autonomy_manager',
    'BudgetEnforcer',
    'Budget',
    'BudgetAlert',
    'get_budget_enforcer',
]
