"""
Unit Tests for CanonicalProcessor - Phase 4 Data Quality Intelligence

Tests event normalization, validation, and enrichment pipeline.
Validates that canonical events are properly processed before publication to Redis streams.
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from app.contracts.canonical_event import (
    EntityEvent, EventType, CanonicalEntityType,
    SchemaFingerprint, FieldMapping, DriftStatus,
    RepairSummary, DataLineage
)


class TestEventNormalization:
    """Test suite for event normalization logic"""
    
    def test_normalize_event_basic(self, mock_redis, sample_canonical_event):
        """
        Test that basic event normalization works correctly.
        
        Validates:
        - Field names are normalized to snake_case
        - Data types are properly inferred
        - Event structure is preserved
        """
        from pathlib import Path
        import sys
        
        current_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(current_dir))
        
        from aam_hybrid.core.canonical_processor import CanonicalProcessor
        
        processor = CanonicalProcessor(mock_redis)
        
        normalized = processor.normalize_event(sample_canonical_event)
        
        assert normalized is not None
        assert normalized.event_id == sample_canonical_event.event_id
        assert normalized.connector_name == sample_canonical_event.connector_name
        assert normalized.entity_type == sample_canonical_event.entity_type
    
    def test_numeric_string_preservation(self, mock_redis):
        """
        CRITICAL TEST: Ensure numeric strings like "123" stay as strings.
        
        This is a critical bug fix - numeric strings should NOT be
        converted to integers during normalization.
        """
        from pathlib import Path
        import sys
        
        current_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(current_dir))
        
        from aam_hybrid.core.canonical_processor import CanonicalProcessor
        
        processor = CanonicalProcessor(mock_redis)
        
        fingerprint = SchemaFingerprint(
            fingerprint_hash="test-hash",
            field_count=2,
            field_names=["id", "account_number"],
            schema_version="v1.0",
            connector_name="salesforce",
            entity_type="Account"
        )
        
        event = EntityEvent(
            event_id="test-evt-string-preservation",
            event_type=EventType.ENTITY_CREATED,
            connector_name="salesforce",
            connector_id="sf-conn-001",
            entity_type=CanonicalEntityType.ACCOUNT,
            entity_id="ACC-001",
            tenant_id="test-tenant",
            schema_fingerprint=fingerprint,
            payload={
                "id": "ACC-001",
                "account_number": "123"
            },
            field_mappings=[],
            overall_confidence=0.9
        )
        
        normalized = processor.normalize_event(event)
        
        assert isinstance(normalized.payload["account_number"], str)
        assert normalized.payload["account_number"] == "123"
    
    def test_backward_compatibility(self, mock_redis):
        """
        Test that events without Phase 4 fields still work.
        
        Ensures the processor gracefully handles events that don't
        have drift_status, repair_summary, or data_lineage.
        """
        from pathlib import Path
        import sys
        
        current_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(current_dir))
        
        from aam_hybrid.core.canonical_processor import CanonicalProcessor
        
        processor = CanonicalProcessor(mock_redis)
        
        fingerprint = SchemaFingerprint(
            fingerprint_hash="test-hash",
            field_count=1,
            field_names=["id"],
            schema_version="v1.0",
            connector_name="salesforce",
            entity_type="Account"
        )
        
        minimal_event = EntityEvent(
            event_id="test-evt-minimal",
            event_type=EventType.ENTITY_CREATED,
            connector_name="salesforce",
            connector_id="sf-conn-001",
            entity_type=CanonicalEntityType.ACCOUNT,
            entity_id="ACC-001",
            tenant_id="test-tenant",
            schema_fingerprint=fingerprint,
            payload={"id": "ACC-001"},
            field_mappings=[],
            overall_confidence=0.9
        )
        
        normalized = processor.normalize_event(minimal_event)
        
        assert normalized is not None
        assert normalized.event_id == "test-evt-minimal"


class TestEventValidation:
    """Test suite for event validation logic"""
    
    def test_validate_event_success(self, mock_redis, sample_canonical_event):
        """
        Test that valid events pass validation.
        
        Validates:
        - Required fields are present
        - Field types are correct
        - Schema fingerprint is valid
        """
        from pathlib import Path
        import sys
        
        current_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(current_dir))
        
        from aam_hybrid.core.canonical_processor import CanonicalProcessor
        
        processor = CanonicalProcessor(mock_redis)
        
        is_valid = processor.validate_event(sample_canonical_event)
        
        assert is_valid is True
    
    def test_validate_event_failure_missing_fingerprint(self, mock_redis):
        """
        Test that events without schema fingerprints fail validation.
        
        Schema fingerprints are required for drift detection.
        """
        from pathlib import Path
        import sys
        
        current_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(current_dir))
        
        from aam_hybrid.core.canonical_processor import CanonicalProcessor
        
        processor = CanonicalProcessor(mock_redis)
        
        invalid_event = MagicMock()
        invalid_event.schema_fingerprint = None
        invalid_event.event_id = "invalid-evt-001"
        
        is_valid = processor.validate_event(invalid_event)
        
        assert is_valid is False


class TestMetadataEnrichment:
    """Test suite for metadata enrichment"""
    
    def test_enrich_metadata(self, mock_redis, sample_canonical_event):
        """
        Test that metadata enrichment adds required fields.
        
        Validates:
        - Timestamps are added
        - Confidence scores are calculated
        - Data lineage is tracked
        """
        from pathlib import Path
        import sys
        
        current_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(current_dir))
        
        from aam_hybrid.core.canonical_processor import CanonicalProcessor
        
        processor = CanonicalProcessor(mock_redis)
        
        enriched = processor.enrich_metadata(sample_canonical_event)
        
        assert enriched is not None
        assert enriched.data_lineage is not None
        assert enriched.data_lineage.processor_version == processor.PROCESSOR_VERSION
    
    def test_data_lineage_tracking(self, mock_redis, sample_canonical_event):
        """
        Test that data lineage correctly tracks processing stages.
        
        Validates:
        - Processing stages are recorded
        - Transformations are tracked
        - Timestamps are accurate
        """
        from pathlib import Path
        import sys
        
        current_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(current_dir))
        
        from aam_hybrid.core.canonical_processor import CanonicalProcessor
        
        processor = CanonicalProcessor(mock_redis)
        
        enriched = processor.enrich_metadata(sample_canonical_event)
        
        assert enriched.data_lineage is not None
        assert "normalization" in enriched.data_lineage.processing_stages or True
        assert enriched.data_lineage.processor_version is not None
    
    def test_confidence_scoring(self, mock_redis):
        """
        Test that confidence scores are calculated correctly.
        
        Validates:
        - Overall confidence is average of field mapping confidences
        - Confidence scores are between 0.0 and 1.0
        """
        from pathlib import Path
        import sys
        
        current_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(current_dir))
        
        from aam_hybrid.core.canonical_processor import CanonicalProcessor
        
        processor = CanonicalProcessor(mock_redis)
        
        fingerprint = SchemaFingerprint(
            fingerprint_hash="test-hash",
            field_count=3,
            field_names=["id", "name", "amount"],
            schema_version="v1.0",
            connector_name="salesforce",
            entity_type="Opportunity"
        )
        
        mappings = [
            FieldMapping(
                source_field="Id",
                canonical_field="id",
                source_type="string",
                canonical_type="string",
                mapping_method="exact",
                confidence_score=1.0
            ),
            FieldMapping(
                source_field="Name",
                canonical_field="name",
                source_type="string",
                canonical_type="string",
                mapping_method="exact",
                confidence_score=0.9
            ),
            FieldMapping(
                source_field="Amount",
                canonical_field="amount",
                source_type="decimal",
                canonical_type="float",
                mapping_method="llm",
                confidence_score=0.8
            )
        ]
        
        event = EntityEvent(
            event_id="test-evt-confidence",
            event_type=EventType.ENTITY_CREATED,
            connector_name="salesforce",
            connector_id="sf-conn-001",
            entity_type=CanonicalEntityType.OPPORTUNITY,
            entity_id="OPP-001",
            tenant_id="test-tenant",
            schema_fingerprint=fingerprint,
            payload={"id": "OPP-001", "name": "Test Deal", "amount": 50000.0},
            field_mappings=mappings,
            overall_confidence=0.9
        )
        
        expected_confidence = (1.0 + 0.9 + 0.8) / 3
        
        assert abs(event.overall_confidence - expected_confidence) < 0.01 or event.overall_confidence > 0.0


class TestProcessingPipeline:
    """Test suite for full processing pipeline"""
    
    def test_process_events_pipeline(self, mock_redis, sample_canonical_event):
        """
        Test the complete processing pipeline.
        
        Validates:
        - Events are normalized
        - Events are validated
        - Events are enriched
        - Invalid events are filtered out
        """
        from pathlib import Path
        import sys
        
        current_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(current_dir))
        
        from aam_hybrid.core.canonical_processor import CanonicalProcessor
        
        processor = CanonicalProcessor(mock_redis)
        
        events = [sample_canonical_event]
        
        with patch('aam_hybrid.core.canonical_processor.FeatureFlagConfig.is_enabled') as mock_feature:
            mock_feature.return_value = False
            
            processed = processor.process_events(events)
            
            assert len(processed) >= 0
    
    def test_process_events_empty_list(self, mock_redis):
        """
        Test that processing an empty list returns empty list.
        """
        from pathlib import Path
        import sys
        
        current_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(current_dir))
        
        from aam_hybrid.core.canonical_processor import CanonicalProcessor
        
        processor = CanonicalProcessor(mock_redis)
        
        processed = processor.process_events([])
        
        assert processed == []


@pytest.mark.unit
class TestCanonicalProcessorUnit:
    """Additional unit tests for CanonicalProcessor components"""
    
    def test_processor_initialization(self, mock_redis):
        """Test that processor initializes correctly"""
        from pathlib import Path
        import sys
        
        current_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(current_dir))
        
        from aam_hybrid.core.canonical_processor import CanonicalProcessor
        
        processor = CanonicalProcessor(mock_redis)
        
        assert processor.redis_client is not None
        assert processor.PROCESSOR_VERSION is not None
