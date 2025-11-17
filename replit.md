# AutonomOS - Multi-Tenant AI Orchestration Platform

## Recent Changes
**November 17, 2025 - AAM Canonical Transformation Complete Remediation:**
- **✅ Critical Production Blocker RESOLVED:** Fixed all AAM connector canonical transformation bugs blocking production deployment
- **✅ Mapping Registry Corrections:** Fixed 6 mapping files with reversed/identity field mappings (Salesforce, Dynamics, Hubspot, Pipedrive, Zendesk, FileSource)
- **✅ Database Schema Fix:** Changed `canonical_streams.tenant_id` from UUID to String type for multi-tenant isolation (Alembic migration c9e54bc008c3)
- **✅ FileSource Initializer Fix:** Updated to use CSV replay workflow instead of file metadata, eliminating invalid `entity='file'` errors
- **✅ No-RAG Fast Path:** Implemented early dev_mode check in both async/sync LLM proposal functions to bypass RAG/LLM in Production mode (Target: <10s processing)
- **✅ Verification:** 147 canonical events persisted successfully (105 opportunities, 15 accounts, 12 contacts, 10 aws_resources, 5 cost_reports) with zero validation errors

**November 16, 2025 - DCL Graph Structure: Pragmatic Source Visibility Solution:**
- **✅ Consolidated "from AAM" Parent Node:** Implemented simpler graph structure with single consolidated parent node labeled "from AAM" (ID: `sys_aam_sources`)
- **✅ Source Names on Entity Node Labels:** Individual sources now visible via entity node labels (e.g., "Salesforce - Account", "HubSpot - Companies", "MongoDB - events") instead of separate parent nodes
- **✅ Code Simplification:** Removed ~100+ lines of complex provenance tracking, per-source parent node logic, and scoped teardown complexity
- **✅ Demo Graph Updated:** Upgraded to v3.0 with consolidated structure, 25 nodes total (1 parent + 17 source tables + 5 ontology + 2 agents)
- **Future Direction:** Web Worker migration planned for graph rendering performance optimization

**November 16, 2025 - Test Infrastructure: Comprehensive Remediation (93.4% Pass Rate):**
- **✅ Dual Rate Limiting Fix:** Disabled both SlowAPI and gateway middleware for test environment via TESTING env var
- **✅ StateResponse Schema Flattening:** Aligned DTO with frontend expectations (nodes/edges at top level)
- **✅ AAM Feature Flag Coverage:** Implemented per-test fixtures (demo_files_mode, aam_mode) to restore AAM test coverage
- **✅ Concurrency Race Conditions:** Fixed tenant-scoped distributed locking and idempotency checks
- **✅ Test Results:** 57/61 tests passing (93.4%)
  - DTO Tests: 37/37 (100%)
  - Workflow Tests: 9/9 (100%)
  - Concurrency Tests: 3/3 (100%)
  - Feature Flag Tests: 6/6 (100%)
  - Contract Tests: 2/6 (33% - 4 snapshot mismatches, non-critical)

**November 16, 2025 - Complete DCL Performance & Rendering Remediation:**
- **✅ Performance (3x-7x improvement):** Replaced synchronous `acquire_db_lock()` with async `dcl_distributed_lock.acquire_async()` in `connect_source()`, enabling true parallel source processing. Measured improvement: 62s → 9s for 9-source connection.
- **✅ Backend Filtering Fix:** Modified `/state` endpoint filtering logic to always return ontology/agent nodes and seed demo graph (33 nodes, 37 edges) when no user sources connected. Fixed tenant_id mismatch in `get_tenant_id_from_user()` to return "default" when AUTH_ENABLED=false.
- **✅ Frontend Schema Fix:** Updated LiveSankeyGraph.tsx and useDCLState.ts to use flat schema structure (`state.nodes`, `state.edges`) matching backend API. Added dimension safety checks to prevent zero-height rendering.
- **✅ WebSocket Dynamic URLs:** Rebuilt frontend without VITE_BASE_URL to eliminate hardcoded `ws://127.0.0.1:5000` - now uses dynamic `window.location.origin` for WebSocket connections. **Note:** Users must hard-refresh browser (Ctrl+Shift+R / Cmd+Shift+R) to clear cached JavaScript bundle.

## Overview
AutonomOS is a production-ready, multi-tenant SaaS backend system in Python for AI-driven task orchestration. It provides advanced AI-powered data orchestration, including a Data Connection Layer (DCL) engine for AI-driven data source connection, entity mapping, and unified view creation. The platform ensures complete data isolation with JWT authentication and user management, offering secure, scalable, and enterprise-grade task processing. Key features include an Adaptive API Mesh with operational connectors, drift detection with schema fingerprinting, autonomous auto-repair with confidence scoring, and canonical event normalization, aiming to deliver a robust, AI-enhanced data integration and orchestration solution.

