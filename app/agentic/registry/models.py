"""
Agent Registry Models

Core data structures for agent inventory and metadata.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


class TrustTier(str, Enum):
    """Trust tier classification for agents."""
    NATIVE = "native"  # Built-in platform agents
    VERIFIED = "verified"  # Verified third-party agents
    CUSTOMER = "customer"  # Customer-developed agents
    THIRD_PARTY = "third_party"  # Unverified external agents
    SANDBOX = "sandbox"  # Testing/development agents


class AgentDomain(str, Enum):
    """Domain classification for agents."""
    DATA = "data"  # Data processing agents
    INTEGRATION = "integration"  # Integration/connector agents
    ANALYSIS = "analysis"  # Analytics agents
    AUTOMATION = "automation"  # Workflow automation agents
    SECURITY = "security"  # Security/governance agents
    INFRASTRUCTURE = "infrastructure"  # Infrastructure management agents
    CUSTOM = "custom"  # Custom domain agents


class AgentStatus(str, Enum):
    """Agent operational status."""
    ACTIVE = "active"  # Fully operational
    INACTIVE = "inactive"  # Temporarily disabled
    DEPRECATED = "deprecated"  # Scheduled for removal
    PENDING = "pending"  # Awaiting activation
    SUSPENDED = "suspended"  # Suspended due to policy violation
    ZOMBIE = "zombie"  # Detected as inactive/orphaned


@dataclass
class AgentOwnership:
    """Ownership information for an agent."""
    owner_id: UUID
    owner_type: str  # "user", "team", "organization"
    owner_name: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    transferred_at: Optional[datetime] = None
    previous_owner_id: Optional[UUID] = None


@dataclass
class AgentMetadata:
    """Extended metadata for an agent."""
    # Classification
    domain: AgentDomain = AgentDomain.CUSTOM
    trust_tier: TrustTier = TrustTier.CUSTOMER
    tags: List[str] = field(default_factory=list)

    # Versioning
    version: str = "1.0.0"
    version_history: List[Dict[str, Any]] = field(default_factory=list)

    # Documentation
    description: str = ""
    documentation_url: Optional[str] = None
    support_contact: Optional[str] = None

    # Configuration
    config_schema: Dict[str, Any] = field(default_factory=dict)
    default_config: Dict[str, Any] = field(default_factory=dict)

    # Capabilities
    declared_capabilities: List[str] = field(default_factory=list)
    observed_capabilities: List[str] = field(default_factory=list)

    # Resource limits
    max_concurrent_runs: int = 10
    max_tokens_per_run: int = 100000
    max_cost_per_run_usd: float = 10.0

    # Audit
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None


@dataclass
class AgentRecord:
    """
    Complete agent record in the registry.

    Combines identity, ownership, metadata, and runtime state.
    """
    # Identity
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    agent_type: str = "custom"
    tenant_id: Optional[UUID] = None

    # Ownership
    ownership: AgentOwnership = field(default_factory=lambda: AgentOwnership(
        owner_id=uuid4(),
        owner_type="user",
        owner_name="unknown"
    ))

    # Metadata
    metadata: AgentMetadata = field(default_factory=AgentMetadata)

    # Status
    status: AgentStatus = AgentStatus.PENDING
    status_reason: Optional[str] = None
    status_updated_at: datetime = field(default_factory=datetime.utcnow)

    # Runtime state
    last_active_at: Optional[datetime] = None
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    total_cost_usd: float = 0.0

    # Certification
    certification_id: Optional[str] = None
    certification_expires_at: Optional[datetime] = None

    # Health
    health_status: str = "unknown"
    health_check_url: Optional[str] = None
    last_health_check_at: Optional[datetime] = None

    def is_healthy(self) -> bool:
        """Check if agent is in a healthy state."""
        return self.status == AgentStatus.ACTIVE and self.health_status == "healthy"

    def is_certified(self) -> bool:
        """Check if agent has valid certification."""
        if not self.certification_id or not self.certification_expires_at:
            return False
        return self.certification_expires_at > datetime.utcnow()

    def success_rate(self) -> float:
        """Calculate run success rate."""
        if self.total_runs == 0:
            return 0.0
        return self.successful_runs / self.total_runs

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": str(self.id),
            "name": self.name,
            "agent_type": self.agent_type,
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "status": self.status.value,
            "status_reason": self.status_reason,
            "health_status": self.health_status,
            "metadata": {
                "domain": self.metadata.domain.value,
                "trust_tier": self.metadata.trust_tier.value,
                "version": self.metadata.version,
                "tags": self.metadata.tags,
                "description": self.metadata.description,
            },
            "ownership": {
                "owner_id": str(self.ownership.owner_id),
                "owner_type": self.ownership.owner_type,
                "owner_name": self.ownership.owner_name,
            },
            "stats": {
                "total_runs": self.total_runs,
                "successful_runs": self.successful_runs,
                "failed_runs": self.failed_runs,
                "success_rate": self.success_rate(),
                "total_cost_usd": self.total_cost_usd,
            },
            "certification": {
                "id": self.certification_id,
                "expires_at": self.certification_expires_at.isoformat() if self.certification_expires_at else None,
                "is_valid": self.is_certified(),
            },
            "last_active_at": self.last_active_at.isoformat() if self.last_active_at else None,
        }
