# AutonomOS Platform Architecture

## Table of Contents
1. [High-Level System Architecture](#high-level-system-architecture)
2. [Data Flow: Source → AAM → DCL](#data-flow-source--aam--dcl)
3. [AAM Components](#aam-components)
4. [Gateway Middleware Stack](#gateway-middleware-stack)
5. [Database Schema](#database-schema)
6. [Frontend Architecture](#frontend-architecture)

---

## High-Level System Architecture

```mermaid
graph TB
    subgraph "External Systems"
        SF[Salesforce]
        HS[HubSpot]
        DY[Dynamics]
        CSV[CSV Files]
    end

    subgraph "AutonomOS Platform"
        subgraph "Frontend Layer"
            UI[React/TypeScript UI]
            DCL_UI[DCL Graph Viz]
            AAM_UI[AAM Monitor Dashboard]
        end

        subgraph "API Gateway"
            MW_TRACE[Tracing Middleware]
            MW_AUTH[Auth Middleware]
            MW_RATE[Rate Limit Middleware]
            MW_IDEMPOT[Idempotency Middleware]
            MW_AUDIT[Audit Middleware]
        end

        subgraph "Backend Services"
            API[FastAPI Server]
            DCL[DCL Engine]
            AAM[AAM Orchestrator]
            WORKER[RQ Worker]
        end

        subgraph "Data Layer"
            PG[(PostgreSQL)]
            REDIS[(Redis)]
            DUCKDB[(DuckDB)]
        end

        subgraph "AI Layer"
            GEMINI[Gemini AI]
            OPENAI[OpenAI]
            RAG[RAG Engine]
        end
    end

    SF --> AAM
    HS --> AAM
    DY --> AAM
    CSV --> AAM

    UI --> MW_TRACE
    DCL_UI --> MW_TRACE
    AAM_UI --> MW_TRACE

    MW_TRACE --> MW_AUTH
    MW_AUTH --> MW_RATE
    MW_RATE --> MW_IDEMPOT
    MW_IDEMPOT --> MW_AUDIT
    MW_AUDIT --> API

    API --> DCL
    API --> AAM
    API --> WORKER

    AAM --> PG
    DCL --> DUCKDB
    WORKER --> REDIS
    
    AAM --> GEMINI
    AAM --> OPENAI
    DCL --> RAG

    style SF fill:#90EE90,color:#0D1117
    style HS fill:#90EE90,color:#0D1117
    style DY fill:#90EE90,color:#0D1117
    style CSV fill:#90EE90,color:#0D1117
    style UI fill:#87CEEB,color:#0D1117
    style PG fill:#FFD700,color:#0D1117
    style REDIS fill:#FF6347
```

---

## Data Flow: Source → AAM → DCL

```mermaid
graph LR
    subgraph "Data Sources"
        SF_OPP[Salesforce<br/>Opportunity]
        CSV_OPP[CSV File<br/>Opportunity]
    end

    subgraph "AAM - Adaptive API Mesh"
        CONN_SF[Salesforce<br/>Connector]
        CONN_FS[FileSource<br/>Connector]
        MAP_REG[Mapping<br/>Registry]
        CANON[Canonical<br/>Schema]
        STREAM[Canonical<br/>Streams DB]
    end

    subgraph "DCL - Data Catalog Layer"
        SUB[DCL<br/>Subscriber]
        MAT[Materialized<br/>Tables]
        VIEWS[DCL Views<br/>API]
    end

    subgraph "Frontend"
        UI[React UI]
        DEBUG[Debug<br/>Endpoint]
    end

    SF_OPP -->|REST API| CONN_SF
    CSV_OPP -->|CSV Read| CONN_FS

    CONN_SF -->|Apply Mapping| MAP_REG
    CONN_FS -->|Apply Mapping| MAP_REG

    MAP_REG -->|Transform| CANON
    CANON -->|Validate| STREAM

    STREAM -->|Process| SUB
    SUB -->|Upsert| MAT

    MAT -->|Query| VIEWS
    STREAM -->|Query| DEBUG

    VIEWS --> UI
    DEBUG --> UI

    style SF_OPP fill:#90EE90,color:#0D1117
    style CSV_OPP fill:#90EE90,color:#0D1117
    style CANON fill:#FFD700,color:#0D1117
    style STREAM fill:#FFD700,color:#0D1117
    style MAT fill:#87CEEB,color:#0D1117
```

---

## AAM Components

```mermaid
graph TB
    subgraph "AAM - Adaptive API Mesh"
        subgraph "Intelligence Plane"
            ORCH[AAM Orchestrator<br/>FastAPI Service]
            DRIFT[Drift Repair Agent<br/>Self-Healing]
            SCHEMA_OBS[Schema Observer<br/>Change Detection]
            RAG_ENG[RAG Engine<br/>Semantic Search]
        end

        subgraph "Execution Plane"
            CONN_SF[Salesforce Connector]
            CONN_FS[FileSource Connector]
            CONN_PG[PostgreSQL Connector<br/>Coming Soon]
        end

        subgraph "Control Plane"
            MAP_REG[Mapping Registry<br/>YAML Configs]
            CANON_SCH[Canonical Schemas<br/>Pydantic Models]
            CONN_REG[Connector Registry<br/>PostgreSQL]
        end

        subgraph "Canonical Layer"
            CANON_ACC[CanonicalAccount]
            CANON_OPP[CanonicalOpportunity]
            CANON_CON[CanonicalContact]
            CANON_EVT[CanonicalEvent<br/>Envelope]
        end
    end

    CONN_SF --> MAP_REG
    CONN_FS --> MAP_REG
    CONN_PG -.-> MAP_REG

    MAP_REG --> CANON_SCH
    CANON_SCH --> CANON_ACC
    CANON_SCH --> CANON_OPP
    CANON_SCH --> CANON_CON

    CANON_ACC --> CANON_EVT
    CANON_OPP --> CANON_EVT
    CANON_CON --> CANON_EVT

    ORCH --> DRIFT
    ORCH --> SCHEMA_OBS
    ORCH --> RAG_ENG

    DRIFT --> CONN_REG
    SCHEMA_OBS --> CONN_REG

    style CANON_EVT fill:#FFD700,color:#0D1117
    style MAP_REG fill:#87CEEB,color:#0D1117
    style DRIFT fill:#FF6347
```

---

## Gateway Middleware Stack

```mermaid
graph TD
    REQ[Incoming HTTP Request]
    
    REQ --> MW1[1. Tracing Middleware<br/>Generate trace_id]
    MW1 --> MW2[2. Auth Middleware<br/>JWT validation, tenant extraction]
    MW2 --> MW3[3. Rate Limit Middleware<br/>Per-tenant rate limiting]
    MW3 --> MW4[4. Idempotency Middleware<br/>Prevent duplicate requests]
    MW4 --> MW5[5. Audit Middleware<br/>Log all actions]
    
    MW5 --> ROUTE{Route?}
    
    ROUTE -->|/api/v1/auth| AUTH[Auth Endpoints]
    ROUTE -->|/api/v1/aoa| AOA[AOA Orchestration]
    ROUTE -->|/api/v1/aam| AAM[AAM Monitoring]
    ROUTE -->|/api/v1/filesource| FS[FileSource API]
    ROUTE -->|/api/v1/dcl/views| DCL_V[DCL Views API]
    ROUTE -->|/api/v1/debug| DEBUG[Debug Endpoints<br/>DEV_DEBUG=true]
    ROUTE -->|/dcl| DCL[DCL Engine]
    ROUTE -->|/| STATIC[Static Frontend]

    subgraph "Public Endpoints (Bypass Auth)"
        PUB1[/docs, /health]
        PUB2[/api/v1/auth/login]
        PUB3[/dcl/ws, /dcl/state]
        PUB4[/api/v1/aam/*]
        PUB5[/api/v1/debug/*]
    end

    style MW1 fill:#E6E6FA,color:#0D1117
    style MW2 fill:#FFB6C1,color:#0D1117
    style MW3 fill:#FFE4B5,color:#0D1117
    style MW4 fill:#B0E0E6,color:#0D1117
    style MW5 fill:#98FB98,color:#0D1117
    style DEBUG fill:#FF6347
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
    CANONICAL_STREAMS ||--o{ MATERIALIZED_CONTACTS : sources
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
        int employee_count
        string website
        jsonb extras
        datetime created_at
        datetime updated_at
    }

    MATERIALIZED_OPPORTUNITIES {
        int id PK
        string tenant_id
        string opportunity_id UK
        string account_id FK
        string name
        string stage
        decimal amount
        string currency
        date close_date
        string owner_id
        int probability
        jsonb extras
        datetime created_at
        datetime updated_at
    }

    MATERIALIZED_CONTACTS {
        int id PK
        string tenant_id
        string contact_id UK
        string account_id FK
        string first_name
        string last_name
        string email
        string phone
        string title
        jsonb extras
        datetime created_at
        datetime updated_at
    }

    JOB_HISTORY {
        int id PK
        string tenant_id
        string job_id
        string job_type
        string status
        jsonb result
        datetime created_at
    }

    DCL_CONNECTIONS {
        int id PK
        string connection_id UK
        string name
        string type
        jsonb config
        datetime created_at
    }
```

---

## Frontend Architecture

```mermaid
graph TB
    subgraph "React/TypeScript Frontend"
        subgraph "Pages"
            HOME[Home Page<br/>Hero + FAQ]
            DCL_PAGE[DCL Page<br/>Graph Visualization]
            AAM_PAGE[AAM Monitor<br/>Dashboard]
            ONT_PAGE[Ontology Page<br/>Data Mappings]
        end

        subgraph "Components"
            SANKEY[Sankey Graph<br/>D3.js]
            METRICS[Metrics Cards<br/>Real-time Stats]
            CONN_TABLE[Connection Health<br/>Table]
            EVENT_LOG[Events Log<br/>Recent Activity]
        end

        subgraph "WebSocket"
            WS[DCL WebSocket<br/>Real-time Updates]
        end

        subgraph "API Clients"
            API_DCL[DCL API Client]
            API_AAM[AAM API Client]
            API_DEBUG[Debug API Client]
        end
    end

    HOME --> DCL_PAGE
    HOME --> AAM_PAGE
    HOME --> ONT_PAGE

    DCL_PAGE --> SANKEY
    AAM_PAGE --> METRICS
    AAM_PAGE --> CONN_TABLE
    AAM_PAGE --> EVENT_LOG

    DCL_PAGE --> WS
    AAM_PAGE --> API_AAM
    DCL_PAGE --> API_DCL
    AAM_PAGE --> API_DEBUG

    WS -.->|Real-time| SANKEY
    API_AAM -.->|Polling| METRICS
    API_AAM -.->|Polling| CONN_TABLE
    API_DCL -.->|On-Demand| SANKEY

    style SANKEY fill:#87CEEB,color:#0D1117
    style WS fill:#90EE90,color:#0D1117
```

---

## Canonical Schema Type Hierarchy

```mermaid
graph TD
    CANON_EVT[CanonicalEvent<br/>Complete Envelope]
    
    subgraph "Metadata"
        META[CanonicalMeta<br/>version, tenant, trace_id]
        SRC[CanonicalSource<br/>system, connection_id]
    end

    subgraph "Entity Data (Union Type)"
        ACC[CanonicalAccount<br/>account_id, name, industry]
        OPP[CanonicalOpportunity<br/>opportunity_id, stage, amount]
        CON[CanonicalContact<br/>contact_id, email, phone]
    end

    CANON_EVT --> META
    CANON_EVT --> SRC
    CANON_EVT --> ACC
    CANON_EVT --> OPP
    CANON_EVT --> CON

    subgraph "Validation"
        VAL[model_validator<br/>Ensures entity matches data type]
    end

    CANON_EVT --> VAL

    style CANON_EVT fill:#FFD700,color:#0D1117
    style VAL fill:#FF6347
```

---

## Functional Probe Flow

```mermaid
sequenceDiagram
    participant Script as Functional Probe Script
    participant SF as Salesforce API
    participant Conn as SalesforceConnector
    participant Map as Mapping Registry
    participant Canon as Canonical Schema
    participant DB as canonical_streams
    participant Sub as DCL Subscriber
    participant Mat as materialized_opportunities
    participant API as DCL Views API
    
    Script->>SF: GET latest Opportunity (REST)
    SF-->>Script: Opportunity data (JSON)
    
    Script->>Conn: normalize_opportunity()
    Conn->>Map: apply_mapping(salesforce, opportunity)
    Map-->>Conn: canonical_data dict
    Conn->>Canon: CanonicalOpportunity(**data)
    Canon-->>Conn: Validated Pydantic model
    Conn-->>Script: CanonicalEvent
    
    Script->>Conn: emit_canonical_event()
    Conn->>DB: INSERT canonical event
    DB-->>Conn: Success
    
    Script->>Sub: process_canonical_streams()
    Sub->>DB: SELECT unprocessed events
    DB-->>Sub: Canonical events
    Sub->>Mat: UPSERT opportunity
    Mat-->>Sub: Success
    
    loop Exponential Backoff (max 10s)
        Script->>API: GET /dcl/views/opportunities?opportunity_id=X
        API->>Mat: SELECT WHERE opportunity_id=X
        Mat-->>API: Records
        API-->>Script: JSON response
        
        alt Record Found
            Script->>Script: Print PASS
        else No Record
            Script->>Script: Wait & Retry
        end
    end
```

---

## Key Design Patterns

### 1. **Multi-Tenancy**
- Every table has `tenant_id` for data isolation
- JWT tokens carry `tenant_id` for automatic scoping
- Middleware enforces tenant-based access control

### 2. **Strict Typing with Pydantic**
- `CanonicalEvent.data` is a Union of typed models
- `@model_validator` ensures entity type matches data
- Required fields enforced at event creation time

### 3. **Event-Driven Architecture**
- Connectors emit canonical events to streams
- DCL subscriber processes streams asynchronously
- WebSocket broadcasts state changes to frontend

### 4. **Idempotency**
- Trace IDs track request lifecycles
- Idempotency middleware prevents duplicate operations
- Upsert logic in DCL prevents duplicate data

### 5. **Feature Flags**
- `DEV_DEBUG` enables debug endpoints
- `FEATURE_USE_FILESOURCE` toggles FileSource connector
- `FEATURE_DRIFT_AUTOFIX` controls auto-repair

---

## Technology Stack Summary

| Layer | Technology |
|-------|-----------|
| **Frontend** | React, TypeScript, Vite, D3.js |
| **Backend** | FastAPI, Python 3.11, Uvicorn |
| **Database** | PostgreSQL (Replit), DuckDB (DCL) |
| **Cache/Queue** | Redis, Python RQ |
| **AI/LLM** | Gemini 2.5, OpenAI, RAG (multilingual-e5) |
| **Auth** | JWT (HS256), Argon2 password hashing |
| **Deployment** | Replit, Nix environment |

---

## Component Count Summary

- **Backend Microservices:** 5 (API, DCL, AAM Orchestrator, Worker, Auth Broker)
- **Connectors:** 2 (Salesforce, FileSource) + 1 planned (PostgreSQL)
- **Middleware Layers:** 5 (Tracing, Auth, Rate Limit, Idempotency, Audit)
- **API Endpoints:** 20+ (Auth, AOA, AAM, DCL, FileSource, Debug)
- **Database Tables:** 8+ (Users, CanonicalStreams, 3× Materialized, JobHistory, etc.)
- **Canonical Entities:** 3 (Account, Opportunity, Contact)
- **Frontend Pages:** 4 (Home, DCL, AAM Monitor, Ontology)
- **WebSocket Channels:** 1 (DCL real-time updates)

---

This architecture supports:
- ✅ Multi-tenant data isolation
- ✅ Strict type safety with Pydantic
- ✅ Real-time UI updates via WebSocket
- ✅ Self-healing connectivity (AAM Drift Repair)
- ✅ Semantic search with RAG
- ✅ Comprehensive audit trail
- ✅ Production-ready security (JWT, rate limiting)
