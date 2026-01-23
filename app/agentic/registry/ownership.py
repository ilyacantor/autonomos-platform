"""
Agent Ownership Manager

Handles agent ownership tracking and transfers.
Implements Agent Registry: Agent metadata & ownership from RACI.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID, uuid4

from .models import AgentOwnership, AgentRecord

logger = logging.getLogger(__name__)


@dataclass
class OwnershipTransfer:
    """Record of an ownership transfer."""
    id: UUID = field(default_factory=uuid4)
    agent_id: UUID = field(default_factory=uuid4)
    agent_name: str = ""

    from_owner_id: UUID = field(default_factory=uuid4)
    from_owner_type: str = ""
    from_owner_name: str = ""

    to_owner_id: UUID = field(default_factory=uuid4)
    to_owner_type: str = ""
    to_owner_name: str = ""

    transferred_at: datetime = field(default_factory=datetime.utcnow)
    transferred_by: Optional[UUID] = None
    reason: Optional[str] = None

    # Status
    status: str = "completed"  # pending, completed, rejected, reverted
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "agent_id": str(self.agent_id),
            "agent_name": self.agent_name,
            "from_owner": {
                "id": str(self.from_owner_id),
                "type": self.from_owner_type,
                "name": self.from_owner_name,
            },
            "to_owner": {
                "id": str(self.to_owner_id),
                "type": self.to_owner_type,
                "name": self.to_owner_name,
            },
            "transferred_at": self.transferred_at.isoformat(),
            "transferred_by": str(self.transferred_by) if self.transferred_by else None,
            "reason": self.reason,
            "status": self.status,
        }


class OwnershipManager:
    """
    Manages agent ownership and transfers.

    Features:
    - Track current ownership
    - Process ownership transfers
    - Maintain transfer history
    - Support pending/approval workflows
    """

    def __init__(self):
        """Initialize the ownership manager."""
        # Transfer history
        self._transfers: Dict[UUID, OwnershipTransfer] = {}
        self._by_agent: Dict[UUID, List[UUID]] = {}
        self._pending_transfers: Dict[UUID, OwnershipTransfer] = {}

        # Callbacks
        self._on_transfer: List[Callable[[OwnershipTransfer], None]] = []
        self._on_transfer_request: List[Callable[[OwnershipTransfer], None]] = []

    def transfer(
        self,
        record: AgentRecord,
        to_owner_id: UUID,
        to_owner_type: str,
        to_owner_name: str,
        transferred_by: Optional[UUID] = None,
        reason: Optional[str] = None,
        require_approval: bool = False,
    ) -> OwnershipTransfer:
        """
        Transfer ownership of an agent.

        Args:
            record: Agent record to transfer
            to_owner_id: New owner ID
            to_owner_type: New owner type (user, team, organization)
            to_owner_name: New owner name
            transferred_by: User initiating transfer
            reason: Reason for transfer
            require_approval: Whether transfer requires approval

        Returns:
            OwnershipTransfer record
        """
        # Create transfer record
        transfer = OwnershipTransfer(
            agent_id=record.id,
            agent_name=record.name,
            from_owner_id=record.ownership.owner_id,
            from_owner_type=record.ownership.owner_type,
            from_owner_name=record.ownership.owner_name,
            to_owner_id=to_owner_id,
            to_owner_type=to_owner_type,
            to_owner_name=to_owner_name,
            transferred_by=transferred_by,
            reason=reason,
            status="pending" if require_approval else "completed",
        )

        if require_approval:
            # Store as pending
            self._pending_transfers[transfer.id] = transfer

            # Notify callbacks
            for callback in self._on_transfer_request:
                try:
                    callback(transfer)
                except Exception as e:
                    logger.error(f"Transfer request callback error: {e}")

            logger.info(f"Ownership transfer requested for {record.name}: pending approval")
        else:
            # Execute transfer immediately
            self._execute_transfer(record, transfer)

        return transfer

    def approve_transfer(
        self,
        transfer_id: UUID,
        approved_by: UUID,
        agent_record: AgentRecord,
    ) -> Optional[OwnershipTransfer]:
        """
        Approve a pending ownership transfer.

        Args:
            transfer_id: Transfer to approve
            approved_by: User approving
            agent_record: Current agent record

        Returns:
            Completed transfer or None if not found
        """
        transfer = self._pending_transfers.pop(transfer_id, None)
        if not transfer:
            logger.warning(f"Transfer not found: {transfer_id}")
            return None

        transfer.status = "completed"
        transfer.approved_by = approved_by
        transfer.approved_at = datetime.utcnow()

        self._execute_transfer(agent_record, transfer)
        return transfer

    def reject_transfer(
        self,
        transfer_id: UUID,
        rejected_by: UUID,
        reason: Optional[str] = None,
    ) -> Optional[OwnershipTransfer]:
        """
        Reject a pending ownership transfer.

        Args:
            transfer_id: Transfer to reject
            rejected_by: User rejecting
            reason: Rejection reason

        Returns:
            Rejected transfer or None if not found
        """
        transfer = self._pending_transfers.pop(transfer_id, None)
        if not transfer:
            logger.warning(f"Transfer not found: {transfer_id}")
            return None

        transfer.status = "rejected"
        transfer.approved_by = rejected_by
        transfer.approved_at = datetime.utcnow()
        if reason:
            transfer.reason = f"{transfer.reason or ''} | Rejected: {reason}"

        # Store in history
        self._transfers[transfer.id] = transfer

        logger.info(f"Ownership transfer rejected for agent {transfer.agent_id}")
        return transfer

    def get_transfer(self, transfer_id: UUID) -> Optional[OwnershipTransfer]:
        """Get a transfer record by ID."""
        transfer = self._transfers.get(transfer_id)
        if not transfer:
            transfer = self._pending_transfers.get(transfer_id)
        return transfer

    def get_pending_transfers(
        self,
        agent_id: Optional[UUID] = None,
        to_owner_id: Optional[UUID] = None,
    ) -> List[OwnershipTransfer]:
        """Get pending transfers, optionally filtered."""
        transfers = list(self._pending_transfers.values())

        if agent_id:
            transfers = [t for t in transfers if t.agent_id == agent_id]
        if to_owner_id:
            transfers = [t for t in transfers if t.to_owner_id == to_owner_id]

        return transfers

    def get_transfer_history(
        self,
        agent_id: Optional[UUID] = None,
        owner_id: Optional[UUID] = None,
        limit: int = 100,
    ) -> List[OwnershipTransfer]:
        """
        Get transfer history.

        Args:
            agent_id: Filter by agent
            owner_id: Filter by owner (from or to)
            limit: Maximum records to return

        Returns:
            List of transfers sorted by date descending
        """
        transfers = list(self._transfers.values())

        if agent_id:
            transfers = [t for t in transfers if t.agent_id == agent_id]
        if owner_id:
            transfers = [
                t for t in transfers
                if t.from_owner_id == owner_id or t.to_owner_id == owner_id
            ]

        # Sort by date descending
        transfers.sort(key=lambda t: t.transferred_at, reverse=True)
        return transfers[:limit]

    def get_agent_history(self, agent_id: UUID) -> List[OwnershipTransfer]:
        """Get complete ownership history for an agent."""
        transfer_ids = self._by_agent.get(agent_id, [])
        transfers = [self._transfers[tid] for tid in transfer_ids if tid in self._transfers]
        transfers.sort(key=lambda t: t.transferred_at)
        return transfers

    def on_transfer(self, callback: Callable[[OwnershipTransfer], None]) -> None:
        """Register callback for completed transfers."""
        self._on_transfer.append(callback)

    def on_transfer_request(self, callback: Callable[[OwnershipTransfer], None]) -> None:
        """Register callback for transfer requests."""
        self._on_transfer_request.append(callback)

    def _execute_transfer(
        self,
        record: AgentRecord,
        transfer: OwnershipTransfer,
    ) -> None:
        """Execute the ownership transfer."""
        # Update agent record
        old_ownership = record.ownership
        record.ownership = AgentOwnership(
            owner_id=transfer.to_owner_id,
            owner_type=transfer.to_owner_type,
            owner_name=transfer.to_owner_name,
            created_at=old_ownership.created_at,
            transferred_at=datetime.utcnow(),
            previous_owner_id=old_ownership.owner_id,
        )

        # Store transfer
        transfer.transferred_at = datetime.utcnow()
        self._transfers[transfer.id] = transfer

        # Update agent index
        if record.id not in self._by_agent:
            self._by_agent[record.id] = []
        self._by_agent[record.id].append(transfer.id)

        # Notify callbacks
        for callback in self._on_transfer:
            try:
                callback(transfer)
            except Exception as e:
                logger.error(f"Transfer callback error: {e}")

        logger.info(
            f"Ownership transferred for {record.name}: "
            f"{transfer.from_owner_name} -> {transfer.to_owner_name}"
        )


# Global instance
_ownership_manager: Optional[OwnershipManager] = None


def get_ownership_manager() -> OwnershipManager:
    """Get the global ownership manager instance."""
    global _ownership_manager
    if _ownership_manager is None:
        _ownership_manager = OwnershipManager()
    return _ownership_manager
