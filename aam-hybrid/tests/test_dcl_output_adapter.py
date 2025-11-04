"""
Test Suite for DCL Output Adapter

Tests the transformation of AAM canonical events to DCL format and Redis Streams integration.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, Any

import pytest

from aam_hybrid.core.dcl_output_adapter import (
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
    events = [
        MockCanonicalEvent("evt-1", "opportunity", {"name": "Deal 1"}),
        MockCanonicalEvent("evt-2", "opportunity", {"name": "Deal 2"}),
        MockCanonicalEvent("evt-3", "account", {"name": "Account 1"}),
        MockCanonicalEvent("evt-4", "contact", {"name": "Contact 1"}),
    ]
    
    grouped = _group_events_by_entity(events)
    
    assert len(grouped) == 3
    assert "opportunity" in grouped
    assert "account" in grouped
    assert "contact" in grouped
    assert len(grouped["opportunity"]) == 2
    assert len(grouped["account"]) == 1
    assert len(grouped["contact"]) == 1


def test_infer_schema_from_events():
    """Test schema inference from event payloads"""
    events = [
        MockCanonicalEvent("evt-1", "opportunity", {
            "id": "opp-1",
            "name": "Enterprise Deal",
            "amount": 100000.0,
            "is_active": True,
            "created_at": datetime.utcnow()
        }),
        MockCanonicalEvent("evt-2", "opportunity", {
            "id": "opp-2",
            "name": "SMB Deal",
            "amount": 50000.0,
            "is_active": False
        }),
    ]
    
    schema = _infer_schema_from_events(events)
    
    assert "id" in schema
    assert "name" in schema
    assert "amount" in schema
    assert "is_active" in schema
    
    assert schema["name"] == "string"
    assert schema["amount"] == "number"
    assert schema["is_active"] == "boolean"


def test_extract_payload():
    """Test payload extraction from different event structures"""
    payload_dict = {"name": "Test", "amount": 1000}
    
    event = MockCanonicalEvent("evt-1", "opportunity", payload_dict)
    
    extracted = _extract_payload(event)
    
    assert extracted == payload_dict
    assert "name" in extracted
    assert extracted["amount"] == 1000


def test_compute_schema_fingerprint():
    """Test schema fingerprint computation"""
    schema1 = {"id": "string", "name": "string", "amount": "number"}
    schema2 = {"id": "string", "name": "string", "amount": "number"}
    schema3 = {"id": "string", "name": "string"}
    
    fingerprint1 = _compute_schema_fingerprint(schema1)
    fingerprint2 = _compute_schema_fingerprint(schema2)
    fingerprint3 = _compute_schema_fingerprint(schema3)
    
    assert fingerprint1 == fingerprint2
    assert fingerprint1 != fingerprint3
    assert len(fingerprint1) == 16


def test_create_dcl_payload():
    """Test DCL payload creation"""
    events_by_entity = {
        "opportunity": [
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
        ],
        "account": [
            MockCanonicalEvent("evt-3", "account", {
                "id": "acc-1",
                "name": "Account 1"
            }),
        ]
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
    assert payload["record_count"] == 3
    
    assert "lineage" in payload
    assert payload["lineage"]["source"] == "AAM"
    assert payload["lineage"]["connector_config_id"] == "sf-config-1"
    
    assert "tables" in payload
    assert "opportunity" in payload["tables"]
    assert "account" in payload["tables"]
    
    opp_table = payload["tables"]["opportunity"]
    assert opp_table["path"] == "aam://stream"
    assert "schema" in opp_table
    assert "samples" in opp_table
    assert opp_table["record_count"] == 2
    assert len(opp_table["samples"]) == 2
    
    acc_table = payload["tables"]["account"]
    assert acc_table["record_count"] == 1
    assert len(acc_table["samples"]) == 1


def test_get_dcl_stream_key():
    """Test DCL stream key generation"""
    key = get_dcl_stream_key("test-tenant", "salesforce")
    
    assert key == "aam:dcl:test-tenant:salesforce"


def test_publish_to_dcl_stream_empty():
    """Test publishing empty event list"""
    redis_client = MockRedisClient()
    
    result = publish_to_dcl_stream(
        tenant_id="test-tenant",
        connector_type="salesforce",
        canonical_events=[],
        redis_client=redis_client
    )
    
    assert result["success"] is True
    assert result["batches_published"] == 0
    assert result["total_records"] == 0
    assert len(result["batch_ids"]) == 0


def test_publish_to_dcl_stream_single_batch():
    """Test publishing a single batch"""
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
    assert len(result["batch_ids"]) == 1
    assert len(result["errors"]) == 0
    
    assert "aam:dcl:test-tenant:salesforce" in redis_client.streams
    messages = redis_client.streams["aam:dcl:test-tenant:salesforce"]
    assert len(messages) == 1
    
    payload_json = messages[0]["fields"]["payload"]
    payload = json.loads(payload_json)
    
    assert payload["connector_type"] == "salesforce"
    assert payload["tenant_id"] == "test-tenant"
    assert payload["record_count"] == 2
    assert "opportunity" in payload["tables"]


def test_publish_to_dcl_stream_multiple_batches():
    """Test publishing multiple batches with chunking"""
    redis_client = MockRedisClient()
    
    events = []
    for i in range(250):
        events.append(MockCanonicalEvent(
            f"evt-{i}",
            "opportunity",
            {"id": f"opp-{i}", "name": f"Deal {i}", "amount": 1000.0 * i}
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


def test_publish_to_dcl_stream_multiple_entities():
    """Test publishing events with multiple entity types"""
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
    assert payload["tables"]["contact"]["record_count"] == 1


if __name__ == "__main__":
    print("Running DCL Output Adapter Tests")
    print("=" * 60)
    
    test_group_events_by_entity()
    print("✓ test_group_events_by_entity passed")
    
    test_infer_schema_from_events()
    print("✓ test_infer_schema_from_events passed")
    
    test_extract_payload()
    print("✓ test_extract_payload passed")
    
    test_compute_schema_fingerprint()
    print("✓ test_compute_schema_fingerprint passed")
    
    test_create_dcl_payload()
    print("✓ test_create_dcl_payload passed")
    
    test_get_dcl_stream_key()
    print("✓ test_get_dcl_stream_key passed")
    
    test_publish_to_dcl_stream_empty()
    print("✓ test_publish_to_dcl_stream_empty passed")
    
    test_publish_to_dcl_stream_single_batch()
    print("✓ test_publish_to_dcl_stream_single_batch passed")
    
    test_publish_to_dcl_stream_multiple_batches()
    print("✓ test_publish_to_dcl_stream_multiple_batches passed")
    
    test_publish_to_dcl_stream_multiple_entities()
    print("✓ test_publish_to_dcl_stream_multiple_entities passed")
    
    print()
    print("All tests passed! ✓")
