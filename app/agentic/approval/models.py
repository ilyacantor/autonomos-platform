"""
Approval Workflow Models

Data structures for human-in-the-loop approvals.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


class ApprovalStatus(str, Enum):
    """Status of an approval request."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    ESCALATED = "escalated"
    CANCELLED = "cancelled"
    AUTO_APPROVED = "auto_approved"


class ApprovalPriority(str, Enum):
    """Priority level for approval requests."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalType(str, Enum):
    """Type of approval request."""
    TOOL_EXECUTION = "tool_execution"
    DATA_ACCESS = "data_access"
    RESOURCE_ALLOCATION = "resource_allocation"
    POLICY_OVERRIDE = "policy_override"
    AGENT_ACTION = "agent_action"
    CONFIGURATION_CHANGE = "configuration_change"
    DEPLOYMENT = "deployment"
    ESCALATION = "escalation"


class EscalationLevel(str, Enum):
    """Escalation level."""
    NONE = "none"
    TEAM_LEAD = "team_lead"
    MANAGER = "manager"
    DIRECTOR = "director"
    EXECUTIVE = "executive"
    EMERGENCY = "emergency"


@dataclass
class ApprovalDecision:
    """Record of an approval decision."""
    id: UUID = field(default_factory=uuid4)
    request_id: UUID = field(default_factory=uuid4)

    # Decision
    decision: ApprovalStatus = ApprovalStatus.PENDING
    decided_by: Optional[UUID] = None
    decided_at: Optional[datetime] = None

    # Context
    reason: Optional[str] = None
    conditions: List[str] = field(default_factory=list)
    notes: Optional[str] = None

    # Metadata
    auto_decision: bool = False
    decision_time_seconds: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "request_id": str(self.request_id),
            "decision": self.decision.value,
            "decided_by": str(self.decided_by) if self.decided_by else None,
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
            "reason": self.reason,
            "conditions": self.conditions,
            "notes": self.notes,
            "auto_decision": self.auto_decision,
        }


@dataclass
class ApprovalRequest:
    """Request for human approval."""
    id: UUID = field(default_factory=uuid4)

    # Context
    agent_id: UUID = field(default_factory=uuid4)
    run_id: Optional[UUID] = None
    tenant_id: Optional[UUID] = None

    # Request details
    request_type: ApprovalType = ApprovalType.AGENT_ACTION
    priority: ApprovalPriority = ApprovalPriority.MEDIUM
    title: str = ""
    description: str = ""

    # Action details
    action_type: str = ""
    action_details: Dict[str, Any] = field(default_factory=dict)
    resource_id: Optional[str] = None
    resource_type: Optional[str] = None

    # Status
    status: ApprovalStatus = ApprovalStatus.PENDING
    escalation_level: EscalationLevel = EscalationLevel.NONE

    # Routing
    assigned_to: Optional[UUID] = None
    assigned_group: Optional[str] = None
    assigned_at: Optional[datetime] = None

    # Timing
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    decided_at: Optional[datetime] = None

    # Decision
    decision: Optional[ApprovalDecision] = None

    # History
    escalation_history: List[Dict[str, Any]] = field(default_factory=list)
    assignment_history: List[Dict[str, Any]] = field(default_factory=list)

    # Risk assessment
    risk_score: float = 0.0
    risk_factors: List[str] = field(default_factory=list)
    auto_approve_eligible: bool = False

    def is_expired(self) -> bool:
        """Check if request has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def time_remaining(self) -> Optional[timedelta]:
        """Get time remaining before expiry."""
        if self.expires_at is None:
            return None
        remaining = self.expires_at - datetime.utcnow()
        return remaining if remaining.total_seconds() > 0 else timedelta(0)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "agent_id": str(self.agent_id),
            "run_id": str(self.run_id) if self.run_id else None,
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "request_type": self.request_type.value,
            "priority": self.priority.value,
            "title": self.title,
            "description": self.description,
            "action_type": self.action_type,
            "action_details": self.action_details,
            "status": self.status.value,
            "escalation_level": self.escalation_level.value,
            "assigned_to": str(self.assigned_to) if self.assigned_to else None,
            "assigned_group": self.assigned_group,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
            "risk_score": self.risk_score,
            "risk_factors": self.risk_factors,
            "decision": self.decision.to_dict() if self.decision else None,
        }


@dataclass
class Override:
    """Record of a policy override."""
    id: UUID = field(default_factory=uuid4)

    # Context
    agent_id: Optional[UUID] = None
    tenant_id: Optional[UUID] = None
    request_id: Optional[UUID] = None

    # Override details
    policy_id: str = ""
    policy_name: str = ""
    original_decision: str = ""  # What the policy would have done
    override_decision: str = ""  # What was actually done

    # Justification
    reason: str = ""
    justification: str = ""
    risk_acknowledgement: bool = False

    # Scope
    scope: str = "single"  # single, session, time_limited, permanent
    applies_to: List[str] = field(default_factory=list)  # agent_ids, action_types, etc.
    valid_until: Optional[datetime] = None
    max_uses: Optional[int] = None
    current_uses: int = 0

    # Audit
    created_by: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None

    # Status
    active: bool = True
    revoked_at: Optional[datetime] = None
    revoked_by: Optional[UUID] = None
    revoke_reason: Optional[str] = None

    def is_valid(self) -> bool:
        """Check if override is still valid."""
        if not self.active:
            return False
        if self.valid_until and datetime.utcnow() > self.valid_until:
            return False
        if self.max_uses and self.current_uses >= self.max_uses:
            return False
        return True

    def use(self) -> bool:
        """Record a use of this override. Returns True if valid."""
        if not self.is_valid():
            return False
        self.current_uses += 1
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "agent_id": str(self.agent_id) if self.agent_id else None,
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "policy_id": self.policy_id,
            "policy_name": self.policy_name,
            "original_decision": self.original_decision,
            "override_decision": self.override_decision,
            "reason": self.reason,
            "scope": self.scope,
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            "max_uses": self.max_uses,
            "current_uses": self.current_uses,
            "active": self.active,
            "is_valid": self.is_valid(),
            "created_by": str(self.created_by),
            "created_at": self.created_at.isoformat(),
        }
