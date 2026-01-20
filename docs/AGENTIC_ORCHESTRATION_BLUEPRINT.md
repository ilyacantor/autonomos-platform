# Agentic Orchestration Platform
## Senior Technical Blueprint v2.0

**Version**: 2.1 (Approved)
**Date**: 2026-01-20
**Status**: ✅ APPROVED FOR DEVELOPMENT
**Revision Note**: Incorporates Architecture Review Board feedback + Approval Conditions

---

## 1. Executive Summary

### 1.1 What Changed from v1.0

| Component | v1.0 (Rejected) | v2.0 (Revised) | Rationale |
|-----------|-----------------|----------------|-----------|
| **Agent Runtime** | Custom Python loop | **LangGraph** | Durable execution, checkpointing, time-travel debugging |
| **Tool Schema** | Proprietary `class Tool` | **Model Context Protocol (MCP)** | Ecosystem compatibility, 1000s of existing connectors |
| **NLP Gateway** | Intent Classifier → Router | **Reasoning Router (LLM)** | Handles compound tasks, no brittle keyword matching |
| **State Persistence** | Redis Streams | **PostgreSQL via LangGraph Checkpointer** | Crash recovery, durable execution guarantees |
| **Sandboxing** | Subprocess | **Firecracker MicroVMs / E2B** | Proper isolation |
| **Auth Model** | System-wide tokens | **On-Behalf-Of (OBO) flows** | User-scoped permissions |

### 1.2 Strategic Positioning

**The Moat is NOT the Runtime. The Moat is the Data.**

AOS's differentiation:
- **Deep Data Access**: Navigate complex enterprise data topology (DCL/AAM/AOD)
- **Semantic Understanding**: Know what "revenue" means across 5 different systems
- **Governance**: HITL controls for sensitive cross-system operations

What we **buy/integrate** (commodity):
- Agent execution (LangGraph)
- Tool protocol (MCP)
- LLM routing (AI Gateway)

What we **build** (differentiator):
- Introspective data tools that expose DCL/AAM/AOD to agents
- Semantic schema discovery
- Cross-system lineage tracking
- Enterprise governance controls

---

## 2. Revised Architecture

### 2.1 High-Level Architecture (v2.0)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              PRESENTATION LAYER                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │   Control       │  │   Agent         │  │   Time Travel               │  │
│  │   Center        │  │   Workbench     │  │   Debugger                  │  │
│  │   (Chat + Ops)  │  │   (Config/Test) │  │   (Replay/Rewind)           │  │
│  └────────┬────────┘  └────────┬────────┘  └──────────────┬──────────────┘  │
└───────────┼────────────────────┼─────────────────────────┼──────────────────┘
            │                    │                         │
            ▼                    ▼                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API GATEWAY LAYER                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  Auth (JWT+OBO) │ Rate Limit │ Tracing │ Audit │ Multi-Tenant              │
