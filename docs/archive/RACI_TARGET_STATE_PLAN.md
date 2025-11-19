# RACI Target State Remediation Plan
## Architect-Reviewed Implementation Roadmap

**Version:** 1.0  
**Date:** November 18, 2025  
**Status:** ARCHITECT APPROVED  
**Methodology:** Correctness First → Reliability → Speed → Scale

---

## Executive Summary

**Current State**: 54% RACI compliant, P1 infrastructure operational but untested  
**Target State**: 100% RACI compliant, production-ready, DCL owns all intelligence/mapping decisions  
**Strategy**: Four-phase remediation prioritizing correctness validation, intelligence migration, reliability hardening, production rollout

### Critical Findings from Architect Review

**Phase 1 Blockers (P0)**:
- Contract/integration/performance tests completely absent
- Dual-read parity validation not executed
- Feature flag at 0% (no production rollout)
- YAML files and AAM mapping code still active
- **SECURITY**: POST /dcl/mappings lacks admin authorization + cache invalidation

**RACI Violations (5 capabilities)**:
- LLM-powered mapping proposals (AAM → DCL)
- RAG mapping lookup (AAM → DCL)
- Confidence scoring (AAM → DCL)
- Drift repair proposals (AAM → DCL)
- Mapping approval workflow (AAM → DCL)

**Reliability Gaps**:
- No production observability for DCL registry path
- No error budget guardrails for rollout
- Rollback plan not formalized
- Load/performance baselines missing

---

## Remediation Architecture

### Four-Phase Program Structure

```
PHASE 1: Correctness Validation (P0 - Critical)
├── Complete P1 testing infrastructure
├── Fix security gaps (admin auth, cache invalidation)
├── Execute dual-read validation
├── Staged rollout (10% → 100%)
└── YAML deprecation and cutover

PHASE 2: Intelligence Migration (P0 - Critical)
├── Move LLM proposals to DCL
├── Move RAG lookup to DCL
├── Move confidence scoring to DCL
├── Move drift repair to DCL
└── Implement mapping approval workflow

PHASE 3: Reliability Hardening (High Priority)
├── Production observability
├── Error budget & SLO monitoring
├── Rollback automation
├── Load testing & capacity planning
└── Cache warming strategies

PHASE 4: Production Rollout (High Priority)
├── 100% DCL cutover validation
├── Remove legacy AAM mapping code
├── Archive YAML files (read-only)
├── Update documentation
└── Final RACI compliance audit
```

---

## PHASE 1: Correctness Validation
**Priority**: P0 (Critical Blocker)  
**Objective**: Complete P1 foundation with full test coverage, security fixes, and production rollout  
**Dependencies**: None (can start immediately)

### 1.1: Security & Control Fixes (P0 - Critical)

**Tasks**:
- **Admin Authorization for POST /dcl/mappings**
  - Implement `require_admin()` dependency in FastAPI
  - Check `current_user.is_admin` before allowing writes
  - Return 403 Forbidden for non-admin users
  - Add audit logging for all mapping write operations
  
- **Cache Invalidation on Write**
  - Invalidate Redis cache when mappings created/updated
  - Clear cache keys matching pattern: `mapping:{tenant_id}:{connector}:*`
  - Add cache invalidation to POST /dcl/mappings response
  - Publish Redis pub/sub event for cross-worker invalidation

**Success Criteria**:
- ✅ Non-admin users receive 403 on POST /dcl/mappings
- ✅ Admin users can create/update mappings with audit log entry
- ✅ Cache invalidated within 1 second of write
- ✅ All workers receive invalidation event via pub/sub

**Files to Modify**:
- `app/dcl_engine/routers/mappings.py` (add admin check)
- `app/security.py` (add `require_admin()` dependency)
- `app/models.py` (ensure User.is_admin field exists)

**Blockers**: None

---

### 1.2: Contract Tests - RACI Boundary Enforcement (P0)

**Tasks**:
- **Create test directory structure**
  - `tests/contract/test_aam_raci_boundaries.py`
  - `tests/contract/test_dcl_ownership.py`
  
- **Test: AAM Cannot Write Mappings**
  ```python
  def test_aam_cannot_create_mappings():
      """AAM should not have write methods to mapping registry"""
      from aam_hybrid.core.canonical_processor import CanonicalProcessor
      processor = CanonicalProcessor()
      assert not hasattr(processor, 'create_mapping')
      assert not hasattr(processor, 'update_mapping')
      assert not hasattr(processor, 'delete_mapping')
  ```

- **Test: AAM Must Use DCL Client**
  ```python
  def test_aam_must_use_dcl_client():
      """AAM connectors must use DCLMappingClient, not direct DB"""
      from services.aam.canonical.mapping_registry import mapping_registry
      # Verify mapping_registry uses DCLMappingClient
      assert hasattr(mapping_registry, 'dcl_client')
      # Verify no direct DB session access
      assert not hasattr(mapping_registry, 'db_session')
  ```

- **Test: DCL Owns Mapping Registry Storage**
  ```python
  def test_dcl_owns_mapping_storage():
      """Only DCL should have write access to field_mappings table"""
      from app.models import FieldMapping
      from sqlalchemy import inspect
      # Verify table exists in DCL schema
      assert FieldMapping.__tablename__ == 'field_mappings'
      # Verify DCL API is only write path
      assert POST_DCL_MAPPINGS_ENDPOINT_EXISTS
  ```

**Success Criteria**:
- ✅ 3/3 contract tests passing
- ✅ Tests fail if AAM gains write access to mapping registry
- ✅ Tests fail if AAM bypasses DCL client

**Dependencies**: None

**Blockers**: None

---

### 1.3: Integration Tests - End-to-End Flow (P0)

**Tasks**:
- **Create test file**: `tests/integration/test_dcl_aam_mapping_flow.py`

- **Test: DCL API Returns Correct Mapping**
  ```python
  @pytest.mark.integration
  def test_dcl_api_returns_mapping(client, db_session):
      """Test DCL API endpoint returns correct mapping"""
      response = client.get(
          "/dcl/mappings/salesforce/opportunity/Amount",
          headers={"Authorization": f"Bearer {test_jwt}"}
      )
      assert response.status_code == 200
      data = response.json()
      assert data["canonical_field"] == "amount"
      assert data["confidence"] >= 0.9
  ```

- **Test: AAM Uses DCL Mapping for Transformation**
  ```python
  @pytest.mark.integration
  def test_aam_transforms_using_dcl_mapping(db_session):
      """Test AAM connector uses DCL mapping for transformation"""
      from services.aam.canonical.mapping_registry import mapping_registry
      
      # Enable DCL API via feature flag
      set_feature_flag('USE_DCL_MAPPING_REGISTRY', True, 'default')
      
      # Get mapping (should call DCL API)
      mapping = mapping_registry.get_mapping('salesforce', 'opportunity', 'default')
      
      assert mapping is not None
      assert 'amount' in mapping['fields']
      assert mapping['fields']['amount']['canonical'] == 'amount'
  ```

