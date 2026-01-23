"""
Observability Models

Data structures for traces, metrics, and vitals.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


class SpanKind(str, Enum):
    """Kind of span in a trace."""
    INTERNAL = "internal"
    CLIENT = "client"
    SERVER = "server"
    PRODUCER = "producer"
    CONSUMER = "consumer"
    AGENT = "agent"
    TOOL = "tool"
    LLM = "llm"


class MetricType(str, Enum):
    """Type of metric."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class VitalStatus(str, Enum):
    """Status of a vital sign."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class Span:
    """A span in a distributed trace."""
    id: UUID = field(default_factory=uuid4)
    trace_id: UUID = field(default_factory=uuid4)
    parent_id: Optional[UUID] = None

    # Identity
    name: str = ""
    kind: SpanKind = SpanKind.INTERNAL

    # Timing
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    duration_ms: Optional[int] = None

    # Context
    agent_id: Optional[UUID] = None
    run_id: Optional[UUID] = None
    tenant_id: Optional[UUID] = None

    # Status
    status: str = "ok"  # ok, error
    error: Optional[str] = None

    # Attributes
    attributes: Dict[str, Any] = field(default_factory=dict)

    # Events
    events: List[Dict[str, Any]] = field(default_factory=list)

    # Links to other spans
    links: List[UUID] = field(default_factory=list)

    def end(self, error: Optional[str] = None) -> None:
        """End the span."""
        self.end_time = datetime.utcnow()
        self.duration_ms = int((self.end_time - self.start_time).total_seconds() * 1000)
        if error:
            self.status = "error"
            self.error = error

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """Add an event to the span."""
        self.events.append({
            "name": name,
            "timestamp": datetime.utcnow().isoformat(),
            "attributes": attributes or {},
        })

    def set_attribute(self, key: str, value: Any) -> None:
        """Set a span attribute."""
        self.attributes[key] = value

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "trace_id": str(self.trace_id),
            "parent_id": str(self.parent_id) if self.parent_id else None,
            "name": self.name,
            "kind": self.kind.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "agent_id": str(self.agent_id) if self.agent_id else None,
            "run_id": str(self.run_id) if self.run_id else None,
            "status": self.status,
            "error": self.error,
            "attributes": self.attributes,
            "events": self.events,
        }


@dataclass
class Trace:
    """A distributed trace."""
    id: UUID = field(default_factory=uuid4)

    # Context
    name: str = ""
    agent_id: Optional[UUID] = None
    run_id: Optional[UUID] = None
    tenant_id: Optional[UUID] = None

    # Timing
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    duration_ms: Optional[int] = None

    # Spans
    spans: List[Span] = field(default_factory=list)
    root_span_id: Optional[UUID] = None

    # Status
    status: str = "ok"
    error: Optional[str] = None

    # Metadata
    attributes: Dict[str, Any] = field(default_factory=dict)

    # Replay support
    replayable: bool = True
    replay_data: Optional[Dict[str, Any]] = None

    def add_span(self, span: Span) -> None:
        """Add a span to the trace."""
        span.trace_id = self.id
        self.spans.append(span)
        if not self.root_span_id:
            self.root_span_id = span.id

    def end(self, error: Optional[str] = None) -> None:
        """End the trace."""
        self.end_time = datetime.utcnow()
        self.duration_ms = int((self.end_time - self.start_time).total_seconds() * 1000)
        if error:
            self.status = "error"
            self.error = error

    def get_span_tree(self) -> Dict[str, Any]:
        """Get spans as a tree structure."""
        span_map = {s.id: s for s in self.spans}
        children: Dict[UUID, List[Span]] = {}

        for span in self.spans:
            if span.parent_id:
                if span.parent_id not in children:
                    children[span.parent_id] = []
                children[span.parent_id].append(span)

        def build_tree(span: Span) -> Dict[str, Any]:
            node = span.to_dict()
            node["children"] = [
                build_tree(child)
                for child in children.get(span.id, [])
            ]
            return node

        root = span_map.get(self.root_span_id) if self.root_span_id else None
        if root:
            return build_tree(root)
        return {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "name": self.name,
            "agent_id": str(self.agent_id) if self.agent_id else None,
            "run_id": str(self.run_id) if self.run_id else None,
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "error": self.error,
            "span_count": len(self.spans),
            "replayable": self.replayable,
            "attributes": self.attributes,
        }


@dataclass
class Metric:
    """A metric data point."""
    id: UUID = field(default_factory=uuid4)

    # Identity
    name: str = ""
    metric_type: MetricType = MetricType.GAUGE
    unit: str = ""

    # Value
    value: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Context
    agent_id: Optional[UUID] = None
    run_id: Optional[UUID] = None
    tenant_id: Optional[UUID] = None

    # Labels
    labels: Dict[str, str] = field(default_factory=dict)

    # Histogram/Summary specific
    buckets: Optional[Dict[str, int]] = None
    quantiles: Optional[Dict[str, float]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "name": self.name,
            "type": self.metric_type.value,
            "unit": self.unit,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "agent_id": str(self.agent_id) if self.agent_id else None,
            "labels": self.labels,
        }


@dataclass
class Vital:
    """A vital sign for an agent or component."""
    id: UUID = field(default_factory=uuid4)

    # Identity
    name: str = ""
    component: str = ""  # agent, system, service

    # Status
    status: VitalStatus = VitalStatus.UNKNOWN
    message: Optional[str] = None

    # Value
    value: Optional[float] = None
    unit: Optional[str] = None

    # Thresholds
    warning_threshold: Optional[float] = None
    critical_threshold: Optional[float] = None

    # Context
    agent_id: Optional[UUID] = None
    tenant_id: Optional[UUID] = None

    # Timing
    checked_at: datetime = field(default_factory=datetime.utcnow)

    # Trend
    previous_value: Optional[float] = None
    trend: Optional[str] = None  # up, down, stable

    def evaluate(self) -> VitalStatus:
        """Evaluate status based on thresholds."""
        if self.value is None:
            return VitalStatus.UNKNOWN

        if self.critical_threshold is not None and self.value >= self.critical_threshold:
            return VitalStatus.CRITICAL
        if self.warning_threshold is not None and self.value >= self.warning_threshold:
            return VitalStatus.WARNING

        return VitalStatus.HEALTHY

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "name": self.name,
            "component": self.component,
            "status": self.status.value,
            "message": self.message,
            "value": self.value,
            "unit": self.unit,
            "agent_id": str(self.agent_id) if self.agent_id else None,
            "checked_at": self.checked_at.isoformat(),
            "trend": self.trend,
        }
