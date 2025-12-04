# Phase 2: Intelligence Migration - Execution Plan
## Complete RACI Compliance for AI/ML Decision-Making

**Version:** 1.0  
**Date:** November 18, 2025  
**Status:** READY TO EXECUTE  
**Methodology:** Correctness First → Reliability → Speed → Scale  
**Priority:** P0 (Critical for RACI Compliance)

---

## Executive Summary

**Objective**: Move ALL intelligence/decision-making from AAM to DCL per RACI matrix  
**Current RACI Compliance**: 54% (5/11 capabilities)  
**Target RACI Compliance**: 100% (11/11 capabilities)  
**Dependencies**: ✅ Phase 1 Complete (DCL mapping registry proven operational)

### What Moves from AAM → DCL

| Capability | Current Owner | Target Owner | Rationale |
|------------|---------------|--------------|-----------|
| LLM-powered mapping proposals | ❌ AAM | ✅ DCL | Intelligence = DCL responsibility |
| RAG mapping lookup | ❌ AAM | ✅ DCL | Knowledge retrieval = DCL responsibility |
| Confidence scoring | ❌ AAM | ✅ DCL | Mapping quality = DCL responsibility |
| Drift repair proposals | ❌ AAM | ✅ DCL | Mapping decisions = DCL responsibility |
| Mapping approval workflow | ❌ Not implemented | ✅ DCL | Human-in-the-loop = DCL orchestration |

**What Stays in AAM**:
- ✅ Schema drift **detection** (AAM observes source systems)
- ✅ Data transport (AAM connects to sources)
- ✅ Connection runtime (AAM manages connectors)

---

## Architecture Overview

### Current Architecture (RACI Violation)
```
AAM Connector
├── Detects schema drift ✅ (correct)
├── Generates LLM repair proposal ❌ (violation - intelligence in AAM)
├── Scores confidence ❌ (violation - intelligence in AAM)
├── Queries RAG for mappings ❌ (violation - intelligence in AAM)
└── Applies transformation ✅ (correct - execution in AAM)
```

### Target Architecture (RACI Compliant)
```
AAM Connector (Transport Layer)
├── Detects schema drift ✅
├── Reports drift to DCL Intelligence API ✅
└── Applies transformation ✅

DCL Intelligence Service (Intelligence Layer)
├── Receives drift event from AAM
├── Queries RAG for historical mappings
├── Generates LLM repair proposal
├── Scores confidence
├── Routes to approval workflow
└── Returns approved mapping to AAM
```

---

## Phase 2 Tasks

### Task 2.1: Design Intelligence Service Architecture
**Priority**: High  
**Estimated Effort**: Design phase (no code)

**Deliverables**:
1. **Service Interface Definitions**
   - `LLMProposalService` - Mapping suggestions via Gemini
   - `RAGLookupService` - Vector similarity search via pgvector
   - `ConfidenceScoringService` - Multi-factor confidence calculation
   - `DriftRepairService` - Schema drift repair proposals
   - `MappingApprovalService` - Human-in-the-loop workflow

2. **API Contract Specifications**
   ```
   POST /dcl/intelligence/propose-mapping
   POST /dcl/intelligence/rag-lookup
   POST /dcl/intelligence/calculate-confidence
   POST /dcl/intelligence/repair-drift
   POST /dcl/intelligence/submit-for-approval
   GET  /dcl/intelligence/approval-status/{proposal_id}
   ```

3. **Database Schema Design**
   - `mapping_proposals` table (LLM proposal storage)
   - `approval_workflows` table (HITL tracking)
   - `confidence_scores` table (historical scoring data)
   - `drift_events` table (schema change tracking)

4. **Data Flow Diagrams**
   - AAM → DCL Intelligence → RAG → LLM → PostgreSQL → AAM
   - Approval workflow state machine diagram

**Success Criteria**:
- ✅ All service interfaces documented with Pydantic schemas
- ✅ API contracts defined with request/response examples
- ✅ Database schema reviewed by architect
- ✅ Data flow diagrams approved

**Blockers**: None

---

### Task 2.2: Migrate LLM Proposal Logic to DCL
**Priority**: P0 (Critical)  
**Dependencies**: Task 2.1 complete

