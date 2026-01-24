"""
Simulation Executor

Executes FARM-generated workflows through AOA modules with:
- Full observability (traces, metrics, vitals)
- Governance integration (policies, budgets, approvals)
- All 9 chaos types
- Event streaming for UI
"""

import asyncio
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import UUID, uuid4

from app.agentic.registry import (
    AgentRecord,
    AgentMetadata,
    AgentOwnership,
    TrustTier,
    AgentDomain,
    AgentStatus,
    get_agent_inventory,
)
from app.agentic.coordination import (
    CoordinationTask,
    WorkflowPattern,
    get_orchestrator,
    get_arbitrator,
)
from app.agentic.governance import (
    Policy,
    PolicyRule,
    PolicyScope,
    RuleAction,
    get_policy_engine,
    get_autonomy_manager,
    AutonomyBounds,
    AutonomyLevel,
)
from app.agentic.approval import (
    ApprovalType,
    ApprovalPriority,
    get_approval_workflow,
)

from app.agentic.simulation.metrics_bridge import MetricsBridge, get_metrics_bridge
from app.agentic.simulation.event_emitter import EventEmitter, get_event_emitter

logger = logging.getLogger(__name__)


class ChaosType(str, Enum):
    """All 9 FARM chaos types."""
    TOOL_TIMEOUT = "tool_timeout"
    TOOL_FAILURE = "tool_failure"
    AGENT_CONFLICT = "agent_conflict"
    POLICY_VIOLATION = "policy_violation"
    CHECKPOINT_CRASH = "checkpoint_crash"
    MEMORY_PRESSURE = "memory_pressure"
    RATE_LIMIT = "rate_limit"
    DATA_CORRUPTION = "data_corruption"
    NETWORK_PARTITION = "network_partition"


@dataclass
class ExecutionConfig:
    """Configuration for simulation execution."""
    # Timing
    speedup_factor: float = 10.0  # Speed up execution by this factor
    max_parallel_tasks: int = 10

    # Feature toggles
    emit_events: bool = True
    record_metrics: bool = True
    apply_policies: bool = True
    require_approvals: bool = False  # Auto-approve in simulation
    register_agents: bool = True

    # Chaos handling
    chaos_recovery_enabled: bool = True
    max_retries: int = 3


@dataclass
class TaskResult:
    """Result of a single task execution."""
    task_id: str
    status: str  # completed, failed, timeout, retried
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: int = 0
    assigned_agent_id: Optional[str] = None
    chaos_occurred: bool = False
    chaos_type: Optional[str] = None
    chaos_recovered: bool = False
    error_message: Optional[str] = None
    retry_count: int = 0
    tokens_used: int = 0
    cost_usd: float = 0.0


@dataclass
class WorkflowResult:
    """Result of a workflow execution."""
    workflow_id: str
    status: str  # completed, failed, partial
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_duration_ms: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    tasks_retried: int = 0
    chaos_events_handled: int = 0
    chaos_events_recovered: int = 0
    task_results: List[TaskResult] = field(default_factory=list)
    total_tokens: int = 0
    total_cost_usd: float = 0.0


@dataclass
class ExecutionResult:
    """Result of a complete stress scenario execution."""
    scenario_id: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_duration_ms: int = 0

    # Workflow metrics
    workflows_completed: int = 0
    workflows_failed: int = 0
    workflow_results: List[WorkflowResult] = field(default_factory=list)

    # Task metrics
    total_tasks: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0

    # Chaos metrics
    chaos_events_total: int = 0
    chaos_events_recovered: int = 0

    # Performance metrics
    throughput_wf_per_sec: float = 0.0
    throughput_tasks_per_sec: float = 0.0
    avg_latency_ms: float = 0.0

    # Cost metrics
    total_tokens: int = 0
    total_cost_usd: float = 0.0

    # FARM validation
    completion_rate: float = 0.0
    chaos_recovery_rate: float = 0.0
    validation: Dict[str, Any] = field(default_factory=dict)
    verdict: str = "PENDING"  # PASS, DEGRADED, FAIL
    analysis: Dict[str, Any] = field(default_factory=dict)


