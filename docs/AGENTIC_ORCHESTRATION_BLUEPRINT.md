# Agentic Orchestration Architecture (AOA)
## Technical Blueprint v3.0

**Version**: 3.0 (Current Implementation)
**Date**: 2026-01-28
**Status**: PRODUCTION-READY CORE + ONGOING ENHANCEMENTS

---

## 1. Executive Summary

### 1.1 What is AOA?

AOA (Agentic Orchestration Architecture) is the runtime orchestration layer of AutonomOS that manages AI agent workflows across enterprise systems. It provides:

- **Unified Task Orchestration**: Single runtime for all agent tasks with priority queuing
- **Fabric Plane Mesh Integration**: Routes all actions through enterprise integration planes (NOT direct SaaS connections)
- **RACI Compliance**: Every action has clear Responsible, Accountable, Consulted, Informed roles
- **Multi-Agent Coordination**: A2A protocol for agent-to-agent communication
- **PII Protection**: Detection and policy enforcement at context sharing ingress

### 1.2 Implementation Status

| Component | Status | Description |
|-----------|--------|-------------|
| **AOARuntime** | COMPLETE | Unified runtime absorbing TaskQueue + WorkerPool |
| **AOAScheduler** | COMPLETE | Fabric-aware job scheduling (cron, interval, daily) |
| **A2A Protocol** | COMPLETE | Agent-to-agent messaging with fabric routing |
| **Context Sharing** | COMPLETE | PII detection at ingress with policy enforcement |
| **Fabric Routing** | COMPLETE | ActionRouter with 6 Enterprise Presets |
| **RACI Audit Logging** | COMPLETE | All actions logged with Primary_Plane_ID |
| **MCP Servers** | PLANNED | DCL/AAM/AOD exposed as Model Context Protocol |
| **LangGraph Integration** | PLANNED | Durable execution with checkpointing |

### 1.3 Strategic Positioning

**The Moat is NOT the Runtime. The Moat is the Data.**

AOS's differentiation:
- **Deep Data Access**: Navigate complex enterprise data topology (DCL/AAM/AOD)
- **Semantic Understanding**: Know what "revenue" means across 5 different systems
- **Governance**: HITL controls for sensitive cross-system operations
- **Fabric Plane Compliance**: Enterprise-grade routing through iPaaS/API Gateway/Event Bus

---

## 2. Architecture Overview

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              PRESENTATION LAYER                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │   Control       │  │   AOA           │  │   Stress Testing            │  │
│  │   Center        │  │   Dashboard     │  │   & Simulation              │  │
│  │   (NLQ + Ops)   │  │   (Monitoring)  │  │   (Validation)              │  │
│  └────────┬────────┘  └────────┬────────┘  └──────────────┬──────────────┘  │
└───────────┼────────────────────┼─────────────────────────┼──────────────────┘
            │                    │                         │
            ▼                    ▼                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API GATEWAY LAYER                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  Auth (JWT) │ Rate Limit │ Tracing │ Audit │ Multi-Tenant │ PII Detection   │
