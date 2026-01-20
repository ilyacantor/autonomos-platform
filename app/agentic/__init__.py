"""
Agentic Orchestration Platform

LangGraph-based agent execution with MCP tool integration.

Modules:
- checkpointer: Durable checkpoint storage with blob offload
- workflow: LangGraph workflow builder and executor
- mcp_client: MCP protocol client for tool execution
- mcp_servers: AOS-specific MCP servers (DCL, AAM)
- streaming: WebSocket event streaming
- eval: Test-Driven Agent Development (TDAD) framework
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
]
