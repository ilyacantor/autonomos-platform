# AutonomOS - Multi-Tenant AI Orchestration Platform

## Overview
AutonomOS is a production-ready, multi-tenant SaaS backend system in Python for AI-driven task orchestration. It ensures complete data isolation between organizations, providing secure, scalable, and enterprise-grade task processing. The platform includes JWT authentication and comprehensive user management, serving as a foundational component for AI applications requiring isolated task execution for multiple clients. Its ambition is to enable advanced AI-powered data orchestration for diverse business needs and offers a DCL (Data Catalog Layer) engine for AI-driven data source connection, entity mapping, and unified view creation.

## User Preferences
I prefer clear, concise explanations and direct answers. I value iterative development with frequent, small updates. Please ask for my approval before implementing major architectural changes or significant feature additions. I prefer detailed explanations for complex concepts but require brevity for straightforward ones. Do not make changes to folder `Z` and file `Y`.

## System Architecture
AutonomOS is built with FastAPI, PostgreSQL, Redis, and Python RQ, implementing a multi-tenant task orchestration platform.

**UI/UX Decisions:**
- API documentation is provided via Swagger UI and ReDoc.
- The frontend features interactive DCL graph controls, data source and intelligence agent selection, and a real-time status panel with a two-column design.
- The UI includes a connection timer, a horizontal progress bar, and a reorganized right sidebar with narration, RAG Learning Engine, and Intelligence Review panels.
- Graph labels are themed with color-coded, pill-shaped labels and SVG icons for unified ontology fields, outlined styles for agent nodes, and type-specific outlined styles for source nodes.
- Mobile optimization includes responsive navigation with a hamburger menu, enlarged touch targets, a compact mobile top bar, and stacking for connections page.
- The DCL graph visualization is designed to be clean and minimalist, showing only clean boxes and edges, with vertical centering.
- The graph flows vertically (top to bottom) with labels oriented to match data flow.

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
- **DCL Graph Architecture:** The backend owns the complete data structure hierarchy, emitting `source_parent` nodes with explicit metadata and typed edges (`hierarchy` or `dataflow`). The frontend consumes this structure directly.
- **Sankey Layer Enforcement:** Node depths are manually assigned based on architectural type after initial D3-Sankey layout to ensure stable layer positioning.

**System Design Choices:**
- Core components: `main.py` (FastAPI), `worker.py` (RQ), `models.py` (SQLAlchemy), `schemas.py` (Pydantic), `crud.py`, `security.py`, `database.py`, `config.py`.
- DCL engine is located at `app/dcl_engine/` and mounted at `/dcl`. Worker processes call DCL functions directly via Python imports.
- System orchestration via `start.sh`.
- Frontend is a React/TypeScript application built with Vite, deployed to `static/`.
- Automatic production mode detection (via `REDIS_URL`) defaults to heuristic-only mapping for speed.
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

### October 25, 2025 - DCL Graph Maximum Visibility Enhancements
**Objective:** Ensure DCL graph displays all nodes at once regardless of screen size or device, with responsive resizing and no node clipping.

**Implementation:**
- **Dynamic Height Calculation:** Removed fixed heights (400/500/600px) and implemented node-count-based sizing
  - Formula: `Math.min(800, 100 + (totalNodeCount * 40))`
  - Uses total nodes (sources + unified + agents) for accurate sizing
  - Container and SVG elements dynamically adjust to calculated height
- **Fit-to-View Scaling:** Automatic D3 bounding box calculation for perfect content fit
  - Computes min/max X/Y from all nodes after Sankey layout
  - ViewBox dynamically set with 100px padding: `viewBox="${minX - 100} ${minY - 100} ${width + 200} ${height + 200}"`
  - Graph scales to show all content within viewport
- **Removed Clipping Restrictions:** Eliminated overflow-hidden and clipPath
  - Removed `overflow: 'hidden'` from container wrapper
  - Deleted entire clipPath definition and all references
  - Graph can now expand freely to show all nodes without cropping
- **ResizeObserver Integration:** Automatic re-rendering on window/container resize
  - Watches containerRef for size changes
  - Debounced at 150ms to prevent excessive re-renders
  - Updates containerSize state to trigger graph refresh
  - Proper cleanup on component unmount

**Result:**
- All nodes guaranteed visible without manual scrolling
- Dynamic sizing adapts to actual node count (2-50+ nodes)
- Responsive to window resize and orientation changes
- No overflow clipping or hidden content
- Maintains dark theme, animations, tooltips, and WebSocket updates
- Zero backend logic modifications (layout/styling only)
- Architect-approved implementation

### October 25, 2025 - Data Lineage Search Moved to Connections Tab
**Objective:** Improve UX by consolidating data source management and lineage search in one location.

**Implementation:**
- **ConnectionsPage Enhancement:** Added "Trace Data Lineage" search box under data sources container
  - Search input with orange-themed styling to match lineage page branding
  - "Trace Lineage" button navigates to Data Lineage page with query
  - Uses sessionStorage to pass search query between pages
  - Disabled state when search box is empty
- **DataLineagePage Simplification:** Removed search input box from lineage page
  - Auto-triggers search on mount if query exists in sessionStorage
  - Shows helpful guidance directing users to Connections page when no search active
  - Displays active search query in page description
  - Maintains all existing visualization functionality
- **Navigation Update:** Removed "Data Lineage" nav item from TopBar
  - Users access lineage functionality via Connections page search
  - Data lineage page still accessible programmatically if needed
  - Cleaner, more streamlined navigation

**Result:**
- Streamlined UX with single entry point for data operations
- Data lineage search positioned logically near data source selection
- Cross-page integration via sessionStorage handoff
- Simplified navigation with one less top-level menu item
- No regressions in existing functionality

### October 24, 2025 - Clean Bounded Graph with 8px Nodes
**Objective:** Restore clean, well-bounded graph visualization with proper node sizing.

**Implementation:**
- **8px Node Width:** Set nodeWidth to 8px in sankey configuration
- **Updated Node Positions:** Node x1 positions calculated as x0 + 8 for consistent width
- **Proper Padding:** Added leftPadding (20px) and rightPadding (20px) to coordinate system
  - LayerXPositions start at leftPadding instead of edge (x=1)
  - LayerWidth calculation accounts for padding: (validWidth - leftPadding - rightPadding) / 3
  - Rightmost layer positioned at validWidth - rightPadding - nodeWidth
- **SVG ClipPath:** Applied clipPath to prevent graph bleeding outside container bounds
- **Clean Coordinate System:** Nodes positioned with proper margins BEFORE rotation
  - Ensures clipPath works correctly (applied in pre-rotation frame)
  - No transform band-aids needed

**Result:**
- Clean graph with 8px wide nodes
- Well-bounded on all sides with 20px padding
- Vertical flow (top→bottom) with strict 4-layer enforcement
- No visual clutter from headers, footers, or labels
- Consistent uniform styling across all node types
- Clean architecture without transform workarounds