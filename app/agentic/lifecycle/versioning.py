"""
Agent Version Manager

Manages agent versioning, upgrades, and rollbacks.
Implements Agent Lifecycle: Agent version management from RACI.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from .models import AgentVersion, VersionStatus

logger = logging.getLogger(__name__)


@dataclass
class VersionTransition:
    """Record of a version transition."""
    id: UUID = field(default_factory=uuid4)
    agent_id: UUID = field(default_factory=uuid4)

    from_version: str = ""
    to_version: str = ""
    from_version_id: Optional[UUID] = None
    to_version_id: Optional[UUID] = None

    transition_type: str = "upgrade"  # upgrade, downgrade, rollback
    status: str = "completed"  # pending, in_progress, completed, failed, rolled_back

    # Timing
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    # Audit
    initiated_by: Optional[UUID] = None
    reason: Optional[str] = None
    error: Optional[str] = None

    # Rollback info
    can_rollback: bool = True
    rolled_back_at: Optional[datetime] = None
    rolled_back_by: Optional[UUID] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "agent_id": str(self.agent_id),
            "from_version": self.from_version,
            "to_version": self.to_version,
            "transition_type": self.transition_type,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "initiated_by": str(self.initiated_by) if self.initiated_by else None,
            "reason": self.reason,
            "error": self.error,
            "can_rollback": self.can_rollback,
        }


class VersionManager:
    """
    Agent Version Manager.

    Manages agent versions:
    - Register and track versions
    - Handle version transitions
    - Support rollbacks
    - Maintain version history
    """

    def __init__(self):
        """Initialize the version manager."""
        # Version registry
        self._versions: Dict[UUID, AgentVersion] = {}
        self._by_agent: Dict[UUID, List[UUID]] = {}
        self._active_versions: Dict[UUID, UUID] = {}  # agent_id -> version_id

        # Transition history
        self._transitions: Dict[UUID, VersionTransition] = {}
        self._transitions_by_agent: Dict[UUID, List[UUID]] = {}

        # Callbacks
        self._on_version_created: List[Callable[[AgentVersion], None]] = []
        self._on_transition: List[Callable[[VersionTransition], None]] = []
        self._on_rollback: List[Callable[[VersionTransition], None]] = []

    def register_version(self, version: AgentVersion) -> AgentVersion:
        """
        Register a new version for an agent.

        Args:
            version: Version to register

        Returns:
            Registered version
        """
        # Parse version string
        major, minor, patch, prerelease = AgentVersion.parse_version(version.version)
        version.semver_major = major
        version.semver_minor = minor
        version.semver_patch = patch
        version.prerelease = prerelease

        # Store version
        self._versions[version.id] = version

        if version.agent_id not in self._by_agent:
            self._by_agent[version.agent_id] = []
        self._by_agent[version.agent_id].append(version.id)

        logger.info(f"Version registered: {version.version} for agent {version.agent_id}")

        # Notify callbacks
        for callback in self._on_version_created:
            try:
                callback(version)
            except Exception as e:
                logger.error(f"Version created callback error: {e}")

        return version

    def get_version(self, version_id: UUID) -> Optional[AgentVersion]:
        """Get a version by ID."""
        return self._versions.get(version_id)

    def get_agent_versions(
        self,
        agent_id: UUID,
        include_retired: bool = False,
    ) -> List[AgentVersion]:
        """Get all versions for an agent."""
        version_ids = self._by_agent.get(agent_id, [])
        versions = [self._versions[vid] for vid in version_ids if vid in self._versions]

        if not include_retired:
            versions = [v for v in versions if v.status != VersionStatus.RETIRED]

        # Sort by version (newest first)
        versions.sort(
            key=lambda v: (v.semver_major, v.semver_minor, v.semver_patch),
            reverse=True,
        )
        return versions

    def get_active_version(self, agent_id: UUID) -> Optional[AgentVersion]:
        """Get the currently active version for an agent."""
        version_id = self._active_versions.get(agent_id)
        if version_id:
            return self._versions.get(version_id)
        return None

    def get_latest_version(self, agent_id: UUID) -> Optional[AgentVersion]:
        """Get the latest (highest) version for an agent."""
        versions = self.get_agent_versions(agent_id)
        return versions[0] if versions else None

    def find_version(self, agent_id: UUID, version_str: str) -> Optional[AgentVersion]:
        """Find a specific version by version string."""
        versions = self.get_agent_versions(agent_id, include_retired=True)
        for v in versions:
            if v.version == version_str:
                return v
        return None

    def activate(
        self,
        version_id: UUID,
        initiated_by: Optional[UUID] = None,
        reason: Optional[str] = None,
    ) -> Tuple[AgentVersion, Optional[VersionTransition]]:
        """
        Activate a version (deploy it).

        Args:
            version_id: Version to activate
            initiated_by: User initiating activation
            reason: Reason for activation

        Returns:
            Tuple of (activated version, transition record)
        """
        version = self._versions.get(version_id)
        if not version:
            raise ValueError(f"Version not found: {version_id}")

        if not version.is_deployable():
            raise ValueError(f"Version not deployable: {version.status.value}")

        # Get current active version
        current_version = self.get_active_version(version.agent_id)

        # Create transition record
        transition = None
        if current_version and current_version.id != version_id:
            transition_type = self._determine_transition_type(
                current_version.version,
                version.version,
            )

            transition = VersionTransition(
                agent_id=version.agent_id,
                from_version=current_version.version,
                to_version=version.version,
                from_version_id=current_version.id,
                to_version_id=version.id,
                transition_type=transition_type,
                status="completed",
                initiated_by=initiated_by,
                reason=reason,
                completed_at=datetime.utcnow(),
            )

            # Store transition
            self._transitions[transition.id] = transition
            if version.agent_id not in self._transitions_by_agent:
                self._transitions_by_agent[version.agent_id] = []
            self._transitions_by_agent[version.agent_id].append(transition.id)

            # Deactivate old version
            current_version.status = VersionStatus.DEPRECATED
            current_version.deprecated_at = datetime.utcnow()

        # Activate new version
        version.status = VersionStatus.ACTIVE
        version.published_at = datetime.utcnow()
        self._active_versions[version.agent_id] = version_id

        logger.info(f"Version activated: {version.version} for agent {version.agent_id}")

        # Notify callbacks
        if transition:
            for callback in self._on_transition:
                try:
                    callback(transition)
                except Exception as e:
                    logger.error(f"Transition callback error: {e}")

        return version, transition

    def rollback(
        self,
        agent_id: UUID,
        to_version: Optional[str] = None,
        initiated_by: Optional[UUID] = None,
        reason: Optional[str] = None,
    ) -> VersionTransition:
        """
        Rollback to a previous version.

        Args:
            agent_id: Agent to rollback
            to_version: Specific version to rollback to (default: previous)
            initiated_by: User initiating rollback
            reason: Reason for rollback

        Returns:
            Rollback transition record
        """
        current_version = self.get_active_version(agent_id)
        if not current_version:
            raise ValueError(f"No active version for agent: {agent_id}")

        # Find target version
        target = None
        if to_version:
            target = self.find_version(agent_id, to_version)
        else:
            # Get previous version from transition history
            transitions = self.get_transition_history(agent_id, limit=1)
            if transitions and transitions[0].from_version_id:
                target = self._versions.get(transitions[0].from_version_id)

        if not target:
            raise ValueError("No valid rollback target found")

        # Create rollback transition
        transition = VersionTransition(
            agent_id=agent_id,
            from_version=current_version.version,
            to_version=target.version,
            from_version_id=current_version.id,
            to_version_id=target.id,
            transition_type="rollback",
            status="completed",
            initiated_by=initiated_by,
            reason=reason,
            completed_at=datetime.utcnow(),
            can_rollback=False,  # Can't rollback a rollback
        )

        # Store transition
        self._transitions[transition.id] = transition
        if agent_id not in self._transitions_by_agent:
            self._transitions_by_agent[agent_id] = []
        self._transitions_by_agent[agent_id].append(transition.id)

        # Deactivate current version
        current_version.status = VersionStatus.DEPRECATED

        # Activate target version
        target.status = VersionStatus.ACTIVE
        self._active_versions[agent_id] = target.id

        logger.info(f"Rolled back agent {agent_id}: {current_version.version} -> {target.version}")

        # Notify callbacks
        for callback in self._on_rollback:
            try:
                callback(transition)
            except Exception as e:
                logger.error(f"Rollback callback error: {e}")

        return transition

    def deprecate(
        self,
        version_id: UUID,
        reason: Optional[str] = None,
    ) -> AgentVersion:
        """
        Deprecate a version.

        Args:
            version_id: Version to deprecate
            reason: Deprecation reason

        Returns:
            Deprecated version
        """
        version = self._versions.get(version_id)
        if not version:
            raise ValueError(f"Version not found: {version_id}")

        version.status = VersionStatus.DEPRECATED
        version.deprecated_at = datetime.utcnow()
        version.status_reason = reason

        logger.info(f"Version deprecated: {version.version}")
        return version

    def retire(self, version_id: UUID) -> AgentVersion:
        """
        Retire a version (permanently remove from availability).

        Args:
            version_id: Version to retire

        Returns:
            Retired version
        """
        version = self._versions.get(version_id)
        if not version:
            raise ValueError(f"Version not found: {version_id}")

        if version.status == VersionStatus.ACTIVE:
            raise ValueError("Cannot retire active version")

        version.status = VersionStatus.RETIRED
        version.retired_at = datetime.utcnow()

        logger.info(f"Version retired: {version.version}")
        return version

    def get_transition_history(
        self,
        agent_id: UUID,
        limit: int = 50,
    ) -> List[VersionTransition]:
        """Get version transition history for an agent."""
        transition_ids = self._transitions_by_agent.get(agent_id, [])
        transitions = [
            self._transitions[tid]
            for tid in transition_ids
            if tid in self._transitions
        ]

        # Sort by date descending
        transitions.sort(key=lambda t: t.started_at, reverse=True)
        return transitions[:limit]

    def compare_versions(self, v1: str, v2: str) -> int:
        """
        Compare two version strings.

        Returns:
            -1 if v1 < v2, 0 if equal, 1 if v1 > v2
        """
        major1, minor1, patch1, pre1 = AgentVersion.parse_version(v1)
        major2, minor2, patch2, pre2 = AgentVersion.parse_version(v2)

        # Compare major.minor.patch
        if (major1, minor1, patch1) < (major2, minor2, patch2):
            return -1
        if (major1, minor1, patch1) > (major2, minor2, patch2):
            return 1

        # Same version, check prerelease
        if pre1 is None and pre2 is None:
            return 0
        if pre1 is None:
            return 1  # Release > prerelease
        if pre2 is None:
            return -1
        if pre1 < pre2:
            return -1
        if pre1 > pre2:
            return 1
        return 0

    def _determine_transition_type(self, from_version: str, to_version: str) -> str:
        """Determine the type of version transition."""
        comparison = self.compare_versions(from_version, to_version)
        if comparison < 0:
            return "upgrade"
        elif comparison > 0:
            return "downgrade"
        else:
            return "redeploy"

    # Event registration
    def on_version_created(self, callback: Callable[[AgentVersion], None]) -> None:
        """Register callback for version creation."""
        self._on_version_created.append(callback)

    def on_transition(self, callback: Callable[[VersionTransition], None]) -> None:
        """Register callback for version transitions."""
        self._on_transition.append(callback)

    def on_rollback(self, callback: Callable[[VersionTransition], None]) -> None:
        """Register callback for rollbacks."""
        self._on_rollback.append(callback)


# Global instance
_version_manager: Optional[VersionManager] = None


def get_version_manager() -> VersionManager:
    """Get the global version manager instance."""
    global _version_manager
    if _version_manager is None:
        _version_manager = VersionManager()
    return _version_manager
