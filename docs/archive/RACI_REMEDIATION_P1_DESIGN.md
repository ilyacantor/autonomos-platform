# RACI Remediation Phase 1: DCL Mapping Registry
## Technical Design Document

**Version:** 1.0  
**Date:** November 18, 2025  
**Status:** ARCHITECT APPROVED  
**Objective:** Move mapping registry ownership from AAM to DCL per RACI matrix

---

## Executive Summary

**Problem**: AAM currently owns mapping registry storage and decisions, violating RACI matrix where DCL should be accountable for mapping intelligence.

**Solution**: Create DCL mapping registry API, migrate YAML mappings to PostgreSQL, update AAM connectors to request mappings from DCL instead of loading YAML files.

**Impact**: Clean RACI boundary enforcement, scalable database-backed registry, runtime mapping updates without redeployment.

**Effort**: 2-3 weeks, 10 subtasks, sequential execution

---

## Architecture Overview

### Current State (RACI Violation)
```
AAM Connectors
    ↓ (loads YAML directly)
services/aam/canonical/mappings/
├── salesforce.yaml
├── mongodb.yaml
├── filesource.yaml
└── ... (6 YAML files)
    ↓ (applies transformations)
Canonical Events
```

**Problem**: AAM owns both storage AND decisions for mappings.

---

### Target State (RACI Compliant)
```
AAM Connectors
    ↓ (HTTP request)
DCL Mapping Registry API
    ↓ (query)
PostgreSQL mapping_registry table
    ↓ (returns mapping decision)
AAM Connectors
    ↓ (executes transformation per DCL decision)
Canonical Events
```

**Solution**: AAM requests mapping decisions from DCL, only executes transformations.

---

## API Design

### Endpoint 1: Get Field Mapping
```http
GET /dcl/mappings/{connector}/{source_table}/{source_field}
Authorization: Bearer <jwt_token>
```

**Request Parameters:**
- `connector` (path): Connector ID (e.g., "salesforce", "mongodb")
- `source_table` (path): Source table/entity name
- `source_field` (path): Source field name
- `tenant_id` (from JWT): Tenant isolation

**Response 200 OK:**
```json
{
  "mapping_id": "uuid",
  "connector_id": "salesforce",
  "source_table": "Opportunity",
  "source_field": "Amount",
  "canonical_entity": "opportunity",
  "canonical_field": "amount",
  "confidence": 1.0,
  "mapping_type": "direct",
  "transform_expr": null,
  "metadata": {},
  "created_at": "2025-11-18T12:00:00Z",
  "updated_at": "2025-11-18T12:00:00Z"
}
```

**Response 404 Not Found:**
```json
{
  "detail": "No mapping found for salesforce.Opportunity.Amount",
  "suggestion": "Use POST /dcl/rag/propose-mapping for AI suggestion"
}
```

**Caching:**
- Redis cache: 5 minute TTL
- Cache key: `mapping:{tenant_id}:{connector}:{table}:{field}`
- Invalidation: On mapping update via admin API

---

### Endpoint 2: List Connector Mappings
```http
GET /dcl/mappings/{connector}
Authorization: Bearer <jwt_token>
```

**Query Parameters:**
- `source_table` (optional): Filter by source table
- `canonical_entity` (optional): Filter by canonical entity
- `limit` (optional): Default 100, max 1000
- `offset` (optional): Pagination

**Response 200 OK:**
```json
{
  "connector_id": "salesforce",
  "total_count": 147,
  "mappings": [
    {
      "source_table": "Opportunity",
      "source_field": "Amount",
      "canonical_entity": "opportunity",
      "canonical_field": "amount",
      "confidence": 1.0
    },
    ...
  ]
}
```

---

### Endpoint 3: Create/Update Mapping (Admin Only)
```http
POST /dcl/mappings
Authorization: Bearer <admin_jwt_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "connector_id": "salesforce",
  "source_table": "Opportunity",
  "source_field": "Amount",
  "canonical_entity": "opportunity",
  "canonical_field": "amount",
  "confidence": 1.0,
  "mapping_type": "direct",
  "transform_expr": null,
  "metadata": {}
}
```

