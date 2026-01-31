# AutonomOS - Enterprise AI Orchestration Platform

## What AutonomOS Does

AutonomOS (AOS) is an AI-native operating system for enterprise data and agent workflows. It solves the fundamental problem of **data chaos** - where business-critical information is scattered across dozens of disconnected systems, making it impossible for AI agents (or humans) to get accurate, timely answers.

### The Problem We Solve

Enterprises struggle with:
- **Shadow IT**: Unknown applications running across the organization
- **Data Silos**: Customer data in Salesforce, billing in Stripe, usage in DataDog - never unified
- **Schema Drift**: APIs and data structures constantly changing, breaking integrations
- **No Single Source of Truth**: Finance, Sales, and Ops all have different "customer" definitions

### How AutonomOS Solves It

The platform operates as a three-stage pipeline:

1. **Discover** (AOD) - Find and catalog everything running in your environment
2. **Connect** (AAM) - Establish self-healing connections to your data sources
3. **Unify** (DCL) - Transform fragmented data into a canonical business ontology

This creates a foundation where AI agents can finally get reliable, consistent answers.

---

## Platform Modules

### NLQ - Natural Language Query
**What it does**: Ask questions in plain English across all your unified data and get instant, interactive dashboards.

- Query across Salesforce, Stripe, NetSuite, and more with natural language
- AI understands business context (e.g., "Show me at-risk customers" combines usage, billing, and support data)
- Persona-aware responses (CFO sees financial impact, CRO sees pipeline risk)

**Self-Generating Dashboard Features:**
- **Galaxy View**: Interactive visualization with center node (main answer) and connected nodes (related metrics)
- **Dashboard View**: For overview questions like "2025 results" or "CFO dashboard" - generates full KPI dashboards
- **Customizable Widgets**: Drag to reposition, resize by dragging corners, refine with natural language
- **Refinement Box**: Modify dashboards with commands like "Add a pipeline chart" or "Make the revenue card bigger"
- **Save/Load**: Save customized layouts and create reusable templates
- **Confidence Indicators**: Green (high), Yellow (medium), Red (lower) confidence scoring on all answers
- **Trend Arrows**: Visual indicators showing if metrics are improving, declining, or stable

### AOD - Asset & Observability Discovery
**What it does**: Automatically discover, catalog, and score everything running in your environment.

- Scans infrastructure and SaaS telemetry to build a complete Asset Graph
- Identifies shadow IT, risky applications, and compliance gaps
- Scores assets by risk, cost, and business criticality
- Flags anomalies and assets without proper ownership

### AAM - Adaptive API Mesh
**What it does**: Connect to any data source with self-healing, intelligent integrations.

- Production connectors for Salesforce, Stripe, NetSuite, Supabase, MongoDB, and more
- Automatic schema drift detection - knows when APIs change
- LLM-powered auto-repair - fixes broken mappings without manual intervention
- Canonical event normalization - every source speaks the same language

### DCL - Data Connectivity Layer
**What it does**: Transform raw data into a unified business ontology.

- Maps source fields (e.g., `sf_account_name`) to canonical entities (e.g., `Account.name`)
- Performs entity resolution - recognizes "Acme Corp" and "ACME Corporation" as the same company
- Produces canonical streams that agents and dashboards consume
- AI-assisted field mapping with confidence scoring

### AOA - Agentic Orchestration Architecture
**What it does**: Orchestrate complex, multi-step AI workflows across your business.

- Fabric-aware scheduling routes tasks through proper enterprise integration planes
- RACI compliance ensures every action has clear accountability
- Stress testing and simulation modes for validating workflows before production
- Real-time monitoring of agent execution and performance

---

## Business Personas

AutonomOS tailors information for different executive roles:

| Persona | What They See | Key Questions Answered |
|---------|---------------|------------------------|
| **CFO** | Revenue, Cost, Margin, Cash, Risk | "What's our actual MRR?" "Where are we over-spending?" |
| **CRO** | Accounts, Pipeline, Opportunities, Churn | "Which deals are at risk?" "What's our true pipeline?" |
| **COO** | Usage, Health, SLAs, Incidents | "Are we meeting SLAs?" "What's affecting customer health?" |
| **CTO** | Assets, Cloud Resources, Tech Debt, Security | "What shadow IT exists?" "Where's our infrastructure risk?" |

---

## Key Capabilities

### Self-Healing Integrations
When a vendor changes their API schema, most integrations break. AutonomOS:
- Detects schema drift automatically via fingerprinting
- Uses AI to propose mapping repairs
- Applies fixes with human-in-the-loop approval for critical changes
- Maintains audit trails of all changes

### Canonical Data Model
Instead of every system having its own definition of "Customer", AutonomOS maintains a single ontology:
- **Account**: Unified company/organization entity
- **Opportunity**: Sales deals across all sources
- **Revenue**: Billing and payment data normalized
- **Cost**: Spending across vendors and resources
- **Usage**: Product and service utilization metrics
- **Health**: Composite customer health scoring

### Fabric Plane Architecture
Enterprise integrations flow through aggregated planes, not point-to-point connections:
- **iPaaS Plane**: Workato, Tray.io, Celigo for complex workflows
- **API Gateway Plane**: Kong, Apigee for API management
- **Event Bus Plane**: Kafka, EventBridge for real-time events
- **Data Warehouse Plane**: Snowflake, BigQuery for analytics

This ensures governance, auditability, and scalability.

### Real-Time Telemetry
Track data as it flows through the system:
- Live flow monitoring across AAM → DCL → Agent pipeline
- Entity lifecycle tracking from source to action
- Performance metrics and bottleneck identification

---

## User Preferences

**Development Philosophy:**
- ALWAYS choose fundamental/root-cause fixes over workarounds
- No band-aids, quick patches, or shortcuts
- Fix underlying architecture properly

**Communication:**
- Clear, concise explanations
- Iterative development with frequent updates
- Ask before major architectural changes

**Planning:**
- No time-based estimates (Week 1, Week 2)
- Organize by priorities (P0/Critical, High, Medium, Low)
- Focus on dependencies and logical phases

---

## Navigation Structure

The frontend provides access to all modules:

```
Overview → NLQ → AOD → AAM → DCL → AOA → Help
```

Each module embeds its specialized interface:
- **NLQ**: nlq.autonomos.software
- **AOD**: discover.autonomos.software  
- **AAM**: aam.autonomos.software
- **DCL**: dcl.autonomos.software

---

## Technical Architecture

### Stack
- **Frontend**: React 18, TypeScript, Tailwind CSS
- **Backend**: FastAPI (Python), SQLAlchemy ORM
- **Database**: PostgreSQL (Supabase) with pgvector for embeddings
- **Cache/Queue**: Redis (Upstash) with RQ for job processing
- **AI**: OpenAI, Google Gemini for intelligence services

### Security
- JWT-based authentication with Argon2 hashing
- Multi-tenant isolation via UUID-based tenant_id scoping
- PII detection at ingress with configurable policies (BLOCK/REDACT/WARN/ALLOW)
- TLS encryption for all Redis connections

### Resilience
- Circuit breakers for external service calls
- Retry logic with exponential backoff
- Graceful degradation when services unavailable
- Feature flags for safe rollouts

---

## External Services

| Service | Purpose |
|---------|---------|
| Supabase PostgreSQL | Primary database |
| Upstash Redis | Caching, queues, pub/sub |
| Airbyte | Data integration monitoring |
| Slack Webhooks | Notifications |

---

## Documentation

| File | Purpose |
|------|---------|
| `README.md` | Platform overview and quick start |
| `replit.md` | This file - capabilities and architecture |
| `SECURITY.md` | Security controls and compliance |
| `DOCUMENTATION_INDEX.md` | Complete file directory |
