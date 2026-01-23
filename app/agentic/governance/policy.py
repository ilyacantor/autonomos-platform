"""
Policy Engine

Agent-level policy evaluation and enforcement.
Implements Policy & Governance: Agent-level policy evaluation from RACI.
"""

import fnmatch
import logging
import operator
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID

from .models import (
    Policy,
    PolicyRule,
    PolicyDecision,
    PolicyScope,
    RuleAction,
    EscalationTrigger,
)

logger = logging.getLogger(__name__)


@dataclass
class EvaluationContext:
    """Context for policy evaluation."""
    agent_id: Optional[UUID] = None
    tenant_id: Optional[UUID] = None
    action_type: str = ""
    resource_id: Optional[str] = None
    resource_type: Optional[str] = None
    capability: Optional[str] = None

    # Risk and cost
    risk_score: float = 0.0
    estimated_cost_usd: float = 0.0
    confidence_score: float = 1.0

    # Additional context
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class PolicyEvaluator:
    """Evaluates a single policy against a context."""

    # Condition operators
    OPERATORS = {
        "eq": operator.eq,
        "ne": operator.ne,
        "gt": operator.gt,
        "ge": operator.ge,
        "lt": operator.lt,
        "le": operator.le,
        "in": lambda v, lst: v in lst,
        "not_in": lambda v, lst: v not in lst,
        "contains": lambda v, s: s in v if isinstance(v, str) else False,
        "matches": lambda v, p: fnmatch.fnmatch(str(v), p),
    }

    def evaluate(
        self,
        policy: Policy,
        context: EvaluationContext,
    ) -> PolicyDecision:
        """
        Evaluate a policy against a context.

        Args:
            policy: Policy to evaluate
            context: Evaluation context

        Returns:
            Policy decision
        """
        start_time = datetime.utcnow()

        decision = PolicyDecision(
            agent_id=context.agent_id,
            action_type=context.action_type,
            resource_id=context.resource_id,
        )

        if not policy.enabled:
            decision.allowed = True
            decision.action = RuleAction.ALLOW
            decision.reason = "Policy disabled"
            return decision

        # Check scope
        if not self._check_scope(policy, context):
            decision.allowed = True
            decision.action = RuleAction.ALLOW
            decision.reason = "Out of scope"
            return decision

        # Evaluate rules in priority order
        for rule in policy.get_sorted_rules():
            if self._matches_rule(rule, context, decision):
                decision.matched_rule = rule.id
                decision.matched_policy = str(policy.id)
                decision.action = rule.action
                decision.allowed = rule.action in [RuleAction.ALLOW, RuleAction.WARN, RuleAction.LOG]

                if rule.action == RuleAction.REQUIRE_APPROVAL:
                    decision.requires_escalation = True
                    decision.escalation_trigger = EscalationTrigger.POLICY_VIOLATION
                elif rule.action == RuleAction.ESCALATE:
                    decision.requires_escalation = True
                    decision.escalation_trigger = EscalationTrigger.MANUAL_REQUEST

                decision.reason = f"Matched rule: {rule.name}"
                break

        # Default action if no rule matched
        if decision.matched_rule is None:
            decision.action = policy.default_action
            decision.allowed = policy.default_action == RuleAction.ALLOW
            decision.reason = f"Default action: {policy.default_action.value}"

        decision.evaluation_time_ms = int(
            (datetime.utcnow() - start_time).total_seconds() * 1000
        )

        return decision

    def _check_scope(self, policy: Policy, context: EvaluationContext) -> bool:
        """Check if policy applies to this context."""
        if policy.scope == PolicyScope.GLOBAL:
            return True
        if policy.scope == PolicyScope.TENANT and policy.scope_id:
            return context.tenant_id == policy.scope_id
        if policy.scope == PolicyScope.AGENT and policy.scope_id:
            return context.agent_id == policy.scope_id
        return True

    def _matches_rule(
        self,
        rule: PolicyRule,
        context: EvaluationContext,
        decision: PolicyDecision,
    ) -> bool:
        """Check if a rule matches the context."""
        # Check action patterns
        if rule.action_patterns:
            if not any(
                fnmatch.fnmatch(context.action_type, pattern)
                for pattern in rule.action_patterns
            ):
                return False

        # Check resource patterns
        if rule.resource_patterns and context.resource_id:
            if not any(
                fnmatch.fnmatch(context.resource_id, pattern)
                for pattern in rule.resource_patterns
            ):
                return False

        # Check agent patterns
        if rule.agent_patterns and context.agent_id:
            agent_str = str(context.agent_id)
            if not any(
                fnmatch.fnmatch(agent_str, pattern)
                for pattern in rule.agent_patterns
            ):
                return False

        # Check capability patterns
        if rule.capability_patterns and context.capability:
            if not any(
                fnmatch.fnmatch(context.capability, pattern)
                for pattern in rule.capability_patterns
            ):
                return False

        # Check conditions
        for field, condition in rule.conditions.items():
            value = self._get_context_value(context, field)
            if not self._evaluate_condition(value, condition, decision):
                return False

        return True

    def _get_context_value(self, context: EvaluationContext, field: str) -> Any:
        """Get a value from the context."""
        if hasattr(context, field):
            return getattr(context, field)
        return context.metadata.get(field)

    def _evaluate_condition(
        self,
        value: Any,
        condition: Dict[str, Any],
        decision: PolicyDecision,
    ) -> bool:
        """Evaluate a condition against a value."""
        for op_name, expected in condition.items():
            op_func = self.OPERATORS.get(op_name)
            if not op_func:
                logger.warning(f"Unknown operator: {op_name}")
                continue

            try:
                if op_func(value, expected):
                    decision.conditions_met.append(f"{op_name}({expected})")
                else:
                    decision.conditions_failed.append(f"{op_name}({expected})")
                    return False
            except Exception as e:
                logger.error(f"Condition evaluation error: {e}")
                decision.conditions_failed.append(f"{op_name}({expected}): error")
                return False

        return True