**Response 201 Created:**
```json
{
  "mapping_id": "uuid",
  "status": "created",
  "cache_invalidated": true
}
```

---

## Database Schema

### Existing Table: `mapping_registry`

**Current Schema** (verified in production):
```sql
CREATE TABLE mapping_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connector_id VARCHAR(100) NOT NULL,
    source_table VARCHAR(255) NOT NULL,
    source_field VARCHAR(255) NOT NULL,
    canonical_entity VARCHAR(100) NOT NULL,
    canonical_field VARCHAR(100) NOT NULL,
    confidence FLOAT DEFAULT 1.0,
    mapping_type VARCHAR(50) DEFAULT 'direct',
    transform_expr TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_mapping_lookup ON mapping_registry(connector_id, source_table, source_field);
CREATE INDEX idx_canonical_lookup ON mapping_registry(canonical_entity, canonical_field);
```

**No schema changes required** - table already exists and is properly structured!

---

## YAML Migration Strategy

### Migration Script: `scripts/migrate_yaml_to_db.py`

**Approach**: Idempotent ETL with tenant-scoped verification

**Steps**:
1. **Load YAML files** from `services/aam/canonical/mappings/`
2. **Parse mappings** (connector, source, canonical)
3. **Tenant scoping**: Use "default" tenant for initial migration
4. **Idempotent insert**: Use `ON CONFLICT DO UPDATE`
5. **Verification**: Checksum validation (YAML count == DB count)
6. **Audit log**: Record migration timestamp, file checksums

**Idempotent Insert Pattern**:
```sql
INSERT INTO mapping_registry (
    connector_id, source_table, source_field, 
    canonical_entity, canonical_field, confidence
) VALUES ($1, $2, $3, $4, $5, $6)
ON CONFLICT (connector_id, source_table, source_field) 
DO UPDATE SET 
    canonical_entity = EXCLUDED.canonical_entity,
    canonical_field = EXCLUDED.canonical_field,
    confidence = EXCLUDED.confidence,
    updated_at = NOW();
```

**Verification Queries**:
```sql
-- Count YAML mappings
SELECT COUNT(*) FROM mapping_registry WHERE connector_id = 'salesforce';

-- Checksum validation
SELECT md5(string_agg(source_field || canonical_field, ',' ORDER BY source_field))
FROM mapping_registry WHERE connector_id = 'salesforce';
```

**Rollback Plan**:
- Keep YAML files as read-only backups until cutover validation complete
- Dual-read mode allows fallback to YAML if DB has issues

---

## Feature Flag Strategy

### Flag: `USE_DCL_MAPPING_REGISTRY`

**Type**: Redis-backed boolean flag with percentage rollout  
**Scope**: Per-tenant or global  
**Default**: `false` (uses AAM YAML during migration)

**Rollout Phases**:
1. **0% (Week 1)**: Migration only, flag=false, all use YAML
2. **10% (Week 2)**: Staging tenant uses DCL API, dual-logging enabled
3. **50% (Week 2)**: Half tenants use DCL API after validation
4. **100% (Week 3)**: All tenants use DCL API, YAML deprecated

**Implementation**:
```python
# In AAM connector
from shared.feature_flags import get_feature_flag

def get_field_mapping(connector, table, field):
    use_dcl = get_feature_flag("USE_DCL_MAPPING_REGISTRY", tenant_id)
    
    if use_dcl:
        # Call DCL API
        response = httpx.get(f"{DCL_URL}/mappings/{connector}/{table}/{field}")
        return response.json()
    else:
        # Fallback to YAML (legacy)
        return load_yaml_mapping(connector, table, field)
```

