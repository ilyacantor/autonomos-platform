"""
Override Manager

Tracks and manages policy overrides.
Implements Override tracking from RACI.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID

from .models import Override

logger = logging.getLogger(__name__)


@dataclass
class OverridePolicy:
    """Policy governing when overrides are allowed."""
    id: str
    name: str
    description: str = ""

    # Scope
    applies_to_policies: List[str] = field(default_factory=list)
    applies_to_agents: Optional[List[UUID]] = None
    applies_to_tenants: Optional[List[UUID]] = None

    # Permissions
    allowed_roles: List[str] = field(default_factory=list)
    requires_approval: bool = True
    requires_justification: bool = True
    requires_risk_acknowledgement: bool = True

    # Limits
    max_duration_hours: Optional[int] = 24
    max_uses: Optional[int] = None
    cooldown_hours: Optional[int] = None

    # Audit
    require_audit_log: bool = True
    notify_on_use: bool = True

    enabled: bool = True


class OverrideManager:
    """
    Override Manager.

    Manages policy overrides:
    - Create and track overrides
    - Validate override usage
    - Maintain override history
    - Enforce override policies
    """

    def __init__(self):
        """Initialize the override manager."""
        # Override storage
        self._overrides: Dict[UUID, Override] = {}
        self._by_policy: Dict[str, List[UUID]] = {}
        self._by_agent: Dict[UUID, List[UUID]] = {}
        self._by_tenant: Dict[UUID, List[UUID]] = {}

        # Override policies
        self._policies: Dict[str, OverridePolicy] = {}

        # Usage history
        self._usage_log: List[Dict[str, Any]] = []

        # Callbacks
        self._on_override_created: List[Callable[[Override], None]] = []
        self._on_override_used: List[Callable[[Override, Dict[str, Any]], None]] = []
        self._on_override_revoked: List[Callable[[Override], None]] = []

    def add_policy(self, policy: OverridePolicy) -> None:
        """Add an override policy."""
        self._policies[policy.id] = policy
        logger.info(f"Override policy added: {policy.name}")

    def remove_policy(self, policy_id: str) -> Optional[OverridePolicy]:
        """Remove an override policy."""
        return self._policies.pop(policy_id, None)

    def create_override(
        self,
        policy_id: str,
        policy_name: str,
        original_decision: str,
        override_decision: str,
        reason: str,
        justification: str,
        created_by: UUID,
        agent_id: Optional[UUID] = None,
        tenant_id: Optional[UUID] = None,
        request_id: Optional[UUID] = None,
        scope: str = "single",
        applies_to: Optional[List[str]] = None,
        valid_duration_hours: Optional[int] = None,
        max_uses: Optional[int] = None,
        risk_acknowledgement: bool = False,
    ) -> Override:
        """
        Create a new override.

        Args:
            policy_id: Policy being overridden
            policy_name: Policy name
            original_decision: What policy would have done
            override_decision: What to do instead
            reason: Short reason
            justification: Detailed justification
            created_by: User creating override
            agent_id: Agent scope
            tenant_id: Tenant scope
            request_id: Associated approval request
            scope: Override scope (single, session, time_limited, permanent)
            applies_to: List of items this applies to
            valid_duration_hours: How long override is valid
            max_uses: Maximum uses
            risk_acknowledgement: User acknowledged risks

        Returns:
            Created override
        """
        # Check override policy
        override_policy = self._policies.get(policy_id)
        if override_policy:
            self._validate_override_policy(override_policy, risk_acknowledgement)

            # Apply policy limits
            if override_policy.max_duration_hours and valid_duration_hours:
                valid_duration_hours = min(valid_duration_hours, override_policy.max_duration_hours)
            if override_policy.max_uses and max_uses:
                max_uses = min(max_uses, override_policy.max_uses)

        # Calculate expiry
        valid_until = None
        if valid_duration_hours:
            valid_until = datetime.utcnow() + timedelta(hours=valid_duration_hours)
        elif scope == "single":
            max_uses = 1

        override = Override(
            policy_id=policy_id,
            policy_name=policy_name,
            original_decision=original_decision,
            override_decision=override_decision,
            reason=reason,
            justification=justification,
            risk_acknowledgement=risk_acknowledgement,
            created_by=created_by,
            agent_id=agent_id,
            tenant_id=tenant_id,
            request_id=request_id,
            scope=scope,
            applies_to=applies_to or [],
            valid_until=valid_until,
            max_uses=max_uses,
        )

        # Store override
        self._store_override(override)

        # Notify callbacks
        for callback in self._on_override_created:
            try:
                callback(override)
            except Exception as e:
                logger.error(f"Override created callback error: {e}")

        logger.info(f"Override created: {override.id} for policy {policy_id}")
        return override

    def use_override(
        self,
        override_id: UUID,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Use an override.

        Args:
            override_id: Override to use
            context: Usage context

        Returns:
            True if override was valid and used
        """
        override = self._overrides.get(override_id)
        if not override:
            logger.warning(f"Override not found: {override_id}")
            return False

        if not override.use():
            logger.warning(f"Override no longer valid: {override_id}")
            return False

        # Log usage
        usage_record = {
            "override_id": str(override_id),
            "policy_id": override.policy_id,
            "used_at": datetime.utcnow().isoformat(),
            "context": context or {},
            "uses_remaining": (override.max_uses - override.current_uses) if override.max_uses else None,
        }
        self._usage_log.append(usage_record)

        # Notify callbacks
        for callback in self._on_override_used:
            try:
                callback(override, usage_record)
            except Exception as e:
                logger.error(f"Override used callback error: {e}")

        logger.info(f"Override used: {override_id}")
        return True

    def find_applicable_override(
        self,
        policy_id: str,
        agent_id: Optional[UUID] = None,
        tenant_id: Optional[UUID] = None,
        action_type: Optional[str] = None,
    ) -> Optional[Override]:
        """
        Find an applicable override for a policy.

        Args:
            policy_id: Policy ID
            agent_id: Agent ID
            tenant_id: Tenant ID
            action_type: Action type

        Returns:
            Applicable override or None
        """
        override_ids = self._by_policy.get(policy_id, [])

        for oid in override_ids:
            override = self._overrides.get(oid)
            if not override or not override.is_valid():
                continue

            # Check scope
            if override.agent_id and override.agent_id != agent_id:
                continue
            if override.tenant_id and override.tenant_id != tenant_id:
                continue

            # Check applies_to
            if override.applies_to and action_type:
                import fnmatch
                if not any(fnmatch.fnmatch(action_type, pattern) for pattern in override.applies_to):
                    continue

            return override

        return None

    def revoke(
        self,
        override_id: UUID,
        revoked_by: UUID,
        reason: Optional[str] = None,
    ) -> Optional[Override]:
        """
        Revoke an override.

        Args:
            override_id: Override to revoke
            revoked_by: User revoking
            reason: Revocation reason

        Returns:
            Revoked override or None
        """
        override = self._overrides.get(override_id)
        if not override:
            return None

        override.active = False
        override.revoked_at = datetime.utcnow()
        override.revoked_by = revoked_by
        override.revoke_reason = reason

        # Notify callbacks
        for callback in self._on_override_revoked:
            try:
                callback(override)
            except Exception as e:
                logger.error(f"Override revoked callback error: {e}")

        logger.info(f"Override revoked: {override_id}")
        return override

    def get_override(self, override_id: UUID) -> Optional[Override]:
        """Get an override by ID."""
        return self._overrides.get(override_id)

    def get_active_overrides(
        self,
        policy_id: Optional[str] = None,
        agent_id: Optional[UUID] = None,
        tenant_id: Optional[UUID] = None,
    ) -> List[Override]:
        """Get active overrides with optional filters."""
        overrides = []

        for override in self._overrides.values():
            if not override.is_valid():
                continue
            if policy_id and override.policy_id != policy_id:
                continue
            if agent_id and override.agent_id and override.agent_id != agent_id:
                continue
            if tenant_id and override.tenant_id and override.tenant_id != tenant_id:
                continue

            overrides.append(override)

        return overrides

    def get_override_history(
        self,
        policy_id: Optional[str] = None,
        agent_id: Optional[UUID] = None,
        limit: int = 100,
    ) -> List[Override]:
        """Get override history."""
        overrides = list(self._overrides.values())

        if policy_id:
            overrides = [o for o in overrides if o.policy_id == policy_id]
        if agent_id:
            overrides = [o for o in overrides if o.agent_id == agent_id]

        overrides.sort(key=lambda o: o.created_at, reverse=True)
        return overrides[:limit]

    def get_usage_log(
        self,
        override_id: Optional[UUID] = None,
        policy_id: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get override usage log."""
        log = self._usage_log.copy()

        if override_id:
            log = [r for r in log if r["override_id"] == str(override_id)]
        if policy_id:
            log = [r for r in log if r["policy_id"] == policy_id]
        if since:
            log = [r for r in log if datetime.fromisoformat(r["used_at"]) >= since]

        # Most recent first
        log.reverse()
        return log[:limit]

    def get_stats(self, tenant_id: Optional[UUID] = None) -> Dict[str, Any]:
        """Get override statistics."""
        overrides = list(self._overrides.values())
        if tenant_id:
            overrides = [o for o in overrides if o.tenant_id == tenant_id]

        active = [o for o in overrides if o.is_valid()]
        revoked = [o for o in overrides if o.revoked_at]

        by_policy: Dict[str, int] = {}
        for o in active:
            by_policy[o.policy_id] = by_policy.get(o.policy_id, 0) + 1

        return {
            "total_overrides": len(overrides),
            "active_overrides": len(active),
            "revoked_overrides": len(revoked),
            "by_policy": by_policy,
            "total_uses": sum(o.current_uses for o in overrides),
        }

    # Event registration
    def on_override_created(self, callback: Callable[[Override], None]) -> None:
        """Register callback for override creation."""
        self._on_override_created.append(callback)

    def on_override_used(self, callback: Callable[[Override, Dict[str, Any]], None]) -> None:
        """Register callback for override usage."""
        self._on_override_used.append(callback)

    def on_override_revoked(self, callback: Callable[[Override], None]) -> None:
        """Register callback for override revocation."""
        self._on_override_revoked.append(callback)

    # Private methods

    def _store_override(self, override: Override) -> None:
        """Store override and update indexes."""
        self._overrides[override.id] = override

        if override.policy_id not in self._by_policy:
            self._by_policy[override.policy_id] = []
        self._by_policy[override.policy_id].append(override.id)

        if override.agent_id:
            if override.agent_id not in self._by_agent:
                self._by_agent[override.agent_id] = []
            self._by_agent[override.agent_id].append(override.id)

        if override.tenant_id:
            if override.tenant_id not in self._by_tenant:
                self._by_tenant[override.tenant_id] = []
            self._by_tenant[override.tenant_id].append(override.id)

    def _validate_override_policy(
        self,
        policy: OverridePolicy,
        risk_acknowledgement: bool,
    ) -> None:
        """Validate override against policy."""
        if not policy.enabled:
            raise ValueError(f"Override policy {policy.id} is disabled")

        if policy.requires_risk_acknowledgement and not risk_acknowledgement:
            raise ValueError("Risk acknowledgement required for this override")


# Global instance
_override_manager: Optional[OverrideManager] = None


def get_override_manager() -> OverrideManager:
    """Get the global override manager instance."""
    global _override_manager
    if _override_manager is None:
        _override_manager = OverrideManager()
    return _override_manager
