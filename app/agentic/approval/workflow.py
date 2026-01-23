"""
Approval Workflow

Human-in-the-loop approval routing and processing.
Implements Approval Workflows from RACI.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID

from .models import (
    ApprovalRequest,
    ApprovalDecision,
    ApprovalStatus,
    ApprovalPriority,
    ApprovalType,
    EscalationLevel,
)

logger = logging.getLogger(__name__)


@dataclass
class ApprovalRoute:
    """Routing rule for approval requests."""
    id: str
    name: str
    description: str = ""

    # Matching criteria
    request_types: List[ApprovalType] = field(default_factory=list)
    priority_levels: List[ApprovalPriority] = field(default_factory=list)
    agent_ids: Optional[List[UUID]] = None
    tenant_ids: Optional[List[UUID]] = None
    action_patterns: List[str] = field(default_factory=list)
    risk_threshold: Optional[float] = None

    # Routing target
    assign_to_user: Optional[UUID] = None
    assign_to_group: Optional[str] = None
    escalation_path: List[EscalationLevel] = field(default_factory=list)

    # Timing
    timeout_minutes: int = 60
    escalate_after_minutes: int = 30

    # Auto-approval
    auto_approve_if_low_risk: bool = False
    auto_approve_threshold: float = 0.3

    # Status
    enabled: bool = True
    priority: int = 0  # Higher priority routes are evaluated first


class ApprovalWorkflow:
    """
    Approval Workflow Manager.

    Manages human-in-the-loop approvals:
    - Create and route approval requests
    - Process approval decisions
    - Handle escalations
    - Track approval metrics
    """

    # Default timeouts by priority
    DEFAULT_TIMEOUTS = {
        ApprovalPriority.LOW: 120,  # 2 hours
        ApprovalPriority.MEDIUM: 60,  # 1 hour
        ApprovalPriority.HIGH: 30,  # 30 minutes
        ApprovalPriority.CRITICAL: 15,  # 15 minutes
    }

    # Default escalation paths
    DEFAULT_ESCALATION = {
        ApprovalPriority.LOW: [EscalationLevel.TEAM_LEAD],
        ApprovalPriority.MEDIUM: [EscalationLevel.TEAM_LEAD, EscalationLevel.MANAGER],
        ApprovalPriority.HIGH: [EscalationLevel.MANAGER, EscalationLevel.DIRECTOR],
        ApprovalPriority.CRITICAL: [EscalationLevel.DIRECTOR, EscalationLevel.EMERGENCY],
    }

    def __init__(self):
        """Initialize the approval workflow."""
        # Request storage
        self._requests: Dict[UUID, ApprovalRequest] = {}
        self._by_status: Dict[ApprovalStatus, List[UUID]] = {s: [] for s in ApprovalStatus}
        self._by_assignee: Dict[UUID, List[UUID]] = {}
        self._by_agent: Dict[UUID, List[UUID]] = {}

        # Routing rules
        self._routes: List[ApprovalRoute] = []

        # Callbacks
        self._on_request: List[Callable[[ApprovalRequest], None]] = []
        self._on_decision: List[Callable[[ApprovalRequest, ApprovalDecision], None]] = []
        self._on_escalation: List[Callable[[ApprovalRequest, EscalationLevel], None]] = []
        self._on_expiry: List[Callable[[ApprovalRequest], None]] = []

        # Waiting callbacks (for blocked agent runs)
        self._waiting: Dict[UUID, Callable[[ApprovalDecision], None]] = {}

    def add_route(self, route: ApprovalRoute) -> None:
        """Add a routing rule."""
        self._routes.append(route)
        self._routes.sort(key=lambda r: r.priority, reverse=True)
        logger.info(f"Added approval route: {route.name}")

    def remove_route(self, route_id: str) -> Optional[ApprovalRoute]:
        """Remove a routing rule."""
        for i, route in enumerate(self._routes):
            if route.id == route_id:
                return self._routes.pop(i)
        return None

    def create_request(
        self,
        agent_id: UUID,
        request_type: ApprovalType,
        title: str,
        description: str,
        action_type: str,
        action_details: Dict[str, Any],
        run_id: Optional[UUID] = None,
        tenant_id: Optional[UUID] = None,
        priority: Optional[ApprovalPriority] = None,
        risk_score: float = 0.5,
        risk_factors: Optional[List[str]] = None,
    ) -> ApprovalRequest:
        """
        Create a new approval request.

        Args:
            agent_id: Agent requesting approval
            request_type: Type of approval
            title: Request title
            description: Request description
            action_type: Type of action
            action_details: Action details
            run_id: Associated run ID
            tenant_id: Tenant ID
            priority: Request priority
            risk_score: Risk score (0-1)
            risk_factors: Risk factors

        Returns:
            Created approval request
        """
        # Auto-determine priority if not provided
        if priority is None:
            priority = self._assess_priority(risk_score, request_type)

        # Calculate expiry
        timeout = self.DEFAULT_TIMEOUTS.get(priority, 60)
        expires_at = datetime.utcnow() + timedelta(minutes=timeout)

        request = ApprovalRequest(
            agent_id=agent_id,
            run_id=run_id,
            tenant_id=tenant_id,
            request_type=request_type,
            priority=priority,
            title=title,
            description=description,
            action_type=action_type,
            action_details=action_details,
            status=ApprovalStatus.PENDING,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            risk_score=risk_score,
            risk_factors=risk_factors or [],
        )

        # Route the request
        self._route_request(request)

        # Check for auto-approval
        if self._check_auto_approve(request):
            self._auto_approve(request)
        else:
            # Store request
            self._store_request(request)

            # Notify callbacks
            for callback in self._on_request:
                try:
                    callback(request)
                except Exception as e:
                    logger.error(f"Request callback error: {e}")

        logger.info(f"Approval request created: {request.id} - {title}")
        return request

    async def wait_for_decision(
        self,
        request_id: UUID,
        timeout_seconds: Optional[int] = None,
    ) -> ApprovalDecision:
        """
        Wait for an approval decision (for blocking workflows).

        Args:
            request_id: Request to wait for
            timeout_seconds: Max wait time

        Returns:
            Approval decision
        """
        import asyncio

        request = self._requests.get(request_id)
        if not request:
            raise ValueError(f"Request not found: {request_id}")

        if request.decision:
            return request.decision

        # Create a future to wait on
        future: asyncio.Future = asyncio.Future()

        def callback(decision: ApprovalDecision):
            if not future.done():
                future.set_result(decision)

        self._waiting[request_id] = callback

        try:
            if timeout_seconds:
                decision = await asyncio.wait_for(future, timeout=timeout_seconds)
            else:
                decision = await future
            return decision
        except asyncio.TimeoutError:
            # Mark as expired
            self._expire_request(request)
            raise TimeoutError(f"Approval request timed out: {request_id}")
        finally:
            self._waiting.pop(request_id, None)

    def approve(
        self,
        request_id: UUID,
        approved_by: UUID,
        reason: Optional[str] = None,
        conditions: Optional[List[str]] = None,
        notes: Optional[str] = None,
    ) -> ApprovalDecision:
        """
        Approve a request.

        Args:
            request_id: Request to approve
            approved_by: Approving user
            reason: Approval reason
            conditions: Approval conditions
            notes: Additional notes

        Returns:
            Approval decision
        """
        return self._decide(
            request_id=request_id,
            decision=ApprovalStatus.APPROVED,
            decided_by=approved_by,
            reason=reason,
            conditions=conditions,
            notes=notes,
        )

    def reject(
        self,
        request_id: UUID,
        rejected_by: UUID,
        reason: str,
        notes: Optional[str] = None,
    ) -> ApprovalDecision:
        """
        Reject a request.

        Args:
            request_id: Request to reject
            rejected_by: Rejecting user
            reason: Rejection reason
            notes: Additional notes

        Returns:
            Approval decision
        """
        return self._decide(
            request_id=request_id,
            decision=ApprovalStatus.REJECTED,
            decided_by=rejected_by,
            reason=reason,
            notes=notes,
        )

    def escalate(
        self,
        request_id: UUID,
        escalated_by: Optional[UUID] = None,
        reason: Optional[str] = None,
    ) -> ApprovalRequest:
        """
        Escalate a request to the next level.

        Args:
            request_id: Request to escalate
            escalated_by: User escalating (None for auto)
            reason: Escalation reason

        Returns:
            Updated request
        """
        request = self._requests.get(request_id)
        if not request:
            raise ValueError(f"Request not found: {request_id}")

        # Determine next escalation level
        current_level = request.escalation_level
        escalation_path = self.DEFAULT_ESCALATION.get(request.priority, [])

        next_level = None
        for level in escalation_path:
            if self._escalation_order(level) > self._escalation_order(current_level):
                next_level = level
                break

        if not next_level:
            next_level = EscalationLevel.EMERGENCY

        # Record escalation
        request.escalation_history.append({
            "from_level": current_level.value,
            "to_level": next_level.value,
            "escalated_by": str(escalated_by) if escalated_by else "system",
            "reason": reason,
            "escalated_at": datetime.utcnow().isoformat(),
        })

        request.escalation_level = next_level
        request.status = ApprovalStatus.ESCALATED

        # Re-route for new level
        self._route_request(request)

        # Notify callbacks
        for callback in self._on_escalation:
            try:
                callback(request, next_level)
            except Exception as e:
                logger.error(f"Escalation callback error: {e}")

        logger.info(f"Request escalated: {request_id} to {next_level.value}")
        return request

    def cancel(
        self,
        request_id: UUID,
        cancelled_by: Optional[UUID] = None,
        reason: Optional[str] = None,
    ) -> ApprovalRequest:
        """
        Cancel a pending request.

        Args:
            request_id: Request to cancel
            cancelled_by: User cancelling
            reason: Cancellation reason

        Returns:
            Cancelled request
        """
        request = self._requests.get(request_id)
        if not request:
            raise ValueError(f"Request not found: {request_id}")

        if request.status != ApprovalStatus.PENDING:
            raise ValueError(f"Can only cancel pending requests")

        request.status = ApprovalStatus.CANCELLED
        request.decision = ApprovalDecision(
            request_id=request_id,
            decision=ApprovalStatus.CANCELLED,
            decided_by=cancelled_by,
            decided_at=datetime.utcnow(),
            reason=reason,
        )

        self._update_indexes(request)
        logger.info(f"Request cancelled: {request_id}")
        return request

    def get_request(self, request_id: UUID) -> Optional[ApprovalRequest]:
        """Get a request by ID."""
        return self._requests.get(request_id)

    def get_pending_requests(
        self,
        assignee: Optional[UUID] = None,
        group: Optional[str] = None,
        agent_id: Optional[UUID] = None,
        tenant_id: Optional[UUID] = None,
        limit: int = 100,
    ) -> List[ApprovalRequest]:
        """Get pending requests with optional filters."""
        request_ids = self._by_status.get(ApprovalStatus.PENDING, [])
        requests = []

        for rid in request_ids:
            request = self._requests.get(rid)
            if not request:
                continue

            if assignee and request.assigned_to != assignee:
                continue
            if group and request.assigned_group != group:
                continue
            if agent_id and request.agent_id != agent_id:
                continue
            if tenant_id and request.tenant_id != tenant_id:
                continue

            requests.append(request)
            if len(requests) >= limit:
                break

        # Sort by priority and creation time
        requests.sort(
            key=lambda r: (
                -self._priority_order(r.priority),
                r.created_at,
            )
        )
        return requests

    def get_stats(self, tenant_id: Optional[UUID] = None) -> Dict[str, Any]:
        """Get approval workflow statistics."""
        requests = list(self._requests.values())
        if tenant_id:
            requests = [r for r in requests if r.tenant_id == tenant_id]

        by_status = {}
        for status in ApprovalStatus:
            by_status[status.value] = sum(1 for r in requests if r.status == status)

        by_priority = {}
        for priority in ApprovalPriority:
            by_priority[priority.value] = sum(
                1 for r in requests
                if r.priority == priority and r.status == ApprovalStatus.PENDING
            )

        avg_decision_time = 0.0
        decided = [r for r in requests if r.decision and r.decision.decision_time_seconds]
        if decided:
            avg_decision_time = sum(r.decision.decision_time_seconds for r in decided) / len(decided)

        return {
            "total_requests": len(requests),
            "by_status": by_status,
            "pending_by_priority": by_priority,
            "avg_decision_time_seconds": avg_decision_time,
            "escalated_count": sum(1 for r in requests if r.escalation_level != EscalationLevel.NONE),
        }

    # Event registration
    def on_request(self, callback: Callable[[ApprovalRequest], None]) -> None:
        """Register callback for new requests."""
        self._on_request.append(callback)

    def on_decision(self, callback: Callable[[ApprovalRequest, ApprovalDecision], None]) -> None:
        """Register callback for decisions."""
        self._on_decision.append(callback)

    def on_escalation(self, callback: Callable[[ApprovalRequest, EscalationLevel], None]) -> None:
        """Register callback for escalations."""
        self._on_escalation.append(callback)

    def on_expiry(self, callback: Callable[[ApprovalRequest], None]) -> None:
        """Register callback for expired requests."""
        self._on_expiry.append(callback)

    # Private methods

    def _store_request(self, request: ApprovalRequest) -> None:
        """Store request and update indexes."""
        self._requests[request.id] = request
        self._by_status[request.status].append(request.id)

        if request.assigned_to:
            if request.assigned_to not in self._by_assignee:
                self._by_assignee[request.assigned_to] = []
            self._by_assignee[request.assigned_to].append(request.id)

        if request.agent_id not in self._by_agent:
            self._by_agent[request.agent_id] = []
        self._by_agent[request.agent_id].append(request.id)

    def _update_indexes(self, request: ApprovalRequest) -> None:
        """Update indexes after status change."""
        # Remove from old status lists
        for status, ids in self._by_status.items():
            if request.id in ids and status != request.status:
                ids.remove(request.id)

        # Add to current status
        if request.id not in self._by_status[request.status]:
            self._by_status[request.status].append(request.id)

    def _route_request(self, request: ApprovalRequest) -> None:
        """Route request to appropriate approver."""
        for route in self._routes:
            if not route.enabled:
                continue
            if self._matches_route(request, route):
                request.assigned_to = route.assign_to_user
                request.assigned_group = route.assign_to_group
                request.assigned_at = datetime.utcnow()

                # Update timeout based on route
                if route.timeout_minutes:
                    request.expires_at = datetime.utcnow() + timedelta(minutes=route.timeout_minutes)

                request.assignment_history.append({
                    "route_id": route.id,
                    "assigned_to": str(route.assign_to_user) if route.assign_to_user else None,
                    "assigned_group": route.assign_to_group,
                    "assigned_at": datetime.utcnow().isoformat(),
                })
                return

        # Default routing based on escalation level
        request.assigned_group = f"approvers_{request.escalation_level.value}"

    def _matches_route(self, request: ApprovalRequest, route: ApprovalRoute) -> bool:
        """Check if request matches routing rule."""
        if route.request_types and request.request_type not in route.request_types:
            return False
        if route.priority_levels and request.priority not in route.priority_levels:
            return False
        if route.agent_ids and request.agent_id not in route.agent_ids:
            return False
        if route.tenant_ids and request.tenant_id not in route.tenant_ids:
            return False
        if route.risk_threshold and request.risk_score < route.risk_threshold:
            return False

        if route.action_patterns:
            import fnmatch
            if not any(fnmatch.fnmatch(request.action_type, p) for p in route.action_patterns):
                return False

        return True

    def _check_auto_approve(self, request: ApprovalRequest) -> bool:
        """Check if request can be auto-approved."""
        if not request.auto_approve_eligible:
            return False

        for route in self._routes:
            if self._matches_route(request, route):
                if route.auto_approve_if_low_risk:
                    return request.risk_score <= route.auto_approve_threshold

        return False

    def _auto_approve(self, request: ApprovalRequest) -> None:
        """Auto-approve a request."""
        request.status = ApprovalStatus.AUTO_APPROVED
        request.decision = ApprovalDecision(
            request_id=request.id,
            decision=ApprovalStatus.APPROVED,
            decided_at=datetime.utcnow(),
            reason="Auto-approved based on low risk score",
            auto_decision=True,
        )
        request.decided_at = datetime.utcnow()
        self._store_request(request)
        logger.info(f"Request auto-approved: {request.id}")

    def _decide(
        self,
        request_id: UUID,
        decision: ApprovalStatus,
        decided_by: Optional[UUID],
        reason: Optional[str] = None,
        conditions: Optional[List[str]] = None,
        notes: Optional[str] = None,
    ) -> ApprovalDecision:
        """Record a decision on a request."""
        request = self._requests.get(request_id)
        if not request:
            raise ValueError(f"Request not found: {request_id}")

        if request.status not in [ApprovalStatus.PENDING, ApprovalStatus.ESCALATED]:
            raise ValueError(f"Request already decided: {request.status}")

        # Calculate decision time
        decision_time = (datetime.utcnow() - request.created_at).total_seconds()

        approval_decision = ApprovalDecision(
            request_id=request_id,
            decision=decision,
            decided_by=decided_by,
            decided_at=datetime.utcnow(),
            reason=reason,
            conditions=conditions or [],
            notes=notes,
            decision_time_seconds=decision_time,
        )

        request.decision = approval_decision
        request.status = decision
        request.decided_at = datetime.utcnow()

        self._update_indexes(request)

        # Notify callbacks
        for callback in self._on_decision:
            try:
                callback(request, approval_decision)
            except Exception as e:
                logger.error(f"Decision callback error: {e}")

        # Notify waiting callers
        if request_id in self._waiting:
            self._waiting[request_id](approval_decision)

        logger.info(f"Request decided: {request_id} - {decision.value}")
        return approval_decision

    def _expire_request(self, request: ApprovalRequest) -> None:
        """Mark request as expired."""
        request.status = ApprovalStatus.EXPIRED
        request.decision = ApprovalDecision(
            request_id=request.id,
            decision=ApprovalStatus.EXPIRED,
            decided_at=datetime.utcnow(),
            reason="Request expired",
            auto_decision=True,
        )

        self._update_indexes(request)

        for callback in self._on_expiry:
            try:
                callback(request)
            except Exception as e:
                logger.error(f"Expiry callback error: {e}")

    def _assess_priority(self, risk_score: float, request_type: ApprovalType) -> ApprovalPriority:
        """Assess priority based on risk and type."""
        if risk_score >= 0.8 or request_type == ApprovalType.DEPLOYMENT:
            return ApprovalPriority.CRITICAL
        if risk_score >= 0.6 or request_type == ApprovalType.POLICY_OVERRIDE:
            return ApprovalPriority.HIGH
        if risk_score >= 0.4:
            return ApprovalPriority.MEDIUM
        return ApprovalPriority.LOW

    def _priority_order(self, priority: ApprovalPriority) -> int:
        """Get numeric order for priority sorting."""
        return {
            ApprovalPriority.CRITICAL: 4,
            ApprovalPriority.HIGH: 3,
            ApprovalPriority.MEDIUM: 2,
            ApprovalPriority.LOW: 1,
        }.get(priority, 0)

    def _escalation_order(self, level: EscalationLevel) -> int:
        """Get numeric order for escalation levels."""
        return {
            EscalationLevel.NONE: 0,
            EscalationLevel.TEAM_LEAD: 1,
            EscalationLevel.MANAGER: 2,
            EscalationLevel.DIRECTOR: 3,
            EscalationLevel.EXECUTIVE: 4,
            EscalationLevel.EMERGENCY: 5,
        }.get(level, 0)


# Global instance
_approval_workflow: Optional[ApprovalWorkflow] = None


def get_approval_workflow() -> ApprovalWorkflow:
    """Get the global approval workflow instance."""
    global _approval_workflow
    if _approval_workflow is None:
        _approval_workflow = ApprovalWorkflow()
    return _approval_workflow
