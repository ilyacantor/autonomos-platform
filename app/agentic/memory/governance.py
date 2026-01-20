"""
Memory Governance

GDPR-compliant memory management:
- Right to Forget (data erasure)
- Retention policies
- Data portability
- Consent management
- Audit logging
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import UUID, uuid4

from app.agentic.memory.vector_store import (
    VectorStore,
    DocumentType,
    MemoryDocument,
    get_vector_store,
)

logger = logging.getLogger(__name__)


class RetentionPeriod(str, Enum):
    """Standard retention periods."""
    EPHEMERAL = "ephemeral"      # Delete after session
    DAY = "1_day"                # 24 hours
    WEEK = "1_week"              # 7 days
    MONTH = "1_month"            # 30 days
    QUARTER = "3_months"         # 90 days
    YEAR = "1_year"              # 365 days
    INDEFINITE = "indefinite"    # No automatic expiration


class ForgetScope(str, Enum):
    """Scope of data to forget."""
    ALL = "all"                      # All user data
    CONVERSATION = "conversation"    # Specific conversation
    DATE_RANGE = "date_range"       # Data within date range
    DOCUMENT_TYPE = "document_type"  # Specific document types
    AGENT = "agent"                  # Data from specific agent


class ConsentType(str, Enum):
    """Types of consent."""
    MEMORY_STORAGE = "memory_storage"      # Store conversation history
    LEARNING = "learning"                  # Use for model learning
    ANALYTICS = "analytics"                # Use for analytics
    PERSONALIZATION = "personalization"    # Use for personalization
    THIRD_PARTY = "third_party"           # Share with third parties


@dataclass
class RetentionPolicy:
    """Policy for data retention."""

    policy_id: str
    tenant_id: str
    name: str

    # Default retention
    default_retention: RetentionPeriod = RetentionPeriod.MONTH

    # Retention by document type
    retention_by_type: Dict[DocumentType, RetentionPeriod] = field(default_factory=dict)

    # Auto-cleanup
    auto_cleanup_enabled: bool = True
    cleanup_interval_hours: int = 24

    # Anonymization
    anonymize_before_delete: bool = False

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def get_retention_period(self, doc_type: DocumentType) -> RetentionPeriod:
        """Get retention period for a document type."""
        return self.retention_by_type.get(doc_type, self.default_retention)

    def get_expiration(
        self,
        doc_type: DocumentType,
        created_at: Optional[datetime] = None,
    ) -> Optional[datetime]:
        """Calculate expiration date for a document."""
        created_at = created_at or datetime.utcnow()
        period = self.get_retention_period(doc_type)

        if period == RetentionPeriod.INDEFINITE:
            return None
        elif period == RetentionPeriod.EPHEMERAL:
            return created_at  # Immediate expiration after session
        elif period == RetentionPeriod.DAY:
            return created_at + timedelta(days=1)
        elif period == RetentionPeriod.WEEK:
            return created_at + timedelta(weeks=1)
        elif period == RetentionPeriod.MONTH:
            return created_at + timedelta(days=30)
        elif period == RetentionPeriod.QUARTER:
            return created_at + timedelta(days=90)
        elif period == RetentionPeriod.YEAR:
            return created_at + timedelta(days=365)
        else:
            return created_at + timedelta(days=30)  # Default to 30 days

    def to_dict(self) -> dict:
        return {
            "policy_id": self.policy_id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "default_retention": self.default_retention.value,
            "retention_by_type": {
                k.value: v.value for k, v in self.retention_by_type.items()
            },
            "auto_cleanup_enabled": self.auto_cleanup_enabled,
            "cleanup_interval_hours": self.cleanup_interval_hours,
            "anonymize_before_delete": self.anonymize_before_delete,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class ForgetRequest:
    """Request to forget (delete) user data."""

    request_id: str
    tenant_id: str
    user_id: str

    # Scope
    scope: ForgetScope
    conversation_id: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    document_types: Optional[List[DocumentType]] = None
    agent_id: Optional[str] = None

    # Options
    include_backups: bool = True
    include_derived_data: bool = True

    # Verification
    verified: bool = False
    verification_code: Optional[str] = None

    # Status
    status: str = "pending"  # pending, processing, completed, failed
    error_message: Optional[str] = None

    # Timestamps
    requested_at: datetime = field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "scope": self.scope.value,
            "conversation_id": self.conversation_id,
            "date_from": self.date_from.isoformat() if self.date_from else None,
            "date_to": self.date_to.isoformat() if self.date_to else None,
            "document_types": [dt.value for dt in self.document_types] if self.document_types else None,
            "agent_id": self.agent_id,
            "include_backups": self.include_backups,
            "include_derived_data": self.include_derived_data,
            "verified": self.verified,
            "status": self.status,
            "error_message": self.error_message,
            "requested_at": self.requested_at.isoformat(),
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
        }


@dataclass
class ForgetResult:
    """Result of a forget request."""

    request_id: str
    success: bool
    documents_deleted: int
    documents_anonymized: int = 0
    errors: List[str] = field(default_factory=list)
    processing_time_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "success": self.success,
            "documents_deleted": self.documents_deleted,
            "documents_anonymized": self.documents_anonymized,
            "errors": self.errors,
            "processing_time_ms": self.processing_time_ms,
        }


@dataclass
class UserConsent:
    """User consent record."""

    consent_id: str
    tenant_id: str
    user_id: str
    consents: Dict[ConsentType, bool] = field(default_factory=dict)
    granted_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None

    def is_granted(self, consent_type: ConsentType) -> bool:
        """Check if specific consent is granted."""
        return self.consents.get(consent_type, False)

    def to_dict(self) -> dict:
        return {
            "consent_id": self.consent_id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "consents": {k.value: v for k, v in self.consents.items()},
            "granted_at": self.granted_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


@dataclass
class AuditEntry:
    """Audit log entry for governance actions."""

    entry_id: str
    tenant_id: str
    user_id: Optional[str]
    action: str  # forget_request, policy_update, consent_change, etc.
    details: Dict[str, Any]
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "entry_id": self.entry_id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "action": self.action,
            "details": self.details,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "timestamp": self.timestamp.isoformat(),
        }


class MemoryGovernance:
    """
    Memory governance service.

    Handles GDPR compliance:
    - Right to Forget (Article 17)
    - Data Portability (Article 20)
    - Consent Management
    - Retention Policies
    """

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
    ):
        """Initialize memory governance."""
        self.vector_store = vector_store or get_vector_store()

        # Storage
        self._retention_policies: Dict[str, RetentionPolicy] = {}
        self._forget_requests: Dict[str, ForgetRequest] = {}
        self._user_consents: Dict[str, UserConsent] = {}  # keyed by user_id
        self._audit_log: List[AuditEntry] = []

    async def create_retention_policy(
        self,
        tenant_id: str,
        name: str,
        default_retention: RetentionPeriod = RetentionPeriod.MONTH,
        retention_by_type: Optional[Dict[DocumentType, RetentionPeriod]] = None,
        auto_cleanup_enabled: bool = True,
    ) -> RetentionPolicy:
        """Create a retention policy."""
        policy = RetentionPolicy(
            policy_id=str(uuid4()),
            tenant_id=tenant_id,
            name=name,
            default_retention=default_retention,
            retention_by_type=retention_by_type or {},
            auto_cleanup_enabled=auto_cleanup_enabled,
        )

        self._retention_policies[policy.policy_id] = policy

        # Audit log
        await self._audit(
            tenant_id=tenant_id,
            user_id=None,
            action="policy_created",
            details={"policy_id": policy.policy_id, "name": name},
        )

        return policy

    async def get_retention_policy(
        self,
        policy_id: str,
    ) -> Optional[RetentionPolicy]:
        """Get a retention policy."""
        return self._retention_policies.get(policy_id)

    async def list_retention_policies(
        self,
        tenant_id: str,
    ) -> List[RetentionPolicy]:
        """List all retention policies for a tenant."""
        return [
            p for p in self._retention_policies.values()
            if p.tenant_id == tenant_id
        ]

    async def request_forget(
        self,
        tenant_id: str,
        user_id: str,
        scope: ForgetScope = ForgetScope.ALL,
        conversation_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        document_types: Optional[List[DocumentType]] = None,
        agent_id: Optional[str] = None,
        require_verification: bool = True,
    ) -> ForgetRequest:
        """
        Request to forget (delete) user data.

        GDPR Article 17 - Right to Erasure.
        """
        import secrets

        request = ForgetRequest(
            request_id=str(uuid4()),
            tenant_id=tenant_id,
            user_id=user_id,
            scope=scope,
            conversation_id=conversation_id,
            date_from=date_from,
            date_to=date_to,
            document_types=document_types,
            agent_id=agent_id,
            verified=not require_verification,
            verification_code=secrets.token_urlsafe(16) if require_verification else None,
        )

        self._forget_requests[request.request_id] = request

        # Audit log
        await self._audit(
            tenant_id=tenant_id,
            user_id=user_id,
            action="forget_requested",
            details={
                "request_id": request.request_id,
                "scope": scope.value,
                "require_verification": require_verification,
            },
        )

        logger.info(f"Forget request created: {request.request_id}")
        return request

    async def verify_forget_request(
        self,
        request_id: str,
        verification_code: str,
    ) -> bool:
        """Verify a forget request."""
        request = self._forget_requests.get(request_id)
        if not request:
            return False

        if request.verification_code != verification_code:
            return False

        request.verified = True

        # Audit log
        await self._audit(
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            action="forget_verified",
            details={"request_id": request_id},
        )

        return True

    async def process_forget_request(
        self,
        request_id: str,
    ) -> ForgetResult:
        """
        Process a verified forget request.

        This deletes all matching data from the vector store.
        """
        start_time = datetime.utcnow()
        request = self._forget_requests.get(request_id)

        if not request:
            return ForgetResult(
                request_id=request_id,
                success=False,
                documents_deleted=0,
                errors=["Request not found"],
            )

        if not request.verified:
            return ForgetResult(
                request_id=request_id,
                success=False,
                documents_deleted=0,
                errors=["Request not verified"],
            )

        if request.status == "completed":
            return ForgetResult(
                request_id=request_id,
                success=True,
                documents_deleted=0,
                errors=["Request already processed"],
            )

        request.status = "processing"
        deleted = 0
        errors = []

        try:
            if request.scope == ForgetScope.ALL:
                # Delete all user data
                deleted = await self.vector_store.delete_by_user(
                    user_id=request.user_id,
                    tenant_id=request.tenant_id,
                )

            elif request.scope == ForgetScope.CONVERSATION:
                if request.conversation_id:
                    deleted = await self.vector_store.delete_by_conversation(
                        conversation_id=request.conversation_id,
                        tenant_id=request.tenant_id,
                    )
                else:
                    errors.append("conversation_id required for CONVERSATION scope")

            # TODO: Implement other scopes (DATE_RANGE, DOCUMENT_TYPE, AGENT)

            request.status = "completed"
            request.processed_at = datetime.utcnow()

        except Exception as e:
            request.status = "failed"
            request.error_message = str(e)
            errors.append(str(e))
            logger.error(f"Forget request failed: {e}")

        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        # Audit log
        await self._audit(
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            action="forget_processed",
            details={
                "request_id": request_id,
                "documents_deleted": deleted,
                "success": request.status == "completed",
            },
        )

        return ForgetResult(
            request_id=request_id,
            success=request.status == "completed",
            documents_deleted=deleted,
            errors=errors,
            processing_time_ms=processing_time,
        )

    async def get_forget_request(
        self,
        request_id: str,
    ) -> Optional[ForgetRequest]:
        """Get a forget request."""
        return self._forget_requests.get(request_id)

    async def list_forget_requests(
        self,
        tenant_id: str,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[ForgetRequest]:
        """List forget requests."""
        requests = [
            r for r in self._forget_requests.values()
            if r.tenant_id == tenant_id
        ]

        if user_id:
            requests = [r for r in requests if r.user_id == user_id]

        if status:
            requests = [r for r in requests if r.status == status]

        return sorted(requests, key=lambda r: r.requested_at, reverse=True)

    async def set_user_consent(
        self,
        tenant_id: str,
        user_id: str,
        consents: Dict[ConsentType, bool],
    ) -> UserConsent:
        """Set user consent preferences."""
        existing = self._user_consents.get(user_id)

        if existing:
            existing.consents.update(consents)
            existing.updated_at = datetime.utcnow()
            consent = existing
        else:
            consent = UserConsent(
                consent_id=str(uuid4()),
                tenant_id=tenant_id,
                user_id=user_id,
                consents=consents,
            )
            self._user_consents[user_id] = consent

        # Audit log
        await self._audit(
            tenant_id=tenant_id,
            user_id=user_id,
            action="consent_updated",
            details={"consents": {k.value: v for k, v in consents.items()}},
        )

        return consent

    async def get_user_consent(
        self,
        user_id: str,
    ) -> Optional[UserConsent]:
        """Get user consent."""
        return self._user_consents.get(user_id)

    async def check_consent(
        self,
        user_id: str,
        consent_type: ConsentType,
    ) -> bool:
        """Check if user has granted specific consent."""
        consent = self._user_consents.get(user_id)
        if not consent:
            return False
        return consent.is_granted(consent_type)

    async def export_user_data(
        self,
        tenant_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Export all user data (GDPR Article 20 - Data Portability).

        Returns all data associated with the user in a portable format.
        """
        # Get all documents for user
        tenant_docs = self.vector_store._documents.get(tenant_id, {})
        user_docs = [
            doc.to_dict() for doc in tenant_docs.values()
            if doc.user_id == user_id
        ]

        # Get consent record
        consent = self._user_consents.get(user_id)

        # Get forget requests
        forget_requests = [
            r.to_dict() for r in self._forget_requests.values()
            if r.user_id == user_id
        ]

        # Audit log
        await self._audit(
            tenant_id=tenant_id,
            user_id=user_id,
            action="data_exported",
            details={"document_count": len(user_docs)},
        )

        return {
            "export_date": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "tenant_id": tenant_id,
            "documents": user_docs,
            "document_count": len(user_docs),
            "consent": consent.to_dict() if consent else None,
            "forget_requests": forget_requests,
        }

    async def run_retention_cleanup(
        self,
        tenant_id: Optional[str] = None,
    ) -> int:
        """Run retention cleanup to remove expired documents."""
        deleted = await self.vector_store.cleanup_expired(tenant_id)

        logger.info(f"Retention cleanup removed {deleted} expired documents")

        if tenant_id:
            await self._audit(
                tenant_id=tenant_id,
                user_id=None,
                action="retention_cleanup",
                details={"documents_deleted": deleted},
            )

        return deleted

    async def get_audit_log(
        self,
        tenant_id: str,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 100,
    ) -> List[AuditEntry]:
        """Get audit log entries."""
        entries = [
            e for e in self._audit_log
            if e.tenant_id == tenant_id
        ]

        if user_id:
            entries = [e for e in entries if e.user_id == user_id]

        if action:
            entries = [e for e in entries if e.action == action]

        return sorted(entries, key=lambda e: e.timestamp, reverse=True)[:limit]

    async def _audit(
        self,
        tenant_id: str,
        user_id: Optional[str],
        action: str,
        details: Dict[str, Any],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """Add an entry to the audit log."""
        entry = AuditEntry(
            entry_id=str(uuid4()),
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        self._audit_log.append(entry)

        # Keep log bounded
        if len(self._audit_log) > 10000:
            self._audit_log = self._audit_log[-10000:]


# Global instance
_memory_governance: Optional[MemoryGovernance] = None


def get_memory_governance() -> MemoryGovernance:
    """Get the global memory governance instance."""
    global _memory_governance
    if _memory_governance is None:
        _memory_governance = MemoryGovernance()
    return _memory_governance
