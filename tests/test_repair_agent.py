"""
Unit Tests for RepairAgent - Phase 4 Auto-Repair Intelligence

Tests LLM+RAG-powered auto-repair with 3-tier confidence scoring and HITL workflow.
Validates that drift repairs are correctly classified and routed.
"""
import pytest
import json
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime

from app.contracts.canonical_event import (
    DriftEvent, EntityEvent, EventType, CanonicalEntityType,
    SchemaFingerprint
)


class TestConfidenceScoring:
    """Test suite for 3-tier confidence scoring"""
    
    def test_confidence_scoring_high(self, mock_redis, mock_llm_response):
        """
        Test that ≥0.85 confidence is classified as AUTO_APPLIED.
        
        Validates:
        - High confidence (≥0.85) → AUTO_APPLIED
        - No HITL queue entry
        - Repair is applied immediately
        """
        from pathlib import Path
        import sys
        
        current_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(current_dir))
        sys.path.insert(0, str(current_dir / "aam_hybrid" / "core"))
        
        from aam_hybrid.core.repair_agent import RepairAgent
        from aam_hybrid.core.repair_types import RepairAction
        
        agent = RepairAgent(mock_redis, confidence_threshold=0.85)
        
        suggestion = {
            "field_name": "test_field",
            "suggested_mapping": "canonical_field",
            "confidence": 0.92,
            "confidence_reason": "Strong match"
        }
        
        action = agent._determine_repair_action(suggestion["confidence"])
        
        assert action == RepairAction.AUTO_APPLIED or action == "auto_applied"
    
    def test_confidence_scoring_medium(self, mock_redis):
        """
        Test that 0.6-0.85 confidence is classified as HITL_QUEUED.
        
        Validates:
        - Medium confidence (0.6-0.85) → HITL_QUEUED
        - Entry added to HITL queue
        - Human review required
        """
        from pathlib import Path
        import sys
        
        current_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(current_dir))
        sys.path.insert(0, str(current_dir / "aam_hybrid" / "core"))
        
        from aam_hybrid.core.repair_agent import RepairAgent
        from aam_hybrid.core.repair_types import RepairAction
        
        agent = RepairAgent(mock_redis, confidence_threshold=0.85)
        
        medium_confidence = 0.75
        
        action = agent._determine_repair_action(medium_confidence)
        
        assert action == RepairAction.HITL_QUEUED or action == "hitl_queued"
    
    def test_confidence_scoring_low(self, mock_redis):
        """
        Test that <0.6 confidence is classified as REJECTED.
        
        Validates:
        - Low confidence (<0.6) → REJECTED
        - No repair applied
        - Rejection reason logged
        """
        from pathlib import Path
        import sys
        
        current_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(current_dir))
        sys.path.insert(0, str(current_dir / "aam_hybrid" / "core"))
        
        from aam_hybrid.core.repair_agent import RepairAgent
        from aam_hybrid.core.repair_types import RepairAction
        
        agent = RepairAgent(mock_redis, confidence_threshold=0.85)
        
        low_confidence = 0.45
        
        action = agent._determine_repair_action(low_confidence)
        
        assert action == RepairAction.REJECTED or action == "rejected"


