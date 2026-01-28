"""
Workflow models - Approval workflows and HITL repair audit.

Includes human-in-the-loop approval processes and repair audit tracking.
"""
from app.models.base import (
    uuid, Column, String, JSON, DateTime, Integer, Float, ForeignKey, func, Index, UUID, relationship, Base
)


class HITLRepairAudit(Base):
    """
    HITL Repair Audit - persistent tracking of Human-In-The-Loop repair decisions.

    Complements Redis queue (7-day TTL) with permanent audit logging for:
    - Repair suggestions requiring human review (confidence 0.6-0.85)
    - Review decisions (approved/rejected)
    - Full audit trail for compliance and learning
    """
    __tablename__ = "hitl_repair_audit"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)

    drift_event_id = Column(String, nullable=False, index=True)
    field_name = Column(String, nullable=False)
    connector_name = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)

    suggested_mapping = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    confidence_reason = Column(String)
    transformation = Column(String)
    rag_similarity_count = Column(Integer, default=0)

    review_status = Column(String, default="pending", nullable=False)
    reviewed_by = Column(String, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(String, nullable=True)

    audit_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('idx_hitl_tenant_status', 'tenant_id', 'review_status'),
        Index('idx_hitl_drift_event', 'drift_event_id'),
    )


class ApprovalWorkflow(Base):
    """
    Phase 2: Human-in-the-Loop Approval Workflow

    Manages approval process for medium-confidence mapping proposals (0.6-0.85).
    7-day TTL for review with Slack/email notifications.
    """
    __tablename__ = "approval_workflows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    proposal_id = Column(UUID(as_uuid=True), ForeignKey("mapping_proposals.id"), nullable=False, index=True)

    status = Column(String(20), nullable=False, server_default='pending')
    priority = Column(String(20), server_default='normal')

    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    approver_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    approval_notes = Column(String, nullable=True)
    rejection_reason = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    proposal = relationship("MappingProposal", back_populates="approval_workflows")

    __table_args__ = (
        Index('idx_workflows_status', 'tenant_id', 'status', 'created_at'),
        Index('idx_workflows_assigned', 'assigned_to', 'status'),
    )