**Implementation Steps**:

1. **Create DCL Intelligence Module**
   ```bash
   mkdir -p app/dcl_engine/services/intelligence
   touch app/dcl_engine/services/intelligence/__init__.py
   touch app/dcl_engine/services/intelligence/llm_proposal_service.py
   touch app/dcl_engine/routers/intelligence.py
   ```

2. **Extract LLM Logic from AAM**
   - **Source**: `services/aam/canonical/mapping_registry.py` (search for Gemini calls)
   - **Target**: `app/dcl_engine/services/intelligence/llm_proposal_service.py`
   - **Pattern**: Move prompt engineering, LLM invocation, response parsing

3. **Implement LLMProposalService**
   ```python
   class LLMProposalService:
       async def propose_mapping(
           self,
           connector: str,
           source_table: str,
           source_field: str,
           sample_values: List[Any],
           tenant_id: str
       ) -> MappingProposal:
           # 1. Check RAG first (fast path)
           rag_result = await self.rag.lookup_mapping(...)
           if rag_result and rag_result.confidence > 0.9:
               return rag_result
           
           # 2. Fallback to LLM (slow path)
           prompt = self._build_prompt(connector, source_table, source_field, sample_values)
           llm_response = await self.llm_client.generate(prompt)
           
           # 3. Parse and validate
           proposal = self._parse_llm_response(llm_response)
           
           # 4. Score confidence
           proposal.confidence = await self.confidence_service.calculate(proposal)
           
           # 5. Store proposal
           await self._store_proposal(proposal, tenant_id)
           
           return proposal
   ```

4. **Create DCL API Endpoint**
   ```python
   @router.post("/intelligence/propose-mapping")
   async def propose_mapping(
       request: ProposeRequest,
       current_user: User = Depends(get_current_user),
       db: Session = Depends(get_db)
   ):
       service = LLMProposalService(llm_client, rag_service, confidence_service)
       proposal = await service.propose_mapping(
           request.connector,
           request.source_table,
           request.source_field,
           request.sample_values,
           current_user.tenant_id
       )
       return proposal
   ```

5. **Update AAM to Call DCL API**
   - **File**: `services/aam/canonical/mapping_registry.py`
   - **Change**: Replace LLM calls with DCL API HTTP requests
   - **Pattern**: `httpx.post(f"{DCL_BASE_URL}/dcl/intelligence/propose-mapping", ...)`

6. **Remove LLM Dependencies from AAM**
   - Remove `google-generativeai` imports from AAM
   - Remove prompt templates from AAM
   - Remove LLM client initialization from AAM

**Testing Requirements**:
- ✅ Contract test: AAM cannot directly call LLM (no Gemini client)
- ✅ Integration test: AAM → DCL Intelligence API → LLM → Response
- ✅ Unit test: LLMProposalService logic (mock LLM responses)
- ✅ Performance test: Proposal latency < 2s (P95)

**Success Criteria**:
- ✅ AAM has zero LLM client dependencies
- ✅ All LLM calls routed through DCL Intelligence API
- ✅ Proposal quality unchanged from pre-migration
- ✅ 3/3 new tests passing

**Rollback Plan**:
- Feature flag `USE_DCL_INTELLIGENCE_API` (default: false)
- Fallback to AAM LLM calls if DCL API fails

---

### Task 2.3: Migrate RAG Lookup to DCL
**Priority**: P0 (Critical)  
**Dependencies**: Task 2.2 complete

**Implementation Steps**:

1. **Create RAGLookupService**
   ```python
   # app/dcl_engine/services/intelligence/rag_lookup_service.py
   class RAGLookupService:
       def __init__(self, vector_store: VectorStore):
           self.vector_store = vector_store  # pgvector
       
       async def lookup_mapping(
           self,
           connector: str,
           source_table: str,
           source_field: str,
           tenant_id: str
       ) -> Optional[MappingProposal]:
           # 1. Build query embedding
           query = f"{connector}.{source_table}.{source_field}"
           embedding = await self.embedding_model.embed(query)
           
           # 2. Vector similarity search
           results = await self.vector_store.similarity_search(
               embedding,
               tenant_id=tenant_id,
               top_k=5,
               similarity_threshold=0.85
           )
           
           # 3. Return best match
           if results:
               return self._convert_to_proposal(results[0])
           return None
   ```

