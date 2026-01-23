"""
Coordination Models

Data structures for multi-agent coordination.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


class ConflictType(str, Enum):
    """Types of conflicts between agents."""
    RESOURCE_CONTENTION = "resource_contention"
    DATA_CONFLICT = "data_conflict"
    PRIORITY_CONFLICT = "priority_conflict"
    CAPABILITY_OVERLAP = "capability_overlap"
    TIMING_CONFLICT = "timing_conflict"
    POLICY_VIOLATION = "policy_violation"
    DEADLOCK = "deadlock"


class ResolutionStrategy(str, Enum):
    """Strategies for conflict resolution."""
    PRIORITY_BASED = "priority_based"  # Higher priority wins
    FIRST_COME = "first_come"  # First request wins
    ROUND_ROBIN = "round_robin"  # Rotate between agents
    CONSENSUS = "consensus"  # Require agreement
    MERGE = "merge"  # Combine results
    DEFER = "defer"  # Delay decision
    ESCALATE = "escalate"  # Escalate to human
    ABORT = "abort"  # Cancel conflicting operations


class WorkflowPattern(str, Enum):
    """Multi-agent workflow patterns."""
    SEQUENTIAL = "sequential"  # One after another
    PARALLEL = "parallel"  # All at once
    FAN_OUT = "fan_out"  # One to many
    FAN_IN = "fan_in"  # Many to one
    PIPELINE = "pipeline"  # Chain of transformations
    SCATTER_GATHER = "scatter_gather"  # Distribute and collect
    SAGA = "saga"  # Distributed transaction
    CHOREOGRAPHY = "choreography"  # Event-driven coordination


@dataclass
class CoordinationTask:
    """A task to be coordinated across agents."""
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""

    # Task definition
    task_type: str = ""
    input_data: Dict[str, Any] = field(default_factory=dict)
    expected_output: Optional[Dict[str, Any]] = None

    # Agent assignment
    assigned_agent_id: Optional[UUID] = None
    candidate_agents: List[UUID] = field(default_factory=list)
    required_capabilities: List[str] = field(default_factory=list)

    # Dependencies
    depends_on: List[UUID] = field(default_factory=list)  # Task IDs
    blocks: List[UUID] = field(default_factory=list)  # Task IDs this blocks

    # Execution
    priority: int = 5  # 1-10, higher is more important
    timeout_seconds: int = 300
    retry_count: int = 0
    max_retries: int = 3

    # Status
    status: str = "pending"  # pending, assigned, running, completed, failed, cancelled
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

    # Results
    result: Optional["TaskResult"] = None

    def is_ready(self, completed_tasks: set) -> bool:
        """Check if all dependencies are satisfied."""
        return all(dep in completed_tasks for dep in self.depends_on)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "task_type": self.task_type,
            "assigned_agent_id": str(self.assigned_agent_id) if self.assigned_agent_id else None,
            "priority": self.priority,
            "status": self.status,
            "depends_on": [str(d) for d in self.depends_on],
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
        }


@dataclass
class TaskResult:
    """Result of a coordination task."""
    id: UUID = field(default_factory=uuid4)
    task_id: UUID = field(default_factory=uuid4)
    agent_id: UUID = field(default_factory=uuid4)

    # Result data
    success: bool = True
    output_data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    # Execution metrics
    execution_time_ms: int = 0
    tokens_used: int = 0
    cost_usd: float = 0.0

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "task_id": str(self.task_id),
            "agent_id": str(self.agent_id),
            "success": self.success,
            "output_data": self.output_data,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "tokens_used": self.tokens_used,
            "cost_usd": self.cost_usd,
            "created_at": self.created_at.isoformat(),
        }
