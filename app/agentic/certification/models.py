"""
Certification Models

Data structures for agent certification system.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


class CertificationStatus(str, Enum):
    """Status of an agent's certification."""
    PENDING = "pending"           # Awaiting certification
    IN_PROGRESS = "in_progress"   # Certification checks running
    CERTIFIED = "certified"       # Passed all requirements
    CONDITIONAL = "conditional"   # Certified with conditions/limitations
    FAILED = "failed"             # Failed certification
    EXPIRED = "expired"           # Certification has expired
    REVOKED = "revoked"           # Certification manually revoked
    SUSPENDED = "suspended"       # Temporarily suspended


class CertificationType(str, Enum):
    """Type of certification process."""
    AUTOMATED = "automated"       # Fully automated checks
    MANUAL = "manual"             # Human review required
    HYBRID = "hybrid"             # Automated + manual review
    EXPEDITED = "expedited"       # Fast-track for minor changes
    EMERGENCY = "emergency"       # Emergency certification bypass


class CertificationScope(str, Enum):
    """Scope of what the certification covers."""
    FULL = "full"                 # Full agent capabilities
    LIMITED = "limited"           # Subset of capabilities
    SANDBOX = "sandbox"           # Sandbox/test environment only
    PRODUCTION = "production"     # Production environment
    INTERNAL = "internal"         # Internal use only
    EXTERNAL = "external"         # External/customer-facing


class RequirementCategory(str, Enum):
    """Categories of certification requirements."""
    SECURITY = "security"
    SAFETY = "safety"
    PERFORMANCE = "performance"
    COMPLIANCE = "compliance"
    FUNCTIONALITY = "functionality"
    RELIABILITY = "reliability"
    GOVERNANCE = "governance"


@dataclass
class CertificationRequirement:
    """A single certification requirement to be verified."""
    id: str
    name: str
    description: str
    category: RequirementCategory

    # Validation
    validator_type: str  # "automated", "manual", "hybrid"
    validator_config: Dict[str, Any] = field(default_factory=dict)

    # Thresholds
    required: bool = True
    severity: str = "critical"  # critical, high, medium, low
    pass_threshold: float = 1.0  # 0.0 to 1.0

    # Metadata
    documentation_url: Optional[str] = None
    remediation_guide: Optional[str] = None


@dataclass
class RequirementResult:
    """Result of evaluating a single requirement."""
    requirement_id: str
    passed: bool
    score: float  # 0.0 to 1.0

    # Details
    evidence: Dict[str, Any] = field(default_factory=dict)
    findings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    # Timing
    evaluated_at: datetime = field(default_factory=datetime.utcnow)
    duration_ms: int = 0

    # Error handling
    error: Optional[str] = None
    skipped: bool = False
    skip_reason: Optional[str] = None


@dataclass
class CertificationResult:
    """Complete result of a certification evaluation."""
    id: str = field(default_factory=lambda: str(uuid4()))
    agent_id: UUID = field(default_factory=uuid4)
    agent_version: int = 1

    # Status
    status: CertificationStatus = CertificationStatus.PENDING
    certification_type: CertificationType = CertificationType.AUTOMATED
    scope: CertificationScope = CertificationScope.FULL

    # Results
    requirement_results: List[RequirementResult] = field(default_factory=list)
    overall_score: float = 0.0
    passed_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0

    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: int = 0

    # Certifier
    certifier_id: Optional[UUID] = None  # User or system ID
    certifier_type: str = "system"  # "system", "user", "committee"
    certifier_notes: Optional[str] = None

    # Validity
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None

    def calculate_totals(self):
        """Calculate totals from requirement results."""
        self.passed_count = sum(1 for r in self.requirement_results if r.passed)
        self.failed_count = sum(1 for r in self.requirement_results if not r.passed and not r.skipped)
        self.skipped_count = sum(1 for r in self.requirement_results if r.skipped)

        scored = [r for r in self.requirement_results if not r.skipped]
        if scored:
            self.overall_score = sum(r.score for r in scored) / len(scored)

    def is_passed(self, pass_threshold: float = 0.8) -> bool:
        """Check if certification passed based on threshold."""
        self.calculate_totals()
        return self.failed_count == 0 and self.overall_score >= pass_threshold