- **Test: End-to-End Canonical Transformation**
  ```python
  @pytest.mark.integration
  def test_e2e_canonical_transformation(db_session):
      """Test complete flow: DCL API → AAM → Canonical event"""
      # 1. Create mapping via DCL API
      create_response = admin_client.post("/dcl/mappings", json={
          "connector_id": "test_connector",
          "source_table": "test_table",
          "source_field": "test_field",
          "canonical_entity": "test_entity",
          "canonical_field": "test_canonical"
      })
      assert create_response.status_code == 201
      
      # 2. AAM fetches mapping from DCL
      mapping = dcl_client.get_mapping("test_connector", "test_table", "test_field")
      assert mapping["canonical_field"] == "test_canonical"
      
      # 3. AAM executes transformation
      raw_event = {"test_field": "test_value"}
      canonical_event = transform_event(raw_event, mapping)
      assert canonical_event["test_canonical"] == "test_value"
  ```

**Success Criteria**:
- ✅ 3/3 integration tests passing
- ✅ DCL API returns mappings within <100ms
- ✅ AAM successfully transforms events using DCL mappings
- ✅ Zero errors in end-to-end flow

**Dependencies**: Contract tests passing, admin auth implemented

**Blockers**: None

---

### 1.4: Performance Tests - Latency & Throughput (P0)

**Tasks**:
- **Create test directory**: `tests/performance/`
- **Create test file**: `tests/performance/test_dcl_registry_performance.py`

- **Test: DCL API Latency P95 < 50ms**
  ```python
  def test_dcl_api_latency_p95():
      """Ensure DCL API P95 latency < 50ms"""
      latencies = []
      for _ in range(1000):
          start = time.time()
          response = client.get("/dcl/mappings/salesforce/opportunity/Amount")
          latencies.append((time.time() - start) * 1000)
      
      p50 = np.percentile(latencies, 50)
      p95 = np.percentile(latencies, 95)
      p99 = np.percentile(latencies, 99)
      
      assert p95 < 50, f"P95 latency {p95}ms exceeds 50ms threshold"
      print(f"Latency - P50: {p50}ms, P95: {p95}ms, P99: {p99}ms")
  ```

- **Test: Cache Hit Rate > 90%**
  ```python
  def test_cache_hit_rate():
      """Ensure >90% cache hit rate for repeated lookups"""
      # Warm cache
      client.get("/dcl/mappings/salesforce/opportunity/Amount")
      
      hits = 0
      total = 1000
      for _ in range(total):
          start = time.time()
          client.get("/dcl/mappings/salesforce/opportunity/Amount")
          duration = (time.time() - start) * 1000
          if duration < 5:  # Cache hits are <5ms
              hits += 1
      
      hit_rate = hits / total
      assert hit_rate > 0.9, f"Cache hit rate {hit_rate:.1%} below 90%"
  ```

- **Test: Concurrent Request Handling**
  ```python
  def test_concurrent_requests():
      """Test 100 concurrent requests without errors"""
      import concurrent.futures
      
      def make_request():
          response = client.get("/dcl/mappings/salesforce/opportunity/Amount")
          return response.status_code
      
      with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
          futures = [executor.submit(make_request) for _ in range(100)]
          results = [f.result() for f in futures]
      
      assert all(r == 200 for r in results), "Some requests failed"
  ```

- **Test: Performance Comparison (DCL API vs YAML)**
  ```python
  def test_dcl_vs_yaml_performance():
      """Compare DCL API performance to YAML loading baseline"""
      # Measure DCL API
      dcl_times = []
      for _ in range(100):
          start = time.time()
          mapping = dcl_client.get_mapping('salesforce', 'opportunity', 'default')
          dcl_times.append(time.time() - start)
      
      # Measure YAML loading
      yaml_times = []
      for _ in range(100):
          start = time.time()
          mapping = load_yaml_mapping('salesforce', 'opportunity')
          yaml_times.append(time.time() - start)
      
      dcl_avg = np.mean(dcl_times) * 1000
      yaml_avg = np.mean(yaml_times) * 1000
      
      print(f"DCL API: {dcl_avg:.2f}ms, YAML: {yaml_avg:.2f}ms")
      assert dcl_avg < yaml_avg * 2, "DCL API should not be >2x slower than YAML"
  ```

**Success Criteria**:
- ✅ P95 latency < 50ms for DCL API
- ✅ Cache hit rate > 90% for repeated queries
- ✅ 100 concurrent requests succeed without errors
- ✅ DCL API performance within 2x of YAML baseline

**Dependencies**: Integration tests passing

**Blockers**: None

---

### 1.5: Dual-Read Validation - Parity Checks (P0)

**Tasks**:
- **Enable Dual-Read Mode**
  - Set `DUAL_READ_VALIDATE=true` environment variable
  - Ensure both DCL API and YAML loaded simultaneously
  
- **Execute Parity Checks**
  - Run AAM connectors with dual-read enabled
  - Compare DCL API results vs YAML results for every mapping lookup
  - Log mismatches with details (connector, table, field, expected, actual)
  - Generate mismatch report with statistics

- **Mismatch Analysis Script**
  ```python
  # scripts/analyze_mapping_mismatches.py
  def analyze_mismatches(log_file):
      """Parse dual-read logs and identify mismatches"""
      mismatches = []
      with open(log_file) as f:
          for line in f:
              if 'Mapping mismatch' in line:
                  mismatches.append(parse_mismatch(line))
      
      report = {
          'total_lookups': count_total_lookups(log_file),
          'mismatches': len(mismatches),
          'mismatch_rate': len(mismatches) / count_total_lookups(log_file),
          'by_connector': group_by_connector(mismatches),
          'by_field': group_by_field(mismatches)
      }
      return report
  ```

- **Fix Identified Mismatches**
  - Investigate root cause of each mismatch
  - Update database mappings or YAML (whichever is incorrect)
  - Re-run dual-read validation
  - Repeat until zero mismatches

**Success Criteria**:
- ✅ Zero mapping mismatches observed across 10,000+ lookups
- ✅ Dual-read validation runs without errors
- ✅ Mismatch report shows 100% parity
- ✅ All connectors validated (Salesforce, MongoDB, FileSource, etc.)

**Dependencies**: Contract tests + integration tests passing

**Blockers**: None

---

### 1.6: Staged Rollout - Feature Flag Activation (P0)

**Tasks**:
- **Stage 1: 10% Rollout (Canary)**
  - Set `USE_DCL_MAPPING_REGISTRY` flag to 10%
  - Monitor error rates, latency, cache hit rate
  - Run for sustained period (observe for regressions)
  - Validate no increase in errors or latency degradation

- **Stage 2: 25% Rollout**
  - Increase flag to 25%
  - Continue monitoring
  - Validate performance remains stable

- **Stage 3: 50% Rollout**
  - Increase flag to 50%
  - Load testing at scale
  - Validate cache effectiveness

- **Stage 4: 100% Rollout**
  - Increase flag to 100%
  - All tenants using DCL API exclusively
  - YAML loading deprecated (but still available for emergency rollback)

- **Monitoring Dashboard**
  ```python
  # Track key metrics during rollout:
  - DCL API request rate
  - DCL API error rate
  - DCL API P50/P95/P99 latency
  - Cache hit rate
  - Mapping not found rate (404s)
  - Dual-read mismatch rate (should be 0)
  ```

