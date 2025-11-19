# DCL Engine Service Decomposition Plan

**Document Version:** 1.0  
**Date:** November 15, 2025  
**Status:** Analysis & Planning Phase  
**Scope:** Multi-tenant migration strategy for DCL Engine using Strangler Fig pattern

---

## Executive Summary

### Current State: Critical Tenant Isolation Gaps

The DCL Engine (`app/dcl_engine/app.py`) currently uses **shared global state** across all tenants, creating critical data isolation and scalability issues:

**Severity: HIGH** 🔴
- **GRAPH_STATE** (line 39): Single shared dictionary for ALL tenants' graph visualizations
- **SOURCES_ADDED** (line 40): Shared list causes cross-tenant data leakage
- **ENTITY_SOURCES** (line 41): No tenant scoping on entity-source mappings
- **SOURCE_SCHEMAS** (line 52): Schema metadata shared across tenants
- **EVENT_LOG** (line 38): Operational logs mixed across tenants
- **SELECTED_AGENTS** (line 45): Agent selections not tenant-scoped

**Impact:**
- ❌ Tenant A can see Tenant B's graph visualizations
- ❌ Connecting a source in one tenant affects all tenants
- ❌ Agent selections and results leak across tenant boundaries
- ❌ No scalability beyond single-process deployment
- ❌ Violates enterprise security and compliance requirements

**Partial Migrations (In Progress):**
- ✅ DEV_MODE → Redis (cross-process safe)
- ✅ LLM_CALLS/LLM_TOKENS → Redis (persists across restarts)
- ✅ GRAPH_STATE persistence → Redis (tenant-scoped, optional)
- ✅ AGENT_RESULTS_CACHE → In-memory with tenant_id keys

**Good News:**
- Some tenant-scoping infrastructure already exists (tenant_id parameters)
- Redis client infrastructure is in place
- AgentExecutor already uses tenant_id for results caching
- GraphStateStore has tenant-scoping logic (not yet enforced in all paths)

---

## Part 1: Complete Global State Inventory

### 1.1 Tenant Data State (CRITICAL - Must Be Tenant-Scoped)

| Variable | Line | Current Scope | Tenant Risk | Migration Path |
|----------|------|---------------|-------------|----------------|
| `GRAPH_STATE` | 39 | Global (shared) | 🔴 CRITICAL | Redis hash per tenant |
| `SOURCES_ADDED` | 40 | Global list | 🔴 CRITICAL | Redis set per tenant |
| `ENTITY_SOURCES` | 41 | Global dict | 🔴 CRITICAL | Redis hash per tenant |
| `SOURCE_SCHEMAS` | 52 | Global dict | 🔴 CRITICAL | Redis hash per tenant |
| `SELECTED_AGENTS` | 45 | Global list | 🔴 CRITICAL | Redis set per tenant |
| `AGENT_RESULTS_CACHE` | 46 | In-memory (tenant_id keyed) | 🟡 MEDIUM | Already tenant-scoped, move to Redis |
| `EVENT_LOG` | 38 | Global list | 🟡 MEDIUM | Separate log stream per tenant |
| `TIMING_LOG` | 58-63 | Global dict | 🟢 LOW | Aggregate metrics (shared OK) |

**Key Findings:**
- **6 critical global variables** require immediate tenant isolation
- **GRAPH_STATE** is the most visible issue (user-facing graph visualization)
- **SOURCES_ADDED** and **ENTITY_SOURCES** cause data correctness issues
- **SELECTED_AGENTS** affects query results and agent execution

### 1.2 Configuration State (Shared - Global OK)

| Variable | Line | Scope | Notes |
|----------|------|-------|-------|
| `ontology` | 43 | Global | ✅ Configuration - same for all tenants |
| `agents_config` | 44 | Global | ✅ Configuration - same for all tenants |
| `DB_PATH` | 22 | Global constant | ✅ Shared DuckDB (tenant isolation via table naming) |
| `ONTOLOGY_PATH` | 23 | Global constant | ✅ Static config file |
| `CONF_THRESHOLD` | 26 | Global constant | ✅ System-wide setting |

**Analysis:** Configuration state can remain global as it's shared across all tenants.

### 1.3 Infrastructure State (Shared - Global OK with Concurrency Controls)

| Variable | Line | Scope | Notes |
|----------|------|-------|-------|
| `redis_client` | 70 | Global | ✅ Shared connection pool (thread-safe) |
| `async_redis_client` | 72 | Global | ✅ Async connection pool |
| `rag_engine` | 50 | Global | ✅ Shared RAG service (tenant-agnostic embeddings) |
| `agent_executor` | 47 | Global | ✅ Orchestrator (tenant_id parameter) |
| `ws_manager` | 337 | Global | ⚠️ Needs tenant filtering on broadcasts |
| `STATE_LOCK` | 54 | Global | ✅ Thread safety (synchronous contexts) |
| `ASYNC_STATE_LOCK` | 55 | Global | ✅ Async concurrency control |
| `graph_store` | 153 | Global | ✅ Helper class (tenant-scoped operations) |

**Analysis:** Infrastructure components are correctly shared, but need tenant-aware operations.

### 1.4 Feature Flag State (Redis-Backed - Already Migrated)

| Variable | Line | Storage | Notes |
|----------|------|---------|-------|
| `DEV_MODE` | 53 | Redis (DEV_MODE_KEY) | ✅ Migrated - cross-process safe |
| Feature flags | N/A | Redis (FeatureFlagConfig) | ✅ Production-ready persistence |

