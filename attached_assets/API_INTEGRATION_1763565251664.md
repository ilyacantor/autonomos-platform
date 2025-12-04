# AOS Discover v2 - API Integration Guide

## Overview
AOS Discover v2 is now deployable as a **microservice API** for integration with the Main AOS Demo (AOA). This guide provides everything you need to integrate the two systems.

## 🔗 Primary Integration Endpoint

### POST `/api/discover`

**Purpose:** NLP-based asset discovery endpoint that accepts natural language queries and returns filtered asset data.

**Performance:** P50 220ms, P95 230ms (meets production SLO)

**Request Format:**
```json
{
  "query": "find all prod assets"
}
```

**Response Format:**
```json
{
  "status": "success",
  "query": "find all prod assets",
  "filters_detected": {
    "env": "prod",
    "vendor": null,
    "kind": null,
    "state": null,
    "shadow_it": null
  },
  "assets": [
    {
      "asset_id": "asset-001",
      "uri": "gcp-sql-us-west1-prod-db",
      "kind": "db",
      "vendor": "GCP",
      "env": "prod",
      "state": "READY_FOR_CONNECT",
      "priority": 85,
      "confidence": 0.95,
      "anomaly_score": 0.12,
      "shadow_it_suspected": false
    }
  ],
  "total_count": 213,
  "total_assets_in_system": 382,
  "timestamp": "2025-11-07T22:04:49.657194"
}
```

## 📝 Supported Query Patterns

The NLP parser understands these natural language patterns:

### Environment Filters
- **Production:** "find all prod assets", "show production databases"
- **Staging:** "list staging services", "show stage environments"  
- **Development:** "get dev assets", "show development hosts"

### Vendor Filters
- **AWS:** "show AWS databases", "find Amazon services"
- **GCP:** "list GCP assets", "show Google Cloud services"
- **Azure:** "find Microsoft Azure hosts"
- **Salesforce:** "show Salesforce apps", "list SFDC assets"
- **Others:** Okta, MongoDB, Datadog

### Asset Type Filters
- **Services:** "find all services", "show microservices"
- **Databases:** "list databases", "show all db"
- **SaaS:** "find SaaS apps"
- **Hosts:** "show servers", "list hosts"
- **APIs:** "find API endpoints"

### State Filters
- **Ready:** "show ready assets", "list catalogued assets"
- **Connected:** "find connected assets"
- **Parked:** "show parked assets" (needs review)
- **Unknown:** "list unknown assets"
- **Processing:** "show processing assets"

### Security Filters
- **Shadow IT:** "list shadow IT risks", "show unauthorized assets", "find rogue services"

### Combined Queries
- "show AWS databases in production"
- "find shadow IT services"
- "list all ready GCP assets"
- "get parked Salesforce apps"

## 🔄 End-to-End Data Flow

```
┌─────────────────────────┐
│  Main AOS Demo (AOA)    │
│  - NLP Interface        │
└───────────┬─────────────┘
            │
            │ 1. User Query: "find all prod AWS services"
            │
            ▼
┌─────────────────────────┐
│  fetch/axios API Call   │
│  POST /api/discover     │
│  Body: {"query": "..."}│
└───────────┬─────────────┘
            │
            │ 2. Network Request
            │
            ▼
┌─────────────────────────┐
│  AOS Discover Service   │
│  (This microservice)    │
│  - Parse NLP query      │
│  - Filter assets        │
│  - Return JSON          │
└───────────┬─────────────┘
            │
            │ 3. JSON Response
            │
            ▼
┌─────────────────────────┐
│  Main AOS Demo          │
│  - Log received data    │
│  - Pass to Agents &     │
│    Humans components    │
└─────────────────────────┘
```

## 🚀 Deployment Instructions

### Step 1: Deploy AOS Discover
1. Click the **"Deploy"** button in this Replit project
2. Configure deployment settings:
   - **Deployment Type:** Autoscale (stateless API service)
   - **Build:** (leave empty, no build step needed)
   - **Run:** Already configured in `.replit` file
3. Click **"Deploy"** and wait for deployment to complete
4. Copy the **deployment URL** (e.g., `https://aos-discover-v2-yourname.replit.app`)

### Step 2: Test the Deployment
```bash
# Replace YOUR_DEPLOYMENT_URL with your actual URL
curl -X POST https://YOUR_DEPLOYMENT_URL/api/discover \
  -H "Content-Type: application/json" \
  -d '{"query": "find all prod assets"}'
```

### Step 3: Integrate with Main AOS Demo

**In the Main AOS Demo codebase:**

```javascript
// Example integration code
const AOS_DISCOVER_URL = "https://aos-discover-v2-yourname.replit.app";

async function queryAssets(nlpQuery) {
  try {
    const response = await fetch(`${AOS_DISCOVER_URL}/api/discover`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ query: nlpQuery })
    });
    
    const data = await response.json();
    
    // Log for debugging
    console.log('AOS Discover Response:', data);
    console.log(`Found ${data.total_count} assets matching: "${data.query}"`);
    
    // Pass to Agents & Humans components
    return data.assets;
    
  } catch (error) {
    console.error('Failed to query AOS Discover:', error);
    throw error;
  }
}

// Usage example
const prodAssets = await queryAssets("find all prod assets");
const shadowIT = await queryAssets("list shadow IT risks");
const awsDatabases = await queryAssets("show AWS databases");
```