**Rollback Criteria** (trigger immediate rollback if):
- Error rate increases >5%
- P95 latency increases >100ms
- Cache hit rate drops <80%
- Any mapping mismatches detected

**Success Criteria**:
- ✅ 100% feature flag enabled in production
- ✅ Zero error rate increase from baseline
- ✅ P95 latency remains <50ms
- ✅ Cache hit rate remains >90%
- ✅ Zero mapping mismatches observed

**Dependencies**: Dual-read validation complete with zero mismatches

**Blockers**: None

---

### 1.7: YAML Deprecation & Cutover (P0)

**Tasks**:
- **Archive YAML Files**
  - Create `services/aam/canonical/mappings/archive/` directory
  - Move all YAML files to archive with timestamp
  - Add README explaining deprecation and emergency restore procedure
  - Mark as read-only (remove write permissions)

- **Remove YAML Loading Code**
  - Remove `load_yaml_mapping()` function from AAM
  - Remove YAML parsing logic from `mapping_registry.py`
  - Remove YAML file path constants
  - Update to DCL API calls only

- **Update Configuration**
  - Remove `DUAL_READ_VALIDATE` environment variable
  - Remove YAML fallback logic
  - Update `.env.example` to remove YAML references

- **Update Documentation**
  - Mark YAML mapping files as DEPRECATED in all docs
  - Update API documentation to reference DCL API only
  - Create migration guide for future connector additions
  - Document emergency YAML restore procedure (rollback plan)

**Success Criteria**:
- ✅ YAML files archived and read-only
- ✅ AAM code has zero YAML references
- ✅ All connectors operational with DCL API only
- ✅ Documentation updated with deprecation notices
- ✅ Emergency rollback procedure documented and tested

**Dependencies**: 100% feature flag rollout successful

**Blockers**: None

---

### 1.8: Unique Constraint Deployment (High Priority)

**Tasks**:
- **Add Unique Constraint to Database**
  ```sql
  -- Prevent duplicate mappings at database level
  ALTER TABLE field_mappings
  ADD CONSTRAINT unique_mapping_per_tenant
  UNIQUE (tenant_id, connector_id, LOWER(source_table), source_field);
  ```

- **Test Constraint**
  - Attempt to insert duplicate mapping (should fail with constraint violation)
  - Verify error message is clear
  - Verify existing data doesn't violate constraint

- **Handle Constraint Violations in Code**
  - Update POST /dcl/mappings to handle IntegrityError
  - Return 409 Conflict with clear error message
  - Suggest using PUT for updates instead of duplicate POST

**Success Criteria**:
- ✅ Unique constraint deployed to production
- ✅ Duplicate inserts rejected at database level
- ✅ API returns 409 Conflict for duplicates with helpful message
- ✅ Zero data integrity violations

**Dependencies**: YAML cutover complete (ensures no more duplicates)

**Blockers**: None

---

## PHASE 2: Intelligence Migration
**Priority**: P0 (Critical for RACI Compliance)  
**Objective**: Move LLM proposals, RAG lookup, confidence scoring, drift repair from AAM to DCL  
**Dependencies**: Phase 1 complete (DCL mapping registry proven operational)

### 2.1: Design Intelligence Service Architecture (High Priority)

**Tasks**:
- **Design DCL Intelligence Service**
  - Create `app/dcl_engine/services/intelligence/` module
  - Define service interfaces for:
    - `LLMProposalService` - LLM-powered mapping suggestions
    - `RAGLookupService` - RAG-based mapping retrieval
    - `ConfidenceScoringService` - Mapping confidence calculation
    - `DriftRepairService` - Schema drift auto-repair proposals
    - `MappingApprovalService` - Human-in-the-loop workflow

- **Define API Contracts**
  ```python
  # POST /dcl/intelligence/propose-mapping
  # Request: { connector, source_table, source_field, sample_values }
  # Response: { canonical_field, confidence, reasoning, alternatives }
  
  # POST /dcl/intelligence/calculate-confidence
  # Request: { mapping_id, validation_results }
  # Response: { confidence_score, factors, recommendations }
  
  # POST /dcl/intelligence/repair-drift
  # Request: { drift_event_id, schema_diff }
  # Response: { repair_proposal, confidence, estimated_impact }
  ```

- **Design Data Flow**
  ```
  AAM Connector (detects drift/needs mapping)
      ↓ HTTP Request
  DCL Intelligence API
      ↓ Query
  RAG Vector Store (Pinecone/pgvector)
      ↓ Fallback
  LLM Service (Gemini)
      ↓ Store Result
  PostgreSQL (mapping_proposals table)
      ↓ Return
  AAM Connector (applies proposal)
  ```

**Success Criteria**:
- ✅ Intelligence service architecture documented
- ✅ API contracts defined with request/response schemas
- ✅ Data flow diagrams created
- ✅ Database schema designed for proposals/approvals

**Dependencies**: Phase 1 complete

**Blockers**: None

---

### 2.2: Migrate LLM Proposal Logic to DCL (P0)

**Tasks**:
- **Extract LLM Logic from AAM**
  - Identify all LLM calls in `aam_hybrid/core/canonical_processor.py`
  - Extract to `app/dcl_engine/services/intelligence/llm_proposal_service.py`
  - Remove LLM dependencies from AAM

- **Implement DCL LLM Service**
  ```python
  # app/dcl_engine/services/intelligence/llm_proposal_service.py
  class LLMProposalService:
      def __init__(self, llm_client, rag_service):
          self.llm = llm_client
          self.rag = rag_service
      
      async def propose_mapping(
          self,
          connector: str,
          source_table: str,
          source_field: str,
          sample_values: List[Any],
          tenant_id: str
      ) -> MappingProposal:
          # 1. Check RAG first
          rag_result = await self.rag.lookup_mapping(
              connector, source_table, source_field, tenant_id
          )
          if rag_result and rag_result.confidence > 0.9:
              return rag_result
          
          # 2. Fallback to LLM
          prompt = self._build_prompt(connector, source_table, source_field, sample_values)
          llm_response = await self.llm.generate(prompt)
          
          # 3. Parse and validate
          proposal = self._parse_llm_response(llm_response)
          proposal.confidence = self._calculate_confidence(proposal)
          
          # 4. Store in database
          await self._store_proposal(proposal, tenant_id)
          
          return proposal
  ```

- **Create DCL API Endpoint**
  ```python
  # app/dcl_engine/routers/intelligence.py
  @router.post("/intelligence/propose-mapping")
  async def propose_mapping(
      request: ProposeRequest,
      current_user: User = Depends(get_current_user),
      db: Session = Depends(get_db)
  ):
      service = LLMProposalService(llm_client, rag_service)
      proposal = await service.propose_mapping(
          request.connector,
          request.source_table,
          request.source_field,
          request.sample_values,
          current_user.tenant_id
      )
      return proposal
  ```