2. **Create RAG API Endpoint**
   ```python
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
           raise HTTPException(404, "No RAG match found")
       return result
   ```

3. **Update AAM to Use DCL RAG**
   - Remove `pgvector` client from AAM
   - Remove embedding model from AAM
   - Call DCL RAG API instead
   - Handle 404 gracefully (fallback to LLM proposal)

**Testing Requirements**:
- ✅ Contract test: AAM cannot access vector store directly
- ✅ Integration test: AAM → DCL RAG API → pgvector → Response
- ✅ Performance test: RAG lookup < 100ms (P95)

**Success Criteria**:
- ✅ AAM has zero vector store dependencies
- ✅ All RAG queries routed through DCL
- ✅ RAG accuracy unchanged from pre-migration

---

### Task 2.4: Migrate Confidence Scoring to DCL
**Priority**: P0 (Critical)  
**Dependencies**: Task 2.3 complete

**Implementation Steps**:

1. **Create ConfidenceScoringService**
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
           
           # Weighted average (configurable per tenant)
           weights = self._get_tenant_weights(mapping.tenant_id)
           score = sum(factors[k] * weights[k] for k in factors)
           
           return ConfidenceScore(
               score=score,
               factors=factors,
               recommendations=self._generate_recommendations(factors)
           )
   ```

2. **Create Confidence API Endpoint**
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

3. **Update AAM to Use DCL Confidence**
   - Remove confidence calculation logic from AAM
   - Call DCL Confidence API instead

**Testing Requirements**:
- ✅ Contract test: AAM cannot calculate confidence scores
- ✅ Integration test: AAM → DCL Confidence API → Scores
- ✅ Unit test: Confidence calculation algorithm

**Success Criteria**:
- ✅ AAM delegates all confidence scoring to DCL
- ✅ Confidence scores stored in `field_mappings` table
- ✅ Scoring quality unchanged

---

### Task 2.5: Migrate Drift Repair to DCL
**Priority**: P0 (Critical)  
**Dependencies**: Task 2.4 complete

**Implementation Steps**:

1. **Clarify Responsibility Split**
   - **AAM**: Detects schema drift (observes source system changes)
   - **DCL**: Proposes repair (generates mapping suggestions)
   - **AAM**: Applies repair (executes transformation with new mapping)

2. **Create DriftRepairService**
   ```python
   # app/dcl_engine/services/intelligence/drift_repair_service.py
   class DriftRepairService:
       async def propose_repair(
           self,
           drift_event: DriftEvent,
           tenant_id: str
       ) -> RepairProposal:
           # 1. Analyze schema diff
           schema_diff = drift_event.schema_diff
           
           # 2. Check RAG for similar drift events
           rag_result = await self.rag.lookup_similar_drift(schema_diff, tenant_id)
           if rag_result and rag_result.confidence > 0.9:
               return rag_result.repair_proposal
           
           # 3. Fallback to LLM
           prompt = self._build_drift_repair_prompt(drift_event)
           llm_response = await self.llm_client.generate(prompt)
           
           # 4. Parse repair proposal
           proposal = self._parse_repair_proposal(llm_response)
           proposal.confidence = await self.confidence_service.calculate(proposal)
           
           # 5. Store proposal
           await self._store_repair_proposal(proposal, tenant_id)
           
           return proposal
   ```

3. **Create Drift Repair API Endpoint**
   ```python
   @router.post("/intelligence/repair-drift")
   async def repair_drift(
       request: DriftRepairRequest,
       current_user: User = Depends(get_current_user),
       db: Session = Depends(get_db)
   ):
       drift_event = db.query(DriftEvent).filter_by(id=request.drift_event_id).first()
       service = DriftRepairService(llm_client, rag_service, confidence_service)
       proposal = await service.propose_repair(drift_event, current_user.tenant_id)
       return proposal
   ```

4. **Update AAM Drift Detection**
   - **File**: `services/aam/canonical/drift_detector.py`
   - **Keep**: Schema fingerprinting, diff detection
   - **Change**: After detecting drift, call DCL API for repair proposal
   - **Remove**: LLM-based repair logic

**Testing Requirements**:
- ✅ Contract test: AAM cannot propose drift repairs (only detect)
- ✅ Integration test: AAM detects drift → DCL proposes repair → AAM applies
- ✅ Performance test: Repair proposal < 3s (P95)

**Success Criteria**:
- ✅ AAM detects drift, DCL proposes repairs
- ✅ Repair quality unchanged
- ✅ Clear separation of concerns

---

### Task 2.6: Implement Mapping Approval Workflow
**Priority**: High  
**Dependencies**: Tasks 2.2-2.5 complete

**Implementation Steps**:

1. **Create MappingApprovalService**
   ```python
   # app/dcl_engine/services/intelligence/approval_service.py
   class MappingApprovalService:
       async def submit_for_approval(
           self,
           proposal: MappingProposal,
           tenant_id: str
       ) -> ApprovalWorkflow:
           # 1. Create approval workflow
           workflow = ApprovalWorkflow(
               proposal_id=proposal.id,
               tenant_id=tenant_id,
               status='pending',
               assigned_to=self._get_tenant_admin(tenant_id)
           )
           db.add(workflow)
           db.commit()
           
           # 2. Trigger notification (Slack, email)
           await self._notify_approver(workflow)
           
           return workflow
       
       async def approve_proposal(
           self,
           workflow_id: str,
           approver_id: str,
           notes: Optional[str]
       ):
           workflow = db.query(ApprovalWorkflow).filter_by(id=workflow_id).first()
           workflow.status = 'approved'
           workflow.approver_id = approver_id
           workflow.approval_notes = notes
           
           # Auto-create mapping in field_mappings table
           await self._create_approved_mapping(workflow.proposal)
           
           db.commit()
   ```

2. **Create Approval API Endpoints**
   ```python
   @router.post("/intelligence/submit-for-approval")
   async def submit_for_approval(proposal_id: str, ...):
       ...
   
   @router.post("/intelligence/approve/{workflow_id}")
   async def approve_proposal(workflow_id: str, ...):
       ...
   
   @router.get("/intelligence/approval-status/{proposal_id}")
   async def get_approval_status(proposal_id: str, ...):
       ...
   ```

3. **Integrate with LLM/RAG/Drift Services**
   - Low-confidence proposals (< 0.7) auto-route to approval workflow
   - High-confidence proposals (>= 0.7) auto-approve
   - Manual review required for critical connectors

**Testing Requirements**:
- ✅ Integration test: Proposal → Approval → Auto-create mapping
- ✅ Unit test: Approval workflow state machine

**Success Criteria**:
- ✅ Low-confidence proposals routed to human review
- ✅ Approval notifications working
- ✅ Auto-creation of approved mappings

---

## Testing Strategy

### Contract Tests (RACI Boundary Enforcement)
```python
# tests/contract/test_phase2_raci_boundaries.py

