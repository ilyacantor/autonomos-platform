# AutonomOS Platform - API Reference

**Version:** 1.0  
**Last Updated:** November 18, 2025  
**Base URL:** `https://your-domain.repl.co` or `http://localhost:5000`

---

## Table of Contents

1. [Authentication](#authentication)
2. [DCL Endpoints](#dcl-endpoints)
3. [AAM Endpoints](#aam-endpoints)
4. [NLP Endpoints](#nlp-endpoints)
5. [WebSocket Connections](#websocket-connections)
6. [Error Codes](#error-codes)
7. [Rate Limits](#rate-limits)
8. [Pagination](#pagination)

---

## Authentication

⚠️ **CURRENT STATUS**: Demo Mode (Development)

The platform currently runs with **`DCL_AUTH_ENABLED=false`** in `start.sh`, enabling development without authentication barriers:

### Demo Mode Behavior

When `DCL_AUTH_ENABLED=false`:
- **All requests use randomly-generated MockUser** - No persistent identity
- **No Authorization headers required** - Authentication middleware bypassed
- **Registration/login endpoints functional** - Create real users but tokens not validated
- **Ideal for demos and rapid development** - Production auth planned for v2.0

**MockUser Pattern** (applied to all requests):
- **Structure**: Stable fields (`email`, `id`, `tenant_id`)
- **Values**: Randomized `id` and `tenant_id` generated per request
- **Email**: Constant `dev@autonomos.dev`
- **Persistence**: None - IDs change on every request

Example MockUser (varies per request):
```json
{
  "email": "dev@autonomos.dev",
  "id": "f8ab4417-3c5d-4b29-8e0f-1a2b3c4d5e6f",
  "tenant_id": "65c72aa8-9f12-4321-abcd-ef1234567890"
}
```

⚠️ **Note**: MockUser IDs are randomly generated on each request and are NOT persistent across requests.

### POST `/api/v1/auth/register`

⚠️ **Status**: Implemented but bypassed in demo mode

This endpoint creates real users/tenants in the database, but is not required when `DCL_AUTH_ENABLED=false`.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "secure_password_123",
  "name": "Acme Corporation"
}
```

**Response (201 Created):**
```json
{
  "user": {
    "email": "runtime_test@example.com",
    "id": "ddccc436-7bec-4cb3-b085-9c860b480d51",
    "tenant_id": "9497f49c-5e3b-496a-a10f-d7a5bbed1e21",
    "created_at": "2025-11-18T16:46:53.088453Z"
  },
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiZGRjY2M0MzYtN2JlYy00Y2IzLWIwODUtOWM4NjBiNDgwZDUxIiwidGVuYW50X2lkIjoiOTQ5N2Y0OWMtNWUzYi00OTZhLWExMGYtZDdhNWJiZWQxZTIxIiwiZXhwIjoxNzYzNTEzMjEzfQ.iSIcXtdWk8UMjsicv3KcEqeLsWTw04ifYEnac0E0qQ4",
  "token_type": "bearer"
}
```

**Error Responses:**

**400 Bad Request** - Email already exists:
```json
{
  "detail": "Email already registered"
}
```

**400 Bad Request** - Organization name conflict:
```json
{
  "detail": "Organization name already exists. Please choose a different name."
}
```

**400 Bad Request** - User creation failed:
```json
{
  "detail": "Unable to create user. Please try again."
}
```

**cURL Example:**
```bash
curl -X POST https://your-domain.repl.co/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "secure_password_123",
    "name": "Acme Corporation"
  }'
```

**Python Example:**
```python
import requests

response = requests.post(
    "https://your-domain.repl.co/api/v1/auth/register",
    json={
        "email": "user@example.com",
        "password": "secure_password_123",
        "name": "Acme Corporation"
    }
)

data = response.json()
access_token = data["access_token"]
```

**JavaScript Example:**
```javascript
const response = await fetch('https://your-domain.repl.co/api/v1/auth/register', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'secure_password_123',
    name: 'Acme Corporation'
  })
});

const data = await response.json();
const accessToken = data.access_token;
```

---

### POST `/api/v1/auth/login`

⚠️ **Status**: Implemented but bypassed in demo mode

This endpoint authenticates users and returns real JWT tokens, but they are not validated when `DCL_AUTH_ENABLED=false`.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "secure_password_123"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiZGRjY2M0MzYtN2JlYy00Y2IzLWIwODUtOWM4NjBiNDgwZDUxIiwidGVuYW50X2lkIjoiOTQ5N2Y0OWMtNWUzYi00OTZhLWExMGYtZDdhNWJiZWQxZTIxIiwiZXhwIjoxNzYzNTEzMjE0fQ.YiPlHp9RdsrvXHomG8qAu7RPg7oAKcnd_aPR0-qR5SI",
  "token_type": "bearer"
}
```

**Error Response:**

**401 Unauthorized** - Invalid credentials:
```json
{
  "detail": "Incorrect email or password"
}
```

**HTTP Headers (not in JSON body):**
```
WWW-Authenticate: Bearer
```

**Note**: In demo mode, you can call any endpoint without this token - all requests use MockUser with randomized IDs per request.

---

### GET `/api/v1/auth/me`

⚠️ **Status**: Returns MockUser with randomized IDs in demo mode

In demo mode (`DCL_AUTH_ENABLED=false`), this endpoint ignores Authorization headers and returns a MockUser with randomized `id` and `tenant_id` per request.

**Current Behavior (Demo Mode):**
```bash
# No Authorization header needed
curl -X GET https://your-domain.repl.co/api/v1/auth/me
```

**Response (200 OK):**
```json
{
  "email": "dev@autonomos.dev",
  "id": "8ce8ea61-339d-42b7-afbe-e0938db6e381",
  "tenant_id": "f8ab4417-86a1-4dd2-a049-ea423063850e",
  "created_at": "2025-11-18T16:47:27.648847"
}
```

**Note**: In demo mode, returns a MockUser object with stable structure but randomized `id` and `tenant_id` values on each request (regardless of Authorization header). Only the `email` field remains constant as `dev@autonomos.dev`.

---

## DCL Endpoints

### GET `/api/v1/dcl/views/accounts`

Retrieve unified account view from DCL materialized tables.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "account_id": "ACC-001",
      "name": "Acme Corporation",
      "type": null,
      "industry": "Technology",
      "owner_id": null,
      "status": "active",
      "external_ids": {},
      "extras": {
        "annual_revenue": 1000000
      },
      "source_system": "salesforce",
      "source_connection_id": "conn-123",
      "created_at": "2025-11-15T08:00:00Z",
      "updated_at": "2025-11-18T10:00:00Z",
      "synced_at": "2025-11-18T10:00:00Z"
    }
  ],
  "meta": {
    "total": 150,
    "limit": 100,
    "offset": 0,
    "count": 1
  }
}
```

**cURL Example:**
```bash
curl -X GET https://your-domain.repl.co/api/v1/dcl/views/accounts \
  -H "Authorization: Bearer <token>"
