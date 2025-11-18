"""
Phase 2 Contract Tests: RACI Boundary Enforcement

Enforces strict RACI compliance - AAM cannot perform intelligence operations.
Critical for achieving 100% RACI compliance target.

Tests verify:
1. AAM has NO direct LLM client access
2. AAM has NO pgvector/vector store access
3. AAM has NO confidence calculation logic
4. AAM can only DETECT drift, NOT propose repairs
5. DCL owns ALL 5 intelligence services
"""

import pytest
import importlib
import sys
from pathlib import Path


class TestAAMCannotCallLLMDirectly:
    """Contract: AAM should not have LLM client (only DCL Intelligence)"""
    
    def test_aam_has_no_llm_imports(self):
        """Verify AAM does not import LLM clients directly"""
        aam_files = [
            "aam_hybrid.core.repair_agent",
            "aam_hybrid.services.rag_engine.service",
            "aam_hybrid.core.canonical_processor",
            "services.aam.schema_observer"
        ]
        
        forbidden_imports = [
            'google.generativeai',
            'openai',
            'anthropic',
            'LLMService',
            'llm_service'
        ]
        
        for module_name in aam_files:
            try:
                module = importlib.import_module(module_name)
                module_code = str(module.__dict__)
                
                for forbidden in forbidden_imports:
                    assert forbidden.lower() not in module_code.lower(), \
                        f"RACI VIOLATION: {module_name} contains forbidden LLM import: {forbidden}"
            
            except ImportError:
                continue
    
    def test_repair_agent_has_no_llm_client(self):
        """RepairAgent should not instantiate LLM clients"""
        try:
            from aam_hybrid.core.repair_agent import RepairAgent
            from unittest.mock import MagicMock
            
            if hasattr(RepairAgent, 'suggest_repairs'):
                # Mock redis_client to avoid connection errors
                mock_redis = MagicMock()
                agent = RepairAgent(redis_client=mock_redis)
                assert not hasattr(agent, 'llm'), \
                    "RACI VIOLATION: RepairAgent has llm client attribute"
                assert not hasattr(agent, 'llm_client'), \
                    "RACI VIOLATION: RepairAgent has llm_client attribute"
        
        except ImportError:
            pytest.skip("RepairAgent not available")


class TestAAMCannotAccessVectorStore:
    """Contract: AAM should not have pgvector access (only DCL Intelligence)"""
    
    def test_aam_has_no_vector_store_imports(self):
        """Verify AAM does not import vector store clients"""
        aam_files = [
            "aam_hybrid.services.rag_engine.service",
            "aam_hybrid.core.repair_agent",
        ]
        
        forbidden_imports = [
            'pgvector',
            'ChromaDB',
            'Pinecone',
            'embedding',
            'sentence_transformers'
        ]
        
        for module_name in aam_files:
            try:
                module = importlib.import_module(module_name)
                module_code = str(module.__dict__)
                
                for forbidden in forbidden_imports:
                    assert forbidden.lower() not in module_code.lower(), \
                        f"RACI VIOLATION: {module_name} contains forbidden vector store import: {forbidden}"
            
            except ImportError:
                continue
    
    def test_rag_engine_delegates_to_dcl(self):
        """AAM RAGEngine should delegate to DCL, not own vector store"""
        try:
            from aam_hybrid.services.rag_engine.service import RAGEngine
            
            engine = RAGEngine()
            
            assert not hasattr(engine, 'vector_store'), \
                "RACI VIOLATION: RAGEngine owns vector_store (should delegate to DCL)"
            assert not hasattr(engine, 'embeddings'), \
                "RACI VIOLATION: RAGEngine owns embeddings (should delegate to DCL)"
        
        except ImportError:
            pytest.skip("RAGEngine not available")


class TestAAMCannotCalculateConfidence:
    """Contract: AAM should not calculate confidence scores (only DCL Intelligence)"""
    
    def test_repair_agent_has_no_confidence_logic(self):
        """RepairAgent should not calculate confidence scores"""
        try:
            from aam_hybrid.core.repair_agent import RepairAgent
            import inspect
            
            if hasattr(RepairAgent, 'suggest_repairs'):
                source = inspect.getsource(RepairAgent)
                
                forbidden_patterns = [
                    'confidence_score',
                    'calculate_confidence',
                    'score_confidence',
                    'confidence =',
                    'AUTO_APPLY_THRESHOLD',
                    'HITL_THRESHOLD'
                ]
                
                for pattern in forbidden_patterns:
                    assert pattern.lower() not in source.lower(), \
                        f"RACI VIOLATION: RepairAgent contains confidence logic: {pattern}"
        
        except ImportError:
            pytest.skip("RepairAgent not available")
    
    def test_aam_has_no_confidence_constants(self):
        """AAM should not define confidence thresholds"""
        aam_modules = [
            "aam_hybrid.core.repair_agent",
            "aam_hybrid.services.rag_engine.service"
        ]
        
        for module_name in aam_modules:
            try:
                module = importlib.import_module(module_name)
                
                forbidden_attrs = [
                    'AUTO_APPLY_THRESHOLD',
                    'HITL_THRESHOLD',
                    'CONFIDENCE_THRESHOLD',
                    'HIGH_CONFIDENCE',
                    'MEDIUM_CONFIDENCE',
                    'LOW_CONFIDENCE'
                ]
                
                for attr in forbidden_attrs:
                    assert not hasattr(module, attr), \
                        f"RACI VIOLATION: {module_name} defines confidence threshold: {attr}"
            
            except ImportError:
                continue


