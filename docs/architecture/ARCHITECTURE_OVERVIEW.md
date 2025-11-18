# AutonomOS Platform - Architecture Overview

**Version:** 1.0  
**Last Updated:** November 18, 2025  
**Status:** Production-Ready

---

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Component Descriptions](#component-descriptions)
3. [Data Flow Diagrams](#data-flow-diagrams)
4. [Multi-Tenant Isolation](#multi-tenant-isolation)
5. [Security Model](#security-model)
6. [Scaling Considerations](#scaling-considerations)
7. [Technology Stack](#technology-stack)
8. [Design Decisions](#design-decisions)

---

## System Architecture

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         PRESENTATION LAYER                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐│
│  │   React UI  │  │ DCL Graph   │  │ AAM Monitor │  │ Live Flow  ││
│  │  (Vite SPA) │  │  Visualizer │  │  Dashboard  │  │  Real-time ││
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬─────┘│
│         │                │                │                │       │
│         └────────────────┴────────────────┴────────────────┘       │
│                              ▼                                      │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────┴──────────────────────────────────────┐
│                        API GATEWAY LAYER                            │
│  ┌──────────┐  ┌────────────┐  ┌────────┐  ┌───────┐  ┌─────────┐ │
│  │  Tracing │→ │    Auth    │→ │  Rate  │→ │ Idmp. │→ │  Audit  │ │
│  │  (trace) │  │    (JWT)   │  │  Limit │  │  Keys │  │   Log   │ │
│  └──────────┘  └────────────┘  └────────┘  └───────┘  └─────────┘ │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────┴──────────────────────────────────────┐
│                         APPLICATION LAYER                           │
│                                                                     │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │                     FastAPI Backend                         │   │
│  │  ┌─────────┐  ┌─────────┐  ┌──────────┐  ┌──────────────┐│   │
│  │  │   DCL   │  │   AAM   │  │   NLP    │  │ Bulk Mapping ││   │
│  │  │ Engine  │  │  Intel  │  │ Gateway  │  │  Job Queue   ││   │
│  │  └────┬────┘  └────┬────┘  └────┬─────┘  └──────┬───────┘│   │
│  └───────┼────────────┼────────────┼────────────────┼────────┘   │
│          │            │            │                │            │
│  ┌───────┴────┐  ┌────┴──────┐  ┌─┴────────┐  ┌────┴──────────┐ │
│  │   DCL      │  │    RAG    │  │ Persona  │  │  RQ Workers   │ │
│  │ Graph DB   │  │  Engine   │  │ Classify │  │ (Background)  │ │
│  │ (DuckDB)   │  │ (Gemini)  │  │          │  │               │ │
│  └────────────┘  └───────────┘  └──────────┘  └───────────────┘ │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │
┌──────────────────────────────────┴──────────────────────────────────┐
│                          DATA LAYER                                 │
│                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐ │
│  │   PostgreSQL     │  │      Redis       │  │     DuckDB       │ │
│  │  (Supabase)      │  │    (Upstash)     │  │   (Embedded)     │ │
│  │ ───────────────  │  │ ───────────────  │  │ ───────────────  │ │
│  │ • Users          │  │ • Job Queue      │  │ • Graph Nodes    │ │
│  │ • Tenants        │  │ • Feature Flags  │  │ • Graph Edges    │ │
│  │ • Canonical Data │  │ • Session Cache  │  │ • Temp Views     │ │
│  │ • Mappings       │  │ • Pub/Sub Events │  │ • Query Engine   │ │
│  │ • Drift Events   │  │ • Semaphores     │  │                  │ │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                      EXTERNAL DATA SOURCES                          │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────┐  ┌──────────────┐ │
│  │ Salesforce  │  │  Supabase   │  │ MongoDB  │  │  FileSource  │ │
│  │  (CRM)      │  │  (Cloud DB) │  │  (NoSQL) │  │    (CSV)     │ │
│  └─────────────┘  └─────────────┘  └──────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component Descriptions

### 1. DCL (Data Connection Layer)

**Purpose:** Unified query interface over disparate data sources

**Key Components:**

- **Graph Engine:** Builds knowledge graph of entities and relationships
- **DuckDB:** In-memory OLAP database for fast aggregations
- **Materialized Views:** Pre-computed tables (accounts, opportunities, contacts)
- **Entity Unification:** Merges duplicate records across sources

**Architecture:**

```
┌──────────────────────────────────────────────────────────────┐
│                         DCL Engine                           │
│                                                              │
│  ┌────────────────┐       ┌──────────────────┐             │
│  │ Source Loader  │──────▶│  Graph Builder   │             │
│  │ (Schemas)      │       │  (Nodes, Edges)  │             │
│  └────────────────┘       └─────────┬────────┘             │
│                                     │                       │
│  ┌────────────────┐       ┌─────────▼────────┐             │
│  │  RAG Engine    │──────▶│   DuckDB Query   │             │
│  │ (Similarity)   │       │    Engine        │             │
│  └────────────────┘       └─────────┬────────┘             │
│                                     │                       │
│  ┌────────────────┐       ┌─────────▼────────┐             │
│  │ Agent Executor │◀──────│  Materialized    │             │
│  │ (RevOps/FinOps)│       │     Views        │             │
│  └────────────────┘       └──────────────────┘             │
└──────────────────────────────────────────────────────────────┘
```

**Data Flow:**

1. Canonical events ingested from AAM
2. Graph builder creates nodes/edges
3. DuckDB materializes queryable views
4. Agents execute domain logic (RevOps, FinOps)
5. Results exposed via REST API

**Tenant Isolation:**

- DuckDB files are tenant-scoped: `registry_{tenant_id}.duckdb`
- All queries filtered by `tenant_id`
- No cross-tenant data leakage

---

### 2. AAM (Adaptive API Mesh)

**Purpose:** Self-healing data connectors with drift detection and auto-repair

**Architecture (Three-Plane Design):**

```
┌──────────────────────────────────────────────────────────────┐
│                    INTELLIGENCE PLANE                        │
│  ┌────────────┐  ┌───────────────┐  ┌──────────────────┐   │
│  │Orchestrator│──│ Drift Repair  │──│  Schema Observer │   │
│  │  (Event    │  │    Agent      │  │   (Polling)      │   │
│  │   Bus)     │  │  (RAG + LLM)  │  │                  │   │
│  └────────────┘  └───────────────┘  └──────────────────┘   │
└──────────────────────────┬───────────────────────────────────┘
                           │
┌──────────────────────────┴───────────────────────────────────┐
│                     EXECUTION PLANE                          │
│  ┌──────────────┐  ┌───────────────┐  ┌───────────────┐    │
│  │  Salesforce  │  │   Supabase    │  │    MongoDB    │    │
│  │  Connector   │  │   Connector   │  │   Connector   │    │
│  └──────┬───────┘  └───────┬───────┘  └───────┬───────┘    │
│         │                  │                  │             │
│  ┌──────▼──────────────────▼──────────────────▼──────┐     │
│  │         Canonical Schema Normalization           │     │
│  │  (CanonicalAccount, CanonicalOpportunity, etc.) │     │
│  └──────────────────────────┬───────────────────────┘     │
└──────────────────────────────┴───────────────────────────────┘
                               │
┌──────────────────────────────┴───────────────────────────────┐
│                      CONTROL PLANE                           │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────┐ │
│  │ Mapping Registry│  │ Canonical Schemas│  │  Connector │ │
│  │    (YAML)       │  │    (Pydantic)    │  │  Registry  │ │
│  └─────────────────┘  └──────────────────┘  └────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**Key Features:**

1. **Drift Detection:** Monitors source schema changes every 60s
2. **Auto-Repair:** RAG-powered field mapping suggestions (confidence > 0.85)
3. **HITL Queue:** Human review for medium-confidence mappings (0.6-0.85)
4. **Canonical Events:** Publishes to PostgreSQL `canonical_streams` table

**Event Flow:**

```
Source Change → Schema Observer → Drift Detected → RAG Analysis →
    ├─ High Confidence (>0.85) → Auto-Apply → Emit Canonical Event
    └─ Medium Confidence (0.6-0.85) → HITL Queue → Human Review
```

---

### 3. NLP Gateway

**Purpose:** Persona-based query routing and intent classification

**Components:**

- **Persona Classifier:** Routes queries to CTO/CRO/COO/CFO dashboards
- **Intent Parser:** Extracts entities and actions from natural language
- **RAG Retrieval:** Semantic search over knowledge base

**Example Flow:**

```
User Query: "What is our cloud spend this month?"
    ↓
Persona Classifier → COO (FinOps)
    ↓
Intent Parser → {entity: "cloud_spend", timeframe: "MTD"}
    ↓
RAG Retrieval → [Similar queries, historical context]
    ↓
Response Generator → Dashboard with cloud spend metrics
```

---

### 4. Job Queue (RQ + Redis)

**Purpose:** Asynchronous bulk mapping generation

**Architecture:**

```
┌───────────────────────────────────────────────────┐
│                  Job Lifecycle                    │
│                                                   │
│  ┌────────┐    ┌─────────┐    ┌──────────┐      │
│  │ Queued │───▶│ Running │───▶│Completed │      │
│  └────────┘    └────┬────┘    └──────────┘      │
│                     │                            │
│                     ▼                            │
│               ┌─────────┐                        │
│               │ Failed  │                        │
│               └─────────┘                        │
└───────────────────────────────────────────────────┘

Redis Keys:
  job:state:tenant:{tenant_id}:job:{job_id}  → Job metadata
  job:semaphore:tenant:{tenant_id}           → Concurrency control
  rq:queue:tenant:{tenant_id}:mappings       → Job queue
```

**Concurrency Control:**

- **Max concurrent jobs per tenant:** 5
- **Atomic semaphore:** Redis INCR/DECR
- **Leak detection:** Prometheus alerts on semaphore != active jobs

---

## Data Flow Diagrams

### End-to-End Data Flow

```
┌─────────────┐
│ Salesforce  │ (Source)
└──────┬──────┘
       │ Raw Event: {Name: "Acme Corp", Industry: "Tech"}
       ▼
┌──────────────────────┐
│ AAM Connector        │
│ (Salesforce Adapter) │
└──────┬───────────────┘
       │ Normalized
       ▼
┌──────────────────────────────────────────┐
│ Mapping Registry                         │
│ Salesforce.Name → canonical.account_name │
└──────┬───────────────────────────────────┘
       │ Mapped
       ▼
┌──────────────────────────────────────────┐
│ Canonical Event                          │
│ {                                        │
│   entity: "account",                     │
│   data: {account_name: "Acme Corp", ...} │
│   meta: {tenant_id, trace_id, ...}       │
│   source: {system: "salesforce", ...}    │
│ }                                        │
└──────┬───────────────────────────────────┘
       │ Published
       ▼
┌──────────────────────────────────────────┐
│ PostgreSQL: canonical_streams            │
└──────┬───────────────────────────────────┘
       │ Consumed by
       ▼
┌──────────────────────────────────────────┐
│ DCL Subscriber                           │
│ (Materializes to DuckDB + PostgreSQL)    │
└──────┬───────────────────────────────────┘
       │ Queryable via
       ▼
┌──────────────────────────────────────────┐
│ REST API: GET /api/v1/dcl/views/accounts │
└──────┬───────────────────────────────────┘
       │ Consumed by
       ▼
┌──────────────────────────────────────────┐
│ React UI                                 │
│ (Displays unified account view)          │
└──────────────────────────────────────────┘
```

---

## Multi-Tenant Isolation

### Isolation Boundaries

```
┌─────────────────────────────────────────────────────────┐
│                  TENANT ISOLATION MODEL                 │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Tenant A                                         │  │
│  │  ┌────────────┐  ┌─────────────┐  ┌───────────┐│  │
│  │  │  Database  │  │    Redis    │  │  DuckDB   ││  │
│  │  │ (Filter by │  │ (Namespaced │  │  (Scoped  ││  │
│  │  │ tenant_id) │  │    Keys)    │  │   File)   ││  │
│  │  └────────────┘  └─────────────┘  └───────────┘│  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Tenant B                                         │  │
│  │  ┌────────────┐  ┌─────────────┐  ┌───────────┐│  │
│  │  │  Database  │  │    Redis    │  │  DuckDB   ││  │
│  │  │ (Filter by │  │ (Namespaced │  │  (Scoped  ││  │
│  │  │ tenant_id) │  │    Keys)    │  │   File)   ││  │
│  │  └────────────┘  └─────────────┘  └───────────┘│  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│                  ⚠️ NO DATA LEAKAGE ⚠️                 │
└─────────────────────────────────────────────────────────┘
```

### Implementation

**PostgreSQL:**
- All tables have `tenant_id UUID NOT NULL` column
- Row-Level Security (RLS) policies enforce isolation
- Indexes on `(tenant_id, ...)` for performance

**Redis:**
- Namespaced keys: `job:state:tenant:{tenant_id}:job:{job_id}`
- Semaphore per tenant: `job:semaphore:tenant:{tenant_id}`
- No shared keys across tenants

**DuckDB:**
- Separate file per tenant: `registry_{tenant_id}.duckdb`
- Files stored in `app/dcl_engine/`
- No cross-tenant queries

**JWT Claims:**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "tenant_id": "7f8c9d0a-1b2c-3d4e-5f6g-7h8i9j0k1l2m",
  "exp": 1700308800
}
```

All API requests extract `tenant_id` from JWT and filter data accordingly.

---

## Security Model

### Authentication Flow

```
┌──────────┐         ┌──────────┐         ┌──────────┐
│  User    │────────▶│   API    │────────▶│ Database │
│ (Client) │         │ Gateway  │         │          │
└──────────┘         └──────────┘         └──────────┘
     │                     │                     │
     │ 1. POST /auth/login │                     │
     ├────────────────────▶│                     │
     │  {email, password}  │                     │
     │                     │ 2. Validate user    │
     │                     ├────────────────────▶│
     │                     │                     │
     │                     │ 3. Return user      │
     │                     │◀────────────────────┤
     │                     │                     │
     │ 4. Return JWT token │                     │
     │◀────────────────────┤                     │
     │  {access_token: ...}│                     │
     │                     │                     │
     │ 5. GET /api/v1/...  │                     │
     ├────────────────────▶│                     │
     │ Authorization: Bearer│                     │
     │                     │ 6. Verify JWT       │
     │                     │                     │
     │                     │ 7. Extract tenant_id│
     │                     │                     │
     │                     │ 8. Query with filter│
     │                     ├────────────────────▶│
     │                     │ WHERE tenant_id=... │
     │                     │                     │
     │ 9. Return data      │                     │
     │◀────────────────────┤                     │
```

### Security Layers

1. **Transport Security:** TLS 1.2+ (HTTPS)
2. **Authentication:** JWT (HS256), 30-minute expiry
3. **Authorization:** Tenant-scoped data access
4. **Rate Limiting:** 60 req/min per tenant (configurable)
5. **Audit Logging:** All mutating operations logged
6. **Input Validation:** Pydantic schemas

---

## Scaling Considerations

### Horizontal Scaling

**Application Tier:**
```yaml
# Kubernetes Deployment
replicas: 4  # Scale FastAPI pods
```

**Worker Tier:**
```bash
# Scale RQ workers
kubectl scale deployment rq-worker --replicas=8
```

**Bottlenecks:**

| Component | Scaling Strategy |
|-----------|------------------|
| **API Server** | Add pods (stateless) |
| **RQ Workers** | Add workers (stateless) |
| **PostgreSQL** | Read replicas, connection pooling (PgBouncer) |
| **Redis** | Cluster mode, sentinel for HA |
| **DuckDB** | Per-tenant files (no shared state) |

### Vertical Scaling

**Database:**
- Upgrade instance size (CPU, RAM)
- Increase connection pool (max_connections)

**Redis:**
- Increase memory limit
- Enable persistence (AOF + RDB)

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | React 18, TypeScript, Vite | SPA framework |
| **Visualization** | D3.js, Framer Motion | Graph rendering, animations |
| **Backend** | FastAPI, Python 3.11, Uvicorn | API server |
| **Auth** | JWT (python-jose), Argon2 (passlib) | Authentication |
| **Database** | PostgreSQL 14+ (Supabase), pgvector | Primary data store |
| **Cache/Queue** | Redis 6+, Python RQ | Job queue, caching |
| **OLAP** | DuckDB 1.0+ | In-memory analytics |
| **AI/LLM** | Google Gemini 2.5 Flash | RAG intelligence |
| **Embeddings** | sentence-transformers (multilingual-e5) | Semantic search |
| **Monitoring** | Prometheus, Grafana | Metrics, dashboards |
| **Logging** | structlog, Loki | Structured logging |
| **Reverse Proxy** | Nginx, Caddy | TLS termination, load balancing |
| **Deployment** | Replit, Docker, Kubernetes | Hosting |

---

## Design Decisions

### Why DuckDB for DCL?

**Pros:**
- ✅ In-memory OLAP = fast aggregations
- ✅ Embedded = no separate service
- ✅ SQL interface = familiar querying
- ✅ Multi-tenant isolation = separate files

**Cons:**
- ❌ Not a persistent store (rebuilt from canonical streams)
- ❌ Memory-constrained (not suitable for >10M rows per tenant)

**Alternative Considered:** ClickHouse (rejected: too heavyweight for embedded use)

---

### Why Redis for Job Queue?

**Pros:**
- ✅ Fast (in-memory)
- ✅ Simple (RQ library)
- ✅ Atomic operations (INCR/DECR for semaphores)

**Cons:**
- ❌ Not durable (needs persistence enabled)
- ❌ Single-threaded (limited throughput)

**Alternative Considered:** Celery + RabbitMQ (rejected: more complex setup)

---

### Why Pydantic for Validation?

**Pros:**
- ✅ Type safety (Python 3.10+ type hints)
- ✅ Auto-documentation (OpenAPI schema generation)
- ✅ Performance (Rust core)

**Cons:**
- ❌ Learning curve for complex nested models

**Alternative Considered:** Marshmallow (rejected: slower, less type-safe)

---

## Future Architecture

### Planned Enhancements

1. **Streaming Architecture:** Kafka/Kinesis for real-time event ingestion
2. **Vector Database:** Pinecone/Weaviate for large-scale RAG
3. **GraphQL API:** Apollo Server for flexible queries
4. **Service Mesh:** Istio for advanced routing and observability
5. **Event Sourcing:** Append-only event log for full audit trail

---

## References

- [Deployment Guide](../deployment/DEPLOYMENT_GUIDE.md)
- [API Reference](../api/API_REFERENCE.md)
- [Performance Tuning](../performance/PERFORMANCE_TUNING.md)
- [Security Hardening](../security/SECURITY_HARDENING.md)
