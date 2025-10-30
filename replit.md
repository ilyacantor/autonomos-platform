# AutonomOS - Multi-Tenant AI Orchestration Platform

## Overview
AutonomOS is a production-ready, multi-tenant SaaS backend system in Python for AI-driven task orchestration. It ensures complete data isolation, providing secure, scalable, and enterprise-grade task processing with JWT authentication and user management. The platform's core purpose is to enable advanced AI-powered data orchestration, including a Data Catalog Layer (DCL) engine for AI-driven data source connection, entity mapping, and unified view creation. 

**AAM Hybrid MVP (January 2025):** The platform now includes a production-ready implementation of the Adaptive API Mesh (Phases 1 & 2), combining Airbyte OSS for data movement with FastAPI microservices for intelligent orchestration and drift repair. **For complete technical documentation, see `aam-hybrid/AAM_FULL_CONTEXT.md`**.

## User Preferences
I prefer clear, concise explanations and direct answers. I value iterative development with frequent, small updates. Please ask for my approval before implementing major architectural changes or significant feature additions. I prefer detailed explanations for complex concepts but require brevity for straightforward ones. Do not make changes to folder `Z` and file `Y`.

## System Architecture
AutonomOS is built with FastAPI, PostgreSQL, Redis, and Python RQ, implementing a multi-tenant task orchestration platform.

**UI/UX Decisions:**
The frontend is a React/TypeScript application with a focus on a clean, minimalist design. Key UI/UX features include:
- Interactive DCL graph visualization for data mapping and orchestration, with color-coded, collision-detected labels and dynamic sizing for optimal visibility across devices.
- A hero section showcasing the product value proposition and an agent layer container for AI agents.
- Comprehensive FAQ section explaining AutonomOS capabilities and technology.
- Mobile-first design with responsive typography, touch-optimized elements, and dynamic adjustments for various screen sizes, including a horizontal Sankey layout for the DCL graph and layout-aware directional arrows for architecture flow.
- Consistent typography using Quicksand font and specific color schemes for different UI elements (e.g., green for data sources, blue for ontology, purple for agents).

**System Design Choices:**
- **Multi-Tenancy:** Achieved through `tenant_id` scoping for data isolation.
- **Microservices:** The Adaptive API Mesh (AAM) includes dedicated FastAPI microservices: Orchestrator, Auth Broker, Drift Repair Agent, and skeleton services for Schema Observer and RAG Engine.
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