## 📊 Additional API Endpoints

### Health Check
**GET** `/healthz`
```json
{"status": "ok"}
```

### System Status
**GET** `/status`
```json
{
  "status": "operational",
  "api_uptime_seconds": 1234.5,
  "pipeline_ready": {
    "twins_generated": true,
    "features_ready": true,
    "models_trained": true
  }
}
```

### Dashboard Stats
**GET** `/dashboard/pipeline`
```json
{
  "UNKNOWN": 0,
  "PROCESSING": 2,
  "PARKED": 5,
  "READY_FOR_CONNECT": 320,
  "CONNECTED": 2
}
```

**GET** `/dashboard/inventory`
```json
{
  "by_kind": {"service": 120, "db": 85, "saas": 70, "host": 42},
  "by_environment": {"prod": 180, "staging": 95, "dev": 47},
  "by_vendor": {"AWS": 105, "GCP": 78, "Salesforce": 45},
  "total_catalogued": 322
}
```

**GET** `/dashboard/hitl-queues`
Returns lists of assets requiring human review:
- `high_risk_shadow_it`: Security threats
- `shadow_it_risks`: Unauthorized assets
- `data_conflicts`: ML/Rules disagreements

## 🔧 Configuration & Customization

### Enable Vendor Mode (Advanced Controls)
Set environment variable: `VENDOR_MODE=true`

This exposes additional training controls and configuration endpoints for ML model tuning.

### Run Discovery Manually
**POST** `/discover/run`
```json
{
  "mode": "hybrid",
  "use_seeds": true,
  "use_simulated": false
}
```

Modes: `rules`, `ml`, `hybrid`

## 📋 Asset Schema

Each asset in the response includes:

```typescript
interface Asset {
  asset_id: string;           // Unique identifier
  fingerprint: string;        // MD5 hash for deduplication
  uri: string;                // Resource URI
  kind: string;               // service | db | saas | host | api
  vendor: string;             // AWS, GCP, Azure, etc.
  env: string;                // prod | staging | dev
  state: string;              // UNKNOWN | PROCESSING | PARKED | READY_FOR_CONNECT | CONNECTED
  priority: number;           // 0-100, rules-based scoring
  confidence: number;         // 0-1, ML confidence
  anomaly_score: number;      // 0-1, IsolationForest score
  shadow_it_suspected: boolean;
  exceptions?: string[];      // Actionable exception messages
  pred_kind?: string;         // ML prediction
  pred_vendor?: string;       // ML prediction
  pred_env?: string;          // ML prediction
  prob_kind?: number;         // ML probability
  prob_vendor?: number;       // ML probability
  prob_env?: number;          // ML probability
}
```

## 🛠️ Troubleshooting

### No Data Available
**Error:** `"status": "no_data"`

**Solution:** Run discovery first:
```bash
curl -X POST https://YOUR_DEPLOYMENT_URL/discover/run \
  -H "Content-Type: application/json" \
  -d '{"mode": "hybrid", "use_seeds": true}'
```

### CORS Issues
If the Main AOS Demo is hosted on a different domain, you may need to enable CORS.

**Add to main.py:**
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or specify your AOA domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## ⚡ Performance Characteristics

### Production Performance (Phase 3D - November 2025)

The API has been systematically optimized for production deployment:

**Overall System:**
- **Reliability:** 0% failure rate (100% uptime under load)
- **Typical Response:** P50 190ms (78% improvement from baseline)
- **Tail Latency:** P95 3,900ms (47% improvement from baseline)
- **Throughput:** 22.89 requests/sec

**Primary Integration Endpoint (`POST /api/discover`):**
- **P50 Latency:** 220ms ✅
- **P95 Latency:** 230ms ✅
- **Status:** Meets production SLO (<300ms target)

**Dashboard Endpoints:**
- `GET /dashboard/hitl-queues`: P50 79ms, P95 280ms ✅
- `GET /dashboard/pipeline`: P50 130ms, P95 2,200ms ✅
- `GET /dashboard/inventory`: P50 1,200ms, P95 4,400ms

**HITL Triage Actions:**
- `POST /dashboard/hitl/{asset_id}/approve`: P50 1,700ms, P95 5,100ms
- `POST /dashboard/hitl/{asset_id}/review`: P50 1,800ms, P95 4,800ms

### Production Capacity

**Concurrent Users:**
- **Optimal:** <30 concurrent users
- **Degraded:** 30-50 concurrent users (7-60x slowdown due to database contention)
- **Recommendation:** Monitor concurrent user count, plan database scaling if approaching 30 users

**Background Services:**
- Dashboard stats refresh: 30-second interval (stats may be up to 30s stale)
- HITL audit queue: Batched writes (0.5s delay or 10-entry batches)
- Discovery cache: 5-minute TTL

### Performance Testing

To validate performance in your environment:

```bash
# Quick smoke test
cd tests/performance
locust -f locustfile.py --users 10 --spawn-rate 2 --run-time 30s --headless --host http://YOUR_API_URL

# Standard load test
locust -f locustfile.py --users 50 --spawn-rate 5 --run-time 5m --headless --host http://YOUR_API_URL
```

See `docs/performance_optimization_summary.md` for complete performance details.

## 📞 Support

For questions or issues with this integration, contact the AOS Discover development team or file an issue in the project repository.

---

**Last Updated:** November 15, 2025  
**Version:** 2.0.0  
**Status:** Production Ready ✅
