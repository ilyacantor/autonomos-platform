# AutonomOS - Multi-Tenant AI Orchestration Platform

## Overview
AutonomOS is a production-ready, multi-tenant SaaS backend system in Python for AI-driven task orchestration. Its core purpose is to enable advanced AI-powered data orchestration, including a Data Connection Layer (DCL) engine for AI-driven data source connection, entity mapping, and unified view creation. The platform ensures complete data isolation, providing secure, scalable, and enterprise-grade task processing with JWT authentication and user management. It features a production-ready Adaptive API Mesh with operational connectors, complete drift detection with schema fingerprinting, autonomous auto-repair with confidence scoring, and canonical event normalization.

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
*   **Event Streaming System:** Real-time event delivery via Server-Sent Events (SSE) and WebSockets, with Redis Pub/Sub for inter-service broadcasting.
*   **Frontend:** Built with React 18 and TypeScript, featuring a responsive UI/UX design with Quicksand typography, a distinct color scheme (Green, Blue, Purple), and dark mode support. Includes pages for Dashboard, AAM Monitor, Live Flow, Ontology, Connections, Data Lineage, and an interactive architecture viewer.
*   **API Endpoints:** Organized by domain (Auth, AOA, DCL Views, Events, AAM, Debug) with OpenAPI/Swagger documentation.
*   **System Design:** The platform employs a "Strangler Fig" pattern with feature flags for zero downtime, restructuring towards a unified data flow: Data Sources → AAM → DCL → Agents. This includes a unified PostgreSQL database for DCL and AAM, Redis-based LLM counter persistence, and intelligent RAG coverage checks.
*   **Data Quality Intelligence Layer:** Implements canonical event processing (Pydantic validation, metadata enrichment), schema drift detection (fingerprinting with Redis persistence), an LLM/RAG-powered auto-repair agent with confidence scoring, and a Human-in-the-Loop (HITL) workflow (Redis + PostgreSQL for audit). Metadata flows end-to-end, providing data quality insights to agents and visualizations in the frontend.

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