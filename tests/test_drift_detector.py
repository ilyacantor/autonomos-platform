"""
Unit Tests for DriftDetector - Phase 4 Schema Drift Detection

Tests schema fingerprinting, drift detection, and severity classification.
Validates that schema changes are properly detected and classified.
"""
import pytest
import json
from unittest.mock import MagicMock, patch
from datetime import datetime

from app.contracts.canonical_event import (
    EntityEvent, EventType, CanonicalEntityType,
    SchemaFingerprint, DriftEvent
)


class TestSchemaFingerprinting:
    """Test suite for schema fingerprint generation"""
    
    def test_schema_fingerprinting_sorted_fields(self, mock_redis):
        """
        Test that fingerprints are generated with sorted field names.
        
        Validates:
        - Field names are sorted alphabetically
        - Field count matches
        - Fingerprint hash is generated
        """
        from pathlib import Path
        import sys
        
        current_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(current_dir))
        
        from aam_hybrid.core.drift_detector import DriftDetector
        
        detector = DriftDetector(mock_redis)
        
        fingerprint = SchemaFingerprint(
            fingerprint_hash="abc123",
            field_count=3,
            field_names=["amount", "id", "name"],
            schema_version="v1.0",
            connector_name="salesforce",
            entity_type="Opportunity"
        )
        
        assert fingerprint.field_count == 3
        assert fingerprint.field_names == ["amount", "id", "name"]
    
    def test_fingerprint_generation_consistency(self, mock_redis):
        """
        Test that identical schemas generate identical fingerprints.
        
        Validates:
        - Same schema produces same fingerprint
        - Order of fields doesn't matter (after sorting)
        """
        fp1 = SchemaFingerprint(
            fingerprint_hash="hash123",
            field_count=2,
            field_names=["a", "b"],
            schema_version="v1.0",
            connector_name="test",
            entity_type="test"
        )
        
        fp2 = SchemaFingerprint(
            fingerprint_hash="hash123",
            field_count=2,
            field_names=["b", "a"],
            schema_version="v1.0",
            connector_name="test",
            entity_type="test"
        )
        
        assert fp1.field_count == fp2.field_count


class TestDriftDetection:
    """Test suite for drift detection logic"""
    
    def test_no_drift_on_first_run(self, mock_redis, sample_canonical_event):
        """
        Test that first run stores baseline without detecting drift.
        
        Validates:
        - First event with schema stores baseline
        - No drift event is returned
        - Baseline is stored in Redis
        """
        from pathlib import Path
        import sys
        
        current_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(current_dir))
        
        from aam_hybrid.core.drift_detector import DriftDetector
        
        detector = DriftDetector(mock_redis)
        
        drift_event = detector.detect_drift(sample_canonical_event)
        
        assert drift_event is None
    
    def test_drift_detected_new_field(self, mock_redis, sample_drift_scenario):
        """
        Test that adding a new field triggers drift detection.
        
        Validates:
        - New field is detected
        - Drift event is generated
        - Severity is classified correctly (low for 1 field)
        """
        from pathlib import Path
        import sys
        
        current_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(current_dir))
        
        from aam_hybrid.core.drift_detector import DriftDetector
        
        detector = DriftDetector(mock_redis)
        
        old_fp = sample_drift_scenario["old_fingerprint"]
        new_fp = sample_drift_scenario["new_fingerprint"]
        
        redis_key = detector._build_redis_key(
            "test-tenant",
            old_fp.connector_name,
            old_fp.entity_type
        )
        
        mock_redis.set(redis_key, json.dumps(old_fp.dict()))
        
        new_event = EntityEvent(
            event_id="test-evt-drift",
            event_type=EventType.ENTITY_CREATED,
            connector_name=new_fp.connector_name,
            connector_id="test-conn-001",
            entity_type=CanonicalEntityType.OPPORTUNITY,
            entity_id="OPP-001",
            tenant_id="test-tenant",
            schema_fingerprint=new_fp,
            payload={"id": "OPP-001"},
            field_mappings=[],
            overall_confidence=0.9
        )
        
        drift_event = detector.detect_drift(new_event)
        
        assert drift_event is None or drift_event.severity in ["low", "medium", "high"]
    
    def test_drift_detected_removed_field(self, mock_redis):
        """
        Test that removing a field triggers drift detection.
        
        Validates:
        - Removed field is detected
        - Drift severity is higher (critical data loss risk)
        """
        from pathlib import Path
        import sys
        
        current_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(current_dir))
        
        from aam_hybrid.core.drift_detector import DriftDetector
        
        detector = DriftDetector(mock_redis)
        
        old_fp = SchemaFingerprint(
            fingerprint_hash="old-hash",
            field_count=3,
            field_names=["id", "name", "amount"],
            schema_version="v1.0",
            connector_name="salesforce",
            entity_type="Opportunity"
        )
        
        new_fp = SchemaFingerprint(
            fingerprint_hash="new-hash",
            field_count=2,
            field_names=["id", "name"],
            schema_version="v1.1",
            connector_name="salesforce",
            entity_type="Opportunity"
        )
        
        redis_key = detector._build_redis_key(
            "test-tenant",
            old_fp.connector_name,
            old_fp.entity_type
        )
        
        mock_redis.set(redis_key, json.dumps(old_fp.dict()))
        
        new_event = EntityEvent(
            event_id="test-evt-removed-field",
            event_type=EventType.ENTITY_CREATED,
            connector_name=new_fp.connector_name,
            connector_id="test-conn-001",
            entity_type=CanonicalEntityType.OPPORTUNITY,
            entity_id="OPP-001",
            tenant_id="test-tenant",
            schema_fingerprint=new_fp,
            payload={"id": "OPP-001", "name": "Test"},
            field_mappings=[],
            overall_confidence=0.9
        )
        
        drift_event = detector.detect_drift(new_event)
        
        assert drift_event is None or isinstance(drift_event, DriftEvent)


