"""
Simple standalone test for DCL Output Adapter (no pytest required)
"""

import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

import json
from datetime import datetime
from typing import Dict, Any

from core.dcl_output_adapter import (
    publish_to_dcl_stream,
    _group_events_by_entity,
    _infer_schema_from_events,
    _create_dcl_payload,
    _extract_payload,
    _compute_schema_fingerprint,
    get_dcl_stream_key,
)


class MockCanonicalEvent:
    """Mock CanonicalEvent for testing"""
    
    def __init__(
        self,
        event_id: str,
        entity_type: str,
        payload: Dict[str, Any],
        connector_name: str = "salesforce",
        tenant_id: str = "test-tenant"
    ):
        self.event_id = event_id
        self.entity_type = entity_type
        self.payload = payload
        self.connector_name = connector_name
        self.tenant_id = tenant_id
        self.timestamp = datetime.utcnow()
        
        self.schema_fingerprint = type('obj', (object,), {
            'fingerprint_hash': 'abc123def456'
        })()


class MockRedisClient:
    """Mock Redis client for testing"""
    
    def __init__(self):
        self.streams = {}
        self.message_counter = 0
    
    def xadd(self, stream_key: str, fields: Dict[str, str], maxlen: int = None, approximate: bool = True):
        """Mock XADD command"""
        if stream_key not in self.streams:
            self.streams[stream_key] = []
        
        self.message_counter += 1
        message_id = f"{int(datetime.utcnow().timestamp() * 1000)}-{self.message_counter}"
        
        message = {
            "id": message_id,
            "fields": fields
        }
        
        self.streams[stream_key].append(message)
        
        if maxlen and len(self.streams[stream_key]) > maxlen:
            self.streams[stream_key] = self.streams[stream_key][-maxlen:]
        
        return message_id.encode()
    
    def delete(self, stream_key: str):
        """Mock DELETE command"""
        if stream_key in self.streams:
            del self.streams[stream_key]
            return 1
        return 0


def test_group_events_by_entity():
    """Test grouping events by entity_type"""
    print("Running: test_group_events_by_entity...")
    
    events = [
        MockCanonicalEvent("evt-1", "opportunity", {"name": "Deal 1"}),
        MockCanonicalEvent("evt-2", "opportunity", {"name": "Deal 2"}),
        MockCanonicalEvent("evt-3", "account", {"name": "Account 1"}),
    ]
    
    grouped = _group_events_by_entity(events)
    
    assert len(grouped) == 2, f"Expected 2 entity types, got {len(grouped)}"
    assert "opportunity" in grouped
    assert "account" in grouped
    assert len(grouped["opportunity"]) == 2
    assert len(grouped["account"]) == 1
    
    print("  ✓ Passed")


def test_infer_schema():
    """Test schema inference"""
    print("Running: test_infer_schema...")
    
    events = [
        MockCanonicalEvent("evt-1", "opportunity", {
            "id": "opp-1",
            "name": "Enterprise Deal",
            "amount": 100000.0,
            "is_active": True,
        }),
    ]
    
    schema = _infer_schema_from_events(events)
    
    assert "id" in schema
    assert "name" in schema
    assert "amount" in schema
    assert schema["amount"] == "number"
    assert schema["is_active"] == "boolean"
    
    print("  ✓ Passed")


def test_create_dcl_payload():
    """Test DCL payload creation"""
    print("Running: test_create_dcl_payload...")
    
    events_by_entity = {
        "opportunity": [
            MockCanonicalEvent("evt-1", "opportunity", {
                "id": "opp-1",
                "name": "Deal 1",
                "amount": 100000.0
            }),
        ],
    }
    
    payload = _create_dcl_payload(
        tenant_id="test-tenant",
        connector_type="salesforce",
        events_by_entity=events_by_entity,
        batch_id="sf_123_1",
        connector_config_id="sf-config-1"
    )
    
    assert payload["schema_version"] == "v1.0"
    assert payload["batch_id"] == "sf_123_1"
    assert payload["connector_type"] == "salesforce"
    assert payload["tenant_id"] == "test-tenant"
    assert payload["record_count"] == 1
    assert "lineage" in payload
    assert payload["lineage"]["source"] == "AAM"
    assert "tables" in payload
    assert "opportunity" in payload["tables"]
    
    print("  ✓ Passed")