def test_aam_cannot_call_llm_directly():
    """AAM should not have LLM client"""
    from services.aam import canonical
    assert not hasattr(canonical, 'llm_client')
    assert not hasattr(canonical, 'genai')

def test_aam_cannot_access_vector_store():
    """AAM should not have pgvector client"""
    from services.aam import canonical
    assert not hasattr(canonical, 'vector_store')
    assert not hasattr(canonical, 'pinecone')

def test_aam_cannot_calculate_confidence():
    """AAM should not have confidence scoring logic"""
    from services.aam.canonical.mapping_registry import mapping_registry
    assert not hasattr(mapping_registry, 'calculate_confidence')

def test_dcl_owns_all_intelligence():
    """DCL should own LLM, RAG, confidence, drift repair"""
    from app.dcl_engine.services.intelligence import (
        LLMProposalService,
        RAGLookupService,
        ConfidenceScoringService,
        DriftRepairService
    )
    assert all([
        LLMProposalService,
        RAGLookupService,
        ConfidenceScoringService,
        DriftRepairService
    ])
```

### Integration Tests
```python
# tests/integration/test_phase2_intelligence_flow.py

@pytest.mark.asyncio
async def test_llm_proposal_flow():
    """Test AAM → DCL Intelligence API → LLM → Response"""
    # AAM calls DCL for proposal
    response = await dcl_client.post("/dcl/intelligence/propose-mapping", ...)
    assert response.status_code == 200
    assert 'canonical_field' in response.json()

