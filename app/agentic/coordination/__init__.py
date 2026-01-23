"""
Agent Coordination

Multi-agent coordination and orchestration:
- Arbitration and conflict resolution
- Multi-agent workflow orchestration
- Fan-in / fan-out patterns
- Deterministic outcomes
"""

from app.agentic.coordination.models import (
    CoordinationTask,
    TaskResult,
    ConflictType,
    ResolutionStrategy,
    WorkflowPattern,
)
from app.agentic.coordination.arbitration import (
    Arbitrator,
    Conflict,
    Resolution,
    get_arbitrator,
)
from app.agentic.coordination.orchestrator import (
    MultiAgentOrchestrator,
    OrchestrationPlan,
    AgentAssignment,
    get_orchestrator,
)

__all__ = [
    # Models
    "CoordinationTask",
    "TaskResult",
    "ConflictType",
    "ResolutionStrategy",
    "WorkflowPattern",
    # Arbitration
    "Arbitrator",
    "Conflict",
    "Resolution",
    "get_arbitrator",
    # Orchestration
    "MultiAgentOrchestrator",
    "OrchestrationPlan",
    "AgentAssignment",
    "get_orchestrator",
]
