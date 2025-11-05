# AAM Hybrid - Full System Context

**Document Version:** 2.0  
**Last Updated:** November 2025  
**Status:** Production-Ready (All 4 Connectors Complete with Drift Detection)

---

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [System Components](#system-components)
4. [Data Models](#data-models)
5. [API Reference](#api-reference)
6. [Workflows & Processes](#workflows--processes)
7. [Configuration](#configuration)
8. [Deployment](#deployment)
9. [Security](#security)
10. [Future Roadmap](#future-roadmap)

---

## Executive Summary

### What is AAM Hybrid?

The **Adaptive API Mesh (AAM) Hybrid** is a production-ready microservices architecture that combines:
- **Airbyte OSS** for reliable data movement (Execution Plane)
- **FastAPI microservices** for intelligent orchestration (Intelligence Plane)
- **PostgreSQL Connector Registry** for state tracking and versioning (Control Plane)

### Business Value

AAM solves the problem of **fragile data pipelines** by:
1. **Automating schema drift detection and repair** - No more broken pipelines when APIs change
2. **Versioning all schema changes** - Complete audit trail for compliance
3. **Abstracting credential management** - Secure, centralized OAuth token handling
4. **Enabling programmatic connection management** - API-first infrastructure

### Current Capabilities (Production Ready)

✅ **4 Production Connectors**: Salesforce, FileSource (CSV), Supabase (PostgreSQL), MongoDB (NoSQL)  
✅ **Drift Detection**: SHA-256 schema fingerprinting with automatic ticket creation  
✅ **Self-Healing Repair**: Autonomous schema updates with confidence scoring (≥85% threshold)  
✅ **Canonical Event Normalization**: Unified data model for Accounts, Opportunities, Contacts  
✅ **YAML-Based Mappings**: Field mapping configurations in `services/aam/canonical/mappings/`  
✅ **Functional Testing**: End-to-end test scripts for drift detection and repair workflows  
✅ **Mutation Testing**: API endpoints for triggering schema changes (`/api/v1/mesh/test/supabase/mutate`, `/api/v1/mesh/test/mongo/mutate`)  
✅ **Human-in-the-Loop**: Manual repair approval endpoint (`/api/v1/mesh/repair/approve`)  

---

## Architecture Overview

### Three-Tier Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    INTELLIGENCE PLANE                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Orchestrator │  │ Auth Broker  │  │ Drift Repair Agent   │  │
│  │   :8001      │  │   :8002      │  │      :8003           │  │
│  │              │  │              │  │                      │  │
│  │ • Onboarding │  │ • OAuth      │  │ • Catalog Updates    │  │
│  │ • Sync Mgmt  │  │ • Credentials│  │ • Versioning         │  │
│  │ • Lifecycle  │  │ • Secrets    │  │ • Healing            │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
│         │                  │                     │              │
│         └──────────────────┼─────────────────────┘              │
│                            │                                    │
└────────────────────────────┼────────────────────────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────────┐
│                    EXECUTION PLANE                               │
│                            │                                    │
│  ┌─────────────────────────▼──────────────────────────────────┐ │
│  │            Airbyte OSS (via abctl) :8000                    │ │
│  │                                                              │ │
│  │  • 4 Production Connectors: Salesforce (OAuth2), FileSource │ │
│  │  •   (CSV), Supabase (PostgreSQL), MongoDB (NoSQL)          │ │
│  │  • Sync Orchestration & Scheduling                          │ │
│  │  • Change Data Capture (CDC)                                │ │
│  └──────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────────┐
│                     CONTROL PLANE                                │
│  ┌──────────────────────────▼──────────────────────────────────┐ │
│  │         PostgreSQL Connector Registry                       │ │
│  │                                                              │ │
│  │  Tables:                                                     │ │
│  │  • connections          - All managed connections           │ │
│  │  • sync_catalog_versions - Schema version history           │ │
│  │  • job_history          - Sync job audit trail              │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │         Redis Event Bus                                      │ │
│  │  • Inter-service messaging (future)                          │ │
│  │  • Distributed locking                                       │ │
│  │  • Task queuing                                              │ │
│  └──────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

### Design Principles

1. **Separation of Concerns**: Execution (Airbyte), Intelligence (FastAPI), and Control (PostgreSQL) are independent
2. **Fail-Fast**: Validation at startup and request time prevents silent failures
3. **Audit-First**: Every schema change and sync job is logged for compliance
4. **API-Driven**: All operations accessible via REST APIs for automation
5. **Stateless Services**: Microservices store state in PostgreSQL/Redis, enabling horizontal scaling

---

## System Components

### 1. Orchestrator Service (:8001)

**Purpose**: Central hub for connection lifecycle management

**Responsibilities**:
- Onboard new connections (create source → discover schema → create connection)
- Trigger manual sync jobs
- Query connection status and metadata
- Coordinate with Auth Broker and Drift Repair Agent

**Key Endpoints**:
- `POST /connections/onboard` - Onboard new connection
- `GET /connections` - List all connections
- `GET /connections/{id}` - Get connection details
- `POST /connections/{id}/sync` - Trigger sync job

**Dependencies**:
- Auth Broker (for credentials)
- Airbyte API (for source/connection creation)
- PostgreSQL (for state persistence)

**Startup Validation**:
```python
# Orchestrator validates these on boot:
- AIRBYTE_CLIENT_ID
- AIRBYTE_CLIENT_SECRET
- AIRBYTE_WORKSPACE_ID
- AIRBYTE_DESTINATION_ID

# Fails with clear error if missing
```

---

### 2. Auth Broker Service (:8002)

**Purpose**: Secure credential management and retrieval

**Responsibilities**:
- Store and retrieve OAuth credentials
- Abstract credential complexity from other services
- Validate credential completeness before returning
- Future: Integrate with HashiCorp Vault, AWS Secrets Manager

**Key Endpoints**:
- `GET /credentials/{credential_id}` - Generic credential retrieval
- `GET /credentials/salesforce/{credential_id}` - Salesforce OAuth config

**Security Model** (Current MVP):
```
Environment Variables → Auth Broker → Sanitized Config → Orchestrator
                ↓
         Never logged or exposed
```

**Production Enhancement** (Future):
```
HashiCorp Vault → Auth Broker → Time-limited tokens → Orchestrator
       ↓
  Audit logging
```

---

### 3. Drift Repair Agent Service (:8003)

**Purpose**: Automated schema drift detection and healing

**Responsibilities**:
- Accept new syncCatalog updates
- Update Airbyte connection configurations
- Version catalog changes in PostgreSQL
- Transition connection status (ACTIVE → HEALING → ACTIVE/FAILED)

**Key Endpoints**:
- `POST /repair/apply_new_catalog` - Apply catalog update

**Workflow**:
```
1. Connection status → HEALING
2. Update Airbyte connection catalog via API
3. Get current max version from sync_catalog_versions
4. Insert new version (version_number = max + 1)
5. Connection status → ACTIVE (or FAILED on error)
```

**Versioning Example**:
```sql
-- Initial catalog
version_number: 1
streams: [Account, Contact]

-- After drift detected
version_number: 2  
streams: [Account, Contact, Opportunity]  ← New object added

-- Complete audit trail maintained
```

---

### 4. Production Connector Suite

**Status**: Production-Ready (4 Connectors Complete)

**Connectors**:

#### **Salesforce Connector**
- OAuth2 authentication with CRM integration
- Entities: Account, Opportunity, Contact
- Full CRUD operations
- Canonical event emission to `canonical_streams` table
- YAML mapping: `services/aam/canonical/mappings/salesforce.yaml`

#### **FileSource Connector (CSV/Excel)**
- Local file ingestion with schema detection
- Entities: accounts, opportunities from CSV files
- Idempotent uploads and data validation
- YAML mapping: `services/aam/canonical/mappings/filesource.yaml`

#### **Supabase Connector (PostgreSQL)**
- Cloud PostgreSQL database connector
- Schema mutation testing endpoint: `/api/v1/mesh/test/supabase/mutate`
- Drift detection with SHA-256 fingerprinting
- Auto-repair with confidence scoring
- Idempotent seed data methods for testing
- YAML mapping: `services/aam/canonical/mappings/supabase.yaml`

#### **MongoDB Connector (NoSQL)**
- Document database connector with BSON handling
- Collections: accounts, opportunities
- Schema mutation testing endpoint: `/api/v1/mesh/test/mongo/mutate`
- Drift detection and repair workflow
- Canonical event normalization
- YAML mapping: `services/aam/canonical/mappings/mongodb.yaml`

**Drift Detection Workflow**:
1. Schema fingerprinting via SHA-256 hashing
2. Drift tickets created in `drift_events` table with confidence scores
3. Auto-repair executes if confidence ≥85%, manual approval otherwise
4. Repair approval endpoint: `/api/v1/mesh/repair/approve`

**Testing Infrastructure**:
- `scripts/aam/ingest_seed.py` - Seed Supabase and MongoDB with demo data
- `scripts/aam/drift_supabase.py` - Test Supabase drift detection
- `scripts/aam/drift_mongo.py` - Test MongoDB drift detection
- `scripts/aam/e2e_revops_probe.py` - Full RevOps pipeline validation

---

### 5. Schema Observer & Drift Detection

**Status**: Production-Ready

**Capabilities**:
- SHA-256 schema fingerprinting for all 4 connectors
- Automatic drift ticket creation in `drift_events` table
- Confidence scoring for repair proposals
- Integration with Drift Repair Agent for autonomous updates

**Database Tables**:
- `drift_events` - Schema drift detection and repair tickets
- `schema_changes` - Historical schema version tracking
- `canonical_streams` - Normalized event log (append-only)

**Drift Event Schema**:
```python
class DriftEvent:
    id: UUID
    tenant_id: UUID
    connection_id: UUID
    event_type: str  # 'field_added', 'field_renamed', 'field_removed'
    old_schema: JSON
    new_schema: JSON
    confidence: float  # 0.0 - 1.0
    status: str  # 'pending', 'approved', 'repaired', 'failed'
    created_at: datetime
```

### 6. Canonical Schema & Event Normalization

**Purpose**: Unified data model across all connectors

**Canonical Entities**:
- **CanonicalAccount** - Unified account schema
- **CanonicalOpportunity** - Unified opportunity schema
- **CanonicalContact** - Unified contact schema (future)

**Canonical Event Structure**:
```python
class CanonicalEvent:
    meta: CanonicalMeta  # version, tenant, trace_id, emitted_at
    source: CanonicalSource  # system, connection_id, schema_version
    entity: str  # 'account', 'opportunity', 'contact'
    op: str  # 'upsert', 'delete'
    data: Union[CanonicalAccount, CanonicalOpportunity]  # Pydantic validated
    unknown_fields: Dict[str, Any]  # Fields not in canonical schema
```

**Mapping Registry**:
- YAML-based field mappings in `services/aam/canonical/mappings/`
- Supports nested field mapping (e.g., `annual_revenue` → `extras.annual_revenue`)
- Unknown fields automatically captured for manual review

---

### 6. Shared Library (`shared/`)

**Purpose**: Common code shared across all microservices

**Modules**:

#### `config.py`
```python
class Settings(BaseSettings):
    # Airbyte
    AIRBYTE_API_URL: str
    AIRBYTE_CLIENT_ID: Optional[str]
    AIRBYTE_CLIENT_SECRET: Optional[str]
    AIRBYTE_WORKSPACE_ID: Optional[str]
    AIRBYTE_DESTINATION_ID: Optional[str]
    
    # Salesforce
    SALESFORCE_CLIENT_ID: Optional[str]
    SALESFORCE_CLIENT_SECRET: Optional[str]
    SALESFORCE_REFRESH_TOKEN: Optional[str]
    
    # Infrastructure
    SUPABASE_DB_URL: str
    REDIS_URL: str
    SECRET_KEY: str
```

#### `database.py`
- Async SQLAlchemy engine and session management
- `get_db()` dependency for FastAPI routes
- `init_db()` creates all tables on startup

#### `models.py`
- SQLAlchemy ORM models (Connection, SyncCatalogVersion, JobHistory)
- Pydantic schemas for API request/response validation
- Enums (ConnectionStatus, JobStatus)

#### `airbyte_client.py`
- Async httpx client wrapper for Airbyte API
- OAuth2 token management
- Methods:
  - `get_source_definition_id(source_type)`
  - `create_source(workspace_id, source_definition_id, config, name)`
  - `discover_schema(source_id)`
  - `create_connection(source_id, destination_id, sync_catalog, name)`
  - `update_connection(connection_id, sync_catalog)`
  - `trigger_sync(connection_id)`

---

## Data Models

### Database Schema

#### **connections** table
```sql
CREATE TABLE connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    source_type VARCHAR(100) NOT NULL,  -- e.g., "Salesforce", "PostgreSQL"
    airbyte_source_id UUID NOT NULL,    -- Airbyte source ID
    airbyte_connection_id UUID NOT NULL, -- Airbyte connection ID
    status VARCHAR(50) NOT NULL,         -- PENDING, ACTIVE, FAILED, HEALING
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_connections_status ON connections(status);
CREATE INDEX idx_connections_source_type ON connections(source_type);
```

**Status Lifecycle**:
- `PENDING` → Initial state during onboarding
- `ACTIVE` → Connection successfully created and ready
- `HEALING` → Schema drift repair in progress
- `FAILED` → Onboarding or healing failed

#### **sync_catalog_versions** table
```sql
CREATE TABLE sync_catalog_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connection_id UUID REFERENCES connections(id) ON DELETE CASCADE,
    sync_catalog JSONB NOT NULL,          -- Full Airbyte syncCatalog object
    version_number INTEGER NOT NULL,       -- Incremental version (1, 2, 3...)
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_catalog_connection_version 
    ON sync_catalog_versions(connection_id, version_number);
CREATE INDEX idx_catalog_created ON sync_catalog_versions(created_at DESC);
```

**Example syncCatalog**:
```json
{
  "streams": [
    {
      "stream": {
        "name": "Account",
        "json_schema": {
          "type": "object",
          "properties": {
            "Id": {"type": "string"},
            "Name": {"type": "string"}
          }
        },
        "supported_sync_modes": ["full_refresh", "incremental"]
      },
      "sync_mode": "incremental",
      "destination_sync_mode": "append_dedup"
    }
  ]
}
```

#### **job_history** table
```sql
CREATE TABLE job_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connection_id UUID REFERENCES connections(id) ON DELETE CASCADE,
    airbyte_job_id VARCHAR(255),           -- Airbyte's job identifier
    status VARCHAR(50) NOT NULL,           -- pending, running, succeeded, failed
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_job_connection ON job_history(connection_id);
CREATE INDEX idx_job_status ON job_history(status);
```

---

## API Reference

### Orchestrator API (:8001)

#### POST /connections/onboard

**Purpose**: Onboard a new data source connection

**Request Body**:
```json
{
  "source_type": "Salesforce",
  "connection_name": "Salesforce Production",
  "credential_id": "salesforce-prod"
}
```

**Response** (201 Created):
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "name": "Salesforce Production",
  "source_type": "Salesforce",
  "status": "ACTIVE",
  "airbyte_source_id": "e5f6-7890-abcd-ef12",
  "airbyte_connection_id": "7890-abcd-ef12-3456",
  "created_at": "2025-01-15T10:30:00Z"
}
```

**Process Flow**:
```
1. Validate request
2. Call Auth Broker → Get credentials
3. Call Airbyte → Get source definition ID
4. Call Airbyte → Create source
5. Call Airbyte → Discover schema
6. Call Airbyte → Create connection
7. Save to PostgreSQL → connections table
8. Save initial catalog → sync_catalog_versions (v1)
9. Return connection details
```

**Error Responses**:
- `500` - Missing Airbyte/Salesforce credentials
- `400` - Invalid source_type
- `500` - Airbyte API failure

---

#### GET /connections

**Purpose**: List all managed connections

**Response** (200 OK):
```json
[
  {
    "id": "uuid",
    "name": "Salesforce Production",
    "source_type": "Salesforce",
    "status": "ACTIVE",
    "airbyte_source_id": "uuid",
    "airbyte_connection_id": "uuid",
    "created_at": "2025-01-15T10:30:00Z"
  }
]
```

---

#### GET /connections/{id}

**Purpose**: Get details for a specific connection

**Response** (200 OK):
```json
{
  "id": "uuid",
  "name": "Salesforce Production",
  "source_type": "Salesforce",
  "status": "ACTIVE",
  "airbyte_source_id": "uuid",
  "airbyte_connection_id": "uuid",
  "created_at": "2025-01-15T10:30:00Z"
}
```

---

#### POST /connections/{id}/sync

**Purpose**: Trigger manual sync job

**Response** (200 OK):
```json
{
  "connection_id": "uuid",
  "job_id": "12345678",
  "status": "triggered",
  "message": "Sync job started successfully"
}
```

---

### Auth Broker API (:8002)

#### GET /credentials/salesforce/{credential_id}

**Purpose**: Get Salesforce OAuth configuration

**Response** (200 OK):
```json
{
  "client_id": "3MVG9...",
  "client_secret": "ABC123...",
  "refresh_token": "5Aep861...",
  "is_sandbox": false,
  "auth_type": "Client",
  "start_date": "2024-01-01T00:00:00Z"
}
```

**Error Responses**:
- `500` - Missing SALESFORCE_CLIENT_ID, SALESFORCE_CLIENT_SECRET, or SALESFORCE_REFRESH_TOKEN

---

### Drift Repair Agent API (:8003)

#### POST /repair/apply_new_catalog

**Purpose**: Apply schema drift repair

**Request Body**:
```json
{
  "connection_id": "uuid",
  "new_sync_catalog": {
    "streams": [
      {
        "stream": {
          "name": "Account",
          "json_schema": {...},
          "supported_sync_modes": ["full_refresh", "incremental"]
        },
        "sync_mode": "incremental",
        "destination_sync_mode": "append_dedup"
      }
    ]
  }
}
```

**Response** (200 OK):
```json
{
  "connection_id": "uuid",
  "previous_version": 1,
  "new_version": 2,
  "status": "success",
  "message": "Catalog updated and versioned successfully"
}
```

---

## Workflows & Processes

### Connection Onboarding Flow

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ POST /connections/onboard
       ▼
┌─────────────────────────────────────────┐
│         Orchestrator                    │
│  1. Validate request                    │
│  2. Call Auth Broker                    │──────┐
└─────────────────────────────────────────┘      │
       │                                          ▼
       │                               ┌──────────────────┐
       │                               │  Auth Broker     │
       │                               │  Return OAuth    │
       │                               └──────────────────┘
       ▼
┌─────────────────────────────────────────┐
│  3. Get source definition ID            │
│  4. Create source                       │
│  5. Discover schema                     │──────► Airbyte API
│  6. Create connection                   │
└─────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  7. Save to connections table           │
│  8. Save catalog to sync_catalog_v1     │──────► PostgreSQL
└─────────────────────────────────────────┘
       │
       ▼
   Return connection details
```

---

### Schema Drift Repair Flow

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ POST /repair/apply_new_catalog
       ▼
┌─────────────────────────────────────────┐
│      Drift Repair Agent                 │
│  1. Fetch connection from DB            │
│  2. Set status → HEALING                │──────► PostgreSQL
└─────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  3. Update Airbyte connection catalog   │──────► Airbyte API
└─────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  4. Get max version from DB             │
│  5. Insert new catalog version          │──────► PostgreSQL
│  6. Set status → ACTIVE                 │
└─────────────────────────────────────────┘
       │
       ▼
   Return version details
```

---

## Configuration

### Required Environment Variables

**Orchestrator, Drift Repair Agent**:
```bash
# REQUIRED - Services will not start without these
AIRBYTE_API_URL=http://localhost:8000/api/public/v1
AIRBYTE_CLIENT_ID=<from abctl local credentials>
AIRBYTE_CLIENT_SECRET=<from abctl local credentials>
AIRBYTE_WORKSPACE_ID=<from Airbyte UI>
AIRBYTE_DESTINATION_ID=<from Airbyte UI>
```

**Auth Broker**:
```bash
# REQUIRED for Salesforce connections
SALESFORCE_CLIENT_ID=<Salesforce Consumer Key>
SALESFORCE_CLIENT_SECRET=<Salesforce Consumer Secret>
SALESFORCE_REFRESH_TOKEN=<OAuth Refresh Token>
```

**All Services**:
```bash
SUPABASE_DB_URL=postgresql://user:pass@host:port/db
REDIS_URL=redis://localhost:6379
SECRET_KEY=random-32-character-string
```

### Startup Validation

The Orchestrator validates configuration on boot:

```python
# startup_check.py
def validate_configuration():
    missing = []
    
    # Critical checks (fail-fast)
    if not AIRBYTE_CLIENT_ID:
        missing.append("AIRBYTE_CLIENT_ID")
    if not AIRBYTE_WORKSPACE_ID:
        missing.append("AIRBYTE_WORKSPACE_ID")
    
    if missing:
        raise Exception(f"Missing required: {missing}")
    
    # Warning for optional
    if not SALESFORCE_CLIENT_ID:
        logger.warning("Salesforce onboarding will fail")
```

**Success Output**:
```
INFO: ✅ Configuration validation passed
INFO: Airbyte API: http://localhost:8000/api/public/v1
INFO: Workspace ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890
INFO: Destination ID: b2c3d4e5-f6a7-8901-bcde-f2345678901a
```

**Failure Output**:
```
ERROR: ❌ CRITICAL: Missing required Airbyte credentials: AIRBYTE_CLIENT_ID, AIRBYTE_WORKSPACE_ID

These are REQUIRED for AAM to function. Please:
1. Run: abctl local credentials
2. Set AIRBYTE_CLIENT_ID and AIRBYTE_CLIENT_SECRET from the output
3. Get AIRBYTE_WORKSPACE_ID and AIRBYTE_DESTINATION_ID from Airbyte UI
4. Update your .env file or docker-compose environment variables
```

---

## Deployment

### Docker Compose (Recommended)

**Prerequisites**:
1. Airbyte running on host (`abctl local install`)
2. `.env` file with all required credentials

**Start All Services**:
```bash
cd aam-hybrid
docker-compose up -d
```

**Services Started**:
- PostgreSQL (:5433)
- Redis (:6379)
- Auth Broker (:8002)
- Orchestrator (:8001)
- Drift Repair Agent (:8003)
- Schema Observer (:8004)
- RAG Engine (:8005)

**View Logs**:
```bash
docker-compose logs -f orchestrator
docker-compose logs -f auth_broker
docker-compose logs -f drift_repair_agent
```

**Health Checks**:
```bash
curl http://localhost:8001/health  # Orchestrator
curl http://localhost:8002/health  # Auth Broker
curl http://localhost:8003/health  # Drift Repair
```

---

### Local Development

**Run Services Individually**:

```bash
# Terminal 1: Auth Broker
cd aam-hybrid
export $(cat .env | xargs)
python -m services.auth_broker.main

# Terminal 2: Orchestrator
export $(cat .env | xargs)
python -m services.orchestrator.main

# Terminal 3: Drift Repair
export $(cat .env | xargs)
python -m services.drift_repair_agent.main
```

---

### Kubernetes (Future)

**Planned Architecture**:
```yaml
# Deployment structure
deployments:
  - orchestrator (3 replicas)
  - auth-broker (2 replicas)
  - drift-repair (2 replicas)
  - schema-observer (1 replica)
  - rag-engine (1 replica)

services:
  - orchestrator-service (ClusterIP)
  - auth-broker-service (ClusterIP)
  - drift-repair-service (ClusterIP)

ingress:
  - /api/orchestrator → orchestrator-service
  - /api/auth → auth-broker-service

configmaps:
  - airbyte-config
  - service-ports

secrets:
  - airbyte-credentials
  - salesforce-oauth
  - database-url
```

---

## Security

### Current Security Model (MVP)

**Credential Storage**:
- Environment variables (`.env` file)
- Passed to containers via docker-compose
- Never logged or exposed in API responses

**OAuth Flow**:
```
Salesforce → OAuth 2.0 Web Server Flow → Refresh Token → .env
                                              ↓
                                        Auth Broker
                                              ↓
                                        Orchestrator
                                              ↓
                                         Airbyte
```

**API Security**:
- No authentication (MVP - internal services only)
- CORS enabled for development
- All services communicate over internal network

---

### Production Security Roadmap

#### Phase 1: Secret Management
- [ ] Integrate HashiCorp Vault for credential storage
- [ ] Implement secret rotation (90-day expiry)
- [ ] Use IAM roles instead of static credentials

#### Phase 2: API Security
- [ ] JWT authentication for all endpoints
- [ ] API key management for external clients
- [ ] Rate limiting (100 req/min per client)

#### Phase 3: Network Security
- [ ] mTLS between microservices
- [ ] Private subnets for services
- [ ] Bastion host for Airbyte access

#### Phase 4: Compliance
- [ ] Audit logging for all credential access
- [ ] Encryption at rest for PostgreSQL
- [ ] SOC 2 Type II compliance

---

## Implementation Status

### ✅ Phase 3: Advanced Intelligence - **COMPLETE**

**Schema Observer** - Automated Drift Detection ✅
- ✅ Schema fingerprinting for Supabase (PostgreSQL) via information_schema
- ✅ Schema fingerprinting for MongoDB via document sampling
- ✅ Drift detection with confidence scoring (0.75-1.0 range)
- ✅ Drift ticket generation to `drift_events` table
- ✅ Production code: `services/aam/schema_observer.py` (269 lines)

**Drift Repair System** - Auto-Healing ✅
- ✅ Manual approval endpoint: `/api/v1/mesh/repair/approve`
- ✅ Auto-repair for high-confidence changes (≥85%)
- ✅ Human-in-the-loop for low-confidence changes (<85%)
- ✅ Schema mutation testing endpoints for Supabase and MongoDB
- ✅ Comprehensive test scripts in `scripts/aam/`

**Production Connector Suite** ✅
- ✅ Salesforce (OAuth2 CRM connector)
- ✅ FileSource (CSV/Excel file ingestion)
- ✅ Supabase (PostgreSQL cloud connector)
- ✅ MongoDB (NoSQL document connector)

**Canonical Event Normalization** ✅
- ✅ YAML-based field mappings in `services/aam/canonical/mappings/`
- ✅ Pydantic validation with `CanonicalAccount`, `CanonicalOpportunity`
- ✅ Append-only event log in `canonical_streams` table
- ✅ Unknown field capture for manual review

---

## Future Roadmap

### Phase 4: Production Hardening - **IN PROGRESS**

**Observability** (Partially Complete):
- ✅ AAM monitoring dashboard with real-time metrics
- ✅ Drift event tracking (24h windows)
- ✅ Repair performance metrics endpoints
- ✅ Connection health monitoring
- ⏳ Prometheus metrics for all services (planned)
- ⏳ Distributed tracing with Jaeger (planned)
- ⏳ Centralized logging with ELK stack (planned)

**RAG Engine** - AI-Powered Mapping (Planned):
- ⏳ Ingest source schemas and destination models
- ⏳ Use RAG to suggest field mappings based on:
  - Field names and data types
  - Historical user mappings
  - Industry-standard ontologies
- ⏳ Learn from user corrections
- ⏳ Generate dbt transformation logic

---

### Phase 4: Production Hardening (6 Months)

**Observability**:
- Prometheus metrics for all services
- Grafana dashboards for drift monitoring
- Distributed tracing with Jaeger
- Centralized logging with ELK stack

**Resilience**:
- Circuit breakers for Airbyte API calls
- Exponential backoff with jitter
- Dead letter queues for failed operations
- Health checks with auto-restart

**Performance**:
- Connection pooling for PostgreSQL
- Redis caching for frequently accessed credentials
- Horizontal pod autoscaling (Kubernetes)
- Database query optimization

---

### Phase 5: Multi-Source Intelligence (12 Months)

**Cross-Source Schema Unification**:
- Detect duplicate entities across sources
- Recommend master data management strategies
- Auto-generate unified views

**Intelligent Sync Scheduling**:
- ML-based prediction of data change frequency
- Adaptive sync intervals (hourly → daily based on patterns)
- Cost optimization for API calls

---

## Metrics & Monitoring

### Key Performance Indicators (KPIs)

**Reliability**:
- Connection uptime: 99.9% target
- Drift repair success rate: 95% target
- Mean time to repair (MTTR): < 5 minutes

**Performance**:
- Onboarding latency: < 30 seconds
- Catalog update latency: < 10 seconds
- API response time (p95): < 500ms

**Business**:
- Total connections managed
- Schema changes detected per week
- Manual interventions avoided

---

## Troubleshooting Guide

### Common Issues

**Issue**: Orchestrator fails to start with "Missing required Airbyte credentials"

**Solution**:
```bash
# Get Airbyte credentials
abctl local credentials

# Update .env
AIRBYTE_CLIENT_ID=<from above>
AIRBYTE_CLIENT_SECRET=<from above>

# Get workspace/destination IDs from Airbyte UI
# Update .env and restart
docker-compose restart orchestrator
```

---

**Issue**: Onboarding fails with "Auth Broker error: 500"

**Solution**:
```bash
# Check Auth Broker logs
docker-compose logs auth_broker

# Likely missing Salesforce credentials
# Add to .env:
SALESFORCE_CLIENT_ID=...
SALESFORCE_CLIENT_SECRET=...
SALESFORCE_REFRESH_TOKEN=...

docker-compose restart auth_broker orchestrator
```

---

**Issue**: Catalog update fails with "Connection has no Airbyte connection ID"

**Solution**:
```sql
-- Check connection record
SELECT * FROM connections WHERE id = 'uuid';

-- If airbyte_connection_id is NULL, re-onboard
```

---

## Appendix

### File Structure
```
aam-hybrid/
├── services/
│   ├── orchestrator/
│   │   ├── main.py              # FastAPI app
│   │   ├── service.py           # Business logic
│   │   ├── startup_check.py     # Config validation
│   │   └── Dockerfile
│   ├── auth_broker/
│   │   ├── main.py
│   │   ├── service.py
│   │   └── Dockerfile
│   ├── drift_repair_agent/
│   │   ├── main.py
│   │   ├── service.py
│   │   └── Dockerfile
│   ├── schema_observer/
│   │   └── main.py              # Skeleton
│   └── rag_engine/
│       └── main.py              # Skeleton
├── shared/
│   ├── __init__.py
│   ├── config.py                # Pydantic settings
│   ├── database.py              # SQLAlchemy async
│   ├── models.py                # ORM + Pydantic
│   └── airbyte_client.py        # Airbyte API wrapper
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── README.md
├── CONFIGURATION_GUIDE.md
├── AIRBYTE_SETUP.md
├── AAM_FULL_CONTEXT.md          # This file
├── test_health.sh
└── test_onboarding.sh
```

---

### Technology Stack

**Languages**:
- Python 3.11+ (all microservices)

**Frameworks**:
- FastAPI (web framework)
- SQLAlchemy 2.0 (async ORM)
- Pydantic (data validation)

**Infrastructure**:
- PostgreSQL 15+ (state storage)
- Redis 7+ (event bus)
- Docker & Docker Compose (containerization)
- Airbyte OSS 0.50+ (data movement)

**HTTP Client**:
- httpx (async HTTP for Airbyte API)

**Development Tools**:
- uvicorn (ASGI server)
- mypy (type checking)
- black (code formatting)
- pytest (testing)

---

### Contact & Support

**Documentation**:
- API Docs: `http://localhost:8001/docs` (Swagger UI)
- ReDoc: `http://localhost:8001/redoc`

**Support Channels**:
- GitHub Issues: [link]
- Slack: #aam-hybrid
- Email: support@autonomos.com

---

**END OF DOCUMENT**

*This document provides a complete technical overview of the AAM Hybrid MVP. For specific implementation details, refer to the codebase and inline documentation.*