```

**Python Example:**
```python
headers = {"Authorization": f"Bearer {access_token}"}
response = requests.get(
    "https://your-domain.repl.co/api/v1/dcl/views/accounts",
    headers=headers
)
data = response.json()
accounts = data["data"]  # Note: returns {success, data, meta} structure
total_accounts = data["meta"]["total"]
```

---

### GET `/api/v1/dcl/views/opportunities`

Retrieve unified opportunity view from DCL.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `limit` (optional): Maximum records to return (default: 100, max: 1000)
- `offset` (optional): Number of records to skip (default: 0)

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "opportunity_id": "OPP-001",
      "account_id": "ACC-001",
      "name": "Q4 Enterprise Deal",
      "stage": "Proposal",
      "amount": 50000.0,
      "currency": "USD",
      "close_date": "2025-12-31",
      "owner_id": null,
      "probability": 0.7,
      "extras": {},
      "source_system": "salesforce",
      "source_connection_id": "conn-123",
      "created_at": "2025-11-15T08:00:00Z",
      "updated_at": "2025-11-18T10:00:00Z",
      "synced_at": "2025-11-18T10:00:00Z"
    }
  ],
  "meta": {
    "total": 245,
    "limit": 100,
    "offset": 0,
    "count": 1
  }
}
```

---

### POST `/api/v1/dcl/unify/run`

