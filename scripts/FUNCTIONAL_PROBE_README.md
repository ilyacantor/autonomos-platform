# Functional Probe: Salesforce → AAM → DCL

**Last Updated:** November 19, 2025

## Purpose
This functional probe validates the complete end-to-end flow from live Salesforce data through AAM normalization into DCL materialized views.

## Components

### 1. Debug Endpoint (Dev-Only)
**URL:** `GET /api/v1/debug/last-canonical?entity=opportunity&limit=1`

**Purpose:** Retrieve the most recent canonical events for debugging

**Query Parameters:**
- `entity` (required): Entity type (`account`, `opportunity`, `contact`)
- `limit` (optional): Number of events to return (default: 1, max: 100)

**Response Example:**
```json
[
  {
    "opportunity_id": "006XXXXXXXXXXXXXXX",
    "account_id": "001XXXXXXXXXXXXXXX",
    "name": "Acme Corp - Enterprise License",
    "stage": "Negotiation/Review",
    "amount": 125000.00,
    "currency": "USD",
    "close_date": "2025-03-15",
    "owner_id": "005XXXXXXXXXXXXXXX",
    "probability": 75,
    "emitted_at": "2025-01-31T20:45:12.345Z",
    "trace_id": "abc123-def456-ghi789",
    "source_system": "salesforce"
  }
]
```

**Access:** Only enabled when `DEV_DEBUG=true` or `NODE_ENV=development`

---

### 2. Salesforce Connector
**Location:** `services/aam/connectors/salesforce/connector.py`

**Features:**
- Fetches latest Salesforce Opportunity via REST API
- Normalizes Salesforce data to canonical format using mapping registry
- Enforces strict Pydantic validation
- Emits canonical events to database

**Required Environment Variables:**
- `SALESFORCE_ACCESS_TOKEN`: OAuth 2.0 access token
- `SALESFORCE_INSTANCE_URL`: Your Salesforce instance (e.g., `https://yourorg.my.salesforce.com`)

---

### 3. Functional Probe Script
**Location:** `scripts/functional_probe.py`

**Flow:**
1. Fetch latest Salesforce Opportunity (via REST API)
2. Normalize through AAM (Salesforce → Canonical)
3. Emit canonical event to AAM streams
4. Process through DCL subscriber (materialize into views)
5. Verify materialization with exponential backoff (max 10s)
6. Print verification output

**Verification Output Format:**
```
AOS_FUNC_CANONICAL_ID: 006XXXXXXXXXXXXXXX
AOS_FUNC_CANONICAL_NAME: Acme Corp - Enterprise License
AOS_FUNC_CANONICAL_AMOUNT: 125000.00
AOS_FUNC_TRACE_ID: abc123-def456-ghi789
AOS_FUNC_VIEW_COUNT: 1
AOS_FUNC_STATUS: PASS
```

---

## Setup Instructions

### Step 1: Configure Salesforce Credentials

You need to obtain a Salesforce access token and instance URL. There are two methods:

#### Method A: OAuth 2.0 Web Server Flow (Recommended)
1. Create a Connected App in Salesforce Setup
2. Obtain authorization code via OAuth flow
3. Exchange for access token

#### Method B: Session ID (Quick Test)
1. Log into Salesforce
2. Open Developer Console (F12)
3. Run: `console.log($Api.Session_Id)` (in Lightning Experience)
4. Copy the session ID (this is your access token)

Set environment variables:
```bash
export SALESFORCE_ACCESS_TOKEN="your_access_token_here"
export SALESFORCE_INSTANCE_URL="https://yourorg.my.salesforce.com"
export DEV_DEBUG="true"
export BASE_URL="http://localhost:5000"
```

### Step 2: Run the Functional Probe

```bash
python scripts/functional_probe.py
```

### Step 3: Verify Results

The script will output:
- Each step of the process with ✅ or ❌ status
- Verification output with exact fields specified in the probe spec
- Debug endpoint URL for manual inspection

---

## Testing Without Salesforce

If you don't have Salesforce credentials, you can test the AAM → DCL flow using the FileSource connector:

```bash
# 1. Replay CSV files to emit canonical events
curl -X POST "http://localhost:5000/api/v1/filesource/replay?entity=opportunity&system=salesforce"

# 2. Check the debug endpoint
curl "http://localhost:5000/api/v1/debug/last-canonical?entity=opportunity&limit=1"

# 3. Verify DCL views
curl "http://localhost:5000/api/v1/dcl/views/opportunities?limit=10"
```

---

## Troubleshooting

### No Records in DCL Views
- Check that the canonical event was emitted: `GET /api/v1/debug/last-canonical?entity=opportunity`
- Manually trigger DCL subscriber processing (automatic on next API call to DCL views)
- Check server logs for errors

### Salesforce API Errors
- Verify `SALESFORCE_ACCESS_TOKEN` is valid (tokens expire)
- Verify `SALESFORCE_INSTANCE_URL` matches your org
- Check API version (currently using v59.0)

### Debug Endpoint Returns 403
- Set `DEV_DEBUG=true` or `NODE_ENV=development`
- Restart the server after setting environment variables

---

## Architecture

```
┌─────────────────┐
│   Salesforce    │  (Live data via REST API)
│   Opportunity   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ AAM Salesforce  │  (Normalize to canonical format)
│   Connector     │  (Apply mapping registry)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Canonical Event │  (Strict Pydantic validation)
│   (opportunity) │  (Union[Account, Opportunity, Contact])
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ AAM Streams DB  │  (canonical_streams table)
│  (canonical)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ DCL Subscriber  │  (Process canonical events)
│  (Materialize)  │  (Upsert into materialized tables)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  DCL Views API  │  (GET /api/v1/dcl/views/opportunities)
│ (Materialized)  │  (Query materialized_opportunities)
└─────────────────┘
```

---

## Guardrails Respected

✅ **No DCL transforms modified**  
✅ **No UI/graph CSS/layout touched**  
✅ **New endpoints under /api/v1 only**  
✅ **Debug endpoint dev-only (feature-flagged)**

---

## Next Steps

- [ ] Extend to Accounts and Contacts
- [ ] Add drift detection integration
- [ ] Create automated test suite
- [ ] Add Salesforce OAuth flow helper
