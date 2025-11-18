"""
Mapping Approval Service - Phase 2

Human-in-the-Loop (HITL) workflow for medium-confidence proposals.
Manages approval queue, notifications, and auto-routing based on confidence tiers.

Confidence Routing:
- High (>=0.85): Auto-approved, no human review needed
- Medium (0.6-0.85): HITL queue with 7-day TTL
- Low (<0.6): Auto-rejected, too uncertain
"""

import logging
import uuid
from typing import Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)


@dataclass
class ApprovalWorkflow:
    """Approval workflow record"""
    workflow_id: str
    proposal_id: str
    status: str
    assigned_to: str
    created_at: datetime
    expires_at: datetime
    priority: str = "normal"
    approver_id: Optional[str] = None
    approval_notes: Optional[str] = None
    rejection_reason: Optional[str] = None


class MappingApprovalService:
    """
    Approval workflow service for medium-confidence proposals.
    Manages HITL queue, notifications, and auto-approval.
    """
    
    APPROVAL_TTL_DAYS = 7
    
    def __init__(self, db_session: AsyncSession, notification_service: Optional[Any] = None):
        """
        Initialize approval service.
        
        Args:
            db_session: Async SQLAlchemy session
            notification_service: Optional notification service (Slack, email)
        """
        self.db = db_session
        self.notifications = notification_service
        logger.info("MappingApprovalService initialized")
    
    async def submit_for_approval(
        self,
        proposal_id: str,
        tenant_id: str,
        priority: str = "normal",
        notes: Optional[str] = None
    ) -> ApprovalWorkflow:
        """
        Submit proposal to approval workflow.
        
        Flow:
        1. Create ApprovalWorkflow record (status='pending')
        2. Assign to tenant admin
        3. Send notification (Slack, email)
        4. Set 7-day TTL for review
        
        Args:
            proposal_id: Mapping proposal ID
            tenant_id: Tenant identifier
            priority: Workflow priority (normal/high/critical)
            notes: Optional submission notes
            
        Returns:
            ApprovalWorkflow with ID, status, assigned_to
        """
        workflow_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        expires_at = created_at + timedelta(days=self.APPROVAL_TTL_DAYS)
        
        assigned_to = await self._get_tenant_admin(tenant_id)
        
        try:
            query = text("""
                INSERT INTO approval_workflows (
                    id, tenant_id, proposal_id, status, priority,
                    assigned_to, created_at, expires_at
                ) VALUES (
                    :id, :tenant_id, :proposal_id, :status, :priority,
                    :assigned_to, :created_at, :expires_at
                )
            """)
            
            await self.db.execute(
                query,
                {
                    'id': workflow_id,
                    'tenant_id': tenant_id,
                    'proposal_id': proposal_id,
                    'status': 'pending',
                    'priority': priority,
                    'assigned_to': assigned_to,
                    'created_at': created_at,
                    'expires_at': expires_at
                }
            )
            await self.db.commit()
            
            logger.info(
                f"Created approval workflow: {workflow_id} "
                f"(proposal={proposal_id}, assigned_to={assigned_to})"
            )
            
            if self.notifications:
                await self._notify_approver(workflow_id, proposal_id, assigned_to)
            
        except Exception as e:
            logger.error(f"Failed to create approval workflow: {e}")
            await self.db.rollback()
            raise
        
        return ApprovalWorkflow(
            workflow_id=workflow_id,
            proposal_id=proposal_id,
            status='pending',
            assigned_to=assigned_to,
            created_at=created_at,
            expires_at=expires_at,
            priority=priority
        )
    
    async def approve_proposal(
        self,
        workflow_id: str,
        approver_id: str,
        notes: Optional[str] = None
    ):
        """
        Approve a pending proposal.
        
        Flow:
        1. Update workflow status to 'approved'
        2. Create FieldMapping record from proposal
        3. Index mapping in RAG vector store
        4. Notify requester
        
        Args:
            workflow_id: Approval workflow ID
            approver_id: User ID of approver
            notes: Optional approval notes
        """
        try:
            query = text("""
                UPDATE approval_workflows
                SET 
                    status = 'approved',
                    approver_id = :approver_id,
                    approval_notes = :notes,
                    updated_at = :updated_at
                WHERE id = :workflow_id
                RETURNING proposal_id, tenant_id
            """)
            
            result = await self.db.execute(
                query,
                {
                    'workflow_id': workflow_id,
                    'approver_id': approver_id,
                    'notes': notes,
                    'updated_at': datetime.utcnow()
                }
            )
            
            row = result.fetchone()
            if not row:
                raise ValueError(f"Workflow {workflow_id} not found")
            
            proposal_id = row.proposal_id
            tenant_id = row.tenant_id
            
            await self._create_field_mapping_from_proposal(proposal_id, tenant_id)
            
            await self.db.commit()
            
            logger.info(
                f"Approved workflow: {workflow_id} "
                f"(proposal={proposal_id}, approver={approver_id})"
            )
            
        except Exception as e:
            logger.error(f"Failed to approve proposal: {e}")
            await self.db.rollback()
            raise
    
    async def reject_proposal(
        self,
        workflow_id: str,
        approver_id: str,
        reason: str
    ):
        """
        Reject a pending proposal.
        
        Flow:
        1. Update workflow status to 'rejected'
        2. Store rejection reason
        3. Notify requester
        
        Args:
            workflow_id: Approval workflow ID
            approver_id: User ID of approver
            reason: Rejection reason (required)
        """
        try:
            query = text("""
                UPDATE approval_workflows
                SET 
                    status = 'rejected',
                    approver_id = :approver_id,
                    rejection_reason = :reason,
                    updated_at = :updated_at
                WHERE id = :workflow_id
            """)
            
            await self.db.execute(
                query,
                {
                    'workflow_id': workflow_id,
                    'approver_id': approver_id,
                    'reason': reason,
                    'updated_at': datetime.utcnow()
                }
            )
            await self.db.commit()
            
            logger.info(
                f"Rejected workflow: {workflow_id} "
                f"(approver={approver_id}, reason={reason})"
            )
            
        except Exception as e:
            logger.error(f"Failed to reject proposal: {e}")
            await self.db.rollback()
            raise
    
    async def get_approval_status(self, proposal_id: str) -> Optional[ApprovalWorkflow]:
        """
        Check approval workflow status for a proposal.
        
        Args:
            proposal_id: Mapping proposal ID
            
        Returns:
            ApprovalWorkflow if found, None otherwise
        """
        try:
            query = text("""
                SELECT 
                    id, proposal_id, status, assigned_to, approver_id,
                    approval_notes, rejection_reason, priority,
                    created_at, updated_at, expires_at
                FROM approval_workflows
                WHERE proposal_id = :proposal_id
                ORDER BY created_at DESC
                LIMIT 1
            """)
            
            result = await self.db.execute(query, {'proposal_id': proposal_id})
            row = result.fetchone()
            
            if not row:
                return None
            
            return ApprovalWorkflow(
                workflow_id=str(row.id),
                proposal_id=str(row.proposal_id),
                status=row.status,
                assigned_to=str(row.assigned_to),
                created_at=row.created_at,
                expires_at=row.expires_at,
                priority=row.priority,
                approver_id=str(row.approver_id) if row.approver_id else None,
                approval_notes=row.approval_notes,
                rejection_reason=row.rejection_reason
            )
            
        except Exception as e:
            logger.error(f"Failed to get approval status: {e}")
            return None
    
    async def _get_tenant_admin(self, tenant_id: str) -> str:
        """
        Get tenant admin user ID for approval assignment.
        
        Returns first admin user for the tenant.
        """
        try:
            query = text("""
                SELECT id 
                FROM users 
                WHERE tenant_id = :tenant_id 
                    AND is_admin = 'true'
                ORDER BY created_at
                LIMIT 1
            """)
            
            result = await self.db.execute(query, {'tenant_id': tenant_id})
            row = result.fetchone()
            
            if row:
                return str(row.id)
            
            logger.warning(f"No admin found for tenant {tenant_id}, using system default")
            return "system"
            
        except Exception as e:
            logger.error(f"Failed to get tenant admin: {e}")
            return "system"
    
    async def _create_field_mapping_from_proposal(
        self,
        proposal_id: str,
        tenant_id: str
    ):
        """
        Create FieldMapping record from approved MappingProposal.
        
        Converts proposal into active mapping configuration.
        """
        try:
            query = text("""
                INSERT INTO field_mappings (
                    id, tenant_id, connector_id, entity_schema_id,
                    source_table, source_field, canonical_entity, canonical_field,
                    confidence_score, mapping_source, status, created_at
                )
                SELECT 
                    gen_random_uuid(),
                    :tenant_id,
                    cd.id,
                    es.id,
                    mp.source_table,
                    mp.source_field,
                    mp.canonical_entity,
                    mp.canonical_field,
                    mp.confidence,
                    'approval',
                    'active',
                    NOW()
                FROM mapping_proposals mp
                CROSS JOIN LATERAL (
                    SELECT id FROM connector_definitions 
                    WHERE connector_name = mp.connector 
                    AND tenant_id = :tenant_id
                    LIMIT 1
                ) cd
                CROSS JOIN LATERAL (
                    SELECT id FROM entity_schemas 
                    WHERE entity_name = mp.canonical_entity
                    LIMIT 1
                ) es
                WHERE mp.id = :proposal_id
            """)
            
            await self.db.execute(
                query,
                {
                    'tenant_id': tenant_id,
                    'proposal_id': proposal_id
                }
            )
            
            logger.info(f"Created field mapping from approved proposal: {proposal_id}")
            
        except Exception as e:
            logger.error(f"Failed to create field mapping: {e}")
            raise
    
    async def _notify_approver(
        self,
        workflow_id: str,
        proposal_id: str,
        assigned_to: str
    ):
        """
        Send notification to approver (Slack, email).
        
        Placeholder for notification integration.
        """
        if not self.notifications:
            logger.debug("No notification service configured, skipping notification")
            return
        
        try:
            message = (
                f"New mapping approval request: {workflow_id}\n"
                f"Proposal ID: {proposal_id}\n"
                f"Please review within 7 days"
            )
            
            await self.notifications.send(
                recipient=assigned_to,
                message=message,
                channel="approvals"
            )
            
            logger.info(f"Sent approval notification to {assigned_to}")
            
        except Exception as e:
            logger.warning(f"Failed to send notification: {e}")
