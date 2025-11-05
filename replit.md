# AutonomOS - Multi-Tenant AI Orchestration Platform

## Overview
AutonomOS is a production-ready, multi-tenant SaaS backend system in Python for AI-driven task orchestration. Its core purpose is to enable advanced AI-powered data orchestration, including a Data Connection Layer (DCL) engine for AI-driven data source connection, entity mapping, and unified view creation. The platform ensures complete data isolation, providing secure, scalable, and enterprise-grade task processing with JWT authentication and user management. It features a production-ready Adaptive API Mesh with operational connectors, complete drift detection with schema fingerprinting, autonomous auto-repair with confidence scoring, and canonical event normalization.

## User Preferences
I prefer clear, concise explanations and direct answers. I value iterative development with frequent, small updates. Please ask for my approval before implementing major architectural changes or significant feature additions. I prefer detailed explanations for complex concepts but require brevity for straightforward ones. Do not make changes to folder `Z` and file `Y`.

## System Architecture
AutonomOS is a full-stack SaaS platform built around a multi-tenant architecture ensuring complete data isolation via UUID-based `tenant_id` scoping and JWT authentication.

**Key Architectural Components & Features:**

*   **Task Orchestration System:** Utilizes Python RQ and Redis Queue for asynchronous background job processing with full lifecycle management, automatic retries, error handling, and per-tenant job concurrency.
*   **Authentication & Security:** Implements JWT-based authentication with Argon2 password hashing and 7-day token expiration. All API endpoints require JWT authentication.
*   **AOA (Agentic Orchestration Architecture):** High-level orchestration layer managing DCL engine operations, enforcing a single active job per tenant for DCL state management.
*   **DCL Engine (Data Connection Layer):** An AI-driven, in-process engine for data orchestration, leveraging DuckDB for materialized views and concurrent access control via Redis. It supports multiple connectors, AI-powered entity mapping, graph generation, and idempotent operations. Materialized views are exposed via PostgreSQL tables with dedicated API endpoints, automatic syncing, and tenant-specific querying. LLM Telemetry tracks cumulative LLM calls and token usage via Redis persistence.
*   **Adaptive API Mesh (AAM):** Provides self-healing data connectivity with four production connectors (Salesforce, FileSource, Supabase, MongoDB). Features include canonical event normalization using Pydantic, schema fingerprinting for drift detection, an auto-repair agent with LLM-powered field mapping, and RAG intelligence for semantic matching.
*   **Event Streaming System:** Real-time event delivery via Server-Sent Events (SSE) and WebSockets, supporting various event types with Redis Pub/Sub for inter-service broadcasting.
*   **Frontend:** Built with React 18 and TypeScript, featuring pages like Dashboard, AAM Monitor, Live Flow, Ontology, Connections, Data Lineage, and an interactive architecture viewer. UI/UX design includes Quicksand typography, a distinct color scheme (Green, Blue, Purple), mobile-first responsiveness, and dark mode support.
*   **API Endpoints:** Organized by domain (Auth, AOA, DCL Views, Events, AAM, Debug) with OpenAPI/Swagger documentation.
*   **System Design:** The platform is undergoing a comprehensive restructuring to implement a proper data flow architecture (Data Sources → AAM → DCL → Agents) using a "Strangler Fig" pattern with feature flags for zero downtime and backward compatibility. This includes a unified PostgreSQL database for DCL and AAM, Redis-based LLM counter persistence, and intelligent RAG coverage checks to optimize LLM calls.

## Recent Changes

### Phase 2.5: AAM Connector Integration (COMPLETED - 2025-11-04)

**Objective:** Establish production-ready AAM → DCL data bridge with end-to-end validation.

**Deliverables:**
1. **Data Ingestion Pipeline** (`aam-hybrid/core/data_ingestion.py`):
   - CSV → Canonical events transformation using Pydantic models
   - Support for 5 connectors: Salesforce, HubSpot, Dynamics, Supabase, MongoDB
   - Field mapping with proper data type inference

2. **DCL Output Adapter** (`aam-hybrid/core/dcl_output_adapter.py`):
   - Batching: Groups events by entity type, chunks up to 200 records (configurable)
   - Redis Streams publishing: `aam:dcl:{tenant_id}:{connector}`
   - Atomic batch IDs for idempotent processing
   - MAXLEN trimming (1000 entries default, configurable)

3. **AAMSourceAdapter** (`app/dcl_engine/source_loader.py`):
   - Redis consumer groups: `dcl_engine:{tenant_id}`
   - Message acknowledgment (XACK) after successful processing
   - Idempotent batch tracking in Redis SET with 24h TTL (configurable)
   - Non-blocking reads with proper error handling

4. **Configuration Management:**
   - `AAM_BATCH_CHUNK_SIZE`: Batch chunking size (default: 200)
   - `AAM_MAX_SAMPLES_PER_TABLE`: Schema sampling limit (default: 8)
   - `AAM_REDIS_STREAM_MAXLEN`: Stream trimming threshold (default: 1000)
   - `AAM_IDEMPOTENCY_TTL`: Duplicate prevention window (default: 86400s / 24h)
   - All externalized via environment variables for production tuning

