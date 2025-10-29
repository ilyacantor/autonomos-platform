# AutonomOS - Multi-Tenant AI Orchestration Platform

## Overview
AutonomOS is a production-ready, multi-tenant SaaS backend system in Python for AI-driven task orchestration. It ensures complete data isolation between organizations, providing secure, scalable, and enterprise-grade task processing. The platform includes JWT authentication and comprehensive user management, serving as a foundational component for AI applications requiring isolated task execution for multiple clients. Its ambition is to enable advanced AI-powered data orchestration for diverse business needs and offers a DCL (Data Catalog Layer) engine for AI-driven data source connection, entity mapping, and unified view creation.

The dashboard features a hero section showcasing the product value proposition, followed by the DCL graph visualization for data mapping and orchestration, and an agent layer container showing AI agents with descriptive text about persistent data mappings.

## User Preferences
I prefer clear, concise explanations and direct answers. I value iterative development with frequent, small updates. Please ask for my approval before implementing major architectural changes or significant feature additions. I prefer detailed explanations for complex concepts but require brevity for straightforward ones. Do not make changes to folder `Z` and file `Y`.

## System Architecture
AutonomOS is built with FastAPI, PostgreSQL, Redis, and Python RQ, implementing a multi-tenant task orchestration platform.

**Ontology Table Enhancements:**
- The Ontology page now displays comprehensive mapping information including data sources, source tables, and source fields
- Enhanced `/ontology_schema` endpoint provides source mapping data extracted from the DCL graph state
- Table columns include: Entity Name, Primary Key, Unified Fields, Data Sources, Source Tables, and expandable details showing raw data table/field mappings
- **Data Source Universe View:** New tab showing the complete raw materials hierarchy - all data sources, tables, and fields organized by source system with full drill-down capability
- Two view modes: "Unified Entities View" (entity-centric) and "Data Source Universe" (source-centric with full raw data catalog)

