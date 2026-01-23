"""
Multi-Agent Orchestrator

Coordinates multi-agent workflows.
Implements Coordination: Multi-agent workflow orchestration from RACI.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import UUID, uuid4

from .models import CoordinationTask, TaskResult, WorkflowPattern

logger = logging.getLogger(__name__)


@dataclass
class AgentAssignment:
    """Assignment of an agent to a task."""
    agent_id: UUID
    task_id: UUID
    assigned_at: datetime = field(default_factory=datetime.utcnow)
    priority: int = 5
    capabilities_matched: List[str] = field(default_factory=list)
    score: float = 1.0


@dataclass
class OrchestrationPlan:
    """Plan for orchestrating multiple agents."""
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""

    # Pattern
    pattern: WorkflowPattern = WorkflowPattern.SEQUENTIAL
    parallel_limit: int = 10

    # Tasks
    tasks: List[CoordinationTask] = field(default_factory=list)
    task_order: List[UUID] = field(default_factory=list)

    # Assignments
    assignments: Dict[UUID, AgentAssignment] = field(default_factory=dict)

    # Execution state
    status: str = "pending"  # pending, running, completed, failed, cancelled
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

    # Results
    completed_tasks: Set[UUID] = field(default_factory=set)
    failed_tasks: Set[UUID] = field(default_factory=set)
    results: Dict[UUID, TaskResult] = field(default_factory=dict)

    # Metrics
    total_execution_time_ms: int = 0
    total_cost_usd: float = 0.0

    def get_progress(self) -> float:
        """Get execution progress as percentage."""
        if not self.tasks:
            return 0.0
        completed = len(self.completed_tasks) + len(self.failed_tasks)
        return (completed / len(self.tasks)) * 100

    def get_ready_tasks(self) -> List[CoordinationTask]:
        """Get tasks ready for execution."""
        return [
            task for task in self.tasks
            if task.status == "pending" and task.is_ready(self.completed_tasks)
        ]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "name": self.name,
            "pattern": self.pattern.value,
            "status": self.status,
            "progress": self.get_progress(),
            "total_tasks": len(self.tasks),
            "completed_tasks": len(self.completed_tasks),
            "failed_tasks": len(self.failed_tasks),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
        }


class MultiAgentOrchestrator:
    """
    Multi-Agent Orchestrator.

    Coordinates workflows across multiple agents:
    - Sequential execution
    - Parallel execution
    - Fan-out / fan-in patterns
    - Dependency management
    """

    def __init__(self):
        """Initialize the orchestrator."""
        # Active plans
        self._plans: Dict[UUID, OrchestrationPlan] = {}

        # Agent capabilities (for assignment)
        self._agent_capabilities: Dict[UUID, Set[str]] = {}

        # Task executors (registered handlers)
        self._executors: Dict[str, Callable] = {}

        # Callbacks
        self._on_plan_start: List[Callable[[OrchestrationPlan], None]] = []
        self._on_plan_complete: List[Callable[[OrchestrationPlan], None]] = []
        self._on_task_start: List[Callable[[OrchestrationPlan, CoordinationTask], None]] = []
        self._on_task_complete: List[Callable[[OrchestrationPlan, CoordinationTask, TaskResult], None]] = []

    def register_agent_capabilities(
        self,
        agent_id: UUID,
        capabilities: List[str],
    ) -> None:
        """Register an agent's capabilities for task matching."""
        self._agent_capabilities[agent_id] = set(capabilities)

    def register_executor(
        self,
        task_type: str,
        executor: Callable,
    ) -> None:
        """Register an executor for a task type."""
        self._executors[task_type] = executor

    def create_plan(
        self,
        name: str,
        tasks: List[CoordinationTask],
        pattern: WorkflowPattern = WorkflowPattern.SEQUENTIAL,
        description: str = "",
        parallel_limit: int = 10,
    ) -> OrchestrationPlan:
        """
        Create an orchestration plan.

        Args:
            name: Plan name
            tasks: Tasks to execute
            pattern: Workflow pattern
            description: Plan description
            parallel_limit: Max parallel tasks

        Returns:
            Created plan
        """
        plan = OrchestrationPlan(
            name=name,
            description=description,
            pattern=pattern,
            parallel_limit=parallel_limit,
            tasks=tasks,
        )

        # Compute task order based on dependencies
        plan.task_order = self._compute_task_order(tasks)

        # Assign agents to tasks
        for task in tasks:
            assignment = self._assign_agent(task)
            if assignment:
                plan.assignments[task.id] = assignment
                task.assigned_agent_id = assignment.agent_id

        self._plans[plan.id] = plan
        logger.info(f"Created orchestration plan: {name} with {len(tasks)} tasks")

        return plan

    async def execute_plan(self, plan_id: UUID) -> OrchestrationPlan:
        """
        Execute an orchestration plan.

        Args:
            plan_id: Plan to execute

        Returns:
            Completed plan
        """
        plan = self._plans.get(plan_id)
        if not plan:
            raise ValueError(f"Plan not found: {plan_id}")

        if plan.status != "pending":
            raise ValueError(f"Plan already executed: {plan.status}")

        # Start plan
        plan.status = "running"
        plan.started_at = datetime.utcnow()

        # Notify callbacks
        for callback in self._on_plan_start:
            try:
                callback(plan)
            except Exception as e:
                logger.error(f"Plan start callback error: {e}")

        try:
            if plan.pattern == WorkflowPattern.SEQUENTIAL:
                await self._execute_sequential(plan)
            elif plan.pattern == WorkflowPattern.PARALLEL:
                await self._execute_parallel(plan)
            elif plan.pattern in [WorkflowPattern.FAN_OUT, WorkflowPattern.SCATTER_GATHER]:
                await self._execute_fan_out(plan)
            elif plan.pattern == WorkflowPattern.PIPELINE:
                await self._execute_pipeline(plan)
            else:
                # Default to sequential with dependency handling
                await self._execute_with_dependencies(plan)

            # Determine final status
            if plan.failed_tasks:
                plan.status = "completed_with_errors"
            else:
                plan.status = "completed"

        except Exception as e:
            logger.error(f"Plan execution failed: {e}")
            plan.status = "failed"
            plan.error = str(e)

        plan.completed_at = datetime.utcnow()
        plan.total_execution_time_ms = int(
            (plan.completed_at - plan.started_at).total_seconds() * 1000
        )

        # Notify callbacks
        for callback in self._on_plan_complete:
            try:
                callback(plan)
            except Exception as e:
                logger.error(f"Plan complete callback error: {e}")

        logger.info(f"Plan completed: {plan.name} - {plan.status}")
        return plan

    async def cancel_plan(self, plan_id: UUID, reason: Optional[str] = None) -> OrchestrationPlan:
        """Cancel an executing plan."""
        plan = self._plans.get(plan_id)
        if not plan:
            raise ValueError(f"Plan not found: {plan_id}")

        plan.status = "cancelled"
        plan.error = reason or "Cancelled by user"
        plan.completed_at = datetime.utcnow()

        # Cancel pending tasks
        for task in plan.tasks:
            if task.status == "pending":
                task.status = "cancelled"

        logger.info(f"Plan cancelled: {plan_id}")
        return plan

    def get_plan(self, plan_id: UUID) -> Optional[OrchestrationPlan]:
        """Get a plan by ID."""
        return self._plans.get(plan_id)

    def get_plans(
        self,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[OrchestrationPlan]:
        """Get plans with optional status filter."""
        plans = list(self._plans.values())

        if status:
            plans = [p for p in plans if p.status == status]

        # Sort by creation (most recent first)
        plans.sort(key=lambda p: p.started_at or datetime.min, reverse=True)
        return plans[:limit]

    def get_stats(self) -> Dict[str, Any]:
        """Get orchestration statistics."""
        plans = list(self._plans.values())

        by_status = {}
        for p in plans:
            by_status[p.status] = by_status.get(p.status, 0) + 1

        by_pattern = {}
        for p in plans:
            by_pattern[p.pattern.value] = by_pattern.get(p.pattern.value, 0) + 1

        total_tasks = sum(len(p.tasks) for p in plans)
        completed_tasks = sum(len(p.completed_tasks) for p in plans)

        return {
            "total_plans": len(plans),
            "by_status": by_status,
            "by_pattern": by_pattern,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "total_cost_usd": sum(p.total_cost_usd for p in plans),
            "registered_agents": len(self._agent_capabilities),
            "registered_executors": len(self._executors),
        }

    # Event registration
    def on_plan_start(self, callback: Callable[[OrchestrationPlan], None]) -> None:
        """Register callback for plan start."""
        self._on_plan_start.append(callback)

    def on_plan_complete(self, callback: Callable[[OrchestrationPlan], None]) -> None:
        """Register callback for plan completion."""
        self._on_plan_complete.append(callback)

    def on_task_start(
        self,
        callback: Callable[[OrchestrationPlan, CoordinationTask], None],
    ) -> None:
        """Register callback for task start."""
        self._on_task_start.append(callback)

    def on_task_complete(
        self,
        callback: Callable[[OrchestrationPlan, CoordinationTask, TaskResult], None],
    ) -> None:
        """Register callback for task completion."""
        self._on_task_complete.append(callback)

    # Private methods

    def _compute_task_order(self, tasks: List[CoordinationTask]) -> List[UUID]:
        """Compute topological order of tasks based on dependencies."""
        # Build dependency graph
        task_map = {t.id: t for t in tasks}
        in_degree = {t.id: len(t.depends_on) for t in tasks}

        # Find tasks with no dependencies
        queue = [tid for tid, deg in in_degree.items() if deg == 0]
        order = []

        while queue:
            tid = queue.pop(0)
            order.append(tid)

            task = task_map.get(tid)
            if task:
                for blocked_id in task.blocks:
                    if blocked_id in in_degree:
                        in_degree[blocked_id] -= 1
                        if in_degree[blocked_id] == 0:
                            queue.append(blocked_id)

        # Add any remaining tasks (might have cycles)
        for task in tasks:
            if task.id not in order:
                order.append(task.id)

        return order

    def _assign_agent(self, task: CoordinationTask) -> Optional[AgentAssignment]:
        """Assign an agent to a task based on capabilities."""
        if task.assigned_agent_id:
            return AgentAssignment(
                agent_id=task.assigned_agent_id,
                task_id=task.id,
                capabilities_matched=[],
            )

        if not task.required_capabilities:
            # If no requirements, use first candidate
            if task.candidate_agents:
                return AgentAssignment(
                    agent_id=task.candidate_agents[0],
                    task_id=task.id,
                    capabilities_matched=[],
                )
            return None

        # Find agent with matching capabilities
        best_match = None
        best_score = 0.0

        for agent_id, capabilities in self._agent_capabilities.items():
            if task.candidate_agents and agent_id not in task.candidate_agents:
                continue

            matched = capabilities & set(task.required_capabilities)
            score = len(matched) / len(task.required_capabilities) if task.required_capabilities else 1.0

            if score > best_score:
                best_score = score
                best_match = AgentAssignment(
                    agent_id=agent_id,
                    task_id=task.id,
                    capabilities_matched=list(matched),
                    score=score,
                )

        return best_match

    async def _execute_task(
        self,
        plan: OrchestrationPlan,
        task: CoordinationTask,
    ) -> TaskResult:
        """Execute a single task."""
        # Notify start
        for callback in self._on_task_start:
            try:
                callback(plan, task)
            except Exception as e:
                logger.error(f"Task start callback error: {e}")

        task.status = "running"
        task.started_at = datetime.utcnow()

        try:
            # Find executor
            executor = self._executors.get(task.task_type)
            if executor:
                output = await executor(task)
            else:
                # Default mock execution
                output = {"status": "completed", "task_id": str(task.id)}

            result = TaskResult(
                task_id=task.id,
                agent_id=task.assigned_agent_id or uuid4(),
                success=True,
                output_data=output,
                execution_time_ms=int(
                    (datetime.utcnow() - task.started_at).total_seconds() * 1000
                ),
            )

            task.status = "completed"
            task.completed_at = datetime.utcnow()
            task.result = result
            plan.completed_tasks.add(task.id)
            plan.results[task.id] = result

        except Exception as e:
            logger.error(f"Task execution failed: {task.name} - {e}")

            result = TaskResult(
                task_id=task.id,
                agent_id=task.assigned_agent_id or uuid4(),
                success=False,
                error=str(e),
            )

            task.status = "failed"
            task.completed_at = datetime.utcnow()
            task.error = str(e)
            task.result = result
            plan.failed_tasks.add(task.id)
            plan.results[task.id] = result

        # Update plan metrics
        plan.total_cost_usd += result.cost_usd

        # Notify completion
        for callback in self._on_task_complete:
            try:
                callback(plan, task, result)
            except Exception as e:
                logger.error(f"Task complete callback error: {e}")

        return result

    async def _execute_sequential(self, plan: OrchestrationPlan) -> None:
        """Execute tasks sequentially."""
        for task_id in plan.task_order:
            task = next((t for t in plan.tasks if t.id == task_id), None)
            if task and task.status == "pending":
                await self._execute_task(plan, task)

    async def _execute_parallel(self, plan: OrchestrationPlan) -> None:
        """Execute tasks in parallel."""
        pending_tasks = [t for t in plan.tasks if t.status == "pending"]

        # Execute in batches
        for i in range(0, len(pending_tasks), plan.parallel_limit):
            batch = pending_tasks[i:i + plan.parallel_limit]
            await asyncio.gather(
                *[self._execute_task(plan, task) for task in batch],
                return_exceptions=True,
            )

    async def _execute_fan_out(self, plan: OrchestrationPlan) -> None:
        """Execute tasks in fan-out pattern."""
        # All tasks start in parallel
        await asyncio.gather(
            *[self._execute_task(plan, task) for task in plan.tasks if task.status == "pending"],
            return_exceptions=True,
        )

    async def _execute_pipeline(self, plan: OrchestrationPlan) -> None:
        """Execute tasks as a pipeline, passing output to next task."""
        previous_output = None

        for task_id in plan.task_order:
            task = next((t for t in plan.tasks if t.id == task_id), None)
            if not task or task.status != "pending":
                continue

            # Pass previous output as input
            if previous_output:
                task.input_data["previous_output"] = previous_output

            result = await self._execute_task(plan, task)
            previous_output = result.output_data if result.success else None

    async def _execute_with_dependencies(self, plan: OrchestrationPlan) -> None:
        """Execute tasks respecting dependencies."""
        while True:
            ready_tasks = plan.get_ready_tasks()
            if not ready_tasks:
                break

            # Execute ready tasks in parallel (up to limit)
            batch = ready_tasks[:plan.parallel_limit]
            await asyncio.gather(
                *[self._execute_task(plan, task) for task in batch],
                return_exceptions=True,
            )


# Global instance
_orchestrator: Optional[MultiAgentOrchestrator] = None


def get_orchestrator() -> MultiAgentOrchestrator:
    """Get the global orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = MultiAgentOrchestrator()
    return _orchestrator
