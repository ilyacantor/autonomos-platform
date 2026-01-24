"""
AOA Dashboard Metrics API

Provides aggregated KPIs for UI dashboards:
- Agent activity metrics
- Workflow performance
- Cost tracking
- Governance stats
- Real-time vitals
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Header, Query
from pydantic import BaseModel

from app.agentic.registry import get_agent_inventory, AgentStatus
from app.agentic.observability import get_metrics_collector, get_vitals_monitor, get_tracer
from app.agentic.governance import get_budget_enforcer, get_policy_engine
from app.agentic.approval import get_approval_workflow
from app.agentic.simulation import get_metrics_bridge

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/aoa", tags=["aoa-dashboard"])


# Response Models

class AgentMetrics(BaseModel):
    """Agent-related metrics."""
    total_registered: int
    active: int
    inactive: int
    by_status: Dict[str, int]
    by_type: Dict[str, int]
    by_trust_tier: Dict[str, int]


class WorkflowMetrics(BaseModel):
    """Workflow execution metrics."""
    active_workflows: int
    completed_24h: int
    failed_24h: int
    completion_rate: float
    avg_duration_ms: float
    throughput_per_min: float


class ChaosMetrics(BaseModel):
    """Chaos/resilience metrics."""
    events_triggered: int
    events_recovered: int
    events_failed: int
    recovery_rate: float
    by_type: Dict[str, int]


class CostMetrics(BaseModel):
    """Cost tracking metrics."""
    today_usd: float
    week_usd: float
    month_usd: float
    tokens_today: int
    budget_remaining_usd: Optional[float]
    budget_utilization: float


class GovernanceMetrics(BaseModel):
    """Governance and policy metrics."""
    policies_active: int
    policy_violations_24h: int
    pending_approvals: int
    approvals_auto_approved: int
    approvals_escalated: int


class VitalsSnapshot(BaseModel):
    """System vitals snapshot."""
    cpu_usage: Optional[float]
    memory_usage: Optional[float]
    workflows_active: int
    throughput_tps: float
    chaos_recovery_rate: float
    status: str  # healthy, warning, critical


class DashboardResponse(BaseModel):
    """Complete dashboard response."""
    timestamp: str
    tenant_id: Optional[str]

    # Metrics sections
    agents: AgentMetrics
    workflows: WorkflowMetrics
    chaos: ChaosMetrics
    costs: CostMetrics
    governance: GovernanceMetrics
    vitals: VitalsSnapshot

    # Simulation status
    simulation_active: bool
    simulation_scenario_id: Optional[str]


class TimeSeriesPoint(BaseModel):
    """Single point in a time series."""
    timestamp: str
    value: float


class TimeSeriesResponse(BaseModel):
    """Time series data response."""
    metric_name: str
    period: str
    points: List[TimeSeriesPoint]


# Endpoints

@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    tenant_id: str = Header(None, alias="X-Tenant-ID"),
):
    """
    Get complete dashboard metrics.

    Returns aggregated KPIs across all AOA modules for UI visualization.
    """
    tenant_id = tenant_id or "default"
    tenant_uuid = None
    try:
        tenant_uuid = UUID(tenant_id)
    except (ValueError, TypeError):
        pass

    # Get module instances
    inventory = get_agent_inventory()
    metrics_collector = get_metrics_collector()
    vitals_monitor = get_vitals_monitor()
    budget_enforcer = get_budget_enforcer()
    policy_engine = get_policy_engine()
    approval_workflow = get_approval_workflow()
    metrics_bridge = get_metrics_bridge()

    # Agent metrics
    all_agents = list(inventory._agents.values())  # Access internal for stats
    agents = AgentMetrics(
        total_registered=len(all_agents),
        active=sum(1 for a in all_agents if a.status == AgentStatus.ACTIVE),
        inactive=sum(1 for a in all_agents if a.status != AgentStatus.ACTIVE),
        by_status={s.value: sum(1 for a in all_agents if a.status == s) for s in AgentStatus},
        by_type={},  # Would need agent_type grouping
        by_trust_tier={},  # Would need trust_tier grouping
    )

    # Workflow metrics from simulation bridge
    sim_metrics = metrics_bridge.get_metrics()
    workflows = WorkflowMetrics(
        active_workflows=len(metrics_bridge._workflow_traces),
        completed_24h=sim_metrics.workflows_completed,
        failed_24h=sim_metrics.workflows_failed,
        completion_rate=metrics_bridge.get_completion_rate(),
        avg_duration_ms=sim_metrics.total_duration_ms / max(sim_metrics.workflows_completed, 1),
        throughput_per_min=metrics_bridge.get_throughput_tps() * 60,
    )

    # Chaos metrics
    chaos = ChaosMetrics(
        events_triggered=sim_metrics.chaos_events_triggered,
        events_recovered=sim_metrics.chaos_events_recovered,
        events_failed=sim_metrics.chaos_events_failed,
        recovery_rate=metrics_bridge.get_chaos_recovery_rate(),
        by_type={},  # Would track per-type
    )

    # Cost metrics
    costs = CostMetrics(
        today_usd=sim_metrics.total_cost_usd,
        week_usd=sim_metrics.total_cost_usd,  # Would need time-based tracking
        month_usd=sim_metrics.total_cost_usd,
        tokens_today=sim_metrics.total_tokens,
        budget_remaining_usd=None,
        budget_utilization=0.0,
    )

    # Get budget info if tenant exists
    if tenant_uuid:
        budget = budget_enforcer._budgets.get(tenant_uuid)
        if budget:
            usage = budget_enforcer.get_usage(tenant_uuid)
            costs.today_usd = usage.get("today_usd", 0)
            costs.month_usd = usage.get("month_usd", 0)
            costs.budget_remaining_usd = budget.monthly_limit_usd - costs.month_usd
            costs.budget_utilization = costs.month_usd / budget.monthly_limit_usd if budget.monthly_limit_usd > 0 else 0

    # Governance metrics
    pending = approval_workflow.get_pending_requests()
    governance = GovernanceMetrics(
        policies_active=len(policy_engine._policies),
        policy_violations_24h=0,  # Would need tracking
        pending_approvals=len(pending),
        approvals_auto_approved=0,
        approvals_escalated=0,
    )

    # Vitals snapshot
    tps = metrics_bridge.get_throughput_tps()
    recovery_rate = metrics_bridge.get_chaos_recovery_rate()

    vitals_status = "healthy"
    if tps < 0.5 or recovery_rate < 0.8:
        vitals_status = "warning"
    if tps < 0.2 or recovery_rate < 0.5:
        vitals_status = "critical"

    vitals = VitalsSnapshot(
        cpu_usage=None,  # Would get from system
        memory_usage=None,
        workflows_active=len(metrics_bridge._workflow_traces),
        throughput_tps=tps,
        chaos_recovery_rate=recovery_rate,
        status=vitals_status,
    )

    return DashboardResponse(
        timestamp=datetime.utcnow().isoformat(),
        tenant_id=tenant_id,
        agents=agents,
        workflows=workflows,
        chaos=chaos,
        costs=costs,
        governance=governance,
        vitals=vitals,
        simulation_active=len(metrics_bridge._workflow_traces) > 0,
        simulation_scenario_id=None,
    )


@router.get("/metrics/timeseries", response_model=TimeSeriesResponse)
async def get_timeseries(
    metric: str = Query(..., description="Metric name (e.g., 'workflows.completed')"),
    period: str = Query("1h", description="Time period: 1h, 6h, 24h, 7d"),
    tenant_id: str = Header(None, alias="X-Tenant-ID"),
):
    """
    Get time-series data for a specific metric.

    Useful for charts and trend analysis.
    """
    metrics_collector = get_metrics_collector()

    # Map period to timedelta
    period_map = {
        "1h": timedelta(hours=1),
        "6h": timedelta(hours=6),
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
    }

    delta = period_map.get(period, timedelta(hours=1))
    cutoff = datetime.utcnow() - delta

    # Get metric data (simplified - real impl would query time-series store)
    points = []

    # Generate sample points for now
    current = cutoff
    while current < datetime.utcnow():
        points.append(TimeSeriesPoint(
            timestamp=current.isoformat(),
            value=0.0,  # Would get actual value
        ))
        current += timedelta(minutes=5)

    return TimeSeriesResponse(
        metric_name=metric,
        period=period,
        points=points,
    )


@router.get("/agents/summary")
async def get_agents_summary(
    tenant_id: str = Header(None, alias="X-Tenant-ID"),
):
    """Get summary of registered agents."""
    inventory = get_agent_inventory()
    stats = inventory.get_stats()

    return {
        "total": stats.total_agents,
        "active": stats.active_agents,
        "by_status": stats.by_status,
        "by_domain": stats.by_domain,
        "by_trust_tier": stats.by_trust_tier,
    }


@router.get("/workflows/active")
async def get_active_workflows(
    tenant_id: str = Header(None, alias="X-Tenant-ID"),
):
    """Get list of currently active workflows."""
    metrics_bridge = get_metrics_bridge()

    return {
        "count": len(metrics_bridge._workflow_traces),
        "workflow_ids": list(metrics_bridge._workflow_traces.keys()),
    }


@router.get("/approvals/pending")
async def get_pending_approvals(
    tenant_id: str = Header(None, alias="X-Tenant-ID"),
):
    """Get pending approval requests."""
    approval_workflow = get_approval_workflow()
    pending = approval_workflow.get_pending_requests()

    return {
        "count": len(pending),
        "requests": [
            {
                "id": str(r.id),
                "type": r.request_type.value,
                "priority": r.priority.value,
                "title": r.title,
                "created_at": r.created_at.isoformat(),
            }
            for r in pending[:20]  # Limit to 20
        ],
    }


@router.get("/health")
async def health_check():
    """Health check for AOA dashboard API."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "modules": {
            "registry": "ok",
            "observability": "ok",
            "governance": "ok",
            "simulation": "ok",
        }
    }