Run DCL contact unification process using exact email matching.

**Note:** This endpoint is hardcoded to unify contact entities by matching email addresses. No request body is required.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body:** None (empty POST)

**Response (200 OK):**
```json
{
  "status": "ok",
  "unified_contacts": 42,
  "links": 87
}
```

**cURL Example:**
```bash
curl -X POST https://your-domain.repl.co/api/v1/dcl/unify/run \
  -H "Authorization: Bearer <token>"
```

---

## AAM Endpoints

⚠️ **IMPORTANT**: AAM endpoints require AAM services to be running (`AAM_MODELS_AVAILABLE=True`). If AAM models are not available, endpoints will return 503 errors.

### GET `/api/v1/aam/connectors`

List all AAM connectors with status, drift detection, and Airbyte sync activity.

**Status**: ✅ **Fully Implemented**

**Headers:**
```
Authorization: Bearer <access_token>  # Optional in demo mode
```

**Response (200 OK):**
```json
{
  "connectors": [
    {
      "id": "10ca3a88-5105-4e24-b984-6e350a5fa443",
      "name": "FilesSource Demo",
      "source_type": "filesource",
      "status": "ACTIVE",
      "mapping_count": 0,
      "last_event_type": null,
      "last_event_at": null,
      "has_drift": false,
      "last_sync_status": null,
      "last_sync_records": null,
      "last_sync_bytes": null,
      "last_sync_at": null
    },
    {
      "id": "4d559c3f-088f-432a-bb01-794837b985f7",
      "name": "MongoDB Production",
      "source_type": "mongodb",
      "status": "ACTIVE",
      "mapping_count": 0,
      "last_event_type": null,
      "last_event_at": null,
      "has_drift": false,
      "last_sync_status": null,
      "last_sync_records": null,
      "last_sync_bytes": null,
      "last_sync_at": null
    },
    {
      "id": "e961fb3b-fc8f-408e-a83d-63080e2181e5",
      "name": "Salesforce Production",
      "source_type": "salesforce",
      "status": "ACTIVE",
      "mapping_count": 0,
      "last_event_type": null,
      "last_event_at": null,
      "has_drift": false,
      "last_sync_status": "succeeded",
      "last_sync_records": 38,
      "last_sync_bytes": 36376,
      "last_sync_at": "2025-11-12T16:02:06Z"
    }
  ],
  "total": 3
}
```

**Field Descriptions:**
- `id`: Unique connector identifier (UUID as string)
- `name`: Human-readable connector name
- `source_type`: Data source type (e.g., filesource, salesforce, supabase, mongodb)
- `status`: Connection status (ACTIVE, PENDING, FAILED, etc.)
- `last_discovery_at`: Timestamp of last schema discovery (from `connection.updated_at`)
- `mapping_count`: Number of field mappings registered for this connector
- `last_event_type`: Type of most recent drift event (e.g., DRIFT_DETECTED), `null` if no drift
- `last_event_at`: Timestamp of most recent drift event, `null` if no drift
- `has_drift`: Boolean indicating whether drift has been detected
- `last_sync_status`: Status of most recent Airbyte sync job (succeeded, failed, running, etc.), `null` if no sync data
- `last_sync_records`: Number of records synced in last Airbyte job, `null` if unavailable
- `last_sync_bytes`: Bytes transferred in last Airbyte sync, `null` if unavailable
- `last_sync_at`: Timestamp of last Airbyte sync job, `null` if unavailable

**Error Responses:**

**503 Service Unavailable** - AAM models not configured:
```json
{
  "detail": "AAM models not configured"
}
```

**500 Internal Server Error** - Database or query error:
```json
{
  "detail": "Failed to fetch connectors: <error message>"
}
```

**cURL Example:**
```bash
curl -X GET https://your-domain.repl.co/api/v1/aam/connectors
```

**Note**: Airbyte sync metadata (`last_sync_*` fields) requires SchemaObserver service to be running and connection to have `airbyte_connection_id` set. Drift metadata requires DriftEvent records in database.

---

### POST `/api/v1/aam/connectors/{connector_id}/discover`

