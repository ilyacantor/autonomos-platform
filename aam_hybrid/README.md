# AAM Hybrid MVP - Adaptive API Mesh

**Last Updated:** November 19, 2025

## Overview

The **Adaptive API Mesh (AAM)** is a hybrid architecture that combines:
- **Execution Plane**: Airbyte OSS for data movement
- **Intelligence/Control Planes**: FastAPI microservices for orchestration
- **Connector Registry**: PostgreSQL/Supabase for state tracking and versioning

This implementation delivers **Phase 1 (Infrastructure), Phase 2 (Orchestration), and Phase 3 (Advanced Intelligence)** of the AAM platform, featuring 4 production connectors, complete drift detection with schema fingerprinting, autonomous auto-repair with confidence scoring, and canonical event normalization.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      AAM HYBRID ARCHITECTURE                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────┐  ┌────────────────┐  ┌─────────────────┐   │
│  │  Orchestrator  │  │  Auth Broker   │  │ Drift Repair    │   │
│  │     :8001      │  │     :8002      │  │   Agent :8003   │   │
│  └────────┬───────┘  └────────┬───────┘  └────────┬────────┘   │
│           │                   │                    │            │
│           └───────────────────┼────────────────────┘            │
│                               │                                 │
│  ┌────────────────────────────┼────────────────────────────┐   │
│  │         SHARED LAYER       │                            │   │
│  │  • Airbyte Client (httpx)  │                            │   │
│  │  • Database (SQLAlchemy)   │                            │   │
│  │  • Models & Config         │                            │   │
│  └────────────────────────────┼────────────────────────────┘   │
│                               │                                 │
│  ┌────────────────────────────┼────────────────────────────┐   │
│  │      EXECUTION PLANE       │                            │   │
│  │   ┌────────────────────────▼─────────────────────┐      │   │
│  │   │    Airbyte OSS (via abctl)  :8000           │      │   │
│  │   │  • Source Connectors (Salesforce, etc.)     │      │   │
│  │   │  • Destination Connectors                   │      │   │
│  │   │  • Sync Orchestration                       │      │   │
│  │   └─────────────────────────────────────────────┘      │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐   │
│  │      CONNECTOR REGISTRY (PostgreSQL/Supabase)          │   │
│  │  • Connections                                         │   │
│  │  • SyncCatalogVersions (Schema Versioning)             │   │
│  │  • JobHistory                                          │   │
│  └────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Features Implemented

### ✅ Phase 1: Infrastructure
- [x] Async PostgreSQL database with SQLAlchemy
- [x] Airbyte async API client with OAuth2 authentication
- [x] Versioned schema tracking (SyncCatalogVersion)
- [x] Docker Compose orchestration
- [x] Microservice skeletons for all components

### ✅ Phase 2: Orchestration
- [x] **Auth Broker**: Secure credential retrieval
- [x] **AAM Orchestrator**: Connection onboarding workflow
- [x] **Drift Repair Agent**: Catalog update and versioning
- [x] **Sync Triggering**: Manual job execution
- [x] **Registry Versioning**: Full audit trail of schema changes

### ✅ Phase 3: Advanced Intelligence
- [x] **Schema Observer**: Automated drift detection with fingerprinting
- [x] **4 Production Connectors**: Salesforce, FileSource, Supabase, MongoDB
- [x] **Auto-Repair**: Confidence scoring (≥85% threshold)
- [x] **Canonical Events**: Unified data model with Pydantic validation
- [x] **YAML Mappings**: Field mapping registry
- [x] **Testing Suite**: Mutation endpoints and functional test scripts
- [x] **Monitoring**: Real-time AAM dashboard with drift metrics

---

## Project Structure

```
aam-hybrid/
├── services/
│   ├── orchestrator/           # Main orchestration service
│   │   ├── main.py            # FastAPI app
│   │   ├── service.py         # Business logic
│   │   ├── Dockerfile
│   │   └── __init__.py
│   ├── auth_broker/           # Credential management
│   │   ├── main.py
│   │   ├── service.py
│   │   ├── Dockerfile
│   │   └── __init__.py
│   ├── drift_repair_agent/    # Schema drift repair
│   │   ├── main.py
│   │   ├── service.py
│   │   ├── Dockerfile
│   │   └── __init__.py
│   ├── connectors/            # Production connector suite
│   │   ├── salesforce/       # OAuth2 CRM connector
│   │   ├── filesource/       # CSV/Excel file ingestion
│   │   ├── supabase/         # PostgreSQL cloud connector
│   │   └── mongodb/          # NoSQL document connector
│   ├── canonical/            # Event normalization
│   │   ├── mappings/         # YAML field mappings
│   │   ├── schemas.py        # Canonical Pydantic models
│   │   └── mapping_registry.py
│   └── schema_observer.py    # Drift detection (269 lines)
├── shared/
│   ├── airbyte_client.py      # Async Airbyte API wrapper
│   ├── database.py            # SQLAlchemy async setup
│   ├── models.py              # DB and Pydantic models
│   ├── config.py              # Pydantic settings
│   └── __init__.py
├── docker-compose.yml         # Service orchestration
├── requirements.txt
├── AIRBYTE_SETUP.md          # Airbyte installation guide
├── .env.example
└── README.md                  # This file
```

