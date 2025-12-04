# Phase 2: Intelligence Service Architecture Design
## DCL Intelligence Layer - Technical Specification

**Version:** 1.0  
**Date:** November 18, 2025  
**Status:** APPROVED FOR IMPLEMENTATION  
**Task:** 2.1 - Design Intelligence Service Architecture

---

## Executive Summary

This document specifies the complete architecture for migrating ALL intelligence/decision-making from AAM to DCL, achieving 100% RACI compliance. The DCL Intelligence Layer will own LLM proposals, RAG lookup, confidence scoring, drift repair proposals, and approval workflows.

### Current State Analysis

**AAM Intelligence Components (RACI Violations)**:
1. **LLM Repair Agent** (`aam_hybrid/core/repair_agent.py`)
   - `RepairAgent.suggest_repairs()` - Proposes field mappings via LLM
   - 3-tier confidence thresholds (auto-apply >=0.85, HITL 0.6-0.85, reject <0.6)
   - Uses `app/dcl_engine/llm_service.LLMService` (Gemini)

2. **RAG Engine** (`aam_hybrid/services/rag_engine/service.py`)
   - `RAGEngine.retrieve_similar_repairs()` - pgvector similarity search
   - `RAGEngine.generate_repair_proposal()` - LLM with RAG context (OpenAI)
   - Uses OpenAI embeddings + chat completions

3. **Drift Detection** (`services/aam/schema_observer.py` + `aam_hybrid/core/canonical_processor.py`)
   - **Detection**: AAM (✅ CORRECT)
   - **Repair Proposals**: AAM via RepairAgent (❌ VIOLATION)

4. **HITL Workflow** (Redis queue in `repair_agent.py`)
   - Medium-confidence repairs queued in Redis
   - 7-day TTL for human review

**Target State (RACI Compliant)**:
- AAM: Transport + Observation (detects drift, reports to DCL)
- DCL: Intelligence + Orchestration (LLM, RAG, confidence, repairs, approvals)

---

## Service Architecture

### 1. Service Interface Definitions

#### 1.1 LLMProposalService
**Responsibility**: Generate mapping proposals using Gemini LLM  
**Location**: `app/dcl_engine/services/intelligence/llm_proposal_service.py`

```python
class LLMProposalService:
    """
    LLM-powered mapping proposal service.
    Uses RAG-first strategy with LLM fallback.
    """
    
    def __init__(
        self, 
        llm_client: LLMService, 
        rag_service: RAGLookupService,
        confidence_service: ConfidenceScoringService
    ):
        self.llm = llm_client
        self.rag = rag_service
        self.confidence = confidence_service
    
    async def propose_mapping(
        self,
        connector: str,
        source_table: str,
        source_field: str,
        sample_values: List[Any],
        tenant_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> MappingProposal:
        """
        Propose canonical mapping for a source field.
        
        Strategy:
        1. RAG lookup (fast path, high confidence)
        2. LLM generation (slow path, medium confidence)
        3. Confidence scoring
        4. Store proposal
        
        Args:
            connector: Source connector ID (e.g., 'salesforce')
            source_table: Source table name (e.g., 'Opportunity')
            source_field: Source field name (e.g., 'Amount')
            sample_values: Sample values from source field for type inference
            tenant_id: Tenant identifier
            context: Optional metadata (drift event ID, etc.)
            
        Returns:
            MappingProposal with canonical_field, confidence, reasoning
        """
        pass
```

**Key Methods**:
- `propose_mapping()` - Main proposal logic (RAG → LLM → confidence → store)
- `_build_llm_prompt()` - Construct LLM prompt with context
- `_parse_llm_response()` - Extract canonical field from LLM JSON response
- `_store_proposal()` - Persist to `mapping_proposals` table

---

#### 1.2 RAGLookupService
**Responsibility**: Vector similarity search for historical mappings  
**Location**: `app/dcl_engine/services/intelligence/rag_lookup_service.py`

