# AutonomOS - Multi-Tenant AI Orchestration Platform

## Overview
AutonomOS is a production-ready, multi-tenant SaaS backend system in Python for AI-driven task orchestration. Its core purpose is to enable advanced AI-powered data orchestration, including a Data Connection Layer (DCL) engine for AI-driven data source connection, entity mapping, and unified view creation. The platform ensures complete data isolation, providing secure, scalable, and enterprise-grade task processing with JWT authentication and user management. It features a production-ready Adaptive API Mesh with operational connectors, complete drift detection with schema fingerprinting, autonomous auto-repair with confidence scoring, and canonical event normalization.

## Recent Changes (November 2025)
*   **Demo Features: Scan Switch, Dashboard Embedding & HITL Workflow (Nov 7):** Implemented three major demo features: (1) **Demo Scan Switch** in Control Center with DemoScanPanel component and POST `/aoa/demo-scan` endpoint that triggers full asset discovery from AOD, categorizes assets by risk level (high 15%, medium 25%, low 60%), and returns scan statistics; (2) **AOD Dashboard Embedding** in Discovery tab via responsive iframe embedding `https://aos-discover.replit.app` with "open in new tab" option; (3) **HITL Decision Queue** component (HITLQueue) showing high/medium risk assets requiring human review with filtering (all/high/medium), decision panel (approve/reject/flag), and detailed asset metadata display. Demo flow: User clicks scan → AOD discovers assets → Results shown in stats → High/medium risk assets appear in HITL queue for human decisions on edge cases. Frontend uses mock data for demonstration; backend endpoint fully operational with AOD integration.
*   **API-Based E2E Microservice Integration (Nov 7):** Implemented CTO-mandated microservice architecture for AOS Discover service integration. Created POST `/aoa/discover` endpoint that makes network API calls to external AOS Discover service (AOD) with comprehensive logging. Built DiscoverConsole frontend component with NLP input interface. Established AOD API contract with Pydantic models (DiscoveryRequest, DiscoveryResponse, DiscoveryHandoff) for type-safe communication. Flow: User NLP input → Backend AOA → Network call to AOD service → JSON response → Agent recommendations → Frontend display. All three logging points implemented (sent data, received JSON, agent handoff) for debugging. AOD_BASE_URL environment variable configures external service endpoint (default: http://localhost:8000).
*   **Single Database Architecture (Nov 7):** Resolved publishing errors by consolidating to Supabase PostgreSQL as the single database for both development and production. Removed accidentally-created Replit Neon database that was causing schema mismatches. Fixed PgBouncer prepared statement warnings by adding `statement_cache_size=0` to all async database connections. Auto-migrations re-enabled in `start.sh`. System now runs cleanly on Supabase with 36 tables at Alembic version 5a9d6371e18c.
*   **Deployment Safety Infrastructure (Nov 7):** Implemented comprehensive deployment guardrails to prevent Replit Publishing from proposing destructive DROP TABLE operations. Added idempotent production baseline stamping script (`stamp_prod_baseline.sh`), pre-publish safety guard (`deploy_guard.sh`), database audit tooling (`db_audit.sh`), and emergency `DISABLE_AUTO_MIGRATIONS` flag in `start.sh`. Created `DEPLOYMENT_POLICY.md` establishing Alembic as single source of truth for migrations. Makefile targets added for `make deploy-check`, `make db-audit`, and `make stamp-prod`. Root cause: production database was never stamped with Alembic baseline, causing Alembic to think prod was unmigrated and generate destructive migrations.
*   **Alembic Migration System:** Implemented Alembic for production-ready database schema versioning and migrations. Replaces manual `create_all()` approach with proper migration tracking. Migrations run automatically on server startup via `alembic upgrade head` in `start.sh`. Baseline migration created for existing production database to avoid data loss.
*   **FileSource → AAM → DCL Integration Complete:** FileSource connector now publishes AWS cost data (aws_resources, cost_reports) to Redis streams using `dcl_output_adapter` with table-based payload format. FinOps Pilot successfully receives and processes 15 records (10 resources + 5 cost reports).
*   **Heuristic Filtering Fix:** Added "filesource" to FINOPS_SOURCES in heuristic domain filtering logic to ensure correct routing of AWS cost data to FinOps Pilot (previously misrouted to RevOps).
*   **LLM/RAG Behavior:** Confirmed that LLM/RAG intelligence layer operates identically in both AAM mode and Legacy mode. The `dev_mode` flag controls LLM usage, not the data source type. RAG retrieval always runs in both modes; LLM calls are skipped in Prod Mode (dev_mode=false), falling back to heuristics.

## User Preferences
I prefer clear, concise explanations and direct answers. I value iterative development with frequent, small updates. Please ask for my approval before implementing major architectural changes or significant feature additions. I prefer detailed explanations for complex concepts but require brevity for straightforward ones. Do not make changes to folder `Z` and file `Y`.

## System Architecture
AutonomOS is a full-stack SaaS platform built around a multi-tenant architecture ensuring complete data isolation via UUID-based `tenant_id` scoping and JWT authentication.

**Key Architectural Components & Features:**

*   **Task Orchestration System:** Utilizes Python RQ and Redis Queue for asynchronous background job processing with full lifecycle management.
*   **Authentication & Security:** Implements JWT-based authentication with Argon2 password hashing.
*   **AOA (Agentic Orchestration Architecture):** High-level orchestration layer managing DCL engine operations.
*   **DCL Engine (Data Connection Layer):** An AI-driven, in-process engine for data orchestration, leveraging DuckDB for materialized views and Redis for concurrent access control. It supports multiple connectors, AI-powered entity mapping, graph generation, and idempotent operations. Materialized views are exposed via PostgreSQL tables. LLM Telemetry tracks cumulative LLM calls and token usage via Redis.
*   **Adaptive API Mesh (AAM):** Provides self-healing data connectivity with production connectors (Salesforce, FileSource, Supabase, MongoDB). Features include canonical event normalization (Pydantic), schema fingerprinting for drift detection, an auto-repair agent with LLM-powered field mapping, and RAG intelligence for semantic matching. AAM integrates with DCL via Redis Streams for data ingestion.
    *   **FileSource Connector:** Ingests CSV data files, normalizes events to canonical format, persists to PostgreSQL for audit trail, and publishes batched payloads to Redis streams (`aam:dcl:{tenant_id}:filesource`) using `dcl_output_adapter` for table-based format. Includes DecimalEncoder for financial data serialization. Recognized as FinOps source in heuristic filtering.
    *   **Data Flow:** FileSource → Canonical Events (DB + Redis) → AAM Source Adapter → DCL Materialized Views → Agent Consumption
    *   **Domain Filtering:** Heuristic-based routing ensures data reaches appropriate agents. FinOps sources (snowflake, sap, netsuite, legacy_sql, filesource) route to FinOps Pilot. RevOps sources (dynamics, salesforce, hubspot) route to RevOps Pilot. Unknown sources pass through without filtering for extensibility.
*   **Event Streaming System:** Real-time event delivery via Server-Sent Events (SSE) and WebSockets, with Redis Pub/Sub for inter-service broadcasting.
*   **Frontend:** Built with React 18 and TypeScript, featuring a responsive UI/UX design with Quicksand typography, a distinct color scheme (Green, Blue, Purple), and dark mode support. Includes pages for Dashboard, AAM Monitor, Live Flow, Ontology, Connections, Data Lineage, and an interactive architecture viewer.
*   **API Endpoints:** Organized by domain (Auth, AOA, DCL Views, Events, AAM, Debug) with OpenAPI/Swagger documentation.
*   **System Design:** The platform employs a "Strangler Fig" pattern with feature flags for zero downtime, restructuring towards a unified data flow: Data Sources → AAM → DCL → Agents. This includes a unified PostgreSQL database for DCL and AAM, Redis-based LLM counter persistence, and intelligent RAG coverage checks.
*   **Data Quality Intelligence Layer:** Implements canonical event processing (Pydantic validation, metadata enrichment), schema drift detection (fingerprinting with Redis persistence), an LLM/RAG-powered auto-repair agent with confidence scoring, and a Human-in-the-Loop (HITL) workflow (Redis + PostgreSQL for audit). Metadata flows end-to-end, providing data quality insights to agents and visualizations in the frontend.

## Database Migration Workflow

**Migration System:** Alembic (production-ready schema versioning for SQLAlchemy)

### How Migrations Work

1. **Automatic Migrations on Startup:**
   - Every server startup runs `alembic upgrade head` automatically
   - Ensures database schema is always up-to-date
   - Configured in `start.sh` script

2. **Creating New Migrations:**
   ```bash
   # After changing models in app/models.py or aam_hybrid/shared/models.py
   alembic revision --autogenerate -m "Description of changes"
   
   # Review the generated migration in alembic/versions/
   # Test locally, then commit to git
   ```

3. **Applying Migrations:**
   ```bash
   # Apply pending migrations
   alembic upgrade head
   
   # Rollback last migration
   alembic downgrade -1
   
   # Check current migration version
   alembic current
   ```

4. **First-Time Production Setup:**
   ```bash
   # Run ONCE when first deploying Alembic to existing database
   ./scripts/stamp_baseline.sh
   
   # This marks current production schema as baseline
   # Future migrations will only track changes from this point
   ```

### Multi-Base Architecture

The project uses two SQLAlchemy Base objects:
- `app.models.Base` - Main platform tables (users, tasks, canonical_streams, etc.)
- `aam_hybrid.shared.models.Base` - AAM connector tables (connections, job_history, etc.)

Alembic is configured in `alembic/env.py` to merge metadata from both Base objects, ensuring all tables are tracked in a single migration history.

### Important Notes

- **Never manually edit production database schema** - Use Alembic migrations
- **Baseline migration is empty** - Existing production tables are preserved
- **Test migrations locally first** - Use development database before production deploy
- **Migrations are version-controlled** - Committed to git with code changes

## External Dependencies
*   **FastAPI:** Web framework.
*   **uvicorn:** ASGI server.
*   **SQLAlchemy:** ORM.
*   **Alembic:** Database migration tool.
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