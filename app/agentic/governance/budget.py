"""
Budget Enforcer

Budget enforcement for agent execution.
Implements Economics: Budget enforcement from RACI.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


@dataclass
class Budget:
    """Budget configuration for an agent or tenant."""
    id: UUID = field(default_factory=uuid4)

    # Scope
    agent_id: Optional[UUID] = None
    tenant_id: Optional[UUID] = None

    # Budget limits
    daily_limit_usd: float = 100.0
    weekly_limit_usd: float = 500.0
    monthly_limit_usd: float = 2000.0

    # Per-action limits
    per_action_limit_usd: float = 1.0
    per_run_limit_usd: float = 10.0

    # Alert thresholds (percentage of limit)
    alert_threshold_50: bool = True
    alert_threshold_75: bool = True
    alert_threshold_90: bool = True
    alert_threshold_100: bool = True

    # Actions when limit reached
    action_on_limit: str = "block"  # block, warn, alert_only

    # Current usage
    daily_usage_usd: float = 0.0
    weekly_usage_usd: float = 0.0
    monthly_usage_usd: float = 0.0

    # Tracking
    last_reset_daily: datetime = field(default_factory=datetime.utcnow)
    last_reset_weekly: datetime = field(default_factory=datetime.utcnow)
    last_reset_monthly: datetime = field(default_factory=datetime.utcnow)

    # Status
    active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def daily_remaining(self) -> float:
        """Get remaining daily budget."""
        return max(0, self.daily_limit_usd - self.daily_usage_usd)

    def weekly_remaining(self) -> float:
        """Get remaining weekly budget."""
        return max(0, self.weekly_limit_usd - self.weekly_usage_usd)

    def monthly_remaining(self) -> float:
        """Get remaining monthly budget."""
        return max(0, self.monthly_limit_usd - self.monthly_usage_usd)

    def daily_usage_percent(self) -> float:
        """Get daily usage as percentage."""
        if self.daily_limit_usd == 0:
            return 0.0
        return (self.daily_usage_usd / self.daily_limit_usd) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "agent_id": str(self.agent_id) if self.agent_id else None,
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "limits": {
                "daily_usd": self.daily_limit_usd,
                "weekly_usd": self.weekly_limit_usd,
                "monthly_usd": self.monthly_limit_usd,
                "per_action_usd": self.per_action_limit_usd,
                "per_run_usd": self.per_run_limit_usd,
            },
            "usage": {
                "daily_usd": self.daily_usage_usd,
                "weekly_usd": self.weekly_usage_usd,
                "monthly_usd": self.monthly_usage_usd,
            },
            "remaining": {
                "daily_usd": self.daily_remaining(),
                "weekly_usd": self.weekly_remaining(),
                "monthly_usd": self.monthly_remaining(),
            },
            "usage_percent": {
                "daily": self.daily_usage_percent(),
            },
            "action_on_limit": self.action_on_limit,
            "active": self.active,
        }


@dataclass
class BudgetAlert:
    """Alert for budget threshold."""
    id: UUID = field(default_factory=uuid4)
    budget_id: UUID = field(default_factory=uuid4)

    # Context
    agent_id: Optional[UUID] = None
    tenant_id: Optional[UUID] = None

    # Alert details
    alert_type: str = ""  # daily_50, daily_75, daily_90, daily_100, etc.
    threshold_percent: int = 0
    period: str = "daily"  # daily, weekly, monthly

    # Values at time of alert
    limit_usd: float = 0.0
    usage_usd: float = 0.0
    usage_percent: float = 0.0

    # Status
    created_at: datetime = field(default_factory=datetime.utcnow)
    acknowledged: bool = False
    acknowledged_by: Optional[UUID] = None
    acknowledged_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "budget_id": str(self.budget_id),
            "agent_id": str(self.agent_id) if self.agent_id else None,
            "alert_type": self.alert_type,
            "threshold_percent": self.threshold_percent,
            "period": self.period,
            "limit_usd": self.limit_usd,
            "usage_usd": self.usage_usd,
            "usage_percent": self.usage_percent,
            "created_at": self.created_at.isoformat(),
            "acknowledged": self.acknowledged,
        }


@dataclass
class BudgetCheck:
    """Result of a budget check."""
    allowed: bool = True
    reason: Optional[str] = None

    # Budget state
    remaining_daily_usd: float = 0.0
    remaining_weekly_usd: float = 0.0
    remaining_monthly_usd: float = 0.0

    # Warnings
    warnings: List[str] = field(default_factory=list)

    # Actions
    action: str = "allow"  # allow, warn, block


class BudgetEnforcer:
    """
    Budget Enforcer.

    Enforces budget limits for agent execution:
    - Track spending per agent/tenant
    - Block/warn on budget limits
    - Generate budget alerts
    - Support per-action and per-run limits
    """

    def __init__(self):
        """Initialize the budget enforcer."""
        # Budget storage
        self._budgets: Dict[UUID, Budget] = {}
        self._by_agent: Dict[UUID, UUID] = {}
        self._by_tenant: Dict[UUID, UUID] = {}

        # Alerts
        self._alerts: List[BudgetAlert] = []
        self._sent_alerts: set = set()  # (budget_id, alert_type) to prevent duplicates

        # Run tracking
        self._run_costs: Dict[UUID, float] = {}  # run_id -> cost

        # Callbacks
        self._on_alert: List[Callable[[BudgetAlert], None]] = []
        self._on_limit_reached: List[Callable[[Budget, str], None]] = []

        # Default budget
        self._default_budget = Budget()

    def set_budget(self, budget: Budget) -> Budget:
        """
        Set budget for an agent or tenant.

        Args:
            budget: Budget to set

        Returns:
            Set budget
        """
        # Reset usage periods if needed
        self._reset_periods_if_needed(budget)

        self._budgets[budget.id] = budget

        if budget.agent_id:
            self._by_agent[budget.agent_id] = budget.id
        if budget.tenant_id and not budget.agent_id:
            self._by_tenant[budget.tenant_id] = budget.id

        logger.info(
            f"Budget set: ${budget.daily_limit_usd}/day for "
            f"agent={budget.agent_id} tenant={budget.tenant_id}"
        )
        return budget

    def get_budget(
        self,
        agent_id: Optional[UUID] = None,
        tenant_id: Optional[UUID] = None,
    ) -> Budget:
        """
        Get applicable budget for an agent.

        Args:
            agent_id: Agent ID
            tenant_id: Tenant ID

        Returns:
            Applicable budget
        """
        # Check agent-specific budget first
        if agent_id and agent_id in self._by_agent:
            budget_id = self._by_agent[agent_id]
            budget = self._budgets.get(budget_id)
            if budget and budget.active:
                self._reset_periods_if_needed(budget)
                return budget

        # Check tenant-level budget
        if tenant_id and tenant_id in self._by_tenant:
            budget_id = self._by_tenant[tenant_id]
            budget = self._budgets.get(budget_id)
            if budget and budget.active:
                self._reset_periods_if_needed(budget)
                return budget

        return self._default_budget

    def check_budget(
        self,
        agent_id: UUID,
        estimated_cost_usd: float,
        tenant_id: Optional[UUID] = None,
        run_id: Optional[UUID] = None,
    ) -> BudgetCheck:
        """
        Check if an action is within budget.

        Args:
            agent_id: Agent ID
            estimated_cost_usd: Estimated cost
            tenant_id: Tenant ID
            run_id: Run ID

        Returns:
            Budget check result
        """
        budget = self.get_budget(agent_id, tenant_id)
        check = BudgetCheck(
            remaining_daily_usd=budget.daily_remaining(),
            remaining_weekly_usd=budget.weekly_remaining(),
            remaining_monthly_usd=budget.monthly_remaining(),
        )

        # Check per-action limit
        if estimated_cost_usd > budget.per_action_limit_usd:
            check.allowed = budget.action_on_limit != "block"
            check.action = budget.action_on_limit
            check.reason = f"Cost ${estimated_cost_usd} exceeds per-action limit ${budget.per_action_limit_usd}"
            check.warnings.append(check.reason)

        # Check per-run limit
        if run_id:
            run_cost = self._run_costs.get(run_id, 0.0)
            if run_cost + estimated_cost_usd > budget.per_run_limit_usd:
                check.allowed = budget.action_on_limit != "block"
                check.action = budget.action_on_limit
                check.reason = f"Run cost would exceed limit ${budget.per_run_limit_usd}"
                check.warnings.append(check.reason)

        # Check daily limit
        if budget.daily_usage_usd + estimated_cost_usd > budget.daily_limit_usd:
            check.allowed = budget.action_on_limit != "block"
            check.action = budget.action_on_limit
            check.reason = f"Would exceed daily limit ${budget.daily_limit_usd}"

            if check.action == "block":
                self._notify_limit_reached(budget, "daily")

        # Check weekly limit
        if budget.weekly_usage_usd + estimated_cost_usd > budget.weekly_limit_usd:
            check.allowed = budget.action_on_limit != "block"
            check.action = budget.action_on_limit
            check.reason = f"Would exceed weekly limit ${budget.weekly_limit_usd}"
            check.warnings.append(check.reason)

        # Check monthly limit
        if budget.monthly_usage_usd + estimated_cost_usd > budget.monthly_limit_usd:
            check.allowed = budget.action_on_limit != "block"
            check.action = budget.action_on_limit
            check.reason = f"Would exceed monthly limit ${budget.monthly_limit_usd}"
            check.warnings.append(check.reason)

        return check

    def record_cost(
        self,
        agent_id: UUID,
        cost_usd: float,
        tenant_id: Optional[UUID] = None,
        run_id: Optional[UUID] = None,
    ) -> Budget:
        """
        Record a cost against the budget.

        Args:
            agent_id: Agent ID
            cost_usd: Cost to record
            tenant_id: Tenant ID
            run_id: Run ID

        Returns:
            Updated budget
        """
        budget = self.get_budget(agent_id, tenant_id)

        # Update usage
        budget.daily_usage_usd += cost_usd
        budget.weekly_usage_usd += cost_usd
        budget.monthly_usage_usd += cost_usd
        budget.updated_at = datetime.utcnow()

        # Track run cost
        if run_id:
            self._run_costs[run_id] = self._run_costs.get(run_id, 0.0) + cost_usd

        # Check and send alerts
        self._check_alerts(budget)

        return budget

    def get_usage_summary(
        self,
        agent_id: Optional[UUID] = None,
        tenant_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Get usage summary for an agent or tenant."""
        budget = self.get_budget(agent_id, tenant_id)

        return {
            "daily": {
                "usage_usd": budget.daily_usage_usd,
                "limit_usd": budget.daily_limit_usd,
                "remaining_usd": budget.daily_remaining(),
                "usage_percent": budget.daily_usage_percent(),
            },
            "weekly": {
                "usage_usd": budget.weekly_usage_usd,
                "limit_usd": budget.weekly_limit_usd,
                "remaining_usd": budget.weekly_remaining(),
            },
            "monthly": {
                "usage_usd": budget.monthly_usage_usd,
                "limit_usd": budget.monthly_limit_usd,
                "remaining_usd": budget.monthly_remaining(),
            },
        }

    def get_alerts(
        self,
        agent_id: Optional[UUID] = None,
        tenant_id: Optional[UUID] = None,
        unacknowledged_only: bool = False,
        limit: int = 100,
    ) -> List[BudgetAlert]:
        """Get budget alerts."""
        alerts = self._alerts.copy()

        if agent_id:
            alerts = [a for a in alerts if a.agent_id == agent_id]
        if tenant_id:
            alerts = [a for a in alerts if a.tenant_id == tenant_id]
        if unacknowledged_only:
            alerts = [a for a in alerts if not a.acknowledged]

        # Most recent first
        alerts.sort(key=lambda a: a.created_at, reverse=True)
        return alerts[:limit]

    def acknowledge_alert(
        self,
        alert_id: UUID,
        acknowledged_by: UUID,
    ) -> Optional[BudgetAlert]:
        """Acknowledge a budget alert."""
        for alert in self._alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                alert.acknowledged_by = acknowledged_by
                alert.acknowledged_at = datetime.utcnow()
                return alert
        return None

    def reset_usage(
        self,
        agent_id: Optional[UUID] = None,
        tenant_id: Optional[UUID] = None,
        period: str = "all",  # daily, weekly, monthly, all
    ) -> Budget:
        """Reset usage counters for a budget."""
        budget = self.get_budget(agent_id, tenant_id)

        if period in ["daily", "all"]:
            budget.daily_usage_usd = 0.0
            budget.last_reset_daily = datetime.utcnow()
        if period in ["weekly", "all"]:
            budget.weekly_usage_usd = 0.0
            budget.last_reset_weekly = datetime.utcnow()
        if period in ["monthly", "all"]:
            budget.monthly_usage_usd = 0.0
            budget.last_reset_monthly = datetime.utcnow()

        budget.updated_at = datetime.utcnow()

        # Clear sent alerts
        self._sent_alerts = {
            (bid, atype) for bid, atype in self._sent_alerts
            if bid != budget.id
        }

        return budget

    def get_stats(self) -> Dict[str, Any]:
        """Get budget enforcement statistics."""
        total_daily = sum(b.daily_usage_usd for b in self._budgets.values())
        total_alerts = len(self._alerts)
        unack_alerts = sum(1 for a in self._alerts if not a.acknowledged)

        return {
            "total_budgets": len(self._budgets),
            "total_daily_usage_usd": total_daily,
            "total_alerts": total_alerts,
            "unacknowledged_alerts": unack_alerts,
            "agents_with_budgets": len(self._by_agent),
            "tenants_with_budgets": len(self._by_tenant),
        }

    # Event registration
    def on_alert(self, callback: Callable[[BudgetAlert], None]) -> None:
        """Register callback for budget alerts."""
        self._on_alert.append(callback)

    def on_limit_reached(self, callback: Callable[[Budget, str], None]) -> None:
        """Register callback for limit reached events."""
        self._on_limit_reached.append(callback)

    # Private methods

    def _reset_periods_if_needed(self, budget: Budget) -> None:
        """Reset usage periods if time has elapsed."""
        now = datetime.utcnow()

        # Daily reset (midnight)
        if now.date() > budget.last_reset_daily.date():
            budget.daily_usage_usd = 0.0
            budget.last_reset_daily = now
            # Clear daily alerts
            self._sent_alerts = {
                (bid, atype) for bid, atype in self._sent_alerts
                if bid != budget.id or not atype.startswith("daily_")
            }

        # Weekly reset (Monday)
        days_since_weekly = (now - budget.last_reset_weekly).days
        if days_since_weekly >= 7:
            budget.weekly_usage_usd = 0.0
            budget.last_reset_weekly = now

        # Monthly reset (1st of month)
        if now.month != budget.last_reset_monthly.month:
            budget.monthly_usage_usd = 0.0
            budget.last_reset_monthly = now

    def _check_alerts(self, budget: Budget) -> None:
        """Check and generate alerts for a budget."""
        thresholds = [
            (50, budget.alert_threshold_50),
            (75, budget.alert_threshold_75),
            (90, budget.alert_threshold_90),
            (100, budget.alert_threshold_100),
        ]

        usage_percent = budget.daily_usage_percent()

        for threshold, enabled in thresholds:
            if not enabled:
                continue

            alert_key = (budget.id, f"daily_{threshold}")
            if usage_percent >= threshold and alert_key not in self._sent_alerts:
                self._create_alert(budget, "daily", threshold, usage_percent)
                self._sent_alerts.add(alert_key)

    def _create_alert(
        self,
        budget: Budget,
        period: str,
        threshold: int,
        usage_percent: float,
    ) -> BudgetAlert:
        """Create a budget alert."""
        alert = BudgetAlert(
            budget_id=budget.id,
            agent_id=budget.agent_id,
            tenant_id=budget.tenant_id,
            alert_type=f"{period}_{threshold}",
            threshold_percent=threshold,
            period=period,
            limit_usd=budget.daily_limit_usd,
            usage_usd=budget.daily_usage_usd,
            usage_percent=usage_percent,
        )

        self._alerts.append(alert)

        # Notify callbacks
        for callback in self._on_alert:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Budget alert callback error: {e}")

        logger.info(
            f"Budget alert: {alert.alert_type} for "
            f"agent={budget.agent_id} tenant={budget.tenant_id}"
        )
        return alert

    def _notify_limit_reached(self, budget: Budget, period: str) -> None:
        """Notify callbacks that budget limit was reached."""
        for callback in self._on_limit_reached:
            try:
                callback(budget, period)
            except Exception as e:
                logger.error(f"Limit reached callback error: {e}")


# Global budget enforcer
_budget_enforcer: Optional[BudgetEnforcer] = None


def get_budget_enforcer() -> BudgetEnforcer:
    """Get the global budget enforcer instance."""
    global _budget_enforcer
    if _budget_enforcer is None:
        _budget_enforcer = BudgetEnforcer()
    return _budget_enforcer