- **Update AAM to Call DCL API**
  ```python
  # services/aam/canonical/mapping_registry.py (updated)
  def get_or_propose_mapping(self, connector, table, field):
      # Try to get existing mapping
      mapping = self.get_mapping(connector, table, 'default')
      if mapping and field in mapping.get('fields', {}):
          return mapping['fields'][field]
      
      # Call DCL API for proposal
      response = httpx.post(
          f"{DCL_BASE_URL}/dcl/intelligence/propose-mapping",
          json={
              "connector": connector,
              "source_table": table,
              "source_field": field,
              "sample_values": self._get_sample_values(table, field)
          }
      )
      return response.json()
  ```

**Success Criteria**:
- ✅ LLM proposal logic fully migrated to DCL
- ✅ AAM has zero LLM client dependencies
- ✅ DCL API endpoint operational and tested
- ✅ AAM successfully calls DCL for proposals
- ✅ Proposal quality unchanged from pre-migration

**Dependencies**: Phase 2.1 design complete

**Blockers**: None

---

### 2.3: Migrate RAG Lookup to DCL (P0)

**Tasks**:
- **Extract RAG Logic from AAM**
  - Identify RAG vector search in AAM
  - Move to `app/dcl_engine/services/intelligence/rag_lookup_service.py`
  - Remove RAG dependencies from AAM

- **Implement DCL RAG Service**
  ```python
  # app/dcl_engine/services/intelligence/rag_lookup_service.py
  class RAGLookupService:
      def __init__(self, vector_store):
          self.vector_store = vector_store  # pgvector or Pinecone
      
      async def lookup_mapping(
          self,
          connector: str,
          source_table: str,
          source_field: str,
          tenant_id: str
      ) -> Optional[MappingProposal]:
          # 1. Build query embedding
          query = f"{connector}.{source_table}.{source_field}"
          embedding = await self._embed(query)
          
          # 2. Vector similarity search
          results = await self.vector_store.similarity_search(
              embedding,
              tenant_id=tenant_id,
              top_k=5
          )
          
          # 3. Filter and rank
          if results and results[0].similarity > 0.85:
              return self._convert_to_proposal(results[0])
          
          return None
  ```

- **Create RAG API Endpoint**
  ```python
  # app/dcl_engine/routers/intelligence.py
  @router.get("/intelligence/rag-lookup/{connector}/{source_table}/{source_field}")
  async def rag_lookup(
      connector: str,
      source_table: str,
      source_field: str,
      current_user: User = Depends(get_current_user)
  ):
      service = RAGLookupService(vector_store)
      result = await service.lookup_mapping(
          connector, source_table, source_field, current_user.tenant_id
      )
      if not result:
          raise HTTPException(404, "No RAG result found")
      return result
  ```

- **Update AAM to Use DCL RAG**
  - Remove RAG client from AAM
  - Call DCL RAG API instead
  - Handle 404 gracefully (fallback to LLM proposal)

**Success Criteria**:
- ✅ RAG lookup fully migrated to DCL
- ✅ AAM has zero RAG/vector store dependencies
- ✅ DCL RAG API operational and tested
- ✅ RAG lookup quality unchanged from pre-migration
- ✅ Vector store access consolidated in DCL

**Dependencies**: Phase 2.2 complete

**Blockers**: None

---

### 2.4: Migrate Confidence Scoring to DCL (P0)

**Tasks**:
- **Extract Confidence Logic from AAM**
  - Identify confidence calculation in AAM
  - Move to `app/dcl_engine/services/intelligence/confidence_service.py`

- **Implement DCL Confidence Service**
  ```python
  # app/dcl_engine/services/intelligence/confidence_service.py
  class ConfidenceScoringService:
      def calculate_confidence(
          self,
          mapping: FieldMapping,
          validation_results: Dict[str, Any]
      ) -> ConfidenceScore:
          factors = {
              'source_quality': self._assess_source_quality(mapping),
              'usage_frequency': self._assess_usage(mapping),
              'validation_success': validation_results.get('success_rate', 0),
              'human_approval': mapping.approval_status == 'approved',
              'rag_similarity': validation_results.get('rag_similarity', 0)
          }
          
          # Weighted average
          weights = {
              'source_quality': 0.2,
              'usage_frequency': 0.15,
              'validation_success': 0.3,
              'human_approval': 0.25,
              'rag_similarity': 0.1
          }
          
          score = sum(factors[k] * weights[k] for k in factors)
          
          return ConfidenceScore(
              score=score,
              factors=factors,
              recommendations=self._generate_recommendations(factors)
          )
  ```

- **Create Confidence API Endpoint**
  ```python
  @router.post("/intelligence/calculate-confidence")
  async def calculate_confidence(
      request: ConfidenceRequest,
      current_user: User = Depends(get_current_user),
      db: Session = Depends(get_db)
  ):
      mapping = db.query(FieldMapping).filter_by(id=request.mapping_id).first()
      service = ConfidenceScoringService()
      result = service.calculate_confidence(mapping, request.validation_results)
      
      # Update mapping confidence in database
      mapping.confidence = result.score
      db.commit()
      
      return result
  ```

**Success Criteria**:
- ✅ Confidence scoring fully migrated to DCL
- ✅ AAM uses DCL API for confidence calculations
- ✅ Confidence scores stored in `field_mappings` table
- ✅ Confidence calculation quality unchanged

**Dependencies**: Phase 2.3 complete

**Blockers**: None

---

### 2.5: Migrate Drift Repair to DCL (P0)

**Tasks**:
- **Extract Drift Repair Logic from AAM**
  - Identify drift detection and repair in AAM
  - Move repair proposal logic to DCL (keep detection in AAM)
  - AAM detects drift, DCL proposes repair

- **Implement DCL Drift Repair Service**
  ```python
  # app/dcl_engine/services/intelligence/drift_repair_service.py
  class DriftRepairService:
      async def propose_repair(
          self,
          drift_event: DriftEvent,
          schema_diff: SchemaDiff,
          tenant_id: str
      ) -> RepairProposal:
          # 1. Analyze drift impact
          impact = self._analyze_impact(drift_event, schema_diff)
          
          # 2. Generate repair proposals (multiple options)
          proposals = []
          
          # Option 1: Update existing mapping
          if schema_diff.change_type == 'field_renamed':
              proposals.append({
                  'type': 'update_mapping',
                  'action': 'rename',
                  'old_field': schema_diff.old_field,
                  'new_field': schema_diff.new_field,
                  'confidence': 0.9
              })
          
          # Option 2: Create new mapping
          if schema_diff.change_type == 'field_added':
              llm_proposal = await self.llm_service.propose_mapping(...)
              proposals.append({
                  'type': 'create_mapping',
                  'mapping': llm_proposal,
                  'confidence': llm_proposal.confidence
              })
          
          # Option 3: Deprecate old mapping
          if schema_diff.change_type == 'field_removed':
              proposals.append({
                  'type': 'deprecate_mapping',
                  'field': schema_diff.removed_field,
                  'confidence': 1.0
              })
          
          # 3. Rank proposals by confidence
          best_proposal = max(proposals, key=lambda p: p['confidence'])
          
          return RepairProposal(
              proposals=proposals,
              recommended=best_proposal,
              estimated_impact=impact
          )
  ```