```python
class RAGLookupService:
    """
    RAG-based mapping lookup service using pgvector.
    Performs similarity search over historical mapping knowledge base.
    """
    
    def __init__(self, vector_store: VectorStore, embedding_model: EmbeddingModel):
        self.vector_store = vector_store  # pgvector client
        self.embedding_model = embedding_model  # OpenAI embeddings or sentence-transformers
    
    async def lookup_mapping(
        self,
        connector: str,
        source_table: str,
        source_field: str,
        tenant_id: str,
        similarity_threshold: float = 0.85
    ) -> Optional[MappingProposal]:
        """
        Lookup historical mapping via vector similarity search.
        
        Flow:
        1. Build query string: "{connector}.{source_table}.{source_field}"
        2. Generate embedding for query
        3. Perform pgvector <=> similarity search
        4. Filter by tenant_id and similarity_threshold
        5. Return best match (highest similarity)
        
        Args:
            connector: Source connector ID
            source_table: Source table name
            source_field: Source field name
            tenant_id: Tenant identifier for isolation
            similarity_threshold: Minimum cosine similarity (default: 0.85)
            
        Returns:
            MappingProposal if similar mapping found, None otherwise
        """
        pass
    
    async def index_mapping(
        self,
        mapping: FieldMapping,
        tenant_id: str
    ):
        """
        Index a mapping in the vector store for future RAG lookups.
        
        Stores:
        - Query: "{connector}.{source_table}.{source_field}"
        - Embedding: Vector representation of query
        - Metadata: canonical_field, confidence, creation timestamp
        """
        pass
```

**Key Methods**:
- `lookup_mapping()` - Similarity search for existing mappings
- `index_mapping()` - Store new mappings in vector index
- `_generate_embedding()` - Create embedding for query string
- `_convert_to_proposal()` - Transform RAG result to MappingProposal

**Database Integration**:
- Table: `repair_knowledge_base` (existing)
- Uses pgvector extension for similarity search

---

#### 1.3 ConfidenceScoringService
**Responsibility**: Multi-factor confidence calculation  
**Location**: `app/dcl_engine/services/intelligence/confidence_service.py`

```python
class ConfidenceScoringService:
    """
    Confidence scoring service for mapping proposals.
    Uses multi-factor scoring with configurable weights.
    """
    
    # Confidence Tiers (from RepairAgent)
    AUTO_APPLY_THRESHOLD = 0.85
    HITL_LOWER_THRESHOLD = 0.6
    
    def calculate_confidence(
        self,
        mapping: Union[FieldMapping, MappingProposal],
        factors: Dict[str, Any]
    ) -> ConfidenceScore:
        """
        Calculate confidence score using weighted multi-factor analysis.
        
        Factors:
        - source_quality: Source data completeness and consistency
        - usage_frequency: How often this mapping has been used successfully
        - validation_success: Historical validation success rate
        - human_approval: Whether a human has reviewed/approved
        - rag_similarity: RAG lookup similarity score (if available)
        
        Weights (configurable per tenant):
        - source_quality: 0.20
        - usage_frequency: 0.15
        - validation_success: 0.30
        - human_approval: 0.25
        - rag_similarity: 0.10
        
        Returns:
            ConfidenceScore with score, factors, tier, recommendations
        """
        pass
    
    def determine_action(self, confidence_score: float) -> str:
        """
        Determine action based on confidence tier.
        
        Returns:
            - "auto_apply" if >= 0.85
            - "hitl_queued" if 0.6 <= score < 0.85
            - "rejected" if < 0.6
        """
        if confidence_score >= self.AUTO_APPLY_THRESHOLD:
            return "auto_apply"
        elif confidence_score >= self.HITL_LOWER_THRESHOLD:
            return "hitl_queued"
        else:
            return "rejected"
```

**Key Methods**:
- `calculate_confidence()` - Multi-factor scoring
- `determine_action()` - Threshold-based tier assignment
- `_get_tenant_weights()` - Tenant-specific weight configuration
- `_generate_recommendations()` - Improvement suggestions based on factors

---

#### 1.4 DriftRepairService
**Responsibility**: Schema drift repair proposals  
**Location**: `app/dcl_engine/services/intelligence/drift_repair_service.py`

```python
class DriftRepairService:
    """
    Drift repair proposal service.
    Coordinates LLM + RAG + Confidence for drift repairs.
    """
    
    def __init__(
        self,
        llm_service: LLMProposalService,
        rag_service: RAGLookupService,
        confidence_service: ConfidenceScoringService
    ):
        self.llm = llm_service
        self.rag = rag_service
        self.confidence = confidence_service
    
    async def propose_repair(
        self,
        drift_event: DriftEvent,
        tenant_id: str
    ) -> RepairProposal:
        """
        Generate repair proposal for schema drift.
        
        Flow:
        1. Extract drifted fields from drift_event.changes
        2. For each drifted field:
           a. Query RAG for similar drift repairs
           b. Fallback to LLM if RAG miss
           c. Score confidence
        3. Aggregate proposals into RepairProposal
        4. Store in drift_events + repair_proposals tables
        
        Args:
            drift_event: DriftEvent from AAM schema observer
            tenant_id: Tenant identifier
            
        Returns:
            RepairProposal with field mappings, confidence, action tier
        """
        pass
```