---

## Quick Start

### 1. Prerequisites

- **Docker Desktop** or Docker Engine
- **Python 3.11+**
- **Airbyte OSS** installed via `abctl` (see [AIRBYTE_SETUP.md](./AIRBYTE_SETUP.md))
- **PostgreSQL** database (Supabase or local)
- **Redis** instance

### 2. Install Dependencies

```bash
cd aam-hybrid
pip install -r requirements.txt
```

### 3. Configure Environment

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Airbyte Configuration (REQUIRED)
AIRBYTE_API_URL=http://localhost:8000/api/public/v1
AIRBYTE_CLIENT_ID=<from abctl local credentials>
AIRBYTE_CLIENT_SECRET=<from abctl local credentials>
AIRBYTE_WORKSPACE_ID=<from Airbyte UI - see below>
AIRBYTE_DESTINATION_ID=<from Airbyte UI - see below>

# Database
SUPABASE_DB_URL=postgresql://user:password@host:port/database

# Redis
REDIS_URL=redis://localhost:6379

# Salesforce OAuth Credentials (REQUIRED for Salesforce connections)
SALESFORCE_CLIENT_ID=<your-salesforce-client-id>
SALESFORCE_CLIENT_SECRET=<your-salesforce-client-secret>
SALESFORCE_REFRESH_TOKEN=<your-salesforce-refresh-token>
```

**IMPORTANT:** All Airbyte credentials are REQUIRED. The Orchestrator will fail to start if any are missing. Salesforce credentials are optional but required if you want to onboard Salesforce connections.

**Getting Salesforce OAuth Refresh Token:**
1. Create a Connected App in Salesforce Setup → App Manager
2. Enable OAuth Settings with callback URL and scopes: `api refresh_token offline_access`
3. Use OAuth 2.0 Web Server Flow to authenticate and obtain tokens
4. Save the `refresh_token` - it persists until manually revoked

### 4. Start Services

**Option A: Docker Compose (Recommended)**
```bash
docker-compose up -d
```

**Option B: Local Development**
```bash
# Terminal 1: Auth Broker
python -m services.auth_broker.main

# Terminal 2: Orchestrator
python -m services.orchestrator.main

# Terminal 3: Drift Repair Agent
python -m services.drift_repair_agent.main
```

### 5. Verify Health

```bash
curl http://localhost:8001/health  # Orchestrator
curl http://localhost:8002/health  # Auth Broker
curl http://localhost:8003/health  # Drift Repair Agent
```

---

## API Endpoints

### **Auth Broker** (Port 8002)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/credentials/{credential_id}` | Get generic credentials |
| GET | `/credentials/salesforce/{credential_id}` | Get Salesforce config |

### **AAM Orchestrator** (Port 8001)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/connections/onboard` | Onboard new connection |
| GET | `/connections` | List all connections |
| GET | `/connections/{id}` | Get connection details |
| POST | `/connections/{id}/sync` | Trigger sync job |

### **Drift Repair Agent** (Port 8003)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/repair/apply_new_catalog` | Update connection catalog |

---

## Usage Examples

### 1. Onboard a Salesforce Connection

```bash
curl -X POST http://localhost:8001/connections/onboard \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "Salesforce",
    "connection_name": "Salesforce Production",
    "credential_id": "salesforce-prod"
  }'
```

**Expected Response:**
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

**What Happens:**
1. Orchestrator calls Auth Broker for Salesforce credentials
2. Gets Salesforce source definition ID from Airbyte
3. Creates source in Airbyte
4. Discovers schema (syncCatalog)
5. Creates connection to destination
6. Stores in Registry with version 1

---

### 2. List All Connections

```bash
curl http://localhost:8001/connections
```

