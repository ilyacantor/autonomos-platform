"""
Governance Models

Data structures for policy and governance.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


class PolicyScope(str, Enum):
    """Scope of a policy."""
    GLOBAL = "global"  # Applies to all agents
    TENANT = "tenant"  # Applies to a tenant
    AGENT = "agent"  # Applies to specific agent
    CAPABILITY = "capability"  # Applies to a capability
    ACTION = "action"  # Applies to an action type


class RuleAction(str, Enum):
    """Action to take when a rule matches."""
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
    ESCALATE = "escalate"
    WARN = "warn"
    LOG = "log"
    RATE_LIMIT = "rate_limit"


class AutonomyLevel(str, Enum):
    """Level of autonomy for an agent."""
    FULL = "full"  # Can act without approval
    SUPERVISED = "supervised"  # Actions are logged
    ASSISTED = "assisted"  # Some actions require approval
    RESTRICTED = "restricted"  # Most actions require approval
    LOCKED = "locked"  # All actions require approval


class EscalationTrigger(str, Enum):
    """Triggers for HITL escalation."""
    LOW_CONFIDENCE = "low_confidence"
    HIGH_RISK = "high_risk"
    POLICY_VIOLATION = "policy_violation"
    COST_THRESHOLD = "cost_threshold"
    ERROR_RATE = "error_rate"
    MANUAL_REQUEST = "manual_request"
    UNKNOWN_ACTION = "unknown_action"


@dataclass
class PolicyRule:
    """A single rule within a policy."""
    id: str = ""
    name: str = ""
    description: str = ""

    # Matching criteria
    action_patterns: List[str] = field(default_factory=list)
    resource_patterns: List[str] = field(default_factory=list)
    agent_patterns: List[str] = field(default_factory=list)
    capability_patterns: List[str] = field(default_factory=list)

    # Conditions
    conditions: Dict[str, Any] = field(default_factory=dict)
    # e.g., {"risk_score": {"gt": 0.5}, "cost_usd": {"lt": 10}}

    # Action
    action: RuleAction = RuleAction.ALLOW
    action_config: Dict[str, Any] = field(default_factory=dict)

    # Priority (higher = evaluated first)
    priority: int = 0

    # Status
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "action_patterns": self.action_patterns,
            "resource_patterns": self.resource_patterns,
            "action": self.action.value,
            "priority": self.priority,
            "enabled": self.enabled,
        }


@dataclass
class Policy:
    """A complete policy with rules."""
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""

    # Scope
    scope: PolicyScope = PolicyScope.GLOBAL
    scope_id: Optional[UUID] = None  # Tenant/Agent ID if scoped

    # Rules
    rules: List[PolicyRule] = field(default_factory=list)

    # Defaults
    default_action: RuleAction = RuleAction.DENY

    # Metadata
    version: str = "1.0"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[UUID] = None

    # Status
    enabled: bool = True

    def get_sorted_rules(self) -> List[PolicyRule]:
        """Get rules sorted by priority (highest first)."""
        return sorted(
            [r for r in self.rules if r.enabled],
            key=lambda r: r.priority,
            reverse=True,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "scope": self.scope.value,
            "scope_id": str(self.scope_id) if self.scope_id else None,
            "rules": [r.to_dict() for r in self.rules],
            "default_action": self.default_action.value,
            "version": self.version,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class PolicyDecision:
    """Result of a policy evaluation."""
    id: UUID = field(default_factory=uuid4)

    # Decision
    allowed: bool = True
    action: RuleAction = RuleAction.ALLOW
    matched_rule: Optional[str] = None
    matched_policy: Optional[str] = None

    # Context
    agent_id: Optional[UUID] = None
    action_type: str = ""
    resource_id: Optional[str] = None

    # Details
    reason: str = ""
    conditions_met: List[str] = field(default_factory=list)
    conditions_failed: List[str] = field(default_factory=list)

    # Timing
    evaluated_at: datetime = field(default_factory=datetime.utcnow)
    evaluation_time_ms: int = 0

    # Escalation
    requires_escalation: bool = False
    escalation_trigger: Optional[EscalationTrigger] = None
    escalation_level: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "allowed": self.allowed,
            "action": self.action.value,
            "matched_rule": self.matched_rule,
            "matched_policy": self.matched_policy,
            "agent_id": str(self.agent_id) if self.agent_id else None,
            "action_type": self.action_type,
            "resource_id": self.resource_id,
            "reason": self.reason,
            "requires_escalation": self.requires_escalation,
            "escalation_trigger": self.escalation_trigger.value if self.escalation_trigger else None,
            "evaluated_at": self.evaluated_at.isoformat(),
        }