class SimulationExecutor:
    """
    Executes FARM stress scenarios through AOA infrastructure.

    Integrates with:
    - AgentInventory: Register synthetic agents
    - MultiAgentOrchestrator: Coordinate task execution
    - Arbitrator: Handle conflicts
    - PolicyEngine: Apply governance
    - ApprovalWorkflow: Handle HITL
    - Tracer/MetricsCollector/VitalsMonitor: Observability
    - StreamManager: UI events
    """

    def __init__(self, config: Optional[ExecutionConfig] = None):
        self.config = config or ExecutionConfig()

        # AOA modules
        self._inventory = None
        self._orchestrator = None
        self._arbitrator = None
        self._policy_engine = None
        self._approval_workflow = None

        # Simulation bridges
        self._metrics_bridge: Optional[MetricsBridge] = None
        self._event_emitter: Optional[EventEmitter] = None

        # State
        self._registered_agents: Dict[str, UUID] = {}  # farm_agent_id -> registry_id
        self._active_locks: Set[str] = set()

    def initialize(self) -> None:
        """Initialize connections to AOA modules."""
        self._inventory = get_agent_inventory()
        self._orchestrator = get_orchestrator()
        self._arbitrator = get_arbitrator()
        self._policy_engine = get_policy_engine()
        self._approval_workflow = get_approval_workflow()

        self._metrics_bridge = get_metrics_bridge()
        self._event_emitter = get_event_emitter()

        logger.info("SimulationExecutor initialized")

    # -------------------------------------------------------------------------
    # Fleet Registration
    # -------------------------------------------------------------------------

    async def register_fleet(
        self,
        agents: List[Dict[str, Any]],
        tenant_id: Optional[UUID] = None,
    ) -> Dict[str, UUID]:
        """Register FARM agents in AOA AgentInventory."""
        if not self._inventory:
            self.initialize()

        registered = {}

        for farm_agent in agents:
            agent_id = uuid4()

            # Map FARM agent type to AOA domain
            domain_map = {
                "planner": AgentDomain.AUTOMATION,
                "worker": AgentDomain.DATA,
                "specialist": AgentDomain.ANALYSIS,
                "reviewer": AgentDomain.SECURITY,
                "approver": AgentDomain.SECURITY,
                "coordinator": AgentDomain.INFRASTRUCTURE,
            }

            # Map reliability to trust tier
            trust_map = {
                "rock_solid": TrustTier.NATIVE,
                "reliable": TrustTier.VERIFIED,
                "flaky": TrustTier.CUSTOMER,
                "unreliable": TrustTier.SANDBOX,
            }

            reliability = farm_agent.get("reliability", {})
            cost = farm_agent.get("cost", {})

            record = AgentRecord(
                id=agent_id,
                name=farm_agent.get("name", f"farm-agent-{farm_agent['agent_id']}"),
                agent_type=farm_agent.get("type", "worker"),
                tenant_id=tenant_id,
                status=AgentStatus.ACTIVE,
                metadata=AgentMetadata(
                    domain=domain_map.get(farm_agent.get("type"), AgentDomain.CUSTOM),
                    trust_tier=trust_map.get(reliability.get("profile"), TrustTier.CUSTOMER),
                    declared_capabilities=farm_agent.get("capabilities", []),
                    description=f"FARM synthetic agent: {farm_agent.get('type')}",
                    version=farm_agent.get("version", "1.0.0"),
                    max_cost_per_run_usd=cost.get("per_invocation", 0.001) * 1000,
                ),
                ownership=AgentOwnership(
                    owner_id=tenant_id or uuid4(),
                    owner_type="tenant",
                    owner_name="FARM Stress Test",
                ),
            )

            self._inventory.register(record)
            registered[farm_agent["agent_id"]] = agent_id
            self._registered_agents[farm_agent["agent_id"]] = agent_id

        logger.info(f"Registered {len(registered)} FARM agents in AgentInventory")

        if self._metrics_bridge:
            self._metrics_bridge.set_active_agents(len(registered))

        return registered

    # -------------------------------------------------------------------------
    # Workflow Execution
    # -------------------------------------------------------------------------

    async def execute_workflow(
        self,
        workflow: Dict[str, Any],
        agent_assignments: Optional[Dict[str, str]] = None,
        tenant_id: Optional[UUID] = None,
    ) -> WorkflowResult:
        """Execute a single FARM workflow."""
        if not self._orchestrator:
            self.initialize()

        workflow_id = workflow.get("workflow_id", str(uuid4()))
        workflow_type = workflow.get("type", "dag")
        tasks = workflow.get("tasks", [])

        run_id = uuid4()
        started_at = datetime.utcnow()

        # Start trace
        if self._metrics_bridge:
            self._metrics_bridge.start_workflow_trace(workflow_id, workflow_type, tenant_id)

        # Emit run started event
        if self._event_emitter and self.config.emit_events:
            await self._event_emitter.emit_run_started(
                run_id=run_id,
                workflow_id=workflow_id,
                tenant_id=tenant_id,
                metadata={"workflow_type": workflow_type, "task_count": len(tasks)},
            )

        # Build dependency graph
        task_map = {t["task_id"]: t for t in tasks}
        dep_graph = {t["task_id"]: set(t.get("depends_on", t.get("dependencies", []))) for t in tasks}

        # Execute tasks
        task_results: List[TaskResult] = []
        completed_tasks: Set[str] = set()

        while len(completed_tasks) < len(tasks):
            # Find tasks ready to execute
            ready_tasks = [
                task_id for task_id, deps in dep_graph.items()
                if task_id not in completed_tasks
                and all(d in completed_tasks for d in deps)
            ]

            if not ready_tasks:
                logger.warning(f"Workflow {workflow_id}: No ready tasks, possible deadlock")
                break

            # Execute ready tasks in parallel (up to limit)
            batch = ready_tasks[:self.config.max_parallel_tasks]
            batch_tasks = [task_map[task_id] for task_id in batch]

            results = await asyncio.gather(*[
                self._execute_task(
                    task=t,
                    workflow_id=workflow_id,
                    run_id=run_id,
                    agent_id=agent_assignments.get(t["task_id"]) if agent_assignments else None,
                    tenant_id=tenant_id,
                )
                for t in batch_tasks
            ])

            for result in results:
                task_results.append(result)
                if result.status in ("completed", "retried"):
                    completed_tasks.add(result.task_id)

        # Calculate results
        completed_at = datetime.utcnow()
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)

        tasks_completed = sum(1 for r in task_results if r.status in ("completed", "retried"))
        tasks_failed = sum(1 for r in task_results if r.status == "failed")
        tasks_retried = sum(1 for r in task_results if r.retry_count > 0)
        chaos_handled = sum(1 for r in task_results if r.chaos_occurred)
        chaos_recovered = sum(1 for r in task_results if r.chaos_occurred and r.chaos_recovered)

        total_tokens = sum(r.tokens_used for r in task_results)
        total_cost = sum(r.cost_usd for r in task_results)

        status = "completed" if tasks_failed == 0 else "partial" if tasks_completed > 0 else "failed"

        # End trace
        if self._metrics_bridge:
            self._metrics_bridge.end_workflow_trace(
                workflow_id, status, duration_ms, tasks_completed, tasks_failed
            )

        # Emit completion event
        if self._event_emitter and self.config.emit_events:
            await self._event_emitter.emit_run_completed(
                run_id=run_id,
                workflow_id=workflow_id,
                status=status,
                duration_ms=duration_ms,
                tasks_completed=tasks_completed,
                tasks_failed=tasks_failed,
                tenant_id=tenant_id,
            )

        return WorkflowResult(
            workflow_id=workflow_id,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            total_duration_ms=duration_ms,
            tasks_completed=tasks_completed,
            tasks_failed=tasks_failed,
            tasks_retried=tasks_retried,
            chaos_events_handled=chaos_handled,
            chaos_events_recovered=chaos_recovered,
            task_results=task_results,
            total_tokens=total_tokens,
            total_cost_usd=total_cost,
        )

    async def _execute_task(
        self,
        task: Dict[str, Any],
        workflow_id: str,
        run_id: UUID,
        agent_id: Optional[str],
        tenant_id: Optional[UUID],
    ) -> TaskResult:
        """Execute a single task with full AOA integration."""
        task_id = task["task_id"]
        task_type = task.get("type", "compute")
        task_name = task.get("name", task_id)

        started_at = datetime.utcnow()
        status = "completed"
        chaos_occurred = False
        chaos_type = None
        chaos_recovered = False
        error_message = None
        retry_count = 0

        # Resolve agent
        registry_agent_id = self._registered_agents.get(agent_id) if agent_id else None

        # Start task span
        if self._metrics_bridge:
            self._metrics_bridge.start_task_span(workflow_id, task_id, task_type, agent_id)

        # Emit step started
        if self._event_emitter and self.config.emit_events:
            await self._event_emitter.emit_step_started(
                run_id, task_id, task_name, agent_id, tenant_id
            )

        # Check for chaos injection
        chaos_config = task.get("chaos_injection")
        if chaos_config and random.random() < chaos_config.get("trigger_probability", 0):
            chaos_occurred = True
            chaos_type = chaos_config.get("type")

            result = await self._handle_chaos(
                chaos_type=chaos_type,
                task=task,
                workflow_id=workflow_id,
                run_id=run_id,
                tenant_id=tenant_id,
            )

            if result["recovered"]:
                chaos_recovered = True
                retry_count = result.get("retries", 1)
            else:
                status = "failed"
                error_message = result.get("error", f"Chaos event {chaos_type} not recovered")

        # Simulate normal execution (if not failed)
        if status != "failed":
            duration_ms = task.get("estimated_duration_ms", task.get("expected_duration_ms", 500))
            await asyncio.sleep(duration_ms / 1000 / self.config.speedup_factor)

            # Emit tool calls for tools_required
            for tool in task.get("tools_required", []):
                if self._event_emitter and self.config.emit_events:
                    await self._event_emitter.emit_tool_call_started(run_id, task_id, tool, tenant_id)
                    await asyncio.sleep(0.01)  # Brief delay
                    await self._event_emitter.emit_tool_call_completed(
                        run_id, task_id, tool, True, 50, tenant_id
                    )

        # Calculate costs
        tokens_used = task.get("token_budget", 500)
        cost_usd = tokens_used * 0.00001  # $0.01 per 1000 tokens

        # Record cost
        if tenant_id and self._metrics_bridge:
            self._metrics_bridge.record_cost(tenant_id, cost_usd, tokens_used, f"task:{task_type}")

        completed_at = datetime.utcnow()
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)

        # End task span
        if self._metrics_bridge:
            self._metrics_bridge.end_task_span(task_id, status, duration_ms, retry_count, chaos_type)

        # Emit step completed
        if self._event_emitter and self.config.emit_events:
            await self._event_emitter.emit_step_completed(run_id, task_id, status, duration_ms, tenant_id)

        return TaskResult(
            task_id=task_id,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            assigned_agent_id=agent_id,
            chaos_occurred=chaos_occurred,
            chaos_type=chaos_type,
            chaos_recovered=chaos_recovered,
            error_message=error_message,
            retry_count=retry_count,
            tokens_used=tokens_used,
            cost_usd=cost_usd,
        )

    async def _handle_chaos(
        self,
        chaos_type: str,
        task: Dict[str, Any],
        workflow_id: str,
        run_id: UUID,
        tenant_id: Optional[UUID],
    ) -> Dict[str, Any]:
        """Handle chaos injection for all 9 types."""
        chaos_config = task.get("chaos_injection", {})
        recovery_action = chaos_config.get("recovery_action", "retry")

        if not self.config.chaos_recovery_enabled:
            return {"recovered": False, "error": "Chaos recovery disabled"}

        if chaos_type == ChaosType.TOOL_TIMEOUT.value:
            # Simulate timeout and retry
            await asyncio.sleep(0.5 / self.config.speedup_factor)
            return {"recovered": True, "retries": 1}

        elif chaos_type == ChaosType.TOOL_FAILURE.value:
            # Check if recoverable
            recoverable = chaos_config.get("parameters", {}).get("recoverable", True)
            if recoverable:
                await asyncio.sleep(0.2 / self.config.speedup_factor)
                return {"recovered": True, "retries": 1}
            return {"recovered": False, "error": "Non-recoverable tool failure"}

        elif chaos_type == ChaosType.AGENT_CONFLICT.value:
            # Use arbitrator to resolve
            if self._arbitrator:
                # Simulate conflict resolution
                await asyncio.sleep(0.3 / self.config.speedup_factor)
            return {"recovered": True, "retries": 0}

        elif chaos_type == ChaosType.POLICY_VIOLATION.value:
            # Emit approval required event
            if self._event_emitter and self.config.emit_events:
                await self._event_emitter.emit_approval_required(
                    run_id, task["task_id"], "policy_violation",
                    "Action blocked by policy engine", tenant_id
                )
            # Auto-approve in simulation
            await asyncio.sleep(0.2 / self.config.speedup_factor)
            return {"recovered": True, "retries": 0}

        elif chaos_type == ChaosType.CHECKPOINT_CRASH.value:
            # Simulate recovery from checkpoint
            await asyncio.sleep(0.3 / self.config.speedup_factor)
            return {"recovered": True, "retries": 1}

        elif chaos_type == ChaosType.MEMORY_PRESSURE.value:
            # Simulate context window exceeded - summarize and continue
            await asyncio.sleep(0.4 / self.config.speedup_factor)
            return {"recovered": True, "retries": 0}

        elif chaos_type == ChaosType.RATE_LIMIT.value:
            # Simulate backoff and retry
            await asyncio.sleep(1.0 / self.config.speedup_factor)
            return {"recovered": True, "retries": 2}

        elif chaos_type == ChaosType.DATA_CORRUPTION.value:
            # Simulate validation and repair
            await asyncio.sleep(0.5 / self.config.speedup_factor)
            return {"recovered": True, "retries": 1}

        elif chaos_type == ChaosType.NETWORK_PARTITION.value:
            # Simulate queue and retry
            await asyncio.sleep(2.0 / self.config.speedup_factor)
            return {"recovered": True, "retries": 3}

        return {"recovered": False, "error": f"Unknown chaos type: {chaos_type}"}

    # -------------------------------------------------------------------------
    # Scenario Execution
    # -------------------------------------------------------------------------

    async def execute_scenario(
        self,
        scenario: Dict[str, Any],
        tenant_id: Optional[UUID] = None,
    ) -> ExecutionResult:
        """Execute a complete FARM stress scenario."""
        if not self._orchestrator:
            self.initialize()

        scenario_id = scenario.get("scenario_id", str(uuid4()))
        started_at = datetime.utcnow()

        # Register fleet
        agents_data = scenario.get("agents", {})
        agents = agents_data.get("agents", [])
        if agents and self.config.register_agents:
            await self.register_fleet(agents, tenant_id)

        # Get workflows
        workflows_data = scenario.get("workflows", {})
        workflows = workflows_data.get("workflows", workflows_data) if isinstance(workflows_data, dict) else workflows_data
        if isinstance(workflows, dict):
            workflows = [workflows]

        # Get assignments
        agent_assignments = scenario.get("agent_assignments", {})

        # Execute all workflows
        workflow_results: List[WorkflowResult] = []

        for workflow in workflows:
            wf_assignments = agent_assignments.get(workflow.get("workflow_id"), {})
            result = await self.execute_workflow(workflow, wf_assignments, tenant_id)
            workflow_results.append(result)

        # Calculate aggregate metrics
        completed_at = datetime.utcnow()
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)

        workflows_completed = sum(1 for r in workflow_results if r.status == "completed")
        workflows_failed = sum(1 for r in workflow_results if r.status == "failed")

        total_tasks = sum(r.tasks_completed + r.tasks_failed for r in workflow_results)
        tasks_completed = sum(r.tasks_completed for r in workflow_results)
        tasks_failed = sum(r.tasks_failed for r in workflow_results)

        chaos_total = sum(r.chaos_events_handled for r in workflow_results)
        chaos_recovered = sum(r.chaos_events_recovered for r in workflow_results)

        total_tokens = sum(r.total_tokens for r in workflow_results)
        total_cost = sum(r.total_cost_usd for r in workflow_results)

        # Calculate rates
        completion_rate = workflows_completed / len(workflow_results) if workflow_results else 0.0
        chaos_recovery_rate = chaos_recovered / chaos_total if chaos_total > 0 else 1.0
        throughput_wf = len(workflow_results) / (duration_ms / 1000) if duration_ms > 0 else 0.0
        throughput_tasks = tasks_completed / (duration_ms / 1000) if duration_ms > 0 else 0.0
        avg_latency = duration_ms / len(workflow_results) if workflow_results else 0.0

        # FARM validation
        expected = scenario.get("__expected__", scenario.get("expected", {}))
        validation = self._validate_against_expected(
            completion_rate=completion_rate,
            chaos_recovery_rate=chaos_recovery_rate,
            total_tasks=total_tasks,
            tasks_completed=tasks_completed,
            chaos_total=chaos_total,
            chaos_recovered=chaos_recovered,
            expected=expected,
        )

        # Calculate verdict
        verdict = self._calculate_verdict(completion_rate, chaos_recovery_rate, validation)

        # Generate analysis
        analysis = self._generate_analysis(
            completion_rate=completion_rate,
            chaos_recovery_rate=chaos_recovery_rate,
            throughput_tasks=throughput_tasks,
            avg_latency=avg_latency,
            verdict=verdict,
        )

        # Update vitals
        if self._metrics_bridge:
            self._metrics_bridge.update_vitals()

        status = "completed" if workflows_failed == 0 else "completed_with_failures"

        return ExecutionResult(
            scenario_id=scenario_id,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            total_duration_ms=duration_ms,
            workflows_completed=workflows_completed,
            workflows_failed=workflows_failed,
            workflow_results=workflow_results,
            total_tasks=total_tasks,
            tasks_completed=tasks_completed,
            tasks_failed=tasks_failed,
            chaos_events_total=chaos_total,
            chaos_events_recovered=chaos_recovered,
            throughput_wf_per_sec=throughput_wf,
            throughput_tasks_per_sec=throughput_tasks,
            avg_latency_ms=avg_latency,
            total_tokens=total_tokens,
            total_cost_usd=total_cost,
            completion_rate=completion_rate,
            chaos_recovery_rate=chaos_recovery_rate,
            validation=validation,
            verdict=verdict,
            analysis=analysis,
        )

    def _validate_against_expected(
        self,
        completion_rate: float,
        chaos_recovery_rate: float,
        total_tasks: int,
        tasks_completed: int,
        chaos_total: int,
        chaos_recovered: int,
        expected: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Validate results against FARM __expected__ block."""
        validation = {}

        # Completion rate check
        expected_completion = expected.get("expected_completion_rate", 0.8)
        validation["completion_rate"] = {
            "expected": expected_completion,
            "actual": completion_rate,
            "passed": completion_rate >= expected_completion,
        }

        # Chaos recovery check
        expected_chaos = expected.get("chaos_recovery_possible", True)
        if expected_chaos:
            validation["chaos_recovery"] = {
                "expected": 0.8,  # 80% threshold
                "actual": chaos_recovery_rate,
                "passed": chaos_recovery_rate >= 0.8,
            }

        # Task completion check
        expected_tasks = expected.get("total_tasks", total_tasks)
        task_completion_rate = tasks_completed / total_tasks if total_tasks > 0 else 0
        validation["task_completion"] = {
            "expected_tasks": expected_tasks,
            "actual_tasks": total_tasks,
            "completion_rate": task_completion_rate,
            "passed": task_completion_rate >= 0.9,
        }

        # Chaos events check
        expected_chaos_events = expected.get("chaos_events_expected", 0)
        validation["chaos_events"] = {
            "expected": expected_chaos_events,
            "actual": chaos_total,
            "recovered": chaos_recovered,
            "passed": True,  # Informational
        }

        return validation

    def _calculate_verdict(
        self,
        completion_rate: float,
        chaos_recovery_rate: float,
        validation: Dict[str, Any],
    ) -> str:
        """Calculate FARM verdict."""
        # Check all validation results
        all_passed = all(
            v.get("passed", True) for v in validation.values()
            if isinstance(v, dict)
        )

        if completion_rate >= 0.95 and chaos_recovery_rate >= 0.8 and all_passed:
            return "PASS"
        elif completion_rate >= 0.8 and chaos_recovery_rate >= 0.5:
            return "DEGRADED"
        else:
            return "FAIL"

    def _generate_analysis(
        self,
        completion_rate: float,
        chaos_recovery_rate: float,
        throughput_tasks: float,
        avg_latency: float,
        verdict: str,
    ) -> Dict[str, Any]:
        """Generate FARM-compatible operator analysis."""
        sections = {}

        # Reliability section
        reliability_findings = []
        if completion_rate >= 0.95:
            reliability_findings.append(f"Completion rate {completion_rate:.1%} exceeds 95% threshold")
        elif completion_rate >= 0.8:
            reliability_findings.append(f"Completion rate {completion_rate:.1%} is degraded (80-95%)")
        else:
            reliability_findings.append(f"Completion rate {completion_rate:.1%} is below 80% threshold")

        sections["reliability"] = {
            "verdict": "PASS" if completion_rate >= 0.95 else "DEGRADED" if completion_rate >= 0.8 else "FAIL",
            "findings": reliability_findings,
        }

        # Performance section
        performance_findings = []
        if throughput_tasks >= 1.0:
            performance_findings.append(f"Throughput: {throughput_tasks:.1f} tasks/sec (above 1.0 minimum)")
        else:
            performance_findings.append(f"Throughput: {throughput_tasks:.1f} tasks/sec (below 1.0 target)")

        if avg_latency < 1000:
            performance_findings.append(f"Average latency: {avg_latency:.0f}ms (under 1000ms target)")
        else:
            performance_findings.append(f"Average latency: {avg_latency:.0f}ms (exceeds 1000ms target)")

        sections["performance"] = {
            "verdict": "PASS" if throughput_tasks >= 1.0 and avg_latency < 1000 else "DEGRADED",
            "findings": performance_findings,
        }

        # Resilience section
        resilience_findings = []
        if chaos_recovery_rate >= 0.8:
            resilience_findings.append(f"Chaos recovery rate: {chaos_recovery_rate:.1%}")
        else:
            resilience_findings.append(f"Chaos recovery rate: {chaos_recovery_rate:.1%} (below 80% target)")

        sections["resilience"] = {
            "verdict": "PASS" if chaos_recovery_rate >= 0.8 else "DEGRADED" if chaos_recovery_rate >= 0.5 else "FAIL",
            "findings": resilience_findings,
        }

        # Recommendations
        recommendations = []
        if completion_rate < 0.95:
            recommendations.append("Investigate workflow failures to improve completion rate")
        if chaos_recovery_rate < 0.8:
            recommendations.append("Improve chaos handling for better resilience")
        if throughput_tasks < 1.0:
            recommendations.append("Optimize task execution for better throughput")

        return {
            "verdict": verdict,
            "title": f"Stress Test {verdict}",
            "summary": f"Platform achieved {completion_rate:.1%} completion rate with {chaos_recovery_rate:.1%} chaos recovery.",
            "sections": sections,
            "recommendations": recommendations,
            "metrics": {
                "completion_rate": completion_rate,
                "chaos_recovery_rate": chaos_recovery_rate,
                "throughput_tasks_per_sec": throughput_tasks,
                "avg_latency_ms": avg_latency,
            }
        }

    def cleanup(self) -> None:
        """Clean up registered agents and state."""
        self._registered_agents.clear()
        self._active_locks.clear()
        if self._metrics_bridge:
            self._metrics_bridge.reset()


# Singleton instance
_simulation_executor: Optional[SimulationExecutor] = None


def get_simulation_executor() -> SimulationExecutor:
    """Get singleton simulation executor."""
    global _simulation_executor
    if _simulation_executor is None:
        _simulation_executor = SimulationExecutor()
        _simulation_executor.initialize()
    return _simulation_executor
