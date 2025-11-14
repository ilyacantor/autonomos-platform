# AutonomOS - Multi-Tenant AI Orchestration Platform

## Overview
AutonomOS is a production-ready, multi-tenant SaaS backend system in Python for AI-driven task orchestration. Its core purpose is to enable advanced AI-powered data orchestration, including a Data Connection Layer (DCL) engine for AI-driven data source connection, entity mapping, and unified view creation. The platform ensures complete data isolation, providing secure, scalable, and enterprise-grade task processing with JWT authentication and user management. It features a production-ready Adaptive API Mesh with operational connectors, complete drift detection with schema fingerprinting, autonomous auto-repair with confidence scoring, and canonical event normalization. The platform aims to provide a robust, AI-enhanced data integration and orchestration solution for enterprises.

## User Preferences
I prefer clear, concise explanations and direct answers. I value iterative development with frequent, small updates. Please ask for my approval before implementing major architectural changes or significant feature additions. I prefer detailed explanations for complex concepts but require brevity for straightforward ones. Do not make changes to folder `Z` and file `Y`.

## System Architecture
AutonomOS is a full-stack SaaS platform built around a multi-tenant architecture ensuring complete data isolation via UUID-based `tenant_id` scoping and JWT authentication.

**UI/UX Decisions:**
The frontend, built with React 18 and TypeScript, features a responsive UI/UX design with Quicksand typography, a distinct color scheme (Green, Blue, Purple), and dark mode support. It includes pages for AOS Control Center (dashboard), Discover (AOD integration), Connections (Adaptive API Mesh/AAM with compact KPI metrics), Ontology (Data Connectivity Layer/DCL with graph visualization), Orchestration (Agentic Orchestration Architecture/AOA with xAO metrics for all agents—internal + 3rd party), Agents (embedded FinOps and RevOps agent demos), and FAQ. **Live Status Indicators:** Components are tagged with visual "Live" badges (green pulsing dot) to distinguish real backend data from demonstration/mock data. The centralized registry (`frontend/src/config/liveStatus.ts`) manages all component statuses with tooltips explaining data provenance. **Design consistency:** Page titles follow "AOS [Feature]" branding pattern, with Live badges as sole indicators (no "Live" text in titles).

**Technical Implementations:**
*   **Task Orchestration:** Utilizes Python RQ and Redis Queue for asynchronous background job processing with full lifecycle management.
*   **Authentication & Security:** Implements JWT-based authentication with Argon2 password hashing. JWT token expiry configured to 8 hours (480 minutes) for development convenience via `JWT_EXPIRE_MINUTES` environment variable. Both registration (`/api/v1/auth/register`) and login (`/api/v1/auth/login`) endpoints return JWT tokens immediately for seamless authentication. Frontend token expiry synchronized to 8 hours to match backend (Nov 2025).
*   **AOA (Agentic Orchestration Architecture):** High-level orchestration layer managing DCL engine operations.
*   **DCL Engine (Data Connection Layer):** An AI-driven, in-process engine for data orchestration, leveraging DuckDB for materialized views and Redis for concurrent access control. Supports multiple connectors, AI-powered entity mapping, graph generation, and idempotent operations. LLM Telemetry tracks cumulative LLM calls and token usage via Redis. EVENT_LOG narration messages retained with 200-message rolling buffer for extended history (Nov 2025).
*   **Adaptive API Mesh (AAM):** Provides self-healing data connectivity with production connectors (Salesforce, FileSource, Supabase, MongoDB). Features include canonical event normalization (Pydantic), schema fingerprinting for drift detection, an auto-repair agent with LLM-powered field mapping, and RAG intelligence for semantic matching. AAM integrates with DCL via Redis Streams. Includes an auto-onboarding system for data sources with Safe Mode guardrails. **Airbyte Sync Monitoring (Nov 2025):** Real-time sync activity tracking via Airbyte Cloud API integration. Displays last sync status, records transferred, data volume, and timestamp in Connector Details. Smart data selection prioritizes most recent sync WITH actual data transferred over empty incremental syncs. 60-second caching with ThreadPoolExecutor for async compatibility.
*   **NLP Gateway Service:** A dedicated natural-language processing service providing persona-based routing (CTO, CRO, COO, CFO) with context-specific prompts. Features include persona summary endpoint (`/nlp/v1/persona/summary`) with DEMO_MODE support for deterministic mock data, tenant-scoped RAG knowledge base (Postgres + pgvector), hybrid retrieval (BM25 + vector embeddings with Reciprocal Rank Fusion), JWT auth, and PII redaction. Demo data is clearly labeled with amber "Demo" badges to distinguish from live data.
*   **Event Streaming System:** Real-time event delivery via Server-Sent Events (SSE) and WebSockets, with Redis Pub/Sub for inter-service broadcasting.
*   **API Endpoints:** Organized by domain (Auth, AOA, DCL Views, Events, AAM, Debug) with OpenAPI/Swagger documentation.
*   **Data Quality Intelligence Layer:** Implements canonical event processing (Pydantic validation, metadata enrichment), schema drift detection (fingerprinting with Redis persistence), an LLM/RAG-powered auto-repair agent with confidence scoring, and a Human-in-the-Loop (HITL) workflow (Redis + PostgreSQL for audit).

**System Design Choices:**
The platform employs a "Strangler Fig" pattern with feature flags for zero downtime, restructuring towards a unified data flow: Data Sources → AAM → DCL → Agents. A single Supabase PostgreSQL database is used for both development and production, handling DCL and AAM data. Alembic is used for production-ready database schema versioning and migrations, automatically applied on server startup. Deployment safety infrastructure is in place to prevent destructive database operations.