- **Create Drift Repair API Endpoint**
  ```python
  @router.post("/intelligence/repair-drift")
  async def repair_drift(
      request: DriftRepairRequest,
      current_user: User = Depends(get_current_user)
  ):
      service = DriftRepairService(llm_service, rag_service)
      proposal = await service.propose_repair(
          request.drift_event,
          request.schema_diff,
          current_user.tenant_id
      )
      return proposal
  ```

- **Update AAM Drift Flow**
  ```python
  # AAM: Detect drift (remains in AAM - correct per RACI)
  def detect_drift(self, connector, table):
      current_schema = self.scan_schema(connector, table)
      stored_schema = self.get_stored_schema(connector, table)
      diff = self.compare_schemas(current_schema, stored_schema)
      
      if diff.has_changes:
          # Call DCL for repair proposal
          repair = httpx.post(
              f"{DCL_BASE_URL}/dcl/intelligence/repair-drift",
              json={"drift_event": ..., "schema_diff": diff}
          ).json()
          
          return repair
  ```

**Success Criteria**:
- ✅ Drift repair proposals fully migrated to DCL
- ✅ AAM detects drift (correct per RACI), DCL proposes repairs
- ✅ Repair quality unchanged from pre-migration
- ✅ HITL workflow integrated with repair proposals

**Dependencies**: Phase 2.4 complete

**Blockers**: None

---

### 2.6: Implement Mapping Approval Workflow (High Priority)

**Tasks**:
- **Design Approval State Machine**
  ```
  States:
  - PROPOSED → (human review) → APPROVED / REJECTED
  - APPROVED → (validation) → ACTIVE
  - ACTIVE → (drift) → NEEDS_REVIEW
  - REJECTED → (updated) → PROPOSED
  ```

- **Create Approval Database Schema**
  ```sql
  CREATE TABLE mapping_approvals (
      id UUID PRIMARY KEY,
      mapping_id UUID REFERENCES field_mappings(id),
      tenant_id UUID NOT NULL,
      proposal_reason TEXT,
      reviewer_id UUID REFERENCES users(id),
      status VARCHAR(50),  -- proposed, approved, rejected
      reviewed_at TIMESTAMP,
      review_notes TEXT,
      created_at TIMESTAMP DEFAULT NOW()
  );
  ```

- **Implement Approval Service**
  ```python
  # app/dcl_engine/services/intelligence/approval_service.py
  class MappingApprovalService:
      async def submit_for_approval(
          self,
          mapping: FieldMapping,
          reason: str,
          tenant_id: str
      ) -> ApprovalRequest:
          approval = MappingApproval(
              mapping_id=mapping.id,
              tenant_id=tenant_id,
              proposal_reason=reason,
              status='proposed'
          )
          db.add(approval)
          db.commit()
          
          # Notify reviewers
          await self._notify_reviewers(approval)
          
          return approval
      
      async def approve_mapping(
          self,
          approval_id: UUID,
          reviewer: User,
          notes: str
      ):
          approval = db.query(MappingApproval).get(approval_id)
          approval.status = 'approved'
          approval.reviewer_id = reviewer.id
          approval.reviewed_at = datetime.utcnow()
          approval.review_notes = notes
          
          # Activate mapping
          mapping = approval.mapping
          mapping.status = 'active'
          mapping.confidence = 1.0  # Human approval = high confidence
          
          db.commit()
          
          # Invalidate cache
          await self._invalidate_cache(mapping)
  ```

- **Create Approval API Endpoints**
  ```python
  POST /dcl/approvals/submit - Submit mapping for approval
  GET /dcl/approvals/pending - List pending approvals
  POST /dcl/approvals/{id}/approve - Approve mapping
  POST /dcl/approvals/{id}/reject - Reject mapping
  ```

**Success Criteria**:
- ✅ Approval workflow operational
- ✅ Human reviewers can approve/reject proposals
- ✅ Approved mappings auto-activate with high confidence
- ✅ Rejected mappings remain inactive

**Dependencies**: Phase 2.5 complete

**Blockers**: None

---

### 2.7: RACI Compliance Validation (P0)

**Tasks**:
- **Update Contract Tests**
  - Add tests verifying AAM has no LLM dependencies
  - Add tests verifying AAM has no RAG dependencies
  - Add tests verifying AAM has no confidence calculation logic
  - Add tests verifying AAM has no repair proposal logic

- **Run RACI Audit**
  ```python
  # scripts/audit_raci_compliance.py
  def audit_raci_compliance():
      violations = []
      
      # Check: AAM should not import LLM clients
      if check_imports('aam_hybrid/', ['openai', 'google.generativeai']):
          violations.append("AAM has LLM dependencies")
      
      # Check: AAM should not import vector stores
      if check_imports('aam_hybrid/', ['pinecone', 'pgvector']):
          violations.append("AAM has RAG dependencies")
      
      # Check: DCL should have intelligence services
      if not exists('app/dcl_engine/services/intelligence/'):
          violations.append("DCL missing intelligence services")
      
      return {
          'compliant': len(violations) == 0,
          'violations': violations
      }
  ```

- **Generate RACI Compliance Report**
  - Document current ownership of all 11 capabilities
  - Verify 100% alignment with RACI matrix
  - Create compliance certificate

**Success Criteria**:
- ✅ 11/11 RACI capabilities compliant (100%)
- ✅ Zero RACI violations detected by audit
- ✅ Contract tests enforce RACI boundaries
- ✅ Compliance report generated and approved

**Dependencies**: Phase 2.1-2.6 complete

**Blockers**: None

---

## PHASE 3: Reliability Hardening
**Priority**: High  
**Objective**: Production-grade observability, error budgets, rollback automation, load testing  
**Dependencies**: Phase 2 complete (intelligence fully migrated to DCL)

### 3.1: Production Observability (High Priority)

**Tasks**:
- **Structured Logging**
  ```python
  # Add structured logging to all DCL intelligence services
  import structlog
  
  logger = structlog.get_logger()
  
  logger.info(
      "mapping_lookup",
      connector=connector,
      source_table=table,
      source_field=field,
      tenant_id=tenant_id,
      cache_hit=cache_hit,
      latency_ms=duration * 1000
  )
  ```

- **Metrics Collection**
  ```python
  # Add Prometheus metrics
  from prometheus_client import Counter, Histogram, Gauge
  
  # Request metrics
  dcl_api_requests = Counter(
      'dcl_api_requests_total',
      'Total DCL API requests',
      ['endpoint', 'status', 'tenant_id']
  )
  
  # Latency metrics
  dcl_api_latency = Histogram(
      'dcl_api_latency_seconds',
      'DCL API latency',
      ['endpoint']
  )
  
  # Cache metrics
  dcl_cache_hit_rate = Gauge(
      'dcl_cache_hit_rate',
      'Cache hit rate',
      ['tenant_id']
  )
  ```

- **Distributed Tracing**
  ```python
  # Add OpenTelemetry tracing
  from opentelemetry import trace
  
  tracer = trace.get_tracer(__name__)
  
  @tracer.start_as_current_span("dcl_mapping_lookup")
  def get_mapping(connector, table, field):
      span = trace.get_current_span()
      span.set_attribute("connector", connector)
      span.set_attribute("source_table", table)
      # ... rest of logic
  ```

