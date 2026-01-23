"""
Agent Lifecycle Models

Data structures for agent lifecycle management.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


class HealthStatus(str, Enum):
    """Agent health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    STARTING = "starting"
    STOPPING = "stopping"


class VersionStatus(str, Enum):
    """Agent version status."""
    DRAFT = "draft"  # In development
    TESTING = "testing"  # Under test
    STAGED = "staged"  # Ready for deployment
    ACTIVE = "active"  # Currently deployed
    DEPRECATED = "deprecated"  # Scheduled for removal
    RETIRED = "retired"  # No longer available


@dataclass
class HealthCheck:
    """Health check configuration."""
    id: UUID = field(default_factory=uuid4)
    agent_id: UUID = field(default_factory=uuid4)

    # Check configuration
    check_type: str = "http"  # http, tcp, script, heartbeat
    endpoint: Optional[str] = None
    port: Optional[int] = None
    script: Optional[str] = None

    # Timing
    interval_seconds: int = 30
    timeout_seconds: int = 10
    retries: int = 3

    # Thresholds
    healthy_threshold: int = 2  # Consecutive successes to be healthy
    unhealthy_threshold: int = 3  # Consecutive failures to be unhealthy

    # Response validation
    expected_status_codes: List[int] = field(default_factory=lambda: [200])
    expected_body_contains: Optional[str] = None

    # State
    enabled: bool = True
    last_check_at: Optional[datetime] = None
    last_status: HealthStatus = HealthStatus.UNKNOWN
    consecutive_successes: int = 0
    consecutive_failures: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "agent_id": str(self.agent_id),
            "check_type": self.check_type,
            "endpoint": self.endpoint,
            "interval_seconds": self.interval_seconds,
            "timeout_seconds": self.timeout_seconds,
            "enabled": self.enabled,
            "last_check_at": self.last_check_at.isoformat() if self.last_check_at else None,
            "last_status": self.last_status.value,
        }


@dataclass
class AgentVersion:
    """Agent version information."""
    id: UUID = field(default_factory=uuid4)
    agent_id: UUID = field(default_factory=uuid4)

    # Version info
    version: str = "1.0.0"
    semver_major: int = 1
    semver_minor: int = 0
    semver_patch: int = 0
    prerelease: Optional[str] = None  # e.g., "beta.1", "rc.2"

    # Status
    status: VersionStatus = VersionStatus.DRAFT
    status_reason: Optional[str] = None

    # Metadata
    release_notes: str = ""
    breaking_changes: List[str] = field(default_factory=list)
    new_features: List[str] = field(default_factory=list)
    bug_fixes: List[str] = field(default_factory=list)

    # Configuration
    config_schema: Dict[str, Any] = field(default_factory=dict)
    default_config: Dict[str, Any] = field(default_factory=dict)

    # Compatibility
    min_platform_version: Optional[str] = None
    max_platform_version: Optional[str] = None
    compatible_versions: List[str] = field(default_factory=list)

    # Audit
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[UUID] = None
    published_at: Optional[datetime] = None
    deprecated_at: Optional[datetime] = None
    retired_at: Optional[datetime] = None

    def is_active(self) -> bool:
        """Check if version is currently active."""
        return self.status == VersionStatus.ACTIVE

    def is_deployable(self) -> bool:
        """Check if version can be deployed."""
        return self.status in [VersionStatus.STAGED, VersionStatus.ACTIVE]

    def is_compatible_with(self, other_version: str) -> bool:
        """Check compatibility with another version."""
        if not self.compatible_versions:
            return True  # Assume compatible if no restrictions
        return other_version in self.compatible_versions

    @classmethod
    def parse_version(cls, version_str: str) -> tuple:
        """Parse semantic version string."""
        parts = version_str.split("-", 1)
        core = parts[0]
        prerelease = parts[1] if len(parts) > 1 else None

        version_parts = core.split(".")
        major = int(version_parts[0]) if len(version_parts) > 0 else 0
        minor = int(version_parts[1]) if len(version_parts) > 1 else 0
        patch = int(version_parts[2]) if len(version_parts) > 2 else 0

        return major, minor, patch, prerelease

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "agent_id": str(self.agent_id),
            "version": self.version,
            "status": self.status.value,
            "release_notes": self.release_notes,
            "breaking_changes": self.breaking_changes,
            "new_features": self.new_features,
            "bug_fixes": self.bug_fixes,
            "created_at": self.created_at.isoformat(),
            "published_at": self.published_at.isoformat() if self.published_at else None,
        }


@dataclass
class ConfigValidation:
    """Result of configuration validation."""
    is_valid: bool = True
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    validated_at: datetime = field(default_factory=datetime.utcnow)

    def add_error(self, field: str, message: str, code: str = "validation_error"):
        """Add a validation error."""
        self.is_valid = False
        self.errors.append({
            "field": field,
            "message": message,
            "code": code,
        })

    def add_warning(self, field: str, message: str, code: str = "validation_warning"):
        """Add a validation warning."""
        self.warnings.append({
            "field": field,
            "message": message,
            "code": code,
        })


@dataclass
class AgentConfig:
    """Agent configuration."""
    id: UUID = field(default_factory=uuid4)
    agent_id: UUID = field(default_factory=uuid4)
    version_id: Optional[UUID] = None

    # Configuration data
    config: Dict[str, Any] = field(default_factory=dict)
    secrets: Dict[str, str] = field(default_factory=dict)  # Encrypted references

    # Environment
    environment: str = "production"  # production, staging, development
    region: Optional[str] = None

    # Resource limits
    max_memory_mb: int = 512
    max_cpu_cores: float = 1.0
    max_concurrent_requests: int = 10

    # Timeout settings
    request_timeout_seconds: int = 60
    idle_timeout_seconds: int = 300
    startup_timeout_seconds: int = 120

    # Feature flags
    features: Dict[str, bool] = field(default_factory=dict)

    # Audit
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None

    # Validation state
    last_validated_at: Optional[datetime] = None
    validation_result: Optional[ConfigValidation] = None

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        self.config[key] = value
        self.updated_at = datetime.utcnow()

    def has_feature(self, feature: str) -> bool:
        """Check if a feature is enabled."""
        return self.features.get(feature, False)

    def to_dict(self, include_secrets: bool = False) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "id": str(self.id),
            "agent_id": str(self.agent_id),
            "version_id": str(self.version_id) if self.version_id else None,
            "environment": self.environment,
            "config": self.config,
            "features": self.features,
            "resource_limits": {
                "max_memory_mb": self.max_memory_mb,
                "max_cpu_cores": self.max_cpu_cores,
                "max_concurrent_requests": self.max_concurrent_requests,
            },
            "timeouts": {
                "request": self.request_timeout_seconds,
                "idle": self.idle_timeout_seconds,
                "startup": self.startup_timeout_seconds,
            },
            "updated_at": self.updated_at.isoformat(),
        }

        if include_secrets:
            result["secrets"] = list(self.secrets.keys())  # Only keys, not values

        return result