@dataclass
class Certification:
    """
    A complete certification record for an agent.

    This is the published, immutable record of an agent's certification.
    """
    id: str = field(default_factory=lambda: str(uuid4()))

    # Agent identity
    agent_id: UUID = field(default_factory=uuid4)
    agent_name: str = ""
    agent_version: int = 1
    tenant_id: UUID = field(default_factory=uuid4)

    # Certification details
    status: CertificationStatus = CertificationStatus.PENDING
    certification_type: CertificationType = CertificationType.AUTOMATED
    scope: CertificationScope = CertificationScope.FULL

    # Results summary
    result_id: Optional[str] = None
    overall_score: float = 0.0
    requirements_met: int = 0
    requirements_total: int = 0

    # Validity period
    issued_at: Optional[datetime] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None

    # Certifier information
    certifier_id: Optional[UUID] = None
    certifier_type: str = "system"
    certifier_name: Optional[str] = None

    # Conditions and limitations
    conditions: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    allowed_tools: List[str] = field(default_factory=list)  # Empty = all
    denied_tools: List[str] = field(default_factory=list)

    # Audit trail
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    revoked_at: Optional[datetime] = None
    revoked_by: Optional[UUID] = None
    revocation_reason: Optional[str] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    def is_valid(self) -> bool:
        """Check if certification is currently valid."""
        now = datetime.utcnow()

        if self.status not in (CertificationStatus.CERTIFIED, CertificationStatus.CONDITIONAL):
            return False

        if self.valid_from and now < self.valid_from:
            return False

        if self.valid_until and now > self.valid_until:
            return False

        return True

    def days_until_expiry(self) -> Optional[int]:
        """Get days until certification expires."""
        if not self.valid_until:
            return None
        delta = self.valid_until - datetime.utcnow()
        return max(0, delta.days)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "agent_id": str(self.agent_id),
            "agent_name": self.agent_name,
            "agent_version": self.agent_version,
            "tenant_id": str(self.tenant_id),
            "status": self.status.value,
            "certification_type": self.certification_type.value,
            "scope": self.scope.value,
            "overall_score": self.overall_score,
            "requirements_met": self.requirements_met,
            "requirements_total": self.requirements_total,
            "issued_at": self.issued_at.isoformat() if self.issued_at else None,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            "certifier_type": self.certifier_type,
            "certifier_name": self.certifier_name,
            "conditions": self.conditions,
            "limitations": self.limitations,
            "is_valid": self.is_valid(),
            "days_until_expiry": self.days_until_expiry(),
            "tags": self.tags,
        }


# Standard certification requirements
STANDARD_REQUIREMENTS: List[CertificationRequirement] = [
    CertificationRequirement(
        id="SEC-001",
        name="Injection Protection",
        description="Agent must be protected against prompt injection attacks",
        category=RequirementCategory.SECURITY,
        validator_type="automated",
        validator_config={"test_suite": "injection_tests"},
        severity="critical",
    ),
    CertificationRequirement(
        id="SEC-002",
        name="PII Handling",
        description="Agent must properly detect and handle PII data",
        category=RequirementCategory.SECURITY,
        validator_type="automated",
        validator_config={"test_suite": "pii_tests"},
        severity="critical",
    ),
    CertificationRequirement(
        id="SEC-003",
        name="Authentication Integration",
        description="Agent must use proper authentication for all operations",
        category=RequirementCategory.SECURITY,
        validator_type="automated",
        validator_config={"check": "auth_config"},
        severity="critical",
    ),
    CertificationRequirement(
        id="SAF-001",
        name="Cost Limits",
        description="Agent must have configured cost limits",
        category=RequirementCategory.SAFETY,
        validator_type="automated",
        validator_config={"check": "cost_limits"},
        severity="high",
    ),
    CertificationRequirement(
        id="SAF-002",
        name="Step Limits",
        description="Agent must have configured step limits to prevent runaway execution",
        category=RequirementCategory.SAFETY,
        validator_type="automated",
        validator_config={"check": "step_limits"},
        severity="high",
    ),
    CertificationRequirement(
        id="SAF-003",
        name="Approval Rules",
        description="Agent must have human-in-the-loop approval rules for sensitive operations",
        category=RequirementCategory.SAFETY,
        validator_type="automated",
        validator_config={"check": "approval_rules"},
        severity="high",
    ),
    CertificationRequirement(
        id="PERF-001",
        name="Response Time",
        description="Agent must respond within acceptable time limits",
        category=RequirementCategory.PERFORMANCE,
        validator_type="automated",
        validator_config={"test_suite": "performance_tests", "max_latency_ms": 30000},
        severity="medium",
        pass_threshold=0.9,
    ),
    CertificationRequirement(
        id="PERF-002",
        name="Token Efficiency",
        description="Agent must use tokens efficiently",
        category=RequirementCategory.PERFORMANCE,
        validator_type="automated",
        validator_config={"max_tokens_per_step": 8000},
        severity="medium",
        pass_threshold=0.8,
    ),
    CertificationRequirement(
        id="REL-001",
        name="Error Handling",
        description="Agent must gracefully handle errors",
        category=RequirementCategory.RELIABILITY,
        validator_type="automated",
        validator_config={"test_suite": "error_handling_tests"},
        severity="high",
    ),
    CertificationRequirement(
        id="REL-002",
        name="Checkpoint Support",
        description="Agent must support checkpointing for recovery",
        category=RequirementCategory.RELIABILITY,
        validator_type="automated",
        validator_config={"check": "checkpoint_config"},
        severity="medium",
    ),
    CertificationRequirement(
        id="FUNC-001",
        name="Golden Dataset Pass Rate",
        description="Agent must pass evaluation against golden dataset",
        category=RequirementCategory.FUNCTIONALITY,
        validator_type="automated",
        validator_config={"min_pass_rate": 0.8},
        severity="high",
        pass_threshold=0.8,
    ),
    CertificationRequirement(
        id="GOV-001",
        name="Documentation",
        description="Agent must have complete documentation",
        category=RequirementCategory.GOVERNANCE,
        validator_type="manual",
        validator_config={"checklist": ["description", "system_prompt", "tool_docs"]},
        severity="medium",
        required=False,
    ),
    CertificationRequirement(
        id="GOV-002",
        name="Audit Trail",
        description="Agent must emit proper audit events",
        category=RequirementCategory.GOVERNANCE,
        validator_type="automated",
        validator_config={"check": "audit_config"},
        severity="high",
    ),
]
