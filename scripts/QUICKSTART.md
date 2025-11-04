# Functional Probe - Quick Start Guide

## 🎯 What Is This?

A complete end-to-end test that proves the Salesforce → AAM → DCL pipeline works correctly.

## ⚡ Quick Test (Without Salesforce)

Test the AAM/DCL pipeline using mock CSV data:

```bash
# 1. Enable dev mode (in terminal or .env file)
export DEV_DEBUG=true
export NODE_ENV=development

# 2. Restart the server to pick up the env vars
# (Or just restart the workflow in Replit)

# 3. Replay FileSource CSV files to create canonical events
curl -X POST "http://localhost:5000/api/v1/filesource/replay?entity=opportunity"

# 4. Check the debug endpoint to see the canonical event
curl "http://localhost:5000/api/v1/debug/last-canonical?entity=opportunity&limit=1" | python -m json.tool

# 5. Verify it appears in DCL views
curl "http://localhost:5000/api/v1/dcl/views/opportunities?limit=5" | python -m json.tool
```

**Expected Result:** You should see opportunity data in both the debug endpoint and DCL views.

---

## 🚀 Full Salesforce Test

To test with live Salesforce data:

### Step 1: Get Salesforce Credentials

**Quick Method (Session ID):**
1. Log into Salesforce
2. Open browser console (F12)
3. Run: `console.log($Api.Session_Id)` (Lightning) or `console.log(__sfdcSessionId)` (Classic)
4. Copy the session ID

**Production Method (OAuth 2.0):**
- Create a Connected App in Salesforce Setup
- Follow OAuth 2.0 Web Server Flow
- Get access token

### Step 2: Set Environment Variables

```bash
export SALESFORCE_ACCESS_TOKEN="your_token_here"
export SALESFORCE_INSTANCE_URL="https://yourorg.my.salesforce.com"
export DEV_DEBUG="true"
export BASE_URL="http://localhost:5000"
```

### Step 3: Run the Probe

```bash
python scripts/functional_probe.py
```

### Expected Output

```
================================================================================
FUNCTIONAL PROBE: Salesforce → AAM → DCL
================================================================================
🔍 Trace ID: abc123-def456-ghi789

📡 Step 1: Fetching latest Salesforce Opportunity...
✅ Fetched Opportunity: 006XXXXXXXXXXXXXXX - Acme Corp Deal
   Amount: 125000.00, Stage: Negotiation/Review

🔄 Step 2: Normalizing through AAM (Salesforce → Canonical)...
✅ Normalized to canonical format
   Entity: opportunity
   Opportunity ID: 006XXXXXXXXXXXXXXX
   Account ID: 001XXXXXXXXXXXXXXX

📤 Step 3: Emitting canonical event to AAM streams...
✅ Canonical event emitted

🔨 Step 4: Processing through DCL subscriber (materializing)...
✅ DCL subscriber processed canonical streams

🔍 Step 5: Verifying DCL materialization (exponential backoff)...
✅ Found 1 record(s) in DCL views (attempt 1)

================================================================================
VERIFICATION OUTPUT
================================================================================
AOS_FUNC_CANONICAL_ID: 006XXXXXXXXXXXXXXX
AOS_FUNC_CANONICAL_NAME: Acme Corp Deal
AOS_FUNC_CANONICAL_AMOUNT: 125000.00
AOS_FUNC_TRACE_ID: abc123-def456-ghi789
AOS_FUNC_VIEW_COUNT: 1
AOS_FUNC_STATUS: PASS
================================================================================

📊 Debug Endpoint: http://localhost:5000/api/v1/debug/last-canonical?entity=opportunity&limit=1
```

---

## 📊 Debug Endpoint Usage

**URL:** `GET /api/v1/debug/last-canonical`

**Query Parameters:**
- `entity` (required): `account`, `opportunity`, or `contact`
- `limit` (optional): Number of events (default: 1, max: 100)

**Example:**
```bash
# Get last 3 opportunity events
curl "http://localhost:5000/api/v1/debug/last-canonical?entity=opportunity&limit=3"

# Get last account event
curl "http://localhost:5000/api/v1/debug/last-canonical?entity=account&limit=1"

# Get last contact event
curl "http://localhost:5000/api/v1/debug/last-canonical?entity=contact&limit=1"
```

---

## 🔧 Troubleshooting

### Debug Endpoint Returns 403
**Problem:** `Debug endpoints are only available in development mode`

**Solution:** Set `DEV_DEBUG=true` or `NODE_ENV=development` and restart the server

### No Opportunities Found
**Problem:** Empty array returned

**Solution:** Run FileSource replay first:
```bash
curl -X POST "http://localhost:5000/api/v1/filesource/replay?entity=opportunity"
```

### Salesforce API Error
**Problem:** `Salesforce API error: 401`

**Solution:** 
- Verify `SALESFORCE_ACCESS_TOKEN` is valid
- Session IDs expire - regenerate if needed
- Check `SALESFORCE_INSTANCE_URL` matches your org

---

## 📚 Additional Documentation

- **Full Technical Details:** See `scripts/FUNCTIONAL_PROBE_README.md`
- **AAM Architecture:** See `aam-hybrid/AAM_FULL_CONTEXT.md`
- **Canonical Schemas:** See `services/aam/canonical/schemas.py`

---

## ✅ Guardrails

This implementation respects all specified guardrails:
- ✅ No DCL transforms modified
- ✅ No UI/graph CSS/layout changes
- ✅ New endpoints under `/api/v1` only
- ✅ Debug endpoint feature-flagged for dev-only use
