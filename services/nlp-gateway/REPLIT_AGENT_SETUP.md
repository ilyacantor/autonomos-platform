# Replit Agent Configuration for AOS NLP Gateway

**Last Updated:** November 19, 2025

This guide configures Replit Agent to use the AOS NLP Gateway as its backend, enabling natural language queries over AutonomOS services with tenant-scoped RAG knowledge base.

## Prerequisites

1. NLP Gateway service running on port 8001
2. Database migration applied (`alembic upgrade head`)
3. Demo data seeded (`make seed` in services/nlp-gateway/)
4. JWT authentication configured

## System Prompt

Paste this into Replit Agent's "Instructions" or "System Prompt" field:

```
Role
You are the AOS NLP Gateway: a natural-language interface over AutonomOS services (AOD/AAM/DCL/FinOps/etc.). You understand intent, call tools with typed inputs, and produce grounded answers. You never claim to execute changes; you propose actions.

Default scope
- tenant_id = demo-tenant unless user provides one
- Time window = last 30 days (America/Los_Angeles) unless specified
- Environment = prod unless specified (env ∈ {dev, stage, prod})

Core policies
- Prefer tools/RAG over guesses. If a key parameter is missing (tenant, env, time range, service), infer from defaults; if still ambiguous, ask one short question
- Ground every answer in tool outputs and/or RAG citations (e.g., [Doc:Section])
- Redact credentials/PII
- Action requests → respond with a Proposed Action block (never execute)
- Be concise: result first (3–8 bullets or a short paragraph), then sources

Output format (always include)
- Answer (direct, compact)
- Scope: {tenant_id, env, time_window}
- Sources: tool names and/or document citations used
- Proposed Action (only if the user asked to do something)

Failure behavior
- If a tool fails, return a brief error summary with the tool name and suggest a next step
- If the KB lacks an answer, say so and suggest what to ingest (files/URLs)

Tool routing
- Call the single best tool first; chain more only when needed
- Obey each tool's input/output schema exactly
- Echo the resolved scope in your answer
```

## Tool Registration

Register these 7 tools in Replit Agent, mapping them to the NLP Gateway endpoints:

### 1. FinOps Summary
- **Tool Name**: `finops_get_summary`
- **Endpoint**: `POST http://localhost:8001/v1/finops/summary`
- **Description**: Get FinOps cost optimization summary for a date range
- **Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "tenant_id": {"type": "string", "default": "demo-tenant"},
    "env": {"type": "string", "enum": ["dev", "stage", "prod"], "default": "prod"},
    "from": {"type": "string", "format": "date", "description": "Start date YYYY-MM-DD"},
    "to": {"type": "string", "format": "date", "description": "End date YYYY-MM-DD"}
  },
  "required": ["from", "to"]
}
```

### 2. RevOps Incident
- **Tool Name**: `revops_get_incident`
- **Endpoint**: `POST http://localhost:8001/v1/revops/incident`
- **Description**: Get revenue ops incident details and resolution
- **Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "tenant_id": {"type": "string", "default": "demo-tenant"},
    "env": {"type": "string", "enum": ["dev", "stage", "prod"], "default": "prod"},
    "incident_id": {"type": "string", "description": "Incident identifier"}
  },
  "required": ["incident_id"]
}
```

### 3. AOD Dependencies
- **Tool Name**: `aod_get_dependencies`
- **Endpoint**: `POST http://localhost:8001/v1/aod/dependencies`
- **Description**: Get service dependency mapping and health status
- **Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "tenant_id": {"type": "string", "default": "demo-tenant"},
    "env": {"type": "string", "enum": ["dev", "stage", "prod"], "default": "prod"},
    "service": {"type": "string", "description": "Service name"}
  },
  "required": ["service"]
}
```

### 4. AAM Connectors
- **Tool Name**: `aam_list_connectors`
- **Endpoint**: `POST http://localhost:8001/v1/aam/connectors`
- **Description**: List AAM connectors with health and drift status
- **Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "tenant_id": {"type": "string", "default": "demo-tenant"},
    "env": {"type": "string", "enum": ["dev", "stage", "prod"], "default": "prod"},
    "status": {"type": "string", "enum": ["All", "Healthy", "Drifted", "Error"], "default": "All"}
  }
}
```

### 5. KB Search (RAG)
- **Tool Name**: `kb_search`
- **Endpoint**: `POST http://localhost:8001/v1/kb/search`
- **Description**: Search the knowledge base for documentation and answers
- **Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "tenant_id": {"type": "string", "default": "demo-tenant"},
    "env": {"type": "string", "enum": ["dev", "stage", "prod"], "default": "prod"},
    "query": {"type": "string", "description": "Natural language query"},
    "top_k": {"type": "integer", "default": 5, "description": "Number of results"}
  },
  "required": ["query"]
}
```

### 6. KB Ingest (Learning)
- **Tool Name**: `kb_ingest`
- **Endpoint**: `POST http://localhost:8001/v1/kb/ingest`
- **Description**: Ingest documents, files, or URLs into the knowledge base
- **Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "tenant_id": {"type": "string", "default": "demo-tenant"},
    "env": {"type": "string", "enum": ["dev", "stage", "prod"], "default": "prod"},
    "items": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {"type": "string", "enum": ["file", "url", "text"]},
          "location": {"type": "string"},
          "tags": {"type": "array", "items": {"type": "string"}}
        }
      }
    },
    "policy": {
      "type": "object",
      "properties": {
        "chunk": {"type": "string", "enum": ["auto", "fixed"], "default": "auto"},
        "max_chunk_tokens": {"type": "integer", "default": 1200},
        "redact_pii": {"type": "boolean", "default": true}
      }
    }
  },
  "required": ["items"]
}
```

### 7. Feedback Log
- **Tool Name**: `feedback_log`
- **Endpoint**: `POST http://localhost:8001/v1/feedback/log`
- **Description**: Log user feedback for continuous improvement
- **Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "tenant_id": {"type": "string", "default": "demo-tenant"},
    "env": {"type": "string", "enum": ["dev", "stage", "prod"], "default": "prod"},
    "turn_id": {"type": "string", "description": "Conversation turn ID"},
    "rating": {"type": "string", "enum": ["up", "down"]},
    "notes": {"type": "string", "default": ""}
  },
  "required": ["turn_id", "rating"]
}
```

## Authentication

All tools require JWT authentication. Add this header to each request:
```
Authorization: Bearer <JWT_TOKEN>
```

To get a token for demo-tenant:
```bash
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@autonomos.ai", "password": "TestPassword123!"}'
```

## Prompt Starters

Add these suggested prompts to help users discover functionality:

1. **FinOps monthly summary**
   - "Show me the FinOps summary for this month"
   - Expected tool: finops_get_summary

2. **Incident I-9A03 details**
   - "What happened with incident I-9A03?"
   - Expected tool: revops_get_incident

3. **Dependencies for checkout-service**
   - "Show me dependencies for checkout-service"
   - Expected tool: aod_get_dependencies

4. **What connectors are Drifted?**
   - "List all drifted AAM connectors"
   - Expected tool: aam_list_connectors

5. **Summarize attached PDF**
   - "Summarize the attached FinOps PDF (deltas vs last month)"
   - Expected tool: kb_ingest → kb_search

6. **How do I configure Salesforce connector?**
   - "How do I configure the Salesforce connector?"
   - Expected tool: kb_search

7. **Find runbooks for incident response**
   - "Show me runbooks for RevOps incident response"
   - Expected tool: kb_search

## Environment Variables

Configure these in your environment:

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:port/dbname

# Redis for background jobs
REDIS_URL=redis://localhost:6379

# JWT Secret (same as main AutonomOS app)
JWT_SECRET_KEY=<same-as-main-app>

# Optional: ML dependencies
# If not installed, service uses fallback implementations
# - sentence-transformers (for vector embeddings)
# - presidio (for PII redaction)
# - tiktoken (for token counting)
```

