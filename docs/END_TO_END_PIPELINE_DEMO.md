# End-to-End Pipeline Demo Guide

**AOD → AAM → DCL → Agent** Full Data Flow Demonstration

## Overview

This guide demonstrates how AutonomOS orchestrates data from discovery through agent execution using **real production connectors** instead of mock data.

### The Full Pipeline

```
AOD (Discovery) → AAM (Connection) → DCL (Intelligence) → Agent (Execution)
     ↓                  ↓                  ↓                    ↓
Discover assets    Auto-onboard       Map entities        Execute tasks
  from network      connections      Build graph      using context
```

## Prerequisites

### 1. Enable AAM Production Connectors

By default, the platform uses legacy file sources (mock data). To use real production connectors, you must enable the `USE_AAM_AS_SOURCE` feature flag.

**Quick Enable:**
```bash
POST /api/v1/admin/feature-flags/enable-aam
```

**Response:**
```json
{
  "success": true,
  "flag_name": "USE_AAM_AS_SOURCE",
  "enabled": true,
  "tenant_id": "default",
  "message": "✅ AAM production connectors enabled! Platform now uses real data from Salesforce, MongoDB, FileSource, and Supabase."
}
```

### 2. Check Pipeline Status

Verify all components are ready:
```bash
GET /api/v1/demo/pipeline/status
```

**Expected Response:**
```json
{
  "ready": true,
  "status": {
    "aam_enabled": true,
    "onboarding_service_ready": true,
    "dcl_client_ready": true,
    "agent_executor_ready": true,
    "production_connectors": {
      "salesforce": true,
      "mongodb": true,
      "filesource": true,
      "supabase": true
    }
  },
  "message": "✅ Pipeline ready for demo"
}
```

## Running the End-to-End Demo

### Basic Demo Request

Test the full pipeline with a single source:

```bash
POST /api/v1/demo/pipeline/end-to-end?source_type=salesforce
```

**Supported Source Types:**
- `salesforce` - CRM data (Accounts, Contacts, Opportunities)
- `mongodb` - NoSQL database
- `filesource` - File-based data sources
- `supabase` - PostgreSQL database

### Demo Response Structure

```json
{
  "success": true,
  "message": "✅ Full pipeline complete! Data flowed: AOD → AAM (salesforce) → DCL → Agent",
  "aam_enabled": true,
  "connection_id": "conn_abc123",
  "entities_discovered": 5,
  "agent_execution_id": "exec_abc12345",
  "stages": [
    {
      "stage": "AOD_DISCOVERY",
      "status": "success",
      "message": "✅ AOD discovered salesforce data source",
      "data": {
        "source_type": "salesforce",
        "namespace": "demo-pipeline",
        "risk_level": "low"
      }
    },
    {
      "stage": "AAM_ONBOARDING",
      "status": "success",
      "message": "✅ AAM onboarded salesforce connection: success",
      "data": {
        "connection_id": "conn_abc123",
        "funnel_stage": "active",
        "safe_mode": true
      }
    },
    {
      "stage": "DCL_INTELLIGENCE",
      "status": "success",
      "message": "✅ DCL mapped entities and updated knowledge graph",
      "data": {
        "entities_discovered": 5,
        "confidence_score": 0.92,
        "graph_nodes_added": 3
      }
    },
    {
      "stage": "AGENT_EXECUTION",
      "status": "success",
      "message": "✅ Agent executed workflow using DCL context from salesforce",
      "data": {
        "agent_type": "demo-agent",
        "context_source": "salesforce",
        "execution_id": "exec_abc12345"
      }
    }
  ]
}
```

## Understanding Each Stage

### Stage 1: AOD Discovery

**What Happens:**
- External AOD microservice at `https://autonomos.network` discovers data sources
- Sends `ConnectionIntent` to AAM auto-onboarding endpoint
- Includes metadata: source type, namespace, risk level

**Real-World Flow:**
```
AOD Agent → Scans network → Finds Salesforce instance → 
Sends connection intent → AAM receives it
```

### Stage 2: AAM Auto-Onboarding

**What Happens:**
- Validates source type against 30+ connector allowlist
- Resolves credentials (from Replit Secrets)
- Creates/upserts connector (Airbyte or native)
- Discovers schema (metadata-only for Safe Mode)
- Runs tiny first sync (≤20 items)
- Updates connection status to ACTIVE
- Publishes canonical events to Redis Streams

**Key Features:**
- **Safe Mode**: Read-only/metadata scopes, no destructive operations
- **Idempotent**: Can re-run without side effects
- **90% SLO**: Target for day-one success rate

**Credentials Location:**
```
Replit Secrets:
- SALESFORCE_USERNAME
- SALESFORCE_PASSWORD
- SALESFORCE_SECURITY_TOKEN
- MONGODB_URI
- SUPABASE_URL / SUPABASE_KEY
```

### Stage 3: DCL Intelligence

**What Happens:**
- Consumes canonical events from AAM via Redis Streams
- Runs LLM-powered entity mapping with RAG
- Generates knowledge graph relationships
- Provides unified context to agents
- Stores graph state in Redis

**Intelligence Services:**
- Entity mapping with confidence scoring
- Schema drift detection
- LLM-powered auto-repair (>90% confidence)
- HITL workflows for low-confidence mappings

### Stage 4: Agent Execution

**What Happens:**
- Agents access DCL graph context
- Execute domain-specific tasks (FinOps, RevOps)
- Publish execution events to Flow Monitor
- Return results to users

**Example Agent Tasks:**
- RevOps: Analyze deal pipeline health
- FinOps: Identify cost optimization opportunities
- General: Cross-system data enrichment

## Production AAM Connectors

### 1. Salesforce Connector
**Type:** Native AAM adapter  
**Data:** Accounts, Contacts, Opportunities, Custom Objects  
**Auth:** OAuth / Username+Password+Token  
**Safe Mode:** Read-only, metadata discovery

### 2. MongoDB Connector
**Type:** Native AAM adapter  
**Data:** Collections, documents  
**Auth:** Connection URI with credentials  
**Safe Mode:** Read-only queries

### 3. FileSource Connector
**Type:** Native AAM adapter  
**Data:** CSV, JSON, Parquet files  
**Auth:** File system or cloud storage credentials  
**Safe Mode:** Read-only file access

### 4. Supabase Connector
**Type:** Native AAM adapter  
**Data:** PostgreSQL tables via Supabase  
**Auth:** Project URL + Service Role Key  
**Safe Mode:** Read-only SQL queries

## Admin Endpoints

### Toggle Any Feature Flag

```bash
POST /api/v1/admin/feature-flags/toggle
Content-Type: application/json

{
  "flag_name": "USE_AAM_AS_SOURCE",
  "enabled": true,
  "tenant_id": "default"
}
```

### List All Feature Flags

```bash
GET /api/v1/admin/feature-flags?tenant_id=default
```

**Response:**
```json
{
  "USE_AAM_AS_SOURCE": true,
  "ENABLE_DRIFT_DETECTION": true,
  "ENABLE_AUTO_REPAIR": true,
  "ENABLE_CANONICAL_EVENTS": true
}
```

### Disable AAM (Return to Legacy Mode)

```bash
POST /api/v1/admin/feature-flags/disable-aam
```

## Common Workflows

### Test Each Connector Individually

```bash
# Salesforce
POST /api/v1/demo/pipeline/end-to-end?source_type=salesforce

# MongoDB
POST /api/v1/demo/pipeline/end-to-end?source_type=mongodb

# FileSource
POST /api/v1/demo/pipeline/end-to-end?source_type=filesource

# Supabase
POST /api/v1/demo/pipeline/end-to-end?source_type=supabase
```

### Monitor Real-Time Telemetry

After running the demo, check the Flow Monitor dashboard:

```
Navigate to: AAM (Connect) → Flow Monitor tab
```

You'll see real-time events flowing through the pipeline:
- AAM: Connection events, sync status
- DCL: Entity mapping, graph updates
- Agent: Execution events

### View Production Connection Details

```
Navigate to: AAM (Connect) → Connector Details tab
```

Shows all active production connections with:
- Sync status
- Last sync time
- Health checks
- Error logs (if any)

## Troubleshooting

### Pipeline Status Shows "Not Ready"

**Check:**
1. Is AAM enabled? `GET /api/v1/admin/feature-flags`
2. Are credentials in Replit Secrets?
3. Is Redis connected? Check server logs

**Fix:**
```bash
POST /api/v1/admin/feature-flags/enable-aam
```

### Connection Fails During Auto-Onboarding

**Common Issues:**
- Missing credentials in Replit Secrets
- Invalid credential format
- Network connectivity to external system
- Source system rate limiting

**Debug:**
Check server logs for detailed error messages from onboarding service.

### AAM Enabled But Still Shows Mock Data

**Cause:** Frontend may be caching the old state

**Fix:**
1. Hard refresh browser (Cmd+Shift+R / Ctrl+Shift+R)
2. Restart the workflow
3. Check feature flag in Redis: `GET feature_flag:USE_AAM_AS_SOURCE:default`

## Architecture Notes

### Data Flow

```
External Network (AOD scans)
    ↓
Connection Intent (JSON payload)
    ↓
AAM Auto-Onboarding (POST /connections/onboard)
    ↓
Connector Provisioning (Airbyte or native)
    ↓
Redis Streams (Canonical events: aam:flow)
    ↓
DCL Intelligence (Entity mapping, graph gen)
    ↓
Redis Graph State (Knowledge graph)
    ↓
Agent Executor (Context-aware execution)
    ↓
Redis Streams (Agent events: agent:flow)
    ↓
Flow Monitor Dashboard (Real-time visualization)
```

### Safe Mode Guarantees

1. **Read-Only**: No write/update/delete operations
2. **Metadata-First**: Schema discovery before data
3. **Tiny First Sync**: ≤20 items max
4. **Idempotent**: Re-run safe, no side effects
5. **HITL**: Human approval for high-risk operations

### Multi-Tenancy

All connections are scoped by `tenant_id` (default: "default")
- Feature flags: `feature_flag:FLAG_NAME:tenant_id`
- Connections: Namespace field for logical grouping
- Graph state: Per-tenant Redis keys

## Next Steps

1. **Enable AAM**: Switch from mock to production data
2. **Run Demo**: Test all four connectors
3. **Monitor Telemetry**: Watch Flow Monitor for real-time events
4. **View Connections**: Check Connector Details for health status
5. **Integrate Real AOD**: Connect autonomos.network for live discovery

## API Documentation

Full Swagger/OpenAPI docs available at:
```
http://your-domain/docs
```

Filter by tags:
- "Admin - Feature Flags"
- "Demo Pipeline"
- "AAM Auto-Onboarding"
- "Flow Monitoring"
