"""
Metrics Bridge for Simulation

Bridges simulation execution to AOA observability modules:
- MetricsCollector for counters/gauges/histograms
- VitalsMonitor for system health
- BudgetEnforcer for cost tracking
- Tracer for distributed tracing
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from app.agentic.observability import (
    Tracer,
    MetricsCollector,
    VitalsMonitor,
    get_tracer,
    get_metrics_collector,
    get_vitals_monitor,
)
from app.agentic.governance import (
    BudgetEnforcer,
    get_budget_enforcer,
)

logger = logging.getLogger(__name__)


@dataclass
class SimulationMetrics:
    """Aggregated metrics from simulation."""
    # Workflow metrics
    workflows_started: int = 0
    workflows_completed: int = 0
    workflows_failed: int = 0

    # Task metrics
    tasks_started: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    tasks_retried: int = 0

    # Chaos metrics
    chaos_events_triggered: int = 0
    chaos_events_recovered: int = 0
    chaos_events_failed: int = 0

    # Performance metrics
    total_duration_ms: int = 0
    avg_task_duration_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0

    # Cost metrics
    total_cost_usd: float = 0.0
    total_tokens: int = 0

    # Agent metrics
    agents_active: int = 0
    agent_utilization: float = 0.0


class MetricsBridge:
    """
    Bridges simulation activity to AOA observability modules.

    Records all simulation metrics to:
    - MetricsCollector for time-series data
    - VitalsMonitor for health dashboards
    - BudgetEnforcer for cost tracking
    - Tracer for distributed traces
    """

    def __init__(self):
        self._tracer: Optional[Tracer] = None
        self._metrics: Optional[MetricsCollector] = None
        self._vitals: Optional[VitalsMonitor] = None
        self._budget: Optional[BudgetEnforcer] = None

        # Active traces
        self._workflow_traces: Dict[str, UUID] = {}  # workflow_id -> trace_id
        self._task_spans: Dict[str, UUID] = {}  # task_id -> span_id

        # Aggregated metrics
        self._simulation_metrics = SimulationMetrics()

    def initialize(self) -> None:
        """Initialize connections to AOA modules."""
        self._tracer = get_tracer()
        self._metrics = get_metrics_collector()
        self._vitals = get_vitals_monitor()
        self._budget = get_budget_enforcer()

        # Register vitals
        self._vitals.register_vital(
            name="simulation.workflows_active",
            component="simulation",
            warning_threshold=50,
            critical_threshold=100,
        )
        self._vitals.register_vital(
            name="simulation.chaos_recovery_rate",
            component="simulation",
            warning_threshold=0.7,
            critical_threshold=0.5,
        )
        self._vitals.register_vital(
            name="simulation.throughput_tps",
            component="simulation",
            warning_threshold=0.5,
            critical_threshold=0.2,
        )

    # -------------------------------------------------------------------------
    # Workflow Tracking
    # -------------------------------------------------------------------------

    def start_workflow_trace(
        self,
        workflow_id: str,
        workflow_type: str,
        tenant_id: Optional[UUID] = None,
    ) -> UUID:
        """Start a trace for a workflow execution."""
        if not self._tracer:
            self.initialize()

        trace = self._tracer.start_trace(
            name=f"workflow:{workflow_type}",
            tenant_id=tenant_id,
            attributes={
                "workflow_id": workflow_id,
                "workflow_type": workflow_type,
            }
        )

        self._workflow_traces[workflow_id] = trace.id

        # Update metrics
        self._simulation_metrics.workflows_started += 1
        self._metrics.counter(
            "simulation.workflows.started",
            1,
            labels={"workflow_type": workflow_type},
        )

        return trace.id

    def end_workflow_trace(
        self,
        workflow_id: str,
        status: str,
        duration_ms: int,
        tasks_completed: int,
        tasks_failed: int,
    ) -> None:
        """End a workflow trace."""
        trace_id = self._workflow_traces.pop(workflow_id, None)

        if trace_id and self._tracer:
            self._tracer.end_trace(trace_id)

        # Update metrics
        if status == "completed":
            self._simulation_metrics.workflows_completed += 1
            self._metrics.counter("simulation.workflows.completed", 1)
        else:
            self._simulation_metrics.workflows_failed += 1
            self._metrics.counter("simulation.workflows.failed", 1)

        self._simulation_metrics.total_duration_ms += duration_ms
        self._metrics.histogram("simulation.workflow.duration_ms", duration_ms)

    # -------------------------------------------------------------------------
    # Task Tracking
    # -------------------------------------------------------------------------

    def start_task_span(
        self,
        workflow_id: str,
        task_id: str,
        task_type: str,
        agent_id: Optional[str] = None,
    ) -> Optional[UUID]:
        """Start a span for a task execution."""
        if not self._tracer:
            self.initialize()

        trace_id = self._workflow_traces.get(workflow_id)
        if not trace_id:
            return None

        span = self._tracer.start_span(
            name=f"task:{task_type}",
            trace_id=trace_id,
            attributes={
                "task_id": task_id,
                "task_type": task_type,
                "agent_id": agent_id,
            }
        )

        self._task_spans[task_id] = span.id

        # Update metrics
        self._simulation_metrics.tasks_started += 1
        self._metrics.counter(
            "simulation.tasks.started",
            1,
            labels={"task_type": task_type},
        )

        return span.id

    def end_task_span(
        self,
        task_id: str,
        status: str,
        duration_ms: int,
        retry_count: int = 0,
        chaos_type: Optional[str] = None,
    ) -> None:
        """End a task span."""
        span_id = self._task_spans.pop(task_id, None)

        if span_id and self._tracer:
            self._tracer.end_span(span_id)

        # Update metrics
        if status == "completed":
            self._simulation_metrics.tasks_completed += 1
            self._metrics.counter("simulation.tasks.completed", 1)
        else:
            self._simulation_metrics.tasks_failed += 1
            self._metrics.counter("simulation.tasks.failed", 1)

        if retry_count > 0:
            self._simulation_metrics.tasks_retried += 1
            self._metrics.counter("simulation.tasks.retried", retry_count)

        self._metrics.histogram("simulation.task.duration_ms", duration_ms)

        # Chaos tracking
        if chaos_type:
            self._simulation_metrics.chaos_events_triggered += 1
            self._metrics.counter(
                "simulation.chaos.triggered",
                1,
                labels={"chaos_type": chaos_type},
            )

            if status == "completed":
                self._simulation_metrics.chaos_events_recovered += 1
                self._metrics.counter("simulation.chaos.recovered", 1)
            else:
                self._simulation_metrics.chaos_events_failed += 1
                self._metrics.counter("simulation.chaos.failed", 1)

    # -------------------------------------------------------------------------
    # Cost Tracking
    # -------------------------------------------------------------------------

    def record_cost(
        self,
        tenant_id: UUID,
        cost_usd: float,
        tokens: int,
        action: str,
    ) -> bool:
        """Record cost via BudgetEnforcer."""
        if not self._budget:
            self.initialize()

        self._simulation_metrics.total_cost_usd += cost_usd
        self._simulation_metrics.total_tokens += tokens

        # Check and record with budget enforcer
        check = self._budget.check_budget(tenant_id, cost_usd)
        if check.allowed:
            self._budget.record_cost(tenant_id, cost_usd, action)

        # Record metrics
        self._metrics.counter("simulation.cost.usd", cost_usd)
        self._metrics.counter("simulation.tokens.used", tokens)

        return check.allowed

    # -------------------------------------------------------------------------
    # Vitals Updates
    # -------------------------------------------------------------------------

    def update_vitals(self) -> None:
        """Update system vitals with current simulation state."""
        if not self._vitals:
            self.initialize()

        # Active workflows
        active_workflows = len(self._workflow_traces)
        self._vitals.record("simulation.workflows_active", float(active_workflows))

        # Chaos recovery rate
        total_chaos = self._simulation_metrics.chaos_events_triggered
        if total_chaos > 0:
            recovery_rate = self._simulation_metrics.chaos_events_recovered / total_chaos
            self._vitals.record("simulation.chaos_recovery_rate", recovery_rate)

        # Throughput
        if self._simulation_metrics.total_duration_ms > 0:
            tps = (self._simulation_metrics.tasks_completed * 1000) / self._simulation_metrics.total_duration_ms
            self._vitals.record("simulation.throughput_tps", tps)

    # -------------------------------------------------------------------------
    # Agent Tracking
    # -------------------------------------------------------------------------

    def record_agent_activity(
        self,
        agent_id: str,
        agent_type: str,
        task_id: str,
        success: bool,
    ) -> None:
        """Record agent activity."""
        self._metrics.counter(
            "simulation.agent.tasks",
            1,
            labels={
                "agent_type": agent_type,
                "success": str(success).lower(),
            }
        )

    def set_active_agents(self, count: int) -> None:
        """Set active agent count."""
        self._simulation_metrics.agents_active = count
        self._metrics.gauge("simulation.agents.active", count)

    # -------------------------------------------------------------------------
    # Getters
    # -------------------------------------------------------------------------

    def get_metrics(self) -> SimulationMetrics:
        """Get aggregated simulation metrics."""
        return self._simulation_metrics

    def get_completion_rate(self) -> float:
        """Calculate workflow completion rate."""
        total = self._simulation_metrics.workflows_completed + self._simulation_metrics.workflows_failed
        if total == 0:
            return 0.0
        return self._simulation_metrics.workflows_completed / total

    def get_chaos_recovery_rate(self) -> float:
        """Calculate chaos recovery rate."""
        total = self._simulation_metrics.chaos_events_triggered
        if total == 0:
            return 1.0  # No chaos = 100% recovery
        return self._simulation_metrics.chaos_events_recovered / total

    def get_throughput_tps(self) -> float:
        """Calculate tasks per second throughput."""
        if self._simulation_metrics.total_duration_ms == 0:
            return 0.0
        return (self._simulation_metrics.tasks_completed * 1000) / self._simulation_metrics.total_duration_ms

    def reset(self) -> None:
        """Reset all metrics."""
        self._simulation_metrics = SimulationMetrics()
        self._workflow_traces.clear()
        self._task_spans.clear()


# Singleton instance
_metrics_bridge: Optional[MetricsBridge] = None


def get_metrics_bridge() -> MetricsBridge:
    """Get singleton metrics bridge."""
    global _metrics_bridge
    if _metrics_bridge is None:
        _metrics_bridge = MetricsBridge()
        _metrics_bridge.initialize()
    return _metrics_bridge