**Key Methods**:
- `propose_repair()` - Main repair proposal logic
- `_extract_drifted_fields()` - Parse drift_event.changes
- `_query_rag_for_drift()` - RAG lookup for similar drift events
- `_aggregate_proposals()` - Combine per-field proposals into batch

---

#### 1.5 MappingApprovalService
**Responsibility**: Human-in-the-loop workflow orchestration  
**Location**: `app/dcl_engine/services/intelligence/approval_service.py`

```python
class MappingApprovalService:
    """
    Approval workflow service for medium-confidence proposals.
    Manages HITL queue, notifications, and auto-approval.
    """
    
    def __init__(
        self,
        notification_service: NotificationService,
        db_session: Session
    ):
        self.notifications = notification_service
        self.db = db_session
    
    async def submit_for_approval(
        self,
        proposal: MappingProposal,
        tenant_id: str
    ) -> ApprovalWorkflow:
        """
        Submit proposal to approval workflow.
        
        Flow:
        1. Create ApprovalWorkflow record (status='pending')
        2. Assign to tenant admin
        3. Send notification (Slack, email)
        4. Set 7-day TTL for review
        
        Returns:
            ApprovalWorkflow with ID, status, assigned_to
        """
        pass
    
    async def approve_proposal(
        self,
        workflow_id: str,
        approver_id: str,
        notes: Optional[str]
    ):
        """
        Approve a pending proposal.
        
        Flow:
        1. Update workflow status to 'approved'
        2. Create FieldMapping record from proposal
        3. Index mapping in RAG vector store
        4. Notify requester
        """
        pass
    
    async def reject_proposal(
        self,
        workflow_id: str,
        approver_id: str,
        reason: str
    ):
        """
        Reject a pending proposal.
        
        Flow:
        1. Update workflow status to 'rejected'
        2. Store rejection reason
        3. Notify requester
        """
        pass
```

**Key Methods**:
- `submit_for_approval()` - Queue proposal for review
- `approve_proposal()` - Approve and create mapping
- `reject_proposal()` - Reject with reason
- `get_approval_status()` - Check workflow state
- `_notify_approver()` - Send Slack/email notification

---

## 2. API Contract Specifications

### 2.1 POST /dcl/intelligence/propose-mapping
**Purpose**: Generate canonical mapping proposal for source field

**Request Schema**:
```python
class ProposeRequest(BaseModel):
    connector: str = Field(..., example="salesforce")
    source_table: str = Field(..., example="Opportunity")
    source_field: str = Field(..., example="Amount")
    sample_values: List[Any] = Field(..., example=[1000.0, 2500.5, 750.25])
    context: Optional[Dict[str, Any]] = Field(None, example={"drift_event_id": "uuid"})
```

**Response Schema**:
```python
class MappingProposal(BaseModel):
    proposal_id: str
    connector: str
    source_table: str
    source_field: str
    canonical_entity: str
    canonical_field: str
    confidence: float
    reasoning: str
    alternatives: List[Dict[str, Any]]
    action: str  # "auto_apply" | "hitl_queued" | "rejected"
    created_at: datetime
```

**Example**:
```json
POST /dcl/intelligence/propose-mapping
{
  "connector": "salesforce",
  "source_table": "Opportunity",
  "source_field": "Amount",
  "sample_values": [1000.0, 2500.5, 750.25]
}

Response 200:
{
  "proposal_id": "550e8400-e29b-41d4-a716-446655440000",
  "connector": "salesforce",
  "source_table": "Opportunity",
  "source_field": "Amount",
  "canonical_entity": "opportunity",
  "canonical_field": "amount",
  "confidence": 0.95,
  "reasoning": "RAG lookup: similar mapping found for Salesforce.Opportunity.Amount with 98% similarity",
  "alternatives": [
    {"canonical_field": "revenue", "confidence": 0.65}
  ],
  "action": "auto_apply",
  "created_at": "2025-11-18T10:30:00Z"
}
```

---

### 2.2 GET /dcl/intelligence/rag-lookup/{connector}/{source_table}/{source_field}
**Purpose**: RAG similarity search for existing mappings

**Path Parameters**:
- `connector`: Connector ID (e.g., "salesforce")
- `source_table`: Source table name
- `source_field`: Source field name

