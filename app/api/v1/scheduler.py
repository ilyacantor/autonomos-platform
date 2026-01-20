"""
Scheduler API Endpoints

REST API for managing scheduled agent jobs:
- CRUD operations for scheduled jobs
- Job execution history
- Webhook triggers
- Manual job triggers
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Header, Request
from pydantic import BaseModel, Field

from app.agentic.scheduler.models import (
    ScheduledJob,
    JobTrigger,
    JobExecution,
    TriggerType,
    JobStatus,
    ExecutionStatus,
    ScheduledJobCreate,
    ScheduledJobUpdate,
    ScheduledJobResponse,
    JobExecutionResponse,
    JobTriggerCreate,
)
from app.agentic.scheduler.cron import CronParser, validate_cron, describe_cron
from app.agentic.scheduler.executor import get_scheduler_executor

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


# Request/Response Models

class CronValidateRequest(BaseModel):
    """Request to validate a cron expression."""
    expression: str


class CronValidateResponse(BaseModel):
    """Response for cron validation."""
    valid: bool
    error: Optional[str] = None
    description: Optional[str] = None
    next_runs: Optional[List[str]] = None


class JobListResponse(BaseModel):
    """Response for listing jobs."""
    jobs: List[ScheduledJobResponse]
    total: int
    limit: int
    offset: int


class ExecutionListResponse(BaseModel):
    """Response for listing executions."""
    executions: List[JobExecutionResponse]
    total: int
    limit: int
    offset: int


class TriggerResponse(BaseModel):
    """Response for manual job trigger."""
    execution_id: str
    job_id: str
    message: str


class WebhookTriggerResponse(BaseModel):
    """Response for webhook trigger."""
    execution_id: Optional[str]
    job_id: str
    accepted: bool
    message: str


class QueueStatsResponse(BaseModel):
    """Response for queue statistics."""
    pending: int
    processing: int
    dead_letter: int
    total: int


# Helper functions

def get_tenant_id(x_tenant_id: Optional[str] = Header(None)) -> UUID:
    """Extract tenant ID from header or use default."""
    if x_tenant_id:
        try:
            return UUID(x_tenant_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid tenant ID format")
    # Default tenant for demo
    return UUID("00000000-0000-0000-0000-000000000001")


def get_user_id(authorization: Optional[str] = Header(None)) -> Optional[UUID]:
    """Extract user ID from authorization header."""
    # In production, decode JWT and extract user ID
    return None


# Endpoints

@router.post("/jobs", response_model=ScheduledJobResponse, status_code=201)
async def create_job(
    job_data: ScheduledJobCreate,
    tenant_id: UUID = Depends(get_tenant_id),
    user_id: Optional[UUID] = Depends(get_user_id),
):
    """
    Create a new scheduled job.

    The job will be scheduled according to its trigger configuration:
    - cron: Run on a cron schedule
    - interval: Run at fixed intervals
    - once: Run once at a specified time
    - webhook: Run when triggered by webhook
    - event: Run when triggered by an event
    """
    executor = get_scheduler_executor()

    # Validate cron expression if provided
    if job_data.trigger.trigger_type == TriggerType.CRON:
        if not job_data.trigger.cron_expression:
            raise HTTPException(
                status_code=400,
                detail="cron_expression required for cron trigger"
            )
        valid, error = validate_cron(job_data.trigger.cron_expression)
        if not valid:
            raise HTTPException(status_code=400, detail=f"Invalid cron: {error}")

    # Create trigger
    trigger = JobTrigger(
        trigger_type=job_data.trigger.trigger_type,
        cron_expression=job_data.trigger.cron_expression,
        timezone=job_data.trigger.timezone,
        interval_seconds=job_data.trigger.interval_seconds,
        run_at=job_data.trigger.run_at,
        event_type=job_data.trigger.event_type,
        event_filter=job_data.trigger.event_filter,
    )

    # Generate webhook secret if needed
    if trigger.trigger_type == TriggerType.WEBHOOK:
        import secrets
        trigger.webhook_secret = secrets.token_urlsafe(32)

    # Create job
    job = ScheduledJob(
        job_id=uuid4(),
        tenant_id=tenant_id,
        name=job_data.name,
        description=job_data.description,
        agent_id=job_data.agent_id,
        input_template=job_data.input_template,
        input_variables=job_data.input_variables,
        trigger=trigger,
        timeout_seconds=job_data.timeout_seconds,
        max_retries=job_data.max_retries,
        allow_concurrent=job_data.allow_concurrent,
        start_date=job_data.start_date,
        end_date=job_data.end_date,
        created_by=user_id,
    )

    # Register with executor
    created_job = await executor.create_job(job)

    return ScheduledJobResponse(**created_job.to_dict())


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    status: Optional[JobStatus] = None,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    tenant_id: UUID = Depends(get_tenant_id),
):
    """
    List scheduled jobs.

    Optionally filter by status (active, paused, disabled, expired).
    """
    executor = get_scheduler_executor()

    jobs = await executor.list_jobs(
        tenant_id=str(tenant_id),
        status=status,
        limit=limit + offset,
    )

    # Apply offset
    jobs = jobs[offset:offset + limit]

    return JobListResponse(
        jobs=[ScheduledJobResponse(**j.to_dict()) for j in jobs],
        total=len(jobs),
        limit=limit,
        offset=offset,
    )


@router.get("/jobs/{job_id}", response_model=ScheduledJobResponse)
async def get_job(
    job_id: str,
    tenant_id: UUID = Depends(get_tenant_id),
):
    """Get a scheduled job by ID."""
    executor = get_scheduler_executor()

    job = await executor.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if str(job.tenant_id) != str(tenant_id):
        raise HTTPException(status_code=404, detail="Job not found")

    return ScheduledJobResponse(**job.to_dict())


@router.patch("/jobs/{job_id}", response_model=ScheduledJobResponse)
async def update_job(
    job_id: str,
    updates: ScheduledJobUpdate,
    tenant_id: UUID = Depends(get_tenant_id),
):
    """
    Update a scheduled job.

    Only provided fields will be updated.
    """
    executor = get_scheduler_executor()

    job = await executor.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if str(job.tenant_id) != str(tenant_id):
        raise HTTPException(status_code=404, detail="Job not found")

    # Build updates dict
    update_dict = updates.model_dump(exclude_unset=True)

    # Handle trigger update
    if "trigger" in update_dict and update_dict["trigger"]:
        trigger_data = update_dict.pop("trigger")
        update_dict["trigger"] = JobTrigger(
            trigger_type=trigger_data.get("trigger_type", job.trigger.trigger_type),
            cron_expression=trigger_data.get("cron_expression", job.trigger.cron_expression),
            timezone=trigger_data.get("timezone", job.trigger.timezone),
            interval_seconds=trigger_data.get("interval_seconds", job.trigger.interval_seconds),
            run_at=trigger_data.get("run_at", job.trigger.run_at),
            event_type=trigger_data.get("event_type", job.trigger.event_type),
            event_filter=trigger_data.get("event_filter", job.trigger.event_filter),
            webhook_secret=job.trigger.webhook_secret,
        )

    updated_job = await executor.update_job(job_id, update_dict)
    if not updated_job:
        raise HTTPException(status_code=500, detail="Failed to update job")

    return ScheduledJobResponse(**updated_job.to_dict())


@router.delete("/jobs/{job_id}", status_code=204)
async def delete_job(
    job_id: str,
    tenant_id: UUID = Depends(get_tenant_id),
):
    """Delete a scheduled job."""
    executor = get_scheduler_executor()

    job = await executor.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if str(job.tenant_id) != str(tenant_id):
        raise HTTPException(status_code=404, detail="Job not found")

    await executor.delete_job(job_id)


@router.post("/jobs/{job_id}/pause", response_model=ScheduledJobResponse)
async def pause_job(
    job_id: str,
    tenant_id: UUID = Depends(get_tenant_id),
):
    """Pause a scheduled job."""
    executor = get_scheduler_executor()

    job = await executor.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if str(job.tenant_id) != str(tenant_id):
        raise HTTPException(status_code=404, detail="Job not found")

    success = await executor.pause_job(job_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to pause job")

    job = await executor.get_job(job_id)
    return ScheduledJobResponse(**job.to_dict())


@router.post("/jobs/{job_id}/resume", response_model=ScheduledJobResponse)
async def resume_job(
    job_id: str,
    tenant_id: UUID = Depends(get_tenant_id),
):
    """Resume a paused job."""
    executor = get_scheduler_executor()

    job = await executor.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if str(job.tenant_id) != str(tenant_id):
        raise HTTPException(status_code=404, detail="Job not found")

    success = await executor.resume_job(job_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to resume job")

    job = await executor.get_job(job_id)
    return ScheduledJobResponse(**job.to_dict())


@router.post("/jobs/{job_id}/trigger", response_model=TriggerResponse)
async def trigger_job(
    job_id: str,
    tenant_id: UUID = Depends(get_tenant_id),
):
    """
    Manually trigger a job execution.

    This bypasses the schedule and runs the job immediately.
    """
    executor = get_scheduler_executor()

    job = await executor.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if str(job.tenant_id) != str(tenant_id):
        raise HTTPException(status_code=404, detail="Job not found")

    execution_id = await executor.trigger_job(job_id)
    if not execution_id:
        raise HTTPException(status_code=500, detail="Failed to trigger job")

    return TriggerResponse(
        execution_id=execution_id,
        job_id=job_id,
        message="Job triggered successfully",
    )


@router.get("/jobs/{job_id}/executions", response_model=ExecutionListResponse)
async def list_job_executions(
    job_id: str,
    status: Optional[ExecutionStatus] = None,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    tenant_id: UUID = Depends(get_tenant_id),
):
    """List executions for a specific job."""
    executor = get_scheduler_executor()

    job = await executor.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if str(job.tenant_id) != str(tenant_id):
        raise HTTPException(status_code=404, detail="Job not found")

    executions = await executor.list_executions(
        job_id=job_id,
        status=status,
        limit=limit + offset,
    )

    executions = executions[offset:offset + limit]

    return ExecutionListResponse(
        executions=[JobExecutionResponse(**e.to_dict()) for e in executions],
        total=len(executions),
        limit=limit,
        offset=offset,
    )


@router.get("/executions/{execution_id}", response_model=JobExecutionResponse)
async def get_execution(
    execution_id: str,
    tenant_id: UUID = Depends(get_tenant_id),
):
    """Get a specific execution by ID."""
    executor = get_scheduler_executor()

    execution = await executor.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    # Verify tenant access via job
    job = await executor.get_job(str(execution.job_id))
    if not job or str(job.tenant_id) != str(tenant_id):
        raise HTTPException(status_code=404, detail="Execution not found")

    return JobExecutionResponse(**execution.to_dict())


@router.post("/webhook/{job_id}", response_model=WebhookTriggerResponse)
async def webhook_trigger(
    job_id: str,
    request: Request,
    x_webhook_secret: Optional[str] = Header(None),
):
    """
    Webhook endpoint to trigger a job.

    Requires the correct webhook secret in the X-Webhook-Secret header.
    """
    executor = get_scheduler_executor()

    job = await executor.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.trigger.trigger_type != TriggerType.WEBHOOK:
        raise HTTPException(status_code=400, detail="Job is not webhook-triggered")

    # Verify webhook secret
    if job.trigger.webhook_secret and job.trigger.webhook_secret != x_webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    if job.status != JobStatus.ACTIVE:
        return WebhookTriggerResponse(
            execution_id=None,
            job_id=job_id,
            accepted=False,
            message=f"Job is {job.status.value}",
        )

    # Get webhook payload
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    execution_id = await executor.handle_webhook(job_id, payload)

    return WebhookTriggerResponse(
        execution_id=execution_id,
        job_id=job_id,
        accepted=True,
        message="Webhook accepted",
    )


@router.post("/cron/validate", response_model=CronValidateResponse)
async def validate_cron_expression(data: CronValidateRequest):
    """
    Validate a cron expression and get next run times.

    Returns whether the expression is valid, a human-readable
    description, and the next 5 scheduled run times.
    """
    valid, error = validate_cron(data.expression)

    if not valid:
        return CronValidateResponse(
            valid=False,
            error=error,
        )

    # Get description and next runs
    description = describe_cron(data.expression)

    try:
        cron = CronParser.parse(data.expression)
        next_runs = cron.next_runs(5)
        next_runs_str = [r.isoformat() for r in next_runs]
    except Exception:
        next_runs_str = []

    return CronValidateResponse(
        valid=True,
        description=description,
        next_runs=next_runs_str,
    )


@router.get("/queue/stats", response_model=QueueStatsResponse)
async def get_queue_stats(
    tenant_id: UUID = Depends(get_tenant_id),
):
    """Get job queue statistics."""
    from app.agentic.scheduler.queue import get_job_queue

    queue = get_job_queue()
    stats = await queue.get_stats()

    return QueueStatsResponse(**stats)