**Response:**
```json
[
  {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "name": "Salesforce Production",
    "source_type": "Salesforce",
    "status": "ACTIVE",
    "airbyte_source_id": "e5f6-7890-abcd-ef12",
    "airbyte_connection_id": "7890-abcd-ef12-3456",
    "created_at": "2025-01-15T10:30:00Z"
  }
]
```

---

### 3. Trigger a Sync

```bash
curl -X POST http://localhost:8001/connections/a1b2c3d4-e5f6-7890-abcd-ef1234567890/sync \
  -H "Content-Type: application/json"
```

**Response:**
```json
{
  "connection_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "job_id": "12345678",
  "status": "triggered",
  "message": "Sync job started successfully"
}
```

---

### 4. Apply Catalog Update (Drift Repair)

```bash
curl -X POST http://localhost:8003/repair/apply_new_catalog \
  -H "Content-Type: application/json" \
  -d '{
    "connection_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "new_sync_catalog": {
      "streams": [
        {
          "stream": {
            "name": "Account",
            "json_schema": {},
            "supported_sync_modes": ["full_refresh", "incremental"]
          },
          "sync_mode": "incremental",
          "destination_sync_mode": "append_dedup"
        }
      ]
    }
  }'
```

**Response:**
```json
{
  "connection_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "previous_version": 1,
  "new_version": 2,
  "status": "success",
  "message": "Catalog updated and versioned successfully"
}
```

**What Happens:**
1. Connection status → `HEALING`
2. Airbyte connection catalog updated via API
3. New `SyncCatalogVersion` (v2) created
4. Connection status → `ACTIVE`

---

## Database Schema

### **connections**
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| name | String | Human-readable name |
| source_type | String | Source connector type |
| airbyte_source_id | UUID | Airbyte source ID |
| airbyte_connection_id | UUID | Airbyte connection ID |
| status | Enum | PENDING, ACTIVE, FAILED, HEALING |
| created_at | DateTime | Creation timestamp |
| updated_at | DateTime | Last update timestamp |

### **sync_catalog_versions**
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| connection_id | UUID | Foreign key to connections |
| sync_catalog | JSONB | Full syncCatalog object |
| version_number | Integer | Incremental version |
| created_at | DateTime | Creation timestamp |

### **job_history**
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| connection_id | UUID | Foreign key to connections |
| airbyte_job_id | String | Airbyte job identifier |
| status | Enum | pending, running, succeeded, failed |
| started_at | DateTime | Job start time |
| completed_at | DateTime | Job completion time |
| error_message | String | Error details if failed |

---

## Testing

### Run All Health Checks
```bash
./test_health.sh
```

### Test Complete Onboarding Flow
```bash
./test_onboarding.sh
```

### Monitor Logs
```bash
docker-compose logs -f orchestrator
docker-compose logs -f auth_broker
docker-compose logs -f drift_repair_agent
```

---

## Development

### Run Tests
```bash
pytest tests/
```

### Check Code Quality
```bash
# Type checking
mypy shared/ services/

# Linting
flake8 shared/ services/

# Formatting
black shared/ services/
```

### Database Migrations
```bash
# Generate migration
alembic revision --autogenerate -m "description"

# Apply migration
alembic upgrade head
```

---

## Troubleshooting

### Connection Failed: "Source definition not found"
**Solution:** Check Airbyte API connectivity and source type name:
```bash
curl -X GET http://localhost:8000/api/public/v1/source_definitions \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Database Connection Error
**Solution:** Verify `SUPABASE_DB_URL` in `.env` and database accessibility:
```bash
psql "$SUPABASE_DB_URL" -c "SELECT 1"
```

### Airbyte API 401 Unauthorized
**Solution:** Refresh credentials:
```bash
abctl local credentials
# Update .env with new client_id and client_secret
```

---

## Next Steps

### Phase 3: Advanced Intelligence
- [ ] Schema Observer: Automated drift detection
- [ ] RAG Engine: AI-powered mapping recommendations
- [ ] Event-driven healing triggers
- [ ] Multi-source schema unification

### Phase 4: Production Hardening
- [ ] HashiCorp Vault integration
- [ ] Kubernetes deployment
- [ ] Observability (Prometheus, Grafana)
- [ ] Rate limiting and circuit breakers

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit a pull request

---

## License

MIT License - See LICENSE file for details

---

## Resources

- **Airbyte API Docs**: https://reference.airbyte.com/
- **abctl Setup**: See [AIRBYTE_SETUP.md](./AIRBYTE_SETUP.md)
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **SQLAlchemy Async**: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