**Analysis:** Feature flags are correctly implemented with Redis persistence and pub/sub.

### 1.5 Telemetry State (Redis-Backed - Partially Migrated)

| Variable | Line | Storage | Scope | Notes |
|----------|------|---------|-------|-------|
| `LLM_CALLS` | 48 | Redis (LLM_CALLS_KEY) | Global aggregate | ✅ Persists across restarts |
| `LLM_TOKENS` | 49 | Redis (LLM_TOKENS_KEY) | Global aggregate | ✅ Persists across restarts |
| `RAG_CONTEXT` | 51 | In-memory | Global aggregate | 🟡 Consider Redis for multi-process |
| `TIMING_LOG` | 58-63 | In-memory | Global aggregate | 🟡 Consider structured logging |

**Analysis:** Telemetry can remain global (aggregated across tenants), but should persist for production observability.

### 1.6 Request State (In-Memory - Anti-Pattern Detection)

| Variable | Line | Purpose | Issue |
|----------|------|---------|-------|
| `_active_toggle_requests` | 66 | Request deduplication | ⚠️ Process-local only, use Redis for distributed deduplication |

**Analysis:** Request deduplication must use Redis to work across multiple processes.

---

## Part 2: Tenant-Scoping Requirements Analysis

### 2.1 State Classification Matrix

| State Category | Tenant-Specific? | Storage | Lifespan | Priority |
|----------------|------------------|---------|----------|----------|
| **Graph State** | ✅ YES | Redis hash | Session/persistent | P0 (Critical) |
| **Source Connections** | ✅ YES | Redis set | Persistent | P0 (Critical) |
| **Agent Selections** | ✅ YES | Redis set | Persistent | P0 (Critical) |
| **Entity Mappings** | ✅ YES | Redis hash | Persistent | P0 (Critical) |
| **Schema Metadata** | ✅ YES | Redis hash | Persistent | P0 (Critical) |
| **Agent Results** | ✅ YES | Redis hash | Persistent | P1 (High) |
| **Event Logs** | ✅ YES | Redis stream | Ephemeral (24h TTL) | P2 (Medium) |
| **Configuration** | ❌ NO | File system | Static | P3 (Low) |
| **Telemetry** | ❌ NO | Redis counters | Persistent | P3 (Low) |

### 2.2 Redis vs Database Decision

**Use Redis for:**
- ✅ Graph state (frequent reads, moderate writes, JSON serialization)
- ✅ Active source connections (set operations, fast membership checks)
- ✅ Selected agents (set operations, fast lookups)
- ✅ Recent event logs (streams with TTL, time-series data)
- ✅ Request deduplication (TTL-based keys)

**Use PostgreSQL for:**
- ❌ (Future) Historical agent results (long-term analytics, complex queries)
- ❌ (Future) Audit trails (compliance, immutable records)
- ❌ (Future) User preferences (relational data, ACID guarantees)

**Use DuckDB for:**
- ✅ Materialized views (analytical queries, JOIN operations)
- ✅ Table prefixing for tenant isolation (`tenant_{tenant_id}_{table}`)

**Rationale:**
- Redis provides fast, tenant-scoped key-value storage perfect for session state
- PostgreSQL better for historical/audit data (not needed in initial migration)
- DuckDB already used for analytical views (tenant isolation via table naming)

### 2.3 Tenant Isolation Enforcement Points

**API Layer (app/main.py):**
- ✅ JWT tokens contain `tenant_id` claim
- ✅ `get_current_user()` dependency extracts tenant_id
- ⚠️ DCL endpoints need to enforce tenant_id from JWT (not query param)

**Service Layer (app/dcl_engine/app.py):**
- ❌ No tenant validation on state access (CRITICAL GAP)
- ❌ Global state allows cross-tenant reads/writes
- ⚠️ Need tenant_id injection into all state operations

**Data Layer:**
- ✅ DuckDB tables use tenant prefixes (partial isolation)
- ✅ Redis keys can use tenant prefixes (`dcl:graph:{tenant_id}`)
- ❌ In-memory state has no isolation

---

## Part 3: Dependency Mapping

### 3.1 External Dependencies (DCL Engine → External Systems)

| Dependency | Type | Usage | Tenant-Aware? |
|------------|------|-------|---------------|
| **Gemini AI** | LLM | Mapping proposals, semantic validation | ✅ YES (via context) |
| **Pinecone** | Vector DB | RAG retrieval for schema mappings | ❌ NO (shared index) |
| **DuckDB** | OLAP DB | Materialized views, analytical queries | ✅ YES (table prefixes) |
| **Redis** | Cache/Pub-Sub | State persistence, feature flags | ✅ YES (key prefixes) |
| **PostgreSQL** | OLTP DB | Canonical events (via AAM), metadata | ✅ YES (tenant_id column) |

**Key Findings:**
- Pinecone RAG engine is tenant-agnostic (stores generic mapping patterns, not tenant data)
- DuckDB and Redis need consistent tenant prefixing strategy
- LLM calls are stateless (tenant context in prompt only)

### 3.2 Internal Consumers (External Systems → DCL Engine)