## Testing the Setup

1. **Start NLP Gateway**:
```bash
cd services/nlp-gateway
make run
```

2. **Health Check**:
```bash
curl http://localhost:8001/health
# Expected: {"status":"ok"}
```

3. **Test KB Search** (after seeding):
```bash
# Get JWT token first
TOKEN=$(curl -s -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@autonomos.ai","password":"TestPassword123!"}' \
  | jq -r '.access_token')

# Search KB
curl -X POST http://localhost:8001/v1/kb/search \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":"demo-tenant","env":"prod","query":"How does hybrid search work?","top_k":3}'
```

4. **Test via Replit Agent**:
   - Ask: "How does the AAM connector system work?"
   - Agent should call kb_search tool
   - Response should include citations [Doc:Section]

## Observability

Every response includes a `trace_id` for debugging:
```json
{
  "matches": [...],
  "trace_id": "nlp_20251108003524_a1b2c3d4",
  "timestamp": "2025-11-08T00:35:24.123456"
}
```

Logs are structured and include trace_id context:
```
2025-11-08 00:35:24 - nlp_gateway - INFO - [trace_id=nlp_...] KB search completed: 3 results
```

## Next Steps

1. **MCP Wrapper** (Phase 2): Wrap these 7 endpoints with MCP protocol for cross-platform reuse
2. **Production Integration**: Connect business endpoints (FinOps, RevOps, AOD, AAM) to live databases
3. **Advanced RAG**: Add reranking, query expansion, and semantic caching
4. **Metrics**: Add Prometheus/Grafana for p95 latency tracking
5. **Feedback Loop**: Implement nightly job to update retriever weights based on user feedback

## Troubleshooting

**Q: Tool calls fail with 401 Unauthorized**
A: Ensure JWT token is valid and includes tenant_id claim

**Q: KB search returns no results**
A: Run `make seed` to populate demo data, or use kb_ingest to add documents

**Q: Service crashes on startup**
A: Check that optional ML dependencies are wrapped properly (service should start with fallbacks)

**Q: Responses don't include citations**
A: Ensure documents in KB have proper metadata (title, section) during ingestion

## References

- NLP Gateway OpenAPI: http://localhost:8001/docs
- Main AutonomOS API: http://localhost:5000/api/docs
- Replit Agent MCP Docs: https://docs.replit.com/ai/mcp
