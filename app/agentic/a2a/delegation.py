"""
Agent Delegation Protocol

Enables agents to delegate tasks to other agents:
- Task handoff with context preservation
- Delegation tracking and status
- Result aggregation
- Failure handling
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID, uuid4

from .agent_card import AgentCard
from .discovery import AgentDiscovery, get_agent_discovery

logger = logging.getLogger(__name__)


class DelegationStatus(str, Enum):
    """Status of a delegation request."""
    PENDING = "pending"           # Waiting for delegatee to accept
    ACCEPTED = "accepted"         # Delegatee accepted the task
    REJECTED = "rejected"         # Delegatee rejected the task
    IN_PROGRESS = "in_progress"   # Task is being executed
    COMPLETED = "completed"       # Task completed successfully
    FAILED = "failed"             # Task failed
    CANCELLED = "cancelled"       # Delegation was cancelled
    TIMEOUT = "timeout"           # Delegation timed out


class DelegationType(str, Enum):
    """Type of delegation."""
    FULL = "full"           # Complete handoff, delegator waits for result
    PARTIAL = "partial"     # Delegator continues, merges result later
    ASYNC = "async"         # Fire and forget, no result expected
    PARALLEL = "parallel"   # Multiple delegatees work in parallel


@dataclass
class DelegationContext:
    """Context passed to the delegatee."""
    # Original request
    original_input: str
    original_context: Dict[str, Any] = field(default_factory=dict)

    # Delegation-specific
    delegation_reason: Optional[str] = None
    delegated_capability: Optional[str] = None

    # Constraints
    max_steps: Optional[int] = None
    max_cost_usd: Optional[float] = None
    timeout_seconds: int = 300

    # History (for chain of delegations)
    delegation_chain: List[str] = field(default_factory=list)

    # Shared memory/state
    shared_state: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_input": self.original_input,
            "original_context": self.original_context,
            "delegation_reason": self.delegation_reason,
            "delegated_capability": self.delegated_capability,
            "max_steps": self.max_steps,
            "max_cost_usd": self.max_cost_usd,
            "timeout_seconds": self.timeout_seconds,
            "delegation_chain": self.delegation_chain,
            "shared_state": self.shared_state,
        }


@dataclass
class DelegationRequest:
    """A request to delegate work to another agent."""
    id: str = field(default_factory=lambda: str(uuid4()))

    # Parties
    delegator_id: str = ""
    delegatee_id: str = ""

    # Task
    task_input: str = ""
    capability_id: Optional[str] = None
    context: DelegationContext = field(default_factory=DelegationContext)

    # Type and constraints
    delegation_type: DelegationType = DelegationType.FULL
    priority: int = 5  # 1-10, higher = more urgent
    timeout_at: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(minutes=5))

    # Status
    status: DelegationStatus = DelegationStatus.PENDING
    status_message: Optional[str] = None

    # Timing
    created_at: datetime = field(default_factory=datetime.utcnow)
    accepted_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Result
    result: Optional[Any] = None
    error: Optional[str] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if the delegation request has expired."""
        return datetime.utcnow() > self.timeout_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "delegator_id": self.delegator_id,
            "delegatee_id": self.delegatee_id,
            "task_input": self.task_input,
            "capability_id": self.capability_id,
            "context": self.context.to_dict(),
            "delegation_type": self.delegation_type.value,
            "priority": self.priority,
            "timeout_at": self.timeout_at.isoformat(),
            "status": self.status.value,
            "status_message": self.status_message,
            "created_at": self.created_at.isoformat(),
            "accepted_at": self.accepted_at.isoformat() if self.accepted_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error": self.error,
        }


@dataclass
class DelegationResponse:
    """Response from a delegation request."""
    request_id: str
    status: DelegationStatus
    result: Optional[Any] = None
    error: Optional[str] = None

    # Metrics
    tokens_used: int = 0
    cost_usd: float = 0.0
    steps_executed: int = 0
    duration_ms: int = 0

    # Additional output
    output_context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "tokens_used": self.tokens_used,
            "cost_usd": self.cost_usd,
            "steps_executed": self.steps_executed,
            "duration_ms": self.duration_ms,
            "output_context": self.output_context,
        }