| Consumer | Integration Point | Dependency | Tenant-Aware? |
|----------|-------------------|------------|---------------|
| **Frontend** | `/state`, `/connect`, WebSocket `/ws` | Graph state, event logs | ⚠️ Partial (needs JWT enforcement) |
| **AAM** | `source_loader.py` (AAMSourceAdapter) | Source discovery, table loading | ✅ YES (tenant_id param) |
| **Agents** | `agent_executor.py` | Materialized views, metadata | ✅ YES (tenant_id param) |
| **Main App** | `app.mount("/dcl", dcl_app)` | DCL FastAPI app | ✅ YES (JWT middleware) |

**Key Findings:**
- AAMSourceAdapter already supports tenant_id parameter (good foundation)
- AgentExecutor uses tenant_id for results caching (already isolated)
- Frontend WebSocket needs tenant filtering on broadcasts
- API Gateway (main app) provides JWT-based tenant_id

### 3.3 DCL Engine API Surface (Public Contracts)

**Core State Endpoints:**
```
GET  /state                      # Main state (graph, events, telemetry)
GET  /connect?sources=X&agents=Y # Idempotent connection (rebuilds graph)
WS   /ws                         # WebSocket real-time updates
```

**Agent Endpoints:**
```
GET  /dcl/agents/{agent_id}/results?tenant_id=X  # Agent results
GET  /dcl/agents/results?tenant_id=X             # All agent results
```

**Data Quality Endpoints (AAM Integration):**
```
GET  /dcl/metadata?tenant_id=X        # Aggregated metadata
GET  /dcl/drift-alerts?tenant_id=X    # Schema drift alerts
GET  /dcl/hitl-pending?tenant_id=X    # HITL review queue
GET  /dcl/repair-history?tenant_id=X  # Auto-repair history
```

**Admin Endpoints:**
```
GET  /toggle_dev_mode              # Toggle AI/RAG mode
POST /dcl/toggle_aam_mode          # Toggle AAM vs file sources
POST /reset_llm_stats              # Reset telemetry counters
GET  /rag/stats                    # RAG engine statistics
```

**Data Inspection:**
```
GET  /preview?tenant_id=X          # Preview unified data
GET  /source_schemas?tenant_id=X   # Source schema metadata
GET  /ontology_schema              # Ontology definition (shared)
```

**Breaking Change Risk:**
- ✅ **LOW**: Most endpoints already accept `tenant_id` query param
- ⚠️ **MEDIUM**: `/state` and `/connect` need tenant_id enforcement
- ⚠️ **MEDIUM**: WebSocket broadcasts need tenant filtering

---

## Part 4: Service Decomposition Strategy (Strangler Fig Pattern)

### 4.1 Service Boundary Definition

**Proposed Service Architecture:**

```
┌─────────────────────────────────────────────────────────────┐
│                    DCL Unified Service                      │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Graph       │  │  Agent       │  │  Schema      │     │
│  │  Manager     │  │  Executor    │  │  Registry    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │         Tenant State Manager (Redis-backed)         │   │
│  │  - Graph state per tenant                           │   │
│  │  - Source connections per tenant                    │   │
│  │  - Agent selections per tenant                      │   │
│  │  - Entity mappings per tenant                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │         Shared Services Layer                       │   │
│  │  - RAG Engine (tenant-agnostic)                     │   │
│  │  - LLM Service (stateless)                          │   │
│  │  - DuckDB Manager (tenant-prefixed tables)          │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**Service Responsibilities:**

1. **Graph Manager** (tenant-scoped)
   - Owns GRAPH_STATE per tenant
   - Manages graph persistence (Redis)
   - Handles graph updates and broadcasts
   - Filters graph nodes by AAM mode

2. **Agent Executor** (already tenant-aware)
   - Executes agents on tenant-scoped data
   - Stores results per tenant
   - Provides data quality metadata

3. **Schema Registry** (tenant-scoped)
   - Owns SOURCE_SCHEMAS per tenant
   - Tracks SOURCES_ADDED per tenant
   - Manages ENTITY_SOURCES mappings

4. **Tenant State Manager** (NEW - critical component)
   - Central authority for tenant data isolation
   - Redis-backed storage with tenant prefixing
   - Provides get/set operations with tenant_id enforcement
   - Handles state migrations and rollbacks

5. **Shared Services Layer**
   - RAG Engine (tenant-agnostic, shared index)
   - LLM Service (stateless, tenant context in prompts)
   - DuckDB Manager (tenant-prefixed tables)

### 4.2 Strangler Fig Migration Phases

**Phase 0: Foundation (Pre-work)**
- ✅ Already complete: Redis client infrastructure
- ✅ Already complete: Tenant_id parameter threading
- ⬜ Add: Tenant State Manager service class
- ⬜ Add: Redis key naming conventions documentation

**Phase 1: Critical State Migration (Week 1-2)**

**Priority: P0 - CRITICAL**

Migrate tenant-critical state to Redis with backward compatibility:

```python
# New: TenantStateManager class
class TenantStateManager:
    def __init__(self, redis_client):
        self.redis = redis_client
    
    def get_graph_state(self, tenant_id: str) -> dict:
        key = f"dcl:graph_state:{tenant_id}"
        data = self.redis.get(key)
        return json.loads(data) if data else {"nodes": [], "edges": []}
    
    def set_graph_state(self, tenant_id: str, state: dict):
        key = f"dcl:graph_state:{tenant_id}"
        self.redis.set(key, json.dumps(state))
    
    def get_sources_added(self, tenant_id: str) -> set:
        key = f"dcl:sources_added:{tenant_id}"
        return self.redis.smembers(key)
    
    def add_source(self, tenant_id: str, source_id: str):
        key = f"dcl:sources_added:{tenant_id}"
        self.redis.sadd(key, source_id)
