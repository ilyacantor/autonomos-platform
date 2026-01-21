"""
Certification Registry

Central registry for managing agent certifications:
- Store and retrieve certifications
- Query certification status
- Enforce certification requirements
- Publish certification records
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from uuid import UUID

from .models import (
    Certification,
    CertificationResult,
    CertificationScope,
    CertificationStatus,
    CertificationType,
)

logger = logging.getLogger(__name__)


class CertificationRegistry:
    """
    Central registry for agent certifications.

    Manages the lifecycle of certifications:
    - Creation and issuance
    - Status tracking
    - Expiry management
    - Revocation
    - Query and enforcement
    """

    def __init__(self):
        """Initialize the certification registry."""
        # In-memory storage (production would use database)
        self._certifications: Dict[str, Certification] = {}
        self._by_agent: Dict[UUID, List[str]] = {}  # agent_id -> [cert_ids]
        self._by_tenant: Dict[UUID, List[str]] = {}  # tenant_id -> [cert_ids]

        # Certification enforcement settings
        self._require_certification: bool = True
        self._allowed_uncertified_scopes: Set[CertificationScope] = {
            CertificationScope.SANDBOX
        }

    def issue_certification(
        self,
        agent_id: UUID,
        agent_name: str,
        agent_version: int,
        tenant_id: UUID,
        result: CertificationResult,
        certifier_id: Optional[UUID] = None,
        certifier_name: Optional[str] = None,
        validity_days: int = 90,
        conditions: Optional[List[str]] = None,
        limitations: Optional[List[str]] = None,
    ) -> Certification:
        """
        Issue a new certification based on evaluation results.

        Args:
            agent_id: Agent being certified
            agent_name: Human-readable agent name
            agent_version: Version of the agent
            tenant_id: Owning tenant
            result: Certification evaluation result
            certifier_id: ID of certifier (user or system)
            certifier_name: Name of certifier
            validity_days: How long certification is valid
            conditions: Any conditions on the certification
            limitations: Any limitations on agent capabilities

        Returns:
            Issued Certification record
        """
        now = datetime.utcnow()

        # Determine status based on results
        if result.is_passed():
            status = CertificationStatus.CERTIFIED
        elif result.overall_score >= 0.6:
            status = CertificationStatus.CONDITIONAL
        else:
            status = CertificationStatus.FAILED

        certification = Certification(
            agent_id=agent_id,
            agent_name=agent_name,
            agent_version=agent_version,
            tenant_id=tenant_id,
            status=status,
            certification_type=result.certification_type,
            scope=result.scope,
            result_id=result.id,
            overall_score=result.overall_score,
            requirements_met=result.passed_count,
            requirements_total=result.passed_count + result.failed_count,
            issued_at=now,
            valid_from=now,
            valid_until=now + timedelta(days=validity_days),
            certifier_id=certifier_id,
            certifier_type=result.certifier_type,
            certifier_name=certifier_name or "AOS Certification System",
            conditions=conditions or [],
            limitations=limitations or [],
        )

        # Store certification
        self._store_certification(certification)

        logger.info(
            f"Issued certification {certification.id} for agent {agent_name} "
            f"(status: {status.value}, score: {result.overall_score:.2f})"
        )

        return certification

    def _store_certification(self, certification: Certification) -> None:
        """Store a certification in the registry."""
        self._certifications[certification.id] = certification

        # Index by agent
        if certification.agent_id not in self._by_agent:
            self._by_agent[certification.agent_id] = []
        self._by_agent[certification.agent_id].append(certification.id)

        # Index by tenant
        if certification.tenant_id not in self._by_tenant:
            self._by_tenant[certification.tenant_id] = []
        self._by_tenant[certification.tenant_id].append(certification.id)

    def get_certification(self, cert_id: str) -> Optional[Certification]:
        """Get a certification by ID."""
        return self._certifications.get(cert_id)

    def get_current_certification(self, agent_id: UUID) -> Optional[Certification]:
        """
        Get the current valid certification for an agent.

        Returns the most recent valid certification, or None if not certified.
        """
        cert_ids = self._by_agent.get(agent_id, [])
        if not cert_ids:
            return None

        # Find most recent valid certification
        valid_certs = []
        for cert_id in cert_ids:
            cert = self._certifications.get(cert_id)
            if cert and cert.is_valid():
                valid_certs.append(cert)

        if not valid_certs:
            return None

        # Return most recently issued
        return max(valid_certs, key=lambda c: c.issued_at or datetime.min)

    def get_certification_history(
        self,
        agent_id: UUID,
        limit: int = 10,
    ) -> List[Certification]:
        """Get certification history for an agent."""
        cert_ids = self._by_agent.get(agent_id, [])
        certs = [self._certifications[cid] for cid in cert_ids if cid in self._certifications]
        certs.sort(key=lambda c: c.issued_at or datetime.min, reverse=True)
        return certs[:limit]

    def get_tenant_certifications(
        self,
        tenant_id: UUID,
        status: Optional[CertificationStatus] = None,
        include_expired: bool = False,
    ) -> List[Certification]:
        """Get all certifications for a tenant."""
        cert_ids = self._by_tenant.get(tenant_id, [])
        certs = []

        for cert_id in cert_ids:
            cert = self._certifications.get(cert_id)
            if not cert:
                continue

            if status and cert.status != status:
                continue

            if not include_expired and not cert.is_valid():
                # Still include if status filter matches
                if not status:
                    continue

            certs.append(cert)

        return certs

    def is_agent_certified(
        self,
        agent_id: UUID,
        scope: Optional[CertificationScope] = None,
    ) -> bool:
        """
        Check if an agent has a valid certification.

        Args:
            agent_id: Agent to check
            scope: Required scope (None = any scope)

        Returns:
            True if agent has valid certification
        """
        cert = self.get_current_certification(agent_id)
        if not cert:
            return False

        if scope and cert.scope != scope:
            # Check if cert scope is broader
            scope_hierarchy = {
                CertificationScope.SANDBOX: 0,
                CertificationScope.LIMITED: 1,
                CertificationScope.INTERNAL: 2,
                CertificationScope.EXTERNAL: 3,
                CertificationScope.PRODUCTION: 4,
                CertificationScope.FULL: 5,
            }
            if scope_hierarchy.get(cert.scope, 0) < scope_hierarchy.get(scope, 0):
                return False

        return True

    def can_agent_execute(
        self,
        agent_id: UUID,
        scope: CertificationScope = CertificationScope.PRODUCTION,
        tool_name: Optional[str] = None,
    ) -> tuple[bool, Optional[str]]:
        """
        Check if an agent can execute in the given scope.

        Args:
            agent_id: Agent to check
            scope: Execution scope
            tool_name: Optional tool being used

        Returns:
            Tuple of (can_execute, reason_if_not)
        """
        # Check if certification is required for this scope
        if not self._require_certification:
            return True, None

        if scope in self._allowed_uncertified_scopes:
            return True, None

        # Get current certification
        cert = self.get_current_certification(agent_id)

        if not cert:
            return False, "Agent is not certified"

        if not cert.is_valid():
            return False, f"Certification has status: {cert.status.value}"

        # Check scope
        if not self.is_agent_certified(agent_id, scope):
            return False, f"Agent not certified for scope: {scope.value}"

        # Check tool restrictions
        if tool_name:
            if cert.denied_tools and tool_name in cert.denied_tools:
                return False, f"Tool {tool_name} is denied by certification"

            if cert.allowed_tools and tool_name not in cert.allowed_tools:
                return False, f"Tool {tool_name} is not in allowed tools list"

        return True, None

    def revoke_certification(
        self,
        cert_id: str,
        revoked_by: UUID,
        reason: str,
    ) -> Optional[Certification]:
        """
        Revoke a certification.

        Args:
            cert_id: Certification to revoke
            revoked_by: User revoking the certification
            reason: Reason for revocation

        Returns:
            Updated certification or None if not found
        """
        cert = self._certifications.get(cert_id)
        if not cert:
            return None

        cert.status = CertificationStatus.REVOKED
        cert.revoked_at = datetime.utcnow()
        cert.revoked_by = revoked_by
        cert.revocation_reason = reason
        cert.updated_at = datetime.utcnow()

        logger.warning(
            f"Certification {cert_id} revoked for agent {cert.agent_name}: {reason}"
        )

        return cert

    def suspend_certification(
        self,
        cert_id: str,
        reason: str,
    ) -> Optional[Certification]:
        """
        Temporarily suspend a certification.

        Args:
            cert_id: Certification to suspend
            reason: Reason for suspension

        Returns:
            Updated certification or None if not found
        """
        cert = self._certifications.get(cert_id)
        if not cert:
            return None

        cert.status = CertificationStatus.SUSPENDED
        cert.updated_at = datetime.utcnow()
        cert.metadata["suspension_reason"] = reason
        cert.metadata["suspended_at"] = datetime.utcnow().isoformat()

        logger.warning(
            f"Certification {cert_id} suspended for agent {cert.agent_name}: {reason}"
        )

        return cert

    def reinstate_certification(
        self,
        cert_id: str,
    ) -> Optional[Certification]:
        """
        Reinstate a suspended certification.

        Args:
            cert_id: Certification to reinstate

        Returns:
            Updated certification or None if not found
        """
        cert = self._certifications.get(cert_id)
        if not cert:
            return None

        if cert.status != CertificationStatus.SUSPENDED:
            logger.warning(f"Cannot reinstate cert {cert_id}: status is {cert.status.value}")
            return None

        # Restore previous status (default to certified)
        cert.status = CertificationStatus.CERTIFIED
        cert.updated_at = datetime.utcnow()
        cert.metadata["reinstated_at"] = datetime.utcnow().isoformat()

        logger.info(f"Certification {cert_id} reinstated for agent {cert.agent_name}")

        return cert

    def check_expirations(self) -> List[Certification]:
        """
        Check for expiring/expired certifications.

        Returns:
            List of certifications that need attention
        """
        now = datetime.utcnow()
        expiring_soon = now + timedelta(days=14)  # 2 weeks warning

        needs_attention = []

        for cert in self._certifications.values():
            if cert.status not in (CertificationStatus.CERTIFIED, CertificationStatus.CONDITIONAL):
                continue

            if cert.valid_until:
                if cert.valid_until < now:
                    # Mark as expired
                    cert.status = CertificationStatus.EXPIRED
                    cert.updated_at = now
                    needs_attention.append(cert)
                    logger.warning(f"Certification {cert.id} for {cert.agent_name} has expired")

                elif cert.valid_until < expiring_soon:
                    needs_attention.append(cert)
                    logger.info(
                        f"Certification {cert.id} for {cert.agent_name} "
                        f"expires in {cert.days_until_expiry()} days"
                    )

        return needs_attention

    def get_statistics(self, tenant_id: Optional[UUID] = None) -> Dict:
        """Get certification statistics."""
        if tenant_id:
            certs = self.get_tenant_certifications(tenant_id, include_expired=True)
        else:
            certs = list(self._certifications.values())

        stats = {
            "total": len(certs),
            "by_status": {},
            "by_scope": {},
            "average_score": 0.0,
            "expiring_soon": 0,
        }

        scores = []
        now = datetime.utcnow()
        expiring_threshold = now + timedelta(days=14)

        for cert in certs:
            # By status
            status = cert.status.value
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

            # By scope
            scope = cert.scope.value
            stats["by_scope"][scope] = stats["by_scope"].get(scope, 0) + 1

            # Score
            if cert.overall_score > 0:
                scores.append(cert.overall_score)

            # Expiring soon
            if cert.valid_until and now < cert.valid_until < expiring_threshold:
                stats["expiring_soon"] += 1

        if scores:
            stats["average_score"] = sum(scores) / len(scores)

        return stats

    def export_certification(self, cert_id: str) -> Optional[Dict]:
        """
        Export a certification record for publishing.

        This creates an immutable, shareable record of the certification.
        """
        cert = self._certifications.get(cert_id)
        if not cert:
            return None

        return {
            "certification_id": cert.id,
            "agent": {
                "id": str(cert.agent_id),
                "name": cert.agent_name,
                "version": cert.agent_version,
            },
            "certification": {
                "status": cert.status.value,
                "type": cert.certification_type.value,
                "scope": cert.scope.value,
                "score": cert.overall_score,
                "requirements_met": cert.requirements_met,
                "requirements_total": cert.requirements_total,
            },
            "validity": {
                "issued_at": cert.issued_at.isoformat() if cert.issued_at else None,
                "valid_from": cert.valid_from.isoformat() if cert.valid_from else None,
                "valid_until": cert.valid_until.isoformat() if cert.valid_until else None,
                "is_valid": cert.is_valid(),
            },
            "certifier": {
                "type": cert.certifier_type,
                "name": cert.certifier_name,
            },
            "conditions": cert.conditions,
            "limitations": cert.limitations,
            "exported_at": datetime.utcnow().isoformat(),
        }


# Global registry instance
_registry: Optional[CertificationRegistry] = None


def get_certification_registry() -> CertificationRegistry:
    """Get the global certification registry instance."""
    global _registry
    if _registry is None:
        _registry = CertificationRegistry()
    return _registry
