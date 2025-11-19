"""
Phase 2 Integration Tests: Intelligence Flow End-to-End

Tests complete E2E flows through intelligence services:
1. LLM proposal generation
2. RAG lookup
3. Confidence calculation
4. Drift repair workflow
5. Approval workflow

All tests verify AAM → DCL Intelligence API → Response flow.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime


@pytest.mark.asyncio
async def test_llm_proposal_flow():
    """
    Integration: AAM → DCL Intelligence API → LLM → Response
    
    Flow:
    1. AAM detects new field
    2. AAM calls DCL /propose-mapping endpoint
    3. DCL checks RAG (miss)
    4. DCL calls LLM
    5. DCL scores confidence
    6. DCL returns proposal to AAM
    """
    from app.dcl_engine.services.intelligence import LLMProposalService
    from app.dcl_engine.llm_service import LLMService
    from app.dcl_engine.services.intelligence import RAGLookupService, ConfidenceScoringService
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import text
    
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE mapping_proposals (
                id TEXT PRIMARY KEY,
                tenant_id TEXT,
                connector TEXT,
                source_table TEXT,
                source_field TEXT,
                canonical_entity TEXT,
                canonical_field TEXT,
                confidence REAL,
                reasoning TEXT,
                alternatives TEXT,
                action TEXT,
                source TEXT,
                created_at TIMESTAMP
            )
        """))
    
    async with async_session() as session:
        llm_mock = Mock()
        llm_mock.generate = Mock(return_value={
            'canonical_field': 'amount',
            'alternatives': [],
            'reasoning': 'Field stores monetary values'
        })
        
        rag_service = RAGLookupService(db_session=session, embedding_service=None)
        confidence_service = ConfidenceScoringService()
        
        llm_service = LLMProposalService(
            llm_client=llm_mock,
            rag_service=rag_service,
            confidence_service=confidence_service,
            db_session=session
        )
        
        with patch.object(rag_service, 'lookup_mapping', return_value=None):
            proposal = await llm_service.propose_mapping(
                connector='salesforce',
                source_table='Opportunity',
                source_field='Amount',
                sample_values=[1000.0, 2500.0, 750.0],
                tenant_id='test-tenant'
            )
        
        assert proposal is not None
        assert proposal.canonical_field == 'amount'
        assert proposal.confidence > 0
        assert proposal.action in ['auto_apply', 'hitl_queued', 'rejected']
        assert proposal.source == 'llm'


@pytest.mark.asyncio
async def test_rag_lookup_flow():
    """
    Integration: AAM → DCL RAG API → pgvector → Response
    
    Flow:
    1. AAM needs mapping suggestion
    2. AAM calls DCL /rag-lookup endpoint
    3. DCL performs vector similarity search
    4. DCL returns best match (if found)
    """
    from app.dcl_engine.services.intelligence import RAGLookupService
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        rag_service = RAGLookupService(db_session=session, embedding_service=None)
        
        result = await rag_service.lookup_mapping(
            connector='salesforce',
            source_table='Opportunity',
            source_field='Amount',
            tenant_id='test-tenant',
            similarity_threshold=0.85
        )
        
        assert result is None or hasattr(result, 'canonical_field')


@pytest.mark.asyncio
async def test_confidence_calculation_flow():
    """
    Integration: Proposal → DCL Confidence API → Score
    
    Flow:
    1. Proposal generated (LLM or RAG)
    2. DCL calculates multi-factor confidence
    3. DCL determines action tier
    4. Returns score + recommendations
    """
    from app.dcl_engine.services.intelligence import ConfidenceScoringService
    
    confidence_service = ConfidenceScoringService()
    
    result = confidence_service.calculate_confidence(
        factors={
            'source_quality': 0.95,
            'usage_frequency': 100,
            'validation_success': 0.95,
            'human_approval': True,
            'rag_similarity': 0.92
        },
        tenant_id='test-tenant'
    )
    
    assert result.score >= 0.0 and result.score <= 1.0
    assert result.tier in ['auto_apply', 'hitl_queued', 'rejected']
    assert isinstance(result.factors, dict)
    assert isinstance(result.recommendations, list)
    
    assert result.tier == 'auto_apply'
    assert result.score >= 0.85


