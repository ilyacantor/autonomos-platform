# AutonomOS - Multi-Tenant AI Orchestration Platform

## Overview
AutonomOS is a production-ready, multi-tenant SaaS backend system in Python for AI-driven task orchestration. It ensures complete data isolation between organizations, providing secure, scalable, and enterprise-grade task processing. The platform includes JWT authentication and comprehensive user management, serving as a foundational component for AI applications requiring isolated task execution for multiple clients. Its ambition is to enable advanced AI-powered data orchestration for diverse business needs and offers a DCL (Data Catalog Layer) engine for AI-driven data source connection, entity mapping, and unified view creation.

## User Preferences
I prefer clear, concise explanations and direct answers. I value iterative development with frequent, small updates. Please ask for my approval before implementing major architectural changes or significant feature additions. I prefer detailed explanations for complex concepts but require brevity for straightforward ones. Do not make changes to folder `Z` and file `Y`.

## System Architecture
AutonomOS is built with FastAPI, PostgreSQL, Redis, and Python RQ, implementing a multi-tenant task orchestration platform.

**UI/UX Decisions:**
- API documentation via Swagger UI and ReDoc.
- The frontend features interactive DCL graph controls, data source and intelligence agent selection, and a real-time status panel with a two-column design.
- UI includes a connection timer, horizontal progress bar, and reorganized right sidebar with narration, RAG Learning Engine, and Intelligence Review panels.
- Graph labels are color-coded, pill-shaped with SVG icons for unified ontology fields, outlined for agent nodes, and type-specific for source nodes.
- Mobile optimization includes responsive navigation, enlarged touch targets, compact top bar, and stacking for connections page.
- DCL graph visualization is clean, minimalist, with only boxes and edges, vertically centered and flowing top to bottom, with labels oriented to match data flow.
- The AAM container provides an iPaaS-style data flow visualization (Connect → Normalize → Unify) with data source logos and a real-time connection log.

**Technical Implementations:**
- **Authentication:** JWT-based with Argon2 hashing.
- **API:** FastAPI provides REST endpoints for user and task management with tenant-scoped data access and Pydantic validation.
- **Worker:** Python RQ handles asynchronous task processing, lifecycle management, error handling, and retries.
- **Data:** PostgreSQL with SQLAlchemy for persistence and tenant isolation; Redis for high-performance task queuing.
- **Multi-Tenancy:** Achieved through `tenant_id` scoping for data isolation.
- **AOA Orchestration:** An embedded DCL engine handles AI-driven data source connection and mapping. AOA endpoints orchestrate DCL operations via async worker tasks.
- **Callback System:** Supports optional `callback_url` for event-driven workflows.
- **Task Lifecycle:** Tasks transition through `queued`, `in_progress`, `success`, and `failed` states.
- **Concurrency Control:** Redis-based distributed locking for safe concurrent DuckDB access.
- **Idempotent DCL Connections:** The `/dcl/connect` endpoint is idempotent, clearing and rebuilding DCL state.
- **LLM Service Abstraction:** A factory pattern (`llm_service.py`) supports multiple LLM providers (Gemini, OpenAI) with a user-selectable model on the frontend.
- **DCL Graph Architecture:** Backend owns the complete data structure hierarchy, emitting `source_parent` nodes with explicit metadata and typed edges (`hierarchy` or `dataflow`).
- **Sankey Layer Enforcement:** Node depths are manually assigned for stable layer positioning.
- **DCL Graph Optimization:** Achieves fast initial render (≤1s) and perfect scaling using `useLayoutEffect`, `requestAnimationFrame` throttling, dynamic viewBox calculation, and an optimized `ResizeObserver`.
- **DCL Graph Visibility:** Dynamic height calculation `Math.min(800, 100 + (totalNodeCount * 40))` ensures all nodes are visible without clipping, adapting to node count and screen size.
- **Data Lineage Search:** Consolidated into the Connections tab for improved UX, with search box removal from the Data Lineage page and navigation streamlining.
- **Graph Node Sizing:** Nodes are 8px wide with proper padding (20px) and a clipPath to prevent bleeding outside container bounds.

**System Design Choices:**
- Core components: `main.py` (FastAPI), `worker.py` (RQ), `models.py` (SQLAlchemy), `schemas.py` (Pydantic), `crud.py`, `security.py`, `database.py`, `config.py`.
- DCL engine at `app/dcl_engine/` and mounted at `/dcl`.
- System orchestration via `start.sh`.
- Frontend is a React/TypeScript application built with Vite, deployed to `static/`.
- Automatic production mode detection (via `REDIS_URL`) defaults to heuristic-only mapping.
- Enhanced CORS configuration automatically allows all Replit domains.
- `uvicorn[standard]` for WebSocket support.

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

## Recent Changes

### October 25, 2025 - Animated Data-Flow Effect for Layer 0 → Layer 1 Edges
**Objective:** Implement visual-only enhancement with bright cyan color and animated flow effect for edges from source_parent (layer 0) to source (layer 1).

**Implementation:**
- **Edge Detection and Styling:**
  - Detect edges where `source.depth === 0 && target.depth === 1`
  - Color them bright cyan `#00F5FF` with opacity `0.9` (higher than standard edges)
  - All other edges retain their existing colors
- **Animated "Data-Flow" Effect:**
  - SVG stroke-dasharray/stroke-dashoffset animation (5s linear infinite)
  - CSS keyframe animation with dashed pattern moving along edge path
  - Animation controlled by `animate` state with smart timing logic
- **Animation State Management:**
  - `isRunning` derived from `animatingEdges.size > 0`
  - `animate` state follows isRunning with 2-second persistence after isRunning becomes false
  - useEffect hook manages the 2-second timeout cleanup
- **CSS Injection:**
  - One-time style injection into document head (flow-style ID check)
  - Keyframe animation: `flowDash` moves stroke-dashoffset from 0 to -1000
  - `.flow-animated` class with `stroke-dasharray: 6 6` and `will-change: stroke-dashoffset`
- **Edge Class Application:**
  - `flow-animated` class applied conditionally when `animate === true` and edge is layer 0 → 1
  - Compatible with existing `animate-pulse` class for event-driven animations
  - Proper opacity restoration on mouseleave (0.9 for layer 0 → 1 edges)

**Result:**
- Data-source → Layer 1 edges glow bright cyan, clearly visible
- Smooth 5-second animation showing data flow direction
- Animation runs only while isRunning is true and for 2s after
- No UI layout or performance regressions
- Zoom/pan and edge interactivity unchanged
- Zero changes to node data or other edge colors