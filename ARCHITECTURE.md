# AutonomOS Platform Architecture

## Table of Contents
1. [Functional Overview](#functional-overview)
2. [Systems Overview (AOA)](#systems-overview-aoa)
3. [High-Level System Architecture](#high-level-system-architecture)
4. [Data Flow: Source → AAM → DCL](#data-flow-source--aam--dcl)
5. [AAM Components](#aam-components)
6. [Gateway Middleware Stack](#gateway-middleware-stack)
7. [Database Schema](#database-schema)
8. [Frontend Architecture](#frontend-architecture)
9. [Canonical Schema Types](#canonical-schema-types)
10. [Technology Stack](#technology-stack)

---

## Functional Overview

**What AutonomOS Does:** Connects messy data sources, cleans them up intelligently, and gives AI agents a unified view.

```mermaid
flowchart TB
    DS["📊 DATA SOURCES<br/><br/><b>Function:</b> Provide raw business data<br/><br/><b>What they do:</b><br/>• Salesforce stores CRM data<br/>• Supabase tracks product usage<br/>• MongoDB logs customer events<br/>• CSV files hold legacy data<br/><br/><b>Problem:</b> Different formats,<br/>field names, structures"]
    
    AAM["🔧 ADAPTIVE API MESH<br/><br/><b>Function:</b> Normalize chaos into order<br/><br/><b>What it does:</b><br/>• Connects to each source<br/>• Transforms to standard format<br/>• Detects schema changes<br/>• Auto-repairs broken mappings<br/>• Uses AI to match similar fields<br/><br/><b>Output:</b> Clean, validated,<br/>canonical events"]
    
    DCL["📚 DATA CATALOG LAYER<br/><br/><b>Function:</b> Create unified queryable views<br/><br/><b>What it does:</b><br/>• Stores canonical events<br/>• Builds materialized tables<br/>• Links related records<br/>• Infers relationships<br/>• Provides SQL-like queries<br/><br/><b>Output:</b> Single source of truth<br/>for all business entities"]
    
    AGENTS["🤖 AI AGENTS<br/><br/><b>Function:</b> Take intelligent action<br/><br/><b>What they do:</b><br/>• RevOps: Score deals, predict revenue<br/>• FinOps: Find cost anomalies<br/>• Query unified data (no ETL)<br/>• Execute actions automatically<br/>• Write back to sources<br/><br/><b>Result:</b> Automated insights<br/>and actions"]
    
    DS -->|"Raw events<br/>(messy, inconsistent)"| AAM
    AAM -->|"Canonical events<br/>(clean, validated)"| DCL
    DCL -->|"Unified data<br/>(queryable, linked)"| AGENTS
    AGENTS -->|"Actions<br/>(update, alert, optimize)"| AAM
```

**Key Functional Benefits:**

1. **Data Sources** → No integration work needed. Connect once, data flows automatically.
2. **AAM** → Self-healing. When Salesforce adds a field, AAM detects and adapts automatically.
3. **DCL** → Query all sources as one. No more writing separate queries for each system.
4. **Agents** → Built on unified data. Write logic once, works across all sources.

**Example Flow:**
- Salesforce emits "Opportunity closed" → AAM normalizes to CanonicalOpportunity → DCL materializes in unified view → RevOps agent calculates pipeline health → Agent updates forecast in Salesforce

---

## Systems Overview (AOA)

**Agentic Orchestration Architecture** - The complete data flow from sources to AI agents.

```mermaid
flowchart TB
  subgraph Sources["Data Sources Layer"]
    SF["Salesforce<br/>CRM Data"]
    SB["Supabase<br/>Product Analytics"]
    MG["MongoDB<br/>Customer Events"]
    FS["FileSource<br/>CSV/Legacy"]
  end

  subgraph AAM["Adaptive API Mesh - Intelligence Layer"]
    CONN["Connectors<br/>Extract & Normalize"]
    INTEL["AAM Intelligence<br/>Drift Detection, Auto-Repair, RAG"]
  end

  subgraph DCL["Data Catalog Layer - Unified Ontology"]
    CANON["Canonical Event Store<br/>PostgreSQL"]
    MAT["Materialized Views<br/>DuckDB"]
  end

  subgraph Gateway["API Gateway"]
    READ["Read API<br/>JWT Auth"]
    WRITE["Write API<br/>Audit Logs"]
  end

  subgraph Agents["Domain Agents"]
    REVOPS["RevOps Pilot"]
    FINOPS["FinOps Pilot"]
  end

  SF & SB & MG & FS --> CONN
  CONN --> INTEL
  INTEL --> CANON
  CANON --> MAT
  MAT --> READ
  READ --> REVOPS & FINOPS
  REVOPS & FINOPS --> WRITE
  WRITE --> INTEL
```

**Key Data Flow:**
1. **Sources** emit raw events (account.created, opportunity.updated)
2. **AAM** normalizes to canonical schema with drift detection
3. **DCL** materializes queryable views
4. **Gateway** provides secure API access
5. **Agents** query unified data and take actions

---

## High-Level System Architecture

```mermaid
graph TB
    subgraph "Data Sources"
        SF[Salesforce]
        SB[Supabase]
        MG[MongoDB]
        FS[FileSource/CSV]
    end

    subgraph "AutonomOS Platform"
        subgraph "Frontend"
            UI[React UI]
            DCL_VIZ[DCL Graph]
            AAM_MON[AAM Monitor]
            LIVE[Live Flow]
        end

        subgraph "API Gateway"
            MW[Middleware Stack<br/>Auth, Rate Limit, Audit]
        end

        subgraph "Backend"
            API[FastAPI Server]
            DCL[DCL Engine]
            AAM[AAM Orchestrator]
            WORKER[RQ Worker]
        end

        subgraph "Data Layer"
            PG[(PostgreSQL)]
            REDIS[(Redis)]
            DUCK[(DuckDB)]
        end

        subgraph "AI"
            GEMINI[Gemini]
            RAG[RAG Engine]
        end
    end

    SF & SB & MG & FS --> AAM
    UI & DCL_VIZ & AAM_MON & LIVE --> MW
    MW --> API
    API --> DCL & AAM & WORKER
    AAM --> PG & GEMINI & RAG
    DCL --> DUCK
    WORKER --> REDIS
```

---

## Data Flow: Source → AAM → DCL

```mermaid
graph LR
    subgraph "Sources"
        SF_OPP[Salesforce<br/>Opportunity]
        SB_ACC[Supabase<br/>Account]
        MG_USG[MongoDB<br/>Usage]
        FS_CSV[FileSource<br/>CSV]
    end

    subgraph "AAM"
        CONN[Connectors]
        MAP[Mapping Registry]
        CANON[Canonical Schema]
        STREAM[Streams DB]
    end

    subgraph "DCL"
        SUB[Subscriber]
        MAT[Materialized Tables]
        API[Views API]
    end

    subgraph "Frontend"
        UI[React UI]
    end

    SF_OPP & SB_ACC & MG_USG & FS_CSV --> CONN
    CONN --> MAP
    MAP --> CANON
    CANON --> STREAM
    STREAM --> SUB
    SUB --> MAT
    MAT --> API
    API --> UI
```

---

## AAM Components

**Adaptive API Mesh** - Three-plane architecture for intelligent data connectivity.

```mermaid
graph TB
    subgraph "Intelligence Plane"
        ORCH[Orchestrator]
        DRIFT[Drift Repair Agent]
        SCHEMA[Schema Observer]
        RAG[RAG Engine]
    end

    subgraph "Execution Plane"
        SF_CONN[Salesforce Connector]
        SB_CONN[Supabase Connector]
        MG_CONN[MongoDB Connector]
        FS_CONN[FileSource Connector]
    end

    subgraph "Control Plane"
        MAP_REG[Mapping Registry<br/>YAML]
        CANON_SCH[Canonical Schemas<br/>Pydantic]
        CONN_REG[Connector Registry<br/>PostgreSQL]
    end

    SF_CONN & SB_CONN & MG_CONN & FS_CONN --> MAP_REG
    MAP_REG --> CANON_SCH
    ORCH --> DRIFT & SCHEMA & RAG
    DRIFT & SCHEMA --> CONN_REG
```

**Current Connectors:**
- ✅ Salesforce (Production)
- ✅ Supabase (Production)
- ✅ MongoDB (Production)
- ✅ FileSource (Production)

---

## Gateway Middleware Stack

```mermaid
graph TD
    REQ[HTTP Request]
    
    REQ --> MW1[1. Tracing<br/>trace_id]
    MW1 --> MW2[2. Auth<br/>JWT, tenant]
    MW2 --> MW3[3. Rate Limit<br/>Per-tenant]
    MW3 --> MW4[4. Idempotency]
    MW4 --> MW5[5. Audit Log]
    
    MW5 --> ROUTE{Route}
    
    ROUTE -->|/api/v1/auth| AUTH[Auth]
    ROUTE -->|/api/v1/aoa| AOA[AOA]
    ROUTE -->|/api/v1/aam| AAM[AAM]
    ROUTE -->|/api/v1/dcl| DCL[DCL]
    ROUTE -->|/dcl| DCL_WS[DCL WebSocket]
    ROUTE -->|/live-flow| LIVE[Live Flow]
    ROUTE -->|/| STATIC[Frontend]
```

---

## Database Schema

```mermaid
erDiagram
    USERS ||--o{ CANONICAL_STREAMS : creates
    USERS {
        int id PK
        string username
        string email
        string hashed_password
        string tenant_id
    }

    CANONICAL_STREAMS ||--o{ MATERIALIZED_ACCOUNTS : sources
    CANONICAL_STREAMS ||--o{ MATERIALIZED_OPPORTUNITIES : sources
    CANONICAL_STREAMS {
        int id PK
        string tenant_id
        string entity
        jsonb data
        jsonb meta
        jsonb source
        datetime emitted_at
    }

    MATERIALIZED_ACCOUNTS {
        int id PK
        string tenant_id
        string account_id UK
        string name
        string industry
        decimal annual_revenue
        jsonb extras
        datetime created_at
    }

    MATERIALIZED_OPPORTUNITIES {
        int id PK
        string tenant_id
        string opportunity_id UK
        string account_id FK
        string name
        string stage
        decimal amount
        date close_date
        jsonb extras
        datetime created_at
    }
```

---

## Frontend Architecture

```mermaid
graph TB
    subgraph "Pages"
        HOME[Home<br/>Hero + FAQ]
        DCL_PAGE[DCL Graph<br/>Sankey Viz]
        AAM_PAGE[AAM Monitor<br/>Intelligence Metrics]
        ONT_PAGE[Ontology<br/>Mappings]
        LIVE_PAGE[Live Flow<br/>Real-time Events]
    end

    subgraph "Components"
        SANKEY[Sankey Graph<br/>D3.js]
        METRICS[Metrics Cards]
        EVENT_PILLS[Event Pills<br/>Animated]
    end

    subgraph "Real-time"
        WS[DCL WebSocket]
        MOCK[Mock Generator]
    end

    HOME --> DCL_PAGE & AAM_PAGE & ONT_PAGE & LIVE_PAGE
    DCL_PAGE --> SANKEY
    AAM_PAGE --> METRICS
    LIVE_PAGE --> EVENT_PILLS
    DCL_PAGE --> WS
    LIVE_PAGE --> MOCK
```

**Frontend Pages:**
- **Home** - Hero section + FAQ
- **DCL Graph** - Interactive Sankey visualization
- **AAM Monitor** - Intelligence metrics, connection health
- **Ontology** - Data mappings and universe view
- **Live Flow** - Real-time event visualization with animated pills

---

## Canonical Schema Types

```mermaid
graph TD
    EVENT[CanonicalEvent]
    
    EVENT --> META[CanonicalMeta<br/>version, tenant, trace_id]
    EVENT --> SRC[CanonicalSource<br/>system, connection_id]
    EVENT --> DATA[Data Union Type]
    
    DATA --> ACC[CanonicalAccount]
    DATA --> OPP[CanonicalOpportunity]
    DATA --> CON[CanonicalContact]
```

**Canonical Entities:**
- `CanonicalAccount` - Account records
- `CanonicalOpportunity` - Sales opportunities
- `CanonicalContact` - Contact information

All wrapped in `CanonicalEvent` envelope with metadata and source tracking.

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React, TypeScript, Vite, D3.js, Framer Motion |
| **Backend** | FastAPI, Python 3.11, Uvicorn |
| **Database** | PostgreSQL (Replit), DuckDB (DCL) |
| **Cache/Queue** | Redis, Python RQ |
| **AI/LLM** | Gemini 2.5 Flash, RAG (multilingual-e5) |
| **Auth** | JWT (HS256), Argon2 |
| **Deployment** | Replit, Nix |

---

## Current Statistics

- **Connectors:** 4 (Salesforce, Supabase, MongoDB, FileSource)
- **Frontend Pages:** 5 (Home, DCL, AAM, Ontology, Live Flow)
- **Middleware Layers:** 5 (Tracing, Auth, Rate Limit, Idempotency, Audit)
- **Canonical Entities:** 3 (Account, Opportunity, Contact)
- **Database Tables:** 8+ (Users, Streams, Materialized views, etc.)

---

**Platform Capabilities:**
- ✅ Multi-tenant data isolation
- ✅ Real-time event visualization (Live Flow)
- ✅ Self-healing connectivity (AAM Drift Repair)
- ✅ Semantic field matching (RAG)
- ✅ Production-ready security (JWT, rate limiting)
- ✅ Comprehensive audit trail