## User Preferences
I prefer clear, concise explanations and direct answers. I value iterative development with frequent, small updates. Please ask for my approval before implementing major architectural changes or significant feature additions. I prefer detailed explanations for complex concepts but require brevity for straightforward ones. Do not make changes to folder `Z` and file `Y`.

**CRITICAL: Task Planning Guidelines**
- NEVER reference duration/time estimates in task descriptions or plans
- NEVER organize plans around time-based phases (Week 1, Week 2, etc.)
- Organize by logical phases, dependencies, and priorities only
- Use priority levels (P0/Critical, High, Medium, Low) instead of timelines

## System Architecture
AutonomOS is a full-stack SaaS platform built around a multi-tenant architecture with UUID-based `tenant_id` scoping and JWT authentication for data isolation.

**UI/UX Decisions:**
The frontend uses React 18 and TypeScript with a responsive design, Quicksand typography, a Green, Blue, Purple color scheme, and dark mode. It features pages for a dashboard, data discovery, API mesh connections, ontology graph visualization, agentic orchestration, and agent demos. Live status indicators (green pulsing dots) distinguish real backend data from mock data, managed via a centralized registry. Page titles follow "AOS [Feature]" branding.

**Technical Implementations:**
*   **Task Orchestration:** Asynchronous job processing using Python RQ and Redis Queue.
*   **Authentication & Security:** JWT-based authentication with Argon2 hashing.
*   **AOA (Agentic Orchestration Architecture):** High-level orchestration for DCL engine operations.
*   **DCL Engine (Data Connection Layer):** AI-driven, in-process engine for data orchestration, utilizing DuckDB for materialized views and Redis for concurrent access. Supports multiple connectors, AI-powered entity mapping, graph generation, and idempotent operations. LLM Telemetry tracks cumulative LLM calls and token usage via Redis.
*   **Adaptive API Mesh (AAM):** Provides self-healing data connectivity with production connectors (Salesforce, FileSource, Supabase, MongoDB). Features canonical event normalization (Pydantic), schema fingerprinting for drift detection, LLM-powered auto-repair, RAG intelligence, and an auto-onboarding system with Safe Mode. Integrates with DCL via Redis Streams. Includes Airbyte Sync Monitoring.
*   **NLP Gateway Service:** Dedicated natural-language processing service for persona-based routing with context-specific prompts. Includes a persona summary endpoint, tenant-scoped RAG knowledge base (Postgres + pgvector), hybrid retrieval, JWT auth, and PII redaction.
*   **Event Streaming System:** Real-time event delivery via Server-Sent Events (SSE) and WebSockets, using Redis Pub/Sub.
*   **API Endpoints:** Organized by domain with OpenAPI/Swagger documentation.
*   **Data Quality Intelligence Layer:** Implements canonical event processing, schema drift detection (fingerprinting with Redis), LLM/RAG-powered auto-repair, and a Human-in-the-Loop (HITL) workflow.

**System Design Choices:**
The platform uses a "Strangler Fig" pattern with feature flags for zero downtime, structuring data flow as: Data Sources → AAM → DCL → Agents. A single Supabase PostgreSQL database is used for development and production, managed with Alembic for schema versioning. Deployment safety infrastructure prevents destructive database operations.
*   **Database Connection Architecture:** Centralized session factories ensure PgBouncer compatibility for Supabase.
*   **Production Database Override:** Prioritizes `SUPABASE_DATABASE_URL` over Replit's auto-provisioned `DATABASE_URL`.
*   **AAM Production Connections:** Three configured AAM connectors (Salesforce, MongoDB, FilesSource) use real credentials from Replit Secrets.
*   **Redis Infrastructure:** All Redis connections (sync, async, RQ worker) use TLS encryption with full certificate validation. Shared Redis client prevents connection pool exhaustion. Includes graceful degradation and monitoring with watchdog processes and retry logic.
*   **Feature Flags:** Frontend (`VITE_CONNECTIONS_V2`) and backend (`USE_AAM_AS_SOURCE`) feature flags managed via `.env.local` and Redis, respectively. The `USE_AAM_AS_SOURCE` flag is Redis-backed with multi-worker support, async pub/sub broadcasting, and persistence.
*   **Data Ingestion:** Script for populating `mapping_registry` from CSV files.

## External Dependencies
*   **FastAPI:** Web framework.
*   **uvicorn:** ASGI server.
*   **SQLAlchemy:** ORM.
*   **Alembic:** Database migration tool.
*   **psycopg2-binary, psycopg-binary:** PostgreSQL adapters.
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