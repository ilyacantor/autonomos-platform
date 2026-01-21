"""
Scaling API Endpoints

REST API for horizontal scaling management:
- Task queue operations
- Worker pool management
- Scaling controls
- Metrics and monitoring
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.security import get_current_user
from app.agentic.scaling import (
    TaskQueue,
    Task,
    TaskStatus,
    TaskPriority,
    get_task_queue,
    WorkerPool,
    PoolConfig,
    ScalingPolicy,
    get_worker_pool,
)

router = APIRouter(prefix="/scaling", tags=["Scaling"])


# =============================================================================
# Request/Response Schemas
# =============================================================================

class TaskCreateRequest(BaseModel):
    """Request to create a task."""
    task_type: str = "agent_run"
    payload: Dict[str, Any] = Field(default_factory=dict)
    agent_id: Optional[UUID] = None
    run_id: Optional[UUID] = None
    priority: int = Field(default=5, ge=1, le=10)
    scheduled_at: Optional[datetime] = None
    timeout_seconds: int = Field(default=300, ge=30, le=3600)
    max_retries: int = Field(default=3, ge=0, le=10)


class TaskResponse(BaseModel):
    """Task response."""
    id: str
    task_type: str
    status: str
    priority: int
    worker_id: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    result: Optional[Any]
    error: Optional[str]
    retry_count: int
    max_retries: int


class QueueStatsResponse(BaseModel):
    """Queue statistics response."""
    total_pending: int
    pending: Dict[str, int]
    scheduled: int
    processing: int
    dead: int


class WorkerStatusResponse(BaseModel):
    """Worker status response."""
    worker_id: str
    status: str
    started_at: Optional[datetime]
    last_health_check: Optional[datetime]
    consecutive_failures: int


class PoolStatusResponse(BaseModel):
    """Pool status response."""
    pool_id: str
    workers_total: int
    workers_idle: int
    workers_processing: int
    workers_error: int
    queue_pending: int
    tasks_processed: int
    tasks_completed: int
    tasks_failed: int


class ScaleRequest(BaseModel):
    """Request to scale workers."""
    target_workers: int = Field(..., ge=1, le=100)


class PoolMetricsResponse(BaseModel):
    """Pool metrics response."""
    pool_id: str
    timestamp: datetime
    workers: Dict[str, int]
    queue: Dict[str, Any]
    totals: Dict[str, int]


# =============================================================================
# Task Queue Endpoints
# =============================================================================

@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    request: TaskCreateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Create a new task in the queue.

    Tasks are executed by workers asynchronously.
    """
    queue = get_task_queue()

    task = Task(
        task_type=request.task_type,
        payload=request.payload,
        agent_id=request.agent_id,
        tenant_id=current_user.tenant_id,
        run_id=request.run_id,
        priority=TaskPriority(request.priority),
        scheduled_at=request.scheduled_at,
        timeout_seconds=request.timeout_seconds,
        max_retries=request.max_retries,
    )

    await queue.enqueue(task)

    return TaskResponse(
        id=task.id,
        task_type=task.task_type,
        status=task.status.value,
        priority=task.priority.value,
        worker_id=task.worker_id,
        created_at=task.created_at,
        started_at=task.started_at,
        completed_at=task.completed_at,
        result=task.result,
        error=task.last_error,
        retry_count=task.retry_count,
        max_retries=task.max_retries,
    )


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get a task by ID."""
    queue = get_task_queue()
    task = await queue.get_task(task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    # Verify tenant access
    if task.tenant_id and task.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this task",
        )

    return TaskResponse(
        id=task.id,
        task_type=task.task_type,
        status=task.status.value,
        priority=task.priority.value,
        worker_id=task.worker_id,
        created_at=task.created_at,
        started_at=task.started_at,
        completed_at=task.completed_at,
        result=task.result,
        error=task.last_error,
        retry_count=task.retry_count,
        max_retries=task.max_retries,
    )


@router.post("/tasks/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Cancel a pending or assigned task."""
    queue = get_task_queue()
    task = await queue.cancel(task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    return TaskResponse(
        id=task.id,
        task_type=task.task_type,
        status=task.status.value,
        priority=task.priority.value,
        worker_id=task.worker_id,
        created_at=task.created_at,
        started_at=task.started_at,
        completed_at=task.completed_at,
        result=task.result,
        error=task.last_error,
        retry_count=task.retry_count,
        max_retries=task.max_retries,
    )


@router.get("/queue/stats", response_model=QueueStatsResponse)
async def get_queue_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get task queue statistics."""
    queue = get_task_queue()
    stats = await queue.get_queue_stats()

    return QueueStatsResponse(
        total_pending=stats.get("total_pending", 0),
        pending=stats.get("pending", {}),
        scheduled=stats.get("scheduled", 0),
        processing=stats.get("processing", 0),
        dead=stats.get("dead", 0),
    )


@router.post("/queue/cleanup")
async def cleanup_stale_tasks(
    threshold_seconds: int = Query(3600, ge=300, le=86400),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Clean up stale processing tasks."""
    queue = get_task_queue()
    cleaned = await queue.cleanup_stale_tasks(threshold_seconds)

    return {"cleaned_tasks": cleaned}


# =============================================================================
# Worker Pool Endpoints
# =============================================================================

@router.get("/pool/status", response_model=PoolStatusResponse)
async def get_pool_status(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get worker pool status."""
    pool = get_worker_pool()
    metrics = await pool.get_metrics()

    return PoolStatusResponse(
        pool_id=metrics["pool_id"],
        workers_total=metrics["workers"]["total"],
        workers_idle=metrics["workers"]["idle"],
        workers_processing=metrics["workers"]["processing"],
        workers_error=metrics["workers"]["error"],
        queue_pending=metrics["queue"].get("total_pending", 0),
        tasks_processed=metrics["totals"]["tasks_processed"],
        tasks_completed=metrics["totals"]["tasks_completed"],
        tasks_failed=metrics["totals"]["tasks_failed"],
    )


@router.get("/pool/workers", response_model=List[WorkerStatusResponse])
async def get_workers(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get status of all workers in the pool."""
    pool = get_worker_pool()
    workers = pool.get_worker_status()

    return [
        WorkerStatusResponse(
            worker_id=w["worker_id"],
            status=w["status"],
            started_at=datetime.fromisoformat(w["started_at"]) if w.get("started_at") else None,
            last_health_check=datetime.fromisoformat(w["last_health_check"]) if w.get("last_health_check") else None,
            consecutive_failures=w["consecutive_failures"],
        )
        for w in workers
    ]


@router.post("/pool/scale", response_model=PoolStatusResponse)
async def scale_pool(
    request: ScaleRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Scale the worker pool to a specific number of workers."""
    pool = get_worker_pool()
    await pool.scale_to(request.target_workers)

    # Return updated status
    metrics = await pool.get_metrics()

    return PoolStatusResponse(
        pool_id=metrics["pool_id"],
        workers_total=metrics["workers"]["total"],
        workers_idle=metrics["workers"]["idle"],
        workers_processing=metrics["workers"]["processing"],
        workers_error=metrics["workers"]["error"],
        queue_pending=metrics["queue"].get("total_pending", 0),
        tasks_processed=metrics["totals"]["tasks_processed"],
        tasks_completed=metrics["totals"]["tasks_completed"],
        tasks_failed=metrics["totals"]["tasks_failed"],
    )


@router.get("/pool/metrics", response_model=PoolMetricsResponse)
async def get_pool_metrics(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get detailed pool metrics."""
    pool = get_worker_pool()
    metrics = await pool.get_metrics()

    return PoolMetricsResponse(
        pool_id=metrics["pool_id"],
        timestamp=datetime.fromisoformat(metrics["timestamp"]),
        workers=metrics["workers"],
        queue=metrics["queue"],
        totals=metrics["totals"],
    )


# =============================================================================
# Agent Run Task Helpers
# =============================================================================

@router.post("/agents/{agent_id}/runs/queue", response_model=TaskResponse)
async def queue_agent_run(
    agent_id: UUID,
    input_text: str = Query(..., min_length=1, max_length=50000),
    priority: int = Query(5, ge=1, le=10),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Queue an agent run for async execution.

    The run will be executed by a worker when available.
    """
    # Verify agent belongs to tenant
    from sqlalchemy import and_
    agent = db.query(models.Agent).filter(
        and_(
            models.Agent.id == agent_id,
            models.Agent.tenant_id == current_user.tenant_id,
        )
    ).first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found",
        )

    # Create task
    queue = get_task_queue()
    task = Task(
        task_type="agent_run",
        payload={
            "input": input_text,
            "model": agent.model,
            "max_steps": agent.max_steps,
            "max_cost_usd": agent.max_cost_usd,
            "system_prompt": agent.system_prompt,
        },
        agent_id=agent_id,
        tenant_id=current_user.tenant_id,
        priority=TaskPriority(priority),
    )

    await queue.enqueue(task)

    return TaskResponse(
        id=task.id,
        task_type=task.task_type,
        status=task.status.value,
        priority=task.priority.value,
        worker_id=task.worker_id,
        created_at=task.created_at,
        started_at=task.started_at,
        completed_at=task.completed_at,
        result=task.result,
        error=task.last_error,
        retry_count=task.retry_count,
        max_retries=task.max_retries,
    )