@pytest.mark.asyncio
async def test_drift_repair_flow():
    """
    Integration: AAM detects drift → DCL proposes repair → AAM applies
    
    Flow:
    1. AAM detects schema drift
    2. AAM creates DriftEvent
    3. AAM calls DCL /repair-drift endpoint
    4. DCL analyzes drifted fields
    5. DCL generates repair proposals (LLM + RAG)
    6. DCL returns RepairProposal to AAM
    7. AAM applies auto-approved repairs
    """
    from app.dcl_engine.services.intelligence import (
        DriftRepairService,
        LLMProposalService,
        RAGLookupService,
        ConfidenceScoringService
    )
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import text
    import uuid
    
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE drift_events (
                id TEXT PRIMARY KEY,
                tenant_id TEXT,
                connection_id TEXT,
                event_type TEXT,
                old_schema TEXT,
                new_schema TEXT,
                status TEXT,
                repair_proposal_id TEXT,
                repair_status TEXT
            )
        """))
    
    async with async_session() as session:
        drift_event_id = str(uuid.uuid4())
        
        await session.execute(text("""
            INSERT INTO drift_events (id, tenant_id, event_type, old_schema, new_schema, status)
            VALUES (:id, :tenant_id, 'schema_drift', :old_schema, :new_schema, 'detected')
        """), {
            'id': drift_event_id,
            'tenant_id': 'test-tenant',
            'old_schema': '{"connector": "salesforce", "table": "Opportunity", "fields": {}}',
            'new_schema': '{"connector": "salesforce", "table": "Opportunity", "fields": {"Amount": {"type": "currency", "sample_values": [1000, 2000]}}}'
        })
        await session.commit()
        
        llm_mock = Mock()
        llm_mock.generate = Mock(return_value={
            'canonical_field': 'amount',
            'alternatives': [],
            'reasoning': 'Monetary value field'
        })
        
        rag_service = RAGLookupService(db_session=session, embedding_service=None)
        confidence_service = ConfidenceScoringService()
        
        llm_service = LLMProposalService(
            llm_client=llm_mock,
            rag_service=rag_service,
            confidence_service=confidence_service,
            db_session=session
        )
        
        drift_repair_service = DriftRepairService(
            llm_service=llm_service,
            rag_service=rag_service,
            confidence_service=confidence_service,
            db_session=session
        )
        
        with patch.object(rag_service, 'lookup_mapping', return_value=None):
            proposal = await drift_repair_service.propose_repair(
                drift_event_id=drift_event_id,
                tenant_id='test-tenant'
            )
        
        assert proposal is not None
        assert len(proposal.field_repairs) > 0
        assert proposal.overall_confidence >= 0
        assert proposal.auto_applied_count + proposal.hitl_queued_count + proposal.rejected_count == len(proposal.field_repairs)


@pytest.mark.asyncio
async def test_approval_workflow_flow():
    """
    Integration: Proposal → HITL queue → Approval → Mapping creation
    
    Flow:
    1. Medium-confidence proposal generated
    2. DCL creates ApprovalWorkflow
    3. DCL assigns to tenant admin
    4. Human approves via /approve endpoint
    5. DCL creates FieldMapping from proposal
    """
    from app.dcl_engine.services.intelligence import MappingApprovalService
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import text
    import uuid
    
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE approval_workflows (
                id TEXT PRIMARY KEY,
                tenant_id TEXT,
                proposal_id TEXT,
                status TEXT,
                priority TEXT,
                assigned_to TEXT,
                approver_id TEXT,
                approval_notes TEXT,
                rejection_reason TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                expires_at TIMESTAMP
            )
        """))
        
        await conn.execute(text("""
            CREATE TABLE users (
                id TEXT PRIMARY KEY,
                tenant_id TEXT,
                is_admin TEXT
            )
        """))
        
        await conn.execute(text("""
            INSERT INTO users (id, tenant_id, is_admin)
            VALUES ('admin-1', 'test-tenant', 'true')
        """))
    
    async with async_session() as session:
        approval_service = MappingApprovalService(
            db_session=session,
            notification_service=None
        )
        
        proposal_id = str(uuid.uuid4())
        
        workflow = await approval_service.submit_for_approval(
            proposal_id=proposal_id,
            tenant_id='test-tenant',
            priority='normal'
        )
        
        assert workflow is not None
        assert workflow.status == 'pending'
        assert workflow.assigned_to is not None
        assert workflow.expires_at > workflow.created_at
        
        status = await approval_service.get_approval_status(proposal_id)
        assert status is not None
        assert status.status == 'pending'