Trigger schema discovery for a connector.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (202 Accepted):**
```json
{
  "job_id": "job-123e4567-e89b-12d3-a456-426614174000",
  "status": "queued",
  "connector_id": "salesforce-prod"
}
```

---

### GET `/api/v1/aam/intelligence/mappings`

Get mapping registry status with autofix/HITL breakdown.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
  "mappings": [
    {
      "vendor": "salesforce",
      "canonical_field": "account_name",
      "vendor_field": "Name",
      "confidence": 1.0,
      "coercion": null
    },
    {
      "vendor": "hubspot",
      "canonical_field": "account_name",
      "vendor_field": "company_name",
      "confidence": 0.95,
      "coercion": "lowercase"
    }
  ]
}
```

---

### GET `/api/v1/aam/intelligence/drift_events_24h`

Get drift events detected in the last 24 hours grouped by source.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
  "drift_events": [
    {
      "id": "drift-001",
      "connection_id": "conn-123",
      "event_type": "field_added",
      "old_schema": {"fields": ["name", "email"]},
      "new_schema": {"fields": ["name", "email", "phone"]},
      "confidence": 0.85,
      "status": "auto_repaired",
      "created_at": "2025-11-18T10:30:00+00:00"
    }
  ]
}
```

---

### Additional AAM Endpoints

The following additional AAM endpoints are available:

- **GET** `/api/v1/aam/status` - AAM services health check
- **GET** `/api/v1/aam/metrics` - AAM dashboard metrics summary
- **GET** `/api/v1/aam/events` - Recent AAM events with filters
- **GET** `/api/v1/aam/connections` - List all AAM connector connections
- **GET** `/api/v1/aam/intelligence/rag_queue` - RAG-based mapping suggestions queue
- **GET** `/api/v1/aam/intelligence/repair_metrics` - Drift auto-repair metrics
- **GET** `/api/v1/aam/discovery/jobs/{job_id}` - Get schema discovery job status

> **Note:** Bulk mapping endpoints (`/api/v1/bulk-mappings`) are available in the codebase (`app/api/v1/bulk_mappings.py`) but not currently exposed via the API. This functionality is available through the internal `services/mapping_intelligence` module.

---

## NLP Endpoints

### POST `/nlp/v1/persona/classify`

Classify a natural language query into a persona (CTO, CRO, COO, CFO) using keyword matching.

**Request Body:**
```json
{
  "query": "What is our cloud spend this month?"
}
```

**Response (200 OK):**
```json
{
  "persona": "coo",
  "confidence": 0.95,
  "matched_keywords": ["cloud", "spend", "month"],
  "trace_id": "trace-123e4567-e89b-12d3-a456-426614174000"
}
```

**cURL Example:**
```bash
curl -X POST https://your-domain.repl.co/nlp/v1/persona/classify \
  -H "Content-Type: application/json" \
  -d '{"query": "What is our cloud spend this month?"}'
```

**Python Example:**
```python
response = requests.post(
    "https://your-domain.repl.co/nlp/v1/persona/classify",
    json={"query": "What is our cloud spend this month?"}
)

persona_data = response.json()
persona = persona_data["persona"]  # "coo"
```

**JavaScript Example:**
```javascript
const response = await fetch('https://your-domain.repl.co/nlp/v1/persona/classify', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ query: 'What is our cloud spend this month?' })
});

const data = await response.json();
const persona = data.persona;  // "coo"
```

---

### GET `/nlp/v1/persona/summary`

Get role-specific dashboard summary with KPIs and data tables.

**Query Parameters:**
- `persona` (required): `cto`, `cro`, `coo`, or `cfo`

**Response (200 OK):**
```json
{
  "persona": "coo",
  "tiles": [
    {
      "key": "cloud_spend",
      "title": "Cloud Spend (MTD)",
      "value": "$45,230",
      "delta": "+12%",
      "timeframe": "MTD vs Budget",
      "last_updated": "2025-11-18T12:00:00Z",
      "href": "/finops"
    }
  ],
  "table": {
    "title": "Top 10 Cost Centers (MTD)",
    "columns": ["Cost Center", "MTD Spend", "Δ vs prior period"],
    "rows": [
      ["Engineering", "$25,000", "+15%"],
      ["Sales", "$12,500", "+8%"]
    ],
    "href": "/finops/cost-centers"
  },
  "trace_id": "trace-123"
}
```