class TestAAMCannotProposeRepairs:
    """Contract: AAM can DETECT drift but NOT propose repairs (only DCL Intelligence)"""
    
    def test_schema_observer_only_detects_drift(self):
        """SchemaObserver should detect drift but not propose repairs"""
        try:
            from aam_hybrid.services.schema_observer.service import SchemaObserver
            import inspect
            
            observer = SchemaObserver()
            
            allowed_methods = [
                'detect_drift',
                'observe_schema',
                'poll_schema',
                'compare_schemas'
            ]
            
            forbidden_methods = [
                'propose_repair',
                'suggest_mapping',
                'generate_mapping',
                'create_mapping',
                'llm_propose'
            ]
            
            for method in forbidden_methods:
                assert not hasattr(observer, method), \
                    f"RACI VIOLATION: SchemaObserver has repair method: {method}"
        
        except ImportError:
            pytest.skip("SchemaObserver not available")
    
    def test_canonical_processor_delegates_to_dcl(self):
        """CanonicalProcessor should call DCL API for repairs"""
        try:
            from aam_hybrid.core.canonical_processor import CanonicalProcessor
            import inspect
            
            source = inspect.getsource(CanonicalProcessor)
            
            assert 'dcl' in source.lower() or 'intelligence' in source.lower(), \
                "RACI VIOLATION: CanonicalProcessor does not call DCL Intelligence API"
            
            forbidden_patterns = [
                'def suggest_repairs',
                'def propose_mapping',
                'def generate_mapping'
            ]
            
            for pattern in forbidden_patterns:
                assert pattern not in source, \
                    f"RACI VIOLATION: CanonicalProcessor contains repair logic: {pattern}"
        
        except ImportError:
            pytest.skip("CanonicalProcessor not available")


class TestDCLOwnsAllIntelligence:
    """Contract: DCL must own ALL 5 intelligence services"""
    
    def test_dcl_has_all_intelligence_services(self):
        """Verify DCL owns all 5 intelligence services"""
        from app.dcl_engine.services.intelligence import (
            LLMProposalService,
            RAGLookupService,
            ConfidenceScoringService,
            DriftRepairService,
            MappingApprovalService
        )
        
        services = [
            LLMProposalService,
            RAGLookupService,
            ConfidenceScoringService,
            DriftRepairService,
            MappingApprovalService
        ]
        
        for service in services:
            assert service is not None, \
                f"DCL Intelligence service not found: {service.__name__}"
    
    def test_dcl_intelligence_router_exists(self):
        """Verify DCL Intelligence router with all endpoints"""
        from app.dcl_engine.routers.intelligence import router
        
        required_endpoints = [
            '/dcl/intelligence/propose-mapping',
            '/dcl/intelligence/rag-lookup',
            '/dcl/intelligence/calculate-confidence',
            '/dcl/intelligence/repair-drift',
            '/dcl/intelligence/submit-for-approval',
            '/dcl/intelligence/approve',
            '/dcl/intelligence/reject',
            '/dcl/intelligence/approval-status'
        ]
        
        routes = [getattr(route, 'path', '') for route in router.routes]
        
        for endpoint in required_endpoints:
            path_exists = any(endpoint in route for route in routes)
            assert path_exists, \
                f"DCL Intelligence endpoint missing: {endpoint}"
    
    def test_dcl_intelligence_tables_exist(self):
        """Verify DCL Intelligence database tables exist"""
        from app.models import (
            MappingProposal,
            ApprovalWorkflow,
            ConfidenceScore,
            DriftEvent
        )
        
        tables = [MappingProposal, ApprovalWorkflow, ConfidenceScore, DriftEvent]
        
        for table in tables:
            assert hasattr(table, '__tablename__'), \
                f"DCL Intelligence table not properly configured: {table.__name__}"


@pytest.mark.integration
class TestRACIComplianceIntegration:
    """Integration test: Verify end-to-end RACI compliance"""
    
    def test_raci_separation_complete(self):
        """Verify complete separation of responsibilities"""
        from unittest.mock import MagicMock
        aam_violations = []
        dcl_coverage = []
        
        try:
            from aam_hybrid.core.repair_agent import RepairAgent
            mock_redis = MagicMock()
            agent = RepairAgent(redis_client=mock_redis)
            if hasattr(agent, 'llm'):
                aam_violations.append("RepairAgent has LLM client")
        except ImportError:
            pass
        
        try:
            from app.dcl_engine.services.intelligence import (
                LLMProposalService,
                RAGLookupService,
                ConfidenceScoringService
            )
            dcl_coverage.extend(['LLM', 'RAG', 'Confidence'])
        except ImportError:
            pass
        
        assert len(aam_violations) == 0, \
            f"RACI violations in AAM: {', '.join(aam_violations)}"
        
        assert len(dcl_coverage) >= 3, \
            f"DCL does not cover all intelligence services: {dcl_coverage}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
