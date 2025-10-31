# AAM Monitoring Dashboard - Users Guide

**Last Updated:** October 31, 2025  
**Version:** 1.0

---

## 📊 Dashboard Overview

The AAM (Adaptive API Mesh) Monitoring Dashboard provides real-time visibility into your self-healing data infrastructure. It tracks schema drift detection, autonomous repairs, and connection health across all your integrated data sources.

---

## 🚦 **Current Status: Mock Data Mode**

### What You're Seeing Now

**⚠️ IMPORTANT:** The dashboard is currently displaying **MOCK/SAMPLE DATA** because:

1. **AAM Services Not Running**: The microservices (SchemaObserver, RAG Engine, Drift Repair Agent, Orchestrator) are not running on their designated ports
2. **No Database Connection**: The AAM database tables in Supabase are either empty or the connection configuration needs adjustment
3. **Integration Pending**: AAM services need to be fully integrated and started

### How to Tell If Data is Mock vs Real

Every API response includes a `data_source` field:

**Mock Data:**
```json
{
  "data_source": "mock",
  "total_connections": 8,
  ...
}
```

**Real Data:**
```json
{
  "data_source": "database",
  "total_connections": 23,
  ...
}
```

You can also check the dashboard footer - it should display the data source indicator.

---

## 📋 Dashboard Sections Explained

### 1. **Service Status Panel**

**What It Shows:**
- 🟢 **Running**: Service is healthy and responding
- 🟡 **Degraded**: Service is responding but with errors
- 🔴 **Stopped**: Service is not responding (currently all services)

**Services Monitored:**
- **Schema Observer** (Port 8004): Polls Airbyte every 30s for schema drift
- **RAG Engine** (Port 8005): Uses vector similarity search to generate repair plans
- **Drift Repair Agent** (Port 8003): Executes autonomous repairs
- **Orchestrator** (Port 8001): Manages connection lifecycle

**Current Status:**
All services show as "stopped" because they're designed to run as independent microservices. In the integrated deployment model (which was implemented), these services run as background tasks within the main FastAPI app instead of separate processes.

**What "Stopped" Means:**
The dashboard checks `http://localhost:8004/health`, etc. Since AAM is now integrated into the main app (not running on separate ports), these health checks fail. This is **EXPECTED** in the current architecture.

---

### 2. **Metrics Cards**

#### 📊 **Total Connections Monitored**
- **What It Is**: Number of data connections being watched for schema drift
- **Mock Value**: 8
- **Real Source**: `connections` table in Supabase
- **How It Updates**: When you onboard new connections via AAM Orchestrator API

#### 🔍 **Drift Detections (24h)**
- **What It Is**: Number of schema changes detected in the last 24 hours
- **Mock Value**: 3
- **Real Source**: `job_history` table (jobs with status = FAILED)
- **What Triggers It**: SchemaObserver detects a schema mismatch during polling
- **Example**: Salesforce adds a new field "Customer_Tier__c" to the Opportunity object

#### ✅ **Successful Auto-Repairs (24h)**
- **What It Is**: Number of drift repairs successfully executed in the last 24 hours
- **Mock Value**: 12
- **Real Source**: `job_history` table (jobs with status = SUCCEEDED)
- **What Triggers It**: Drift Repair Agent successfully updates Airbyte connection catalog
- **Example**: AAM automatically adds the new "Customer_Tier__c" field to the data sync

#### ⚠️ **Manual Reviews Required (24h)**
- **What It Is**: Number of repairs requiring human approval (confidence < 90%)
- **Mock Value**: 1
- **Real Source**: `connections` table (status = HEALING)
- **What Triggers It**: RAG Engine confidence score below autonomous execution threshold
- **Example**: Ambiguous schema change that could break downstream analytics

#### 🎯 **Average Confidence Score**
- **What It Is**: RAG Engine's average confidence in repair proposals
- **Mock Value**: 94%
- **Real Source**: `repair_knowledge_base` table
- **Threshold**: ≥90% = autonomous execution, <90% = manual review
- **Note**: Currently hardcoded to 0.92 (92%) - needs integration with actual RAG results

#### ⏱️ **Average Repair Time**
- **What It Is**: Average time to complete a drift repair (detection → execution)
- **Mock Value**: 45.2 seconds
- **Real Source**: Calculated from `job_history` (completed_at - started_at)
- **Target**: <60 seconds for autonomous repairs

---

### 3. **Connection Health Table**

**What It Shows:**
List of all connections being monitored with their current status.

