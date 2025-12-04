"""
Unit Tests for Flow Event Telemetry - Phase 4

Tests the telemetry event schema, serialization, and publisher.
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch
import json

from app.telemetry.flow_events import (
    FlowEvent,
    FlowEventLayer,
    FlowEventStage,
    FlowEventStatus,
    AAM_FLOW_STREAM,
    DCL_FLOW_STREAM,
    AGENT_FLOW_STREAM
)
from app.telemetry.flow_publisher import FlowEventPublisher


class TestFlowEventSchema:
    """Test FlowEvent dataclass and serialization"""
    
    def test_create_flow_event(self):
        """Test creating a valid FlowEvent"""
        event = FlowEvent(
            event_id=str(uuid.uuid4()),
            entity_id="salesforce_connector",
            layer=FlowEventLayer.AAM,
            stage=FlowEventStage.CONNECTION_START,
            status=FlowEventStatus.IN_PROGRESS,
            tenant_id="test-tenant",
            timestamp=datetime.utcnow(),
            metadata={"connector_type": "salesforce"}
        )
        
        assert event.event_id is not None
        assert event.layer == FlowEventLayer.AAM
        assert event.stage == FlowEventStage.CONNECTION_START
        assert event.status == FlowEventStatus.IN_PROGRESS
        assert event.tenant_id == "test-tenant"
        assert event.metadata["connector_type"] == "salesforce"
    
    def test_event_serialization(self):
        """Test FlowEvent serialization to dict"""
        event = FlowEvent(
            event_id="test-event-123",
            entity_id="test-entity",
            layer=FlowEventLayer.DCL,
            stage=FlowEventStage.MAPPING_PROPOSED,
            status=FlowEventStatus.SUCCESS,
            tenant_id="test-tenant",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            duration_ms=150,
            metadata={"confidence": 0.95}
        )
        
        data = event.to_dict()
        
        assert data["event_id"] == "test-event-123"
        assert data["layer"] == "dcl"  # Enum converted to string
        assert data["stage"] == "mapping_proposed"
        assert data["status"] == "success"
        assert data["tenant_id"] == "test-tenant"
        assert "2024-01-01" in data["timestamp"]  # ISO format
        assert data["duration_ms"] == 150
        
        # Metadata should be JSON string
        assert isinstance(data["metadata"], str)
        metadata = json.loads(data["metadata"])
        assert metadata["confidence"] == 0.95
    
    def test_event_deserialization(self):
        """Test FlowEvent deserialization from dict"""
        data = {
            "event_id": "test-event-456",
            "entity_id": "test-mapping",
            "layer": "dcl",
            "stage": "confidence_calculated",
            "status": "success",
            "tenant_id": "test-tenant",
            "timestamp": "2024-01-01T12:00:00",
            "duration_ms": "200",
            "metadata": '{"score": 0.88}'
        }
        
        event = FlowEvent.from_dict(data)
        
        assert event.event_id == "test-event-456"
        assert event.layer == FlowEventLayer.DCL
        assert event.stage == FlowEventStage.CONFIDENCE_CALCULATED
        assert event.status == FlowEventStatus.SUCCESS
        assert event.duration_ms == 200
        assert event.metadata["score"] == 0.88
    
    def test_round_trip_serialization(self):
        """Test that serialize → deserialize produces identical event"""
        original = FlowEvent(
            event_id=str(uuid.uuid4()),
            entity_id="round-trip-test",
            layer=FlowEventLayer.AGENT,
            stage=FlowEventStage.TASK_COMPLETED,
            status=FlowEventStatus.SUCCESS,
            tenant_id="test-tenant",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            duration_ms=500,
            metadata={"result": "success", "items_processed": 42}
        )
        
        # Serialize then deserialize
        data = original.to_dict()
        restored = FlowEvent.from_dict(data)
        
        assert restored.event_id == original.event_id
        assert restored.entity_id == original.entity_id
        assert restored.layer == original.layer
        assert restored.stage == original.stage
        assert restored.status == original.status
        assert restored.tenant_id == original.tenant_id
        assert restored.duration_ms == original.duration_ms
        assert restored.metadata == original.metadata


class TestFlowEventPublisher:
    """Test FlowEventPublisher Redis Stream operations"""
    
    @pytest.mark.asyncio
    async def test_publish_basic_event(self):
        """Test publishing a basic flow event"""
        # Mock Redis client
        redis_mock = AsyncMock()
        redis_mock.xadd = AsyncMock(return_value=b'1234567890-0')
        
        publisher = FlowEventPublisher(redis_mock)
        
        # Publish event
        event_id = await publisher.publish(
            layer=FlowEventLayer.AAM,
            stage=FlowEventStage.CONNECTION_START,
            status=FlowEventStatus.IN_PROGRESS,
            entity_id="test-connector",
            tenant_id="test-tenant",
            metadata={"source": "salesforce"}
        )
        
        # Verify event ID returned
        assert event_id != ""
        
        # Verify Redis XADD called
        assert redis_mock.xadd.called
        call_args = redis_mock.xadd.call_args
        
        # Check stream key
        assert call_args.kwargs["name"] == AAM_FLOW_STREAM
        
        # Check event data
        fields = call_args.kwargs["fields"]
        assert fields["layer"] == "aam"
        assert fields["stage"] == "connection_start"
        assert fields["status"] == "in_progress"
        assert fields["entity_id"] == "test-connector"
        assert fields["tenant_id"] == "test-tenant"
    
    @pytest.mark.asyncio
    async def test_publish_aam_connection_success(self):
        """Test convenience method for AAM connection success"""
        redis_mock = AsyncMock()
        redis_mock.xadd = AsyncMock(return_value=b'1234567890-0')
        
        publisher = FlowEventPublisher(redis_mock)
        
        event_id = await publisher.publish_aam_connection_success(
            connector_name="salesforce",
            tenant_id="test-tenant",
            duration_ms=250,
            metadata={"records_fetched": 100}
        )
        
        assert event_id != ""
        
        call_args = redis_mock.xadd.call_args
        fields = call_args.kwargs["fields"]
        
        assert fields["layer"] == "aam"
        assert fields["stage"] == "connection_success"
        assert fields["status"] == "success"
        assert fields["duration_ms"] == 250
    
    @pytest.mark.asyncio
    async def test_publish_dcl_mapping_proposed(self):
        """Test convenience method for DCL mapping proposal"""
        redis_mock = AsyncMock()
        redis_mock.xadd = AsyncMock(return_value=b'1234567890-0')
        
        publisher = FlowEventPublisher(redis_mock)
        
        event_id = await publisher.publish_dcl_mapping_proposed(
            mapping_id="mapping-123",
            tenant_id="test-tenant",
            confidence_score=0.92,
            metadata={"source_field": "TotalAmount", "canonical_field": "total_amount"}
        )
        
        assert event_id != ""
        
        call_args = redis_mock.xadd.call_args
        fields = call_args.kwargs["fields"]
        
        assert fields["layer"] == "dcl"
        assert fields["stage"] == "mapping_proposed"
        
        # Confidence score should be in metadata
        metadata = json.loads(fields["metadata"])
        assert metadata["confidence_score"] == 0.92
    
    @pytest.mark.asyncio
    async def test_publish_agent_task_completed(self):
        """Test convenience method for agent task completion"""
        redis_mock = AsyncMock()
        redis_mock.xadd = AsyncMock(return_value=b'1234567890-0')
        
        publisher = FlowEventPublisher(redis_mock)
        
        event_id = await publisher.publish_agent_task_completed(
            task_id="task-456",
            tenant_id="test-tenant",
            duration_ms=1500,
            metadata={"workflow": "data_sync", "success": True}
        )
        
        assert event_id != ""
        
        call_args = redis_mock.xadd.call_args
        fields = call_args.kwargs["fields"]
        
        assert fields["layer"] == "agent"
        assert fields["stage"] == "task_completed"
        assert fields["status"] == "success"
        assert fields["duration_ms"] == 1500
    
    @pytest.mark.asyncio
    async def test_publish_error_handling(self):
        """Test that publisher handles Redis errors gracefully"""
        # Mock Redis client that fails
        redis_mock = AsyncMock()
        redis_mock.xadd = AsyncMock(side_effect=Exception("Redis unavailable"))
        
        publisher = FlowEventPublisher(redis_mock)
        
        # Should not raise exception, should return empty event_id
        event_id = await publisher.publish(
            layer=FlowEventLayer.AAM,
            stage=FlowEventStage.CONNECTION_START,
            status=FlowEventStatus.IN_PROGRESS,
            entity_id="test-connector",
            tenant_id="test-tenant"
        )
        
        # Empty event_id indicates failure
        assert event_id == ""
    
    @pytest.mark.asyncio
    async def test_tenant_scoping(self):
        """Test that tenant_id is properly included in all events"""
        redis_mock = AsyncMock()
        redis_mock.xadd = AsyncMock(return_value=b'1234567890-0')
        
        publisher = FlowEventPublisher(redis_mock)
        
        # Publish events for different tenants
        await publisher.publish(
            layer=FlowEventLayer.DCL,
            stage=FlowEventStage.MAPPING_PROPOSED,
            status=FlowEventStatus.SUCCESS,
            entity_id="mapping-1",
            tenant_id="tenant-alpha"
        )
        
        await publisher.publish(
            layer=FlowEventLayer.DCL,
            stage=FlowEventStage.MAPPING_PROPOSED,
            status=FlowEventStatus.SUCCESS,
            entity_id="mapping-2",
            tenant_id="tenant-beta"
        )
        
        # Verify both calls included tenant_id
        assert redis_mock.xadd.call_count == 2
        
        calls = redis_mock.xadd.call_args_list
        assert calls[0].kwargs["fields"]["tenant_id"] == "tenant-alpha"
        assert calls[1].kwargs["fields"]["tenant_id"] == "tenant-beta"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