```

**Migration Steps:**
1. Create `TenantStateManager` class in `app/dcl_engine/tenant_state.py`
2. Add dual-write logic (write to both global + Redis)
3. Add dual-read logic (read from Redis, fallback to global)
4. Update `/connect` endpoint to use TenantStateManager
5. Update `/state` endpoint to use TenantStateManager
6. Add tenant_id validation middleware
7. Remove global state variables (GRAPH_STATE, SOURCES_ADDED, etc.)

**Validation:**
- ✅ Multi-tenant smoke test (2+ tenants, no cross-contamination)
- ✅ Performance test (latency < 50ms for state reads)
- ✅ Rollback test (toggle feature flag to revert to global state)

**Phase 2: Agent & Schema State Migration (Week 3)**

**Priority: P1 - HIGH**

Migrate agent results and schema metadata to Redis:

```python
class TenantStateManager:
    def get_agent_results(self, tenant_id: str, agent_id: str) -> dict:
        key = f"dcl:agent_results:{tenant_id}:{agent_id}"
        data = self.redis.get(key)
        return json.loads(data) if data else {}
    
    def get_source_schemas(self, tenant_id: str, source_id: str) -> dict:
        key = f"dcl:source_schemas:{tenant_id}:{source_id}"
        data = self.redis.hgetall(key)
        return {k: json.loads(v) for k, v in data.items()}
```

**Migration Steps:**
1. Migrate AGENT_RESULTS_CACHE to Redis
2. Migrate SOURCE_SCHEMAS to Redis
3. Migrate ENTITY_SOURCES to Redis
4. Migrate SELECTED_AGENTS to Redis
5. Add TTL policies for ephemeral data

**Phase 3: Observability & Logging (Week 4)**

**Priority: P2 - MEDIUM**

Migrate event logs and implement tenant-aware logging:

```python
class TenantStateManager:
    def add_event_log(self, tenant_id: str, message: str):
        key = f"dcl:event_log:{tenant_id}"
        # Use Redis stream for time-series event logs
        self.redis.xadd(key, {"message": message, "timestamp": time.time()})
        # Set TTL to 24 hours (ephemeral logs)
        self.redis.expire(key, 86400)
    
    def get_event_logs(self, tenant_id: str, count: int = 200) -> list:
        key = f"dcl:event_log:{tenant_id}"
        # Read latest N events
        events = self.redis.xrevrange(key, count=count)
        return [e[1]["message"] for e in events]
```

**Migration Steps:**
1. Replace EVENT_LOG list with Redis streams
2. Add tenant_id to all log() calls
3. Implement log rotation (24h TTL)
4. Update frontend to read per-tenant logs

**Phase 4: WebSocket Tenant Filtering (Week 4)**

**Priority: P2 - MEDIUM**

Implement tenant-aware WebSocket broadcasts:

```python
class ConnectionManager:
    def __init__(self):
        # Map: tenant_id -> [websocket1, websocket2, ...]
        self.tenant_connections: Dict[str, List[WebSocket]] = {}
    
    async def broadcast_to_tenant(self, tenant_id: str, message: dict):
        connections = self.tenant_connections.get(tenant_id, [])
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception:
                # Remove disconnected client
                connections.remove(connection)
```

**Migration Steps:**
1. Refactor `ws_manager` to track tenant_id per connection
2. Update `broadcast_state_change()` to accept tenant_id
3. Filter broadcasts to tenant-specific connections only
4. Update frontend WebSocket client to send tenant_id on connect

**Phase 5: DuckDB Tenant Isolation Hardening (Week 5)**

**Priority: P3 - LOW**

Enforce strict table naming conventions and add validation:

```python
def get_tenant_table_name(tenant_id: str, table_name: str) -> str:
    # Enforce naming: tenant_{tenant_id}_{table}
    # Prevent SQL injection via parameterized queries
    safe_tenant_id = re.sub(r'[^a-zA-Z0-9_]', '', tenant_id)
    return f"tenant_{safe_tenant_id}_{table_name}"

def validate_tenant_access(con, tenant_id: str, table_name: str):
    expected_prefix = f"tenant_{tenant_id}_"
    if not table_name.startswith(expected_prefix):
        raise ValueError(f"Tenant {tenant_id} cannot access table {table_name}")
```

**Migration Steps:**
1. Add `get_tenant_table_name()` utility function
2. Audit all DuckDB queries for tenant prefixing
3. Add validation in `apply_plan()` and `connect_source()`
4. Add integration tests for tenant isolation

### 4.3 Communication Patterns

**Current Pattern: Monolith (In-Process)**
```
Frontend → FastAPI → DCL Engine (in-process function calls)
```

**Target Pattern: Service-Oriented (Still In-Process, Better Boundaries)**
```
Frontend → FastAPI → DCL Service Layer → Tenant State Manager → Redis
                                      ↓
                                  DuckDB (tenant-prefixed)
```

**Future Pattern: Microservices (Phase 6+, Optional)**
```
Frontend → API Gateway → DCL Service (HTTP) → Redis Cluster
                      ↓
                   AAM Service (HTTP)
                      ↓
                 Agent Service (HTTP)