5. **Documentation** (`aam-hybrid/README-CONFIGURATION.md`):
   - Complete parameter reference with defaults and examples
   - MAXLEN policy explanation and monitoring guide
   - Production tuning scenarios (high-volume, low-latency, audit/replay)
   - Troubleshooting section with common issues
   - Security considerations

**Validation Results:**
- ✅ 41 canonical events published across 5 connectors
- ✅ Consumer groups operational with proper XACK handling
- ✅ Idempotent processing confirmed (no duplicates)
- ✅ WebSocket events: `mapping_progress`, `sources_connected`
- ✅ End-to-end flow: CSV → AAM → Redis Streams → DCL → WebSocket
- ✅ Tenant alignment: Default tenant "default" matches DCL expectations
- ✅ Feature flag `USE_AAM_AS_SOURCE=true` enables AAM path

**Architecture Pattern:**
```
CSV Files (schemas/) → Data Ingestion → Canonical Events → 
DCL Output Adapter → Redis Streams (aam:dcl:{tenant}:{connector}) → 
AAMSourceAdapter (Consumer Groups) → DCL Engine → Materialized Views
```

**Next Phase:** Phase 3 - DCL → Agents integration with proper agent invocation from unified views.

### Phase 3: DCL → Agents Integration (COMPLETED - 2025-11-05)

**Objective:** Complete end-to-end data flow by implementing agent execution engine that consumes AAM-backed materialized views and delivers actionable insights.

**Deliverables:**
1. **AgentExecutor Class** (`app/dcl_engine/agent_executor.py`):
   - Async execution with `execute_agents_async()` method
   - Tenant-scoped caching with `AGENT_RESULTS_CACHE`
   - WebSocket event broadcasting (agent_started, agent_completed, agent_failed)
   - Prepares agent inputs from DuckDB materialized views
   - Stores results with timestamp and metadata
   - API endpoint: `/dcl/agents/{agent_id}/results` for retrieving cached results

2. **Agent Executor Initialization** (`app/main.py`):
   - Initialized in main app startup_event (FastAPI sub-app limitation workaround)
   - Sets both `dcl_app.agent_executor` and global `dcl_app_module.agent_executor`
   - Shares Redis client from main app
   - Confirmed initialization: "✅ DCL Agent Executor initialized successfully"

3. **Critical Bug Fixes:**
   - **Redis xreadgroup Blocking** (CRITICAL): Changed `block=0` to `block=None` in AAMSourceAdapter
     - Root cause: Redis interprets `block=0` as "wait forever", causing /dcl/connect to hang indefinitely
     - Fix enables truly non-blocking reads from Redis Streams
     - /dcl/connect now completes in ~1.1s instead of timing out
   - **Global Variable Initialization**: Set `dcl_app_module.agent_executor` in main app startup
     - Fix ensures agent_executor is accessible throughout DCL engine

4. **Agent Execution Architecture Fix** (CRITICAL):
   - **REMOVED** unreachable agent execution code from `connect_source()` (per-source invocation)
   - **RELOCATED** agent execution to `/connect` endpoint after `asyncio.gather()` completes
   - Agents now execute ONCE after ALL sources finish materializing views
   - Added DuckDB existence check to gracefully handle empty data scenarios
   - Comprehensive error handling with graceful fallback

**Validation Results:**
- ✅ Agent execution triggers at correct time (post-gather, after all sources complete)
- ✅ WebSocket events: `agent_started`, `agent_completed`, `sources_connected`
- ✅ Results cached and accessible via `/dcl/agents/{agent_id}/results` API
- ✅ Graceful handling when no materialized views available
- ✅ /dcl/connect completes successfully (~1.1s response time)
- ✅ End-to-end flow validated: CSV → AAM → Redis Streams → DCL → AgentExecutor

**Architecture Pattern (Achieved):**
```
CSV Files → AAM Ingestion → Redis Streams (aam:dcl:{tenant}:{connector}) → 
AAMSourceAdapter (Consumer Groups) → DCL Materialized Views (DuckDB) → 
AgentExecutor (Post-Gather) → Cached Results → API Endpoints
```

**Key Architectural Decisions:**
- Agent execution runs ONCE after ALL sources complete (not per-source in parallel)
- DuckDB existence check prevents errors when no data available
- Non-blocking Redis reads enable fast response times
- Graceful degradation when materialized views don't exist

**Known Behavior:**
- AAM sources consumed on first connection; subsequent connections find no new messages (by design)
- Consumer groups track processed batches; need fresh ingestion or group reset for re-processing
- Agent execution skipped when DuckDB doesn't exist (logged: "No materialized views available - skipping agent execution")

## External Dependencies
*   **FastAPI:** Web framework.
*   **uvicorn:** ASGI server.
*   **SQLAlchemy:** ORM.
*   **psycopg2-binary:** PostgreSQL adapter.
*   **redis:** Python client for Redis.
*   **rq (Redis Queue):** Background job processing.
*   **pydantic:** Data validation.
*   **python-dotenv:** Environment variable management.
*   **httpx:** HTTP client.
*   **duckdb:** Embedded SQL database.
*   **pandas:** Data manipulation.
*   **pyyaml:** YAML parsing.
*   **google-generativeai:** Gemini AI integration.
*   **openai:** OpenAI API integration.
*   **Replit's PostgreSQL:** Built-in database service.
*   **Upstash Redis:** External Redis for production.
*   **Slack Incoming Webhooks:** For notifications.