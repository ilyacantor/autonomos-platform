"""
Distributed Tracing

Execution trace and audit for agent workflows.
Implements Observability: Execution trace & audit from RACI.
"""

import logging
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID, uuid4

from .models import Trace, Span, SpanKind

logger = logging.getLogger(__name__)

# Context variable for current trace context
_current_context: ContextVar[Optional["TraceContext"]] = ContextVar(
    "trace_context", default=None
)


@dataclass
class TraceContext:
    """Context for the current trace."""
    trace_id: UUID
    span_id: UUID
    agent_id: Optional[UUID] = None
    run_id: Optional[UUID] = None
    tenant_id: Optional[UUID] = None
    baggage: Dict[str, str] = field(default_factory=dict)

    def with_span(self, span_id: UUID) -> "TraceContext":
        """Create a new context with a different current span."""
        return TraceContext(
            trace_id=self.trace_id,
            span_id=span_id,
            agent_id=self.agent_id,
            run_id=self.run_id,
            tenant_id=self.tenant_id,
            baggage=self.baggage.copy(),
        )


class Tracer:
    """
    Distributed Tracer.

    Creates and manages traces for agent execution:
    - Start and end traces
    - Create spans with proper hierarchy
    - Support deterministic replay
    - Export traces for analysis
    """

    def __init__(self):
        """Initialize the tracer."""
        # Trace storage
        self._traces: Dict[UUID, Trace] = {}
        self._active_traces: Dict[UUID, Trace] = {}

        # Span storage
        self._spans: Dict[UUID, Span] = {}

        # Export handlers
        self._exporters: List[Callable[[Trace], None]] = []

        # Callbacks
        self._on_trace_start: List[Callable[[Trace], None]] = []
        self._on_trace_end: List[Callable[[Trace], None]] = []
        self._on_span_start: List[Callable[[Span], None]] = []
        self._on_span_end: List[Callable[[Span], None]] = []

        # Configuration
        self._max_traces = 10000
        self._sample_rate = 1.0  # 100% sampling

    def start_trace(
        self,
        name: str,
        agent_id: Optional[UUID] = None,
        run_id: Optional[UUID] = None,
        tenant_id: Optional[UUID] = None,
        attributes: Optional[Dict[str, Any]] = None,
        replayable: bool = True,
    ) -> Trace:
        """
        Start a new trace.

        Args:
            name: Trace name
            agent_id: Agent ID
            run_id: Run ID
            tenant_id: Tenant ID
            attributes: Additional attributes
            replayable: Whether trace can be replayed

        Returns:
            New trace
        """
        trace = Trace(
            name=name,
            agent_id=agent_id,
            run_id=run_id,
            tenant_id=tenant_id,
            attributes=attributes or {},
            replayable=replayable,
        )

        self._traces[trace.id] = trace
        self._active_traces[trace.id] = trace

        # Create root span
        root_span = self.start_span(
            name=name,
            trace_id=trace.id,
            kind=SpanKind.AGENT,
            agent_id=agent_id,
            run_id=run_id,
            tenant_id=tenant_id,
        )
        trace.root_span_id = root_span.id

        # Set context
        context = TraceContext(
            trace_id=trace.id,
            span_id=root_span.id,
            agent_id=agent_id,
            run_id=run_id,
            tenant_id=tenant_id,
        )
        _current_context.set(context)

        # Notify callbacks
        for callback in self._on_trace_start:
            try:
                callback(trace)
            except Exception as e:
                logger.error(f"Trace start callback error: {e}")

        logger.debug(f"Started trace: {trace.id} - {name}")
        return trace

    def end_trace(
        self,
        trace_id: UUID,
        error: Optional[str] = None,
    ) -> Trace:
        """
        End a trace.

        Args:
            trace_id: Trace to end
            error: Error if failed

        Returns:
            Completed trace
        """
        trace = self._active_traces.pop(trace_id, None)
        if not trace:
            trace = self._traces.get(trace_id)
            if not trace:
                raise ValueError(f"Trace not found: {trace_id}")

        # End root span
        if trace.root_span_id:
            root_span = self._spans.get(trace.root_span_id)
            if root_span and not root_span.end_time:
                self.end_span(root_span.id, error=error)

        trace.end(error=error)

        # Clear context
        context = _current_context.get()
        if context and context.trace_id == trace_id:
            _current_context.set(None)

        # Export trace
        for exporter in self._exporters:
            try:
                exporter(trace)
            except Exception as e:
                logger.error(f"Trace export error: {e}")

        # Notify callbacks
        for callback in self._on_trace_end:
            try:
                callback(trace)
            except Exception as e:
                logger.error(f"Trace end callback error: {e}")

        # Trim old traces
        self._trim_traces()

        logger.debug(f"Ended trace: {trace_id}")
        return trace

    def start_span(
        self,
        name: str,
        trace_id: Optional[UUID] = None,
        parent_id: Optional[UUID] = None,
        kind: SpanKind = SpanKind.INTERNAL,
        agent_id: Optional[UUID] = None,
        run_id: Optional[UUID] = None,
        tenant_id: Optional[UUID] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Span:
        """
        Start a new span.

        Args:
            name: Span name
            trace_id: Trace ID (uses current if not provided)
            parent_id: Parent span ID (uses current if not provided)
            kind: Span kind
            agent_id: Agent ID
            run_id: Run ID
            tenant_id: Tenant ID
            attributes: Span attributes

        Returns:
            New span
        """
        # Get context
        context = _current_context.get()

        if trace_id is None:
            if context:
                trace_id = context.trace_id
            else:
                # Create a new trace
                trace = self.start_trace(name, agent_id, run_id, tenant_id)
                trace_id = trace.id
                context = _current_context.get()

        if parent_id is None and context:
            parent_id = context.span_id

        span = Span(
            trace_id=trace_id,
            parent_id=parent_id,
            name=name,
            kind=kind,
            agent_id=agent_id or (context.agent_id if context else None),
            run_id=run_id or (context.run_id if context else None),
            tenant_id=tenant_id or (context.tenant_id if context else None),
            attributes=attributes or {},
        )

        self._spans[span.id] = span

        # Add to trace
        trace = self._traces.get(trace_id)
        if trace:
            trace.add_span(span)

        # Update context
        if context:
            new_context = context.with_span(span.id)
            _current_context.set(new_context)

        # Notify callbacks
        for callback in self._on_span_start:
            try:
                callback(span)
            except Exception as e:
                logger.error(f"Span start callback error: {e}")

        return span

    def end_span(
        self,
        span_id: UUID,
        error: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Span:
        """
        End a span.

        Args:
            span_id: Span to end
            error: Error if failed
            attributes: Additional attributes

        Returns:
            Completed span
        """
        span = self._spans.get(span_id)
        if not span:
            raise ValueError(f"Span not found: {span_id}")

        if attributes:
            span.attributes.update(attributes)

        span.end(error=error)

        # Restore parent context
        context = _current_context.get()
        if context and context.span_id == span_id and span.parent_id:
            parent_context = context.with_span(span.parent_id)
            _current_context.set(parent_context)

        # Notify callbacks
        for callback in self._on_span_end:
            try:
                callback(span)
            except Exception as e:
                logger.error(f"Span end callback error: {e}")

        return span

    def current_span(self) -> Optional[Span]:
        """Get the current span."""
        context = _current_context.get()
        if context:
            return self._spans.get(context.span_id)
        return None

    def current_trace(self) -> Optional[Trace]:
        """Get the current trace."""
        context = _current_context.get()
        if context:
            return self._traces.get(context.trace_id)
        return None

    def get_trace(self, trace_id: UUID) -> Optional[Trace]:
        """Get a trace by ID."""
        return self._traces.get(trace_id)

    def get_span(self, span_id: UUID) -> Optional[Span]:
        """Get a span by ID."""
        return self._spans.get(span_id)

    def get_traces(
        self,
        agent_id: Optional[UUID] = None,
        run_id: Optional[UUID] = None,
        tenant_id: Optional[UUID] = None,
        status: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Trace]:
        """Get traces with optional filters."""
        traces = list(self._traces.values())

        if agent_id:
            traces = [t for t in traces if t.agent_id == agent_id]
        if run_id:
            traces = [t for t in traces if t.run_id == run_id]
        if tenant_id:
            traces = [t for t in traces if t.tenant_id == tenant_id]
        if status:
            traces = [t for t in traces if t.status == status]
        if since:
            traces = [t for t in traces if t.start_time >= since]

        # Sort by start time descending
        traces.sort(key=lambda t: t.start_time, reverse=True)
        return traces[:limit]

    def add_exporter(self, exporter: Callable[[Trace], None]) -> None:
        """Add a trace exporter."""
        self._exporters.append(exporter)

    def record_event(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record an event on the current span."""
        span = self.current_span()
        if span:
            span.add_event(name, attributes)

    def set_attribute(self, key: str, value: Any) -> None:
        """Set an attribute on the current span."""
        span = self.current_span()
        if span:
            span.set_attribute(key, value)

    def get_context(self) -> Optional[TraceContext]:
        """Get the current trace context."""
        return _current_context.get()

    def set_context(self, context: TraceContext) -> None:
        """Set the current trace context."""
        _current_context.set(context)

    # Context manager support
    def span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        """Create a span as a context manager."""
        return SpanContextManager(self, name, kind, attributes)

    # Event registration
    def on_trace_start(self, callback: Callable[[Trace], None]) -> None:
        """Register callback for trace start."""
        self._on_trace_start.append(callback)

    def on_trace_end(self, callback: Callable[[Trace], None]) -> None:
        """Register callback for trace end."""
        self._on_trace_end.append(callback)

    def on_span_start(self, callback: Callable[[Span], None]) -> None:
        """Register callback for span start."""
        self._on_span_start.append(callback)

    def on_span_end(self, callback: Callable[[Span], None]) -> None:
        """Register callback for span end."""
        self._on_span_end.append(callback)

    def _trim_traces(self) -> None:
        """Trim old traces to stay within limit."""
        if len(self._traces) <= self._max_traces:
            return

        # Sort by start time
        sorted_traces = sorted(
            self._traces.values(),
            key=lambda t: t.start_time,
        )

        # Remove oldest traces
        to_remove = sorted_traces[:len(self._traces) - self._max_traces]
        for trace in to_remove:
            del self._traces[trace.id]
            for span in trace.spans:
                self._spans.pop(span.id, None)


class SpanContextManager:
    """Context manager for spans."""

    def __init__(
        self,
        tracer: Tracer,
        name: str,
        kind: SpanKind,
        attributes: Optional[Dict[str, Any]],
    ):
        self.tracer = tracer
        self.name = name
        self.kind = kind
        self.attributes = attributes
        self.span: Optional[Span] = None

    def __enter__(self) -> Span:
        self.span = self.tracer.start_span(
            name=self.name,
            kind=self.kind,
            attributes=self.attributes,
        )
        return self.span

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.span:
            error = str(exc_val) if exc_val else None
            self.tracer.end_span(self.span.id, error=error)
        return False


# Global tracer instance
_tracer: Optional[Tracer] = None


def get_tracer() -> Tracer:
    """Get the global tracer instance."""
    global _tracer
    if _tracer is None:
        _tracer = Tracer()
    return _tracer
