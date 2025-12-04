# Quick Start: End-to-End Pipeline Demo

**Switch from Mock Data to Real AAM Production Connectors in 3 Steps**

## TL;DR

```bash
# 1. Enable AAM Production Connectors
curl -X POST "http://your-domain/api/v1/admin/feature-flags/enable-aam"

# 2. Verify Pipeline Ready
curl "http://your-domain/api/v1/demo/pipeline/status"

# 3. Run Full AOD → AAM → DCL → Agent Demo
curl -X POST "http://your-domain/api/v1/demo/pipeline/end-to-end?source_type=salesforce"
```

## What This Does

### Before (Mock Data)
- Platform uses legacy file sources
- Data is static/demo files
- No real external system connections

### After (Production AAM)
- Platform uses 4 real production connectors:
  - **Salesforce** - CRM data
  - **MongoDB** - NoSQL database
  - **FileSource** - File-based data
  - **Supabase** - PostgreSQL database
- Data flows: AOD discovers → AAM connects → DCL maps → Agent executes
- Real-time telemetry in Flow Monitor

## Visual Confirmation

### 1. Check Platform Guide
Navigate to **Platform Guide** and look for:

> **What Makes Us Different:** We create autonomous actions, not just insights. We abstract the complexity of disparate data stacks so you don't have to worry about integration headaches. AutonomOS is an end-to-end platform that autonomously connects, understands, and acts on your data...

### 2. Monitor Flow Events
Navigate to **AAM (Connect) → Flow Monitor** tab to see:
- Real-time connection events
- Entity mapping progress
- Agent execution telemetry

### 3. View Active Connections
Navigate to **AAM (Connect) → Connector Details** tab to see:
- Production connector status
- Sync history
- Health metrics

## API Endpoints

### Admin Feature Flags

**Enable AAM Production Connectors**
```http
POST /api/v1/admin/feature-flags/enable-aam
```

**Disable AAM (Return to Legacy)**
```http
POST /api/v1/admin/feature-flags/disable-aam
```

**List All Feature Flags**
```http
GET /api/v1/admin/feature-flags?tenant_id=default
```

**Toggle Any Flag**
```http
POST /api/v1/admin/feature-flags/toggle
Content-Type: application/json

{
  "flag_name": "USE_AAM_AS_SOURCE",
  "enabled": true,
  "tenant_id": "default"
}
```

### Demo Pipeline

**Check Status**
```http
GET /api/v1/demo/pipeline/status
```

**Run Full Pipeline Test**
```http
POST /api/v1/demo/pipeline/end-to-end?source_type=salesforce
POST /api/v1/demo/pipeline/end-to-end?source_type=mongodb
POST /api/v1/demo/pipeline/end-to-end?source_type=filesource
POST /api/v1/demo/pipeline/end-to-end?source_type=supabase
```

## Full Documentation

See [`docs/END_TO_END_PIPELINE_DEMO.md`](docs/END_TO_END_PIPELINE_DEMO.md) for complete details.

## Swagger Documentation

Interactive API docs with "Try it out" functionality:
```
http://your-domain/docs
```

Filter by tags:
- **Admin - Feature Flags** - Toggle production connectors
- **Demo Pipeline** - Test end-to-end flow
- **AAM Auto-Onboarding** - Auto-onboard from AOD
- **Flow Monitoring** - Real-time telemetry

## Need Help?

1. Check pipeline status: `GET /api/v1/demo/pipeline/status`
2. Check feature flags: `GET /api/v1/admin/feature-flags`
3. View server logs for detailed error messages
4. Ensure Replit Secrets contain production credentials
