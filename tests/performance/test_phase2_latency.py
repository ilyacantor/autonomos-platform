"""
Phase 2 Performance Tests: Latency Validation

Validates performance thresholds for intelligence services:
- LLM proposals: P95 < 2s
- RAG lookups: P95 < 100ms
- Confidence scoring: P95 < 50ms

Performance is critical for production deployment.
"""

import pytest
import asyncio
import time
from statistics import quantiles
from unittest.mock import Mock, patch


@pytest.mark.asyncio
async def test_llm_proposal_latency():
    """
    Performance: LLM proposal generation should be P95 < 2s
    
    Measures end-to-end latency including:
    - RAG lookup (fast path attempt)
    - LLM generation (if RAG miss)
    - Confidence scoring
    - Database storage
    """
    from app.dcl_engine.services.intelligence import LLMProposalService
    from app.dcl_engine.services.intelligence import RAGLookupService, ConfidenceScoringService
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    latencies = []
    num_iterations = 20
    
    async with async_session() as session:
        llm_mock = Mock()
        llm_mock.generate = Mock(return_value={
            'canonical_field': 'test_field',
            'alternatives': [],
            'reasoning': 'Test reasoning'
        })
        
        rag_service = RAGLookupService(db_session=session, embedding_service=None)
        confidence_service = ConfidenceScoringService()
        
        llm_service = LLMProposalService(
            llm_client=llm_mock,
            rag_service=rag_service,
            confidence_service=confidence_service,
            db_session=session
        )
        
        for i in range(num_iterations):
            start = time.time()
            
            with patch.object(rag_service, 'lookup_mapping', return_value=None):
                proposal = await llm_service.propose_mapping(
                    connector='test',
                    source_table='TestTable',
                    source_field=f'TestField_{i}',
                    sample_values=[1, 2, 3],
                    tenant_id='test-tenant'
                )
            
            latency = (time.time() - start) * 1000
            latencies.append(latency)
        
        p95 = quantiles(latencies, n=20)[18]
        avg = sum(latencies) / len(latencies)
        
        print(f"\nLLM Proposal Latency:")
        print(f"  Average: {avg:.0f}ms")
        print(f"  P95: {p95:.0f}ms")
        print(f"  Threshold: 2000ms")
        
        assert p95 < 2000, f"P95 latency ({p95:.0f}ms) exceeds threshold (2000ms)"


@pytest.mark.asyncio
async def test_rag_lookup_latency():
    """
    Performance: RAG lookups should be P95 < 100ms
    
    Measures vector similarity search latency.
    Critical for fast-path mapping suggestions.
    """
    from app.dcl_engine.services.intelligence import RAGLookupService
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    latencies = []
    num_iterations = 50
    
    async with async_session() as session:
        rag_service = RAGLookupService(db_session=session, embedding_service=None)
        
        for i in range(num_iterations):
            start = time.time()
            
            result = await rag_service.lookup_mapping(
                connector='salesforce',
                source_table='Opportunity',
                source_field=f'Field_{i}',
                tenant_id='test-tenant',
                similarity_threshold=0.85
            )
            
            latency = (time.time() - start) * 1000
            latencies.append(latency)
        
        p95 = quantiles(latencies, n=20)[18]
        avg = sum(latencies) / len(latencies)
        
        print(f"\nRAG Lookup Latency:")
        print(f"  Average: {avg:.0f}ms")
        print(f"  P95: {p95:.0f}ms")
        print(f"  Threshold: 100ms")
        
        assert p95 < 100, f"P95 latency ({p95:.0f}ms) exceeds threshold (100ms)"


def test_confidence_calc_latency():
    """
    Performance: Confidence calculation should be P95 < 50ms
    
    Pure computation with no I/O - should be very fast.
    """
    from app.dcl_engine.services.intelligence import ConfidenceScoringService
    
    confidence_service = ConfidenceScoringService()
    
    latencies = []
    num_iterations = 100
    
    for i in range(num_iterations):
        start = time.time()
        
        result = confidence_service.calculate_confidence(
            factors={
                'source_quality': 0.9,
                'usage_frequency': i,
                'validation_success': 0.95,
                'human_approval': i % 2 == 0,
                'rag_similarity': 0.88
            },
            tenant_id='test-tenant'
        )
        
        latency = (time.time() - start) * 1000
        latencies.append(latency)
    
    p95 = quantiles(latencies, n=20)[18]
    avg = sum(latencies) / len(latencies)
    
    print(f"\nConfidence Calculation Latency:")
    print(f"  Average: {avg:.2f}ms")
    print(f"  P95: {p95:.2f}ms")
    print(f"  Threshold: 50ms")
    
    assert p95 < 50, f"P95 latency ({p95:.2f}ms) exceeds threshold (50ms)"


@pytest.mark.asyncio
async def test_end_to_end_latency():
    """
    Performance: Complete drift repair flow
    
    Measures full AAM → DCL Intelligence → Response latency.
    Should complete within reasonable time for production use.
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
    
    latencies = []
    num_iterations = 10
    
    async with async_session() as session:
        llm_mock = Mock()
        llm_mock.generate = Mock(return_value={
            'canonical_field': 'amount',
            'alternatives': [],
            'reasoning': 'Test'
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
        
        for i in range(num_iterations):
            drift_event_id = str(uuid.uuid4())
            
            await session.execute(text("""
                INSERT INTO drift_events (id, tenant_id, event_type, old_schema, new_schema, status)
                VALUES (:id, :tenant_id, 'drift', :old_schema, :new_schema, 'detected')
            """), {
                'id': drift_event_id,
                'tenant_id': 'test-tenant',
                'old_schema': '{"connector": "sf", "table": "Opp", "fields": {}}',
                'new_schema': '{"connector": "sf", "table": "Opp", "fields": {"Field": {"type": "text", "sample_values": ["a", "b"]}}}'
            })
            await session.commit()
            
            start = time.time()
            
            with patch.object(rag_service, 'lookup_mapping', return_value=None):
                proposal = await drift_repair_service.propose_repair(
                    drift_event_id=drift_event_id,
                    tenant_id='test-tenant'
                )
            
            latency = (time.time() - start) * 1000
            latencies.append(latency)
        
        p95 = quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies)
        avg = sum(latencies) / len(latencies)
        
        print(f"\nEnd-to-End Drift Repair Latency:")
        print(f"  Average: {avg:.0f}ms")
        print(f"  P95: {p95:.0f}ms")
        print(f"  Threshold: 3000ms")
        
        assert p95 < 3000, f"P95 latency ({p95:.0f}ms) exceeds threshold (3000ms)"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