def test_publish_to_dcl_stream():
    """Test publishing to Redis Stream"""
    print("Running: test_publish_to_dcl_stream...")
    
    redis_client = MockRedisClient()
    
    events = [
        MockCanonicalEvent("evt-1", "opportunity", {
            "id": "opp-1",
            "name": "Deal 1",
            "amount": 100000.0
        }),
        MockCanonicalEvent("evt-2", "opportunity", {
            "id": "opp-2",
            "name": "Deal 2",
            "amount": 50000.0
        }),
    ]
    
    result = publish_to_dcl_stream(
        tenant_id="test-tenant",
        connector_type="salesforce",
        canonical_events=events,
        redis_client=redis_client
    )
    
    assert result["success"] is True
    assert result["stream_key"] == "aam:dcl:test-tenant:salesforce"
    assert result["batches_published"] == 1
    assert result["total_records"] == 2
    assert len(result["errors"]) == 0
    
    # Check Redis stream
    assert "aam:dcl:test-tenant:salesforce" in redis_client.streams
    messages = redis_client.streams["aam:dcl:test-tenant:salesforce"]
    assert len(messages) == 1
    
    # Verify payload structure
    payload_json = messages[0]["fields"]["payload"]
    payload = json.loads(payload_json)
    
    assert payload["connector_type"] == "salesforce"
    assert payload["record_count"] == 2
    assert "opportunity" in payload["tables"]
    
    print("  ✓ Passed")


def test_batch_chunking():
    """Test batch chunking for large datasets"""
    print("Running: test_batch_chunking...")
    
    redis_client = MockRedisClient()
    
    # Create 250 events (should create 2 batches with chunk size 200)
    events = []
    for i in range(250):
        events.append(MockCanonicalEvent(
            f"evt-{i}",
            "opportunity",
            {"id": f"opp-{i}", "amount": 1000.0 * i}
        ))
    
    result = publish_to_dcl_stream(
        tenant_id="test-tenant",
        connector_type="salesforce",
        canonical_events=events,
        redis_client=redis_client
    )
    
    assert result["success"] is True
    assert result["batches_published"] == 2
    assert result["total_records"] == 250
    assert len(result["batch_ids"]) == 2
    
    messages = redis_client.streams["aam:dcl:test-tenant:salesforce"]
    assert len(messages) == 2
    
    print("  ✓ Passed")


def test_multiple_entity_types():
    """Test handling multiple entity types"""
    print("Running: test_multiple_entity_types...")
    
    redis_client = MockRedisClient()
    
    events = [
        MockCanonicalEvent("evt-1", "opportunity", {"name": "Deal 1"}),
        MockCanonicalEvent("evt-2", "account", {"name": "Account 1"}),
        MockCanonicalEvent("evt-3", "contact", {"name": "Contact 1"}),
        MockCanonicalEvent("evt-4", "opportunity", {"name": "Deal 2"}),
    ]
    
    result = publish_to_dcl_stream(
        tenant_id="test-tenant",
        connector_type="salesforce",
        canonical_events=events,
        redis_client=redis_client
    )
    
    assert result["success"] is True
    assert result["total_records"] == 4
    
    messages = redis_client.streams["aam:dcl:test-tenant:salesforce"]
    payload = json.loads(messages[0]["fields"]["payload"])
    
    assert len(payload["tables"]) == 3
    assert "opportunity" in payload["tables"]
    assert "account" in payload["tables"]
    assert "contact" in payload["tables"]
    
    assert payload["tables"]["opportunity"]["record_count"] == 2
    assert payload["tables"]["account"]["record_count"] == 1
    
    print("  ✓ Passed")


def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("DCL Output Adapter - Standalone Tests")
    print("=" * 60 + "\n")
    
    tests = [
        test_group_events_by_entity,
        test_infer_schema,
        test_create_dcl_payload,
        test_publish_to_dcl_stream,
        test_batch_chunking,
        test_multiple_entity_types,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"  ✗ Failed: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("\n✓ All tests passed!\n")
        return 0
    else:
        print(f"\n✗ {failed} test(s) failed\n")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
