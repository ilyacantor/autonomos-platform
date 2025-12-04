# DCL Removal Assessment

**Date:** December 2, 2025  
**Status:** Assessment Only (No Action Taken)  
**Complexity Rating:** HIGH

## Background

The DCL (Data Connection Layer) implementation in this repository has been characterized as convoluted, slow, and brittle. A fresh implementation has been started in a separate repository. This document assesses what would be required to cleanly remove DCL from this platform.

---

## DCL Footprint

### Backend Directories & Files

| Path | Description |
|------|-------------|
| `app/dcl_engine/` | Main DCL engine (routers, services, DuckDB registry, intelligence workflows) |
| `dcl/` | Legacy DCL module (if exists) |
| `shared/dcl_mapping_client.py` | Shared DCL mapping client |
| `app/api/v1/dcl.py` | DCL API router |
| `app/api/v1/dcl_unify.py` | DCL unification endpoints |
| `app/api/v1/dcl_views.py` | DCL view endpoints |
| `aam_hybrid/core/dcl_output_adapter.py` | AAM-to-DCL integration adapter |

### Scripts

| Path | Description |
|------|-------------|
| `scripts/migrate_dcl_tenant_isolation.py` | DCL tenant isolation migration |
| `scripts/dod/*.py` | Various DCL-related scripts |

### Tests

| Path | Description |
|------|-------------|
| `tests/dcl/` | DCL unit tests |
| `tests/contract/test_dcl_*` | DCL contract tests |
| `tests/integration/test_dcl_aam_mapping_flow.py` | DCL-AAM integration tests |

---

## Dependencies on DCL

### AAM Integration

- `aam_hybrid/core/dcl_output_adapter.py` - Bridges AAM canonical events to DCL
- Canonical mapping registries used by AAM
- **Impact:** Would need stubbing or removal; AAM-to-ontology flows would break

### Frontend Components

| Component | File | Purpose |
|-----------|------|---------|
| NewOntologyPage | `frontend/src/components/NewOntologyPage.tsx` | Ontology management UI |
| DCLGraphContainer | `frontend/src/components/DCLGraphContainer.tsx` | Graph visualization container |
| LiveSankeyGraph | `frontend/src/components/LiveSankeyGraph.tsx` | Real-time Sankey diagram |
| LazyGraphShell | `frontend/src/components/LazyGraphShell.tsx` | Lazy-loaded graph wrapper |

### Frontend Hooks & Services

| Hook/Service | Purpose |
|--------------|---------|
| `useDCLState` | DCL state management hook |
| `dclDefaults` | Default DCL configuration |
| `dclBridgeService` | Bridge between frontend and DCL API |

### API Endpoints Called by Frontend

- `/dcl/connect` - Connect data sources
- `/dcl/state` - Get DCL state
- `/dcl/ontology_schema` - Get ontology schema
- `/dcl/feature_flags` - Get feature flags

### Navigation Impact

- "Ontology" menu item in LeftNav/TopBar
- Control Center metrics cards that reference DCL data

---

## Database Artifacts

### Tables Requiring Archival/Removal

| Table | Purpose |
|-------|---------|
| `mapping_registry` | Source-to-ontology field mappings |
| `canonical_streams` | Canonical event stream storage |
| `drift_events` | Schema drift event records |
| `schema_changes` | Schema change history |
| `materialized_*` | DuckDB materialized views |
| `dcl_unified_contact*` | Unified contact entities |
| `hitl_*` | Human-in-the-loop audit tables |

### Migration Considerations

- Alembic migrations created these tables
- Would require new down-migrations or archival strategy
- Data retention decisions needed before deletion

---

## Package Dependencies

### Potentially Removable (DCL-Specific)

| Package | Purpose | Caution |
|---------|---------|---------|
| `duckdb` | Embedded SQL analytics | DCL-specific |
| `pandas` | Data manipulation | May be used elsewhere |
| `sentence-transformers` | Embeddings for RAG | NLP Gateway may need |
| `google-generativeai` | Gemini LLM integration | NLP Gateway may need |
| `openai` | OpenAI API integration | NLP Gateway may need |
| `pinecone` | Vector database | RAG-specific |
| `rank-bm25` | BM25 retrieval | RAG-specific |
| `presidio-analyzer` | PII detection | NLP Gateway may need |
| `presidio-anonymizer` | PII anonymization | NLP Gateway may need |

**Note:** Validate NLP Gateway dependencies before removing LLM/PII packages.

---

## Configuration & Feature Flags

### Backend Feature Flags

| Flag | Purpose |
|------|---------|
| `USE_AAM_AS_SOURCE` | Toggle AAM as DCL data source |
| `USE_DCL_INTELLIGENCE_API` | Enable DCL intelligence endpoints |

### Environment Variables

- DuckDB registry paths
- DCL-specific config in `app/dcl_engine/config`

### Frontend Feature Flags

- `VITE_CONNECTIONS_V2` - May affect DCL-related UI

---

## Functionality Lost Upon Removal

1. **Ontology Visualization** - Sankey graph showing Sources → Ontology → Agents flow
2. **Canonical Mapping Workflows** - Source field to ontology field mapping
3. **Drift HITL Review** - Human-in-the-loop approval for schema repairs
4. **Agent Intelligence Surfaces** - Agents expecting standardized DCL entities
5. **Demo Pipeline** - End-to-end AOD→AAM→DCL→Agent demo flow
6. **Graph Generation** - Visual representation of data relationships

---

## Recommended Removal Approach

### Phase A: Feature Flag Off (No Deletion)

1. Set `USE_DCL_INTELLIGENCE_API=false`
2. Add fallback stubs for frontend components
3. Validate platform still loads without DCL endpoints
4. Monitor for any runtime errors

### Phase B: Backend Removal

1. Remove DCL routers from `app/main.py`
2. Delete `app/dcl_engine/` directory
3. Update AAM adapters to neutral stubs or remove entirely
4. Remove DCL-related scripts

### Phase C: Frontend Cleanup

1. Remove or stub DCL-dependent components
2. Update navigation (remove "Ontology" item or replace with placeholder)
3. Update Control Center to not reference DCL metrics
4. Remove `dclBridgeService` and related hooks

### Phase D: Database Cleanup

1. Create down-migration for DCL tables
2. Archive data if retention required
3. Run migration to drop tables

### Phase E: Dependency Pruning

1. Identify packages not used by remaining services
2. Remove from `requirements.txt`
3. Verify NLP Gateway still functions
4. Run full test suite

---

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Breaking AAM-to-ontology flow | High | Stub adapters before removal |
| Frontend crashes on missing endpoints | High | Feature flag and fallbacks first |
| Removing packages needed by NLP | Medium | Audit package usage before removal |
| Data loss in DCL tables | Medium | Archive before deletion |
| Test suite failures | Low | Update/remove DCL tests |

---

## Effort Estimate

| Layer | Files Affected | Complexity |
|-------|----------------|------------|
| Backend | ~10-15 files | High |
| Frontend | ~6-8 components | Medium |
| Database | ~8 tables | Medium |
| Dependencies | ~10 packages | Low |
| Tests | ~5-10 test files | Low |
| Config/Flags | ~5 settings | Low |

**Overall Complexity:** HIGH - Requires coordinated changes across all layers with careful sequencing to avoid breaking the platform.

---

## Decision

**Status:** Assessment documented. No action taken.

The DCL implementation has been superseded by a fresh repository. This assessment is preserved for reference when the team decides to proceed with removal.
