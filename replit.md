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

### October 25, 2025 - Profile Dropdown with Logout Functionality
**Objective:** Verify profile dropdown menu is properly established with persona selection and logout functionality.

**Implementation:**
- **Profile Button (TopBar.tsx):**
  - Displays user avatar, name (Alex Johnson), and current persona
  - ChevronDown icon indicates dropdown capability
  - Hover states for better UX
- **Dropdown Menu:**
  - **Persona Selector:** Switch between Data Engineer, RevOps, and FinOps personas
  - **Active State:** Currently selected persona highlighted in blue
  - **Logout Button:** Red logout option with LogOut icon at bottom
- **Logout Functionality (AuthContext):**
  - Clears AUTH_TOKEN_KEY from localStorage
  - Removes TOKEN_EXPIRY_KEY timestamp
  - Resets user and token state to null
  - Triggers redirect to login screen
- **UX Features:**
  - Backdrop overlay closes dropdown when clicking outside
  - Smooth transitions and hover effects
  - Proper z-index layering (backdrop z-10, menu z-20)

**Result:**
- Fully functional profile dropdown with persona switching
- Secure logout that clears all authentication data
- Professional UI/UX with smooth interactions

### October 25, 2025 - DCL Graph Performance Optimization
**Objective:** Optimize LiveSankeyGraph for fast initial render (≤1s) and perfect scaling at any zoom/device size.

**Key Improvements:**
- Fast initial render with loading skeleton and useLayoutEffect
- requestAnimationFrame throttling for smooth performance
- Perfect responsive scaling with overflow-hidden container
- Dynamic viewBox calculation based on node bounding box
- No clipping or overflow at 75%-125% browser zoom

### October 25, 2025 - Enhanced Edge Visibility
**Objective:** Improve visual clarity of data flow from source nodes to layer 1 nodes.

**Changes:**
- Increased stroke-opacity from 0.4 to 0.7 for edges from data sources
- Applied to both source and source_parent node types
- 75% more visible connections emphasizing initial data ingestion layer

### October 25, 2025 - AAM Container Implementation
**Objective:** Create AAM (Adaptive API Mesh) container showing iPaaS-style data flow visualization.

**Features:**
- iPaaS flow diagram: Data Sources → AAM Normalize → DCL Mapping → Agents
- 8 connected platform logos at 128px height
- Real-time Connection Log with 20 technical API status messages
- Website link to autonomos.tech in top-right corner
- Two-column responsive grid layout with scrollable log panel