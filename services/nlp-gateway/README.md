# AOS NLP Gateway

Production-grade natural language interface for AutonomOS services. Query your infrastructure using plain English.

## 📚 Documentation

- **[How-To Guide](HOW_TO_USE.md)** - Complete user guide with examples and workflows
- **[Quick Reference](QUICK_REFERENCE.md)** - Fast lookup cheat sheet
- **[Replit Agent Setup](REPLIT_AGENT_SETUP.md)** - Configure Replit Agent integration
- **[API Documentation](http://localhost:8001/docs)** - OpenAPI spec (when gateway is running)

## 🚀 Quick Start

```bash
# 1. Seed demo data (first time only)
make seed

# 2. Start the gateway
make run

# 3. Access via AutonomOS UI
# Navigate to Control Center tab → NLP Gateway at top
```

## 🎯 What It Does

The NLP Gateway provides 7 REST endpoints for natural language interaction:

1. **Knowledge Base** (`/v1/kb/search`) - RAG-powered documentation search
2. **FinOps** (`/v1/finops/summary`) - Cost summaries and optimization
3. **RevOps** (`/v1/revops/incident`) - Incident details and resolutions
4. **Discovery** (`/v1/aod/dependencies`) - Service dependency mapping
5. **Connectors** (`/v1/aam/connectors`) - AAM health monitoring
6. **Ingest** (`/v1/kb/ingest`) - Document ingestion
7. **Feedback** (`/v1/feedback/log`) - User feedback collection

## 🏗️ Architecture

```
User Input → NLP Gateway (Port 8001) → Service Endpoint
                ↓
         RAG Knowledge Base
         (Postgres + pgvector)
                ↓
    Hybrid Retrieval (BM25 + Vector)
                ↓
         Response + Citations
```

**Key Features:**
- Tenant-scoped data isolation
- Hybrid search (BM25 + 384-dim vector embeddings)
- JWT authentication
- PII redaction
- Structured logging with trace IDs
- Sub-1.5s p95 latency

## 🛠️ Tech Stack

- **Framework**: FastAPI (async)
- **Database**: PostgreSQL + pgvector
- **Search**: BM25 (full-text) + Vector similarity
- **Fusion**: Reciprocal Rank Fusion (RRF)
- **Auth**: JWT token extraction
- **Optional ML**: sentence-transformers, presidio, tiktoken (graceful fallbacks)

## 📁 Project Structure

```
services/nlp-gateway/
├── main.py                 # FastAPI app entry point
├── Makefile               # Build commands
├── requirements.txt       # Python dependencies
├── api/                   # 7 REST endpoint handlers
│   ├── kb_search.py
│   ├── kb_ingest.py
│   ├── finops.py
│   ├── revops.py
│   ├── aod.py
│   ├── aam.py
│   └── feedback.py
├── kb/                    # RAG engine
│   ├── retrieval.py      # Hybrid search
│   ├── ingestion.py      # Document chunking
│   └── models.py         # SQLAlchemy models
├── schemas/              # Pydantic models
│   ├── common.py
│   ├── kb.py
│   └── services.py
├── utils/                # Utilities
│   ├── auth.py           # JWT middleware
│   ├── logging.py        # Trace IDs
│   └── pii.py            # Redaction
├── tests/                # E2E tests
├── examples/             # HTTP requests + eval dataset
└── docs/                 # User guides
    ├── HOW_TO_USE.md
    ├── QUICK_REFERENCE.md
    └── REPLIT_AGENT_SETUP.md
```

## 🧪 Development

```bash
# Run tests
make test

# Lint code
make lint

# Evaluate on test set (25 prompts)
make eval

# Run in development mode
make run

# View logs
tail -f /tmp/logs/nlp_gateway_*.log
```

## 🗄️ Database Schema

**5 New Tables** (Alembic migration `b15b4a5021b3`):

1. `kb_documents` - Document metadata (title, source, tenant_id, env)
2. `kb_chunks` - Text chunks with vector embeddings (384-dim)
3. `kb_metadata` - Configuration and settings
4. `kb_ingest_jobs` - Background job tracking
5. `kb_feedback` - User feedback for improvement

**Indexes:**
- GIN index on `content_tsv` for BM25 full-text search
- IVFFlat index on `embedding` for fast vector similarity
- Composite indexes on `(tenant_id, env)` for tenant isolation

## 🔒 Security

- **Tenant Isolation**: All queries scoped by `tenant_id` + `env`
- **JWT Authentication**: Extracts tenant context from token claims
- **PII Redaction**: Optional presidio-based redaction on ingestion
- **SQL Injection Prevention**: Parameterized queries via SQLAlchemy
- **Rate Limiting**: TODO (Phase 2)

## 📊 Performance

**Target Metrics:**
- p50 latency: < 500ms
- p95 latency: < 1.5s
- Throughput: 100+ req/sec (single instance)

**Optimization:**
- Async database operations
- Connection pooling
- Optimized vector indexes (IVFFlat)
- BM25 GIN indexes
- Result caching (TODO)

## 🔄 Migration Path

```bash
# Apply database migration (creates KB tables)
cd /home/runner/workspace
alembic upgrade head

# Verify
psql $DATABASE_URL -c "SELECT tablename FROM pg_tables WHERE tablename LIKE 'kb_%';"
```

## 🐛 Troubleshooting

See [How-To Guide - Troubleshooting Section](HOW_TO_USE.md#troubleshooting)

Common issues:
- Connection refused → `make run` to start gateway
- No results → `make seed` to populate demo data
- 401 errors → Re-login to refresh JWT token
- Slow queries → Check database indexes

## 🚦 Health Check

```bash
curl http://localhost:8001/health
# Expected: {"status":"ok"}
```

## 🧩 Integration

### With Main AutonomOS App

The gateway is designed to run **independently** on port 8001, separate from the main AutonomOS API (port 5000).

**Shared Resources:**
- Same PostgreSQL database
- Same JWT secret key
- Same Redis instance (for background jobs)

**Communication:**
- Frontend calls gateway directly via HTTP
- Gateway calls main app services when needed

### With Replit Agent

See [REPLIT_AGENT_SETUP.md](REPLIT_AGENT_SETUP.md) for complete configuration.

**Quick Summary:**
1. Register 7 tools in Replit Agent
2. Configure system prompt
3. Set default scope (tenant, env, time window)
4. Add prompt starters

## 🛣️ Roadmap

### Phase 1: ✅ Complete
- 7 REST endpoints
- Hybrid RAG search
- JWT auth integration
- E2E tests
- Demo data seeding
- User documentation

### Phase 2: 🚧 Next
- MCP protocol wrapper
- Advanced reranking
- Query expansion
- Semantic caching
- Feedback loop integration
- Production service integration

### Phase 3: 🔮 Future
- Multi-turn conversations
- Proactive alerts
- Trend analysis
- Predictive insights
- Multi-modal support (images, tables)
- Custom embedding models

## 📝 License

Part of AutonomOS Platform - Internal use only

## 🤝 Contributing

1. Test locally: `make test`
2. Lint code: `make lint`
3. Add tests for new features
4. Update documentation
5. Submit PR with trace IDs for testing

## 📧 Support

- **User Guide**: [HOW_TO_USE.md](HOW_TO_USE.md)
- **Quick Ref**: [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
- **API Docs**: http://localhost:8001/docs
- **Logs**: `/tmp/logs/nlp_gateway_*.log`

---

**Built with ❤️ for the AutonomOS Platform**