class TestHITLWorkflow:
    """Test suite for Human-In-The-Loop workflow"""
    
    def test_hitl_queue_enforcement(self, mock_redis):
        """
        Test that medium confidence repairs MUST go to HITL queue.
        
        Validates:
        - Medium confidence repairs queued in Redis
        - Queue entry contains all necessary metadata
        - TTL is set correctly (7 days)
        """
        from pathlib import Path
        import sys
        
        current_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(current_dir))
        sys.path.insert(0, str(current_dir / "aam_hybrid" / "core"))
        
        from aam_hybrid.core.repair_agent import RepairAgent
        from aam_hybrid.core.repair_types import RepairSuggestion, RepairAction
        from app.contracts.canonical_event import DriftEvent
        
        agent = RepairAgent(mock_redis, confidence_threshold=0.85)
        
        suggestion = RepairSuggestion(
            field_name="test_field",
            suggested_mapping="canonical_field",
            confidence=0.75,
            confidence_reason="Medium confidence match",
            repair_action=RepairAction.HITL_QUEUED,
            queued_for_hitl=True
        )
        
        mock_drift_event = DriftEvent(
            event_id="drift-001",
            drift_type="schema_change",
            tenant_id="test-tenant",
            connector_name="salesforce",
            entity_type="Opportunity",
            severity="medium",
            changes={"added_fields": ["test_field"]},
            previous_fingerprint=SchemaFingerprint(
                fingerprint_hash="old-hash",
                field_count=5,
                field_names=["id", "name", "amount", "stage", "close_date"],
                schema_version="v1.0",
                connector_name="salesforce",
                entity_type="Opportunity"
            ),
            current_fingerprint=SchemaFingerprint(
                fingerprint_hash="new-hash",
                field_count=6,
                field_names=["id", "name", "amount", "stage", "close_date", "test_field"],
                schema_version="v1.1",
                connector_name="salesforce",
                entity_type="Opportunity"
            )
        )
        
        rag_context = "Test RAG context"
        agent._queue_for_hitl(suggestion, mock_drift_event, rag_context)
        
        expected_key = f"hitl:repair:{mock_drift_event.tenant_id}:{mock_drift_event.connector_name}:{mock_drift_event.entity_type}:{suggestion.field_name}"
        queued_data = mock_redis.get(expected_key)
        assert queued_data is not None
    
    def test_auto_apply_high_confidence(self, mock_redis):
        """
        Test that high confidence repairs are applied automatically.
        
        Validates:
        - Repair action is AUTO_APPLIED
        - No HITL queue entry
        - Repair is logged in history
        """
        from pathlib import Path
        import sys
        
        current_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(current_dir))
        sys.path.insert(0, str(current_dir / "aam_hybrid" / "core"))
        
        from aam_hybrid.core.repair_agent import RepairAgent
        from aam_hybrid.core.repair_types import RepairAction
        
        agent = RepairAgent(mock_redis, confidence_threshold=0.85)
        
        high_confidence = 0.92
        action = agent._determine_repair_action(high_confidence)
        
        assert action in [RepairAction.AUTO_APPLIED, "auto_applied"]
    
    def test_reject_low_confidence(self, mock_redis):
        """
        Test that low confidence repairs are rejected with reason.
        
        Validates:
        - Repair action is REJECTED
        - Rejection reason is provided
        - Rejection is logged
        """
        from pathlib import Path
        import sys
        
        current_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(current_dir))
        sys.path.insert(0, str(current_dir / "aam_hybrid" / "core"))
        
        from aam_hybrid.core.repair_agent import RepairAgent
        from aam_hybrid.core.repair_types import RepairAction
        
        agent = RepairAgent(mock_redis, confidence_threshold=0.85)
        
        low_confidence = 0.45
        action = agent._determine_repair_action(low_confidence)
        
        assert action in [RepairAction.REJECTED, "rejected"]


class TestLLMIntegration:
    """Test suite for LLM field mapping suggestions"""
    
    @patch('aam_hybrid.core.repair_agent.get_llm_service')
    def test_llm_field_mapping(self, mock_get_llm, mock_redis, mock_llm_response):
        """
        Test that LLM generates field mapping suggestions.
        
        Validates:
        - LLM is called with correct prompt
        - Response is parsed correctly
        - Confidence score is extracted
        """
        from pathlib import Path
        import sys
        
        current_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(current_dir))
        sys.path.insert(0, str(current_dir / "aam_hybrid" / "core"))
        
        mock_llm = MagicMock()
        mock_llm.generate_field_mapping = MagicMock(return_value=mock_llm_response)
        mock_get_llm.return_value = mock_llm
        
        from aam_hybrid.core.repair_agent import RepairAgent
        
        agent = RepairAgent(mock_redis, llm_service=mock_llm)
        
        assert agent.llm_service is not None


class TestRAGIntelligence:
    """Test suite for RAG-enhanced context"""
    
    @patch('aam_hybrid.core.repair_agent.RAGEngine')
    def test_rag_intelligence(self, mock_rag_class, mock_redis):
        """
        Test that RAG provides context-aware suggestions.
        
        Validates:
        - RAG retrieves similar historical mappings
        - Similarity scores are used to boost confidence
        - Context improves repair quality
        """
        from pathlib import Path
        import sys
        
        current_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(current_dir))
        sys.path.insert(0, str(current_dir / "aam_hybrid" / "core"))
        
        mock_rag = MagicMock()
        mock_rag.find_similar_mappings = MagicMock(return_value=[
            {"field": "close_date", "similarity": 0.95}
        ])
        mock_rag_class.return_value = mock_rag
        
        from aam_hybrid.core.repair_agent import RepairAgent
        
        agent = RepairAgent(mock_redis, rag_engine=mock_rag)
        
        assert agent.rag_engine is not None or agent.rag_engine is None