- **Create Monitoring Dashboard**
  - Grafana dashboard for DCL registry metrics
  - Alert on P95 latency > 50ms
  - Alert on error rate > 1%
  - Alert on cache hit rate < 80%

**Success Criteria**:
- ✅ All DCL API endpoints have structured logging
- ✅ Prometheus metrics exported from /metrics endpoint
- ✅ OpenTelemetry traces sent to collector
- ✅ Grafana dashboard operational with alerts

**Dependencies**: Phase 2 complete

**Blockers**: None

---

### 3.2: Error Budgets & SLO Monitoring (High Priority)

**Tasks**:
- **Define SLOs**
  ```yaml
  # DCL Mapping Registry SLOs
  slos:
    availability:
      target: 99.9%  # 43 minutes downtime per month
      error_budget: 0.1%
    
    latency:
      target: 50ms P95
      error_budget: 5% requests can exceed
    
    cache_hit_rate:
      target: 90%
      error_budget: 80% minimum
  ```

- **Implement Error Budget Tracking**
  ```python
  # Track error budget consumption
  class ErrorBudgetTracker:
      def __init__(self, slo_config):
          self.config = slo_config
          self.redis = get_redis_client()
      
      def record_request(self, endpoint, success, latency_ms):
          key = f"error_budget:{endpoint}:{date.today()}"
          
          # Track total requests
          self.redis.hincrby(key, 'total', 1)
          
          # Track failures
          if not success:
              self.redis.hincrby(key, 'failures', 1)
          
          # Track latency violations
          if latency_ms > self.config['latency']['target']:
              self.redis.hincrby(key, 'latency_violations', 1)
      
      def get_budget_status(self, endpoint):
          key = f"error_budget:{endpoint}:{date.today()}"
          total = int(self.redis.hget(key, 'total') or 0)
          failures = int(self.redis.hget(key, 'failures') or 0)
          
          error_rate = failures / total if total > 0 else 0
          budget_consumed = error_rate / self.config['availability']['error_budget']
          
          return {
              'budget_consumed_pct': budget_consumed * 100,
              'budget_remaining': 1 - budget_consumed,
              'should_halt_rollout': budget_consumed > 0.5  # >50% consumed
          }
  ```

- **Automated Rollout Control**
  - Pause rollout if error budget >50% consumed
  - Auto-rollback if error budget >90% consumed
  - Alert SRE team for manual review

**Success Criteria**:
- ✅ SLOs defined and documented
- ✅ Error budget tracking operational
- ✅ Automated rollout halt if budget exceeded
- ✅ SLO dashboard shows real-time budget status

**Dependencies**: Phase 3.1 complete

**Blockers**: None

---

### 3.3: Rollback Automation (High Priority)

**Tasks**:
- **Automated Rollback Script**
  ```python
  # scripts/rollback_dcl_registry.py
  def rollback_dcl_registry():
      """Emergency rollback to YAML mappings"""
      logger.warning("🚨 EXECUTING EMERGENCY ROLLBACK")
      
      # 1. Set feature flag to 0%
      set_feature_flag('USE_DCL_MAPPING_REGISTRY', False, 'all')
      
      # 2. Verify YAML files accessible
      assert os.path.exists('services/aam/canonical/mappings/archive/')
      
      # 3. Restore YAML files from archive
      restore_yaml_files()
      
      # 4. Restart AAM workers
      restart_workers()
      
      # 5. Verify AAM using YAML
      verify_yaml_mode()
      
      logger.info("✅ Rollback complete - system using YAML")
  ```

- **Rollback Playbook**
  ```markdown
  # DCL Registry Rollback Playbook
  
  ## Trigger Conditions
  - Error rate >5% above baseline
  - P95 latency >100ms for 5 minutes
  - Critical mapping failures detected
  - Data integrity violations
  
  ## Manual Rollback Steps
  1. Run: `python scripts/rollback_dcl_registry.py`
  2. Verify: Check AAM using YAML via logs
  3. Monitor: Watch error rates return to baseline
  4. Investigate: Root cause analysis of failure
  5. Fix: Address issues before re-enabling
  
  ## Automated Rollback
  - Monitoring system triggers rollback script
  - Pagerduty alert sent to on-call engineer
  - Post-mortem required before re-enabling
  ```

- **Rollback Testing**
  - Execute rollback in staging environment
  - Verify AAM immediately falls back to YAML
  - Verify zero data loss during rollback
  - Time rollback execution (should be <60 seconds)

**Success Criteria**:
- ✅ Rollback script tested in staging
- ✅ Rollback executes in <60 seconds
- ✅ Zero data loss during rollback
- ✅ Playbook documented and reviewed by SRE

**Dependencies**: Phase 3.2 complete

**Blockers**: None

---

### 3.4: Load Testing & Capacity Planning (High Priority)

**Tasks**:
- **Load Test Scenarios**
  ```python
  # tests/load/test_dcl_registry_load.py
  from locust import HttpUser, task, between
  
  class DCLMappingUser(HttpUser):
      wait_time = between(0.1, 0.5)
      
      @task(10)
      def get_common_mapping(self):
          """Most common query - high cache hit rate"""
          self.client.get("/dcl/mappings/salesforce/opportunity/Amount")
      
      @task(3)
      def get_uncommon_mapping(self):
          """Less common query - lower cache hit rate"""
          field = random.choice(['Email', 'Phone', 'Website'])
          self.client.get(f"/dcl/mappings/salesforce/account/{field}")
      
      @task(1)
      def list_mappings(self):
          """List endpoint - higher latency"""
          self.client.get("/dcl/mappings/salesforce?limit=100")
  ```

- **Execute Load Tests**
  - Baseline: 100 RPS (current production load)
  - Target: 1,000 RPS (10x capacity)
  - Peak: 5,000 RPS (50x capacity, Black Friday)
  - Sustained: Run 1,000 RPS for 1 hour (soak test)

- **Capacity Analysis**
  ```python
  # Analyze load test results
  def analyze_capacity(results):
      return {
          'max_rps_p95_under_50ms': results['max_rps_at_slo'],
          'cache_hit_rate_at_1k_rps': results['cache_hit_rate'],
          'error_rate_at_peak': results['error_rate_at_5k_rps'],
          'recommended_max_rps': results['max_rps_at_slo'] * 0.7,  # 70% headroom
          'scaling_recommendation': 'horizontal' if results['cpu_bound'] else 'vertical'
      }
  ```

- **Cache Warming Strategy**
  ```python
  # Pre-warm cache before rollout
  def warm_cache():
      """Pre-load most common mappings into Redis"""
      common_lookups = [
          ('salesforce', 'opportunity', 'Amount'),
          ('salesforce', 'opportunity', 'StageName'),
          ('salesforce', 'account', 'Name'),
          # ... top 100 queries
      ]
      
      for connector, table, field in common_lookups:
          dcl_client.get_mapping(connector, table, field)
  ```

**Success Criteria**:
- ✅ Load tests pass at 1,000 RPS with P95 <50ms
- ✅ Soak test (1 hour) shows zero degradation
- ✅ Capacity plan documents max RPS and scaling strategy
- ✅ Cache warming reduces cold start latency

**Dependencies**: Phase 3.3 complete

**Blockers**: None

