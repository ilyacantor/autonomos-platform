"""
Agent Lifecycle Management

Complete agent lifecycle management:
- Agent health monitoring
- Agent registration and configuration
- Agent version management
- Agent onboarding and versioning
- Zombie agent detection
"""

from app.agentic.lifecycle.models import (
    HealthCheck,
    HealthStatus,
    AgentVersion,
    VersionStatus,
    AgentConfig,
    ConfigValidation,
)
from app.agentic.lifecycle.health import (
    HealthMonitor,
    HealthCheckResult,
    get_health_monitor,
)
from app.agentic.lifecycle.versioning import (
    VersionManager,
    VersionTransition,
    get_version_manager,
)
from app.agentic.lifecycle.onboarding import (
    OnboardingWorkflow,
    OnboardingStep,
    OnboardingStatus,
    get_onboarding_workflow,
)

__all__ = [
    # Models
    "HealthCheck",
    "HealthStatus",
    "AgentVersion",
    "VersionStatus",
    "AgentConfig",
    "ConfigValidation",
    # Health
    "HealthMonitor",
    "HealthCheckResult",
    "get_health_monitor",
    # Versioning
    "VersionManager",
    "VersionTransition",
    "get_version_manager",
    # Onboarding
    "OnboardingWorkflow",
    "OnboardingStep",
    "OnboardingStatus",
    "get_onboarding_workflow",
]