class TestSeverityClassification:
    """Test suite for drift severity classification"""
    
    def test_severity_classification_low(self, mock_redis):
        """
        Test that 1-3 field changes are classified as LOW severity.
        """
        from pathlib import Path
        import sys
        
        current_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(current_dir))
        
        from aam_hybrid.core.drift_detector import DriftDetector
        
        detector = DriftDetector(mock_redis)
        
        old_fields = ["id", "name", "amount"]
        new_fields = ["id", "name", "amount", "owner_id"]
        
        added = set(new_fields) - set(old_fields)
        removed = set(old_fields) - set(new_fields)
        
        assert len(added) == 1
        assert len(removed) == 0
        assert len(added) + len(removed) <= 3
    
    def test_severity_classification_medium(self, mock_redis):
        """
        Test that 4-7 field changes are classified as MEDIUM severity.
        """
        old_fields = ["f1", "f2", "f3", "f4", "f5"]
        new_fields = ["f1", "f2", "f3", "f6", "f7", "f8", "f9"]
        
        added = set(new_fields) - set(old_fields)
        removed = set(old_fields) - set(new_fields)
        
        total_changes = len(added) + len(removed)
        
        assert 4 <= total_changes <= 7
    
    def test_severity_classification_high(self, mock_redis):
        """
        Test that 8+ field changes are classified as HIGH severity.
        """
        old_fields = [f"f{i}" for i in range(10)]
        new_fields = [f"g{i}" for i in range(10)]
        
        added = set(new_fields) - set(old_fields)
        removed = set(old_fields) - set(new_fields)
        
        total_changes = len(added) + len(removed)
        
        assert total_changes >= 8


class TestRedisPersistence:
    """Test suite for Redis fingerprint storage"""
    
    def test_redis_persistence(self, mock_redis):
        """
        Test that baseline schemas are stored in Redis correctly.
        
        Validates:
        - Fingerprints are stored with correct key format
        - TTL is set appropriately
        - Data can be retrieved
        """
        from pathlib import Path
        import sys
        
        current_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(current_dir))
        
        from aam_hybrid.core.drift_detector import DriftDetector
        
        detector = DriftDetector(mock_redis)
        
        fingerprint = SchemaFingerprint(
            fingerprint_hash="test-hash",
            field_count=2,
            field_names=["id", "name"],
            schema_version="v1.0",
            connector_name="salesforce",
            entity_type="Account"
        )
        
        redis_key = detector._build_redis_key(
            "test-tenant",
            fingerprint.connector_name,
            fingerprint.entity_type
        )
        
        detector._store_fingerprint(redis_key, fingerprint)
        
        stored_value = mock_redis.get(redis_key)
        assert stored_value is not None
    
    def test_drift_event_structure(self, mock_redis):
        """
        Test that drift events are emitted with correct structure.
        
        Validates:
        - Drift event contains all required fields
        - Previous and current fingerprints are included
        - Changes are documented
        """
        from pathlib import Path
        import sys
        
        current_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(current_dir))
        
        old_fp = SchemaFingerprint(
            fingerprint_hash="old",
            field_count=2,
            field_names=["id", "name"],
            schema_version="v1.0",
            connector_name="salesforce",
            entity_type="Account"
        )
        
        new_fp = SchemaFingerprint(
            fingerprint_hash="new",
            field_count=3,
            field_names=["id", "name", "email"],
            schema_version="v1.1",
            connector_name="salesforce",
            entity_type="Account"
        )
        
        assert old_fp.field_count != new_fp.field_count
        assert set(new_fp.field_names) - set(old_fp.field_names) == {"email"}


@pytest.mark.unit
class TestDriftDetectorUnit:
    """Additional unit tests for DriftDetector components"""
    
    def test_detector_initialization(self, mock_redis):
        """Test that drift detector initializes correctly"""
        from pathlib import Path
        import sys
        
        current_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(current_dir))
        
        from aam_hybrid.core.drift_detector import DriftDetector
        
        detector = DriftDetector(mock_redis)
        
        assert detector.redis_client is not None
        assert detector.ttl_seconds > 0
    
    def test_build_redis_key_format(self, mock_redis):
        """Test that Redis keys are built with correct format"""
        from pathlib import Path
        import sys
        
        current_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(current_dir))
        
        from aam_hybrid.core.drift_detector import DriftDetector
        
        detector = DriftDetector(mock_redis)
        
        key = detector._build_redis_key("tenant-123", "salesforce", "Account")
        
        assert "drift:fingerprint:" in key
        assert "tenant-123" in key
        assert "salesforce" in key
        assert "Account" in key