---

### 3.5: Disaster Recovery Planning (Medium Priority)

**Tasks**:
- **Backup Strategy**
  - Daily PostgreSQL backups of `field_mappings` table
  - Hourly Redis snapshots for cache state
  - Version control for mapping changes (Git-like tracking)

- **Recovery Procedures**
  ```markdown
  ## Disaster Recovery Procedures
  
  ### Scenario 1: PostgreSQL Data Loss
  1. Restore from latest daily backup
  2. Replay mapping changes from audit log
  3. Re-run migration script to fill gaps
  4. Validate data integrity
  
  ### Scenario 2: Redis Cache Failure
  1. Redis automatically fails over to replica
  2. Cache miss rate temporarily increases
  3. PostgreSQL handles increased load (tested in capacity planning)
  4. Cache rebuilds automatically via normal traffic
  
  ### Scenario 3: Complete DCL Failure
  1. Execute rollback script (falls back to YAML)
  2. AAM continues operating with YAML
  3. Fix DCL issues offline
  4. Re-enable DCL once validated
  ```

- **Disaster Recovery Testing**
  - Quarterly DR drill
  - Test full PostgreSQL restore
  - Test Redis failover
  - Test rollback under load

**Success Criteria**:
- ✅ DR procedures documented
- ✅ Backup/restore tested successfully
- ✅ RTO <1 hour, RPO <1 hour
- ✅ Quarterly DR drill scheduled

**Dependencies**: Phase 3.4 complete

**Blockers**: None

---

## PHASE 4: Production Rollout & Certification
**Priority**: High  
**Objective**: Final validation, YAML retirement, legacy code removal, RACI certification  
**Dependencies**: Phase 3 complete (reliability hardening operational)

### 4.1: Pre-Production Validation Checklist (P0)

**Checklist**:
```markdown
## Phase 1 Validation
- [ ] Contract tests passing (3/3)
- [ ] Integration tests passing (3/3)
- [ ] Performance tests passing (4/4)
- [ ] Dual-read validation: zero mismatches
- [ ] Feature flag at 100% in production
- [ ] YAML files archived and read-only

## Phase 2 Validation
- [ ] LLM proposals migrated to DCL
- [ ] RAG lookup migrated to DCL
- [ ] Confidence scoring migrated to DCL
- [ ] Drift repair migrated to DCL
- [ ] Approval workflow operational
- [ ] RACI audit: 11/11 compliant

## Phase 3 Validation
- [ ] Observability: logs, metrics, traces operational
- [ ] Error budgets: tracking and enforcement active
- [ ] Rollback: tested and playbook reviewed
- [ ] Load tests: pass at 1,000 RPS
- [ ] DR plan: documented and tested

## Production Readiness
- [ ] Admin authorization enforced
- [ ] Cache invalidation working
- [ ] Unique constraint deployed
- [ ] Monitoring dashboard operational
- [ ] On-call runbook complete
- [ ] Incident response plan documented
```

**Success Criteria**:
- ✅ 100% checklist items complete
- ✅ Architect approval obtained
- ✅ Security review passed
- ✅ SRE sign-off received

**Dependencies**: Phases 1-3 complete

**Blockers**: None

---

### 4.2: Legacy Code Removal (High Priority)

**Tasks**:
- **Remove YAML Loading from AAM**
  ```python
  # Delete these files/functions:
  - services/aam/canonical/load_yaml_mapping()
  - services/aam/canonical/yaml_parser.py
  - Remove pyyaml dependency from requirements.txt
  ```

- **Remove Dual-Read Logic**
  ```python
  # Remove DUAL_READ_VALIDATE environment variable checks
  # Remove comparison logic between DCL and YAML
  # Simplify mapping_registry.py to DCL-only
  ```

- **Remove LLM/RAG from AAM**
  ```python
  # Delete LLM client initialization in AAM
  # Delete RAG vector store access in AAM
  # Remove openai, google-generativeai from AAM requirements
  ```

- **Clean Up Feature Flags**
  ```python
  # Remove USE_DCL_MAPPING_REGISTRY flag (always true now)
  # Remove flag checks from code
  # Update docs to remove flag references
  ```

**Success Criteria**:
- ✅ Zero YAML references in AAM code
- ✅ Zero LLM/RAG dependencies in AAM
- ✅ Codebase 30% smaller (legacy code removed)
- ✅ All tests still passing after cleanup

**Dependencies**: Phase 4.1 complete

**Blockers**: None

---

### 4.3: Documentation Updates (High Priority)

**Tasks**:
- **Update Architecture Docs**
  - Update `RACI_REMEDIATION_P1_DESIGN.md` to "COMPLETE" status
  - Update `AAM_DCL_ARCHITECTURE_OVERVIEW.md` with new boundaries
  - Create `RACI_COMPLIANCE_CERTIFICATE.md` documenting 100% compliance

- **Update API Documentation**
  - Document DCL intelligence APIs
  - Mark YAML endpoints as deprecated
  - Update code examples to use DCL API

- **Create Runbooks**
  - DCL mapping registry operations runbook
  - Incident response runbook
  - Rollback procedure runbook

- **Update Developer Guide**
  - How to add new mappings (via DCL API)
  - How to propose LLM mappings
  - How to debug mapping issues

**Success Criteria**:
- ✅ All docs updated and reviewed
- ✅ RACI compliance certificate generated
- ✅ Runbooks tested by SRE team
- ✅ Developer guide validated with onboarding exercise

**Dependencies**: Phase 4.2 complete

**Blockers**: None

---

### 4.4: Final RACI Compliance Audit (P0)

**Tasks**:
- **Run Automated RACI Audit**
  ```bash
  python scripts/audit_raci_compliance.py --comprehensive
  ```

- **Manual Verification**
  - Review all 11 capabilities in RACI matrix
  - Verify DCL owns intelligence (LLM, RAG, confidence, drift repair, approvals)
  - Verify AAM owns runtime (auth, data fetch, pagination, rate limiting, monitoring)
  - Verify DCL owns graph/ontology/agents
  - Verify clear API boundaries enforced

- **Generate Compliance Report**
  ```markdown
  # RACI Compliance Certificate
  Date: [Date]
  Version: 1.0
  
  ## Certification Statement
  We certify that AutonomOS platform achieves 100% compliance with the
  defined RACI matrix for AAM/DCL component boundaries.
  
  ## Capabilities Verified
  ✅ Discovery & Cataloging (AOD accountable)
  ✅ Connection Runtime (AAM accountable)
  ✅ Intelligence & Mapping (DCL accountable)
  ✅ Transformation (DCL decides, AAM executes)
  ✅ Graph & Ontology (DCL accountable)
  ✅ Agent Orchestration (DCL accountable)
  
  ## Evidence
  - Contract tests enforce boundaries: 3/3 passing
  - Code audit shows zero violations: 0 violations found
  - API boundaries documented: 8 DCL intelligence endpoints
  - Ownership verified: All 11 capabilities assigned correctly
  
  ## Signatures
  - Architect: [Name]
  - Engineering Lead: [Name]
  - SRE Lead: [Name]
  ```