**Query Parameters**:
- `similarity_threshold`: Min similarity (default: 0.85)
- `top_k`: Number of results (default: 5)

**Response Schema**:
```python
class RAGResult(BaseModel):
    canonical_field: str
    similarity: float
    source_mapping_id: str
    usage_count: int
    last_used: datetime
```

**Example**:
```json
GET /dcl/intelligence/rag-lookup/salesforce/Opportunity/Amount?similarity_threshold=0.85

Response 200:
{
  "canonical_field": "amount",
  "similarity": 0.98,
  "source_mapping_id": "a1b2c3d4-...",
  "usage_count": 1247,
  "last_used": "2025-11-18T09:15:00Z"
}
```

---

### 2.3 POST /dcl/intelligence/calculate-confidence
**Purpose**: Calculate confidence score for mapping

**Request Schema**:
```python
class ConfidenceRequest(BaseModel):
    mapping_id: Optional[str] = None
    proposal_id: Optional[str] = None
    validation_results: Dict[str, Any] = Field(..., example={
        "success_rate": 0.95,
        "rag_similarity": 0.92,
        "usage_frequency": 1200
    })
```

**Response Schema**:
```python
class ConfidenceScore(BaseModel):
    score: float
    tier: str  # "auto_apply" | "hitl_queued" | "rejected"
    factors: Dict[str, float]
    recommendations: List[str]
```

**Example**:
```json
POST /dcl/intelligence/calculate-confidence
{
  "proposal_id": "550e8400-...",
  "validation_results": {
    "success_rate": 0.95,
    "rag_similarity": 0.92,
    "usage_frequency": 1200
  }
}

Response 200:
{
  "score": 0.89,
  "tier": "auto_apply",
  "factors": {
    "source_quality": 0.90,
    "usage_frequency": 0.85,
    "validation_success": 0.95,
    "human_approval": 0.00,
    "rag_similarity": 0.92
  },
  "recommendations": [
    "Consider human review for production deployment",
    "Monitor validation success rate over time"
  ]
}
```

---

### 2.4 POST /dcl/intelligence/repair-drift
**Purpose**: Generate repair proposals for schema drift

**Request Schema**:
```python
class DriftRepairRequest(BaseModel):
    drift_event_id: str
```

**Response Schema**:
```python
class RepairProposal(BaseModel):
    repair_proposal_id: str
    drift_event_id: str
    field_repairs: List[FieldRepair]
    overall_confidence: float
    auto_applied_count: int
    hitl_queued_count: int
    rejected_count: int
    created_at: datetime

class FieldRepair(BaseModel):
    field_name: str
    drift_type: str  # "added" | "removed" | "type_changed"
    canonical_field: str
    confidence: float
    action: str
    reasoning: str
```

**Example**:
```json
POST /dcl/intelligence/repair-drift
{
  "drift_event_id": "drift-550e8400-..."
}

Response 200:
{
  "repair_proposal_id": "repair-660f9511-...",
  "drift_event_id": "drift-550e8400-...",
  "field_repairs": [
    {
      "field_name": "NewRevenue",
      "drift_type": "added",
      "canonical_field": "revenue",
      "confidence": 0.92,
      "action": "auto_apply",
      "reasoning": "High similarity to existing 'Amount' field mapping"
    },
    {
      "field_name": "UnknownField",
      "drift_type": "added",
      "canonical_field": "unknown_field",
      "confidence": 0.55,
      "action": "rejected",
      "reasoning": "Low confidence, insufficient context"
    }
  ],
  "overall_confidence": 0.75,
  "auto_applied_count": 1,
  "hitl_queued_count": 0,
  "rejected_count": 1,
  "created_at": "2025-11-18T10:45:00Z"
}
```

---

### 2.5 POST /dcl/intelligence/submit-for-approval
**Purpose**: Submit proposal to HITL workflow

**Request Schema**:
```python
class ApprovalSubmitRequest(BaseModel):
    proposal_id: str
    priority: str = "normal"  # "normal" | "high" | "critical"
    notes: Optional[str] = None
```

**Response Schema**:
```python
class ApprovalWorkflow(BaseModel):
    workflow_id: str
    proposal_id: str
    status: str  # "pending" | "approved" | "rejected"
    assigned_to: str
    created_at: datetime
    expires_at: datetime  # 7 days from created_at
```

---

### 2.6 GET /dcl/intelligence/approval-status/{proposal_id}
**Purpose**: Check approval workflow status

