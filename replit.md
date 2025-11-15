# AutonomOS - Multi-Tenant AI Orchestration Platform

## Recent Changes (2025-11-15)
**Critical Security Fix - Complete & Architect Approved:**
- Resolved P0 Deployment Blocker: Fixed TestCurrentUser token validation failures (0/4 → 4/4 passing)
- MockUser Email Fix: Changed from invalid `dev@autonomos.local` to valid `dev@autonomos.dev` (Pydantic EmailStr validation)
- Test Environment Auth: Enabled JWT authentication in tests via `DCL_AUTH_ENABLED=true` in conftest.py
- HTTP Status Corrections: Updated test expectations from 403 to 401 Unauthorized (correct HTTP standard)
- Auth Test Results: **10/10 passing (100%)** - complete security validation working
- Security Impact: Platform now properly validates JWT tokens, enforces authentication, and maintains multi-tenant isolation
- Architect Verified: Pass status - production-ready, no security concerns, critical blocker resolved

**Phase 3 Final Cleanup - Complete & Architect Approved:**
- Cleaned Final 3 Scripts: Removed sys.path from backfill_tenant_ids.py, dod/prime.py, functional_probe.py (production runtime now has zero sys.path)
- Fixed All LSP Diagnostics: Resolved 23 errors across 4 files (functional_probe.py, test_canonical_processor.py, canonical_event.py, conftest.py) - zero diagnostics remaining
- Fixed Auth Test Routing: Corrected endpoint paths from `/token` to `/api/v1/auth/login`, updated request format to JSON
- Legacy Code Deferred: 60+ sys.path instances in aam_hybrid/* and services/nlp-gateway/* moved to Phase 4 backlog
- Architect Verified: Pass status - production runtime clean, type-safe code, auth routing fixed

**Phase 2 Scripts/Tests Cleanup - Complete & Architect Approved:**
- Extended Package Structure: Added "scripts" and "services" to pyproject.toml packages list
- Created scripts/__init__.py: Promoted scripts directory to proper Python package
- Cleaned 20 Priority Scripts/Tests: Removed sys.path from 15 high-priority scripts + 2 test files (69→42 instances)
- Modern Execution Pattern: Scripts now run as `python -m scripts.script_name` from project root
- Absolute Imports: All cleaned files use `from app.*`, `from services.*`, `from aam_hybrid.*` patterns
- Verified Working: provision_demo_tenant, filesource_ingest, seed_salesforce all functional
- Architect Verified: Pass status - package structure works, scripts execute successfully, no regressions

**Phase 1 Architectural Remediation - Complete & Architect Approved:**
- Unified SQLAlchemy Base: All models (app, shared, aam_hybrid) now use shared.database.Base for zero schema drift
- sys.path Cleanup: Removed all core runtime sys.path manipulations from 5 critical files (security.py, main.py, aam_connections.py, aam_monitoring.py, dcl_engine/__init__.py)
- Proper Python Packaging: Created pyproject.toml defining app/shared/aam_hybrid as packages; editable install (pip install -e .) enables proper imports
- Fixed Import Paths: Converted relative imports to absolute package imports in dcl_engine/app.py (rag_engine, llm_service)
- Auth Bypass Implementation: tenant_auth_middleware now respects DCL_AUTH_ENABLED=false for development (early-exit before dependency injection)
- Production-Ready: Application boots cleanly with all services (DCL Engine, RAG Engine, AAM, Redis, RQ worker) without sys.path hacks
- Architect Verified: Pass status - no regressions, no production blockers, auth bypass works correctly

## Recent Changes (2025-11-14)
**Graph State Persistence with Version-Based Demo Seeding:**
- Implemented Redis-backed GraphStateStore for persistent graph state across app restarts
- Added tenant-scoped persistence with key pattern `dcl:graph_state:{tenant_id}`
- Comprehensive demo graph (33 nodes, 37 edges): 9 legacy sources, 5 ontology entities, 2 AI agents
- Version-based upgrade system: `demo_version` field prevents overwriting user-authored graphs
- Smart seeding: only upgrades old demo graphs, never overwrites user state (production-safe)
- Graph state loads automatically on startup with demo-ready visuals for first-time users
- Save hooks after /connect execution, reset hooks after state clears
- Graceful degradation when Redis unavailable (falls back to in-memory state)
- Manual Run control: graph executes only when user clicks Run button (no auto-run)

**Frontend Mode Toggle & Manual Run Control:**
- Fixed AAM/Legacy mode toggle: checkboxes now synchronize correctly when switching between 4 AAM sources and 9 Legacy sources
- Implemented React "lift state up" pattern: NewOntologyPage owns mode state, DCLGraphContainer receives via props (single source of truth)
- Added smart merge algorithm: preserves valid user selections when mode changes, removes incompatible sources
- Removed all auto-run behavior: graph only executes /connect when user explicitly clicks Run button (no auto-run on page load or mode toggle)
- Fixed race conditions: eliminated localStorage stale reads, execution timing issues, and closure bugs
- All changes architect-reviewed and production-ready

**AAM Connector Fundamental Architecture Fixes:**
- Fixed Decimal JSON serialization bug: connectors now use `model_dump(mode='json')` for automatic type conversion
- Migrated AAM connectors from database writes to Redis Streams publishing (production-grade event-driven architecture)
- Created AAMInitializer service that runs on startup to populate Redis Streams with canonical events
- Made AAMSourceAdapter format-flexible to handle both batch (`tables`) and individual (`entity`+`data`) event formats
- Redis Streams verified: supabase=11, mongodb=11 messages successfully published

## Overview
AutonomOS is a production-ready, multi-tenant SaaS backend system in Python for AI-driven task orchestration. It provides advanced AI-powered data orchestration, including a Data Connection Layer (DCL) engine for AI-driven data source connection, entity mapping, and unified view creation. The platform ensures complete data isolation with JWT authentication and user management, offering secure, scalable, and enterprise-grade task processing. Key features include an Adaptive API Mesh with operational connectors, drift detection with schema fingerprinting, autonomous auto-repair with confidence scoring, and canonical event normalization, aiming to deliver a robust, AI-enhanced data integration and orchestration solution.

## User Preferences
I prefer clear, concise explanations and direct answers. I value iterative development with frequent, small updates. Please ask for my approval before implementing major architectural changes or significant feature additions. I prefer detailed explanations for complex concepts but require brevity for straightforward ones. Do not make changes to folder `Z` and file `Y`.

## System Architecture
AutonomOS is a full-stack SaaS platform built around a multi-tenant architecture with UUID-based `tenant_id` scoping and JWT authentication for data isolation.

**UI/UX Decisions:**
The frontend uses React 18 and TypeScript with a responsive design, Quicksand typography, a Green, Blue, Purple color scheme, and dark mode. It features pages for a dashboard, data discovery, API mesh connections, ontology graph visualization, agentic orchestration, and agent demos. Live status indicators (green pulsing dots) distinguish real backend data from mock data, managed via a centralized registry (`frontend/src/config/liveStatus.ts`). Page titles follow "AOS [Feature]" branding.

**Technical Implementations:**
*   **Task Orchestration:** Asynchronous job processing using Python RQ and Redis Queue.
*   **Authentication & Security:** JWT-based authentication with Argon2 hashing; tokens expire in 8 hours (480 minutes).
*   **AOA (Agentic Orchestration Architecture):** High-level orchestration for DCL engine operations.
*   **DCL Engine (Data Connection Layer):** AI-driven, in-process engine for data orchestration, utilizing DuckDB for materialized views and Redis for concurrent access. Supports multiple connectors, AI-powered entity mapping, graph generation, and idempotent operations. LLM Telemetry tracks cumulative LLM calls and token usage via Redis.
*   **Adaptive API Mesh (AAM):** Provides self-healing data connectivity with production connectors (Salesforce, FileSource, Supabase, MongoDB). Features canonical event normalization (Pydantic), schema fingerprinting for drift detection, LLM-powered auto-repair, RAG intelligence, and an auto-onboarding system with Safe Mode. Integrates with DCL via Redis Streams. Includes Airbyte Sync Monitoring with real-time sync activity tracking and smart data selection.
*   **NLP Gateway Service:** Dedicated natural-language processing service for persona-based routing (CTO, CRO, COO, CFO) with context-specific prompts. Includes a persona summary endpoint, tenant-scoped RAG knowledge base (Postgres + pgvector), hybrid retrieval, JWT auth, and PII redaction.
*   **Event Streaming System:** Real-time event delivery via Server-Sent Events (SSE) and WebSockets, using Redis Pub/Sub.
*   **API Endpoints:** Organized by domain with OpenAPI/Swagger documentation.
*   **Data Quality Intelligence Layer:** Implements canonical event processing, schema drift detection (fingerprinting with Redis), LLM/RAG-powered auto-repair, and a Human-in-the-Loop (HITL) workflow.

**System Design Choices:**
The platform uses a "Strangler Fig" pattern with feature flags for zero downtime, structuring data flow as: Data Sources → AAM → DCL → Agents. A single Supabase PostgreSQL database is used for development and production, managed with Alembic for schema versioning. Deployment safety infrastructure prevents destructive database operations.
*   **Database Connection Architecture:** Centralized session factories (`SessionLocal` for sync with psycopg2, `AsyncSessionLocal` for async with psycopg3) ensure PgBouncer compatibility for Supabase.
*   **Production Database Override:** Prioritizes `SUPABASE_DATABASE_URL` over Replit's auto-provisioned `DATABASE_URL` (Neon) to maintain Supabase usage in production.
*   **AAM Production Connections:** Three configured AAM connectors (Salesforce, MongoDB, FilesSource) use real credentials from Replit Secrets.
*   **Redis Infrastructure:** All Redis connections (sync, async, RQ worker) use TLS encryption with full certificate validation (`certs/redis_ca.pem` containing GlobalSign + Redis Labs CA chain). Sync clients use `ssl_cert_reqs=CERT_REQUIRED`, async client uses `ssl_ca_certs` parameter. Shared Redis client prevents connection pool exhaustion. Includes graceful degradation and monitoring with watchdog processes and retry logic.
*   **Feature Flags:** Frontend (`VITE_CONNECTIONS_V2`) and backend (`USE_AAM_AS_SOURCE`) feature flags managed via `.env.local` and Redis, respectively. The `USE_AAM_AS_SOURCE` flag is Redis-backed with multi-worker support, async pub/sub broadcasting, and persistence.
*   **Data Ingestion:** `scripts/filesource_ingest.py` for populating `mapping_registry` from CSV files.

## External Dependencies
*   **FastAPI:** Web framework.
*   **uvicorn:** ASGI server.
*   **SQLAlchemy:** ORM.
*   **Alembic:** Database migration tool.
*   **psycopg2-binary:** PostgreSQL synchronous adapter.
*   **psycopg-binary:** PostgreSQL asynchronous adapter.
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
*   **Supabase PostgreSQL:** Primary database service.
*   **Upstash Redis:** External Redis for production.
*   **Slack Incoming Webhooks:** For notifications.
*   **AOS Discover (AOD):** External microservice for asset discovery.
*   **pgvector:** PostgreSQL extension for vector embeddings.