**UI/UX Decisions:**
- API documentation via Swagger UI and ReDoc.
- Authentication is disabled by default. Login and Sign Up buttons in the TopBar replace the user profile dropdown. The auth modal only appears when users explicitly click these buttons.
- **FAQ Page:** Comprehensive FAQ section accessible via navigation tab, featuring accordion-style Q&A about AutonomOS AI capabilities, including detailed explanations of AAM, DCL, Prebuilt Domain Agents, security architecture, and technology stack.
- The frontend features interactive DCL graph controls, data source and intelligence agent selection, and a real-time status panel with a two-column design.
- **All Sources Selector:** The "All Sources" dropdown option automatically selects all 9 data sources AND all 2 agents, saving them to localStorage before triggering the mapping run.
- Agent robot figures temporarily removed from display (image retained in assets/robot-agents.png for future use).
- The description "Provides persistent, versioned entity mappings..." is now a subheadline under the "Data Connection Layer (DCL)" heading.
- Hero section uses the autonomOS logo image instead of text, with exact styling matching the design spec including varied text colors (cyan for "autonomOS" and "Stop building pipelines", white for other text).
- DCL header is teal/cyan colored to match the Agentic Orchestration section.
- Agentic Orchestration at Scale section is unified in a single container with teal header and subheadline describing orchestration capabilities.
- **Typography:** All text uses Quicksand font (Google Fonts). Headings use font-medium (500 weight), body text uses font-normal (400 weight). All uppercase styling has been removed in favor of normal capitalization.
- UI includes a connection timer, horizontal progress bar, and reorganized right sidebar with narration, RAG Learning Engine, and Intelligence Review panels.
- Graph labels are color-coded pill-shaped boxes with colored borders: green for data source labels, blue for ontology entity labels, purple for agent labels. All labels use consistent sizing (10px font, 16px height, 4px padding). Each label has a 1.5px border matching its node type or edge color. Labels use collision detection to prevent overlaps within each layer. Graph is centered in its container for balanced presentation.
- **Mobile Optimization:** Comprehensive mobile-first design implementation:
  - **Global Utilities:** Safe-area padding for notched devices, 44px minimum touch targets, mobile-tap-highlight, horizontal scroll containers, responsive typography scale
  - **TopBar:** Hamburger menu for <640px screens without scrolling, z-index management (z-50 menu, z-40 overlay), hidden persona text on mobile, clickable logo navigates to dashboard
  - **HeroSection:** Full 3-breakpoint typography scaling (text-lg sm:text-xl md:text-2xl pattern), touch-target buttons, responsive logo sizing
  - **DCL Controls:** 2x2 grid layout on mobile (grid-cols-2 sm:flex), 44px touch targets, larger mobile text (text-xs sm:text-[10px])
  - **DCL Graph ViewBox & ClipPath:** Dynamic viewBox calculation with pre-measured label widths ensures no label clipping. Before SVG creation, code measures all labels (using temporary text elements matching actual fontSize and padding), tracks maximum pill width, and calculates extendedRightPadding = viewBoxPaddingTop (20px) + labelOffset (8px) + maxMeasuredLabelWidth. ViewBox uses asymmetric padding: 20px top/left, 2px bottom to minimize empty margin on mobile. ClipPath boundaries match viewBox dimensions exactly to prevent edge bleeding. Labels positioned horizontally at x1 + labelOffset with collision detection to prevent overlaps within layers. Container uses pb-2 for minimal mobile bottom spacing.
  - **Responsive Height:** Mobile graph containers have no fixed minHeight, allowing them to shrink to fit actual SVG content (minimum 200px). Desktop applies md:min-h-[400px] and md:min-h-[500px] for proper layout. This prevents large empty gaps on mobile while maintaining desktop appearance.
  - **Architecture Flow Navigation:** Clickable module boxes with smooth scroll to corresponding sections (AAM → 3-card visual, DCL → graph, Agents → performance monitor)
  - **Architecture Flow Arrows:** Layout-aware directional arrows properly bound from source to target boxes across all breakpoints:
    - Desktop (lg+, 4-column): Horizontal arrows between all adjacent boxes (Enterprise Data → AAM → DCL → Agents)
    - Tablet (md, 2-column): Horizontal arrows within rows (0→1, 2→3) and vertical arrow between rows (1→2)
    - Mobile (<md, 1-column): Vertical arrows between all adjacent stacked boxes
    - Arrows styled with bright cyan background, bold stroke, glow effect, and mobile pulse animation for maximum visibility
  - **AAM 3-Card Visual:** Horizontal scroll container on mobile (280px cards, touch-optimized scrolling) allows users to swipe through all three architecture layers
  - **Tested:** No layout breakage at 320px, 375px, 428px widths; no horizontal scrolling; all touch targets meet 44px standard; arrows correctly bound at all zoom levels
- **DCL Graph Horizontal Orientation:** Clean, minimalist visualization with boxes and edges flowing left-to-right in natural horizontal Sankey layout. Major refactoring eliminated ~150+ lines of problematic code including 90° rotation transforms, mobile-specific scaling patches, complex touch event handlers, and custom tooltip logic. Graph now uses simple mouseenter/mouseleave tooltips and dynamic label width measurement to prevent clipping.

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
- **Dropdown Z-Index:** Profile and Autonomy Mode dropdowns use z-50 for menus and z-40 for overlays to ensure proper visibility above all layout elements. TopBar container has overflow clipping removed to allow dropdowns to extend beyond boundaries.
- **DCL Edge Colors:** Edges from data sources (layer 0) to layer 1 are green (#22c55e). All other edge colors remain unchanged (layer 1→2→3 use original color scheme).
- **Edge Hover Tooltips:** All edges display tooltips on hover. Level 0→1 (hierarchy) edges show data source name, table name, and complete list of table fields.
- **Graph Labels:** Horizontal pillbox labels positioned to the right of nodes with dark slate background and colored borders matching node types. Agent labels use larger sizing (15px font, 24px height, 6px padding) for emphasis, while source/ontology labels use standard sizing (10px font, 16px height, 4px padding):
  - Layer 0 (source_parent): Full data source names with green borders (#22c55e)
  - Layer 2 (ontology): Entity names without "(Unified)" suffix (e.g., "AWS Resources" from "AWS Resources (Unified)") with blue borders (#60a5fa)
  - Layer 3 (agent): Full agent names with purple borders (#9333ea)

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