```

**Event-Driven Communication (Future):**
- Redis Pub/Sub for real-time state changes
- Redis Streams for event sourcing
- WebSocket for frontend broadcasts

**Rationale:**
- Keep in-process for Phase 1-5 (lower complexity, faster iteration)
- Service boundaries via classes (not network calls)
- Easier rollback and debugging
- Microservices extraction becomes easier if needed later

### 4.4 Backward Compatibility Strategy

**Feature Flag Approach:**
```python
class FeatureFlag(Enum):
    USE_AAM_AS_SOURCE = "use_aam_as_source"  # Existing
    USE_TENANT_STATE_MANAGER = "use_tenant_state_manager"  # NEW

# In app.py
def get_graph_state(tenant_id: str) -> dict:
    if FeatureFlagConfig.is_enabled(FeatureFlag.USE_TENANT_STATE_MANAGER):
        # New path: Redis-backed tenant state
        return tenant_state_manager.get_graph_state(tenant_id)
    else:
        # Old path: Global state (backward compatibility)
        return GRAPH_STATE
```

**Dual-Write Period:**
- Write to BOTH global state and Redis during migration
- Allows instant rollback if issues detected
- Monitor for data consistency issues

**Rollback Plan:**
1. Disable `USE_TENANT_STATE_MANAGER` feature flag
2. System reverts to global state immediately
3. No data loss (dual-write ensures both stores are current)
4. Investigate issue, fix, re-enable flag

---

## Part 5: Risk Assessment & Mitigation

### 5.1 Risk Matrix

| Risk | Likelihood | Impact | Severity | Mitigation |
|------|-----------|--------|----------|------------|
| **Cross-tenant data leakage** | High | Critical | 🔴 P0 | Comprehensive integration tests, tenant validation middleware |
| **Performance degradation (Redis latency)** | Medium | High | 🟡 P1 | Benchmark tests, Redis connection pooling, caching layer |
| **State inconsistency (dual-write)** | Medium | High | 🟡 P1 | Atomic Redis operations, consistency validation tests |
| **WebSocket broadcast storms** | Low | Medium | 🟢 P2 | Rate limiting, tenant filtering, connection limits |
| **DuckDB lock contention** | Medium | Medium | 🟡 P1 | Distributed locks (Redis), query optimization |
| **Rollback failure** | Low | Critical | 🟡 P1 | Feature flag infrastructure, dual-write safety net |
| **Migration data loss** | Low | Critical | 🟡 P1 | Backup global state before migration, dual-write validation |

### 5.2 Testing Strategy

**Unit Tests:**
```python
def test_tenant_isolation():
    # Create state for tenant A
    manager.set_graph_state("tenant_a", {"nodes": [{"id": "A"}]})
    # Create state for tenant B
    manager.set_graph_state("tenant_b", {"nodes": [{"id": "B"}]})
    # Verify isolation
    assert manager.get_graph_state("tenant_a") != manager.get_graph_state("tenant_b")
    assert "A" in str(manager.get_graph_state("tenant_a"))
    assert "B" not in str(manager.get_graph_state("tenant_a"))
```

**Integration Tests:**
```python
async def test_multi_tenant_connect():
    # Tenant A connects to Salesforce
    await connect_source("salesforce", tenant_id="tenant_a")
    # Tenant B connects to MongoDB
    await connect_source("mongodb", tenant_id="tenant_b")
    # Verify tenant A sees only Salesforce
    state_a = manager.get_sources_added("tenant_a")
    assert "salesforce" in state_a
    assert "mongodb" not in state_a
    # Verify tenant B sees only MongoDB
    state_b = manager.get_sources_added("tenant_b")
    assert "mongodb" in state_b
    assert "salesforce" not in state_b
```

**Load Tests:**
```bash
# Simulate 10 concurrent tenants, 100 requests each
locust -f tests/load/tenant_isolation.py --users=10 --spawn-rate=2
```

**Smoke Tests (Pre-Production):**
1. Create 3 test tenants
2. Connect different sources to each tenant
3. Verify graph state isolation
4. Verify agent results isolation
5. Verify WebSocket broadcasts are tenant-filtered
6. Verify DuckDB table isolation

### 5.3 Monitoring & Observability

**Key Metrics:**
```python
# Tenant state metrics
dcl_tenant_state_read_latency_ms{tenant_id="X"}
dcl_tenant_state_write_latency_ms{tenant_id="X"}
dcl_tenant_state_size_bytes{tenant_id="X"}

# Cross-tenant leakage detection
dcl_cross_tenant_access_attempts{source_tenant="X", target_tenant="Y"}
dcl_tenant_validation_failures{endpoint="/connect"}

