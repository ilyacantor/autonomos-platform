"""
Autonomy Manager

Manages agent autonomy levels and bounds.
Implements Policy & Governance: Autonomy bounds enforcement from RACI.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID

from .models import AutonomyLevel, EscalationTrigger

logger = logging.getLogger(__name__)


@dataclass
class AutonomyBounds:
    """Bounds for agent autonomy."""
    id: UUID = field(default_factory=lambda: __import__('uuid').uuid4())
    agent_id: Optional[UUID] = None
    tenant_id: Optional[UUID] = None

    # Autonomy level
    level: AutonomyLevel = AutonomyLevel.SUPERVISED

    # Action limits
    allowed_actions: List[str] = field(default_factory=list)  # Patterns
    forbidden_actions: List[str] = field(default_factory=list)  # Patterns
    require_approval_actions: List[str] = field(default_factory=list)  # Patterns

    # Resource limits
    allowed_resources: List[str] = field(default_factory=list)
    forbidden_resources: List[str] = field(default_factory=list)

    # Cost limits
    max_cost_per_action_usd: float = 1.0
    max_cost_per_run_usd: float = 10.0
    max_cost_per_hour_usd: float = 100.0

    # Risk limits
    max_risk_score: float = 0.7
    require_approval_risk_threshold: float = 0.5

    # Rate limits
    max_actions_per_minute: int = 60
    max_runs_per_hour: int = 100

    # Confidence thresholds
    min_confidence_for_action: float = 0.5
    require_approval_confidence_threshold: float = 0.7

    # Escalation settings
    escalate_on_error: bool = True
    escalate_on_unknown_action: bool = True
    escalation_cooldown_seconds: int = 300

    # Status
    active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "agent_id": str(self.agent_id) if self.agent_id else None,
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "level": self.level.value,
            "limits": {
                "max_cost_per_action_usd": self.max_cost_per_action_usd,
                "max_cost_per_run_usd": self.max_cost_per_run_usd,
                "max_risk_score": self.max_risk_score,
                "max_actions_per_minute": self.max_actions_per_minute,
            },
            "thresholds": {
                "require_approval_risk": self.require_approval_risk_threshold,
                "require_approval_confidence": self.require_approval_confidence_threshold,
            },
            "active": self.active,
        }


@dataclass
class AutonomyCheck:
    """Result of an autonomy check."""
    allowed: bool = True
    requires_approval: bool = False
    requires_escalation: bool = False

    # Violation details
    violation_type: Optional[str] = None
    violation_details: Optional[str] = None

    # Escalation
    escalation_trigger: Optional[EscalationTrigger] = None
    escalation_reason: Optional[str] = None

    # Context
    autonomy_level: AutonomyLevel = AutonomyLevel.FULL
    bounds_id: Optional[UUID] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "allowed": self.allowed,
            "requires_approval": self.requires_approval,
            "requires_escalation": self.requires_escalation,
            "violation_type": self.violation_type,
            "violation_details": self.violation_details,
            "autonomy_level": self.autonomy_level.value,
        }


class AutonomyManager:
    """
    Autonomy Manager.

    Manages and enforces agent autonomy:
    - Set autonomy levels
    - Define autonomy bounds
    - Check actions against bounds
    - Trigger escalations
    """

    def __init__(self):
        """Initialize the autonomy manager."""
        # Bounds storage
        self._bounds: Dict[UUID, AutonomyBounds] = {}
        self._by_agent: Dict[UUID, UUID] = {}
        self._by_tenant: Dict[UUID, UUID] = {}

        # Default bounds
        self._default_bounds = AutonomyBounds()

        # Action tracking for rate limiting
        self._action_counts: Dict[str, List[datetime]] = {}

        # Escalation tracking
        self._last_escalation: Dict[UUID, datetime] = {}

        # Callbacks
        self._on_violation: List[Callable[[AutonomyCheck], None]] = []
        self._on_escalation: List[Callable[[UUID, EscalationTrigger, str], None]] = []

    def set_bounds(self, bounds: AutonomyBounds) -> AutonomyBounds:
        """
        Set autonomy bounds for an agent or tenant.

        Args:
            bounds: Autonomy bounds

        Returns:
            Set bounds
        """
        self._bounds[bounds.id] = bounds

        if bounds.agent_id:
            self._by_agent[bounds.agent_id] = bounds.id
        if bounds.tenant_id and not bounds.agent_id:
            self._by_tenant[bounds.tenant_id] = bounds.id

        logger.info(
            f"Autonomy bounds set: {bounds.level.value} for "
            f"agent={bounds.agent_id} tenant={bounds.tenant_id}"
        )
        return bounds

    def get_bounds(
        self,
        agent_id: Optional[UUID] = None,
        tenant_id: Optional[UUID] = None,
    ) -> AutonomyBounds:
        """
        Get applicable bounds for an agent.

        Args:
            agent_id: Agent ID
            tenant_id: Tenant ID

        Returns:
            Applicable autonomy bounds
        """
        # Check agent-specific bounds first
        if agent_id and agent_id in self._by_agent:
            bounds_id = self._by_agent[agent_id]
            bounds = self._bounds.get(bounds_id)
            if bounds and bounds.active:
                return bounds

        # Check tenant-level bounds
        if tenant_id and tenant_id in self._by_tenant:
            bounds_id = self._by_tenant[tenant_id]
            bounds = self._bounds.get(bounds_id)
            if bounds and bounds.active:
                return bounds

        return self._default_bounds

    def set_autonomy_level(
        self,
        level: AutonomyLevel,
        agent_id: Optional[UUID] = None,
        tenant_id: Optional[UUID] = None,
    ) -> AutonomyBounds:
        """
        Set autonomy level for an agent or tenant.

        Args:
            level: Autonomy level
            agent_id: Agent ID
            tenant_id: Tenant ID

        Returns:
            Updated bounds
        """
        bounds = self.get_bounds(agent_id, tenant_id)

        # Create new bounds if using defaults
        if bounds.id == self._default_bounds.id:
            bounds = AutonomyBounds(
                agent_id=agent_id,
                tenant_id=tenant_id,
            )

        bounds.level = level
        bounds.updated_at = datetime.utcnow()

        return self.set_bounds(bounds)

    def check_action(
        self,
        agent_id: UUID,
        action_type: str,
        tenant_id: Optional[UUID] = None,
        resource_id: Optional[str] = None,
        estimated_cost_usd: float = 0.0,
        risk_score: float = 0.0,
        confidence_score: float = 1.0,
    ) -> AutonomyCheck:
        """
        Check if an action is allowed by autonomy bounds.

        Args:
            agent_id: Agent performing action
            action_type: Type of action
            tenant_id: Tenant ID
            resource_id: Resource being accessed
            estimated_cost_usd: Estimated cost
            risk_score: Risk score
            confidence_score: Confidence score

        Returns:
            Autonomy check result
        """
        bounds = self.get_bounds(agent_id, tenant_id)
        check = AutonomyCheck(
            autonomy_level=bounds.level,
            bounds_id=bounds.id,
        )

        # Locked level - everything requires approval
        if bounds.level == AutonomyLevel.LOCKED:
            check.requires_approval = True
            check.requires_escalation = True
            check.escalation_trigger = EscalationTrigger.POLICY_VIOLATION
            check.escalation_reason = "Agent is in locked autonomy mode"
            return check

        # Check forbidden actions
        if self._matches_patterns(action_type, bounds.forbidden_actions):
            check.allowed = False
            check.violation_type = "forbidden_action"
            check.violation_details = f"Action {action_type} is forbidden"
            self._notify_violation(check)
            return check

        # Check forbidden resources
        if resource_id and self._matches_patterns(resource_id, bounds.forbidden_resources):
            check.allowed = False
            check.violation_type = "forbidden_resource"
            check.violation_details = f"Resource {resource_id} is forbidden"
            self._notify_violation(check)
            return check

        # Check cost limits
        if estimated_cost_usd > bounds.max_cost_per_action_usd:
            check.allowed = False
            check.requires_escalation = True
            check.violation_type = "cost_exceeded"
            check.violation_details = f"Cost ${estimated_cost_usd} exceeds limit ${bounds.max_cost_per_action_usd}"
            check.escalation_trigger = EscalationTrigger.COST_THRESHOLD
            self._notify_violation(check)
            return check

        # Check risk limits
        if risk_score > bounds.max_risk_score:
            check.allowed = False
            check.requires_escalation = True
            check.violation_type = "risk_exceeded"
            check.violation_details = f"Risk score {risk_score} exceeds limit {bounds.max_risk_score}"
            check.escalation_trigger = EscalationTrigger.HIGH_RISK
            self._notify_violation(check)
            return check

        # Check if requires approval based on risk
        if risk_score > bounds.require_approval_risk_threshold:
            check.requires_approval = True
            check.escalation_trigger = EscalationTrigger.HIGH_RISK

        # Check if requires approval based on confidence
        if confidence_score < bounds.min_confidence_for_action:
            check.allowed = False
            check.requires_escalation = True
            check.violation_type = "low_confidence"
            check.violation_details = f"Confidence {confidence_score} below minimum {bounds.min_confidence_for_action}"
            check.escalation_trigger = EscalationTrigger.LOW_CONFIDENCE
            self._notify_violation(check)
            return check

        if confidence_score < bounds.require_approval_confidence_threshold:
            check.requires_approval = True
            check.escalation_trigger = EscalationTrigger.LOW_CONFIDENCE

        # Check if action requires approval based on patterns
        if self._matches_patterns(action_type, bounds.require_approval_actions):
            check.requires_approval = True

        # Check rate limits
        if not self._check_rate_limit(agent_id, bounds):
            check.allowed = False
            check.violation_type = "rate_limit"
            check.violation_details = "Rate limit exceeded"
            self._notify_violation(check)
            return check

        # Apply autonomy level restrictions
        if bounds.level == AutonomyLevel.RESTRICTED:
            # Most actions require approval
            if not self._matches_patterns(action_type, bounds.allowed_actions):
                check.requires_approval = True

        elif bounds.level == AutonomyLevel.ASSISTED:
            # Unknown actions require approval
            if bounds.escalate_on_unknown_action:
                if not self._matches_patterns(action_type, bounds.allowed_actions):
                    check.requires_approval = True
                    check.escalation_trigger = EscalationTrigger.UNKNOWN_ACTION

        # Record action for rate limiting
        self._record_action(agent_id)

        return check

    def trigger_escalation(
        self,
        agent_id: UUID,
        trigger: EscalationTrigger,
        reason: str,
        force: bool = False,
    ) -> bool:
        """
        Trigger an escalation for an agent.

        Args:
            agent_id: Agent ID
            trigger: Escalation trigger
            reason: Escalation reason
            force: Force escalation (ignore cooldown)

        Returns:
            True if escalation was triggered
        """
        bounds = self.get_bounds(agent_id)

        # Check cooldown
        if not force and agent_id in self._last_escalation:
            cooldown = datetime.utcnow().timestamp() - self._last_escalation[agent_id].timestamp()
            if cooldown < bounds.escalation_cooldown_seconds:
                logger.debug(f"Escalation cooldown active for agent {agent_id}")
                return False

        self._last_escalation[agent_id] = datetime.utcnow()

        # Notify callbacks
        for callback in self._on_escalation:
            try:
                callback(agent_id, trigger, reason)
            except Exception as e:
                logger.error(f"Escalation callback error: {e}")

        logger.info(f"Escalation triggered for agent {agent_id}: {trigger.value} - {reason}")
        return True

    def get_stats(self) -> Dict[str, Any]:
        """Get autonomy manager statistics."""
        by_level = {}
        for bounds in self._bounds.values():
            by_level[bounds.level.value] = by_level.get(bounds.level.value, 0) + 1

        return {
            "total_bounds": len(self._bounds),
            "by_level": by_level,
            "agents_with_bounds": len(self._by_agent),
            "tenants_with_bounds": len(self._by_tenant),
        }

    # Event registration
    def on_violation(self, callback: Callable[[AutonomyCheck], None]) -> None:
        """Register callback for autonomy violations."""
        self._on_violation.append(callback)

    def on_escalation(
        self,
        callback: Callable[[UUID, EscalationTrigger, str], None],
    ) -> None:
        """Register callback for escalations."""
        self._on_escalation.append(callback)

    # Private methods

    def _matches_patterns(self, value: str, patterns: List[str]) -> bool:
        """Check if value matches any pattern."""
        import fnmatch
        return any(fnmatch.fnmatch(value, pattern) for pattern in patterns)

    def _check_rate_limit(self, agent_id: UUID, bounds: AutonomyBounds) -> bool:
        """Check if rate limit allows action."""
        key = str(agent_id)
        now = datetime.utcnow()

        if key not in self._action_counts:
            return True

        # Count actions in last minute
        cutoff = now.timestamp() - 60
        recent = [t for t in self._action_counts[key] if t.timestamp() > cutoff]
        self._action_counts[key] = recent

        return len(recent) < bounds.max_actions_per_minute

    def _record_action(self, agent_id: UUID) -> None:
        """Record an action for rate limiting."""
        key = str(agent_id)
        if key not in self._action_counts:
            self._action_counts[key] = []
        self._action_counts[key].append(datetime.utcnow())

    def _notify_violation(self, check: AutonomyCheck) -> None:
        """Notify callbacks of a violation."""
        for callback in self._on_violation:
            try:
                callback(check)
            except Exception as e:
                logger.error(f"Violation callback error: {e}")


# Global autonomy manager
_autonomy_manager: Optional[AutonomyManager] = None


def get_autonomy_manager() -> AutonomyManager:
    """Get the global autonomy manager instance."""
    global _autonomy_manager
    if _autonomy_manager is None:
        _autonomy_manager = AutonomyManager()
    return _autonomy_manager