**cURL Example:**
```bash
curl -X GET "https://your-domain.repl.co/nlp/v1/persona/summary?persona=coo"
```

---

## WebSocket Connections

### WS `/dcl`

Real-time DCL graph updates via WebSocket.

**Connection:**
```javascript
const ws = new WebSocket('ws://your-domain.repl.co/dcl');

ws.onopen = () => {
  console.log('Connected to DCL WebSocket');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('DCL Graph Update:', data);
  // data.nodes, data.edges, data.confidence
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('WebSocket connection closed');
};
```

**Message Format:**
```json
{
  "nodes": [
    {"id": "salesforce", "label": "Salesforce", "type": "source"},
    {"id": "account", "label": "Account", "type": "entity"}
  ],
  "edges": [
    {"source": "salesforce", "target": "account", "weight": 100}
  ],
  "confidence": 0.95,
  "last_updated": "2025-11-18T12:00:00Z"
}
```

---

### GET `/api/v1/events/stream`

Server-Sent Events (SSE) endpoint for real-time event streaming.

**Authentication:** JWT token required via query parameter (EventSource doesn't support custom headers)

**Endpoint:** `GET /api/v1/events/stream?token=<jwt_token>`

**Connection:**
```javascript
// Note: EventSource doesn't support custom headers, so token is passed as query param
const accessToken = 'your_jwt_token_here';
const eventSource = new EventSource(
  `https://your-domain.repl.co/api/v1/events/stream?token=${accessToken}`
);

// Connected event
eventSource.addEventListener('connected', (event) => {
  const data = JSON.parse(event.data);
  console.log('Connected:', data);
  // {"type": "connected", "ts": "2025-11-18T12:00:00.000000", "tenant": "tenant-uuid"}
});

// Regular data events
eventSource.addEventListener('event', (event) => {
  const data = JSON.parse(event.data);
  console.log('Event:', data);
  // See event payload structure below
});

// Heartbeat events (every 15 seconds by default)
eventSource.addEventListener('heartbeat', (event) => {
  const data = JSON.parse(event.data);
  console.log('Heartbeat:', data);
  // {"ts": "2025-11-18T12:00:15.000000"}
});

// Error events
eventSource.addEventListener('error', (event) => {
  const data = JSON.parse(event.data);
  console.error('Error:', data);
  // {"type": "error", "message": "error description", "ts": "2025-11-18T12:00:00.000000"}
});
```

**Event Types Emitted:**

1. **`connected` event** - Initial connection confirmation:
```json
{
  "type": "connected",
  "ts": "2025-11-18T16:47:42.973261",
  "tenant": "9497f49c-5e3b-496a-a10f-d7a5bbed1e21"
}
```

2. **`event` events** - Data events (from Redis PubSub, database polling, or mock generator):
```json
{
  "id": "evt_1700308800123_4567",
  "ts": "2025-11-18T12:00:00.000000",
  "tenant": "9497f49c-5e3b-496a-a10f-d7a5bbed1e21",
  "source_system": "salesforce",
  "entity": "Account",
  "stage": "canonicalized",
  "meta": {
    "record_count": 42,
    "processing_time_ms": 123
  }
}
```

**Event field values:**
- `source_system`: One of: `"salesforce"`, `"supabase"`, `"mongodb"`, `"filesource"`, `"system"`
- `entity`: One of: `"Account"`, `"Contact"`, `"Opportunity"`, `"Lead"`, `"User"`, `"Order"`, `"Product"`
- `stage`: One of: `"ingested"`, `"canonicalized"`, `"materialized"`, `"viewed"`, `"intent"`, `"journaled"`, `"drift"`

3. **`heartbeat` events** - Keep-alive (sent every 15 seconds):
```json
{
  "ts": "2025-11-18T12:00:15.000000"
}
```

4. **`error` events** - Stream errors:
```json
{
  "type": "error",
  "message": "Connection lost",
  "ts": "2025-11-18T12:00:00.000000"
}
```

**Event Sources (in priority order):**
1. **Redis PubSub** (primary): Subscribes to patterns `aam.streams.*`, `aam.events.schema.change`, `aos.intents.*`
2. **Database polling** (fallback): Polls `canonical_events` table for recent events
3. **Mock generator** (development): Generates synthetic events every 2-5 seconds for testing

**Security:**
- All events are filtered by authenticated user's `tenant_id` for multi-tenant isolation
- Invalid or missing JWT token returns `401 Unauthorized`

**Python Example:**
```python
import requests
import json

# SSE client example
url = f"https://your-domain.repl.co/api/v1/events/stream?token={access_token}"
response = requests.get(url, stream=True)

for line in response.iter_lines():
    if line:
        decoded_line = line.decode('utf-8')
        if decoded_line.startswith('data: '):
            data = json.loads(decoded_line[6:])
            print(f"Event: {data}")
```

---

## Error Codes

### HTTP Status Codes

| Code | Description | Example |
|------|-------------|---------|
| `200` | OK | Successful request |
| `201` | Created | Resource created (e.g., user registration) |
| `202` | Accepted | Async job queued |
| `400` | Bad Request | Invalid request body or parameters |
| `401` | Unauthorized | Missing or invalid authentication token |
| `403` | Forbidden | Insufficient permissions |
| `404` | Not Found | Resource not found |
| `429` | Too Many Requests | Rate limit exceeded |
| `500` | Internal Server Error | Unexpected server error |
| `503` | Service Unavailable | Redis/database unavailable |

### Error Response Format

```json
{
  "detail": "Error message describing what went wrong",
  "status_code": 400,
  "trace_id": "trace-123e4567-e89b-12d3-a456-426614174000"
}
```

### Common Error Examples

**401 Unauthorized:**
```json
{
  "detail": "Could not validate credentials"
}
```

**HTTP Headers (not in JSON body):**
```
WWW-Authenticate: Bearer
```

**429 Too Many Requests:**
```json
{
  "detail": "Rate limit exceeded. Please try again in 60 seconds.",
  "retry_after": 60
}
```

**503 Service Unavailable:**
```json
{
  "detail": "Redis is not available. Cannot process bulk mapping jobs."
}
```

---

## Rate Limits

### Default Limits (Per Tenant)

| Endpoint Category | Requests per Minute | Burst |
|-------------------|---------------------|-------|
| Authentication | 10 | 20 |
| Read Operations (GET) | 60 | 100 |
| Write Operations (POST/PUT/DELETE) | 30 | 50 |
| Bulk Operations | 5 | 10 |
| WebSocket Connections | 10 connections | - |

### Rate Limit Headers

Response headers indicate current rate limit status:

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 42
X-RateLimit-Reset: 1700308800
```

### Concurrent Job Limits

- **Max concurrent bulk mapping jobs per tenant:** 5
- **Max queued jobs per tenant:** 100
- **Job TTL (Redis):** 24 hours

---

## Pagination

List endpoints support pagination using query parameters.

### Query Parameters

- `limit` (default: 100, max: 1000): Number of items per page
- `offset` (default: 0): Number of items to skip

### Example Request

```bash
curl -X GET "https://your-domain.repl.co/api/v1/bulk-mappings?limit=50&offset=100" \
  -H "Authorization: Bearer <token>"
```

### Response Format

```json
{
  "items": [...],
  "total": 523,
  "limit": 50,
  "offset": 100,
  "has_more": true
}
```

---

## Best Practices

1. **Always use HTTPS in production** - Never send tokens over unencrypted connections
2. **Store tokens securely** - Use secure storage (environment variables, encrypted key stores)
3. **Implement exponential backoff** - Retry failed requests with increasing delays
4. **Handle rate limits gracefully** - Check `X-RateLimit-Remaining` and back off before hitting limit
5. **Use WebSockets for real-time updates** - More efficient than polling
6. **Set appropriate timeouts** - Default: 30s for REST, 5min for bulk jobs
7. **Validate responses** - Always check HTTP status codes and error messages
8. **Use trace IDs for debugging** - Include in support requests for faster resolution

---

## Support

For API support, contact:
- **Documentation:** See `/docs` directory
- **Issues:** File bug reports with `trace_id` from error responses
- **Updates:** Check `CHANGELOG.md` for API changes

---

## 📋 Planned Features

