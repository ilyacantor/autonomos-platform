"""
Event Emitter for Simulation

Bridges simulation execution to StreamManager for real-time UI updates.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID, uuid4

from app.agentic.streaming import (
    StreamManager,
    StreamEvent,
    EventType,
    get_stream_manager,
)

logger = logging.getLogger(__name__)


@dataclass
class EmitterConfig:
    """Configuration for event emitter."""
    emit_to_stream: bool = True
    emit_to_redis: bool = True
    buffer_events: bool = False
    buffer_size: int = 100


class EventEmitter:
    """
    Emits simulation events to StreamManager and Redis streams.

    Provides real-time visibility into simulated agent activity
    for UI dashboards.
    """

    def __init__(self, config: Optional[EmitterConfig] = None):
        self.config = config or EmitterConfig()
        self._stream_manager: Optional[StreamManager] = None
        self._event_buffer: List[StreamEvent] = []
        self._callbacks: List[Callable[[StreamEvent], None]] = []
        self._redis_client = None

    def set_stream_manager(self, manager: StreamManager) -> None:
        """Set the stream manager for event emission."""
        self._stream_manager = manager

    def set_redis_client(self, client) -> None:
        """Set Redis client for stream emission."""
        self._redis_client = client

    def on_event(self, callback: Callable[[StreamEvent], None]) -> None:
        """Register callback for emitted events."""
        self._callbacks.append(callback)

    async def emit_run_started(
        self,
        run_id: UUID,
        workflow_id: str,
        tenant_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit workflow run started event."""
        event = StreamEvent(
            event_type=EventType.RUN_STARTED,
            run_id=run_id,
            data={
                "workflow_id": workflow_id,
                "tenant_id": str(tenant_id) if tenant_id else None,
                "started_at": datetime.utcnow().isoformat(),
                **(metadata or {}),
            }
        )
        await self._emit(event, tenant_id)

    async def emit_run_completed(
        self,
        run_id: UUID,
        workflow_id: str,
        status: str,
        duration_ms: int,
        tasks_completed: int,
        tasks_failed: int,
        tenant_id: Optional[UUID] = None,
    ) -> None:
        """Emit workflow run completed event."""
        event = StreamEvent(
            event_type=EventType.RUN_COMPLETED,
            run_id=run_id,
            data={
                "workflow_id": workflow_id,
                "status": status,
                "duration_ms": duration_ms,
                "tasks_completed": tasks_completed,
                "tasks_failed": tasks_failed,
                "completed_at": datetime.utcnow().isoformat(),
            }
        )
        await self._emit(event, tenant_id)

    async def emit_run_failed(
        self,
        run_id: UUID,
        workflow_id: str,
        error: str,
        tenant_id: Optional[UUID] = None,
    ) -> None:
        """Emit workflow run failed event."""
        event = StreamEvent(
            event_type=EventType.RUN_FAILED,
            run_id=run_id,
            data={
                "workflow_id": workflow_id,
                "error": error,
                "failed_at": datetime.utcnow().isoformat(),
            }
        )
        await self._emit(event, tenant_id)

    async def emit_step_started(
        self,
        run_id: UUID,
        task_id: str,
        task_name: str,
        agent_id: Optional[str] = None,
        tenant_id: Optional[UUID] = None,
    ) -> None:
        """Emit task step started event."""
        event = StreamEvent(
            event_type=EventType.STEP_STARTED,
            run_id=run_id,
            data={
                "task_id": task_id,
                "task_name": task_name,
                "agent_id": agent_id,
                "started_at": datetime.utcnow().isoformat(),
            }
        )
        await self._emit(event, tenant_id)

    async def emit_step_completed(
        self,
        run_id: UUID,
        task_id: str,
        status: str,
        duration_ms: int,
        tenant_id: Optional[UUID] = None,
    ) -> None:
        """Emit task step completed event."""
        event = StreamEvent(
            event_type=EventType.STEP_COMPLETED,
            run_id=run_id,
            data={
                "task_id": task_id,
                "status": status,
                "duration_ms": duration_ms,
                "completed_at": datetime.utcnow().isoformat(),
            }
        )
        await self._emit(event, tenant_id)

    async def emit_tool_call_started(
        self,
        run_id: UUID,
        task_id: str,
        tool_name: str,
        tenant_id: Optional[UUID] = None,
    ) -> None:
        """Emit tool call started event."""
        event = StreamEvent(
            event_type=EventType.TOOL_CALL_STARTED,
            run_id=run_id,
            data={
                "task_id": task_id,
                "tool_name": tool_name,
                "started_at": datetime.utcnow().isoformat(),
            }
        )
        await self._emit(event, tenant_id)

    async def emit_tool_call_completed(
        self,
        run_id: UUID,
        task_id: str,
        tool_name: str,
        success: bool,
        duration_ms: int,
        tenant_id: Optional[UUID] = None,
    ) -> None:
        """Emit tool call completed event."""
        event_type = EventType.TOOL_CALL_COMPLETED if success else EventType.TOOL_CALL_FAILED
        event = StreamEvent(
            event_type=event_type,
            run_id=run_id,
            data={
                "task_id": task_id,
                "tool_name": tool_name,
                "success": success,
                "duration_ms": duration_ms,
                "completed_at": datetime.utcnow().isoformat(),
            }
        )
        await self._emit(event, tenant_id)

    async def emit_approval_required(
        self,
        run_id: UUID,
        task_id: str,
        approval_type: str,
        reason: str,
        tenant_id: Optional[UUID] = None,
    ) -> None:
        """Emit approval required event."""
        event = StreamEvent(
            event_type=EventType.APPROVAL_REQUIRED,
            run_id=run_id,
            data={
                "task_id": task_id,
                "approval_type": approval_type,
                "reason": reason,
                "requested_at": datetime.utcnow().isoformat(),
            }
        )
        await self._emit(event, tenant_id)

    async def emit_usage_update(
        self,
        run_id: UUID,
        tokens_used: int,
        cost_usd: float,
        tenant_id: Optional[UUID] = None,
    ) -> None:
        """Emit usage/cost update event."""
        event = StreamEvent(
            event_type=EventType.USAGE_UPDATE,
            run_id=run_id,
            data={
                "tokens_used": tokens_used,
                "cost_usd": cost_usd,
                "updated_at": datetime.utcnow().isoformat(),
            }
        )
        await self._emit(event, tenant_id)

    async def _emit(self, event: StreamEvent, tenant_id: Optional[UUID] = None) -> None:
        """Emit event to all configured destinations."""
        # Buffer if configured
        if self.config.buffer_events:
            self._event_buffer.append(event)
            if len(self._event_buffer) >= self.config.buffer_size:
                await self._flush_buffer()

        # Emit to stream manager
        if self.config.emit_to_stream and self._stream_manager:
            try:
                await self._stream_manager.broadcast(event, tenant_id)
            except Exception as e:
                logger.warning(f"Failed to emit to stream manager: {e}")

        # Emit to Redis stream
        if self.config.emit_to_redis and self._redis_client:
            try:
                await self._emit_to_redis(event)
            except Exception as e:
                logger.warning(f"Failed to emit to Redis: {e}")

        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.warning(f"Event callback error: {e}")

    async def _emit_to_redis(self, event: StreamEvent) -> None:
        """Emit event to Redis stream."""
        if not self._redis_client:
            return

        stream_key = f"aoa:events:{event.event_type.value}"
        await self._redis_client.xadd(
            stream_key,
            {
                "event_type": event.event_type.value,
                "run_id": str(event.run_id),
                "timestamp": event.timestamp.isoformat(),
                "data": event.to_json(),
            },
            maxlen=10000,  # Keep last 10k events per stream
        )

    async def _flush_buffer(self) -> None:
        """Flush buffered events."""
        events = self._event_buffer.copy()
        self._event_buffer.clear()

        for event in events:
            if self.config.emit_to_stream and self._stream_manager:
                await self._stream_manager.broadcast(event, None)


# Singleton instance
_event_emitter: Optional[EventEmitter] = None


def get_event_emitter() -> EventEmitter:
    """Get singleton event emitter."""
    global _event_emitter
    if _event_emitter is None:
        _event_emitter = EventEmitter()
    return _event_emitter