├─────────────────────────────────────────────────────────────────────────────┤
│  /api/v1/chat/*     /api/v1/agents/*     /api/v1/runs/*                     │
└─────────────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         REASONING LAYER (NEW)                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     AI GATEWAY (Portkey/Helicone)                    │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │    │
│  │  │   Router    │  │   Cache     │  │   Fallback  │  │   Metrics  │  │    │
│  │  │   (Haiku)   │  │   (Semantic)│  │   (Multi-LLM)│  │   (Cost)   │  │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     LANGGRAPH EXECUTION KERNEL                       │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │    │
│  │  │   State     │  │   Graph     │  │   Check-    │  │   Human    │  │    │
│  │  │   Machine   │  │   Compiler  │  │   pointer   │  │   Interrupt│  │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     MCP CLIENT (Tool Execution)                      │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │    │
│  │  │   Protocol  │  │   Server    │  │   Sandbox   │  │   Auth     │  │    │
│  │  │   Handler   │  │   Registry  │  │   (E2B)     │  │   (OBO)    │  │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    AOS DATA SERVICES (MCP SERVERS) ← THE MOAT                │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │   DCL Server    │  │   AAM Server    │  │   AOD Server                │  │
│  │   ───────────   │  │   ──────────    │  │   ──────────                │  │
│  │   • query_data  │  │   • list_conns  │  │   • discover_assets         │  │
│  │   • get_schema  │  │   • sync_now    │  │   • get_lineage             │  │
│  │   • explain_field│  │  • check_health│  │   • search_metadata         │  │
│  │   • trace_lineage│  │  • get_drift   │  │   • classify_sensitivity    │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA LAYER                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │   PostgreSQL    │  │   Redis         │  │   External                  │  │
│  │   ─────────     │  │   ─────         │  │   ────────                  │  │
│  │   • LangGraph   │  │   • Session     │  │   • Anthropic / OpenAI      │  │
│  │     Checkpoints │  │     Cache       │  │   • Enterprise Data Sources │  │
│  │   • Agent Config│  │   • Pub/Sub     │  │   • MCP Tool Servers        │  │
│  │   • Audit Trail │  │   • Locks       │  │                             │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Key Architectural Changes

#### From Custom Runtime → LangGraph

```python
# OLD (v1.0) - Fragile custom loop
class AgentExecutor:
    async def run(self, input: str):
        while not done:
            response = await self.llm.complete(messages)
            if response.tool_calls:
                results = await self.execute_tools(response.tool_calls)
            # BUG: What if we crash here? State is lost.

# NEW (v2.0) - LangGraph with durable checkpointing
from langgraph.graph import StateGraph
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = PostgresSaver.from_conn_string(DATABASE_URL)

workflow = StateGraph(AgentState)
workflow.add_node("reason", reasoning_node)
workflow.add_node("tools", tool_node)
workflow.add_node("human_review", human_interrupt_node)
workflow.add_conditional_edges("reason", route_decision)

app = workflow.compile(checkpointer=checkpointer, interrupt_before=["human_review"])

# Crash-safe: State persisted after every node
# Resume: app.stream(None, config={"thread_id": run_id})
```

#### From Proprietary Tools → MCP

```python
# OLD (v1.0) - Proprietary, isolated
class QueryDCLTool(Tool):
    name = "query_dcl"
    parameters = { ... }  # Custom schema

# NEW (v2.0) - MCP Server exposing DCL
from mcp.server import Server
from mcp.types import Tool, TextContent

server = Server("aos-dcl")

@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="query_dcl",
            description="Query unified data from the Data Connection Layer",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "entity": {"type": "string", "enum": ["accounts", "opportunities", "contacts"]}
                }
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "query_dcl":
        result = await dcl_service.query(arguments["query"], arguments.get("entity"))
        return [TextContent(type="text", text=json.dumps(result))]
```

#### From Intent Classifier → Reasoning Router

```python
# OLD (v1.0) - Brittle keyword matching
def classify_intent(query: str) -> Intent:
    if "show me" in query.lower():
        return Intent.QUERY_DATA
    elif "run" in query.lower():
        return Intent.EXECUTE_AGENT
    # Fails on: "Check the logs and if there's an error, file a Jira ticket"

# NEW (v2.0) - LLM-based reasoning router
async def route_request(query: str, available_tools: List[Tool]) -> RoutingDecision:
    """Use fast LLM to determine routing based on tool definitions."""
    response = await llm.complete(
        model="claude-haiku-3-5-20241022",
        messages=[{
            "role": "user",
            "content": f"""Given this user request and available tools, determine the execution plan.

User request: {query}

Available tools:
{format_tools(available_tools)}

Return a JSON execution plan with ordered steps."""
        }]
    )
    return parse_routing_decision(response)
```

---

## 3. Revised Data Model

### 3.1 LangGraph-Compatible State

```python
from typing import TypedDict, Annotated, Sequence
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    """State that flows through the LangGraph execution."""
    # Core conversation
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # Agent metadata
    agent_id: str
    tenant_id: str
    run_id: str

    # Execution context
    current_step: int
    max_steps: int
    cost_usd: float
    max_cost_usd: float

    # Tool results (for introspection)
    tool_results: list[dict]

    # Human-in-the-loop
    pending_approval: Optional[ApprovalRequest]
    approval_response: Optional[ApprovalResponse]

    # Final output
    final_answer: Optional[str]
    error: Optional[str]
```

### 3.2 Persistence Models (PostgreSQL)

```python
# These complement LangGraph's checkpoint storage

class Agent(Base):
    """Agent configuration (what to run)"""
    __tablename__ = "agents"

    id = Column(UUID, primary_key=True)
    tenant_id = Column(UUID, ForeignKey("tenants.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # LangGraph workflow definition
    graph_definition = Column(JSON)  # Serialized StateGraph

    # MCP servers this agent can access
    mcp_servers = Column(ARRAY(String))  # ["aos-dcl", "aos-aam", "slack"]

    # Guardrails
    max_steps = Column(Integer, default=20)
    max_cost_usd = Column(Numeric(10, 4), default=1.00)
    require_approval_for = Column(ARRAY(String))  # ["write_operations"]

    # Versioning
    version = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())
    created_by = Column(UUID, ForeignKey("users.id"))


class AgentRun(Base):
    """Execution record (links to LangGraph checkpoints)"""
    __tablename__ = "agent_runs"

    id = Column(UUID, primary_key=True)  # Same as LangGraph thread_id
    agent_id = Column(UUID, ForeignKey("agents.id"), nullable=False)
    tenant_id = Column(UUID, nullable=False)

    # Status tracking
    status = Column(String(20))  # pending, running, paused, completed, failed

    # Trigger context
    triggered_by = Column(UUID, ForeignKey("users.id"))
    trigger_type = Column(String(20))  # chat, api, schedule, webhook

    # Cost tracking
    tokens_input = Column(Integer, default=0)
    tokens_output = Column(Integer, default=0)
    cost_usd = Column(Numeric(10, 4), default=0)

    # Timing
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # Note: Actual execution state is in LangGraph checkpoints table


class Approval(Base):
    """Human-in-the-loop approval records"""
    __tablename__ = "approvals"

    id = Column(UUID, primary_key=True)
    run_id = Column(UUID, ForeignKey("agent_runs.id"), nullable=False)
    tenant_id = Column(UUID, nullable=False)

    # What needs approval
    action_type = Column(String(50))  # write_data, external_call, etc.
    action_details = Column(JSON)

    # State
    status = Column(String(20))  # pending, approved, rejected, timeout
    requested_at = Column(DateTime, server_default=func.now())
    responded_at = Column(DateTime)
    responded_by = Column(UUID, ForeignKey("users.id"))

    # For timeout handling
    expires_at = Column(DateTime)
    auto_action = Column(String(20))  # reject, approve, escalate
```

---

## 4. MCP Server Specifications (The Moat)

### 4.1 AOS-DCL Server

The Data Connection Layer exposed as an MCP server.

```python
# app/mcp_servers/dcl_server.py

from mcp.server import Server
from mcp.types import Tool, Resource, TextContent

server = Server("aos-dcl")

@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="query_data",
            description="Query unified business data. Supports natural language queries.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language query (e.g., 'top 10 accounts by revenue')"
                    },
                    "entity": {
                        "type": "string",
                        "enum": ["accounts", "opportunities", "contacts", "auto"],
                        "description": "Target entity or 'auto' to infer"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_schema",
            description="Get the schema for an entity including field descriptions and lineage",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity": {"type": "string"}
                },
                "required": ["entity"]
            }
        ),
        Tool(
            name="explain_field",
            description="Explain what a field means, its source, and how it's calculated",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity": {"type": "string"},
                    "field": {"type": "string"}
                },
                "required": ["entity", "field"]
            }
        ),
        Tool(
            name="trace_lineage",
            description="Trace data lineage from source systems through transformations",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity": {"type": "string"},
                    "field": {"type": "string"}
                },
                "required": ["entity"]
            }
        )
    ]

@server.list_resources()
async def list_resources():
    """Expose DCL entities as browsable resources"""
    return [
        Resource(uri="dcl://entities", name="Available Entities", description="List of queryable entities"),
        Resource(uri="dcl://accounts/schema", name="Accounts Schema", description="Account entity schema"),
        Resource(uri="dcl://opportunities/schema", name="Opportunities Schema", description="Opportunity entity schema"),
    ]
```

### 4.2 AOS-AAM Server

The Adaptive API Mesh exposed as an MCP server.

```python
# app/mcp_servers/aam_server.py

server = Server("aos-aam")

@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="list_connections",
            description="List all data source connections and their health status",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="get_connection_health",
            description="Get detailed health metrics for a specific connection",
            inputSchema={
                "type": "object",
                "properties": {
                    "connection_id": {"type": "string"}
                },
                "required": ["connection_id"]
            }
        ),
        Tool(
            name="trigger_sync",
            description="Trigger an immediate sync for a connection (requires approval)",
            inputSchema={
                "type": "object",
                "properties": {
                    "connection_id": {"type": "string"},
                    "full_sync": {"type": "boolean", "default": False}
                },
                "required": ["connection_id"]
            },
            # Custom extension for AOS
            _aos_requires_approval=True
        ),
        Tool(
            name="get_drift_report",
            description="Get schema drift detection report for a connection",
            inputSchema={
                "type": "object",
                "properties": {
                    "connection_id": {"type": "string"}
                },
                "required": ["connection_id"]
            }
        ),
        Tool(
            name="propose_drift_repair",
            description="Generate a repair proposal for detected schema drift",
            inputSchema={
                "type": "object",
                "properties": {
                    "drift_id": {"type": "string"}
                },
                "required": ["drift_id"]
            }
        )
    ]
```

### 4.3 AOS-AOD Server

The Asset & Observability Discovery exposed as an MCP server.

```python
# app/mcp_servers/aod_server.py

server = Server("aos-aod")

@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="discover_assets",
            description="Discover data assets matching criteria",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "asset_type": {"type": "string", "enum": ["table", "view", "api", "file", "all"]},
                    "source_system": {"type": "string"}
                }
            }
        ),
        Tool(
            name="get_asset_lineage",
            description="Get upstream and downstream lineage for an asset",
            inputSchema={
                "type": "object",
                "properties": {
                    "asset_id": {"type": "string"},
                    "depth": {"type": "integer", "default": 3}
                },
                "required": ["asset_id"]
            }
        ),
        Tool(
            name="classify_sensitivity",
            description="Get data sensitivity classification for an asset",
            inputSchema={
                "type": "object",
                "properties": {
                    "asset_id": {"type": "string"}
                },
                "required": ["asset_id"]
            }
        ),
        Tool(
            name="search_metadata",
            description="Search across all asset metadata",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "filters": {"type": "object"}
                },
                "required": ["query"]
            }
        )
    ]
```

---

## 5. Security Model (Revised)

### 5.1 On-Behalf-Of (OBO) Authentication

```python
class OBOTokenManager:
    """
    Manages On-Behalf-Of tokens for agent tool calls.
    Agents act with the permissions of the triggering user.
    """

    async def get_tool_token(
        self,
        user_token: str,
        target_service: str,
        scopes: List[str]
    ) -> str:
        """
        Exchange user token for service-specific OBO token.

        Flow:
        1. User authenticates to AOS (JWT)
        2. User triggers agent
        3. Agent needs to call DCL
        4. OBO manager exchanges user JWT for DCL-scoped token
        5. DCL validates token and applies user's permissions
        """
        # Validate original token
        user_claims = await self.validate_token(user_token)

        # Check user has permission to delegate to this service
        if target_service not in user_claims.get("delegatable_services", []):
            raise PermissionError(f"User cannot delegate to {target_service}")

        # Generate OBO token with reduced scope
        obo_token = await self.mint_obo_token(
            subject=user_claims["sub"],
            tenant_id=user_claims["tenant_id"],
            target_service=target_service,
            scopes=scopes,
            expires_in=300  # 5 minute lifetime
        )

        return obo_token
```

### 5.2 Sandboxed Tool Execution

```python
from e2b import Sandbox

class SecureMCPExecutor:
    """
    Execute MCP tool calls in isolated sandboxes.
    """

    async def execute_tool(
        self,
        server: str,
        tool: str,
        arguments: dict,
        context: ExecutionContext
    ) -> ToolResult:
        # Determine isolation level
        isolation = self.get_isolation_level(server, tool)

        if isolation == "sandbox":
            # Run in E2B sandbox
            async with Sandbox() as sandbox:
                result = await sandbox.run_python(
                    self.generate_tool_code(server, tool, arguments)
                )
                return ToolResult(output=result.stdout, error=result.stderr)

        elif isolation == "container":
            # Run in isolated container
            return await self.run_in_container(server, tool, arguments)

        else:
            # Trusted internal service (DCL, AAM, AOD)
            return await self.run_direct(server, tool, arguments, context)

    def get_isolation_level(self, server: str, tool: str) -> str:
        # Internal AOS services are trusted
        if server in ["aos-dcl", "aos-aam", "aos-aod"]:
            return "direct"

        # External MCP servers need sandboxing
        return "sandbox"
```

### 5.3 Security Layers (Revised)

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: Authentication (JWT)                               │
│  • User authenticates, receives JWT                          │
│  • JWT contains: user_id, tenant_id, roles, delegatable_svcs│
├─────────────────────────────────────────────────────────────┤
│  Layer 2: On-Behalf-Of Delegation                            │
│  • Agent acts with USER's permissions, not system perms      │
│  • OBO tokens are short-lived (5 min), service-scoped        │
│  • User must explicitly grant delegation rights              │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: Multi-Tenant Isolation                             │
│  • All data queries filtered by tenant_id                    │
│  • LangGraph checkpoints partitioned by tenant               │
│  • MCP servers validate tenant on every call                 │
├─────────────────────────────────────────────────────────────┤
│  Layer 4: Tool-Level Guardrails                              │
│  • Per-agent tool allowlists                                 │
│  • Approval requirements for sensitive tools                 │
│  • Cost limits enforced in LangGraph state                   │
├─────────────────────────────────────────────────────────────┤
│  Layer 5: Execution Isolation                                │
│  • External tools run in E2B sandboxes                       │
│  • Network policies restrict egress                          │
│  • Secrets injected at runtime, never in code                │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. Revised Implementation Roadmap

### Phase 1: Foundation + Evals (2 weeks)
**Goal**: Database + basic agent CRUD + evaluation baseline

| Task | Effort | Notes |
|------|--------|-------|
| Agent/AgentRun/Approval models | 2d | Keep simple |
| Database migrations | 1d | Alembic |
| Agent CRUD API | 2d | Standard REST |
| LangGraph checkpointer setup | 2d | PostgresSaver with blob offload |
| **Eval framework + Golden Dataset** | 2d | **TDAD: 50 baseline questions** |
| Basic tests | 1d | pytest |

**Deliverable**: Agents can be created and stored; LangGraph checkpointing works; Eval baseline established

### Phase 2: LangGraph + MCP Integration (2 weeks)
**Goal**: Agents can execute with real tools

| Task | Effort | Notes |
|------|--------|-------|
| LangGraph workflow builder | 3d | Compile agent config → StateGraph |
| MCP client integration | 2d | Connect to MCP servers |
| AOS-DCL MCP server | 2d | Expose existing DCL |
| AOS-AAM MCP server | 2d | Expose existing AAM |
| Run API + WebSocket streaming | 1d | Real-time updates |

**Deliverable**: Agent can query DCL via MCP, state survives crashes

### Phase 3: AI Gateway + Reasoning Router (1 week)
**Goal**: Smart request routing

| Task | Effort | Notes |
|------|--------|-------|
| AI Gateway setup (Portkey) | 1d | Routing, caching, fallbacks |
| Reasoning router implementation | 2d | Haiku-based dynamic routing |
| Semantic cache layer | 1d | Avoid redundant LLM calls |
| Cost tracking integration | 1d | Per-run cost in AgentRun |

**Deliverable**: Requests routed intelligently, costs tracked

### Phase 4: Deep Data Tools (3 weeks) ← THE MOAT
**Goal**: Introspective tools that understand the data

| Task | Effort | Notes |
|------|--------|-------|
| Schema introspection tool | 3d | Agent can discover what data exists |
| Semantic field explainer | 3d | "What does 'ARR' mean in this context?" |
| Cross-system lineage tracer | 4d | Track data from source to report |
| Natural language query translator | 3d | NL → SQL/API with context |
| AOS-AOD MCP server | 2d | Asset discovery integration |

**Deliverable**: Agent can navigate complex data topology intelligently

### Phase 5: Control Plane + Observability (3 weeks)
**Goal**: Production-ready management UI

| Task | Effort | Notes |
|------|--------|-------|
| Time-travel debugger UI | 4d | Rewind/replay agent runs |
| HITL approval queue UI | 3d | Approve/reject with context |
| Agent configuration UI | 3d | Visual workflow builder |
| Eval framework | 3d | Automated regression tests |
| Metrics dashboard | 2d | Cost, latency, success rates |

**Deliverable**: Full operational control over agents

---

## 7. Dependencies & Integration Points

### 7.1 New Dependencies

```toml
# pyproject.toml additions

[project.dependencies]
langgraph = ">=0.2.0"
langgraph-checkpoint-postgres = ">=0.2.0"
mcp = ">=1.0.0"  # Model Context Protocol SDK
portkey-ai = ">=1.0.0"  # AI Gateway (optional)
e2b = ">=0.17.0"  # Sandbox execution
```

### 7.2 External Services

| Service | Purpose | Required? |
|---------|---------|-----------|
| **Anthropic API** | Primary LLM | Yes |
| **OpenAI API** | Fallback LLM | Recommended |
| **Portkey.ai** | AI Gateway (routing, caching) | Optional |
| **E2B** | Sandbox execution | For external tools |

### 7.3 Existing AOS Services (Become MCP Servers)

| Service | Current State | MCP Exposure |
|---------|---------------|--------------|
| DCL | REST API | aos-dcl server |
| AAM | REST API + WebSocket | aos-aam server |
| AOD | External iframe | aos-aod server (if local) |

---

## 8. Risk Mitigation

| Risk | Mitigation |
|------|------------|
| **LangGraph learning curve** | Start with simple linear graphs, add complexity later |
| **MCP ecosystem immaturity** | Build AOS servers first, external later |
| **LLM costs** | Aggressive caching, Haiku for routing, hard limits |
| **Checkpoint storage growth** | TTL on old checkpoints, archive to cold storage |
| **OBO token complexity** | Start with simplified model, enhance later |

---

## 9. Success Metrics

### Phase 2 Complete When:
- [ ] Agent executes multi-step DCL query via MCP
- [ ] Crash during execution → resume works
- [ ] WebSocket streams steps in real-time

### Phase 4 Complete When:
- [ ] Agent can answer "What data do we have about customers?"
- [ ] Agent can explain field lineage
- [ ] Agent correctly handles ambiguous queries by asking clarifying questions

### Phase 5 Complete When:
- [ ] Admin can rewind failed agent to specific step
- [ ] Approval queue has < 5 min average response time
- [ ] Eval suite catches regressions before deploy

---

## 10. Appendix: Revised File Structure

```
app/
├── api/v1/
│   ├── agents.py              # Agent CRUD
│   ├── runs.py                # Run management
│   ├── approvals.py           # HITL approvals
│   └── chat.py                # Chat endpoint (replaces nlp_simple)
├── models/
│   ├── agent.py               # Agent, AgentRun
│   └── approval.py            # Approval
├── langgraph/
│   ├── graphs/
│   │   ├── base_agent.py      # Default agent graph
│   │   └── approval_graph.py  # Graph with HITL nodes
│   ├── nodes/
│   │   ├── reasoning.py       # LLM reasoning node
│   │   ├── tools.py           # MCP tool execution node
│   │   └── human.py           # Human interrupt node
│   ├── state.py               # AgentState definition
│   └── checkpointer.py        # PostgresSaver setup
├── mcp_servers/
│   ├── dcl_server.py          # aos-dcl MCP server
│   ├── aam_server.py          # aos-aam MCP server
│   └── aod_server.py          # aos-aod MCP server
├── mcp_client/
│   ├── client.py              # MCP client wrapper
│   ├── registry.py            # Server discovery
│   └── sandbox.py             # E2B integration
├── security/
│   ├── obo.py                 # On-Behalf-Of token manager
│   └── guardrails.py          # Cost/step limits
└── gateway/
    ├── router.py              # Reasoning router
    └── cache.py               # Semantic cache

frontend/src/
├── components/
│   ├── AgentWorkbench/        # Agent config UI
│   ├── RunViewer/             # Real-time run viewer
│   ├── TimeTravelDebugger/    # Rewind/replay UI
│   └── ApprovalQueue/         # HITL queue
└── pages/
    ├── AgentsPage.tsx
    └── ControlCenterPage.tsx  # Enhanced
```

---

## 11. Decision Log

| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| **LangGraph over custom** | Durable execution, checkpointing, community | Temporal (heavier), custom (fragile) |
| **MCP over proprietary** | Ecosystem compatibility, future-proof | Custom schema (isolated) |
| **PostgresSaver over Redis** | Durability, crash recovery | RedisSaver (volatile) |
| **E2B over subprocess** | Security isolation | Docker (overhead), subprocess (unsafe) |
| **OBO over system tokens** | Least privilege, audit trail | Shared secrets (security risk) |
| **Portkey over direct calls** | Routing, caching, observability | Direct (less control) |

---

## 12. ARB Approval Conditions (MANDATORY)

The Architecture Review Board approved this blueprint with **4 critical conditions** that must be implemented.

### 12.1 Condition 1: Token Refresh on Approval Resume

**The Trap**: Agent runs for 2 minutes, hits `human_approval` node. Human approves 3 days later. The OBO token (5-min lifetime) is dead. Agent crashes with `401 Unauthorized`.

**Required Implementation**:

```python
# In approval workflow handler
async def handle_approval_response(approval_id: str, approved_by: str):
    approval = await get_approval(approval_id)
    run = await get_agent_run(approval.run_id)

    # CRITICAL: Mint fresh OBO token for the resuming agent
    fresh_token = await obo_manager.mint_token_for_user(
        user_id=approved_by,  # Use approver's identity
        target_services=run.agent.mcp_servers,
        expires_in=300  # Fresh 5-minute token
    )

    # Inject fresh token into LangGraph state before resuming
    await update_run_state(run.id, {"obo_token": fresh_token})

    # Now safe to resume
    await resume_agent_run(run.id)
```

### 12.2 Condition 2: Metadata RAG (No Raw Schema Dumps)

**The Trap**: `get_schema` dumps 200-column table definition into prompt → 15k tokens → context explosion.

**Required Implementation**:

```python
# In aos-dcl MCP server
@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "get_schema":
        entity = arguments["entity"]
        search_hint = arguments.get("search_hint")  # Optional relevance filter

        if search_hint:
            # Metadata RAG: Return only relevant columns
            schema = await dcl_service.get_schema(entity)
            relevant_fields = await vector_search_fields(
                schema.fields,
                query=search_hint,
                top_k=20  # Max 20 most relevant fields
            )
            return format_schema(entity, relevant_fields)
        else:
            # Return summary, not full dump
            schema = await dcl_service.get_schema(entity)
            return format_schema_summary(entity, schema, max_fields=30)
```

**Tool Schema Update**:
```python
Tool(
    name="get_schema",
    description="Get schema for an entity. Use search_hint to filter to relevant fields.",
    inputSchema={
        "type": "object",
        "properties": {
            "entity": {"type": "string"},
            "search_hint": {
                "type": "string",
                "description": "Optional: filter to fields relevant to this topic (e.g., 'revenue')"
            }
        },
        "required": ["entity"]
    }
)
```

### 12.3 Condition 3: Checkpoint Blob Offload

**The Trap**: LangGraph saves entire state per step. 10MB tool output → 10MB per checkpoint → table bloat.

**Required Implementation**:

```python
from langgraph.checkpoint.postgres import PostgresSaver
import boto3  # or MinIO client

class BlobOffloadCheckpointer(PostgresSaver):
    """
    Custom checkpointer that offloads large artifacts to blob storage.
    """
    BLOB_THRESHOLD = 100_000  # 100KB

    def __init__(self, conn_string: str, blob_client):
        super().__init__.from_conn_string(conn_string)
        self.blob = blob_client

    async def put(self, config: dict, checkpoint: dict, metadata: dict):
        # Scan for large values and offload
        cleaned_checkpoint = await self._offload_blobs(checkpoint, config["thread_id"])
        return await super().put(config, cleaned_checkpoint, metadata)

    async def _offload_blobs(self, data: dict, thread_id: str) -> dict:
        """Recursively find and offload large values."""
        result = {}
        for key, value in data.items():
            if isinstance(value, (str, bytes)) and len(value) > self.BLOB_THRESHOLD:
                # Offload to blob storage
                blob_key = f"checkpoints/{thread_id}/{key}_{uuid4()}"
                await self.blob.put_object(blob_key, value)
                result[key] = {"__blob_ref__": blob_key}
            elif isinstance(value, dict):
                result[key] = await self._offload_blobs(value, thread_id)
            else:
                result[key] = value
        return result

    async def get(self, config: dict):
        checkpoint = await super().get(config)
        return await self._hydrate_blobs(checkpoint)

    async def _hydrate_blobs(self, data: dict) -> dict:
        """Recursively hydrate blob references."""
        # ... inverse of _offload_blobs
```

### 12.4 Condition 4: Self-Hosted Sandbox Alternative

**The Trap**: E2B is SaaS. Sovereign customers cannot egress data to 3rd-party.

**Required Implementation**:

```python
from abc import ABC, abstractmethod

class SandboxBackend(ABC):
    """Abstract sandbox interface supporting multiple backends."""

    @abstractmethod
    async def execute(self, code: str, timeout: int = 30) -> ExecutionResult:
        pass

class E2BSandbox(SandboxBackend):
    """Cloud-hosted E2B sandbox (default)."""
    async def execute(self, code: str, timeout: int = 30) -> ExecutionResult:
        async with Sandbox() as sandbox:
            return await sandbox.run_python(code, timeout=timeout)

class FirecrackerSandbox(SandboxBackend):
    """Self-hosted Firecracker microVM sandbox."""
    def __init__(self, firecracker_endpoint: str):
        self.endpoint = firecracker_endpoint

    async def execute(self, code: str, timeout: int = 30) -> ExecutionResult:
        # Launch microVM, execute code, tear down
        async with aiohttp.ClientSession() as session:
            resp = await session.post(
                f"{self.endpoint}/execute",
                json={"code": code, "timeout": timeout}
            )
            return ExecutionResult(**await resp.json())

# Configuration-driven selection
def get_sandbox_backend() -> SandboxBackend:
    backend = os.getenv("SANDBOX_BACKEND", "e2b")
    if backend == "firecracker":
        return FirecrackerSandbox(os.getenv("FIRECRACKER_ENDPOINT"))
    return E2BSandbox()
```

---

## 13. Test-Driven Agent Development (TDAD)

### 13.1 Golden Dataset Requirements

Before Phase 3 (Reasoning Router), establish a baseline of **50 Golden Questions**:

```yaml
# evals/golden_questions.yaml
questions:
  - id: "revenue_q1"
    query: "What was our total revenue in Q3 2025?"
    expected_tools: ["query_dcl"]
    expected_entity: "opportunities"
    success_criteria: "Returns numeric value, cites source"

  - id: "churn_analysis"
    query: "Show me customers at risk of churning"
    expected_tools: ["query_dcl", "get_schema"]
    expected_entity: "accounts"
    success_criteria: "Returns list with churn indicators"

  - id: "compound_task"
    query: "Check if Salesforce sync is healthy, and if not, show me the drift report"
    expected_tools: ["get_connection_health", "get_drift_report"]
    success_criteria: "Conditionally calls drift report only if unhealthy"

  # ... 47 more questions covering:
  # - Simple queries (20)
  # - Multi-step tasks (15)
  # - Approval-required actions (10)
  # - Error handling (5)
```

### 13.2 Eval Runner

```python
# evals/runner.py
async def run_eval_suite(agent_id: str, golden_path: str = "evals/golden_questions.yaml"):
    """Run golden questions against agent and report results."""
    golden = yaml.safe_load(open(golden_path))
    results = []

    for question in golden["questions"]:
        run = await execute_agent(agent_id, question["query"])
        result = evaluate_run(run, question)
        results.append(result)

    return EvalReport(
        total=len(results),
        passed=sum(1 for r in results if r.passed),
        failed=[r for r in results if not r.passed],
        timestamp=datetime.utcnow()
    )
```

---

**APPROVED BY**: Architecture Review Board
**DATE**: 2026-01-20
**NEXT STEP**: Begin Phase 1 Implementation