@pytest.mark.asyncio
async def test_llm_failure_invokes_resilience_fallback():
    """
    P3-15: Verify resilience decorator invokes fallback when LLM fails
    
    Tests END-TO-END failure path through resilience layer:
    - LLM service fails (all retries exhausted)
    - Resilience decorator catches failure
    - Fallback method (_heuristic_fallback) is invoked
    - System degrades gracefully with fallback result
    
    This proves the resilience layer correctly escalates to fallback.
    """
    from app.dcl_engine.services.intelligence import (
        LLMProposalService,
        RAGLookupService,
        ConfidenceScoringService
    )
    
    # Real confidence service (needed by fallback)
    confidence_service = ConfidenceScoringService()
    
    # Mock RAG service that returns None (cache miss) without DB dependency
    rag_mock = AsyncMock(spec=RAGLookupService)
    rag_mock.lookup_mapping = AsyncMock(return_value=None)
    rag_mock.index_mapping = AsyncMock(return_value=None)
    
    # Mock DB session with required methods
    db_mock = AsyncMock()
    db_mock.execute = AsyncMock(return_value=AsyncMock(scalar_one_or_none=AsyncMock(return_value=None)))
    db_mock.commit = AsyncMock()
    db_mock.rollback = AsyncMock()
    db_mock.close = AsyncMock()
    
    # Mock LLM that always fails
    llm_mock = AsyncMock()
    llm_mock.generate = AsyncMock(side_effect=Exception("LLM service unavailable"))
    
    service = LLMProposalService(
        llm_client=llm_mock,
        rag_service=rag_mock,
        confidence_service=confidence_service,
        db_session=db_mock
    )
    
    # Call the service - should fail LLM but succeed via fallback
    proposal = await service.propose_mapping(
        connector='salesforce',
        source_table='Opportunity',
        source_field='TotalAmount',
        sample_values=[1000.0, 2000.0, 3000.0],
        tenant_id='test-tenant'
    )
    
    # Verify fallback was invoked
    assert proposal is not None, "Resilience layer should return fallback result"
    assert proposal.source == 'heuristic', f"Expected heuristic fallback, got source='{proposal.source}'"
    assert proposal.action == 'hitl_queued', "Fallback proposals should be queued for human review"
    assert proposal.canonical_field is not None, "Fallback should propose canonical field"
    
    # Verify LLM was attempted (retries exhausted before fallback)
    assert llm_mock.generate.call_count >= 1, "LLM should be attempted before fallback"


@pytest.mark.asyncio
async def test_confidence_scoring_all_three_tiers():
    """
    P3-15: Verify confidence scoring tier boundaries
    
    Requirements:
    - High confidence (≥0.85) → auto_apply
    - Medium confidence (0.60-0.84) → hitl_queued
    - Low confidence (<0.60) → rejected
    """
    from app.dcl_engine.services.intelligence import ConfidenceScoringService
    
    service = ConfidenceScoringService()
    
    # Tier 1: High confidence → auto_apply
    high_result = service.calculate_confidence(
        factors={
            'rag_similarity': 0.95,
            'usage_frequency': 100,
            'validation_success': 1.0,
            'source_quality': 0.9,
            'human_approval': True
        },
        tenant_id='test-tenant'
    )
    assert high_result.score >= 0.85, f"High confidence should be ≥0.85, got {high_result.score}"
    assert high_result.tier == 'auto_apply', f"Expected auto_apply, got {high_result.tier}"
    
    # Tier 2: Medium confidence → hitl_queued
    # Target ~0.75 score with weights: validation(30%), human(25%), source(20%), usage(15%), rag(10%)
    medium_result = service.calculate_confidence(
        factors={
            'rag_similarity': 0.80,           # 0.80 × 0.10 = 0.080
            'usage_frequency': 100,           # log10(101)/3 ≈ 0.67 → 0.67 × 0.15 = 0.100
            'validation_success': 0.85,       # 0.85 × 0.30 = 0.255
            'source_quality': 0.85,           # 0.85 × 0.20 = 0.170
            'human_approval': False           # 0.00 × 0.25 = 0.000
        },                                    # Total ≈ 0.605
        tenant_id='test-tenant'
    )
    assert 0.60 <= medium_result.score < 0.85, f"Medium confidence should be 0.60-0.84, got {medium_result.score}"
    assert medium_result.tier == 'hitl_queued', f"Expected hitl_queued, got {medium_result.tier}"
    
    # Tier 3: Low confidence → rejected
    low_result = service.calculate_confidence(
        factors={
            'rag_similarity': 0.30,
            'usage_frequency': 0,
            'validation_success': 0.4,
            'source_quality': 0.3,
            'human_approval': False
        },
        tenant_id='test-tenant'
    )
    assert low_result.score < 0.60, f"Low confidence should be <0.60, got {low_result.score}"
    assert low_result.tier == 'rejected', f"Expected rejected, got {low_result.tier}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