**Database Connection Architecture (Nov 2025):**
*   **Unified Database Access:** All database operations use centralized session factories from `app/database.py`:
    *   Sync: `SessionLocal` (psycopg2) for synchronous operations
    *   Async: `AsyncSessionLocal` (psycopg3) for asynchronous operations
*   **PgBouncer Compatibility:** Switched from asyncpg to psycopg3's async driver to eliminate prepared statement conflicts with Supabase PgBouncer transaction mode. No more `DuplicatePreparedStatementError`!
*   **AAM Integration:** `aam_hybrid/shared/database.py` imports and forwards to shared session factories instead of creating duplicate engines, ensuring consistent PgBouncer-safe connections across all AAM operations.

**AAM Production Connections (Nov 2025):**
Platform includes 3 configured AAM connectors using real external credentials stored in Replit Secrets:
*   **Salesforce Production:** Connects to real Salesforce.com org (`orgfarm-2c8d7db716-dev-ed.develop.my.salesforce.com`) via `SALESFORCE_ACCESS_TOKEN` and `SALESFORCE_INSTANCE_URL` environment secrets. OAuth tokens require periodic refresh.
*   **MongoDB Production:** Connects to real MongoDB Atlas cluster via `MONGODB_URI` environment secret. Fully operational for live data ingestion.
*   **FilesSource Demo:** Local CSV file connector reading from `mock_sources/` directory with connection-scoped mapping registry and drift detection enabled.

All connection credentials use `env_ref` type in `connector_config` for secure secret management. Connection endpoint: `POST /api/v1/aam/connections` (requires JWT authentication).

**Feature Flags:**
*   **VITE_CONNECTIONS_V2** (default: `false`): Frontend feature flag for typed AAM connectors client with drift metadata. When `true`, ConnectPage uses `useConnectorsV2()` hook with OpenAPI-generated TypeScript types and displays DRIFT badges for connectors with detected schema drift. Set via `.env.local` (frontend).

**Data Ingestion:**
*   **FilesSource CSV Ingest:** Use `scripts/filesource_ingest.py` to populate `mapping_registry` from CSV files in `mock_sources/`. This enables field-level mapping visibility for FilesSource connections in the Connections tab.
    ```bash
    # Ingest FilesSource CSV data (idempotent)
    python scripts/filesource_ingest.py --connection-id 10ca3a88-5105-4e24-b984-6e350a5fa443 --namespace demo
    
    # Verify mapping count
    # SQL: SELECT COUNT(*) FROM mapping_registry WHERE connection_id='<connection_uuid>' AND tenant_id='<tenant_id>';
    
    # Fetch connectors with drift metadata (requires JWT)
    curl -H "Authorization: Bearer $JWT" http://localhost:5000/api/v1/aam/connectors
    # Returns: {"connectors": [{"id": "...", "name": "...", "source_type": "...", "status": "...", 
    #                            "mapping_count": 0, "has_drift": false, "last_event_type": null, 
    #                            "last_event_at": null}], "total": 1}
    ```

**AAM Performance Notes:**
*   **Mapping Registry Schema:** Database migration `789c8385e9b1` added `connection_id UUID` column to `mapping_registry` table with index `ix_mapping_registry_connection_id` for connection-scoped mapping counts (Nov 2025).
*   **Connection-Scoped Mapping Counts:** `/api/v1/aam/connectors` endpoint filters `mapping_registry` by `connection_id` (not `vendor`) to prevent overcounting when multiple connections of the same type exist in a tenant.
*   **Backward Compatibility:** `vendor` column retained for transition period; both `vendor` and `connection_id` populated by ingest scripts.
*   **Performance Monitoring:** Endpoint logs latency (`latency_ms`) and total connector count for observability.
*   **Health Check:** `GET /api/v1/aam/healthz` provides lightweight DB connectivity test respecting `AAM_CONNECTORS_SYNC` feature flag.
*   **OpenAPI Contract (Nov 2025):** `/api/v1/aam/connectors` endpoint uses `ConnectorDTO` response model with drift metadata (`has_drift`, `last_event_type`, `last_event_at`). Batched drift query uses `ROW_NUMBER()` window function to avoid N+1 queries.
*   **TypeScript Client Regeneration:** When ConnectorDTO schema changes, manually update `frontend/src/api/generated/connectors.ts` to match the new schema from `/openapi.json`. Contract tests in `tests/api/test_aam_connectors.py` validate DTO compliance.

## External Dependencies
*   **FastAPI:** Web framework.
*   **uvicorn:** ASGI server.
*   **SQLAlchemy:** ORM.
*   **Alembic:** Database migration tool.
*   **psycopg2-binary:** PostgreSQL sync adapter.
*   **psycopg-binary:** PostgreSQL async adapter (PgBouncer-safe).
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

## Deployment Optimizations
*   **Build Optimization:** Vite configured with code splitting (react-vendor, d3-vendor), CSS splitting, and esbuild minification
*   **Static Assets:** Automated cleanup via `emptyOutDir: true`, reduced from 35MB to 1.6MB
*   **.dockerignore:** Comprehensive exclusion list (node_modules, tests, docs, dev files) to minimize deployment image size
*   **Dependencies:** Production-only requirements.txt (removed duplicates and test dependencies)
*   **Build Script:** Uses `npm ci` for faster, reproducible builds