**Response Schema**:
```python
class ApprovalStatus(BaseModel):
    workflow_id: str
    proposal_id: str
    status: str
    assigned_to: str
    approver_id: Optional[str]
    approval_notes: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
```

---

## 3. Database Schema Design

### 3.1 mapping_proposals
```sql
CREATE TABLE mapping_proposals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(255) NOT NULL,
    connector VARCHAR(100) NOT NULL,
    source_table VARCHAR(255) NOT NULL,
    source_field VARCHAR(255) NOT NULL,
    canonical_entity VARCHAR(100) NOT NULL,
    canonical_field VARCHAR(100) NOT NULL,
    confidence DECIMAL(5,4) NOT NULL,
    reasoning TEXT,
    alternatives JSONB,
    action VARCHAR(20) NOT NULL,  -- auto_apply, hitl_queued, rejected
    source VARCHAR(50) NOT NULL,  -- 'llm', 'rag', 'manual'
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(255),
    applied_at TIMESTAMP,
    
    INDEX idx_proposals_lookup (tenant_id, connector, source_table, source_field),
    INDEX idx_proposals_action (tenant_id, action, created_at)
);
```

### 3.2 approval_workflows
```sql
CREATE TABLE approval_workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(255) NOT NULL,
    proposal_id UUID NOT NULL REFERENCES mapping_proposals(id),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, approved, rejected, expired
    priority VARCHAR(20) DEFAULT 'normal',
    assigned_to VARCHAR(255) NOT NULL,
    approver_id VARCHAR(255),
    approval_notes TEXT,
    rejection_reason TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    
    INDEX idx_workflows_status (tenant_id, status, created_at),
    INDEX idx_workflows_assigned (assigned_to, status)
);
```

### 3.3 confidence_scores (historical tracking)
```sql
CREATE TABLE confidence_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(255) NOT NULL,
    mapping_id UUID REFERENCES field_mappings(id),
    proposal_id UUID REFERENCES mapping_proposals(id),
    score DECIMAL(5,4) NOT NULL,
    factors JSONB NOT NULL,  -- {source_quality: 0.9, usage_frequency: 0.8, ...}
    calculated_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_confidence_mapping (mapping_id),
    INDEX idx_confidence_tenant (tenant_id, calculated_at)
);
```

### 3.4 drift_events (extend existing table)
```sql
CREATE TABLE drift_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(255) NOT NULL,
    connector VARCHAR(100) NOT NULL,
    source_table VARCHAR(255) NOT NULL,
    drift_type VARCHAR(50) NOT NULL,  -- table_added, column_added, type_changed, etc.
    severity VARCHAR(20) NOT NULL,  -- low, medium, high, critical
    changes JSONB NOT NULL,
    detected_at TIMESTAMP DEFAULT NOW(),
    
    -- NEW: Link to repair proposal
    repair_proposal_id UUID REFERENCES mapping_proposals(id),
    repair_status VARCHAR(20),  -- pending, auto_applied, hitl_queued, rejected
    
    INDEX idx_drift_connector (tenant_id, connector, detected_at),
    INDEX idx_drift_repair (repair_proposal_id)
);
```

---

## 4. Data Flow Diagrams

### 4.1 LLM Proposal Flow (Normal Path)
```
┌──────────────┐
│ AAM Connector│
│ (Salesforce) │
└──────┬───────┘
       │ POST /dcl/intelligence/propose-mapping
       │ {connector, table, field, sample_values}
       ▼
┌──────────────────────────────────┐
│ DCL Intelligence API             │
│ (LLMProposalService)             │
└──────┬───────────────────────────┘
       │ 1. Check RAG first (fast path)
       ▼
┌──────────────────────────────────┐
│ RAGLookupService                 │
│ (pgvector similarity search)     │
└──────┬───────────────────────────┘
       │ RAG HIT (similarity > 0.85)
       ▼
┌──────────────────────────────────┐
│ ConfidenceScoringService         │
│ (calculate confidence: 0.95)     │
└──────┬───────────────────────────┘
       │ action = "auto_apply"
       ▼
┌──────────────────────────────────┐
│ PostgreSQL                       │
│ INSERT INTO mapping_proposals    │
└──────┬───────────────────────────┘
       │ Return MappingProposal
       ▼
┌──────────────┐
│ AAM Connector│
│ (applies     │
│  mapping)    │
└──────────────┘
```