class DelegationManager:
    """
    Manages agent-to-agent delegation.

    Handles:
    - Creating delegation requests
    - Routing to appropriate delegatees
    - Tracking delegation status
    - Aggregating results
    """

    def __init__(self, discovery: Optional[AgentDiscovery] = None):
        """Initialize the delegation manager."""
        self.discovery = discovery or get_agent_discovery()

        # Active delegations
        self._delegations: Dict[str, DelegationRequest] = {}
        self._by_delegator: Dict[str, List[str]] = {}
        self._by_delegatee: Dict[str, List[str]] = {}

        # Callbacks
        self._on_delegation_created: List[Callable] = []
        self._on_delegation_accepted: List[Callable] = []
        self._on_delegation_completed: List[Callable] = []
        self._on_delegation_failed: List[Callable] = []

        # Execution handlers (registered by agent runtime)
        self._execution_handlers: Dict[str, Callable] = {}

    def register_execution_handler(
        self,
        agent_id: str,
        handler: Callable[[DelegationRequest], DelegationResponse],
    ) -> None:
        """
        Register an execution handler for an agent.

        The handler will be called when the agent receives a delegation.
        """
        self._execution_handlers[agent_id] = handler

    async def delegate(
        self,
        delegator_id: str,
        task_input: str,
        capability_id: Optional[str] = None,
        delegatee_id: Optional[str] = None,
        context: Optional[DelegationContext] = None,
        delegation_type: DelegationType = DelegationType.FULL,
        priority: int = 5,
        timeout_seconds: int = 300,
    ) -> DelegationRequest:
        """
        Create a delegation request.

        Args:
            delegator_id: Agent delegating the task
            task_input: Task to delegate
            capability_id: Specific capability required
            delegatee_id: Specific agent to delegate to (auto-selects if None)
            context: Delegation context
            delegation_type: Type of delegation
            priority: Priority level (1-10)
            timeout_seconds: Timeout for the delegation

        Returns:
            Created DelegationRequest
        """
        # Get delegator card
        delegator = self.discovery.get(delegator_id)
        if not delegator:
            raise ValueError(f"Delegator {delegator_id} not found")

        # Find delegatee if not specified
        if not delegatee_id:
            if capability_id:
                candidates = self.discovery.find_delegatees(
                    capability_id=capability_id,
                    excluding=delegator_id,
                    tenant_id=delegator.tenant_id,
                )
            else:
                # Find any available agent
                candidates = self.discovery.find_delegatees(
                    capability_id="execute",
                    excluding=delegator_id,
                    tenant_id=delegator.tenant_id,
                )

            if not candidates:
                raise ValueError("No suitable delegatee found")

            # Select best candidate (highest trust)
            delegatee_id = candidates[0].id

        # Create context if not provided
        if context is None:
            context = DelegationContext(
                original_input=task_input,
                delegated_capability=capability_id,
            )

        # Add to delegation chain
        context.delegation_chain.append(delegator_id)

        # Create request
        request = DelegationRequest(
            delegator_id=delegator_id,
            delegatee_id=delegatee_id,
            task_input=task_input,
            capability_id=capability_id,
            context=context,
            delegation_type=delegation_type,
            priority=priority,
            timeout_at=datetime.utcnow() + timedelta(seconds=timeout_seconds),
        )

        # Store request
        self._delegations[request.id] = request

        if delegator_id not in self._by_delegator:
            self._by_delegator[delegator_id] = []
        self._by_delegator[delegator_id].append(request.id)

        if delegatee_id not in self._by_delegatee:
            self._by_delegatee[delegatee_id] = []
        self._by_delegatee[delegatee_id].append(request.id)

        logger.info(
            f"Delegation created: {request.id} "
            f"({delegator_id} -> {delegatee_id}, capability: {capability_id})"
        )

        # Notify callbacks
        for callback in self._on_delegation_created:
            try:
                await self._safe_callback(callback, request)
            except Exception as e:
                logger.error(f"Delegation created callback error: {e}")

        # Auto-execute if handler is registered
        if delegatee_id in self._execution_handlers:
            asyncio.create_task(self._execute_delegation(request))

        return request

    async def accept_delegation(
        self,
        request_id: str,
        delegatee_id: str,
    ) -> DelegationRequest:
        """
        Accept a delegation request.

        Args:
            request_id: Delegation to accept
            delegatee_id: Agent accepting the delegation

        Returns:
            Updated DelegationRequest
        """
        request = self._delegations.get(request_id)
        if not request:
            raise ValueError(f"Delegation {request_id} not found")

        if request.delegatee_id != delegatee_id:
            raise ValueError("Only the assigned delegatee can accept")

        if request.status != DelegationStatus.PENDING:
            raise ValueError(f"Cannot accept delegation in status: {request.status.value}")

        if request.is_expired():
            request.status = DelegationStatus.TIMEOUT
            raise ValueError("Delegation has expired")

        request.status = DelegationStatus.ACCEPTED
        request.accepted_at = datetime.utcnow()

        logger.info(f"Delegation {request_id} accepted by {delegatee_id}")

        # Notify callbacks
        for callback in self._on_delegation_accepted:
            try:
                await self._safe_callback(callback, request)
            except Exception as e:
                logger.error(f"Delegation accepted callback error: {e}")

        return request

    async def reject_delegation(
        self,
        request_id: str,
        delegatee_id: str,
        reason: Optional[str] = None,
    ) -> DelegationRequest:
        """
        Reject a delegation request.

        Args:
            request_id: Delegation to reject
            delegatee_id: Agent rejecting the delegation
            reason: Reason for rejection

        Returns:
            Updated DelegationRequest
        """
        request = self._delegations.get(request_id)
        if not request:
            raise ValueError(f"Delegation {request_id} not found")

        if request.delegatee_id != delegatee_id:
            raise ValueError("Only the assigned delegatee can reject")

        request.status = DelegationStatus.REJECTED
        request.status_message = reason
        request.completed_at = datetime.utcnow()

        logger.info(f"Delegation {request_id} rejected by {delegatee_id}: {reason}")

        return request

    async def complete_delegation(
        self,
        request_id: str,
        response: DelegationResponse,
    ) -> DelegationRequest:
        """
        Complete a delegation with results.

        Args:
            request_id: Delegation to complete
            response: Delegation response with results

        Returns:
            Updated DelegationRequest
        """
        request = self._delegations.get(request_id)
        if not request:
            raise ValueError(f"Delegation {request_id} not found")

        request.status = response.status
        request.result = response.result
        request.error = response.error
        request.completed_at = datetime.utcnow()

        if response.status == DelegationStatus.COMPLETED:
            logger.info(f"Delegation {request_id} completed successfully")
            for callback in self._on_delegation_completed:
                try:
                    await self._safe_callback(callback, request, response)
                except Exception as e:
                    logger.error(f"Delegation completed callback error: {e}")
        else:
            logger.warning(f"Delegation {request_id} failed: {response.error}")
            for callback in self._on_delegation_failed:
                try:
                    await self._safe_callback(callback, request, response)
                except Exception as e:
                    logger.error(f"Delegation failed callback error: {e}")

        return request

    async def _execute_delegation(self, request: DelegationRequest) -> None:
        """Execute a delegation using the registered handler."""
        handler = self._execution_handlers.get(request.delegatee_id)
        if not handler:
            return

        try:
            # Accept the delegation
            await self.accept_delegation(request.id, request.delegatee_id)

            # Mark as in progress
            request.status = DelegationStatus.IN_PROGRESS
            request.started_at = datetime.utcnow()

            # Execute
            if asyncio.iscoroutinefunction(handler):
                response = await handler(request)
            else:
                response = handler(request)

            # Complete
            await self.complete_delegation(request.id, response)

        except Exception as e:
            logger.error(f"Delegation execution error: {e}")
            response = DelegationResponse(
                request_id=request.id,
                status=DelegationStatus.FAILED,
                error=str(e),
            )
            await self.complete_delegation(request.id, response)

    def get_delegation(self, request_id: str) -> Optional[DelegationRequest]:
        """Get a delegation by ID."""
        return self._delegations.get(request_id)

    def get_delegator_requests(
        self,
        delegator_id: str,
        status: Optional[DelegationStatus] = None,
    ) -> List[DelegationRequest]:
        """Get all delegations made by an agent."""
        request_ids = self._by_delegator.get(delegator_id, [])
        requests = [self._delegations[rid] for rid in request_ids if rid in self._delegations]

        if status:
            requests = [r for r in requests if r.status == status]

        return requests

    def get_delegatee_requests(
        self,
        delegatee_id: str,
        status: Optional[DelegationStatus] = None,
    ) -> List[DelegationRequest]:
        """Get all delegations received by an agent."""
        request_ids = self._by_delegatee.get(delegatee_id, [])
        requests = [self._delegations[rid] for rid in request_ids if rid in self._delegations]

        if status:
            requests = [r for r in requests if r.status == status]

        return requests

    async def cancel_delegation(
        self,
        request_id: str,
        reason: Optional[str] = None,
    ) -> DelegationRequest:
        """Cancel a delegation request."""
        request = self._delegations.get(request_id)
        if not request:
            raise ValueError(f"Delegation {request_id} not found")

        if request.status in (DelegationStatus.COMPLETED, DelegationStatus.FAILED):
            raise ValueError(f"Cannot cancel delegation in status: {request.status.value}")

        request.status = DelegationStatus.CANCELLED
        request.status_message = reason
        request.completed_at = datetime.utcnow()

        logger.info(f"Delegation {request_id} cancelled: {reason}")

        return request

    async def _safe_callback(self, callback: Callable, *args) -> None:
        """Safely execute a callback."""
        if asyncio.iscoroutinefunction(callback):
            await callback(*args)
        else:
            callback(*args)

    def on_delegation_created(self, callback: Callable) -> None:
        """Register callback for delegation creation."""
        self._on_delegation_created.append(callback)

    def on_delegation_accepted(self, callback: Callable) -> None:
        """Register callback for delegation acceptance."""
        self._on_delegation_accepted.append(callback)

    def on_delegation_completed(self, callback: Callable) -> None:
        """Register callback for successful delegation completion."""
        self._on_delegation_completed.append(callback)

    def on_delegation_failed(self, callback: Callable) -> None:
        """Register callback for delegation failure."""
        self._on_delegation_failed.append(callback)

    def get_statistics(self) -> Dict[str, Any]:
        """Get delegation statistics."""
        status_counts = {s: 0 for s in DelegationStatus}
        for req in self._delegations.values():
            status_counts[req.status] += 1

        return {
            "total_delegations": len(self._delegations),
            "by_status": {s.value: c for s, c in status_counts.items()},
            "active_delegators": len(self._by_delegator),
            "active_delegatees": len(self._by_delegatee),
        }


# Global delegation manager instance
_delegation_manager: Optional[DelegationManager] = None


def get_delegation_manager() -> DelegationManager:
    """Get the global delegation manager instance."""
    global _delegation_manager
    if _delegation_manager is None:
        _delegation_manager = DelegationManager()
    return _delegation_manager
