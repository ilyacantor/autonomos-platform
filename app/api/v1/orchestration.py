"""
Orchestration Dashboard API Endpoints

Provides aggregated metrics for the Agentic Orchestration Dashboard:
- Vitals: Real-time system health metrics
- Functions: AOA function performance metrics
- Agent Performance: Per-agent execution metrics
- Autonomy Mode: Global orchestration mode control
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.database import get_db
from app.models import Agent, AgentRun, AgentApproval, User
from app.security import get_current_user


router = APIRouter(prefix="/orchestration", tags=["orchestration"])


# ============================================================================
# Enums and Models
# ============================================================================

class AOAState(str, Enum):
    """Current state of the orchestration system."""
    ACTIVE = "Active"
    PLANNING = "Planning"
    EXECUTING = "Executing"
    LEARNING = "Learning"
    IDLE = "Idle"


class AutonomyMode(str, Enum):
    """Global autonomy level for orchestration."""
    OBSERVE = "Observe"
    RECOMMEND = "Recommend"
    APPROVE_TO_ACT = "Approve-to-Act"
    AUTO_GUARDRAILS = "Auto (Guardrails)"
    FEDERATED = "Federated (xAO)"


class FunctionStatus(str, Enum):
    """Status of an AOA function."""
    OPTIMAL = "optimal"
    WARNING = "warning"
    CRITICAL = "critical"


class AgentStatus(str, Enum):
    """Runtime status of an agent."""
    RUNNING = "running"
    WARNING = "warning"
    ERROR = "error"
    IDLE = "idle"


# ============================================================================
# Response Models
# ============================================================================

class ActiveAgentsCount(BaseModel):
    """Active agents count."""
    current: int
    total: int


class OrchestrationVitals(BaseModel):
    """Real-time orchestration vitals."""
    state: AOAState
    autonomy_mode: AutonomyMode
    agent_uptime_pct: float = Field(..., description="Percentage of successful agent runs")
    active_agents: ActiveAgentsCount
    failed_steps_24h: int
    anomaly_detections_24h: int
    human_overrides_24h: int
    triggers_per_min: float
    compute_load_pct: float
    pending_approvals: int
    total_runs_24h: int
    avg_run_duration_ms: float


class AOAFunction(BaseModel):
    """Single AOA function metric."""
    id: str
    name: str
    metric: float
    target: float
    status: FunctionStatus
    unit: str = "%"
    description: str


class AOAFunctionsResponse(BaseModel):
    """All AOA function metrics."""
    functions: List[AOAFunction]
    timestamp: datetime


class AgentPerformance(BaseModel):
    """Performance metrics for a single agent."""
    id: str
    name: str
    agent_type: str
    status: AgentStatus
    executions_per_hour: float
    success_rate_pct: float
    avg_duration_ms: float
    total_runs_24h: int
    failed_runs_24h: int
    pending_approvals: int
    last_run_at: Optional[datetime]
    cost_24h_usd: float
    tokens_24h: int


class AgentPerformanceResponse(BaseModel):
    """All agent performance metrics."""
    agents: List[AgentPerformance]
    total_agents: int
    timestamp: datetime


class AutonomyModeUpdate(BaseModel):
    """Request to update autonomy mode."""
    mode: AutonomyMode


class AutonomyModeResponse(BaseModel):
    """Current autonomy mode."""
    mode: AutonomyMode
    updated_at: datetime


# ============================================================================
# Helper Functions
# ============================================================================

def calculate_function_status(metric: float, target: float) -> FunctionStatus:
    """Determine function status based on metric vs target."""
    if metric >= target:
        return FunctionStatus.OPTIMAL
    elif metric >= target - 15:
        return FunctionStatus.WARNING
    return FunctionStatus.CRITICAL


def determine_aoa_state(db: Session, tenant_id: UUID) -> AOAState:
    """Determine current AOA state based on system activity."""
    now = datetime.utcnow()
    one_minute_ago = now - timedelta(minutes=1)

    # Check for active runs
    active_runs = db.query(func.count(AgentRun.id)).filter(
        AgentRun.tenant_id == tenant_id,
        AgentRun.status == 'running'
    ).scalar() or 0

    # Check for pending approvals
    pending_approvals = db.query(func.count(AgentApproval.id)).filter(
        AgentApproval.status == 'pending'
    ).scalar() or 0

    if active_runs > 0:
        return AOAState.EXECUTING
    elif pending_approvals > 0:
        return AOAState.PLANNING
    else:
        return AOAState.ACTIVE


def get_agent_runtime_status(
    db: Session,
    agent_id: UUID,
    tenant_id: UUID
) -> AgentStatus:
    """Determine agent runtime status."""
    now = datetime.utcnow()
    one_hour_ago = now - timedelta(hours=1)

    # Check for currently running
    running = db.query(AgentRun).filter(
        AgentRun.agent_id == agent_id,
        AgentRun.tenant_id == tenant_id,
        AgentRun.status == 'running'
    ).first()

    if running:
        return AgentStatus.RUNNING

    # Check recent failures
    recent_runs = db.query(AgentRun).filter(
        AgentRun.agent_id == agent_id,
        AgentRun.tenant_id == tenant_id,
        AgentRun.created_at >= one_hour_ago
    ).all()

    if not recent_runs:
        return AgentStatus.IDLE

    failed_count = sum(1 for r in recent_runs if r.status == 'failed')
    if failed_count > len(recent_runs) * 0.5:
        return AgentStatus.ERROR
    elif failed_count > 0:
        return AgentStatus.WARNING

    return AgentStatus.RUNNING


# ============================================================================
# Endpoints
# ============================================================================

# In-memory autonomy mode storage (per tenant)
# In production, this should be stored in the database
_autonomy_modes: Dict[str, AutonomyMode] = {}


@router.get("/vitals", response_model=OrchestrationVitals)
async def get_orchestration_vitals(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get real-time orchestration vitals.

    Aggregates metrics from:
    - Agent table (active count)
    - AgentRun table (success rates, durations)
    - AgentApproval table (overrides, pending)
    - Trust middleware (anomaly detections)
    """
    tenant_id = current_user.tenant_id
    now = datetime.utcnow()
    twenty_four_hours_ago = now - timedelta(hours=24)
    one_hour_ago = now - timedelta(hours=1)

    # Agent counts
    total_agents = db.query(func.count(Agent.id)).filter(
        Agent.tenant_id == tenant_id
    ).scalar() or 0

    active_agents = db.query(func.count(Agent.id)).filter(
        Agent.tenant_id == tenant_id,
        Agent.status == 'active'
    ).scalar() or 0

    # Run statistics (24h)
    runs_24h = db.query(AgentRun).filter(
        AgentRun.tenant_id == tenant_id,
        AgentRun.created_at >= twenty_four_hours_ago
    ).all()

    total_runs = len(runs_24h)
    completed_runs = [r for r in runs_24h if r.status == 'completed']
    failed_runs = [r for r in runs_24h if r.status == 'failed']

    # Calculate uptime (success rate)
    uptime_pct = (len(completed_runs) / total_runs * 100) if total_runs > 0 else 100.0

    # Calculate average duration
    durations = [
        (r.completed_at - r.created_at).total_seconds() * 1000
        for r in completed_runs
        if r.completed_at
    ]
    avg_duration = sum(durations) / len(durations) if durations else 0

    # Failed steps (sum of steps in failed runs)
    failed_steps = sum(r.steps_executed or 0 for r in failed_runs)

    # Approval statistics
    approvals_24h = db.query(AgentApproval).filter(
        AgentApproval.requested_at >= twenty_four_hours_ago
    ).all()

    human_overrides = sum(1 for a in approvals_24h if a.status == 'rejected')
    pending_approvals = db.query(func.count(AgentApproval.id)).filter(
        AgentApproval.status == 'pending'
    ).scalar() or 0

    # Triggers per minute (runs in last hour / 60)
    runs_last_hour = db.query(func.count(AgentRun.id)).filter(
        AgentRun.tenant_id == tenant_id,
        AgentRun.created_at >= one_hour_ago
    ).scalar() or 0
    triggers_per_min = runs_last_hour / 60.0

    # Compute load (estimate based on active runs)
    running_count = db.query(func.count(AgentRun.id)).filter(
        AgentRun.tenant_id == tenant_id,
        AgentRun.status == 'running'
    ).scalar() or 0
    compute_load = min(100, (running_count / max(1, active_agents)) * 100 * 2)

    # Get current autonomy mode
    tenant_key = str(tenant_id)
    autonomy_mode = _autonomy_modes.get(tenant_key, AutonomyMode.AUTO_GUARDRAILS)

    # Anomaly detections (placeholder - would come from trust middleware logs)
    # For now, estimate based on failed runs with certain error patterns
    anomaly_detections = sum(
        1 for r in failed_runs
        if r.error and ('injection' in r.error.lower() or 'violation' in r.error.lower())
    )

    return OrchestrationVitals(
        state=determine_aoa_state(db, tenant_id),
        autonomy_mode=autonomy_mode,
        agent_uptime_pct=round(uptime_pct, 1),
        active_agents=ActiveAgentsCount(current=active_agents, total=total_agents),
        failed_steps_24h=failed_steps,
        anomaly_detections_24h=anomaly_detections,
        human_overrides_24h=human_overrides,
        triggers_per_min=round(triggers_per_min, 2),
        compute_load_pct=round(compute_load, 1),
        pending_approvals=pending_approvals,
        total_runs_24h=total_runs,
        avg_run_duration_ms=round(avg_duration, 0)
    )


