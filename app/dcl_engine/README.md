# DCL Engine Source Package

## Overview
This package contains the complete Data Connection Layer (DCL) engine for internalization into the unified AOA backend.

## Contents

### Core Backend Files
- `app.py` - Main FastAPI application with DCL endpoints (73KB)
- `rag_engine.py` - RAG engine for semantic schema mapping
- `vector_helper.py` - Pinecone vector database integration
- `seed_rag.py` - RAG database seeding utility

### Configuration & Data
- `ontology/catalog.yml` - Unified ontology definitions
- `agents/config.yml` - Agent configuration (RevOps, FinOps, etc.)
- `schemas/` - Sample data schemas for 9 enterprise systems

### Dependencies
- `requirements.txt` - Python package dependencies

## Integration Steps

### 1. Extract Package
```bash
tar -xzf dcl_engine_src.tar.gz
cd dcl_engine_package/
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Integration Approach

**Option A: Merge into Existing FastAPI App**
```python
# Import DCL routes from app.py
from dcl_engine.app import router as dcl_router

# Mount in your main FastAPI app
app.include_router(dcl_router, prefix="/api/v1/dcl")
```

**Option B: Run as Microservice**
```bash
uvicorn app:app --host 0.0.0.0 --port 8001
```

### 4. Environment Variables Required
- `GEMINI_API_KEY` - Google Gemini AI API key
- `PINECONE_API_KEY` - Pinecone vector DB (optional, for RAG)
- `DATABASE_URL` - PostgreSQL connection (optional)

### 5. Key Endpoints
- `GET /state` - Current DCL state (sources, entities, mappings)
- `POST /connect` - Add data source and run mapping
- `POST /agents/select` - Configure active agents
- `POST /toggle_dev_mode` - Toggle production/dev validation
- `GET /rag/context` - RAG engine status

## Architecture Notes

- **Thread-safe state management** using `threading.Lock()`
- **DuckDB integration** for view management (registry.duckdb)
- **Dual validation modes**: Heuristic (fast) vs AI/RAG (semantic)
- **Multi-agent filtering** based on ontology domains

## File Structure
```
dcl_engine_package/
├── app.py              # Main DCL backend (1,636 lines)
├── rag_engine.py       # RAG semantic mapping engine
├── vector_helper.py    # Vector embeddings helper
├── seed_rag.py         # RAG database initialization
├── requirements.txt    # Python dependencies
├── ontology/
│   └── catalog.yml     # Unified ontology schema
├── agents/
│   └── config.yml      # Agent configurations
├── schemas/            # Sample schemas (9 systems, 19 files)
│   ├── salesforce/
│   ├── dynamics/
│   ├── netsuite/
│   ├── sap/
│   ├── snowflake/
│   ├── supabase/
│   ├── mongodb/
│   ├── hubspot/
│   └── legacy_sql/
└── README.md          # This file
```

## Testing
After integration, test with:
```bash
curl http://localhost:8000/api/v1/dcl/state
```

Expected response: JSON with `sources`, `entities`, `confidence`

---
**Package Size:** ~250 KB compressed
**Last Updated:** October 20, 2025
**Version:** 2.0 (Unified Backend Ready)
