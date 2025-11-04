# AutonomOS - Multi-Tenant AI Orchestration Platform

## Overview
AutonomOS is a production-ready, multi-tenant SaaS backend system in Python for AI-driven task orchestration. Its core purpose is to enable advanced AI-powered data orchestration, including a Data Connection Layer (DCL) engine for AI-driven data source connection, entity mapping, and unified view creation. The platform ensures complete data isolation, providing secure, scalable, and enterprise-grade task processing with JWT authentication and user management. It features a production-ready Adaptive API Mesh with operational connectors, complete drift detection with schema fingerprinting, autonomous auto-repair with confidence scoring, and canonical event normalization.

## User Preferences
I prefer clear, concise explanations and direct answers. I value iterative development with frequent, small updates. Please ask for my approval before implementing major architectural changes or significant feature additions. I prefer detailed explanations for complex concepts but require brevity for straightforward ones. Do not make changes to folder `Z` and file `Y`.

## System Architecture
AutonomOS is a full-stack SaaS platform built around a multi-tenant architecture ensuring complete data isolation via UUID-based `tenant_id` scoping and JWT authentication.

**Key Architectural Components & Features:**

*   **Task Orchestration System:** Utilizes Python RQ and Redis Queue for asynchronous background job processing with full lifecycle management, automatic retries, error handling, and per-tenant job concurrency.
*   **Authentication & Security:** Implements JWT-based authentication with Argon2 password hashing and 7-day token expiration. All API endpoints require JWT authentication.
*   **AOA (Agentic Orchestration Architecture):** High-level orchestration layer managing DCL engine operations, enforcing a single active job per tenant for DCL state management.
*   **DCL Engine (Data Connection Layer):** An AI-driven, in-process engine for data orchestration, leveraging DuckDB for materialized views and concurrent access control via Redis. It supports multiple connectors, AI-powered entity mapping, graph generation, and idempotent operations. Materialized views are exposed via PostgreSQL tables with dedicated API endpoints, automatic syncing, and tenant-specific querying. LLM Telemetry tracks cumulative LLM calls and token usage via Redis persistence.
*   **Adaptive API Mesh (AAM):** Provides self-healing data connectivity with four production connectors (Salesforce, FileSource, Supabase, MongoDB). Features include canonical event normalization using Pydantic, schema fingerprinting for drift detection, an auto-repair agent with LLM-powered field mapping, and RAG intelligence for semantic matching.
*   **Event Streaming System:** Real-time event delivery via Server-Sent Events (SSE) and WebSockets, supporting various event types with Redis Pub/Sub for inter-service broadcasting.
*   **Frontend:** Built with React 18 and TypeScript, featuring pages like Dashboard, AAM Monitor, Live Flow, Ontology, Connections, Data Lineage, and an interactive architecture viewer. UI/UX design includes Quicksand typography, a distinct color scheme (Green, Blue, Purple), mobile-first responsiveness, and dark mode support.
*   **API Endpoints:** Organized by domain (Auth, AOA, DCL Views, Events, AAM, Debug) with OpenAPI/Swagger documentation.
*   **System Design:** The platform is undergoing a comprehensive restructuring to implement a proper data flow architecture (Data Sources → AAM → DCL → Agents) using a "Strangler Fig" pattern with feature flags for zero downtime and backward compatibility. This includes a unified PostgreSQL database for DCL and AAM, Redis-based LLM counter persistence, and intelligent RAG coverage checks to optimize LLM calls.

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