**Success Criteria**:
- ✅ 11/11 RACI capabilities verified compliant
- ✅ Zero violations detected
- ✅ Compliance certificate signed by stakeholders
- ✅ Certificate published in repository

**Dependencies**: Phase 4.3 complete

**Blockers**: None

---

### 4.5: Production Cutover Celebration (Low Priority)

**Tasks**:
- **Final Metrics Review**
  - Document before/after metrics
  - Compare baseline vs post-migration performance
  - Quantify improvements (latency, reliability, maintainability)

- **Retrospective**
  - What went well
  - What could be improved
  - Lessons learned for future migrations

- **Knowledge Transfer**
  - Training session for team on new architecture
  - Demo of DCL intelligence APIs
  - Q&A session on troubleshooting

**Success Criteria**:
- ✅ Metrics documented showing improvement
- ✅ Retrospective completed with action items
- ✅ Team trained on new architecture

**Dependencies**: Phase 4.4 complete

**Blockers**: None

---

## Success Criteria: Target State Achieved

### Functional Completeness (100%)
- ✅ DCL mapping registry operational with <50ms P95 latency
- ✅ All intelligence consolidated in DCL (LLM, RAG, confidence, drift, approvals)
- ✅ AAM exclusively uses DCL APIs (zero direct mapping access)
- ✅ 191 mappings operational in PostgreSQL
- ✅ Feature flag at 100%, YAML fully deprecated

### Architectural Soundness (100%)
- ✅ Clear API boundaries between AAM and DCL
- ✅ Database-backed registry with tenant isolation
- ✅ Redis caching with >90% hit rate
- ✅ Admin authorization enforced
- ✅ Cache invalidation operational

### RACI Compliance (100%)
- ✅ 11/11 capabilities aligned with RACI matrix
- ✅ DCL owns all intelligence/mapping decisions
- ✅ AAM owns runtime operations only
- ✅ Contract tests enforce boundaries
- ✅ Compliance certificate issued

### Production Readiness (100%)
- ✅ 10/10 contract tests passing
- ✅ 10/10 integration tests passing
- ✅ 8/8 performance tests passing
- ✅ Load tests pass at 1,000 RPS
- ✅ Observability: logs, metrics, traces operational
- ✅ Error budgets tracked with auto-rollback
- ✅ Rollback tested and playbook documented
- ✅ DR plan tested with RTO <1h, RPO <1h
- ✅ On-call runbooks complete

### Reliability Metrics
- ✅ 99.9% availability SLO
- ✅ <50ms P95 latency SLO
- ✅ >90% cache hit rate
- ✅ <1% error rate
- ✅ Zero RACI violations

---

## Risk Mitigation

### High-Risk Items (P0)

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Tests reveal critical bugs** | HIGH | Fix bugs before proceeding to next phase; architect review required |
| **Performance regression** | CRITICAL | Rollback immediately; optimize before retry; load test in staging first |
| **Data loss during cutover** | CRITICAL | Dual-read validation mandatory; YAML backup retained; rollback tested |
| **RACI violations persist** | HIGH | Contract tests block deployment; automated audit in CI/CD |
| **Production incident** | CRITICAL | Rollback automation <60s; on-call runbook; error budget enforcement |

### Medium-Risk Items

| Risk | Impact | Mitigation |
|------|--------|------------|
| Intelligence migration complexity | MEDIUM | Incremental migration (LLM → RAG → confidence → drift); validate each |
| Cache invalidation bugs | MEDIUM | Monitor cache hit rate; alert on drops <80%; manual flush available |
| Load test failures | MEDIUM | Start with 100 RPS baseline; increment gradually; identify bottlenecks |
| Team knowledge gaps | MEDIUM | Training sessions; runbooks; pair programming during migration |

---

## Dependencies & Blockers

### Phase Dependencies
```
Phase 1 (Correctness) → Phase 2 (Intelligence) → Phase 3 (Reliability) → Phase 4 (Rollout)
     ↓                        ↓                        ↓                        ↓
  Must be 100%          Must be 100%             Must be 100%             Must be 100%
  before Phase 2        before Phase 3           before Phase 4           before certification
```

### External Dependencies
- **PostgreSQL**: Supabase operational (current: ✅ operational)
- **Redis**: Upstash operational (current: ✅ operational)
- **LLM Service**: Gemini API access (current: ✅ configured)
- **Monitoring**: Prometheus/Grafana (current: ⚠️ needs setup)

### Internal Blockers
- **Security Review**: Required before production deployment
- **Architect Approval**: Required at each phase gate
- **SRE Sign-off**: Required for Phase 3 completion

---

## Quality Gates

### Phase 1 Gate: Correctness Validated
**Gate Criteria**:
- All contract tests passing (3/3)
- All integration tests passing (3/3)
- All performance tests passing (4/4)
- Dual-read validation: zero mismatches
- Admin auth + cache invalidation deployed

**Gate Review**: Architect + Engineering Lead

---

### Phase 2 Gate: Intelligence Migrated
**Gate Criteria**:
- LLM proposals in DCL (verified via contract tests)
- RAG lookup in DCL (verified via contract tests)
- Confidence scoring in DCL (verified via contract tests)
- Drift repair in DCL (verified via contract tests)
- Approval workflow operational
- RACI audit: 11/11 compliant

**Gate Review**: Architect + Engineering Lead + Security

---

### Phase 3 Gate: Reliability Hardened
**Gate Criteria**:
- Observability operational (logs, metrics, traces)
- Error budgets tracked with enforcement
- Rollback tested and automated
- Load tests pass at 1,000 RPS
- DR plan tested and documented
- SLOs defined and monitored

**Gate Review**: Architect + SRE Lead

---

### Phase 4 Gate: Production Ready
**Gate Criteria**:
- Pre-production checklist 100% complete
- Legacy code removed and cleanup verified
- Documentation updated and reviewed
- RACI compliance certificate issued
- Security review passed
- SRE sign-off obtained

**Gate Review**: Architect + Engineering Lead + SRE Lead + Security

---

## Priority Definitions

**P0 (Critical)**:
- Blocks production deployment
- RACI compliance dependency
- Security/data integrity issue
- Must complete before next phase

**High Priority**:
- Production readiness requirement
- Significant reliability/performance impact
- Should complete before phase gate

**Medium Priority**:
- Important but not blocking
- Can be completed in parallel
- Nice-to-have for certification

**Low Priority**:
- Optional enhancement
- Post-certification work
- Documentation/training

---

## Architect Approval

**Reviewed By**: Architect (Opus 4.1)  
**Date**: November 18, 2025  
**Status**: ✅ APPROVED  

**Architect Notes**:
- Plan follows Correctness → Reliability → Speed → Scale methodology
- Clear phase dependencies prevent premature optimization
- Quality gates enforce standards at each milestone
- Risk mitigation addresses high-impact scenarios
- RACI compliance built into every phase

**Recommended Execution Order**:
1. Complete Phase 1 testing infrastructure (P0 blocker)
2. Fix security gaps immediately (admin auth + cache invalidation)
3. Execute dual-read validation before any rollout
4. Gate Phase 2 on Phase 1 100% complete
5. Do not skip load testing (Phase 3.4)

---

**END OF TARGET STATE PLAN**
