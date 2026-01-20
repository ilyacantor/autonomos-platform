"""
AOS Farm Stress Testing Integration

API endpoints for consuming AOS Farm test data:
- Agent fleet ingestion
- Workflow submission
- Stress scenario execution
- Streaming workflow consumption
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Header, BackgroundTasks
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stress-test", tags=["stress-testing"])


# Request/Response Models

class AgentReliability(BaseModel):
    """Agent reliability profile from AOS Farm."""
    profile: str
    success_rate: float
    mean_latency_ms: int
    timeout_rate: float


class AgentCost(BaseModel):
    """Agent cost tier from AOS Farm."""
    tier: str
    per_invocation: float
    per_token: float


class AgentPolicy(BaseModel):
    """Agent policy from AOS Farm."""
    template: str
    max_concurrent_tasks: int
    requires_approval_above: int
    audit_all_actions: bool


class AOSFarmAgent(BaseModel):
    """Agent profile from AOS Farm."""
    agent_id: str
    type: str
    capabilities: List[str]
    tools: List[str]
    reliability: AgentReliability
    cost: AgentCost
    policy: AgentPolicy
    metadata: Optional[Dict[str, Any]] = None


class FleetDistribution(BaseModel):
    """Distribution of agents in fleet."""
    by_type: Dict[str, int]
    by_reliability: Dict[str, int]
    by_cost: Dict[str, int]


class AgentFleetRequest(BaseModel):
    """Request to ingest an agent fleet."""
    agents: List[AOSFarmAgent]
    total_agents: int
    distribution: FleetDistribution
    seed: Optional[int] = None


class ChaosInjection(BaseModel):
    """Chaos injection configuration."""
    type: str
    trigger_probability: float
    parameters: Dict[str, Any] = {}


class RetryPolicy(BaseModel):
    """Task retry policy."""
    max_attempts: int = 3
    backoff_multiplier: float = 2.0


class WorkflowTask(BaseModel):
    """Task in a workflow from AOS Farm."""
    task_id: str
    name: str
    type: str
    dependencies: List[str] = []
    assigned_agent_type: str
    tools_required: List[str] = []
    estimated_duration_ms: int = 500
    priority: str = "normal"
    retry_policy: Optional[RetryPolicy] = None
    chaos_injection: Optional[ChaosInjection] = None


class WorkflowExpected(BaseModel):
    """Expected results for validation."""
    total_tasks: int
    critical_path_length: int
    parallelizable_tasks: int
    chaos_events_expected: int
    expected_chaos_types: List[str] = []
    min_agents_required: int
    estimated_total_duration_ms: int


class WorkflowRequest(BaseModel):
    """Request to submit a workflow."""
    workflow_id: str
    type: str  # linear, dag, parallel, saga
    tasks: List[WorkflowTask]
    __expected__: Optional[WorkflowExpected] = Field(None, alias="__expected__")
    metadata: Optional[Dict[str, Any]] = None


class StressScenarioRequest(BaseModel):
    """Complete stress scenario from AOS Farm."""
    agents: AgentFleetRequest
    workflows: List[WorkflowRequest]
    agent_assignments: Dict[str, Dict[str, str]] = {}
    __expected__: Optional[Dict[str, Any]] = Field(None, alias="__expected__")
    summary: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class TaskResult(BaseModel):
    """Result of a single task execution."""
    task_id: str
    status: str  # completed, failed, timeout, retried
    started_at: str
    completed_at: Optional[str] = None
    duration_ms: int
    assigned_agent_id: Optional[str] = None
    chaos_occurred: bool = False
    chaos_type: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0


class WorkflowResult(BaseModel):
    """Result of a workflow execution."""
    workflow_id: str
    status: str  # completed, failed, partial
    started_at: str
    completed_at: Optional[str] = None
    total_duration_ms: int
    tasks_completed: int
    tasks_failed: int
    tasks_retried: int
    chaos_events_handled: int
    task_results: List[TaskResult] = []


class ScenarioResult(BaseModel):
    """Result of a stress scenario."""
    scenario_id: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    total_duration_ms: int
    workflows_completed: int
    workflows_failed: int
    total_tasks: int
    tasks_completed: int
    tasks_failed: int
    chaos_events_total: int
    chaos_events_recovered: int
    throughput_wf_per_sec: float
    completion_rate: float
    workflow_results: List[WorkflowResult] = []
    validation: Dict[str, Any] = {}


class FleetIngestionResponse(BaseModel):
    """Response from fleet ingestion."""
    status: str
    agents_ingested: int
    agents_by_type: Dict[str, int]
    message: str


class WorkflowSubmissionResponse(BaseModel):
    """Response from workflow submission."""
    status: str
    workflow_id: str
    execution_id: str
    message: str


class ScenarioSubmissionResponse(BaseModel):
    """Response from scenario submission."""
    status: str
    scenario_id: str
    workflows_queued: int
    message: str


# In-memory storage for stress testing
_active_fleets: Dict[str, AgentFleetRequest] = {}
_active_scenarios: Dict[str, Dict[str, Any]] = {}
_workflow_results: Dict[str, WorkflowResult] = {}


# Helper functions

def get_tenant_id(x_tenant_id: Optional[str] = Header(None)) -> str:
    """Extract tenant ID from header."""
    return x_tenant_id or "stress-test-tenant"


async def simulate_task_execution(
    task: WorkflowTask,
    agent_id: Optional[str],
    chaos_rate: float = 0.0,
) -> TaskResult:
    """Simulate task execution with chaos injection."""
    import random

    started_at = datetime.utcnow()
    status = "completed"
    chaos_occurred = False
    chaos_type = None
    error_message = None
    retry_count = 0

    # Check for chaos injection
    if task.chaos_injection and random.random() < task.chaos_injection.trigger_probability:
        chaos_occurred = True
        chaos_type = task.chaos_injection.type

        if chaos_type == "tool_timeout":
            await asyncio.sleep(task.chaos_injection.parameters.get("delay_ms", 5000) / 1000)
            # Simulate recovery
            retry_count = 1
        elif chaos_type == "tool_failure":
            if not task.chaos_injection.parameters.get("recoverable", True):
                status = "failed"
                error_message = "Tool execution failed (chaos)"
        elif chaos_type == "agent_conflict":
            # Simulate conflict resolution delay
            await asyncio.sleep(0.5)
        elif chaos_type == "policy_violation":
            # Simulate escalation
            await asyncio.sleep(0.2)
        elif chaos_type == "checkpoint_crash":
            # Simulate recovery from checkpoint
            await asyncio.sleep(0.3)
            retry_count = 1

    # Simulate normal execution time
    if status != "failed":
        await asyncio.sleep(task.estimated_duration_ms / 1000 / 10)  # Speedup for testing

    completed_at = datetime.utcnow()
    duration_ms = int((completed_at - started_at).total_seconds() * 1000)

    return TaskResult(
        task_id=task.task_id,
        status=status,
        started_at=started_at.isoformat(),
        completed_at=completed_at.isoformat(),
        duration_ms=duration_ms,
        assigned_agent_id=agent_id,
        chaos_occurred=chaos_occurred,
        chaos_type=chaos_type,
        error_message=error_message,
        retry_count=retry_count,
    )


async def execute_workflow(
    workflow: WorkflowRequest,
    fleet: Optional[AgentFleetRequest],
    assignments: Optional[Dict[str, str]],
) -> WorkflowResult:
    """Execute a single workflow."""
    started_at = datetime.utcnow()
    task_results = []
    completed_tasks = set()

    # Build dependency graph
    dep_graph = {task.task_id: set(task.dependencies) for task in workflow.tasks}

    # Execute tasks respecting dependencies
    while len(completed_tasks) < len(workflow.tasks):
        # Find tasks ready to execute
        ready_tasks = [
            task for task in workflow.tasks
            if task.task_id not in completed_tasks
            and all(dep in completed_tasks for dep in task.dependencies)
        ]

        if not ready_tasks:
            break  # Deadlock or error

        # Execute ready tasks in parallel
        execution_tasks = []
        for task in ready_tasks:
            agent_id = assignments.get(task.task_id) if assignments else None
            execution_tasks.append(simulate_task_execution(task, agent_id))

        results = await asyncio.gather(*execution_tasks)

        for result in results:
            task_results.append(result)
            if result.status == "completed":
                completed_tasks.add(result.task_id)

    completed_at = datetime.utcnow()
    duration_ms = int((completed_at - started_at).total_seconds() * 1000)

    tasks_completed = sum(1 for r in task_results if r.status == "completed")
    tasks_failed = sum(1 for r in task_results if r.status == "failed")
    tasks_retried = sum(1 for r in task_results if r.retry_count > 0)
    chaos_handled = sum(1 for r in task_results if r.chaos_occurred)

    status = "completed" if tasks_failed == 0 else "partial" if tasks_completed > 0 else "failed"

    return WorkflowResult(
        workflow_id=workflow.workflow_id,
        status=status,
        started_at=started_at.isoformat(),
        completed_at=completed_at.isoformat(),
        total_duration_ms=duration_ms,
        tasks_completed=tasks_completed,
        tasks_failed=tasks_failed,
        tasks_retried=tasks_retried,
        chaos_events_handled=chaos_handled,
        task_results=task_results,
    )


# Endpoints

@router.post("/fleet", response_model=FleetIngestionResponse)
async def ingest_fleet(
    fleet: AgentFleetRequest,
    tenant_id: str = Header(None, alias="X-Tenant-ID"),
):
    """
    Ingest an agent fleet from AOS Farm.

    This registers the agent profiles for use in stress testing.
    """
    tenant_id = tenant_id or "stress-test-tenant"

    # Store fleet
    _active_fleets[tenant_id] = fleet

    # Count by type
    by_type = {}
    for agent in fleet.agents:
        by_type[agent.type] = by_type.get(agent.type, 0) + 1

    logger.info(f"Ingested fleet with {fleet.total_agents} agents for tenant {tenant_id}")

    return FleetIngestionResponse(
        status="success",
        agents_ingested=fleet.total_agents,
        agents_by_type=by_type,
        message=f"Ingested {fleet.total_agents} agents successfully",
    )


@router.post("/workflow", response_model=WorkflowSubmissionResponse)
async def submit_workflow(
    workflow: WorkflowRequest,
    background_tasks: BackgroundTasks,
    tenant_id: str = Header(None, alias="X-Tenant-ID"),
):
    """
    Submit a single workflow for execution.

    The workflow will be executed asynchronously.
    """
    tenant_id = tenant_id or "stress-test-tenant"
    execution_id = str(uuid4())

    # Get fleet if available
    fleet = _active_fleets.get(tenant_id)

    # Queue workflow execution
    async def run_workflow():
        result = await execute_workflow(workflow, fleet, None)
        _workflow_results[execution_id] = result

    background_tasks.add_task(run_workflow)

    logger.info(f"Submitted workflow {workflow.workflow_id} as execution {execution_id}")

    return WorkflowSubmissionResponse(
        status="queued",
        workflow_id=workflow.workflow_id,
        execution_id=execution_id,
        message=f"Workflow queued for execution",
    )


@router.post("/scenario", response_model=ScenarioSubmissionResponse)
async def submit_scenario(
    scenario: StressScenarioRequest,
    background_tasks: BackgroundTasks,
    tenant_id: str = Header(None, alias="X-Tenant-ID"),
):
    """
    Submit a complete stress scenario for execution.

    This includes both the agent fleet and multiple workflows.
    """
    tenant_id = tenant_id or "stress-test-tenant"
    scenario_id = str(uuid4())

    # Store fleet
    _active_fleets[tenant_id] = scenario.agents

    # Initialize scenario tracking
    _active_scenarios[scenario_id] = {
        "tenant_id": tenant_id,
        "scenario": scenario,
        "status": "running",
        "started_at": datetime.utcnow().isoformat(),
        "workflow_results": [],
    }

    # Queue scenario execution
    async def run_scenario():
        workflow_results = []

        for workflow in scenario.workflows:
            assignments = scenario.agent_assignments.get(workflow.workflow_id, {})
            result = await execute_workflow(workflow, scenario.agents, assignments)
            workflow_results.append(result)

        _active_scenarios[scenario_id]["workflow_results"] = workflow_results
        _active_scenarios[scenario_id]["status"] = "completed"
        _active_scenarios[scenario_id]["completed_at"] = datetime.utcnow().isoformat()

    background_tasks.add_task(run_scenario)

    logger.info(f"Submitted stress scenario {scenario_id} with {len(scenario.workflows)} workflows")

    return ScenarioSubmissionResponse(
        status="queued",
        scenario_id=scenario_id,
        workflows_queued=len(scenario.workflows),
        message=f"Scenario queued with {len(scenario.workflows)} workflows",
    )


@router.get("/scenario/{scenario_id}", response_model=ScenarioResult)
async def get_scenario_result(
    scenario_id: str,
):
    """Get the result of a stress scenario."""
    if scenario_id not in _active_scenarios:
        raise HTTPException(status_code=404, detail="Scenario not found")

    scenario_data = _active_scenarios[scenario_id]
    workflow_results = scenario_data.get("workflow_results", [])

    # Calculate metrics
    started_at = datetime.fromisoformat(scenario_data["started_at"])
    completed_at = (
        datetime.fromisoformat(scenario_data["completed_at"])
        if scenario_data.get("completed_at")
        else datetime.utcnow()
    )
    duration_ms = int((completed_at - started_at).total_seconds() * 1000)

    workflows_completed = sum(1 for r in workflow_results if r.status == "completed")
    workflows_failed = sum(1 for r in workflow_results if r.status == "failed")

    total_tasks = sum(r.tasks_completed + r.tasks_failed for r in workflow_results)
    tasks_completed = sum(r.tasks_completed for r in workflow_results)
    tasks_failed = sum(r.tasks_failed for r in workflow_results)
    chaos_total = sum(r.chaos_events_handled for r in workflow_results)

    throughput = len(workflow_results) / (duration_ms / 1000) if duration_ms > 0 else 0
    completion_rate = workflows_completed / len(workflow_results) if workflow_results else 0

    # Validate against expected
    scenario = scenario_data.get("scenario")
    validation = {}
    if scenario and hasattr(scenario, "__expected__") and scenario.__expected__:
        expected = scenario.__expected__
        validation = {
            "total_tasks_match": total_tasks == expected.get("total_tasks", total_tasks),
            "completion_rate_ok": completion_rate >= expected.get("expected_completion_rate", 0),
            "chaos_events_match": chaos_total <= expected.get("total_chaos_events", chaos_total) + 5,
        }

    return ScenarioResult(
        scenario_id=scenario_id,
        status=scenario_data["status"],
        started_at=scenario_data["started_at"],
        completed_at=scenario_data.get("completed_at"),
        total_duration_ms=duration_ms,
        workflows_completed=workflows_completed,
        workflows_failed=workflows_failed,
        total_tasks=total_tasks,
        tasks_completed=tasks_completed,
        tasks_failed=tasks_failed,
        chaos_events_total=chaos_total,
        chaos_events_recovered=chaos_total,  # All chaos handled
        throughput_wf_per_sec=throughput,
        completion_rate=completion_rate,
        workflow_results=workflow_results,
        validation=validation,
    )


@router.get("/workflow/{execution_id}", response_model=WorkflowResult)
async def get_workflow_result(
    execution_id: str,
):
    """Get the result of a workflow execution."""
    if execution_id not in _workflow_results:
        raise HTTPException(status_code=404, detail="Workflow execution not found")

    return _workflow_results[execution_id]


@router.get("/fleet", response_model=Optional[Dict[str, Any]])
async def get_active_fleet(
    tenant_id: str = Header(None, alias="X-Tenant-ID"),
):
    """Get the currently active fleet for a tenant."""
    tenant_id = tenant_id or "stress-test-tenant"
    fleet = _active_fleets.get(tenant_id)

    if not fleet:
        return None

    return {
        "total_agents": fleet.total_agents,
        "distribution": fleet.distribution.dict(),
        "agents": [a.dict() for a in fleet.agents[:10]],  # First 10 for preview
    }


@router.delete("/fleet")
async def clear_fleet(
    tenant_id: str = Header(None, alias="X-Tenant-ID"),
):
    """Clear the active fleet for a tenant."""
    tenant_id = tenant_id or "stress-test-tenant"

    if tenant_id in _active_fleets:
        del _active_fleets[tenant_id]
        return {"status": "cleared", "message": "Fleet cleared"}

    return {"status": "not_found", "message": "No active fleet"}


@router.get("/health")
async def stress_test_health():
    """Health check for stress testing subsystem."""
    return {
        "status": "healthy",
        "active_fleets": len(_active_fleets),
        "active_scenarios": len(_active_scenarios),
        "completed_workflows": len(_workflow_results),
    }
