# Agentic Orchestration Platform
## Senior Technical Blueprint

**Version**: 1.0
**Date**: 2026-01-20
**Status**: PROPOSAL
**Author**: Architecture Review

---

## 1. Executive Summary

### 1.1 Vision
Transform the existing AutonomOS platform into an **Agentic Orchestration Platform** that provides:
- Natural language interface for controlling all AOS applications
- Centralized control center for agent lifecycle management
- Real-time observability into agent operations
- Human-in-the-loop approval workflows

### 1.2 Strategic Context
The platform already has:
- Production-grade multi-tenant infrastructure
- Event-driven architecture (AAM event bus)
- Real-time telemetry (WebSocket, Redis Streams)
- Authentication and authorization

What's missing:
- Agent abstraction layer
- LLM-powered NLP gateway
- Workflow orchestration engine
- Agent execution runtime

### 1.3 Build vs. Buy Decision

| Component | Recommendation | Rationale |
|-----------|---------------|-----------|
| Agent Runtime | **Build** | Core differentiator, needs tight integration |
| LLM Integration | **Buy** (OpenAI/Anthropic SDK) | Commodity, fast iteration |
| Workflow Engine | **Build** (lightweight) | Existing event bus provides foundation |
| Observability | **Extend** existing telemetry | Already have Redis Streams + WebSocket |
| Vector Store | **Buy** (pgvector already installed) | Commodity |

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              PRESENTATION LAYER                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │   Control       │  │   Agent         │  │   Embedded Apps             │  │
│  │   Center        │  │   Workbench     │  │   (AOD/AAM/DCL iframes)     │  │
│  │   (NLP Chat)    │  │   (CRUD/Monitor)│  │                             │  │
│  └────────┬────────┘  └────────┬────────┘  └──────────────┬──────────────┘  │
└───────────┼────────────────────┼─────────────────────────┼──────────────────┘
            │                    │                         │
            ▼                    ▼                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API GATEWAY LAYER                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │
│  │  Auth    │ │  Rate    │ │ Tracing  │ │  Audit   │ │  Multi-Tenant    │   │
│  │  (JWT)   │ │  Limit   │ │  (UUID)  │ │  Log     │ │  Isolation       │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────────────┘   │
├─────────────────────────────────────────────────────────────────────────────┤
│  /api/v1/nlp/*     /api/v1/agents/*     /api/v1/workflows/*                 │
│  /api/v1/aam/*     /api/v1/dcl/*        /api/v1/aod/*                       │
└─────────────────────────────────────────────────────────────────────────────┘
            │                    │                         │
            ▼                    ▼                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ORCHESTRATION LAYER                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        NLP GATEWAY                                   │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │    │
│  │  │   Intent    │  │   Entity    │  │   Context   │  │   Tool     │  │    │
│  │  │   Classifier│  │   Extractor │  │   Manager   │  │   Router   │  │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      AGENT ORCHESTRATOR                              │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │    │
│  │  │   Agent     │  │   Workflow  │  │   HITL      │  │   Event    │  │    │
│  │  │   Registry  │  │   Engine    │  │   Queue     │  │   Bus      │  │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      AGENT EXECUTION RUNTIME                         │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │    │
│  │  │   LLM       │  │   Tool      │  │   Memory    │  │   Sandbox  │  │    │
│  │  │   Client    │  │   Executor  │  │   Store     │  │   Runner   │  │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
            │                    │                         │
            ▼                    ▼                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA LAYER                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │   PostgreSQL    │  │   Redis         │  │   External Services         │  │
│  │   ─────────     │  │   ─────         │  │   ────────────────          │  │
│  │   • Agents      │  │   • Sessions    │  │   • OpenAI / Anthropic      │  │
│  │   • Runs        │  │   • Cache       │  │   • AOD Service             │  │
│  │   • Steps       │  │   • Pub/Sub     │  │   • AAM Connectors          │  │
│  │   • Workflows   │  │   • Streams     │  │   • DCL Endpoints           │  │
│  │   • Approvals   │  │   • Locks       │  │   • Vector DB (pgvector)    │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Responsibilities

| Component | Responsibility | State | Dependencies |
|-----------|---------------|-------|--------------|
| **NLP Gateway** | Parse NL → structured intent | Stateless | LLM Client, Context Manager |
| **Agent Registry** | CRUD agents, versioning | PostgreSQL | None |
| **Workflow Engine** | Execute multi-step flows | Redis + PG | Agent Registry, Event Bus |
| **HITL Queue** | Human approval workflows | PostgreSQL | WebSocket (notifications) |
| **Agent Runtime** | Execute single agent run | Redis (session) | LLM Client, Tool Executor |
| **Tool Executor** | Run tools safely | Stateless | Sandboxed subprocess |
| **Event Bus** | Async messaging | Redis Streams | None |

---

## 3. Data Model

### 3.1 Core Entities

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│     Tenant      │       │      User       │       │     Agent       │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ id (PK)         │──┐    │ id (PK)         │       │ id (PK)         │
│ name            │  │    │ tenant_id (FK)  │──┐    │ tenant_id (FK)  │──┐
│ created_at      │  │    │ email           │  │    │ name            │  │
└─────────────────┘  │    │ role            │  │    │ description     │  │
                     │    └─────────────────┘  │    │ agent_type      │  │
                     │                         │    │ config (JSON)   │  │
                     │                         │    │ status          │  │
                     └─────────────────────────┴────│ version         │  │
                                                    │ created_by (FK) │──┘
                                                    └────────┬────────┘
                                                             │
                     ┌───────────────────────────────────────┘
                     │
                     ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│   AgentRun      │       │   AgentStep     │       │   AgentTool     │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ id (PK)         │──┐    │ id (PK)         │       │ id (PK)         │
│ agent_id (FK)   │  │    │ run_id (FK)     │───────│ agent_id (FK)   │
│ tenant_id (FK)  │  │    │ sequence        │       │ name            │
│ status          │  │    │ step_type       │       │ description     │
│ input (JSON)    │  │    │ input (JSON)    │       │ schema (JSON)   │
│ output (JSON)   │  │    │ output (JSON)   │       │ handler         │
│ error           │  │    │ tokens_used     │       │ requires_approval│
│ started_at      │  │    │ latency_ms      │       └─────────────────┘
│ completed_at    │  │    │ created_at      │
│ tokens_total    │  └────└─────────────────┘
│ cost_usd        │
│ triggered_by    │       ┌─────────────────┐
└─────────────────┘       │  Approval       │
                          ├─────────────────┤
                          │ id (PK)         │
                          │ run_id (FK)     │
                          │ step_id (FK)    │
                          │ status          │
                          │ requested_at    │
                          │ responded_at    │
                          │ responded_by    │
                          │ notes           │
                          └─────────────────┘
```

### 3.2 Agent Configuration Schema

```json
{
  "agent_config": {
    "model": "claude-sonnet-4-20250514",
    "temperature": 0.7,
    "max_tokens": 4096,
    "system_prompt": "You are a data operations assistant...",
    "tools": ["query_dcl", "invoke_aam", "search_aod"],
    "guardrails": {
      "max_steps": 20,
      "max_cost_usd": 1.00,
      "require_approval_for": ["write_operations", "external_calls"],
      "forbidden_actions": ["delete_data", "modify_schema"]
    },
    "memory": {
      "type": "conversation",
      "max_messages": 50,
      "summarize_after": 20
    }
  }
}
```

### 3.3 Step Types

| Type | Description | Example |
|------|-------------|---------|
| `think` | LLM reasoning | "I need to query sales data first..." |
| `tool_call` | Tool invocation request | `{ tool: "query_dcl", params: {...} }` |
| `tool_result` | Tool execution result | `{ success: true, data: [...] }` |
| `approval_request` | HITL approval needed | `{ action: "write", awaiting: true }` |
| `approval_response` | Human decision | `{ approved: true, by: "user@..." }` |
| `output` | Final response | "Here are the sales figures..." |
| `error` | Execution error | `{ error: "Rate limit exceeded" }` |

---

## 4. API Design

### 4.1 NLP Gateway API

```yaml
POST /api/v1/nlp/chat
  Description: Process natural language query
  Auth: JWT required
  Request:
    content: string          # User message
    session_id?: string      # Continue existing session
    persona?: string         # CTO | CRO | COO | CFO
    stream?: boolean         # SSE streaming response
  Response:
    session_id: string
    message: string          # Assistant response
    actions_taken: Action[]  # Tools invoked
    suggestions: string[]    # Follow-up suggestions

POST /api/v1/nlp/chat/stream
  Description: Streaming chat (SSE)
  Response: text/event-stream
    event: token | tool_start | tool_end | done
    data: { content: string, ... }
```

### 4.2 Agent Management API

```yaml
# Agent CRUD
GET    /api/v1/agents                    # List agents
POST   /api/v1/agents                    # Create agent
GET    /api/v1/agents/{id}               # Get agent
PATCH  /api/v1/agents/{id}               # Update agent
DELETE /api/v1/agents/{id}               # Delete agent

# Agent Execution
POST   /api/v1/agents/{id}/run           # Start new run
GET    /api/v1/agents/{id}/runs          # List runs
GET    /api/v1/agents/{id}/runs/{run_id} # Get run details
GET    /api/v1/agents/{id}/runs/{run_id}/steps  # Get steps
POST   /api/v1/agents/{id}/runs/{run_id}/cancel # Cancel run

# Real-time
WS     /api/v1/agents/ws/{run_id}        # Stream run events
```

### 4.3 Approval Workflow API

```yaml
GET    /api/v1/approvals                 # List pending approvals
GET    /api/v1/approvals/{id}            # Get approval details
POST   /api/v1/approvals/{id}/approve    # Approve action
POST   /api/v1/approvals/{id}/reject     # Reject action
POST   /api/v1/approvals/{id}/delegate   # Delegate to another user
```

---

## 5. Tool Framework

### 5.1 Built-in Tools

| Tool | Description | Requires Approval |
|------|-------------|-------------------|
| `query_dcl` | Query unified data layer | No |
| `search_aod` | Search discovered assets | No |
| `invoke_aam` | Trigger AAM connector | Configurable |
| `search_kb` | Search knowledge base | No |
| `run_agent` | Invoke another agent | Yes |
| `send_notification` | Send Slack/email | Yes |
| `write_data` | Write to data store | Yes |

### 5.2 Tool Definition Schema

```python
class Tool(BaseModel):
    name: str
    description: str
    parameters: dict  # JSON Schema
    requires_approval: bool = False
    timeout_seconds: int = 30

    async def execute(self, params: dict, context: ExecutionContext) -> ToolResult:
        raise NotImplementedError

class QueryDCLTool(Tool):
    name = "query_dcl"
    description = "Query the Data Connection Layer for unified business data"
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Natural language query"},
            "entity": {"type": "string", "enum": ["accounts", "opportunities", "contacts"]},
            "limit": {"type": "integer", "default": 100}
        },
        "required": ["query"]
    }

    async def execute(self, params: dict, context: ExecutionContext) -> ToolResult:
        # Implementation
        pass
```

### 5.3 Custom Tool Registration

```python
# Users can register custom tools via API
POST /api/v1/agents/{id}/tools
{
    "name": "custom_crm_lookup",
    "description": "Look up customer in CRM",
    "parameters": { ... },
    "handler": {
        "type": "http",
        "method": "POST",
        "url": "https://crm.example.com/api/lookup",
        "headers": { "Authorization": "Bearer ${secrets.CRM_TOKEN}" }
    },
    "requires_approval": false
}
```

---

## 6. NLP Architecture

### 6.1 Intent Classification

```
User Input
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                    INTENT CLASSIFIER                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Query Data  │  │ Run Agent   │  │ System Command      │  │
│  │ ───────────│  │ ─────────── │  │ ──────────────────  │  │
│  │ "Show me"   │  │ "Run the"   │  │ "List agents"       │  │
│  │ "What is"   │  │ "Execute"   │  │ "Create agent"      │  │
│  │ "How many"  │  │ "Start"     │  │ "Show status"       │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                    ENTITY EXTRACTOR                          │
│  • Agent names     • Data entities    • Time ranges          │
│  • Filters         • Sort orders      • Limits               │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                    TOOL ROUTER                               │
│  Intent + Entities → Select Tool(s) → Execute → Format      │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 Conversation Memory

```python
class ConversationMemory:
    """
    Redis-backed conversation memory with summarization.
    """
    def __init__(self, session_id: str, redis: Redis):
        self.session_id = session_id
        self.redis = redis
        self.max_messages = 50
        self.summarize_threshold = 20

    async def add_message(self, role: str, content: str):
        """Add message to conversation history"""

    async def get_context(self) -> List[Message]:
        """Get relevant context for next LLM call"""

    async def summarize_if_needed(self):
        """Summarize old messages to stay within context window"""
```

---

## 7. Security Model

### 7.1 Authentication & Authorization

```
┌─────────────────────────────────────────────────────────────┐
│                    SECURITY LAYERS                           │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: JWT Authentication                                 │
│  ─────────────────────────────                              │
│  • Token validation on every request                         │
│  • Tenant ID embedded in token                               │
│  • 30-minute expiry with refresh                             │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: Multi-Tenant Isolation                             │
│  ───────────────────────────────                            │
│  • All queries filtered by tenant_id                         │
│  • Agent configs isolated per tenant                         │
│  • Redis keys namespaced by tenant                           │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: Role-Based Access Control                          │
│  ──────────────────────────────────                         │
│  • admin: Full access                                        │
│  • operator: Run agents, view results                        │
│  • viewer: Read-only access                                  │
├─────────────────────────────────────────────────────────────┤
│  Layer 4: Agent Guardrails                                   │
│  ─────────────────────────                                  │
│  • Per-agent tool restrictions                               │
│  • Cost limits per run                                       │
│  • Approval requirements for sensitive operations            │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 Secrets Management

```python
# Secrets stored encrypted, referenced by name
class SecretStore:
    """
    Tenant-scoped secret storage for API keys, tokens, etc.
    """
    async def set(self, tenant_id: str, name: str, value: str):
        encrypted = self.encrypt(value)
        await self.db.execute(
            "INSERT INTO secrets (tenant_id, name, value) VALUES ($1, $2, $3)",
            tenant_id, name, encrypted
        )

    async def get(self, tenant_id: str, name: str) -> str:
        row = await self.db.fetchone(
            "SELECT value FROM secrets WHERE tenant_id = $1 AND name = $2",
            tenant_id, name
        )
        return self.decrypt(row['value'])

# Usage in tool handlers
url = f"https://api.example.com?key=${secrets.API_KEY}"
# Resolved at runtime: secrets.API_KEY → actual value
```

---

## 8. Observability

### 8.1 Telemetry Pipeline

```
Agent Execution
      │
      ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Step Events    │────▶│  Redis Streams  │────▶│  WebSocket      │
│  (structured)   │     │  (buffer)       │     │  (real-time UI) │
└─────────────────┘     └─────────────────┘     └─────────────────┘
      │                         │
      │                         ▼
      │                 ┌─────────────────┐
      │                 │  PostgreSQL     │
      │                 │  (persistence)  │
      │                 └─────────────────┘
      │
      ▼
┌─────────────────┐
│  Metrics        │
│  (Prometheus)   │
│  • tokens_used  │
│  • latency_ms   │
│  • error_rate   │
└─────────────────┘
```

### 8.2 Key Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `agent_runs_total` | Counter | Total runs by agent, status |
| `agent_run_duration_seconds` | Histogram | Run duration distribution |
| `agent_tokens_used` | Counter | LLM tokens consumed |
| `agent_cost_usd` | Counter | Estimated cost |
| `agent_errors_total` | Counter | Errors by type |
| `approval_queue_depth` | Gauge | Pending approvals |
| `approval_latency_seconds` | Histogram | Time to human decision |

---

## 9. Implementation Phases

### Phase 1: Foundation (2 weeks)
**Goal**: Stable base for agent development

| Task | Priority | Effort | Dependencies |
|------|----------|--------|--------------|
| Fix AAM background task blocking | P0 | 2d | None |
| Re-enable audit middleware | P1 | 1d | Background fix |
| Add React Router | P1 | 2d | None |
| Create Agent/AgentRun/AgentStep models | P0 | 2d | None |
| Database migrations | P0 | 1d | Models |
| Basic CRUD API for agents | P0 | 2d | Models |

**Deliverable**: Agents can be created, stored, listed via API

### Phase 2: Execution Runtime (3 weeks)
**Goal**: Agents can execute with tools

| Task | Priority | Effort | Dependencies |
|------|----------|--------|--------------|
| LLM client abstraction | P0 | 2d | None |
| Tool framework base classes | P0 | 3d | None |
| Built-in tools (query_dcl, search_aod) | P0 | 3d | Tool framework |
| Agent executor (run loop) | P0 | 4d | LLM + Tools |
| Step persistence | P0 | 2d | Executor |
| WebSocket streaming | P1 | 2d | Executor |
| Cost tracking | P1 | 1d | Executor |

**Deliverable**: Agents can be invoked via API and execute multi-step workflows

### Phase 3: NLP Gateway (2 weeks)
**Goal**: Natural language interface

| Task | Priority | Effort | Dependencies |
|------|----------|--------|--------------|
| Intent classifier | P0 | 2d | LLM client |
| Entity extractor | P0 | 2d | LLM client |
| Conversation memory (Redis) | P0 | 2d | None |
| Tool router | P0 | 2d | Intent + Tools |
| Streaming response API | P1 | 2d | None |
| Persona-based prompts | P2 | 1d | None |

**Deliverable**: Users can chat naturally and invoke agents/tools

### Phase 4: HITL & Approvals (2 weeks)
**Goal**: Human oversight for sensitive operations

| Task | Priority | Effort | Dependencies |
|------|----------|--------|--------------|
| Approval model + API | P0 | 2d | Agent models |
| Approval queue UI | P0 | 3d | API |
| WebSocket notifications | P1 | 2d | Approval API |
| Timeout handling | P1 | 1d | Approval flow |
| Delegation support | P2 | 1d | Approval API |

**Deliverable**: Sensitive operations pause for human approval

### Phase 5: Control Center UI (2 weeks)
**Goal**: Comprehensive management interface

| Task | Priority | Effort | Dependencies |
|------|----------|--------|--------------|
| Agent list/detail pages | P0 | 3d | Agent API |
| Run history + replay | P0 | 2d | Run API |
| Live run viewer | P0 | 3d | WebSocket |
| Chat interface upgrade | P1 | 2d | NLP API |
| Approval queue panel | P1 | 2d | Approval API |

**Deliverable**: Full UI for agent management and monitoring

---

## 10. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| LLM rate limits | High | Medium | Circuit breaker, fallback models, caching |
| Runaway agent costs | Medium | High | Hard cost limits, step caps, alerts |
| Tool execution errors | High | Medium | Sandboxing, retries, graceful degradation |
| Context window overflow | Medium | Medium | Summarization, pruning, chunking |
| Approval queue bottleneck | Low | High | Auto-escalation, timeout defaults, SLAs |
| Multi-tenant data leak | Low | Critical | Query-level isolation, audit logging |

---

## 11. Technology Decisions

### 11.1 LLM Provider Strategy

```
Primary: Claude (Anthropic)
├── claude-sonnet-4-20250514 (default)
├── claude-opus-4-20250514 (complex reasoning)
└── claude-haiku-3-5-20241022 (high volume, low cost)

Fallback: OpenAI
├── gpt-4o (complex)
└── gpt-4o-mini (simple)

Selection Logic:
1. Use tenant-configured default
2. Escalate to stronger model on retry
3. Fall back to alternate provider on rate limit
```

### 11.2 Why Not LangChain/LlamaIndex?

| Factor | LangChain | Our Approach |
|--------|-----------|--------------|
| Abstraction level | High (magic) | Low (explicit) |
| Debugging | Difficult | Transparent |
| Lock-in | Framework-specific | Provider-agnostic |
| Performance | Overhead | Minimal |
| Customization | Fight the framework | Full control |

**Decision**: Build lightweight abstractions. The core loop is simple enough that framework overhead isn't justified.

---

## 12. Success Criteria

### Phase 1 Complete When:
- [ ] Agents can be CRUD'd via API
- [ ] Database schema deployed
- [ ] No blocking issues in server startup

### Phase 2 Complete When:
- [ ] Agent can be invoked and completes multi-step task
- [ ] Steps are persisted and queryable
- [ ] Real-time streaming works

### Phase 3 Complete When:
- [ ] User can chat naturally
- [ ] System correctly routes to tools/agents
- [ ] Conversation context maintained

### Phase 4 Complete When:
- [ ] Sensitive operations pause for approval
- [ ] Approvers notified in real-time
- [ ] Timeouts handled gracefully

### Phase 5 Complete When:
- [ ] All functionality accessible via UI
- [ ] No API-only operations for normal use
- [ ] Performance acceptable (< 2s page loads)

---

## 13. Appendix: File Structure

```
app/
├── api/v1/
│   ├── agents.py           # NEW: Agent CRUD + execution
│   ├── approvals.py        # NEW: Approval workflow
│   └── nlp_gateway.py      # REPLACE: nlp_simple.py
├── models/
│   ├── agent.py            # NEW: Agent, AgentRun, AgentStep
│   └── approval.py         # NEW: Approval model
├── services/
│   ├── agent_executor.py   # NEW: Run loop
│   ├── llm_client.py       # NEW: LLM abstraction
│   ├── tool_registry.py    # NEW: Tool management
│   └── memory_store.py     # NEW: Conversation memory
├── tools/
│   ├── base.py             # NEW: Tool base class
│   ├── query_dcl.py        # NEW: DCL tool
│   ├── search_aod.py       # NEW: AOD tool
│   └── invoke_aam.py       # NEW: AAM tool
└── orchestration/
    ├── workflow_engine.py  # NEW: Multi-agent workflows
    └── hitl_queue.py       # NEW: Approval queue

frontend/src/
├── components/
│   ├── AgentList.tsx       # NEW
│   ├── AgentDetail.tsx     # NEW
│   ├── RunViewer.tsx       # NEW
│   ├── ApprovalQueue.tsx   # NEW
│   └── ChatInterface.tsx   # ENHANCE: NLPGateway.tsx
└── pages/
    └── AgentsPage.tsx      # NEW
```

---

## 14. Next Steps

1. **Review this document** with stakeholders
2. **Approve Phase 1 scope** and begin implementation
3. **Set up LLM API keys** (Anthropic/OpenAI)
4. **Create database migrations** for new models

**Estimated total timeline**: 11 weeks for full implementation
**Recommended MVP (Phases 1-3)**: 7 weeks