@pytest.mark.asyncio
async def test_rag_lookup_flow():
    """Test AAM → DCL RAG API → pgvector → Response"""
    # AAM calls DCL for RAG lookup
    response = await dcl_client.get("/dcl/intelligence/rag-lookup/salesforce/opportunity/Amount")
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_drift_repair_flow():
    """Test AAM detects drift → DCL proposes repair → AAM applies"""
    # 1. AAM detects drift
    drift_event = detect_schema_drift(connector, table)
    
    # 2. AAM calls DCL for repair
    response = await dcl_client.post("/dcl/intelligence/repair-drift", json={
        "drift_event_id": drift_event.id
    })
    
    # 3. Verify repair proposal
    assert response.status_code == 200
    assert 'repair_proposal' in response.json()
```

### Performance Tests
```python
# tests/performance/test_phase2_latency.py

def test_llm_proposal_latency():
    """LLM proposals must complete within 2s (P95)"""
    latencies = []
    for _ in range(100):
        start = time.time()
        dcl_client.post("/dcl/intelligence/propose-mapping", ...)
        latencies.append(time.time() - start)
    
    p95 = np.percentile(latencies, 95)
    assert p95 < 2.0, f"P95 latency {p95}s exceeds 2s threshold"

def test_rag_lookup_latency():
    """RAG lookups must complete within 100ms (P95)"""
    latencies = []
    for _ in range(1000):
        start = time.time()
        dcl_client.get("/dcl/intelligence/rag-lookup/...")
        latencies.append(time.time() - start)
    
    p95 = np.percentile(latencies, 95) * 1000
    assert p95 < 100, f"P95 latency {p95}ms exceeds 100ms threshold"
```

---

## Feature Flag Strategy

**Flag Name**: `USE_DCL_INTELLIGENCE_API`  
**Storage**: Redis-backed with async pub/sub  
**Default**: `false` (safe rollout)

**Rollout Stages**:
1. **0% (Development)**: Test DCL Intelligence API in isolation
2. **10% (Canary)**: Route 10% of intelligence requests to DCL
3. **25%**: Increase if zero errors
4. **50%**: Half of traffic on DCL Intelligence
5. **100%**: Full cutover, remove AAM intelligence code

**Monitoring**:
- Intelligence API request rate
- Intelligence API error rate
- LLM proposal quality (human feedback)
- RAG hit rate
- Confidence score distribution

**Rollback Criteria** (trigger immediate rollback if):
- Error rate increases >5%
- LLM proposal quality degrades (user feedback)
- P95 latency exceeds 2s for proposals

---

## Success Criteria

### Phase 2 Complete When:
- ✅ LLM proposal logic fully migrated to DCL
- ✅ RAG lookup fully migrated to DCL
- ✅ Confidence scoring fully migrated to DCL
- ✅ Drift repair proposals fully migrated to DCL
- ✅ Mapping approval workflow operational
- ✅ AAM has ZERO intelligence/AI dependencies (no LLM, no RAG, no confidence logic)
- ✅ Contract tests passing (12+ tests enforcing RACI boundaries)
- ✅ Integration tests passing (6+ tests validating E2E flows)
- ✅ Performance tests passing (P95 latency within thresholds)
- ✅ Feature flag rolled out to 100%
- ✅ **RACI Compliance: 100% (11/11 capabilities)**

---

## Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| LLM proposal quality degrades | HIGH | MEDIUM | Feature flag rollback, A/B testing |
| RAG migration breaks lookups | HIGH | LOW | Comprehensive integration tests |
| Performance regression | MEDIUM | MEDIUM | Performance testing, caching |
| AAM breaks without intelligence | CRITICAL | LOW | Feature flag, gradual rollout |

---

## Next Steps After Phase 2

**Phase 3**: Reliability Hardening (Production observability, SLO monitoring, rollback automation)  
**Phase 4**: Production Rollout (100% DCL cutover, remove legacy AAM code, YAML deprecation)  

---

**END OF PHASE 2 PLAN**