# Performance metrics
dcl_redis_operation_latency_ms{operation="get_graph_state"}
dcl_duckdb_query_latency_ms{tenant_id="X", table="account"}
dcl_websocket_broadcast_latency_ms{tenant_id="X"}
```

**Alerting:**
- 🚨 CRITICAL: Cross-tenant access detected (immediate page)
- 🚨 CRITICAL: State read latency > 100ms (P1 incident)
- ⚠️ WARNING: Redis connection errors (investigate)
- ⚠️ WARNING: Dual-write inconsistency detected (validate)

**Logging:**
```python
logger.info(
    "Tenant state access",
    extra={
        "tenant_id": tenant_id,
        "operation": "get_graph_state",
        "latency_ms": elapsed_ms,
        "cache_hit": cache_hit
    }
)
```

---

## Part 6: Success Metrics

### 6.1 Functional Success Criteria

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Zero cross-tenant data leakage** | 0 incidents | Integration test suite, production monitoring |
| **State read latency** | < 50ms p99 | Performance benchmarks, APM |
| **State write latency** | < 100ms p99 | Performance benchmarks, APM |
| **Multi-tenant concurrency** | 10+ concurrent tenants | Load testing |
| **WebSocket broadcast accuracy** | 100% tenant filtering | Integration tests |
| **DuckDB query isolation** | 100% tenant-prefixed tables | Code audit, validation tests |
| **Rollback success rate** | 100% (no data loss) | Rollback drills, dual-write validation |

### 6.2 Operational Success Criteria

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Migration downtime** | 0 (zero-downtime migration) | Feature flag rollout |
| **Rollback time** | < 5 minutes | Feature flag toggle + validation |
| **Test coverage** | > 80% for tenant state code | Code coverage tools |
| **Documentation completeness** | 100% of new APIs documented | Doc review |
| **Developer onboarding time** | < 1 hour to understand tenant state | Team feedback |

### 6.3 Business Success Criteria

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Enterprise readiness** | SOC 2 compliant tenant isolation | Security audit |
| **Scalability** | Support 100+ tenants | Horizontal scaling tests |
| **Data residency** | Tenant data stays in tenant-scoped keys | Redis key audit |
| **Cost efficiency** | < 10% increase in Redis costs | Cost monitoring |

---

## Part 7: Implementation Roadmap

### Week 1-2: Phase 1 - Critical State Migration (P0)

**Deliverables:**
- ✅ TenantStateManager class implemented
- ✅ GRAPH_STATE migrated to Redis
- ✅ SOURCES_ADDED migrated to Redis
- ✅ SELECTED_AGENTS migrated to Redis
- ✅ /connect and /state endpoints updated
- ✅ Feature flag USE_TENANT_STATE_MANAGER added
- ✅ Integration tests passing (multi-tenant isolation)

**Exit Criteria:**
- 2+ tenants can connect to different sources without interference
- Graph state is isolated per tenant
- Rollback to global state works flawlessly

### Week 3: Phase 2 - Agent & Schema State (P1)

**Deliverables:**
- ✅ AGENT_RESULTS_CACHE migrated to Redis
- ✅ SOURCE_SCHEMAS migrated to Redis
- ✅ ENTITY_SOURCES migrated to Redis
- ✅ Agent executor endpoints updated
- ✅ Schema inspection endpoints updated

**Exit Criteria:**
- Agent results are isolated per tenant
- Schema metadata is isolated per tenant
- Performance benchmarks pass (< 100ms latency)

### Week 4: Phase 3 & 4 - Observability & WebSocket (P2)

**Deliverables:**
- ✅ EVENT_LOG migrated to Redis streams
- ✅ Tenant-aware logging implemented
- ✅ WebSocket tenant filtering implemented
- ✅ Frontend WebSocket client updated

**Exit Criteria:**
- Event logs are isolated per tenant
- WebSocket broadcasts only reach intended tenant
- Real-time updates work correctly in multi-tenant setup

### Week 5: Phase 5 - DuckDB Hardening (P3)

**Deliverables:**
- ✅ Tenant table naming validation
- ✅ DuckDB query audit complete
- ✅ Integration tests for table isolation
- ✅ Security review of SQL injection risks

**Exit Criteria:**
- All DuckDB tables use tenant prefixes
- No possibility of cross-tenant SQL queries
- Security audit passes

### Week 6: Production Rollout & Monitoring

**Deliverables:**
- ✅ Feature flag enabled for pilot tenants (10%)
- ✅ Monitoring dashboards configured
- ✅ Alerting rules active
- ✅ Runbook documentation complete

**Rollout Plan:**
1. Enable for internal test tenant (Week 6, Day 1)
2. Enable for 10% of production tenants (Week 6, Day 3)
3. Monitor for 48 hours (no issues → proceed)
4. Enable for 50% of production tenants (Week 6, Day 5)
5. Monitor for 48 hours (no issues → proceed)
6. Enable for 100% of production tenants (Week 7, Day 1)

**Rollback Triggers:**
- Cross-tenant data leakage detected
- State read latency > 200ms (2x target)
- Redis connection failures > 5% of requests
- WebSocket broadcast failures > 1% of messages

---

## Part 8: Appendices

### Appendix A: Redis Key Naming Conventions

**Tenant-Scoped Keys:**
```
dcl:graph_state:{tenant_id}              # JSON blob, expires never
dcl:sources_added:{tenant_id}            # Set, expires never
dcl:selected_agents:{tenant_id}          # Set, expires never
dcl:source_schemas:{tenant_id}:{source}  # Hash, expires never
dcl:entity_sources:{tenant_id}           # Hash, expires never
dcl:agent_results:{tenant_id}:{agent_id} # JSON blob, expires 7d
dcl:event_log:{tenant_id}                # Stream, expires 24h
```

**Global Keys:**
```
dcl:dev_mode                     # String ("true"/"false"), expires never
dcl:llm:calls                    # Counter, expires never
dcl:llm:tokens                   # Counter, expires never
dcl:llm:calls_saved              # Counter, expires never
dcl:duckdb:lock                  # String (lock_id), expires 30s
dcl:toggle_request:{tenant_id}   # String (timestamp), expires 60s
```

**Feature Flag Keys:**
```
feature_flag:use_aam_as_source         # String ("true"/"false")
feature_flag:use_tenant_state_manager  # String ("true"/"false")
```

### Appendix B: Migration Checklist

**Pre-Migration:**
- [ ] Backup current global state to JSON file
- [ ] Create Redis keys for all tenants
- [ ] Deploy TenantStateManager code
- [ ] Configure feature flag (disabled by default)
- [ ] Run smoke tests in staging

**Migration:**
- [ ] Enable dual-write (global + Redis)
- [ ] Validate consistency (global == Redis)
- [ ] Enable feature flag for test tenant
- [ ] Run integration tests
- [ ] Monitor for 24 hours
- [ ] Enable for 10% of tenants
- [ ] Monitor for 48 hours
- [ ] Enable for 100% of tenants

**Post-Migration:**
- [ ] Monitor cross-tenant access attempts (should be 0)
- [ ] Monitor state read/write latency
- [ ] Disable dual-write (Redis only)
- [ ] Remove global state variables
- [ ] Archive migration documentation

### Appendix C: Code Examples

**Example 1: Tenant State Manager (Core Implementation)**

```python
# app/dcl_engine/tenant_state.py

