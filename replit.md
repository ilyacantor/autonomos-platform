# AutonomOS - Multi-Tenant AI Orchestration Platform

## Overview
AutonomOS is a production-ready, multi-tenant SaaS backend system in Python for AI-driven task orchestration. It ensures complete data isolation, providing secure, scalable, and enterprise-grade task processing with JWT authentication and user management. The platform's core purpose is to enable advanced AI-powered data orchestration, including a Data Connectivity Layer (DCL) engine for AI-driven data source connection, entity mapping, and unified view creation. 

**AAM Production Status (November 2025):** The platform includes a production-ready implementation of the Adaptive API Mesh through Phase 3, featuring 4 operational connectors (Salesforce, FileSource, Supabase, MongoDB), complete drift detection with schema fingerprinting, autonomous auto-repair with confidence scoring, canonical event normalization, and comprehensive testing infrastructure.

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
- **AAM Monitor (November 2025):** Streamlined dashboard for Adaptive API Mesh intelligence metrics and connection health. Displays intelligence readout cards (mappings, drift events, RAG suggestions, repair confidence), performance metrics, and connection health table. Optimized for fast loading by removing service status boxes and event logs.
- **Live Flow (November 2025):** Dedicated page for real-time event visualization showing canonical events flowing through the 5-stage pipeline (Ingestion → Normalization → Intelligence → Distribution → Delivery). Features animated event pills, speed controls, pause/play functionality, and source filtering. Uses Server-Sent Events (SSE) with JWT query-token authentication for multi-tenant event streaming.
- A hero section showcasing the product value proposition and an agent layer container for AI agents.
- Comprehensive FAQ section explaining AutonomOS capabilities and technology.
- Mobile-first design with responsive typography, touch-optimized elements, and dynamic adjustments for various screen sizes, including a horizontal Sankey layout for the DCL graph and layout-aware directional arrows for architecture flow.
- Consistent typography using Quicksand font and specific color schemes for different UI elements (e.g., green for data sources, blue for ontology, purple for agents).

**System Design Choices:**
- **Multi-Tenancy:** Achieved through `tenant_id` scoping for data isolation.
- **Microservices:** The Adaptive API Mesh (AAM) includes production-ready FastAPI microservices: Orchestrator, Auth Broker, Drift Repair Agent, and Schema Observer with full drift detection capabilities.
- **Data Orchestration:** An embedded DCL engine handles AI-driven data source connection and mapping, with AOA endpoints orchestrating DCL operations via async worker tasks.
- **Authentication:** JWT-based with Argon2 hashing.
- **Task Management:** Python RQ handles asynchronous task processing, lifecycle management, error handling, and retries, supported by Redis for high-performance queuing.
- **Database:** PostgreSQL with SQLAlchemy for persistence, tracking connections, sync catalog versions, and job history.
- **LLM Abstraction:** A factory pattern (`llm_service.py`) supports multiple LLM providers (Gemini, OpenAI) via a user-selectable model.
- **Concurrency Control:** Redis-based distributed locking for safe concurrent DuckDB access within the DCL engine.
- **Frontend Framework:** React/TypeScript with Vite, served from `static/`.
- **API Documentation:** Swagger UI and ReDoc.
- **CORS:** Enhanced configuration for Replit domains.

**Technical Implementations:**
- **Adaptive API Mesh (AAM):** Utilizes Airbyte OSS for data movement (Execution Plane), FastAPI microservices for intelligence (Intelligence Plane), and PostgreSQL for connector registry (Control Plane), with Redis for inter-service communication.
- **DCL Graph:** Backend owns the data structure, emitting `source_parent` nodes with metadata and typed edges. Nodes have manually assigned depths for stable Sankey layer positioning. Optimized for fast rendering and scaling using `useLayoutEffect`, `requestAnimationFrame`, and `ResizeObserver`.
- **Ontology Table Enhancements:** Displays comprehensive mapping info including data sources, tables, fields, and a "Data Source Universe View" for raw materials hierarchy.
- **Idempotent DCL Connections:** The `/dcl/connect` endpoint clears and rebuilds DCL state.
- **Task Lifecycle:** Tasks transition through `queued`, `in_progress`, `success`, and `failed` states.

## External Dependencies
- **FastAPI:** Web framework.
- **uvicorn:** ASGI server.
- **SQLAlchemy:** ORM.
- **psycopg2-binary:** PostgreSQL adapter.
- **redis:** Python client for Redis.
- **rq (Redis Queue):** Background job processing.
- **pydantic:** Data validation.
- **python-dotenv:** Environment variable management.
- **httpx:** HTTP client.
- **duckdb:** Embedded SQL database for DCL engine.
- **pandas:** Data manipulation.
- **pyyaml:** YAML parsing.
- **google-generativeai:** Gemini AI integration.
- **openai:** OpenAI API integration.
- **Replit's PostgreSQL:** Built-in database service.
- **Upstash Redis:** External Redis for production.
- **Slack Incoming Webhooks:** For notifications.

## Recent Updates
- **November 2025:** 
  - **Live Flow Separation:** Created dedicated Live Flow page with independent navigation item, separating it from AAM Monitor for improved performance and user experience. Live Flow uses SSE with query-token JWT auth for real-time event streaming.
  - **AAM Monitor Optimization:** Simplified AAM Monitor by removing service status boxes and recent events log, significantly improving load times. Now focuses on intelligence metrics and connection health.
  - Added interactive architecture documentation viewer at `/architecture.html` with 9 comprehensive Mermaid diagrams. Primary diagram is Systems Overview (AOA) with plain-English annotations explaining what data sources ingest (Accounts, Opportunities, Contacts, Transactions), raw event types (account.created, opportunity.updated, contact.merged), AAM intelligence functions (drift detection, auto-repair, RAG matching), and key architectural junctions (normalization, event store, gateway). All diagrams use accessible high-contrast colors for optimal readability.
  - Implemented Supabase (Postgres) and MongoDB connectors with drift detection, canonical event emission, and self-healing repair capabilities. Added drift mutation endpoints, schema fingerprinting, and 4 functional test scripts for end-to-end validation.