### 4.2 LLM Proposal Flow (LLM Fallback)
```
┌──────────────┐
│ AAM Connector│
└──────┬───────┘
       │ POST /dcl/intelligence/propose-mapping
       ▼
┌──────────────────────────────────┐
│ LLMProposalService               │
└──────┬───────────────────────────┘
       │ 1. Check RAG first
       ▼
┌──────────────────────────────────┐
│ RAGLookupService                 │
└──────┬───────────────────────────┘
       │ RAG MISS (no similar mapping)
       ▼
┌──────────────────────────────────┐
│ LLMService (Gemini)              │
│ Generate mapping via prompt      │
└──────┬───────────────────────────┘
       │ LLM Response: {canonical_field: "amount"}
       ▼
┌──────────────────────────────────┐
│ ConfidenceScoringService         │
│ (confidence: 0.70 - HITL tier)   │
└──────┬───────────────────────────┘
       │ action = "hitl_queued"
       ▼
┌──────────────────────────────────┐
│ MappingApprovalService           │
│ Submit for human review          │
└──────┬───────────────────────────┘
       │ Create ApprovalWorkflow
       ▼
┌──────────────────────────────────┐
│ PostgreSQL                       │
│ INSERT INTO approval_workflows   │
└──────┬───────────────────────────┘
       │ Notify admin via Slack
       ▼
┌──────────────┐
│ Human        │
│ Reviewer     │
└──────────────┘
```

### 4.3 Drift Repair Flow
```
┌──────────────┐
│ AAM Schema   │
│ Observer     │
│ (detects     │
│  drift)      │
└──────┬───────┘
       │ Drift detected: new field "NewRevenue"
       │ POST /dcl/intelligence/repair-drift
       │ {drift_event_id}
       ▼
┌──────────────────────────────────┐
│ DCL DriftRepairService           │
└──────┬───────────────────────────┘
       │ Extract drifted fields
       ▼
┌──────────────────────────────────┐
│ For each field:                  │
│ 1. RAG lookup                    │
│ 2. LLM fallback                  │
│ 3. Confidence scoring            │
└──────┬───────────────────────────┘
       │ Aggregate repair proposals
       ▼
┌──────────────────────────────────┐
│ RepairProposal                   │
│ - Field1: auto_apply (0.92)      │
│ - Field2: rejected (0.45)        │
└──────┬───────────────────────────┘
       │ Return to AAM
       ▼
┌──────────────┐
│ AAM Connector│
│ (applies     │
│  auto repairs│
│  only)       │
└──────────────┘
```

---

## 5. Implementation Plan

### Phase 2.2: LLM Proposal Migration
1. Extract `RepairAgent.suggest_repairs()` logic from `aam_hybrid/core/repair_agent.py`
2. Create `app/dcl_engine/services/intelligence/llm_proposal_service.py`
3. Create FastAPI router: `app/dcl_engine/routers/intelligence.py`
4. Update AAM to call DCL API instead of RepairAgent
5. Remove LLM dependencies from AAM

### Phase 2.3: RAG Lookup Migration
1. Extract `RAGEngine.retrieve_similar_repairs()` from `aam_hybrid/services/rag_engine/service.py`
2. Create `app/dcl_engine/services/intelligence/rag_lookup_service.py`
3. Integrate with existing `repair_knowledge_base` table (pgvector)
4. Update AAM to call DCL RAG API

### Phase 2.4: Confidence Scoring Migration
1. Extract confidence logic from `RepairAgent` (3-tier thresholds)
2. Create `app/dcl_engine/services/intelligence/confidence_service.py`
3. Implement multi-factor scoring algorithm
4. Update LLM/RAG services to use centralized confidence scoring

### Phase 2.5: Drift Repair Migration
1. Create `app/dcl_engine/services/intelligence/drift_repair_service.py`
2. Coordinate LLM + RAG + Confidence for drift repairs
3. Update AAM schema observer to call DCL for repair proposals
4. Keep drift detection in AAM (observation layer)

### Phase 2.6: Approval Workflow
1. Create `app/dcl_engine/services/intelligence/approval_service.py`
2. Implement HITL queue with PostgreSQL (migrate from Redis)
3. Add Slack/email notifications
4. Create approval API endpoints

---

## 6. Success Criteria

Phase 2 Architecture Design complete when:
- ✅ All 5 service interfaces documented with method signatures
- ✅ All 6 API endpoints specified with request/response schemas
- ✅ Database schema designed (4 tables: proposals, workflows, confidence, drift_events)
- ✅ Data flow diagrams created (3 flows: LLM, LLM fallback, drift repair)
- ✅ Implementation plan reviewed by architect

---

**END OF ARCHITECTURE DESIGN DOCUMENT**