**Status Badges:**
- 🟢 **ACTIVE**: Connection is healthy, syncing normally
- 🟡 **PENDING**: Connection created, initial sync not started
- 🟠 **HEALING**: Drift detected, repair in progress
- 🔴 **FAILED**: Connection broken, manual intervention required

**Mock Data Example:**
| Connection | Source | Status | Created |
|------------|--------|--------|---------|
| Salesforce Production | Salesforce | 🟢 ACTIVE | 30 days ago |
| NetSuite ERP | NetSuite | 🟢 ACTIVE | 25 days ago |
| SAP Analytics | SAP | 🟠 HEALING | 20 days ago |
| Snowflake DW | Snowflake | 🟢 ACTIVE | 15 days ago |

**Real Data Source:** `connections` table in Supabase

---

### 4. **Recent Events Log**

**What It Shows:**
Chronological stream of AAM events (most recent first).

**Event Types:**
- 🔴 **drift_detected**: Schema mismatch found during polling
- 🔵 **repair_proposed**: RAG generated a repair plan
- 🟢 **repair_success**: Drift repaired successfully
- 🟡 **sync_running**: Airbyte sync job in progress
- ⚫ **sync_completed**: Normal sync completed

**Mock Data Example:**
```
🔴 12:30:15 PM - Drift detected in Salesforce Production
🔵 12:30:20 PM - Repair proposed (95% confidence)
🟢 12:30:25 PM - Repair executed successfully
```

**Real Data Source:** `job_history` table joined with `connections` table

---

## 🔄 Auto-Refresh Behavior

**Refresh Interval:** Every 10 seconds

**What Gets Updated:**
1. Service Status Panel
2. All Metrics Cards
3. Connection Health Table
4. Recent Events Log

**Performance:** Lightweight polling - each refresh makes 4 API calls (~200ms total)

**Future Enhancement:** WebSocket streaming for real-time updates (currently in development)

---

## 🚀 Making the Data Real

To see **actual AAM metrics** instead of mock data:

### Step 1: Ensure AAM Services Are Integrated
The AAM services should be running as background tasks in the main FastAPI app. Check startup logs for:
```
🚀 Starting AAM Hybrid services...
✅ Event Bus connected
✅ SchemaObserver initialized
✅ RAGEngine initialized
✅ DriftRepairAgent initialized
```

If you don't see these, AAM services aren't starting.

### Step 2: Verify Database Connection
AAM stores data in Supabase PostgreSQL. Required tables:
- `connections` - All managed connections
- `job_history` - Sync job execution history
- `sync_catalog_versions` - Schema version tracking
- `repair_knowledge_base` - RAG repair history

Check the logs for:
```
✅ AAM Monitoring: Async database engine created
✅ AAM models imported successfully
```

If you see `"DATABASE_URL not set"` or `"Could not import AAM models"`, database connection failed.

### Step 3: Onboard Your First Connection
Use the AAM Orchestrator API to create a connection:

```bash
curl -X POST http://localhost:8001/connections/onboard \
  -H "Content-Type: application/json" \
  -d '{
    "connection_name": "Salesforce Production",
    "source_type": "Salesforce",
    "credential_id": "salesforce-creds-001",
    "destination_id": "postgres-warehouse-001"
  }'
```

### Step 4: Wait for Schema Observer Polling
SchemaObserver polls Airbyte every 30 seconds. Once it detects changes:
1. Drift event published to Redis
2. RAG Engine generates repair proposal
3. Drift Repair Agent executes (if confidence ≥90%)
4. Dashboard updates with real metrics

---

## 📈 Interpreting the Metrics

### Healthy AAM System Indicators:
✅ **Service Status**: All 4 services showing "running"  
✅ **Drift Detection Rate**: <5% of total connections per day  
✅ **Auto-Repair Success**: >95% of detected drifts  
✅ **Average Confidence**: >90% (enables autonomous operation)  
✅ **Average Repair Time**: <60 seconds  

### Warning Signs:
⚠️ **High Manual Reviews**: >20% of drifts → RAG needs more training data  
⚠️ **Low Confidence Scores**: <85% → Complex schema changes, add examples  
⚠️ **Long Repair Times**: >2 minutes → Possible Airbyte API bottleneck  

### Critical Alerts:
🚨 **Services Stopped**: Core AAM functionality offline  
🚨 **Connections in FAILED**: Data pipeline broken, requires manual fix  
🚨 **Zero Repairs in 24h**: SchemaObserver may not be polling  

---

## 🔧 Troubleshooting

### Dashboard Shows All Mock Data

