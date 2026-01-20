"""
WebSocket Streaming for Agent Runs

Real-time event streaming for agent execution:
- Run lifecycle events (started, completed, failed)
- Step progress updates
- Tool calls and results
- Approval requests
- Token usage updates
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional, Set
from uuid import UUID

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Types of events that can be streamed."""
    # Run lifecycle
    RUN_STARTED = "run_started"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"
    RUN_CANCELLED = "run_cancelled"

    # Step progress
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"

    # Tool execution
    TOOL_CALL_STARTED = "tool_call_started"
    TOOL_CALL_COMPLETED = "tool_call_completed"
    TOOL_CALL_FAILED = "tool_call_failed"

    # Approvals
    APPROVAL_REQUIRED = "approval_required"
    APPROVAL_RESOLVED = "approval_resolved"

    # Token/cost updates
    USAGE_UPDATE = "usage_update"

    # Connection events
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


@dataclass
class StreamEvent:
    """A single stream event."""
    event_type: EventType
    run_id: UUID
    timestamp: datetime = field(default_factory=datetime.utcnow)
    data: dict = field(default_factory=dict)

    def to_json(self) -> str:
        """Serialize event to JSON."""
        return json.dumps({
            "event": self.event_type.value,
            "run_id": str(self.run_id),
            "timestamp": self.timestamp.isoformat(),
            "data": self.data
        })

    @classmethod
    def from_json(cls, json_str: str) -> "StreamEvent":
        """Deserialize event from JSON."""
        data = json.loads(json_str)
        return cls(
            event_type=EventType(data["event"]),
            run_id=UUID(data["run_id"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            data=data.get("data", {})
        )


class StreamManager:
    """
    Manages WebSocket connections and event broadcasting.

    Supports:
    - Multiple subscribers per run
    - Tenant isolation
    - Automatic cleanup on disconnect
    """

    def __init__(self):
        # Map of run_id -> set of subscriber callbacks
        self._subscribers: dict[UUID, Set[Callable]] = {}
        # Map of run_id -> tenant_id for isolation
        self._run_tenants: dict[UUID, UUID] = {}
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    async def subscribe(
        self,
        run_id: UUID,
        tenant_id: UUID,
        callback: Callable[[StreamEvent], Any]
    ) -> None:
        """
        Subscribe to events for a run.

        Args:
            run_id: Run to subscribe to
            tenant_id: Tenant making the subscription
            callback: Async function called with each event
        """
        async with self._lock:
            # Verify tenant isolation
            if run_id in self._run_tenants:
                if self._run_tenants[run_id] != tenant_id:
                    raise PermissionError(f"Run {run_id} belongs to different tenant")
            else:
                self._run_tenants[run_id] = tenant_id

            if run_id not in self._subscribers:
                self._subscribers[run_id] = set()

            self._subscribers[run_id].add(callback)
            logger.debug(f"Subscriber added for run {run_id}")

    async def unsubscribe(
        self,
        run_id: UUID,
        callback: Callable[[StreamEvent], Any]
    ) -> None:
        """
        Unsubscribe from run events.

        Args:
            run_id: Run to unsubscribe from
            callback: The callback to remove
        """
        async with self._lock:
            if run_id in self._subscribers:
                self._subscribers[run_id].discard(callback)

                # Cleanup if no more subscribers
                if not self._subscribers[run_id]:
                    del self._subscribers[run_id]
                    if run_id in self._run_tenants:
                        del self._run_tenants[run_id]

            logger.debug(f"Subscriber removed for run {run_id}")

    async def publish(self, event: StreamEvent) -> None:
        """
        Publish an event to all subscribers.

        Args:
            event: Event to publish
        """
        async with self._lock:
            subscribers = self._subscribers.get(event.run_id, set()).copy()

        if not subscribers:
            return

        logger.debug(f"Publishing {event.event_type.value} to {len(subscribers)} subscribers")

        # Broadcast to all subscribers
        tasks = []
        for callback in subscribers:
            try:
                if asyncio.iscoroutinefunction(callback):
                    tasks.append(callback(event))
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Error in subscriber callback: {e}")

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def cleanup_run(self, run_id: UUID) -> None:
        """
        Clean up all subscribers for a completed run.

        Args:
            run_id: Run to clean up
        """
        async with self._lock:
            if run_id in self._subscribers:
                del self._subscribers[run_id]
            if run_id in self._run_tenants:
                del self._run_tenants[run_id]

        logger.debug(f"Cleaned up subscribers for run {run_id}")

    def get_subscriber_count(self, run_id: UUID) -> int:
        """Get the number of subscribers for a run."""
        return len(self._subscribers.get(run_id, set()))


# =============================================================================
# Event Factory Functions
# =============================================================================

def create_run_started_event(
    run_id: UUID,
    agent_id: UUID,
    input_text: str
) -> StreamEvent:
    """Create a run started event."""
    return StreamEvent(
        event_type=EventType.RUN_STARTED,
        run_id=run_id,
        data={
            "agent_id": str(agent_id),
            "input": input_text[:500]  # Truncate for safety
        }
    )


def create_run_completed_event(
    run_id: UUID,
    output: str,
    tokens_input: int,
    tokens_output: int,
    cost_usd: float,
    steps_executed: int,
    duration_ms: int
) -> StreamEvent:
    """Create a run completed event."""
    return StreamEvent(
        event_type=EventType.RUN_COMPLETED,
        run_id=run_id,
        data={
            "output": output[:2000],  # Truncate for safety
            "tokens_input": tokens_input,
            "tokens_output": tokens_output,
            "cost_usd": cost_usd,
            "steps_executed": steps_executed,
            "duration_ms": duration_ms
        }
    )


def create_run_failed_event(
    run_id: UUID,
    error: str,
    step_number: int
) -> StreamEvent:
    """Create a run failed event."""
    return StreamEvent(
        event_type=EventType.RUN_FAILED,
        run_id=run_id,
        data={
            "error": error,
            "step_number": step_number
        }
    )


def create_step_started_event(
    run_id: UUID,
    step_number: int
) -> StreamEvent:
    """Create a step started event."""
    return StreamEvent(
        event_type=EventType.STEP_STARTED,
        run_id=run_id,
        data={
            "step_number": step_number
        }
    )


def create_step_completed_event(
    run_id: UUID,
    step_number: int,
    tokens_used: int
) -> StreamEvent:
    """Create a step completed event."""
    return StreamEvent(
        event_type=EventType.STEP_COMPLETED,
        run_id=run_id,
        data={
            "step_number": step_number,
            "tokens_used": tokens_used
        }
    )


def create_tool_call_event(
    run_id: UUID,
    tool_name: str,
    tool_server: str,
    arguments: dict,
    step_number: int
) -> StreamEvent:
    """Create a tool call started event."""
    return StreamEvent(
        event_type=EventType.TOOL_CALL_STARTED,
        run_id=run_id,
        data={
            "tool_name": tool_name,
            "tool_server": tool_server,
            "arguments": arguments,
            "step_number": step_number
        }
    )


def create_tool_result_event(
    run_id: UUID,
    tool_name: str,
    result: Any,
    duration_ms: int,
    step_number: int
) -> StreamEvent:
    """Create a tool call completed event."""
    # Safely serialize result
    try:
        result_str = json.dumps(result, default=str)
        if len(result_str) > 5000:
            result_str = result_str[:5000] + "...(truncated)"
    except Exception:
        result_str = str(result)[:5000]

    return StreamEvent(
        event_type=EventType.TOOL_CALL_COMPLETED,
        run_id=run_id,
        data={
            "tool_name": tool_name,
            "result": result_str,
            "duration_ms": duration_ms,
            "step_number": step_number
        }
    )


def create_approval_required_event(
    run_id: UUID,
    approval_id: UUID,
    action_type: str,
    action_details: dict,
    expires_at: datetime,
    step_number: int
) -> StreamEvent:
    """Create an approval required event."""
    return StreamEvent(
        event_type=EventType.APPROVAL_REQUIRED,
        run_id=run_id,
        data={
            "approval_id": str(approval_id),
            "action_type": action_type,
            "action_details": action_details,
            "expires_at": expires_at.isoformat(),
            "step_number": step_number
        }
    )


def create_approval_resolved_event(
    run_id: UUID,
    approval_id: UUID,
    approved: bool,
    notes: Optional[str] = None
) -> StreamEvent:
    """Create an approval resolved event."""
    return StreamEvent(
        event_type=EventType.APPROVAL_RESOLVED,
        run_id=run_id,
        data={
            "approval_id": str(approval_id),
            "approved": approved,
            "notes": notes
        }
    )


def create_usage_update_event(
    run_id: UUID,
    tokens_input: int,
    tokens_output: int,
    cost_usd: float,
    steps_executed: int
) -> StreamEvent:
    """Create a usage update event."""
    return StreamEvent(
        event_type=EventType.USAGE_UPDATE,
        run_id=run_id,
        data={
            "tokens_input": tokens_input,
            "tokens_output": tokens_output,
            "cost_usd": cost_usd,
            "steps_executed": steps_executed
        }
    )


# =============================================================================
# Global Stream Manager
# =============================================================================

_stream_manager: Optional[StreamManager] = None


def get_stream_manager() -> StreamManager:
    """Get the global stream manager instance."""
    global _stream_manager
    if _stream_manager is None:
        _stream_manager = StreamManager()
    return _stream_manager
