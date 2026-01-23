"""
Metrics Collector

Performance metrics collection and aggregation.
Implements Observability: Performance metrics from RACI.
"""

import logging
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID

from .models import Metric, MetricType

logger = logging.getLogger(__name__)


@dataclass
class MetricsSummary:
    """Summary of metrics for a time period."""
    name: str
    metric_type: MetricType
    count: int = 0
    sum_value: float = 0.0
    min_value: float = float("inf")
    max_value: float = float("-inf")
    avg_value: float = 0.0
    std_dev: float = 0.0
    p50: float = 0.0
    p90: float = 0.0
    p99: float = 0.0

    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None

    labels: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "type": self.metric_type.value,
            "count": self.count,
            "sum": self.sum_value,
            "min": self.min_value if self.count > 0 else None,
            "max": self.max_value if self.count > 0 else None,
            "avg": self.avg_value,
            "std_dev": self.std_dev,
            "percentiles": {
                "p50": self.p50,
                "p90": self.p90,
                "p99": self.p99,
            },
            "period": {
                "start": self.period_start.isoformat() if self.period_start else None,
                "end": self.period_end.isoformat() if self.period_end else None,
            },
            "labels": self.labels,
        }


class MetricsCollector:
    """
    Metrics Collector.

    Collects and aggregates performance metrics:
    - Counter metrics (monotonically increasing)
    - Gauge metrics (point-in-time values)
    - Histogram metrics (distributions)
    - Agent and run-level metrics
    """

    def __init__(self):
        """Initialize the metrics collector."""
        # Metric storage
        self._metrics: Dict[str, List[Metric]] = {}
        self._counters: Dict[str, float] = {}
        self._gauges: Dict[str, float] = {}

        # Histogram buckets
        self._default_buckets = [
            0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0,
            2.5, 5.0, 10.0, float("inf")
        ]

        # Configuration
        self._max_metrics_per_name = 10000
        self._retention_hours = 24

        # Export handlers
        self._exporters: List[Callable[[List[Metric]], None]] = []

        # Callbacks
        self._on_metric: List[Callable[[Metric], None]] = []

    def counter(
        self,
        name: str,
        value: float = 1.0,
        labels: Optional[Dict[str, str]] = None,
        agent_id: Optional[UUID] = None,
        run_id: Optional[UUID] = None,
        tenant_id: Optional[UUID] = None,
    ) -> Metric:
        """
        Record a counter metric.

        Args:
            name: Metric name
            value: Value to add
            labels: Metric labels
            agent_id: Agent ID
            run_id: Run ID
            tenant_id: Tenant ID

        Returns:
            Recorded metric
        """
        key = self._make_key(name, labels)
        self._counters[key] = self._counters.get(key, 0) + value

        return self._record(
            name=name,
            metric_type=MetricType.COUNTER,
            value=self._counters[key],
            labels=labels,
            agent_id=agent_id,
            run_id=run_id,
            tenant_id=tenant_id,
        )

    def gauge(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
        agent_id: Optional[UUID] = None,
        run_id: Optional[UUID] = None,
        tenant_id: Optional[UUID] = None,
    ) -> Metric:
        """
        Record a gauge metric.

        Args:
            name: Metric name
            value: Current value
            labels: Metric labels
            agent_id: Agent ID
            run_id: Run ID
            tenant_id: Tenant ID

        Returns:
            Recorded metric
        """
        key = self._make_key(name, labels)
        self._gauges[key] = value

        return self._record(
            name=name,
            metric_type=MetricType.GAUGE,
            value=value,
            labels=labels,
            agent_id=agent_id,
            run_id=run_id,
            tenant_id=tenant_id,
        )

    def histogram(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
        agent_id: Optional[UUID] = None,
        run_id: Optional[UUID] = None,
        tenant_id: Optional[UUID] = None,
        buckets: Optional[List[float]] = None,
    ) -> Metric:
        """
        Record a histogram metric.

        Args:
            name: Metric name
            value: Observed value
            labels: Metric labels
            agent_id: Agent ID
            run_id: Run ID
            tenant_id: Tenant ID
            buckets: Histogram buckets

        Returns:
            Recorded metric
        """
        buckets = buckets or self._default_buckets

        # Calculate bucket counts
        bucket_counts = {}
        for bucket in buckets:
            bucket_key = f"le_{bucket}" if bucket != float("inf") else "le_inf"
            bucket_counts[bucket_key] = 1 if value <= bucket else 0

        return self._record(
            name=name,
            metric_type=MetricType.HISTOGRAM,
            value=value,
            labels=labels,
            agent_id=agent_id,
            run_id=run_id,
            tenant_id=tenant_id,
            buckets=bucket_counts,
        )

    def timing(
        self,
        name: str,
        duration_ms: float,
        labels: Optional[Dict[str, str]] = None,
        agent_id: Optional[UUID] = None,
        run_id: Optional[UUID] = None,
        tenant_id: Optional[UUID] = None,
    ) -> Metric:
        """
        Record a timing metric (convenience for histograms).

        Args:
            name: Metric name
            duration_ms: Duration in milliseconds
            labels: Metric labels
            agent_id: Agent ID
            run_id: Run ID
            tenant_id: Tenant ID

        Returns:
            Recorded metric
        """
        return self.histogram(
            name=name,
            value=duration_ms,
            labels=labels,
            agent_id=agent_id,
            run_id=run_id,
            tenant_id=tenant_id,
        )

    def get_summary(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> MetricsSummary:
        """
        Get summary statistics for a metric.

        Args:
            name: Metric name
            labels: Filter by labels
            since: Start time
            until: End time

        Returns:
            Metrics summary
        """
        metrics = self._get_metrics(name, labels, since, until)

        if not metrics:
            return MetricsSummary(
                name=name,
                metric_type=MetricType.GAUGE,
                period_start=since,
                period_end=until,
            )

        values = [m.value for m in metrics]

        return MetricsSummary(
            name=name,
            metric_type=metrics[0].metric_type,
            count=len(values),
            sum_value=sum(values),
            min_value=min(values),
            max_value=max(values),
            avg_value=statistics.mean(values),
            std_dev=statistics.stdev(values) if len(values) > 1 else 0.0,
            p50=self._percentile(values, 50),
            p90=self._percentile(values, 90),
            p99=self._percentile(values, 99),
            period_start=since or min(m.timestamp for m in metrics),
            period_end=until or max(m.timestamp for m in metrics),
            labels=labels or {},
        )

    def get_metrics(
        self,
        name: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None,
        agent_id: Optional[UUID] = None,
        run_id: Optional[UUID] = None,
        since: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[Metric]:
        """Get raw metrics with optional filters."""
        all_metrics = []

        for metric_name, metrics in self._metrics.items():
            if name and metric_name != name:
                continue
            all_metrics.extend(metrics)

        # Apply filters
        if labels:
            all_metrics = [
                m for m in all_metrics
                if all(m.labels.get(k) == v for k, v in labels.items())
            ]
        if agent_id:
            all_metrics = [m for m in all_metrics if m.agent_id == agent_id]
        if run_id:
            all_metrics = [m for m in all_metrics if m.run_id == run_id]
        if since:
            all_metrics = [m for m in all_metrics if m.timestamp >= since]

        # Sort by timestamp descending
        all_metrics.sort(key=lambda m: m.timestamp, reverse=True)
        return all_metrics[:limit]

    def get_current_value(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None,
    ) -> Optional[float]:
        """Get the current value for a counter or gauge."""
        key = self._make_key(name, labels)

        if key in self._gauges:
            return self._gauges[key]
        if key in self._counters:
            return self._counters[key]

        return None

    def add_exporter(self, exporter: Callable[[List[Metric]], None]) -> None:
        """Add a metrics exporter."""
        self._exporters.append(exporter)

    def export(self) -> None:
        """Export all recent metrics."""
        all_metrics = []
        cutoff = datetime.utcnow() - timedelta(minutes=1)

        for metrics in self._metrics.values():
            recent = [m for m in metrics if m.timestamp >= cutoff]
            all_metrics.extend(recent)

        for exporter in self._exporters:
            try:
                exporter(all_metrics)
            except Exception as e:
                logger.error(f"Metrics export error: {e}")

    def on_metric(self, callback: Callable[[Metric], None]) -> None:
        """Register callback for new metrics."""
        self._on_metric.append(callback)

    def clear(self, older_than: Optional[datetime] = None) -> int:
        """Clear old metrics."""
        if older_than is None:
            older_than = datetime.utcnow() - timedelta(hours=self._retention_hours)

        count = 0
        for name in list(self._metrics.keys()):
            original_len = len(self._metrics[name])
            self._metrics[name] = [
                m for m in self._metrics[name]
                if m.timestamp >= older_than
            ]
            count += original_len - len(self._metrics[name])

        return count

    # Private methods

    def _record(
        self,
        name: str,
        metric_type: MetricType,
        value: float,
        labels: Optional[Dict[str, str]] = None,
        agent_id: Optional[UUID] = None,
        run_id: Optional[UUID] = None,
        tenant_id: Optional[UUID] = None,
        buckets: Optional[Dict[str, int]] = None,
    ) -> Metric:
        """Record a metric."""
        metric = Metric(
            name=name,
            metric_type=metric_type,
            value=value,
            labels=labels or {},
            agent_id=agent_id,
            run_id=run_id,
            tenant_id=tenant_id,
            buckets=buckets,
        )

        # Store metric
        if name not in self._metrics:
            self._metrics[name] = []
        self._metrics[name].append(metric)

        # Trim if needed
        if len(self._metrics[name]) > self._max_metrics_per_name:
            self._metrics[name] = self._metrics[name][-self._max_metrics_per_name:]

        # Notify callbacks
        for callback in self._on_metric:
            try:
                callback(metric)
            except Exception as e:
                logger.error(f"Metric callback error: {e}")

        return metric

    def _get_metrics(
        self,
        name: str,
        labels: Optional[Dict[str, str]],
        since: Optional[datetime],
        until: Optional[datetime],
    ) -> List[Metric]:
        """Get metrics for a name with filters."""
        metrics = self._metrics.get(name, [])

        if labels:
            metrics = [
                m for m in metrics
                if all(m.labels.get(k) == v for k, v in labels.items())
            ]
        if since:
            metrics = [m for m in metrics if m.timestamp >= since]
        if until:
            metrics = [m for m in metrics if m.timestamp <= until]

        return metrics

    def _make_key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        """Create a unique key for a metric name + labels."""
        if not labels:
            return name

        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def _percentile(self, values: List[float], percentile: float) -> float:
        """Calculate a percentile value."""
        if not values:
            return 0.0

        sorted_values = sorted(values)
        index = (percentile / 100) * (len(sorted_values) - 1)

        if index.is_integer():
            return sorted_values[int(index)]

        lower = sorted_values[int(index)]
        upper = sorted_values[int(index) + 1]
        return lower + (upper - lower) * (index - int(index))


# Global metrics collector
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector
