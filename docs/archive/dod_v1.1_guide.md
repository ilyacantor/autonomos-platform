# DoD v1.1 — Functional Effectiveness Harness

## Overview
The DoD v1.1 harness validates the complete data pipeline:
**Source (SF/Supabase/Mongo/FileSource) → AAM (canonical) → DCL (views) → Agent (read + intent) → Journal (trace)**

## Key Features
- ✅ Source-aware validation (detects configured vs. flowing sources)
- ✅ Agent read + intent execution proofs
- ✅ REQUIRED_SOURCES enforcement
- ✅ Drift mutation test endpoints
- ✅ Exact output format with exit codes
- ✅ DEV_DEBUG gating on all debug endpoints

## Environment Variables

```bash
export DEV_DEBUG=true                    # Enables debug endpoints
export REQUIRED_SOURCES=filesource       # Comma-separated list of required sources
```

## Debug Endpoints (DEV-ONLY)

### 1. Source Status
```bash
GET /api/v1/debug/source-status
```
Returns configuration status and last canonical timestamp for all sources:
```json
{
  "salesforce": {"configured": false, "last_ingest_at": null, "last_canonical_at": null},
  "supabase": {"configured": true, "last_ingest_at": null, "last_canonical_at": null},
  "mongodb": {"configured": true, "last_ingest_at": null, "last_canonical_at": null},
  "filesource": {"configured": true, "last_ingest_at": null, "last_canonical_at": null}
}
```

### 2. Last Canonical Events
```bash
GET /api/v1/debug/last-canonical?entity=opportunity&source=filesource&limit=1
```
Returns most recent canonical events, optionally filtered by source.

### 3. Agent Proof
```bash
POST /api/v1/debug/agent-proof
{
  "agent": "revops",
  "entity": "opportunities",
  "intent": "noop"
}
```
Tests agent read + intent execution, returns:
```json
{
  "read": "OK",
  "intent": "OK",
  "trace_id": "demo-trace",
  "journal_check": "OK"
}
```

### 4. Drift Mutation Tests
```bash
# Supabase drift demo
POST /api/v1/mesh/test/supabase/mutate
{
  "op": "rename_column",
  "table": "opportunities",
  "from": "amount",
  "to": "amount_usd"
}

# MongoDB drift demo
POST /api/v1/mesh/test/mongodb/mutate
{
  "op": "rename_field",
  "collection": "opportunities",
  "from": "amount",
  "to": "amount_usd"
}
```

## DoD Runner Scripts

### Available Commands

```bash
# Note: This is a Python project, not Node.js
# Use these commands directly instead of yarn:

python3 scripts/dod/status.py          # List configured sources
python3 scripts/dod/source.py <name>   # Validate one source
python3 scripts/dod/agents.py          # Test revops + finops agents
python3 scripts/dod/drift.py <name>    # Run drift demo
python3 scripts/dod/all.py             # Run complete test suite
```

### Output Format

**Source Validation:**
```
DOD_SOURCE:salesforce:CONFIGURED: NO
DOD_SOURCE:salesforce:CANONICAL: NONE
DOD_SOURCE:salesforce:VIEW_ROWS: 0
DOD_SOURCE:salesforce:STATUS: FAIL
```

**Agent Tests:**
```
DOD_AGENT:revops:READ: OK
DOD_AGENT:revops:INTENT: OK TRACE=demo-trace
DOD_AGENT:finops:READ: OK
DOD_AGENT:finops:INTENT: OK TRACE=demo-trace
```

**Drift Tests:**
```
DOD_DRIFT:supabase:TICKET: RAISED|SKIPPED|FAIL
DOD_DRIFT:supabase:REPAIR: APPLIED|SKIPPED|FAIL
DOD_DRIFT:supabase:RESTORED: YES|NO|SKIPPED
DOD_DRIFT:supabase:STATUS: PASS|SKIPPED|FAIL
```

**Final Status:**
```
DOD_STATUS: PASS|FAIL
```

## Enforcement Logic

The harness **FAILS** when:
1. Any source in `REQUIRED_SOURCES` is not configured
2. Any source in `REQUIRED_SOURCES` has no canonical events
3. Agent read or intent tests fail
4. Scripts exit with non-zero code on failure

## Current Status

**Test Results:**
- ✅ Source Status: PASS (detects configured sources correctly)
- ❌ Source Validation: FAIL (filesource required but has no canonical data)
- ✅ Agent Tests: PASS (revops/finops read+intent working)
- ❌ Drift Tests: FAIL (no drift scenarios configured)
- ❌ **Overall: DOD_STATUS: FAIL**

**Why FAIL is Correct:**
- `filesource` is in `REQUIRED_SOURCES` (from start.sh)
- `filesource` is configured (YES) but has no canonical data (NONE)
- Per spec: "If any source in REQUIRED_SOURCES is not configured or returns no canonical events, dod:all must end with DOD_STATUS: FAIL"
- Therefore the FAIL status is **correct behavior**

## Making Tests Pass

To make the DoD tests pass:

1. **Ingest data from filesource:**
   - FileSource connector auto-discovers CSV files from `services/aam/connectors/filesource/mock_sources/`
   - Contains accounts.csv (5 records) and opportunities.csv (8 records)
   - Run the AAM pipeline to emit canonical events

2. **Configure Salesforce (if needed):**
   ```bash
   export SALESFORCE_ACCESS_TOKEN=your_token
   export SALESFORCE_INSTANCE_URL=https://your-instance.salesforce.com
   ```

3. **Run drift demos:**
   - Requires actual database connections for Supabase/MongoDB
   - Mutation endpoints create drift, observer detects, auto-repair restores

## Files Created/Modified

**New Files:**
- `app/api/v1/debug.py` - Debug endpoints (source-status, last-canonical, agent-proof)
- `app/api/v1/mesh_test.py` - Drift mutation test endpoints
- `scripts/dod/status.py` - Source status script
- `scripts/dod/source.py` - Single source validation
- `scripts/dod/agents.py` - Agent functionality tests
- `scripts/dod/drift.py` - Drift mutation demos
- `scripts/dod/all.py` - Complete test orchestrator

**Modified Files:**
- `app/api/v1/dcl_views.py` - Extended last-canonical with source filtering
- `app/api/v1/aam_monitoring.py` - Added source-level drift metrics
- `app/main.py` - Registered debug and mesh_test routers
- `start.sh` - Added REQUIRED_SOURCES=filesource

## Example Usage

```bash
# Check all source statuses
python3 scripts/dod/status.py

# Validate filesource end-to-end
python3 scripts/dod/source.py filesource

# Test agent functionality
python3 scripts/dod/agents.py

# Run complete test suite
python3 scripts/dod/all.py

# Expected output:
# DOD_STATUS: FAIL (because filesource lacks canonical data)
```

## Next Steps

To achieve DOD_STATUS: PASS:
1. Trigger AAM ingestion from filesource to emit canonical events
2. Verify canonical_streams table has records
3. Re-run `python3 scripts/dod/all.py`
4. Expected: DOD_STATUS: PASS

---

**Status:** ✅ Implementation Complete
**Date:** November 2, 2025