import json
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
import redis

class TenantStateManager:
    """
    Central manager for tenant-scoped DCL state.
    All state access must go through this class to ensure tenant isolation.
    """
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    # Graph State Management
    def get_graph_state(self, tenant_id: str) -> Dict[str, Any]:
        key = f"dcl:graph_state:{tenant_id}"
        data = self.redis.get(key)
        if data:
            return json.loads(data)
        return {"nodes": [], "edges": [], "confidence": None, "last_updated": None}
    
    def set_graph_state(self, tenant_id: str, state: Dict[str, Any]):
        key = f"dcl:graph_state:{tenant_id}"
        state["last_updated"] = datetime.utcnow().isoformat()
        self.redis.set(key, json.dumps(state))
    
    def reset_graph_state(self, tenant_id: str):
        key = f"dcl:graph_state:{tenant_id}"
        self.redis.delete(key)
    
    # Source Connection Management
    def get_sources_added(self, tenant_id: str) -> Set[str]:
        key = f"dcl:sources_added:{tenant_id}"
        sources = self.redis.smembers(key)
        return {s.decode('utf-8') if isinstance(s, bytes) else s for s in sources}
    
    def add_source(self, tenant_id: str, source_id: str):
        key = f"dcl:sources_added:{tenant_id}"
        self.redis.sadd(key, source_id)
    
    def remove_source(self, tenant_id: str, source_id: str):
        key = f"dcl:sources_added:{tenant_id}"
        self.redis.srem(key, source_id)
    
    def clear_sources(self, tenant_id: str):
        key = f"dcl:sources_added:{tenant_id}"
        self.redis.delete(key)
    
    # Agent Selection Management
    def get_selected_agents(self, tenant_id: str) -> Set[str]:
        key = f"dcl:selected_agents:{tenant_id}"
        agents = self.redis.smembers(key)
        return {a.decode('utf-8') if isinstance(a, bytes) else a for a in agents}
    
    def set_selected_agents(self, tenant_id: str, agent_ids: List[str]):
        key = f"dcl:selected_agents:{tenant_id}"
        # Clear existing and set new
        self.redis.delete(key)
        if agent_ids:
            self.redis.sadd(key, *agent_ids)
    
    # Schema Metadata Management
    def get_source_schemas(self, tenant_id: str) -> Dict[str, Any]:
        key = f"dcl:source_schemas:{tenant_id}"
        schemas = self.redis.hgetall(key)
        return {
            k.decode('utf-8') if isinstance(k, bytes) else k: 
            json.loads(v.decode('utf-8') if isinstance(v, bytes) else v)
            for k, v in schemas.items()
        }
    
    def set_source_schema(self, tenant_id: str, source_id: str, schema: Dict[str, Any]):
        key = f"dcl:source_schemas:{tenant_id}"
        self.redis.hset(key, source_id, json.dumps(schema))
    
    # Entity-Source Mapping Management
    def get_entity_sources(self, tenant_id: str) -> Dict[str, List[str]]:
        key = f"dcl:entity_sources:{tenant_id}"
        mappings = self.redis.hgetall(key)
        return {
            k.decode('utf-8') if isinstance(k, bytes) else k:
            json.loads(v.decode('utf-8') if isinstance(v, bytes) else v)
            for k, v in mappings.items()
        }
    
    def add_entity_source(self, tenant_id: str, entity: str, source: str):
        key = f"dcl:entity_sources:{tenant_id}"
        existing = self.redis.hget(key, entity)
        sources = json.loads(existing) if existing else []
        if source not in sources:
            sources.append(source)
        self.redis.hset(key, entity, json.dumps(sources))
    
    # Event Log Management (Redis Streams)
    def add_event_log(self, tenant_id: str, message: str):
        key = f"dcl:event_log:{tenant_id}"
        self.redis.xadd(
            key,
            {"message": message, "timestamp": datetime.utcnow().isoformat()}
        )
        # Set TTL to 24 hours
        self.redis.expire(key, 86400)
    
    def get_event_logs(self, tenant_id: str, count: int = 200) -> List[str]:
        key = f"dcl:event_log:{tenant_id}"
        # Read latest N events (reverse chronological order)
        events = self.redis.xrevrange(key, count=count)
        return [event[1][b"message"].decode('utf-8') for event in events]
    
    # Validation & Security
    def validate_tenant_access(self, tenant_id: str, user_tenant_id: str):
        """Ensure user can only access their own tenant's data"""
        if tenant_id != user_tenant_id:
            raise PermissionError(
                f"User from tenant {user_tenant_id} cannot access tenant {tenant_id} data"
            )