├─────────────────────────────────────────────────────────────────────────────┤
│  /api/v1/aoa/*     /api/v1/agents/*     /api/v1/fabric/*                    │
└─────────────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AOA ORCHESTRATION LAYER                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                          AOA RUNTIME                                 │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │    │
│  │  │   Task      │  │   Worker    │  │   Fabric    │  │   RACI     │  │    │
│  │  │   Queue     │  │   Pool      │  │   Router    │  │   Audit    │  │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                          AOA SCHEDULER                               │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │    │
│  │  │   Cron      │  │   Interval  │  │   Daily     │  │   One-Time │  │    │
│  │  │   Jobs      │  │   Jobs      │  │   Jobs      │  │   Jobs     │  │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                          A2A PROTOCOL                                │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │    │
│  │  │   Agent     │  │   Context   │  │   Delegation│  │   PII      │  │    │
│  │  │   Discovery │  │   Sharing   │  │   Manager   │  │   Filter   │  │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FABRIC PLANE MESH                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │   iPaaS Plane   │  │   API Gateway   │  │   Event Bus Plane           │  │
│  │   ───────────   │  │   Plane         │  │   ───────────               │  │
│  │   • Workato     │  │   ───────────   │  │   • Kafka                   │  │
│  │   • Tray.io     │  │   • Kong        │  │   • EventBridge             │  │
│  │   • Celigo      │  │   • Apigee      │  │   • Redis Streams           │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────────┘  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │   Data Warehouse│  │   Direct        │  │   Custom Plane              │  │
│  │   Plane         │  │   (Scrappy Only)│  │   (Enterprise)              │  │
│  │   ───────────   │  │   ───────────   │  │   ───────────               │  │
│  │   • Snowflake   │  │   • P2P API     │  │   • Custom iPaaS            │  │
│  │   • BigQuery    │  │   • Dev/Test    │  │   • On-prem Gateway         │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    AOS DATA SERVICES ← THE MOAT                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │   DCL           │  │   AAM           │  │   AOD                       │  │
│  │   ───────────   │  │   ──────────    │  │   ──────────                │  │
│  │   • query_data  │  │   • list_conns  │  │   • discover_assets         │  │
│  │   • get_schema  │  │   • sync_now    │  │   • get_lineage             │  │
│  │   • trace_lineage│ │   • check_health│  │   • search_metadata         │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Core Components (Implemented)

### 3.1 AOA Runtime

The unified orchestration runtime that absorbs TaskQueue and WorkerPool functionality.

**Location**: `app/agentic/aoa/runtime.py`

```python
class AOARuntime:
    """
    Unified AOA Runtime combining TaskQueue and WorkerPool management.
    
    RACI: AOA is RESPONSIBLE for runtime orchestration.
    
    Features:
    - Unified task submission with fabric routing
    - Worker pool management with auto-scaling
    - Health monitoring and metrics
    - Fabric context injection (Primary_Plane_ID)
    """
    
    async def submit_task(self, task: AOATask) -> str:
        # Auto-enriches with fabric context
        context = self.get_fabric_context()
        task.primary_plane_id = context.primary_plane_id
        task.fabric_preset = context.fabric_preset
        return await self._queue.enqueue(task.to_base_task())
    
    async def submit_fabric_action(
        self,
        target_system: TargetSystem,
        action_type: ActionType,
        entity_id: str,
        data: dict,
    ) -> str:
        # Routes through Fabric Plane Mesh
        ...
```

**Key Features**:
- Task priority queuing (CRITICAL, HIGH, NORMAL, LOW, BACKGROUND)
- Worker pool auto-scaling
- Fabric context enrichment on all tasks
- RACI metadata on every task
- Health monitoring and metrics

### 3.2 AOA Scheduler

Fabric-aware job scheduling for recurring and one-time tasks.

**Location**: `app/agentic/aoa/scheduler.py`

```python
class AOAScheduler:
    """
    Fabric-aware job scheduler.
    
    Schedule Types:
    - ONCE: One-time execution at specified time
    - INTERVAL: Recurring at fixed intervals
    - HOURLY: Every hour at specified minute
    - DAILY: Every day at specified hour:minute
    - CRON: Cron expression (planned)
    """
    
    async def schedule_daily(
        self,
        name: str,
        hour: int,
        minute: int = 0,
        payload: dict = None,
    ) -> ScheduledJob:
        # All jobs enriched with fabric context
        context = self.get_fabric_context()
        job.primary_plane_id = context.primary_plane_id
        ...
```

**Key Features**:
- Multiple schedule types (once, interval, hourly, daily)
- Automatic fabric context injection
- Job pause/resume/cancel
- Max runs limit
- Concurrent job limiting

### 3.3 A2A Protocol

Agent-to-agent communication with fabric routing.

**Location**: `app/agentic/a2a/protocol.py`

```python
class A2AProtocolHandler:
    """
    Handles A2A protocol messages between agents.
    
    Message Types:
    - EXECUTE: Request task execution
    - DELEGATE: Delegate task to another agent
    - CONTEXT_SHARE: Share context (with PII filtering)
    - STATUS_QUERY: Check task status
    """
    
    async def _handle_execute(self, message: A2AMessage) -> A2AMessage:
        # Validate/auto-enrich fabric context
        fabric_context = message.fabric_context or {}
        if not fabric_context.get("Primary_Plane_ID"):
            context = self._router.get_fabric_context()
            fabric_context["Primary_Plane_ID"] = context.primary_plane_id
            fabric_context["auto_enriched"] = True
        
        # RACI audit logging
        logger.info(
            "RACI_AUDIT",
            extra={
                "action": "A2A_EXECUTE",
                "Primary_Plane_ID": fabric_context.get("Primary_Plane_ID"),
                "from_agent": message.from_agent,
                "to_agent": message.to_agent,
            }
        )
        ...
```

**Key Features**:
- Message routing between agents
- Fabric context validation and auto-enrichment
- RACI audit logging on all actions
- PII detection on context sharing

### 3.4 Context Sharing with PII Protection

**Location**: `app/agentic/a2a/context_sharing.py`

```python
class ContextSharingManager:
    """
    Manages context sharing between agents with PII protection.
    
    PII Policies:
    - BLOCK: Reject context with PII
    - REDACT: Remove PII fields before sharing
    - WARN: Log warning but allow
    - ALLOW: No PII filtering
    """
    
    async def share_context(
        self,
        context: SharedContext,
        target_agent_id: str,
    ) -> SharedContext:
        # PII detection at ingress
        if self._pii_detector:
            pii_result = self._pii_detector.detect(context.data)
            if pii_result.has_pii:
                context = self._apply_pii_policy(context, pii_result)
        ...
```

---

## 4. Fabric Plane Mesh Architecture

### 4.1 Core Principle

**Agents MUST NOT make direct P2P connections to SaaS applications** (except in PRESET_6_SCRAPPY mode for development).

All actions flow through aggregated Fabric Planes:

| Plane | Purpose | Systems |
|-------|---------|---------|
| **iPaaS Plane** | Complex multi-step workflows | Workato, Tray.io, Celigo |
| **API Gateway Plane** | API management, rate limiting | Kong, Apigee |
| **Event Bus Plane** | Real-time events, streaming | Kafka, EventBridge |
| **Data Warehouse Plane** | Analytics, reporting | Snowflake, BigQuery |
| **Direct (Scrappy)** | Development/test only | Direct API calls |

### 4.2 Enterprise Presets

```python
class FabricPreset(str, Enum):
    PRESET_1_FULL_ENTERPRISE = "preset_1_full_enterprise"      # All planes required
    PRESET_2_IPAAS_FIRST = "preset_2_ipaas_first"              # iPaaS primary
    PRESET_3_API_GATEWAY_FIRST = "preset_3_api_gateway_first"  # Gateway primary
    PRESET_4_EVENT_BUS_FIRST = "preset_4_event_bus_first"      # Event bus primary
    PRESET_5_DATA_WAREHOUSE_FIRST = "preset_5_data_warehouse_first"  # Warehouse primary
    PRESET_6_SCRAPPY = "preset_6_scrappy"                      # Direct P2P allowed
```

### 4.3 Action Routing

```python
class ActionRouter:
    """
    Routes actions through appropriate Fabric Planes.
    
    Enforces:
    - Preset-based routing constraints
    - RACI audit logging
    - Primary_Plane_ID assignment
    """
    
    async def route(self, payload: ActionPayload, agent_id: str) -> RoutedAction:
        context = self.get_fabric_context()
        
        if not context.is_direct_allowed:
            # Must route through a plane
            plane = self._select_plane(payload.action_type, payload.target_system)
            routed_action.primary_plane_id = plane.plane_id
        
        # RACI audit
        logger.info(
            "RACI_AUDIT",
            extra={
                "action": "ROUTE_ACTION",
                "Primary_Plane_ID": routed_action.primary_plane_id,
                "target_system": payload.target_system,
            }
        )
        return routed_action
```

---

## 5. RACI Compliance

### 5.1 RACI Matrix for AOA

| Action | Responsible | Accountable | Consulted | Informed |
|--------|-------------|-------------|-----------|----------|
| Task Orchestration | AOA Runtime | Platform | Agents | Audit Log |
| Job Scheduling | AOA Scheduler | Platform | Users | Telemetry |
| Fabric Routing | ActionRouter | Security | Compliance | Audit Log |
| PII Detection | Security | Compliance | Legal | Audit Log |
| Context Sharing | A2A Protocol | AOA | Agents | Telemetry |

### 5.2 Audit Logging

All AOA actions emit RACI_AUDIT log entries:

```python
logger.info(
    "RACI_AUDIT",
    extra={
        "action": "TASK_SUBMIT",
        "Primary_Plane_ID": task.primary_plane_id,
        "task_id": task.id,
        "task_type": task.task_type.value,
        "agent_id": str(task.agent_id),
        "raci_responsible": task.raci_responsible,
        "raci_accountable": task.raci_accountable,
        "timestamp": datetime.utcnow().isoformat(),
    }
)
```

---

## 6. Data Models

### 6.1 AOATask

```python
@dataclass
class AOATask:
    id: str
    task_type: AOATaskType  # AGENT_RUN, FABRIC_ACTION, SCHEDULED_JOB, etc.
    payload: Dict[str, Any]
    
    # Identity
    agent_id: Optional[UUID]
    tenant_id: Optional[UUID]
    run_id: Optional[UUID]
    
    # Priority & Scheduling
    priority: TaskPriority  # CRITICAL, HIGH, NORMAL, LOW, BACKGROUND
    scheduled_at: Optional[datetime]
    
    # Fabric Routing (REQUIRED)
    primary_plane_id: Optional[str]
    fabric_preset: Optional[FabricPreset]
    fabric_context: Optional[Dict[str, Any]]
    
    # RACI Compliance
    raci_responsible: str = "AOA"
    raci_accountable: Optional[str]
    raci_consulted: List[str]
    raci_informed: List[str]
    
    # Execution
    target_system: Optional[TargetSystem]
    action_type: Optional[ActionType]
    routed_action_id: Optional[str]
    
    # Status
    status: TaskStatus
    timeout_seconds: int = 300
    max_retries: int = 3
```

### 6.2 ScheduledJob

```python
@dataclass
class ScheduledJob:
    id: str
    name: str
    description: str
    
    schedule: ScheduleConfig  # ONCE, INTERVAL, HOURLY, DAILY, CRON
    
    # Fabric Context (auto-enriched)
    primary_plane_id: Optional[str]
    fabric_preset: Optional[FabricPreset]
    
    # Execution
    status: JobStatus  # PENDING, SCHEDULED, RUNNING, COMPLETED, FAILED
    next_run_at: Optional[datetime]
    last_run_at: Optional[datetime]
    
    # Limits
    max_runs: Optional[int]
    run_count: int
```

### 6.3 A2AMessage

```python
@dataclass
class A2AMessage:
    id: str
    type: A2AMessageType  # EXECUTE, DELEGATE, CONTEXT_SHARE, etc.
    
    # Routing
    from_agent: str
    to_agent: str
    
    # Correlation
    correlation_id: Optional[str]
    in_reply_to: Optional[str]
    
    # Payload
    payload: Dict[str, Any]
    
    # Fabric Context (REQUIRED for EXECUTE)
    fabric_context: Optional[Dict[str, Any]]
    
    # Timestamps
    created_at: datetime
    expires_at: Optional[datetime]
```

---

## 7. API Endpoints

### 7.1 AOA Runtime APIs

```
POST   /api/v1/aoa/tasks              Submit a task
GET    /api/v1/aoa/tasks/{id}         Get task status
DELETE /api/v1/aoa/tasks/{id}         Cancel task
GET    /api/v1/aoa/metrics            Get runtime metrics
GET    /api/v1/aoa/health             Health check
```

### 7.2 AOA Scheduler APIs

```
POST   /api/v1/aoa/jobs               Schedule a job
GET    /api/v1/aoa/jobs               List jobs
GET    /api/v1/aoa/jobs/{id}          Get job details
POST   /api/v1/aoa/jobs/{id}/pause    Pause job
POST   /api/v1/aoa/jobs/{id}/resume   Resume job
DELETE /api/v1/aoa/jobs/{id}          Cancel job
GET    /api/v1/aoa/scheduler/stats    Get scheduler stats
```

### 7.3 Fabric Routing APIs

```
GET    /api/v1/fabric/context         Get current fabric context
POST   /api/v1/fabric/preset          Set active preset
GET    /api/v1/fabric/planes          List available planes
```

---

## 8. Future Enhancements

### 8.1 MCP Server Integration (Planned)

Expose DCL, AAM, and AOD as Model Context Protocol servers:

```python
# aos-dcl MCP server
@server.list_tools()
async def list_tools():
    return [
        Tool(name="query_data", description="Query unified business data"),
        Tool(name="get_schema", description="Get entity schema"),
        Tool(name="trace_lineage", description="Trace data lineage"),
    ]
```

### 8.2 LangGraph Integration (Planned)

Durable execution with PostgreSQL checkpointing:

```python
from langgraph.graph import StateGraph
from langgraph.checkpoint.postgres import PostgresSaver

workflow = StateGraph(AgentState)
workflow.add_node("reason", reasoning_node)
workflow.add_node("tools", tool_node)
workflow.add_node("human_review", human_interrupt_node)

app = workflow.compile(
    checkpointer=PostgresSaver.from_conn_string(DATABASE_URL),
    interrupt_before=["human_review"]
)
```

### 8.3 Human-in-the-Loop (Planned)

Approval workflows for sensitive operations:

```python
class Approval(Base):
    __tablename__ = "approvals"
    
    id: UUID
    run_id: UUID
    action_type: str  # write_data, external_call, etc.
    action_details: dict
    status: str  # pending, approved, rejected, timeout
    expires_at: datetime
    auto_action: str  # reject, approve, escalate
```

---

## 9. File Structure

```
app/agentic/
├── aoa/
│   ├── __init__.py
│   ├── runtime.py          # AOARuntime - unified orchestration
│   └── scheduler.py        # AOAScheduler - job scheduling
├── a2a/
│   ├── __init__.py
│   ├── protocol.py         # A2A message handling
│   ├── context_sharing.py  # Context sharing with PII protection
│   ├── agent_card.py       # Agent capability cards
│   ├── discovery.py        # Agent discovery
│   └── delegation.py       # Task delegation
├── fabric/
│   ├── __init__.py
│   ├── planes.py           # FabricPreset, ActionType, TargetSystem
│   └── router.py           # ActionRouter
├── scaling/
│   ├── __init__.py
│   ├── task_queue.py       # Priority task queue
│   ├── pool.py             # Worker pool management
│   └── worker.py           # Worker implementation
└── coordination/
    ├── __init__.py
    └── orchestrator.py     # Multi-agent orchestration
```

---

## 10. Testing & Validation

### 10.1 Stress Testing

The AOA dashboard includes stress testing capabilities:
- Simulate high task load
- Test fabric routing under pressure
- Validate RACI compliance at scale

### 10.2 Simulation Mode

Run agents in simulation mode to validate workflows:
- No actual external API calls
- Full fabric routing enforcement
- Complete audit trail

---

**Document Version**: 3.0
**Last Updated**: 2026-01-28
**Status**: Production-Ready Core
