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
*   **Authentication & Security:** Implements JWT-based authentication with Argon2 password hashing.
*   **AOA (Agentic Orchestration Architecture):** High-level orchestration layer managing DCL engine operations.
*   **DCL Engine (Data Connection Layer):** An AI-driven, in-process engine for data orchestration, leveraging DuckDB for materialized views and Redis for concurrent access control. Supports multiple connectors, AI-powered entity mapping, graph generation, and idempotent operations. LLM Telemetry tracks cumulative LLM calls and token usage via Redis.
*   **Adaptive API Mesh (AAM):** Provides self-healing data connectivity with production connectors (Salesforce, FileSource, Supabase, MongoDB). Features include canonical event normalization (Pydantic), schema fingerprinting for drift detection, an auto-repair agent with LLM-powered field mapping, and RAG intelligence for semantic matching. AAM integrates with DCL via Redis Streams. Includes an auto-onboarding system for data sources with Safe Mode guardrails.
*   **NLP Gateway Service:** A dedicated natural-language processing service providing persona-based routing (CTO, CRO, COO, CFO) with context-specific prompts. Features include persona summary endpoint (`/nlp/v1/persona/summary`) with DEMO_MODE support for deterministic mock data, tenant-scoped RAG knowledge base (Postgres + pgvector), hybrid retrieval (BM25 + vector embeddings with Reciprocal Rank Fusion), JWT auth, and PII redaction. Demo data is clearly labeled with amber "Demo" badges to distinguish from live data.
*   **Event Streaming System:** Real-time event delivery via Server-Sent Events (SSE) and WebSockets, with Redis Pub/Sub for inter-service broadcasting.
*   **API Endpoints:** Organized by domain (Auth, AOA, DCL Views, Events, AAM, Debug) with OpenAPI/Swagger documentation.
*   **Data Quality Intelligence Layer:** Implements canonical event processing (Pydantic validation, metadata enrichment), schema drift detection (fingerprinting with Redis persistence), an LLM/RAG-powered auto-repair agent with confidence scoring, and a Human-in-the-Loop (HITL) workflow (Redis + PostgreSQL for audit).

**System Design Choices:**
The platform employs a "Strangler Fig" pattern with feature flags for zero downtime, restructuring towards a unified data flow: Data Sources → AAM → DCL → Agents. A single Supabase PostgreSQL database is used for both development and production, handling DCL and AAM data. Alembic is used for production-ready database schema versioning and migrations, automatically applied on server startup. Deployment safety infrastructure is in place to prevent destructive database operations.

**Database Connection Workarounds:**
*   **PgBouncer Prepared Statement Conflict:** Supabase PgBouncer runs in transaction mode which conflicts with asyncpg's prepared statement caching. The `/api/v1/aam/connectors` endpoint uses synchronous SQLAlchemy (psycopg2) with explicit `with SessionLocal() as db:` context manager to ensure proper connection cleanup and avoid pool exhaustion. This is a controlled workaround until either (a) asyncpg's `prepare_threshold=0` configuration is tested, or (b) a dedicated session-mode PgBouncer pool is configured.
*   **Async Engine Settings:** All async engines are configured with `statement_cache_size: 0` and `prepared_statement_cache_size: 0` to minimize PgBouncer conflicts for remaining async endpoints.

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