**Dual-Read Validation**:
```python
# During rollout, compare both sources
def get_field_mapping_with_validation(connector, table, field):
    dcl_result = call_dcl_api(connector, table, field)
    yaml_result = load_yaml_mapping(connector, table, field)
    
    if dcl_result != yaml_result:
        logger.warning(f"Mapping mismatch: {connector}.{table}.{field}")
        metrics.increment("mapping_mismatch")
    
    return dcl_result  # Use DCL as source of truth
```

---

## AAM Connector Integration

### Before (RACI Violation):
```python
# aam_hybrid/connectors/salesforce_adapter.py
class SalesforceAdapter:
    def __init__(self):
        # Loads YAML directly
        self.mappings = load_yaml("services/aam/canonical/mappings/salesforce.yaml")
    
    def transform_field(self, table, field, value):
        mapping = self.mappings.get(f"{table}.{field}")
        return {
            "entity": mapping["canonical_entity"],
            "field": mapping["canonical_field"],
            "value": value
        }
```

### After (RACI Compliant):
```python
# aam_hybrid/connectors/salesforce_adapter.py
class SalesforceAdapter:
    def __init__(self, dcl_client: DCLMappingClient):
        self.dcl_client = dcl_client  # Injected dependency
    
    def transform_field(self, table, field, value):
        # Request mapping decision from DCL
        mapping = self.dcl_client.get_mapping("salesforce", table, field)
        
        # AAM only executes transformation per DCL decision
        return {
            "entity": mapping["canonical_entity"],
            "field": mapping["canonical_field"],
            "value": value
        }
```

### DCL Client Library:
```python
# shared/dcl_mapping_client.py
class DCLMappingClient:
    def __init__(self, base_url: str, tenant_id: str):
        self.base_url = base_url
        self.tenant_id = tenant_id
        self.cache = Redis()  # Local cache
    
    def get_mapping(self, connector, table, field):
        # Check local cache first
        cache_key = f"mapping:{self.tenant_id}:{connector}:{table}:{field}"
        cached = self.cache.get(cache_key)
        if cached:
            return json.loads(cached)
        
        # Call DCL API
        response = httpx.get(
            f"{self.base_url}/dcl/mappings/{connector}/{table}/{field}",
            headers={"Authorization": f"Bearer {self.jwt_token}"}
        )
        
        if response.status_code == 200:
            mapping = response.json()
            self.cache.setex(cache_key, 300, json.dumps(mapping))  # 5 min TTL
            return mapping
        elif response.status_code == 404:
            raise MappingNotFoundError(f"No mapping for {connector}.{table}.{field}")
        else:
            response.raise_for_status()
```

---

## Testing Strategy

### 1. Contract Tests (RACI Boundary Enforcement)
```python
# tests/contract/test_aam_cannot_write_mappings.py
def test_aam_cannot_create_mappings():
    """AAM should NOT be able to write to mapping registry"""
    from aam_hybrid.core.canonical_processor import CanonicalProcessor
    
    processor = CanonicalProcessor()
    
    # AAM should not have write methods
    assert not hasattr(processor, 'create_mapping')
    assert not hasattr(processor, 'update_mapping')
    assert not hasattr(processor, 'delete_mapping')

def test_aam_must_use_dcl_client():
    """AAM connectors must use DCLMappingClient, not direct DB access"""
    from aam_hybrid.connectors.salesforce_adapter import SalesforceAdapter
    
    adapter = SalesforceAdapter()
    
    # Should have DCL client injected
    assert hasattr(adapter, 'dcl_client')
    assert isinstance(adapter.dcl_client, DCLMappingClient)
    
    # Should NOT have direct DB session
    assert not hasattr(adapter, 'db_session')
```

### 2. Integration Tests
```python
# tests/integration/test_dcl_mapping_api.py
@pytest.mark.integration
def test_end_to_end_mapping_flow():
    """Test full flow: DCL API → AAM connector → Canonical event"""
    # 1. Create mapping via DCL API
    response = client.post("/dcl/mappings", json={
        "connector_id": "test_connector",
        "source_table": "TestTable",
        "source_field": "test_field",
        "canonical_entity": "test_entity",
        "canonical_field": "test_canonical"
    })
    assert response.status_code == 201
    
    # 2. AAM connector requests mapping
    mapping = dcl_client.get_mapping("test_connector", "TestTable", "test_field")
    assert mapping["canonical_field"] == "test_canonical"
    
    # 3. AAM executes transformation
    result = adapter.transform_field("TestTable", "test_field", "test_value")
    assert result["field"] == "test_canonical"
```

