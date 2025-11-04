# AutonomOS - Multi-Tenant AI Orchestration Platform

## Overview
AutonomOS is a production-ready, multi-tenant SaaS backend system in Python for AI-driven task orchestration. It ensures complete data isolation, providing secure, scalable, and enterprise-grade task processing with JWT authentication and user management. The platform's core purpose is to enable advanced AI-powered data orchestration, including a Data Connection Layer (DCL) engine for AI-driven data source connection, entity mapping, and unified view creation. The platform includes a production-ready implementation of the Adaptive API Mesh, featuring operational connectors, complete drift detection with schema fingerprinting, autonomous auto-repair with confidence scoring, and canonical event normalization.

## Recent Changes (November 2025)
*   **Architectural Restructuring (Phase 0 - In Progress):** Implementing comprehensive restructuring to establish Data Sources → AAM → DCL → Agents flow. Created feature flag infrastructure (`app/config/feature_flags.py`) and data contracts (`app/contracts/`) with schema versioning. Phased approach with approval gates ensures backward compatibility while enabling progressive migration.
*   **Unified Database Architecture:** Fixed AAM database connectivity - both DCL and AAM now share single PostgreSQL database (DATABASE_URL) with separate table sets. AAM tables: `connections`, `job_history`, enums (`connectionstatus`, `jobstatus`). DCL tables: `materialized_*` views. Successfully migrated production database.
*   **LLM Counter Persistence:** Implemented Redis-based LLM call tracking with cross-process persistence. Counter persists across workflow restarts and `/connect` operations for cumulative telemetry tracking (similar to "elapsed time until next run"). Uses dependency injection pattern to avoid circular imports. Manual reset available via `POST /dcl/reset_llm_stats` endpoint.
*   **Upstash Redis Integration:** Fixed TLS/SSL connectivity (redis:// → rediss:// protocol). Implemented shared Redis client pattern to avoid 20-connection free tier limit. DCL engine now reuses main app's Redis client.
*   **Intelligent RAG Coverage Check:** Implemented cost-saving intelligence that calculates RAG coverage (matched fields with >0.8 similarity threshold) before LLM calls. When coverage ≥75%, broadcasts `rag_coverage_check` WebSocket event with coverage stats, recommendation (skip/proceed), and estimated cost savings. Auto-proceeds with LLM for MVP; frontend logs detailed stats to console. Coverage threshold: 75% to emit event, 80% to recommend skipping LLM. Designed for future UI modal implementation.

## User Preferences
I prefer clear, concise explanations and direct answers. I value iterative development with frequent, small updates. Please ask for my approval before implementing major architectural changes or significant feature additions. I prefer detailed explanations for complex concepts but require brevity for straightforward ones. Do not make changes to folder `Z` and file `Y`.

## System Architecture
AutonomOS is a full-stack SaaS platform built around a multi-tenant architecture ensuring complete data isolation via UUID-based `tenant_id` scoping and JWT authentication.

**Key Architectural Components & Features:**

*   **Task Orchestration System:** Utilizes Python RQ and Redis Queue for asynchronous background job processing with full lifecycle management, automatic retries, error handling, and per-tenant job concurrency.
*   **Authentication & Security:** Implements JWT-based authentication with Argon2 password hashing and 7-day token expiration. All API endpoints require JWT authentication.
*   **AOA (Agentic Orchestration Architecture):** High-level orchestration layer managing DCL engine operations, enforcing single active job per tenant for DCL state management (`run`, `reset`, `state`).
*   **DCL Engine (Data Connection Layer):** An AI-driven, in-process engine for data orchestration, leveraging DuckDB for materialized views and concurrent access control via Redis. It supports multiple connectors, AI-powered entity mapping, graph generation, and idempotent operations. Materialized views are exposed via PostgreSQL tables (`materialized_opportunities`, `materialized_accounts`, `materialized_contacts`) with dedicated API endpoints, automatic syncing, and tenant-specific querying. **LLM Telemetry:** Tracks cumulative LLM calls and token usage via Redis persistence (`dcl:llm:calls`, `dcl:llm:tokens`) with dependency injection pattern for counter incrementation.
*   **Adaptive API Mesh (AAM):** Provides self-healing data connectivity with four production connectors (Salesforce, FileSource, Supabase, MongoDB). Features include canonical event normalization using Pydantic, schema fingerprinting for drift detection, an auto-repair agent with LLM-powered field mapping, and RAG intelligence for semantic matching.
*   **Event Streaming System:** Real-time event delivery via Server-Sent Events (SSE) and WebSockets, supporting various event types (ingested, canonicalized, materialized, viewed, intent, journaled, drift) with Redis Pub/Sub for inter-service broadcasting.
*   **Frontend:** Built with React 18 and TypeScript, featuring pages like Dashboard, AAM Monitor, Live Flow, Ontology, Connections, Data Lineage, and an interactive architecture viewer. UI/UX design includes Quicksand typography, a distinct color scheme (Green, Blue, Purple), mobile-first responsiveness, and dark mode support.
*   **API Endpoints:** Organized by domain (Auth, AOA, DCL Views, Events, AAM, Debug) with OpenAPI/Swagger documentation.

**Technology Stack:**
*   **Backend:** FastAPI, Python RQ, PostgreSQL, Redis, DuckDB
*   **Frontend:** React 18, TypeScript, Vite, D3.js
*   **AI/ML:** Gemini/OpenAI LLMs, RAG (Pinecone, sentence-transformers)
*   **Data Connectors:** Salesforce, FileSource, Supabase, MongoDB
*   **Security:** JWT, Argon2
*   **Real-time:** WebSocket, SSE, Redis Pub/Sub

## Architectural Restructuring Plan

**Target Flow:** Data Sources → AAM → DCL → Agents

The platform is undergoing a comprehensive restructuring to implement a proper data flow architecture. This migration uses the "Strangler Fig" pattern with feature flags to ensure zero downtime and backward compatibility.

### Phase 0: Foundation (✅ Complete)
**Status:** Completed November 2025

**Deliverables:**
- Feature flag system (`app/config/feature_flags.py`) with environment variable support
- AAM→DCL data contracts (`app/contracts/aam_dcl_contract.py`) with schema versioning
- Canonical event schema (`app/contracts/canonical_event.py`) for drift detection
- Documentation updates in `replit.md`

**Key Decisions:**
- Schema versioning: All contracts include `schema_version` field (currently v1.0)
- Redis Streams for intermediate storage (not temp files)
- HITL (Human-in-the-Loop) workflow for repairs with <90% confidence
- Structured migrations using `npm run db:push` (never `--force` in production)

### Phase 1: AAM Enhancement (Pending Approval)
**Objective:** Transform AAM from monitoring-only to active connection registry

**Changes:**
- Add `connector_config` JSONB to `connections` table (with GIN indexes)
- Implement connection lifecycle manager (`aam-hybrid/core/connection_manager.py`)
- Create connector adapters: Salesforce, Supabase, MongoDB, FileSource
- New endpoints: `POST /api/v1/aam/connections`, health checks, deregistration
- Frontend: Display registered connections in AAM Monitor

**Backward Compatibility:** AAM operates standalone; no DCL integration yet.

### Phase 2: AAM → DCL Bridge (Pending Approval)
**Objective:** Create optional AAM-backed data path for DCL

**Feature Flag:** `USE_AAM_AS_SOURCE` (default: `False`)
- When `False`: Current file-based demo path (backward compatible)
- When `True`: AAM-backed DCL with normalized data

**Changes:**
- DCL source adapter pattern (`app/dcl_engine/source_loader.py`)
- AAM output formatter (`aam-hybrid/core/dcl_output_adapter.py`)
- Frontend toggle: "Data Source: [Demo Files] [AAM Connectors]"
- Both paths tested independently

**Storage:** Redis Streams for canonical event queuing

### Phase 3: Canonical Event Pipeline (Pending Approval)
**Objective:** Full canonical event normalization with drift detection and auto-repair

**Feature Flags:**
- `ENABLE_CANONICAL_EVENTS`: Canonical event normalization
- `ENABLE_DRIFT_DETECTION`: Schema fingerprinting and drift detection
- `ENABLE_AUTO_REPAIR`: Automated repair (with HITL safeguards)
- `ENABLE_HITL_WORKFLOW`: Human approval for <90% confidence repairs (default: `True`)

**Components:**
- Canonical processor with schema fingerprinting
- Drift detector (field add/remove/rename, type changes)
- Auto-repair agent with LLM/RAG mapping
- Job history tracking in `job_history` table

**HITL Workflow:**
- Confidence ≥90%: Auto-approve
- Confidence <90%: Pause and request human validation
- Store approval status in `job_history.human_verified`

**Drift Scope (Start Simple):**
- Phase 3.1: Field renaming detection
- Phase 3.2: Type changes, field additions/removals
- Phase 3.3: Complex structural changes

### Phase 4: Agent Enhancement (Pending Approval)
**Objective:** Agents receive AAM metadata for enhanced decision-making

**Changes:**
- Pass confidence scores, repair history to agents
- Data lineage visualization in Ontology view
- Repair job navigation from low-confidence indicators
- End-to-end traceability in Live Flow

**Frontend:**
- Clickable confidence badges → navigate to repair job details
- AAM → DCL → Agent flow visualization
- Field-level mapping details with transformations

### Migration Safety

**Feature Flag Strategy:**
- All new features disabled by default
- Environment variable override: `FEATURE_USE_AAM_AS_SOURCE=true`
- Check current phase: `FeatureFlagConfig.get_migration_phase()`

**Testing Protocol:**
- Test flag=False (demo path) after each phase
- Test flag=True (new path) independently
- No cross-contamination between modes

**Database Migrations:**
- Use `npm run db:push` for schema syncs
- Generate structured migration files for production
- NEVER change existing ID column types (serial ↔ varchar)
- Always check existing schema before modifying

**Approval Gates:**
- Each phase requires explicit user approval
- Detailed file change previews before implementation
- Thorough testing after each phase
- Architect review before phase completion

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
*   **duckdb:** Embedded SQL database for DCL engine.
*   **pandas:** Data manipulation.
*   **pyyaml:** YAML parsing.
*   **google-generativeai:** Gemini AI integration.
*   **openai:** OpenAI API integration.
*   **Replit's PostgreSQL:** Built-in database service.
*   **Upstash Redis:** External Redis for production.
*   **Slack Incoming Webhooks:** For notifications.