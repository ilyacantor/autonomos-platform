# AutonomOS - Multi-Tenant AI Orchestration Platform

## Overview
AutonomOS is a production-ready, multi-tenant SaaS backend system in Python for AI-driven task orchestration. It ensures complete data isolation, providing secure, scalable, and enterprise-grade task processing with JWT authentication and user management. The platform's core purpose is to enable advanced AI-powered data orchestration, including a Data Connectivity Layer (DCL) engine for AI-driven data source connection, entity mapping, and unified view creation.

**AAM Production Status (November 2025):** The platform features a fully operational Adaptive API Mesh with 4 production-ready connectors (Salesforce, FileSource, Supabase, MongoDB), complete drift detection and self-healing capabilities, schema fingerprinting, and comprehensive functional testing infrastructure. The AAM combines Airbyte OSS for data movement with FastAPI microservices for intelligent orchestration, drift repair, and canonical event normalization.

## Key Documentation
- **📊 [Architecture Visualizations](./ARCHITECTURE.md)** - Complete Mermaid diagrams of all platform components
- **🌐 [Interactive Architecture Viewer](/architecture.html)** - Web-based architecture documentation with 9 comprehensive diagrams. The primary diagram (#1) is the Systems Overview (AOA) with plain-English annotations explaining data sources, event types, AAM intelligence functions, and key junctions (accessible at `/architecture.html` on any deployment URL)
- **📘 [AAM Full Technical Docs](./aam-hybrid/AAM_FULL_CONTEXT.md)** - Adaptive API Mesh implementation details
- **🔬 [Functional Probe Guide](./scripts/QUICKSTART.md)** - End-to-end testing for Salesforce → AAM → DCL
- **📖 [AAM Dashboard Guide](./AAM_DASHBOARD_GUIDE.md)** - Monitor dashboard user guide

## User Preferences
I prefer clear, concise explanations and direct answers. I value iterative development with frequent, small updates. Please ask for my approval before implementing major architectural changes or significant feature additions. I prefer detailed explanations for complex concepts but require brevity for straightforward ones. Do not make changes to folder `Z` and file `Y`.

## System Architecture
AutonomOS is built with FastAPI, PostgreSQL, Redis, and Python RQ, implementing a multi-tenant task orchestration platform.

**UI/UX Decisions:**
The frontend is a React/TypeScript application with a focus on a clean, minimalist design. Key UI/UX features include:
- Interactive DCL graph visualization for data mapping and orchestration, with color-coded, collision-detected labels and dynamic sizing for optimal visibility across devices.
- **AAM Monitoring Dashboard:** Real-time dashboard for monitoring Adaptive API Mesh operations, including service health status, drift detection metrics, auto-repair success rates, connection health table, and recent events log. Features auto-refresh polling (10s intervals) with graceful mock data fallback. See `AAM_DASHBOARD_GUIDE.md` for complete user guide.
- A hero section showcasing the product value proposition and an agent layer container for AI agents.
- Comprehensive FAQ section explaining AutonomOS capabilities and technology.
- Mobile-first design with responsive typography, touch-optimized elements, and dynamic adjustments for various screen sizes, including a horizontal Sankey layout for the DCL graph and layout-aware directional arrows for architecture flow.
- Consistent typography using Quicksand font and specific color schemes for different UI elements (e.g., green for data sources, blue for ontology, purple for agents).

**System Design Choices:**
- **Multi-Tenancy:** Achieved through `tenant_id` scoping for data isolation across all services.
- **Microservices:** The Adaptive API Mesh (AAM) includes dedicated FastAPI microservices: Orchestrator, Auth Broker, Drift Repair Agent, and skeleton services for Schema Observer and RAG Engine.
- **Data Orchestration:** An embedded DCL engine handles AI-driven data source connection and mapping, with AOA endpoints orchestrating DCL operations via async worker tasks.
- **Authentication:** JWT-based with Argon2 hashing for secure credential storage.
- **Task Management:** Python RQ handles asynchronous task processing, lifecycle management, error handling, and retries, supported by Redis for high-performance queuing.
- **Database:** PostgreSQL with SQLAlchemy for persistence, tracking connections, sync catalog versions, job history, canonical event streams, and drift events.
- **LLM Abstraction:** A factory pattern (`llm_service.py`) supports multiple LLM providers (Gemini, OpenAI) via a user-selectable model.
- **Concurrency Control:** Redis-based distributed locking for safe concurrent DuckDB access within the DCL engine.
- **Frontend Framework:** React/TypeScript with Vite, served from `static/`.
- **API Documentation:** Swagger UI and ReDoc available at `/docs` and `/redoc`.
- **CORS:** Enhanced configuration for Replit domains and cross-origin requests.

**Technical Implementations:**
- **Adaptive API Mesh (AAM):** Three-plane architecture with Execution Plane (Airbyte OSS for data movement), Intelligence Plane (FastAPI microservices for drift detection, auto-repair, RAG matching), and Control Plane (PostgreSQL connector registry). Redis handles inter-service communication and event queuing.
- **Connector Suite:** 4 production-ready connectors with full CRUD, normalization, and drift detection:
  - **Salesforce:** CRM data connector with OAuth2 authentication
  - **FileSource:** CSV/Excel file ingestion with local storage
  - **Supabase:** PostgreSQL cloud database connector with schema mutations
  - **MongoDB:** NoSQL document database connector with BSON handling
- **Canonical Schema:** Unified data model for Accounts, Opportunities, Contacts with Pydantic validation and YAML-based field mappings stored in `services/aam/canonical/mappings/`.
- **Drift Detection:** Schema fingerprinting via SHA-256 hashing, automatic drift ticket creation in `drift_events` table, confidence scoring for auto-repair decisions, and mutation testing endpoints.
- **DCL Graph:** Backend owns the data structure, emitting `source_parent` nodes with metadata and typed edges. Nodes have manually assigned depths for stable Sankey layer positioning. Optimized for fast rendering and scaling using `useLayoutEffect`, `requestAnimationFrame`, and `ResizeObserver`.
- **Ontology Table Enhancements:** Displays comprehensive mapping info including data sources, tables, fields, and a "Data Source Universe View" for raw materials hierarchy.
- **Idempotent DCL Connections:** The `/dcl/connect` endpoint clears and rebuilds DCL state for reproducible testing.
- **Task Lifecycle:** Tasks transition through `queued`, `in_progress`, `success`, and `failed` states with full audit trail.

## External Dependencies
- **FastAPI:** Web framework for async API development.
- **uvicorn:** ASGI server for production deployment.
- **SQLAlchemy:** ORM for database operations.
- **psycopg2-binary:** PostgreSQL adapter.
- **redis:** Python client for Redis.
- **rq (Redis Queue):** Background job processing.
- **pydantic:** Data validation and serialization.
- **python-dotenv:** Environment variable management.
- **httpx:** HTTP client for external API calls.
- **duckdb:** Embedded SQL database for DCL engine.
- **pandas:** Data manipulation and transformation.
- **pyyaml:** YAML parsing for mapping configurations.
- **pymongo:** MongoDB driver for NoSQL connector.
- **google-generativeai:** Gemini AI integration.
- **openai:** OpenAI API integration.
- **Replit's PostgreSQL:** Built-in database service.
- **Upstash Redis:** External Redis for production.
- **Slack Incoming Webhooks:** For notifications and alerts.

## Testing Infrastructure
- **Functional Probes:** End-to-end testing scripts in `scripts/aam/`:
  - `ingest_seed.py` - Seeds Supabase and MongoDB, emits canonical events, verifies DCL materialization
  - `drift_supabase.py` - Tests Supabase schema drift detection and auto-repair workflow
  - `drift_mongo.py` - Tests MongoDB schema drift detection and auto-repair workflow
  - `e2e_revops_probe.py` - Full RevOps pipeline validation
- **Mutation Endpoints:** Schema mutation APIs for drift testing:
  - `/api/v1/mesh/test/supabase/mutate` - Trigger Supabase schema changes
  - `/api/v1/mesh/test/mongo/mutate` - Trigger MongoDB schema changes
- **Repair Approval:** `/api/v1/mesh/repair/approve` - Human-in-the-loop drift repair approval

## Database Schema
**Primary Tables:**
- `tenants` - Multi-tenant isolation with UUID primary keys
- `users` - User accounts with Argon2 hashed passwords
- `tasks` - Async task tracking with RQ integration
- `connections` - Data source connection registry
- `canonical_streams` - Normalized event log (append-only)
- `drift_events` - Schema drift detection and repair tickets
- `schema_changes` - Historical schema version tracking

## Environment Configuration
**Required Variables:**
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `JWT_SECRET` - JWT signing key (min 32 characters)
- `MONGODB_URI` - MongoDB connection URI
- `SUPABASE_DB_URL` - Supabase PostgreSQL connection
- `MONGODB_DB` - MongoDB database name (default: "autonomos")
- `SUPABASE_SCHEMA` - Supabase schema (default: "public")

**Optional Variables:**
- `FEATURE_USE_FILESOURCE` - Enable FileSource connector (default: true)
- `FEATURE_DRIFT_AUTOFIX` - Enable automatic drift repair (default: false)
- `DRIFT_REPAIR_CONFIDENCE_THRESHOLD` - Confidence threshold for auto-repair (default: 0.85)
- `SLACK_WEBHOOK_URL` - Slack notifications webhook

## Recent Updates
- **November 2025:**
  - ✅ **Architecture Documentation Reorganization:** Interactive architecture viewer at `/architecture.html` with 9 comprehensive Mermaid diagrams. Primary diagram is Systems Overview (AOA) with plain-English annotations explaining data sources (Salesforce, Supabase, MongoDB, CSV), raw event types (account.created, opportunity.updated, contact.merged), AAM intelligence functions (drift detection, auto-repair, RAG matching), and key architectural junctions (normalization, event store, gateway). All diagrams use accessible high-contrast colors for optimal readability. Deleted Executive View and Outcomes & KPIs diagrams to focus on technical clarity.
  - ✅ **Production-Ready Connector Suite:** Completed implementation of Supabase (PostgreSQL) and MongoDB connectors with full CRUD operations, canonical event emission, drift detection, and self-healing repair capabilities. Both connectors include:
    - Idempotent seed data methods for testing
    - YAML-based field mapping configurations
    - Schema fingerprinting via SHA-256 hashing
    - Drift mutation endpoints for testing
    - Normalization to canonical Account and Opportunity schemas
    - Error handling and connection resilience
  - ✅ **Comprehensive Testing Infrastructure:** Added 3 functional test scripts (`ingest_seed.py`, `drift_supabase.py`, `drift_mongo.py`) for end-to-end validation of AAM data flow, drift detection, and repair approval workflows.
  - ✅ **Type Safety Improvements:** Fixed MongoDB connector type checking errors for production readiness (all LSP diagnostics resolved).
  - ✅ **Environment Configuration:** Verified all required environment variables (MONGODB_URI, SUPABASE_DB_URL) are configured and operational.

## Architecture Highlights
- **Systems Overview (AOA):** Primary architecture diagram explaining end-to-end data flow from external sources (Salesforce CRM, Supabase analytics, MongoDB events, CSV legacy) through AAM intelligence (drift detection, auto-repair, RAG) to unified DCL views.
- **5-Layer Gateway Stack:** Security (JWT auth), Reliability (rate limits), Accountability (audit logs), Idempotency (duplicate request prevention), and Observability (metrics).
- **Event-Driven Architecture:** Append-only canonical event stream enables time-travel queries, audit trails, and replay capabilities.
- **Self-Healing Connectors:** Automatic detection of schema drift with confidence-scored repair suggestions and optional auto-apply based on threshold.

## File Structure
```
├── app/
│   ├── api/v1/          # API endpoints (auth, tasks, dcl, aam_mesh)
│   ├── models.py        # SQLAlchemy database models
│   ├── database.py      # Database session management
│   └── dcl_engine/      # DuckDB-based DCL engine
├── services/
│   ├── aam/
│   │   ├── connectors/  # Salesforce, FileSource, Supabase, MongoDB
│   │   ├── canonical/   # Schemas, mappings, registry
│   │   ├── drift_repair_agent.py
│   │   └── schema_observer.py
│   └── task_runner.py   # RQ worker
├── scripts/
│   └── aam/             # Functional test scripts
├── static/              # React frontend build
├── requirements.txt     # Python dependencies
└── replit.md           # This file
```

## Next Steps / Enhancements
- **Automated Drift Monitoring:** Scheduled background jobs for continuous schema fingerprinting
- **HITL Dashboard:** UI for reviewing and approving drift repair tickets
- **Notification System:** Slack/email alerts when drift detected
- **Additional Connectors:** HubSpot, Pipedrive, Dynamics 365 (skeleton YAML mappings exist)
- **RAG Engine:** Intelligent field matching using LLM embeddings (skeleton service exists)
- **Performance Optimization:** Connection pooling, caching, batch processing