class PolicyEngine:
    """
    Policy Engine.

    Manages and evaluates policies:
    - Register policies
    - Evaluate actions against policies
    - Track decisions
    """

    def __init__(self):
        """Initialize the policy engine."""
        # Policy storage
        self._policies: Dict[UUID, Policy] = {}
        self._by_scope: Dict[PolicyScope, List[UUID]] = {s: [] for s in PolicyScope}

        # Evaluator
        self._evaluator = PolicyEvaluator()

        # Decision history
        self._decisions: List[PolicyDecision] = []
        self._max_decisions = 10000

        # Callbacks
        self._on_decision: List[Callable[[PolicyDecision], None]] = []
        self._on_deny: List[Callable[[PolicyDecision], None]] = []
        self._on_escalation: List[Callable[[PolicyDecision], None]] = []

    def register_policy(self, policy: Policy) -> Policy:
        """
        Register a policy.

        Args:
            policy: Policy to register

        Returns:
            Registered policy
        """
        self._policies[policy.id] = policy
        self._by_scope[policy.scope].append(policy.id)

        logger.info(f"Policy registered: {policy.name} ({policy.id})")
        return policy

    def unregister_policy(self, policy_id: UUID) -> Optional[Policy]:
        """Unregister a policy."""
        policy = self._policies.pop(policy_id, None)
        if policy:
            self._by_scope[policy.scope].remove(policy_id)
        return policy

    def get_policy(self, policy_id: UUID) -> Optional[Policy]:
        """Get a policy by ID."""
        return self._policies.get(policy_id)

    def evaluate(
        self,
        context: EvaluationContext,
    ) -> PolicyDecision:
        """
        Evaluate all applicable policies.

        Args:
            context: Evaluation context

        Returns:
            Final policy decision
        """
        applicable_policies = self._get_applicable_policies(context)

        # Start with permissive decision
        final_decision = PolicyDecision(
            agent_id=context.agent_id,
            action_type=context.action_type,
            resource_id=context.resource_id,
            allowed=True,
            action=RuleAction.ALLOW,
        )

        # Evaluate each policy
        for policy in applicable_policies:
            decision = self._evaluator.evaluate(policy, context)

            # Most restrictive decision wins
            if not decision.allowed and final_decision.allowed:
                final_decision = decision
            elif decision.requires_escalation and not final_decision.requires_escalation:
                final_decision.requires_escalation = True
                final_decision.escalation_trigger = decision.escalation_trigger
            elif decision.action == RuleAction.DENY:
                final_decision = decision
                break  # Deny is final

        # Store decision
        self._decisions.append(final_decision)
        if len(self._decisions) > self._max_decisions:
            self._decisions = self._decisions[-self._max_decisions:]

        # Notify callbacks
        for callback in self._on_decision:
            try:
                callback(final_decision)
            except Exception as e:
                logger.error(f"Decision callback error: {e}")

        if not final_decision.allowed:
            for callback in self._on_deny:
                try:
                    callback(final_decision)
                except Exception as e:
                    logger.error(f"Deny callback error: {e}")

        if final_decision.requires_escalation:
            for callback in self._on_escalation:
                try:
                    callback(final_decision)
                except Exception as e:
                    logger.error(f"Escalation callback error: {e}")

        return final_decision

    def check_action(
        self,
        agent_id: UUID,
        action_type: str,
        resource_id: Optional[str] = None,
        tenant_id: Optional[UUID] = None,
        risk_score: float = 0.0,
        estimated_cost_usd: float = 0.0,
        **metadata,
    ) -> PolicyDecision:
        """
        Convenience method to check if an action is allowed.

        Args:
            agent_id: Agent performing action
            action_type: Type of action
            resource_id: Resource being accessed
            tenant_id: Tenant ID
            risk_score: Risk score
            estimated_cost_usd: Estimated cost
            **metadata: Additional context

        Returns:
            Policy decision
        """
        context = EvaluationContext(
            agent_id=agent_id,
            tenant_id=tenant_id,
            action_type=action_type,
            resource_id=resource_id,
            risk_score=risk_score,
            estimated_cost_usd=estimated_cost_usd,
            metadata=metadata,
        )
        return self.evaluate(context)

    def get_decisions(
        self,
        agent_id: Optional[UUID] = None,
        action_type: Optional[str] = None,
        allowed: Optional[bool] = None,
        limit: int = 100,
    ) -> List[PolicyDecision]:
        """Get decision history with optional filters."""
        decisions = self._decisions.copy()

        if agent_id:
            decisions = [d for d in decisions if d.agent_id == agent_id]
        if action_type:
            decisions = [d for d in decisions if d.action_type == action_type]
        if allowed is not None:
            decisions = [d for d in decisions if d.allowed == allowed]

        # Most recent first
        decisions.reverse()
        return decisions[:limit]

    def get_stats(self) -> Dict[str, Any]:
        """Get policy engine statistics."""
        decisions = self._decisions

        allowed = sum(1 for d in decisions if d.allowed)
        denied = sum(1 for d in decisions if not d.allowed)
        escalated = sum(1 for d in decisions if d.requires_escalation)

        by_action = {}
        for d in decisions:
            by_action[d.action.value] = by_action.get(d.action.value, 0) + 1

        return {
            "total_policies": len(self._policies),
            "total_decisions": len(decisions),
            "allowed": allowed,
            "denied": denied,
            "escalated": escalated,
            "by_action": by_action,
        }

    # Event registration
    def on_decision(self, callback: Callable[[PolicyDecision], None]) -> None:
        """Register callback for all decisions."""
        self._on_decision.append(callback)

    def on_deny(self, callback: Callable[[PolicyDecision], None]) -> None:
        """Register callback for deny decisions."""
        self._on_deny.append(callback)

    def on_escalation(self, callback: Callable[[PolicyDecision], None]) -> None:
        """Register callback for escalation decisions."""
        self._on_escalation.append(callback)

    def _get_applicable_policies(self, context: EvaluationContext) -> List[Policy]:
        """Get policies applicable to this context."""
        policies = []

        # Global policies always apply
        for pid in self._by_scope[PolicyScope.GLOBAL]:
            policy = self._policies.get(pid)
            if policy and policy.enabled:
                policies.append(policy)

        # Tenant policies
        if context.tenant_id:
            for pid in self._by_scope[PolicyScope.TENANT]:
                policy = self._policies.get(pid)
                if policy and policy.enabled and policy.scope_id == context.tenant_id:
                    policies.append(policy)

        # Agent policies
        if context.agent_id:
            for pid in self._by_scope[PolicyScope.AGENT]:
                policy = self._policies.get(pid)
                if policy and policy.enabled and policy.scope_id == context.agent_id:
                    policies.append(policy)

        return policies


# Global policy engine
_policy_engine: Optional[PolicyEngine] = None


def get_policy_engine() -> PolicyEngine:
    """Get the global policy engine instance."""
    global _policy_engine
    if _policy_engine is None:
        _policy_engine = PolicyEngine()
    return _policy_engine