### 3. Performance Tests
```python
# tests/performance/test_dcl_api_latency.py
def test_dcl_mapping_api_latency():
    """Ensure DCL API response < 50ms P95"""
    latencies = []
    
    for _ in range(1000):
        start = time.time()
        dcl_client.get_mapping("salesforce", "Opportunity", "Amount")
        latencies.append((time.time() - start) * 1000)
    
    p95 = np.percentile(latencies, 95)
    assert p95 < 50, f"P95 latency {p95}ms exceeds 50ms threshold"

def test_cache_hit_rate():
    """Ensure >90% cache hit rate for repeated lookups"""
    hits = 0
    total = 1000
    
    for _ in range(total):
        mapping = dcl_client.get_mapping("salesforce", "Opportunity", "Amount")
        if dcl_client.cache.get(cache_key):
            hits += 1
    
    hit_rate = hits / total
    assert hit_rate > 0.9, f"Cache hit rate {hit_rate} below 90%"
```

---

## Migration Execution Plan

### Week 1: Infrastructure
- **Day 1-2**: Build DCL mapping API endpoints (P1.2)
- **Day 3-4**: Create migration script (P1.3)
- **Day 5**: Implement feature flag (P1.4)

### Week 2: Integration & Validation
- **Day 1-2**: Wire AAM connectors to DCL API (P1.5)
- **Day 3**: Contract tests (P1.6)
- **Day 4**: Integration tests (P1.7)
- **Day 5**: Performance validation (P1.8)

### Week 3: Rollout & Cutover
- **Day 1**: Enable flag 10% (staging)
- **Day 2-3**: Dual-read parity checks (P1.9)
- **Day 4**: Enable flag 100% (production)
- **Day 5**: Deprecate YAML, remove AAM mapping code (P1.10)

---

## Success Criteria

**P1 Complete When**:
1. ✅ DCL mapping API operational with <50ms P95 latency
2. ✅ All YAML mappings migrated to PostgreSQL with checksum validation
3. ✅ AAM connectors successfully calling DCL API (no YAML loading)
4. ✅ Feature flag enabled 100%, zero mapping mismatches
5. ✅ Contract tests passing (AAM cannot write mappings)
6. ✅ Integration tests passing (end-to-end flow works)
7. ✅ Performance validated (no regression from YAML loading)
8. ✅ YAML files deprecated, AAM mapping code removed

**RACI Compliance**:
- ✅ DCL owns mapping registry storage (Accountable)
- ✅ DCL owns mapping decisions (Accountable)
- ✅ AAM only executes transformations (Responsible)
- ✅ Clear API boundary enforces separation

---

## Rollback Plan

**If issues discovered during rollout**:
1. Set `USE_DCL_MAPPING_REGISTRY` flag to `false`
2. AAM immediately falls back to YAML (read-only backups)
3. Investigate DCL API issues
4. Fix and re-enable flag

**Data Safety**:
- YAML files retained as read-only backups until 30 days post-cutover
- PostgreSQL migration is idempotent (can re-run safely)
- Dual-read validation catches discrepancies before full cutover

---

## Post-P1 Readiness for P2

**After P1 Complete**:
- DCL mapping registry API proven at scale
- AAM connectors successfully using DCL API
- Performance validated (<50ms latency)
- RACI boundary enforced via contract tests

**P2 Prerequisites Met**:
- ✅ DCL API infrastructure operational
- ✅ AAM→DCL API call pattern established
- ✅ Feature flag pattern proven
- ✅ Testing framework validated

**Ready to Start**: P2 (Consolidate RAG Intelligence in DCL)

---

**END OF DESIGN DOCUMENT**