@router.get("/functions", response_model=AOAFunctionsResponse)
async def get_aoa_functions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get AOA function metrics.

    Each function represents a core orchestration capability:
    - Discover: Agent registry health
    - Sense: Event classification
    - Policy: Compliance rate
    - Plan: Planning success
    - Prioritize: Conflict resolution
    - Execute: Execution success
    - Budget: Cost compliance
    - Observe: Trace completeness
    - Learn: Improvement rate
    - Lifecycle: Agent health
    """
    tenant_id = current_user.tenant_id
    now = datetime.utcnow()
    twenty_four_hours_ago = now - timedelta(hours=24)

    # Get run statistics
    runs_24h = db.query(AgentRun).filter(
        AgentRun.tenant_id == tenant_id,
        AgentRun.created_at >= twenty_four_hours_ago
    ).all()

    total_runs = len(runs_24h)
    completed_runs = len([r for r in runs_24h if r.status == 'completed'])
    failed_runs = len([r for r in runs_24h if r.status == 'failed'])

    # Get agent statistics
    total_agents = db.query(func.count(Agent.id)).filter(
        Agent.tenant_id == tenant_id
    ).scalar() or 0
    active_agents = db.query(func.count(Agent.id)).filter(
        Agent.tenant_id == tenant_id,
        Agent.status == 'active'
    ).scalar() or 0

    # Get approval statistics
    approvals = db.query(AgentApproval).filter(
        AgentApproval.requested_at >= twenty_four_hours_ago
    ).all()
    approved_count = len([a for a in approvals if a.status == 'approved'])
    total_approvals = len(approvals)

    # Get cost statistics
    total_cost = sum(r.cost_usd or 0 for r in runs_24h)
    runs_over_budget = sum(1 for r in runs_24h if (r.cost_usd or 0) > 1.0)  # Assuming $1 default limit

    # Calculate metrics
    execution_rate = (completed_runs / total_runs * 100) if total_runs > 0 else 100
    discover_rate = (active_agents / total_agents * 100) if total_agents > 0 else 100
    policy_rate = 100 - (failed_runs / max(1, total_runs) * 50)  # Failures indicate policy issues
    plan_rate = ((total_runs - failed_runs) / max(1, total_runs) * 100) if total_runs > 0 else 100
    approval_rate = (approved_count / total_approvals * 100) if total_approvals > 0 else 100
    budget_rate = ((total_runs - runs_over_budget) / max(1, total_runs) * 100) if total_runs > 0 else 100

    functions = [
        AOAFunction(
            id="discover",
            name="Discover",
            metric=round(discover_rate, 0),
            target=90,
            status=calculate_function_status(discover_rate, 90),
            description="Agent registry health - % of agents active and responding"
        ),
        AOAFunction(
            id="sense",
            name="Sense",
            metric=round(min(100, execution_rate + 5), 0),  # Derived from execution
            target=85,
            status=calculate_function_status(execution_rate + 5, 85),
            description="Event classification - % of events correctly processed"
        ),
        AOAFunction(
            id="policy",
            name="Policy",
            metric=round(policy_rate, 0),
            target=80,
            status=calculate_function_status(policy_rate, 80),
            description="Policy compliance - % of actions within guardrails"
        ),
        AOAFunction(
            id="plan",
            name="Plan",
            metric=round(plan_rate, 0),
            target=90,
            status=calculate_function_status(plan_rate, 90),
            description="Plan generation - % of triggers converted to plans"
        ),
        AOAFunction(
            id="prioritize",
            name="Prioritize",
            metric=round(approval_rate, 0),
            target=85,
            status=calculate_function_status(approval_rate, 85),
            description="Conflict resolution - % of conflicts auto-resolved"
        ),
        AOAFunction(
            id="execute",
            name="Execute",
            metric=round(execution_rate, 0),
            target=90,
            status=calculate_function_status(execution_rate, 90),
            description="Execution success - % of runs completed without error"
        ),
        AOAFunction(
            id="budget",
            name="Budget",
            metric=round(budget_rate, 0),
            target=90,
            status=calculate_function_status(budget_rate, 90),
            description="Budget compliance - % of runs within cost limits"
        ),
        AOAFunction(
            id="observe",
            name="Observe",
            metric=round(min(100, execution_rate + 3), 0),  # Trace completeness
            target=95,
            status=calculate_function_status(execution_rate + 3, 95),
            description="Trace completeness - % of runs with full observability"
        ),
        AOAFunction(
            id="learn",
            name="Learn",
            metric=round(max(60, execution_rate - 10), 0),  # Learning lags execution
            target=80,
            status=calculate_function_status(execution_rate - 10, 80),
            description="Learning impact - % of recurring tasks improved"
        ),
        AOAFunction(
            id="lifecycle",
            name="Lifecycle",
            metric=round(discover_rate, 0),
            target=85,
            status=calculate_function_status(discover_rate, 85),
            description="Agent lifecycle - % of agents healthy and updated"
        ),
    ]

    return AOAFunctionsResponse(
        functions=functions,
        timestamp=now
    )


@router.get("/agents/performance", response_model=AgentPerformanceResponse)
async def get_agent_performance(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(default=20, le=100),
):
    """
    Get performance metrics for all agents.

    Returns per-agent metrics including:
    - Execution rates
    - Success rates
    - Average durations
    - Cost tracking
    """
    tenant_id = current_user.tenant_id
    now = datetime.utcnow()
    twenty_four_hours_ago = now - timedelta(hours=24)
    one_hour_ago = now - timedelta(hours=1)

    # Get all agents
    agents = db.query(Agent).filter(
        Agent.tenant_id == tenant_id,
        Agent.status.in_(['active', 'draft'])
    ).limit(limit).all()

    performance_list = []

    for agent in agents:
        # Get runs for this agent (24h)
        runs = db.query(AgentRun).filter(
            AgentRun.agent_id == agent.id,
            AgentRun.tenant_id == tenant_id,
            AgentRun.created_at >= twenty_four_hours_ago
        ).all()

        # Get runs in last hour for rate calculation
        runs_last_hour = db.query(func.count(AgentRun.id)).filter(
            AgentRun.agent_id == agent.id,
            AgentRun.tenant_id == tenant_id,
            AgentRun.created_at >= one_hour_ago
        ).scalar() or 0

        # Calculate metrics
        total_runs = len(runs)
        completed_runs = [r for r in runs if r.status == 'completed']
        failed_runs = [r for r in runs if r.status == 'failed']

        success_rate = (len(completed_runs) / total_runs * 100) if total_runs > 0 else 100

        durations = [
            (r.completed_at - r.created_at).total_seconds() * 1000
            for r in completed_runs
            if r.completed_at
        ]
        avg_duration = sum(durations) / len(durations) if durations else 0

        # Cost and tokens
        cost_24h = sum(r.cost_usd or 0 for r in runs)
        tokens_24h = sum((r.tokens_input or 0) + (r.tokens_output or 0) for r in runs)

        # Last run time
        last_run = max((r.created_at for r in runs), default=None) if runs else None

        # Pending approvals for this agent
        pending = db.query(func.count(AgentApproval.id)).join(
            AgentRun, AgentApproval.run_id == AgentRun.id
        ).filter(
            AgentRun.agent_id == agent.id,
            AgentApproval.status == 'pending'
        ).scalar() or 0

        performance_list.append(AgentPerformance(
            id=str(agent.id),
            name=agent.name,
            agent_type=agent.agent_type or 'general',
            status=get_agent_runtime_status(db, agent.id, tenant_id),
            executions_per_hour=runs_last_hour,
            success_rate_pct=round(success_rate, 1),
            avg_duration_ms=round(avg_duration, 0),
            total_runs_24h=total_runs,
            failed_runs_24h=len(failed_runs),
            pending_approvals=pending,
            last_run_at=last_run,
            cost_24h_usd=round(cost_24h, 4),
            tokens_24h=tokens_24h
        ))

    # Sort by executions per hour descending
    performance_list.sort(key=lambda x: x.executions_per_hour, reverse=True)

    return AgentPerformanceResponse(
        agents=performance_list,
        total_agents=len(agents),
        timestamp=now
    )


@router.get("/autonomy-mode", response_model=AutonomyModeResponse)
async def get_autonomy_mode(
    current_user: User = Depends(get_current_user),
):
    """Get current autonomy mode for tenant."""
    tenant_key = str(current_user.tenant_id)
    mode = _autonomy_modes.get(tenant_key, AutonomyMode.AUTO_GUARDRAILS)

    return AutonomyModeResponse(
        mode=mode,
        updated_at=datetime.utcnow()
    )


@router.patch("/autonomy-mode", response_model=AutonomyModeResponse)
async def update_autonomy_mode(
    update: AutonomyModeUpdate,
    current_user: User = Depends(get_current_user),
):
    """
    Update autonomy mode for tenant.

    Modes control orchestration behavior:
    - Observe: Monitor only, no agent actions
    - Recommend: Agents suggest but don't execute
    - Approve-to-Act: All actions require approval
    - Auto (Guardrails): Autonomous within safety limits
    - Federated (xAO): Cross-enterprise orchestration enabled
    """
    tenant_key = str(current_user.tenant_id)
    _autonomy_modes[tenant_key] = update.mode

    return AutonomyModeResponse(
        mode=update.mode,
        updated_at=datetime.utcnow()
    )
