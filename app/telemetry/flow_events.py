"""
Flow Event Schema - Phase 4

Canonical schema for telemetry events across AAM → DCL → Agent layers.
All events follow same structure for consistent aggregation and visualization.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum
import json


class FlowEventLayer(str, Enum):
    """Which architectural layer emitted this event"""
    AAM = "aam"  # Adaptive API Mesh (connection runtime)
    DCL = "dcl"  # Data Connection Layer (intelligence)
    AGENT = "agent"  # Agent Executor (workflow execution)


class FlowEventStage(str, Enum):
    """What stage of processing this event represents"""
    # AAM stages
    CONNECTION_START = "connection_start"
    CONNECTION_SUCCESS = "connection_success"
    CONNECTION_FAILURE = "connection_failure"
    SCHEMA_DRIFT_DETECTED = "schema_drift_detected"
    EVENT_INGESTED = "event_ingested"
    
    # DCL stages
    MAPPING_PROPOSED = "mapping_proposed"
    CONFIDENCE_CALCULATED = "confidence_calculated"
    RAG_CACHE_HIT = "rag_cache_hit"
    RAG_CACHE_MISS = "rag_cache_miss"
    DRIFT_REPAIR_REQUESTED = "drift_repair_requested"
    APPROVAL_REQUIRED = "approval_required"
    
    # Agent stages
    TASK_DISPATCHED = "task_dispatched"
    TASK_EXECUTING = "task_executing"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    FALLBACK_INVOKED = "fallback_invoked"


class FlowEventStatus(str, Enum):
    """Overall status of the event"""
    SUCCESS = "success"
    FAILURE = "failure"
    IN_PROGRESS = "in_progress"
    DEGRADED = "degraded"  # Operating with fallback
    PENDING = "pending"


@dataclass
class FlowEvent:
    """
    Canonical telemetry event for AAM → DCL → Agent flow tracking.
    
    All layers emit events with this structure for unified monitoring.
    Events are written to Redis Streams with XADD for ordered, replayable history.
    """
    # Event identity
    event_id: str  # Unique event identifier (UUID)
    entity_id: str  # Entity being processed (connector name, mapping ID, task ID)
    
    # Architectural context
    layer: FlowEventLayer  # Which layer emitted this event
    stage: FlowEventStage  # What processing stage
    status: FlowEventStatus  # Overall status
    
    # Tenant context (for multi-tenancy)
    tenant_id: str  # Tenant scope
    
    # Timing
    timestamp: datetime  # When event occurred (ISO 8601)
    duration_ms: Optional[int] = None  # Operation duration if applicable
    
    # Flexible metadata
    metadata: Dict[str, Any] = None  # Layer-specific details
    
    def __post_init__(self):
        """Ensure metadata is initialized"""
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis Stream serialization"""
        data = asdict(self)
        # Convert enums to strings
        data['layer'] = self.layer.value
        data['stage'] = self.stage.value
        data['status'] = self.status.value
        # Convert timestamp to ISO string
        data['timestamp'] = self.timestamp.isoformat()
        # Serialize metadata as JSON string
        data['metadata'] = json.dumps(self.metadata)
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FlowEvent':
        """Deserialize from Redis Stream entry"""
        # Convert string values back to enums
        data['layer'] = FlowEventLayer(data['layer'])
        data['stage'] = FlowEventStage(data['stage'])
        data['status'] = FlowEventStatus(data['status'])
        # Parse timestamp
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        # Deserialize metadata
        if isinstance(data.get('metadata'), str):
            data['metadata'] = json.loads(data['metadata'])
        # Handle optional duration_ms
        if 'duration_ms' in data and data['duration_ms'] == 'None':
            data['duration_ms'] = None
        elif 'duration_ms' in data:
            data['duration_ms'] = int(data['duration_ms'])
        
        return cls(**data)


# Redis Stream key namespaces (per layer)
AAM_FLOW_STREAM = "aam:flow"
DCL_FLOW_STREAM = "dcl:flow"
AGENT_FLOW_STREAM = "agent:flow"

# Map layers to stream keys
LAYER_TO_STREAM = {
    FlowEventLayer.AAM: AAM_FLOW_STREAM,
    FlowEventLayer.DCL: DCL_FLOW_STREAM,
    FlowEventLayer.AGENT: AGENT_FLOW_STREAM,
}