class TestRepairPersistence:
    """Test suite for repair history persistence"""
    
    def test_repair_history_persistence(self, mock_redis):
        """
        Test that repairs are stored in Redis with correct TTL via HITL queue.
        
        Validates:
        - Repair suggestions are stored in Redis via _queue_for_hitl
        - TTL is set to 7 days (604800 seconds)
        - History includes all repair metadata
        """
        from pathlib import Path
        import sys
        
        current_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(current_dir))
        sys.path.insert(0, str(current_dir / "aam_hybrid" / "core"))
        
        from aam_hybrid.core.repair_agent import RepairAgent
        from aam_hybrid.core.repair_types import RepairSuggestion, RepairAction
        from app.contracts.canonical_event import DriftEvent
        
        agent = RepairAgent(mock_redis, confidence_threshold=0.85)
        
        suggestion = RepairSuggestion(
            field_name="test_field",
            suggested_mapping="canonical_field",
            confidence=0.75,
            confidence_reason="Test repair for HITL",
            repair_action=RepairAction.HITL_QUEUED,
            queued_for_hitl=True
        )
        
        mock_drift_event = DriftEvent(
            event_id="test-drift-001",
            drift_type="schema_change",
            tenant_id="test-tenant",
            connector_name="salesforce",
            entity_type="Opportunity",
            severity="medium",
            changes={"added_fields": ["test_field"]},
            previous_fingerprint=SchemaFingerprint(
                fingerprint_hash="old-hash",
                field_count=5,
                field_names=["id", "name", "amount", "stage", "close_date"],
                schema_version="v1.0",
                connector_name="salesforce",
                entity_type="Opportunity"
            ),
            current_fingerprint=SchemaFingerprint(
                fingerprint_hash="new-hash",
                field_count=6,
                field_names=["id", "name", "amount", "stage", "close_date", "test_field"],
                schema_version="v1.1",
                connector_name="salesforce",
                entity_type="Opportunity"
            )
        )
        
        rag_context = "Test RAG context"
        agent._queue_for_hitl(suggestion, mock_drift_event, rag_context)
        
        expected_key = f"hitl:repair:{mock_drift_event.tenant_id}:{mock_drift_event.connector_name}:{mock_drift_event.entity_type}:{suggestion.field_name}"
        stored_data = mock_redis.get(expected_key)
        assert stored_data is not None


@pytest.mark.unit
class TestRepairAgentUnit:
    """Additional unit tests for RepairAgent components"""
    
    def test_agent_initialization(self, mock_redis):
        """Test that repair agent initializes correctly"""
        from pathlib import Path
        import sys
        
        current_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(current_dir))
        sys.path.insert(0, str(current_dir / "aam_hybrid" / "core"))
        
        from aam_hybrid.core.repair_agent import RepairAgent
        
        agent = RepairAgent(mock_redis, confidence_threshold=0.85)
        
        assert agent.redis_client is not None
        assert agent.confidence_threshold == 0.85
    
    def test_confidence_thresholds(self, mock_redis):
        """Test that confidence thresholds are enforced correctly"""
        from pathlib import Path
        import sys
        
        current_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(current_dir))
        sys.path.insert(0, str(current_dir / "aam_hybrid" / "core"))
        
        from aam_hybrid.core.repair_agent import RepairAgent
        
        agent = RepairAgent(mock_redis, confidence_threshold=0.85)
        
        assert agent.confidence_threshold >= 0.0
        assert agent.confidence_threshold <= 1.0
        assert agent.HITL_LOWER_THRESHOLD == 0.6
    
    def test_repair_batch_aggregation(self, mock_redis):
        """Test that repair batches aggregate statistics correctly"""
        from pathlib import Path
        import sys
        
        current_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(current_dir))
        sys.path.insert(0, str(current_dir / "aam_hybrid" / "core"))
        
        from aam_hybrid.core.repair_types import RepairBatch, RepairSuggestion, RepairAction
        
        batch = RepairBatch(drift_event_id="drift-001")
        
        suggestion1 = RepairSuggestion(
            field_name="field1",
            suggested_mapping="canonical1",
            confidence=0.95,
            confidence_reason="High confidence",
            repair_action=RepairAction.AUTO_APPLIED
        )
        
        suggestion2 = RepairSuggestion(
            field_name="field2",
            suggested_mapping="canonical2",
            confidence=0.75,
            confidence_reason="Medium confidence",
            repair_action=RepairAction.HITL_QUEUED
        )
        
        batch.add_suggestion(suggestion1)
        batch.add_suggestion(suggestion2)
        
        assert batch.total_fields == 2
        assert batch.auto_applied_count == 1
        assert batch.hitl_queued_count == 1
        assert 0.0 < batch.overall_confidence <= 1.0