```

**Example 2: Updated connect() Endpoint**

```python
# app/dcl_engine/app.py

@app.get("/connect", dependencies=AUTH_DEPENDENCIES)
@limiter.limit("10/minute")
async def connect(
    request: Request,
    sources: str = Query(...),
    agents: str = Query(...),
    llm_model: str = Query("gemini-2.5-flash"),
    current_user = Depends(get_current_user)  # Extract tenant_id from JWT
):
    """
    Idempotent connection endpoint with tenant isolation.
    Tenant ID is extracted from JWT token (not query param).
    """
    tenant_id = current_user.tenant_id  # From JWT
    
    source_list = [s.strip() for s in sources.split(',') if s.strip()]
    agent_list = [a.strip() for a in agents.split(',') if a.strip()]
    
    if not source_list or not agent_list:
        return JSONResponse({"error": "Missing sources or agents"}, status_code=400)
    
    # Use TenantStateManager for all state operations
    if FeatureFlagConfig.is_enabled(FeatureFlag.USE_TENANT_STATE_MANAGER):
        # NEW PATH: Tenant-scoped Redis state
        tenant_state_manager.clear_sources(tenant_id)
        tenant_state_manager.set_selected_agents(tenant_id, agent_list)
        tenant_state_manager.reset_graph_state(tenant_id)
        tenant_state_manager.add_event_log(
            tenant_id,
            f"🔌 Connecting {len(source_list)} sources with {len(agent_list)} agents"
        )
    else:
        # OLD PATH: Global state (backward compatibility)
        global GRAPH_STATE, SOURCES_ADDED, SELECTED_AGENTS
        GRAPH_STATE = {"nodes": [], "edges": [], "confidence": None}
        SOURCES_ADDED = []
        SELECTED_AGENTS = agent_list
        log(f"🔌 Connecting {len(source_list)} sources with {len(agent_list)} agents")
    
    # Connect sources (pass tenant_id to all operations)
    for source in source_list:
        await connect_source(source, llm_model, tenant_id)
    
    # Execute agents on tenant-scoped data
    if agent_executor:
        await agent_executor.execute_agents_async(agent_list, tenant_id, ws_manager)
    
    return JSONResponse({"status": "connected", "tenant_id": tenant_id})
```

**Example 3: WebSocket Tenant Filtering**

```python
# app/dcl_engine/app.py

class ConnectionManager:
    def __init__(self):
        # Map: tenant_id -> [websocket connections]
        self.tenant_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, tenant_id: str):
        await websocket.accept()
        if tenant_id not in self.tenant_connections:
            self.tenant_connections[tenant_id] = []
        self.tenant_connections[tenant_id].append(websocket)
        log(f"🔌 WebSocket client connected (tenant: {tenant_id})")
    
    def disconnect(self, websocket: WebSocket, tenant_id: str):
        if tenant_id in self.tenant_connections:
            if websocket in self.tenant_connections[tenant_id]:
                self.tenant_connections[tenant_id].remove(websocket)
        log(f"🔌 WebSocket client disconnected (tenant: {tenant_id})")
    
    async def broadcast_to_tenant(self, tenant_id: str, message: dict):
        """Send message only to connections for specific tenant"""
        connections = self.tenant_connections.get(tenant_id, [])
        disconnected = []
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for connection in disconnected:
            if connection in connections:
                connections.remove(connection)

@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    current_user = Depends(get_current_user)
):
    tenant_id = current_user.tenant_id
    await ws_manager.connect(websocket, tenant_id)
    try:
        # Send initial state (tenant-scoped)
        if FeatureFlagConfig.is_enabled(FeatureFlag.USE_TENANT_STATE_MANAGER):
            state = tenant_state_manager.get_graph_state(tenant_id)
            await websocket.send_json({"type": "state_update", "data": state})
        
        while True:
            data = await websocket.receive_text()
            if data == "refresh":
                # Broadcast to this tenant only
                await ws_manager.broadcast_to_tenant(
                    tenant_id,
                    {"type": "state_refresh"}
                )
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, tenant_id)
```

---

## Conclusion

This service decomposition plan provides a **safe, incremental path** to transform the DCL Engine from a single-tenant monolith to a multi-tenant service using the **Strangler Fig pattern**.

**Key Takeaways:**
1. **Zero Downtime:** Feature flags enable instant rollback without data loss
2. **Incremental Migration:** 5 phases spread over 5-6 weeks minimizes risk
3. **Tenant Isolation:** Redis-backed state with strict tenant prefixing
4. **Backward Compatibility:** Dual-write period ensures smooth transition
5. **Comprehensive Testing:** Multi-tenant integration tests prevent cross-contamination

**Next Steps:**
1. Review and approve this plan with stakeholders
2. Create implementation tickets for Phase 1 (Week 1-2)
3. Set up monitoring and alerting infrastructure
4. Begin TenantStateManager implementation
5. Run smoke tests in staging environment

**Questions for Review:**
- Is 5-6 week timeline acceptable for production rollout?
- Should we add PostgreSQL persistence for agent results (longer-term storage)?
- Do we need additional security audits for tenant isolation?
- Should we implement rate limiting per tenant (not just global)?

---

**Document Prepared By:** Replit AI Agent  
**Review Status:** Awaiting Stakeholder Approval  
**Last Updated:** November 15, 2025
