"""
Scheduler Executor

Background service that executes scheduled jobs.
Polls the job queue and triggers agent runs.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID, uuid4

from app.agentic.scheduler.models import (
    ScheduledJob,
    JobExecution,
    JobStatus,
    ExecutionStatus,
    TriggerType,
)
from app.agentic.scheduler.cron import CronParser
from app.agentic.scheduler.queue import JobQueue, QueuedJob, get_job_queue

logger = logging.getLogger(__name__)


class SchedulerExecutor:
    """
    Background executor for scheduled jobs.

    Responsibilities:
    - Poll for due jobs
    - Calculate next run times
    - Enqueue executions
    - Process the job queue
    - Handle retries and failures
    """

    def __init__(
        self,
        job_queue: Optional[JobQueue] = None,
        poll_interval: int = 10,
        batch_size: int = 10,
    ):
        """
        Initialize the scheduler executor.

        Args:
            job_queue: Job queue instance
            poll_interval: Seconds between polls for due jobs
            batch_size: Max jobs to process per poll
        """
        self.queue = job_queue or get_job_queue()
        self.poll_interval = poll_interval
        self.batch_size = batch_size

        # Job storage (in production, use database)
        self._jobs: Dict[str, ScheduledJob] = {}
        self._executions: Dict[str, JobExecution] = {}

        # Callbacks
        self._agent_executor: Optional[Callable] = None
        self._on_execution_complete: Optional[Callable] = None

        # State
        self._running = False
        self._poll_task: Optional[asyncio.Task] = None
        self._worker_task: Optional[asyncio.Task] = None

    def set_agent_executor(self, executor: Callable) -> None:
        """
        Set the function that executes agent runs.

        Args:
            executor: Async function(agent_id, input, timeout) -> (output, run_id)
        """
        self._agent_executor = executor

    def set_completion_callback(self, callback: Callable) -> None:
        """
        Set callback for execution completion.

        Args:
            callback: Async function(execution: JobExecution) -> None
        """
        self._on_execution_complete = callback

    async def start(self) -> None:
        """Start the scheduler executor."""
        if self._running:
            return

        self._running = True
        logger.info("Starting scheduler executor")

        # Start background tasks
        self._poll_task = asyncio.create_task(self._poll_loop())
        self._worker_task = asyncio.create_task(self._worker_loop())

    async def stop(self) -> None:
        """Stop the scheduler executor."""
        self._running = False

        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass

        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

        logger.info("Scheduler executor stopped")

    async def _poll_loop(self) -> None:
        """Background loop that polls for due jobs."""
        while self._running:
            try:
                await self._check_due_jobs()
            except Exception as e:
                logger.error(f"Error in poll loop: {e}")

            await asyncio.sleep(self.poll_interval)

    async def _worker_loop(self) -> None:
        """Background loop that processes queued jobs."""
        while self._running:
            try:
                # Dequeue jobs ready to execute
                jobs = await self.queue.dequeue(self.batch_size)

                if jobs:
                    # Process jobs concurrently
                    tasks = [self._execute_job(job) for job in jobs]
                    await asyncio.gather(*tasks, return_exceptions=True)
                else:
                    # No jobs, wait briefly
                    await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
                await asyncio.sleep(5)

    async def _check_due_jobs(self) -> None:
        """Check for jobs that are due to run."""
        now = datetime.utcnow()

        for job in list(self._jobs.values()):
            if job.status != JobStatus.ACTIVE:
                continue

            if job.is_due(now):
                await self._enqueue_execution(job)

    async def _enqueue_execution(self, job: ScheduledJob) -> str:
        """Create and enqueue a job execution."""
        # Create execution record
        execution = JobExecution(
            execution_id=uuid4(),
            job_id=job.job_id,
            scheduled_at=datetime.utcnow(),
            status=ExecutionStatus.PENDING,
            input_rendered=job.render_input(),
        )

        self._executions[str(execution.execution_id)] = execution

        # Create queued job
        queued = QueuedJob(
            queue_id=str(uuid4()),
            job_id=str(job.job_id),
            execution_id=str(execution.execution_id),
            tenant_id=str(job.tenant_id),
            agent_id=job.agent_id,
            input_rendered=execution.input_rendered,
            timeout_seconds=job.timeout_seconds,
            max_attempts=job.max_retries,
        )

        await self.queue.enqueue(queued)

        # Update job state
        job.last_run_at = datetime.utcnow()
        job.total_runs += 1

        # Calculate next run time
        await self._update_next_run(job)

        logger.info(f"Enqueued execution for job {job.name} (execution_id: {execution.execution_id})")

        return str(execution.execution_id)

    async def _update_next_run(self, job: ScheduledJob) -> None:
        """Update the next run time for a job."""
        trigger = job.trigger

        if trigger.trigger_type == TriggerType.CRON:
            try:
                cron = CronParser.parse(trigger.cron_expression)
                job.next_run_at = cron.next_run()
            except Exception as e:
                logger.error(f"Failed to parse cron for job {job.job_id}: {e}")
                job.status = JobStatus.DISABLED

        elif trigger.trigger_type == TriggerType.INTERVAL:
            job.next_run_at = datetime.utcnow() + timedelta(
                seconds=trigger.interval_seconds
            )

        elif trigger.trigger_type == TriggerType.ONCE:
            # One-time jobs don't repeat
            job.status = JobStatus.EXPIRED
            job.next_run_at = None

        elif trigger.trigger_type == TriggerType.WEBHOOK:
            # Webhook jobs don't have scheduled times
            job.next_run_at = None

        elif trigger.trigger_type == TriggerType.EVENT:
            # Event jobs don't have scheduled times
            job.next_run_at = None

        # Check expiry
        if job.end_date and job.next_run_at and job.next_run_at > job.end_date:
            job.status = JobStatus.EXPIRED
            job.next_run_at = None

    async def _execute_job(self, queued: QueuedJob) -> None:
        """Execute a queued job."""
        execution_id = queued.execution_id
        execution = self._executions.get(execution_id)

        if not execution:
            logger.error(f"Execution not found: {execution_id}")
            await self.queue.complete(queued.queue_id, False, "Execution not found")
            return

        # Update execution status
        execution.status = ExecutionStatus.RUNNING
        execution.started_at = datetime.utcnow()
        execution.attempt = queued.attempt

        logger.info(f"Executing job {queued.job_id} (attempt {queued.attempt})")

        try:
            if self._agent_executor:
                # Execute the agent
                output, run_id = await asyncio.wait_for(
                    self._agent_executor(
                        queued.agent_id,
                        queued.input_rendered,
                        queued.timeout_seconds
                    ),
                    timeout=queued.timeout_seconds
                )

                execution.output = output
                execution.run_id = run_id
                execution.status = ExecutionStatus.COMPLETED

            else:
                # No executor configured - mock success
                execution.output = f"[Mock] Executed: {queued.input_rendered}"
                execution.status = ExecutionStatus.COMPLETED

            # Calculate duration
            execution.completed_at = datetime.utcnow()
            execution.duration_ms = int(
                (execution.completed_at - execution.started_at).total_seconds() * 1000
            )

            # Update job stats
            job = self._jobs.get(queued.job_id)
            if job:
                job.successful_runs += 1

            await self.queue.complete(queued.queue_id, True)
            logger.info(f"Job {queued.job_id} completed successfully")

        except asyncio.TimeoutError:
            execution.status = ExecutionStatus.TIMEOUT
            execution.error = f"Execution timed out after {queued.timeout_seconds}s"
            execution.completed_at = datetime.utcnow()

            job = self._jobs.get(queued.job_id)
            if job:
                job.failed_runs += 1

            await self.queue.complete(queued.queue_id, False, execution.error)
            logger.error(f"Job {queued.job_id} timed out")

        except Exception as e:
            execution.status = ExecutionStatus.FAILED
            execution.error = str(e)
            execution.completed_at = datetime.utcnow()

            job = self._jobs.get(queued.job_id)
            if job:
                job.failed_runs += 1

            await self.queue.complete(queued.queue_id, False, str(e))
            logger.error(f"Job {queued.job_id} failed: {e}")

        # Call completion callback
        if self._on_execution_complete:
            try:
                await self._on_execution_complete(execution)
            except Exception as e:
                logger.error(f"Error in completion callback: {e}")

    # Job management methods

    async def create_job(self, job: ScheduledJob) -> ScheduledJob:
        """Create a new scheduled job."""
        # Calculate initial next run
        await self._update_next_run(job)

        self._jobs[str(job.job_id)] = job
        logger.info(f"Created job {job.name} (id: {job.job_id})")

        return job

    async def get_job(self, job_id: str) -> Optional[ScheduledJob]:
        """Get a job by ID."""
        return self._jobs.get(job_id)

    async def list_jobs(
        self,
        tenant_id: Optional[str] = None,
        status: Optional[JobStatus] = None,
        limit: int = 100,
    ) -> List[ScheduledJob]:
        """List jobs with optional filters."""
        jobs = list(self._jobs.values())

        if tenant_id:
            jobs = [j for j in jobs if str(j.tenant_id) == tenant_id]

        if status:
            jobs = [j for j in jobs if j.status == status]

        return jobs[:limit]

    async def update_job(self, job_id: str, updates: dict) -> Optional[ScheduledJob]:
        """Update a job."""
        job = self._jobs.get(job_id)
        if not job:
            return None

        for key, value in updates.items():
            if hasattr(job, key):
                setattr(job, key, value)

        job.updated_at = datetime.utcnow()

        # Recalculate next run if trigger changed
        if "trigger" in updates:
            await self._update_next_run(job)

        return job

    async def delete_job(self, job_id: str) -> bool:
        """Delete a job."""
        if job_id in self._jobs:
            del self._jobs[job_id]
            return True
        return False

    async def pause_job(self, job_id: str) -> bool:
        """Pause a job."""
        job = self._jobs.get(job_id)
        if job:
            job.status = JobStatus.PAUSED
            return True
        return False

    async def resume_job(self, job_id: str) -> bool:
        """Resume a paused job."""
        job = self._jobs.get(job_id)
        if job and job.status == JobStatus.PAUSED:
            job.status = JobStatus.ACTIVE
            await self._update_next_run(job)
            return True
        return False

    async def trigger_job(self, job_id: str) -> Optional[str]:
        """Manually trigger a job execution."""
        job = self._jobs.get(job_id)
        if not job:
            return None

        return await self._enqueue_execution(job)

    # Execution management

    async def get_execution(self, execution_id: str) -> Optional[JobExecution]:
        """Get an execution by ID."""
        return self._executions.get(execution_id)

    async def list_executions(
        self,
        job_id: Optional[str] = None,
        status: Optional[ExecutionStatus] = None,
        limit: int = 100,
    ) -> List[JobExecution]:
        """List executions with optional filters."""
        executions = list(self._executions.values())

        if job_id:
            executions = [e for e in executions if str(e.job_id) == job_id]

        if status:
            executions = [e for e in executions if e.status == status]

        # Sort by scheduled_at descending
        executions.sort(key=lambda e: e.scheduled_at, reverse=True)

        return executions[:limit]

    # Webhook handling

    async def handle_webhook(self, job_id: str, payload: dict) -> Optional[str]:
        """Handle a webhook trigger for a job."""
        job = self._jobs.get(job_id)
        if not job:
            return None

        if job.trigger.trigger_type != TriggerType.WEBHOOK:
            return None

        if job.status != JobStatus.ACTIVE:
            return None

        # Add webhook payload to variables
        return await self._enqueue_execution(job)

    # Event handling

    async def handle_event(self, event_type: str, event_data: dict) -> List[str]:
        """Handle an event trigger for matching jobs."""
        execution_ids = []

        for job in self._jobs.values():
            if job.trigger.trigger_type != TriggerType.EVENT:
                continue

            if job.status != JobStatus.ACTIVE:
                continue

            if job.trigger.event_type != event_type:
                continue

            # Check event filter if specified
            if job.trigger.event_filter:
                if not self._match_event_filter(event_data, job.trigger.event_filter):
                    continue

            execution_id = await self._enqueue_execution(job)
            execution_ids.append(execution_id)

        return execution_ids

    def _match_event_filter(self, event_data: dict, filter_spec: dict) -> bool:
        """Check if event data matches a filter specification."""
        for key, expected in filter_spec.items():
            actual = event_data.get(key)
            if actual != expected:
                return False
        return True


# Global instance
_scheduler_executor: Optional[SchedulerExecutor] = None


def get_scheduler_executor() -> SchedulerExecutor:
    """Get the global scheduler executor instance."""
    global _scheduler_executor
    if _scheduler_executor is None:
        _scheduler_executor = SchedulerExecutor()
    return _scheduler_executor


async def start_scheduler() -> SchedulerExecutor:
    """Start the global scheduler executor."""
    executor = get_scheduler_executor()
    await executor.start()
    return executor


async def stop_scheduler() -> None:
    """Stop the global scheduler executor."""
    global _scheduler_executor
    if _scheduler_executor:
        await _scheduler_executor.stop()