This appendix documents features currently in development or planned for future releases.

### Authentication (v2.0 - Q2 2025)

**Production JWT Authentication**:
- [ ] Real JWT validation in production mode (`DCL_AUTH_ENABLED=true`)
- [ ] Configurable JWT algorithms (HS256/RS256/RS512)
- [ ] Token refresh endpoints (`POST /api/v1/auth/refresh`)
- [ ] Tenant provisioning during registration (currently implemented, needs production testing)
- [ ] Role-based access control (RBAC) and permission management
- [ ] Multi-factor authentication (MFA) support
- [ ] Session management and revocation
- [ ] OAuth2/OIDC integration for SSO

**Current Status**: Authentication middleware exists (`app/security.py`) but is bypassed in demo mode. Setting `DCL_AUTH_ENABLED=true` in production will enable full JWT validation.

---

### AAM Telemetry (v2.0 - Q2 2025)

**Enhanced Connector Metrics**:
- [ ] Real-time drift event streaming via WebSocket
- [ ] Historical performance analytics and trending
- [ ] Advanced drift detection algorithms (ML-based)
- [ ] RAG queue depth monitoring and optimization
- [ ] Connector health scoring and predictive alerts
- [ ] Multi-tenant isolation for AAM metrics
- [ ] Custom alerting rules and notifications

**Current Status**: AAM endpoints return rich telemetry when AAM services are running (`AAM_MODELS_AVAILABLE=True`). Mock fallbacks are provided when services are unavailable. Production deployments should ensure AAM services (SchemaObserver, RAGEngine, DriftRepairAgent) are running.

---

### Deployment Automation (v1.5 - Q1 2025)

**CI/CD Pipeline**:
- [ ] Automated frontend build pipeline (GitHub Actions)
- [ ] Automated static asset deployment (dist → static/)
- [ ] Blue-green deployment support for zero-downtime updates
- [ ] Automated rollback procedures on deployment failure
- [ ] Container registry integration (Docker Hub, ECR)
- [ ] Kubernetes Helm charts for orchestration
- [ ] Automated database migration testing (pre-deployment)
- [ ] Performance regression testing in CI pipeline

**Current Status**: Frontend assets are manually built and committed to `static/` directory. See `docs/deployment/DEPLOYMENT_GUIDE.md` for current deployment workflow.

---

### Data Layer Enhancements (v1.5 - Q1 2025)

**Multi-Tenant Isolation**:
- [ ] Row-level security (RLS) policies in PostgreSQL
- [ ] Tenant-scoped database connection pools
- [ ] Cross-tenant data leakage prevention audits
- [ ] Tenant-specific rate limiting and quotas

**Performance Optimizations**:
- [ ] Query result caching (Redis-backed)
- [ ] Database connection pooling optimization (PgBouncer)
- [ ] Materialized view refresh optimization
- [ ] Bulk operation batching and parallelization

---

### Observability & Monitoring (v1.5 - Q1 2025)

**Metrics & Alerting**:
- [ ] Prometheus metrics endpoint (`/metrics`)
- [ ] Grafana dashboard templates
- [ ] Custom alerting rules (PagerDuty, Slack, email)
- [ ] Distributed tracing (Jaeger, OpenTelemetry)
- [ ] Log aggregation (Loki, CloudWatch, Datadog)
- [ ] Error tracking integration (Sentry, Rollbar)

**Audit Logging**:
- [ ] Comprehensive audit trail for all mutations
- [ ] Compliance reporting (SOC2, HIPAA)
- [ ] User activity tracking and analytics
- [ ] Data access logs for security audits

---

### Timeline & Roadmap

| Feature | Target Release | Status |
|---------|---------------|--------|
| Automated CI/CD Pipeline | v1.5 (Q1 2025) | Planned |
| Production JWT Auth | v2.0 (Q2 2025) | Code exists, needs production enablement |
| Enhanced AAM Telemetry | v2.0 (Q2 2025) | Partially implemented, needs full AAM stack |
| Multi-Tenant Isolation | v1.5 (Q1 2025) | In progress |
| Observability Stack | v1.5 (Q1 2025) | Planned |

For the latest roadmap updates, see `PLAN.md` in the repository root.
