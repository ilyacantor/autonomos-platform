"""
Arbitration

Conflict detection and resolution between agents.
Implements Coordination: Arbitration & conflict resolution from RACI.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID, uuid4

from .models import ConflictType, ResolutionStrategy

logger = logging.getLogger(__name__)


@dataclass
class Conflict:
    """A detected conflict between agents."""
    id: UUID = field(default_factory=uuid4)

    # Conflict details
    conflict_type: ConflictType = ConflictType.RESOURCE_CONTENTION
    description: str = ""
    severity: int = 5  # 1-10

    # Parties involved
    agent_ids: List[UUID] = field(default_factory=list)
    task_ids: List[UUID] = field(default_factory=list)
    resource_id: Optional[str] = None

    # Context
    context: Dict[str, Any] = field(default_factory=dict)
    detected_at: datetime = field(default_factory=datetime.utcnow)

    # Resolution
    resolved: bool = False
    resolution: Optional["Resolution"] = None
    resolved_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "conflict_type": self.conflict_type.value,
            "description": self.description,
            "severity": self.severity,
            "agent_ids": [str(a) for a in self.agent_ids],
            "task_ids": [str(t) for t in self.task_ids],
            "resource_id": self.resource_id,
            "resolved": self.resolved,
            "detected_at": self.detected_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }


@dataclass
class Resolution:
    """Resolution of a conflict."""
    id: UUID = field(default_factory=uuid4)
    conflict_id: UUID = field(default_factory=uuid4)

    # Resolution details
    strategy: ResolutionStrategy = ResolutionStrategy.PRIORITY_BASED
    decision: str = ""
    reasoning: str = ""

    # Outcome
    winner_agent_id: Optional[UUID] = None
    actions_taken: List[Dict[str, Any]] = field(default_factory=list)

    # Audit
    resolved_by: str = "system"  # system or user_id
    resolved_at: datetime = field(default_factory=datetime.utcnow)

    # Impact
    tasks_affected: List[UUID] = field(default_factory=list)
    tasks_cancelled: List[UUID] = field(default_factory=list)
    tasks_delayed: List[UUID] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "conflict_id": str(self.conflict_id),
            "strategy": self.strategy.value,
            "decision": self.decision,
            "reasoning": self.reasoning,
            "winner_agent_id": str(self.winner_agent_id) if self.winner_agent_id else None,
            "resolved_by": self.resolved_by,
            "resolved_at": self.resolved_at.isoformat(),
            "tasks_affected": [str(t) for t in self.tasks_affected],
        }


class Arbitrator:
    """
    Conflict Arbitrator.

    Detects and resolves conflicts between agents:
    - Resource contention
    - Data conflicts
    - Priority conflicts
    - Deadlock detection
    """

    def __init__(self):
        """Initialize the arbitrator."""
        # Conflict storage
        self._conflicts: Dict[UUID, Conflict] = {}
        self._resolutions: Dict[UUID, Resolution] = {}

        # Active locks/claims
        self._resource_locks: Dict[str, UUID] = {}  # resource_id -> agent_id
        self._pending_claims: Dict[str, List[UUID]] = {}  # resource_id -> [agent_ids]

        # Strategy handlers
        self._strategy_handlers: Dict[ResolutionStrategy, Callable] = {
            ResolutionStrategy.PRIORITY_BASED: self._resolve_by_priority,
            ResolutionStrategy.FIRST_COME: self._resolve_first_come,
            ResolutionStrategy.ROUND_ROBIN: self._resolve_round_robin,
            ResolutionStrategy.ABORT: self._resolve_abort,
            ResolutionStrategy.DEFER: self._resolve_defer,
        }

        # Round robin state
        self._round_robin_index: Dict[str, int] = {}

        # Agent priorities (can be configured)
        self._agent_priorities: Dict[UUID, int] = {}

        # Callbacks
        self._on_conflict: List[Callable[[Conflict], None]] = []
        self._on_resolution: List[Callable[[Conflict, Resolution], None]] = []

    def set_agent_priority(self, agent_id: UUID, priority: int) -> None:
        """Set priority for an agent (higher = more important)."""
        self._agent_priorities[agent_id] = priority

    def acquire_resource(
        self,
        resource_id: str,
        agent_id: UUID,
        task_id: Optional[UUID] = None,
        wait: bool = False,
    ) -> bool:
        """
        Attempt to acquire a resource lock.

        Args:
            resource_id: Resource to acquire
            agent_id: Agent acquiring
            task_id: Associated task
            wait: Whether to wait if locked

        Returns:
            True if acquired, False if conflict
        """
        current_holder = self._resource_locks.get(resource_id)

        if current_holder is None:
            # Resource is free
            self._resource_locks[resource_id] = agent_id
            logger.debug(f"Agent {agent_id} acquired resource {resource_id}")
            return True

        if current_holder == agent_id:
            # Already holding
            return True

        # Conflict detected
        conflict = Conflict(
            conflict_type=ConflictType.RESOURCE_CONTENTION,
            description=f"Resource {resource_id} contention",
            agent_ids=[current_holder, agent_id],
            task_ids=[task_id] if task_id else [],
            resource_id=resource_id,
            context={"current_holder": str(current_holder)},
        )

        self._conflicts[conflict.id] = conflict

        # Notify callbacks
        for callback in self._on_conflict:
            try:
                callback(conflict)
            except Exception as e:
                logger.error(f"Conflict callback error: {e}")

        if wait:
            # Add to pending claims
            if resource_id not in self._pending_claims:
                self._pending_claims[resource_id] = []
            self._pending_claims[resource_id].append(agent_id)

        logger.info(f"Resource conflict detected: {resource_id}")
        return False

    def release_resource(self, resource_id: str, agent_id: UUID) -> None:
        """
        Release a resource lock.

        Args:
            resource_id: Resource to release
            agent_id: Agent releasing
        """
        current_holder = self._resource_locks.get(resource_id)

        if current_holder == agent_id:
            del self._resource_locks[resource_id]
            logger.debug(f"Agent {agent_id} released resource {resource_id}")

            # Check for pending claims
            if resource_id in self._pending_claims and self._pending_claims[resource_id]:
                next_agent = self._pending_claims[resource_id].pop(0)
                self._resource_locks[resource_id] = next_agent
                logger.info(f"Resource {resource_id} transferred to waiting agent {next_agent}")

    def detect_conflict(
        self,
        conflict_type: ConflictType,
        agent_ids: List[UUID],
        description: str,
        task_ids: Optional[List[UUID]] = None,
        resource_id: Optional[str] = None,
        severity: int = 5,
        context: Optional[Dict[str, Any]] = None,
    ) -> Conflict:
        """
        Manually detect/report a conflict.

        Args:
            conflict_type: Type of conflict
            agent_ids: Agents involved
            description: Conflict description
            task_ids: Tasks involved
            resource_id: Resource involved
            severity: Conflict severity
            context: Additional context

        Returns:
            Created conflict
        """
        conflict = Conflict(
            conflict_type=conflict_type,
            description=description,
            severity=severity,
            agent_ids=agent_ids,
            task_ids=task_ids or [],
            resource_id=resource_id,
            context=context or {},
        )

        self._conflicts[conflict.id] = conflict

        # Notify callbacks
        for callback in self._on_conflict:
            try:
                callback(conflict)
            except Exception as e:
                logger.error(f"Conflict callback error: {e}")

        logger.info(f"Conflict detected: {conflict_type.value} - {description}")
        return conflict

    def resolve(
        self,
        conflict_id: UUID,
        strategy: Optional[ResolutionStrategy] = None,
        manual_decision: Optional[str] = None,
        resolved_by: str = "system",
    ) -> Resolution:
        """
        Resolve a conflict.

        Args:
            conflict_id: Conflict to resolve
            strategy: Resolution strategy
            manual_decision: Manual resolution decision
            resolved_by: Who resolved it

        Returns:
            Resolution record
        """
        conflict = self._conflicts.get(conflict_id)
        if not conflict:
            raise ValueError(f"Conflict not found: {conflict_id}")

        if conflict.resolved:
            raise ValueError(f"Conflict already resolved: {conflict_id}")

        # Determine strategy
        if strategy is None:
            strategy = self._select_strategy(conflict)

        # Apply strategy
        handler = self._strategy_handlers.get(strategy)
        if handler and not manual_decision:
            resolution = handler(conflict)
        else:
            resolution = Resolution(
                conflict_id=conflict_id,
                strategy=strategy,
                decision=manual_decision or "Manual resolution",
                reasoning="Manually resolved",
                resolved_by=resolved_by,
            )

        # Update conflict
        conflict.resolved = True
        conflict.resolution = resolution
        conflict.resolved_at = datetime.utcnow()

        # Store resolution
        self._resolutions[resolution.id] = resolution

        # Notify callbacks
        for callback in self._on_resolution:
            try:
                callback(conflict, resolution)
            except Exception as e:
                logger.error(f"Resolution callback error: {e}")

        logger.info(f"Conflict resolved: {conflict_id} using {strategy.value}")
        return resolution

    def get_conflict(self, conflict_id: UUID) -> Optional[Conflict]:
        """Get a conflict by ID."""
        return self._conflicts.get(conflict_id)

    def get_active_conflicts(
        self,
        agent_id: Optional[UUID] = None,
        conflict_type: Optional[ConflictType] = None,
    ) -> List[Conflict]:
        """Get active (unresolved) conflicts."""
        conflicts = [c for c in self._conflicts.values() if not c.resolved]

        if agent_id:
            conflicts = [c for c in conflicts if agent_id in c.agent_ids]
        if conflict_type:
            conflicts = [c for c in conflicts if c.conflict_type == conflict_type]

        return conflicts

    def get_locked_resources(self, agent_id: Optional[UUID] = None) -> Dict[str, UUID]:
        """Get currently locked resources."""
        if agent_id:
            return {k: v for k, v in self._resource_locks.items() if v == agent_id}
        return self._resource_locks.copy()

    def get_stats(self) -> Dict[str, Any]:
        """Get arbitration statistics."""
        conflicts = list(self._conflicts.values())
        resolved = [c for c in conflicts if c.resolved]

        by_type = {}
        for ct in ConflictType:
            by_type[ct.value] = sum(1 for c in conflicts if c.conflict_type == ct)

        by_strategy = {}
        for r in self._resolutions.values():
            by_strategy[r.strategy.value] = by_strategy.get(r.strategy.value, 0) + 1

        return {
            "total_conflicts": len(conflicts),
            "resolved_conflicts": len(resolved),
            "active_conflicts": len(conflicts) - len(resolved),
            "by_type": by_type,
            "by_strategy": by_strategy,
            "active_locks": len(self._resource_locks),
            "pending_claims": sum(len(v) for v in self._pending_claims.values()),
        }

    # Event registration
    def on_conflict(self, callback: Callable[[Conflict], None]) -> None:
        """Register callback for conflict detection."""
        self._on_conflict.append(callback)

    def on_resolution(self, callback: Callable[[Conflict, Resolution], None]) -> None:
        """Register callback for conflict resolution."""
        self._on_resolution.append(callback)

    # Private methods

    def _select_strategy(self, conflict: Conflict) -> ResolutionStrategy:
        """Select appropriate resolution strategy."""
        # High severity conflicts should be escalated
        if conflict.severity >= 8:
            return ResolutionStrategy.ESCALATE

        # Resource contention uses priority
        if conflict.conflict_type == ConflictType.RESOURCE_CONTENTION:
            return ResolutionStrategy.PRIORITY_BASED

        # Deadlocks should be aborted
        if conflict.conflict_type == ConflictType.DEADLOCK:
            return ResolutionStrategy.ABORT

        # Default to priority
        return ResolutionStrategy.PRIORITY_BASED

    def _resolve_by_priority(self, conflict: Conflict) -> Resolution:
        """Resolve conflict by agent priority."""
        # Get priorities for involved agents
        agent_priorities = [
            (aid, self._agent_priorities.get(aid, 5))
            for aid in conflict.agent_ids
        ]

        # Sort by priority (higher first)
        agent_priorities.sort(key=lambda x: x[1], reverse=True)
        winner = agent_priorities[0][0]

        return Resolution(
            conflict_id=conflict.id,
            strategy=ResolutionStrategy.PRIORITY_BASED,
            decision=f"Agent {winner} wins by priority",
            reasoning=f"Priority comparison: {agent_priorities}",
            winner_agent_id=winner,
        )

    def _resolve_first_come(self, conflict: Conflict) -> Resolution:
        """Resolve conflict by first-come-first-served."""
        # First agent in list is assumed to be first
        winner = conflict.agent_ids[0] if conflict.agent_ids else None

        return Resolution(
            conflict_id=conflict.id,
            strategy=ResolutionStrategy.FIRST_COME,
            decision=f"Agent {winner} wins by first-come",
            reasoning="First request takes precedence",
            winner_agent_id=winner,
        )

    def _resolve_round_robin(self, conflict: Conflict) -> Resolution:
        """Resolve conflict by round-robin."""
        resource_id = conflict.resource_id or "default"

        # Get or initialize index
        index = self._round_robin_index.get(resource_id, 0)

        # Select winner
        if conflict.agent_ids:
            winner_idx = index % len(conflict.agent_ids)
            winner = conflict.agent_ids[winner_idx]
            self._round_robin_index[resource_id] = index + 1
        else:
            winner = None

        return Resolution(
            conflict_id=conflict.id,
            strategy=ResolutionStrategy.ROUND_ROBIN,
            decision=f"Agent {winner} wins by round-robin",
            reasoning=f"Round-robin index: {index}",
            winner_agent_id=winner,
        )

    def _resolve_abort(self, conflict: Conflict) -> Resolution:
        """Resolve conflict by aborting all operations."""
        return Resolution(
            conflict_id=conflict.id,
            strategy=ResolutionStrategy.ABORT,
            decision="All conflicting operations aborted",
            reasoning="Conflict cannot be resolved, operations cancelled",
            tasks_cancelled=conflict.task_ids.copy(),
        )

    def _resolve_defer(self, conflict: Conflict) -> Resolution:
        """Defer conflict resolution."""
        return Resolution(
            conflict_id=conflict.id,
            strategy=ResolutionStrategy.DEFER,
            decision="Resolution deferred",
            reasoning="Conflict resolution delayed for later review",
            tasks_delayed=conflict.task_ids.copy(),
        )


# Global instance
_arbitrator: Optional[Arbitrator] = None


def get_arbitrator() -> Arbitrator:
    """Get the global arbitrator instance."""
    global _arbitrator
    if _arbitrator is None:
        _arbitrator = Arbitrator()
    return _arbitrator