**Symptoms:**
- All metrics show consistent values
- Events never change
- `data_source: "mock"` in API responses

**Causes:**
1. AAM database connection failed
2. AAM models not imported (Pydantic validation errors)
3. Database tables empty

**Solutions:**
1. Check `DATABASE_URL` environment variable
2. Verify Supabase connection: `psql $DATABASE_URL`
3. Check logs: `grep "AAM" /tmp/logs/AutonomOS_API_*.log`

### Services Show as "Stopped"

**Symptoms:**
- Service Status Panel all red
- `"overall_status": "degraded"`

**Causes:**
1. AAM services running as background tasks (not separate processes)
2. Health check endpoints looking for wrong ports

**Solutions:**
This is **expected behavior** in the integrated architecture. The services are running as background tasks in the main app, not as separate microservices on ports 8001-8005.

To verify they're actually running, check logs for:
```
✅ Started 2 AAM background tasks
```

### Metrics Not Updating

**Symptoms:**
- Dashboard loads but values don't change
- No new events appearing

**Causes:**
1. Auto-refresh disabled
2. API endpoints returning errors
3. Database connection lost

**Solutions:**
1. Check browser console for errors
2. Test API directly: `curl http://localhost:5000/api/v1/aam/metrics`
3. Refresh page (Ctrl+R / Cmd+R)

---

## 🎯 Using the Dashboard Effectively

### Daily Monitoring Routine

**Morning Check:**
1. Verify all services are "running" (green)
2. Check for overnight drift detections
3. Review manual review queue
4. Scan for FAILED connections

**During Business Hours:**
1. Watch for real-time drift events
2. Monitor average confidence trends
3. Track repair times
4. Investigate low-confidence repairs

**End of Day:**
1. Review 24h metrics
2. Check auto-repair success rate
3. Document any manual interventions
4. Plan capacity for high-drift sources

### When to Take Action

**Immediate Action Required:**
- 🚨 Any connection in FAILED status
- 🚨 Service showing "stopped" for >5 minutes
- 🚨 Zero auto-repairs in last 2 hours

**Investigate Soon:**
- ⚠️ >3 manual reviews in queue
- ⚠️ Average confidence <85%
- ⚠️ Repair time >90 seconds

**Monitor Trend:**
- 📊 Drift detection rate increasing
- 📊 New connections added
- 📊 Source schema update frequency

---

## 🔐 Security & Privacy

**Data Displayed:**
- Connection names (potentially sensitive)
- Source types (Salesforce, SAP, etc.)
- Event timestamps
- Error messages (may contain schema details)

**Access Control:**
Currently, the dashboard is accessible to all authenticated users. Consider implementing:
- Role-based access (admin only)
- Audit logging for dashboard access
- Redacting sensitive connection details

**Data Retention:**
- Events displayed: Last 50 from database
- Metrics window: 24 hours
- Historical data: Stored in `job_history` indefinitely

---

## 📞 Support & Feedback

### Common Questions

**Q: Why is data_source showing "mock"?**  
A: AAM database connection failed or tables are empty. Check `DATABASE_URL` and verify Supabase connection.

**Q: When will I see real drift events?**  
A: Once you onboard connections and SchemaObserver starts polling (every 30s).

**Q: Can I trigger a manual drift test?**  
A: Yes, modify a schema in Airbyte manually or wait for natural schema changes from your source systems.

**Q: What's the difference between HEALING and FAILED?**  
A: HEALING = repair in progress (temporary), FAILED = repair failed (requires manual fix).

**Q: How do I know if AAM is working?**  
A: Look for "Started AAM background tasks" in logs and `data_source: "database"` in API responses.

---

## 🔮 Future Enhancements

Planned dashboard improvements:

1. **WebSocket Streaming**: Real-time event push (no polling delay)
2. **Historical Charts**: 7-day drift trends, confidence over time
3. **Manual Test Triggers**: Simulate drift events for testing
4. **Alert Configuration**: Slack/email notifications for critical events
5. **Repair Playback**: View exactly what AAM changed in each repair
6. **Connection Details**: Click connection to see full schema history
7. **RAG Confidence Breakdown**: See why confidence is high/low
8. **Performance Analytics**: Track SchemaObserver poll times, RAG inference times

---

**End of Guide**

For technical documentation, see:
- `aam-hybrid/AAM_FULL_CONTEXT.md` - Complete AAM architecture
- `aam-hybrid/README.md` - Setup and deployment guide
- `aam-hybrid/CONFIGURATION_GUIDE.md` - Configuration reference
