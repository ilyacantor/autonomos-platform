"""
Worker for Agent Execution

Worker process that executes tasks from the queue:
- Agent run execution
- Evaluation runs
- Scheduled jobs
"""

import asyncio
import logging
import os
import signal
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Optional
from uuid import uuid4

from .task_queue import Task, TaskQueue, TaskStatus, get_task_queue

logger = logging.getLogger(__name__)


class WorkerStatus(str, Enum):
    """Status of a worker."""
    STARTING = "starting"
    IDLE = "idle"
    PROCESSING = "processing"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class WorkerConfig:
    """Configuration for a worker."""
    # Identity
    worker_id: str = field(default_factory=lambda: f"worker-{uuid4().hex[:8]}")
    worker_type: str = "general"  # general, agent, evaluation, scheduler

    # Task handling
    task_types: list = field(default_factory=lambda: ["agent_run", "evaluation", "scheduled_job"])
    max_concurrent_tasks: int = 1
    poll_interval_seconds: float = 1.0

    # Timeouts
    task_timeout_seconds: int = 300
    shutdown_timeout_seconds: int = 30

    # Health check
    heartbeat_interval_seconds: float = 10.0

    # Retry
    retry_on_error: bool = True
    max_task_retries: int = 3


@dataclass
class WorkerMetrics:
    """Metrics for a worker."""
    tasks_processed: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_processing_time_ms: int = 0
    last_task_at: Optional[datetime] = None
    started_at: datetime = field(default_factory=datetime.utcnow)


class Worker:
    """
    Worker process for executing tasks.

    Polls the task queue and executes tasks using registered handlers.
    """

    def __init__(
        self,
        config: Optional[WorkerConfig] = None,
        task_queue: Optional[TaskQueue] = None,
    ):
        """
        Initialize the worker.

        Args:
            config: Worker configuration
            task_queue: Task queue to use
        """
        self.config = config or WorkerConfig()
        self.queue = task_queue or get_task_queue()

        # State
        self.status = WorkerStatus.STOPPED
        self.current_task: Optional[Task] = None
        self.metrics = WorkerMetrics()

        # Task handlers by type
        self._handlers: Dict[str, Callable] = {}

        # Control
        self._stop_event = asyncio.Event()
        self._task_semaphore: Optional[asyncio.Semaphore] = None

        # Register default handlers
        self._register_default_handlers()

    def _register_default_handlers(self):
        """Register built-in task handlers."""
        self.register_handler("agent_run", self._handle_agent_run)
        self.register_handler("evaluation", self._handle_evaluation)
        self.register_handler("scheduled_job", self._handle_scheduled_job)

    def register_handler(
        self,
        task_type: str,
        handler: Callable[[Task], Any],
    ) -> None:
        """
        Register a handler for a task type.

        Args:
            task_type: Type of task to handle
            handler: Async function that processes the task
        """
        self._handlers[task_type] = handler
        logger.info(f"Registered handler for task type: {task_type}")

    async def start(self):
        """Start the worker."""
        logger.info(f"Starting worker {self.config.worker_id}")

        self.status = WorkerStatus.STARTING
        self._stop_event.clear()
        self._task_semaphore = asyncio.Semaphore(self.config.max_concurrent_tasks)

        # Set up signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))

        self.status = WorkerStatus.IDLE
        self.metrics.started_at = datetime.utcnow()

        # Start main loop and heartbeat
        await asyncio.gather(
            self._main_loop(),
            self._heartbeat_loop(),
        )

    async def stop(self):
        """Stop the worker gracefully."""
        logger.info(f"Stopping worker {self.config.worker_id}")
        self.status = WorkerStatus.STOPPING
        self._stop_event.set()

        # Wait for current task to complete
        if self.current_task:
            logger.info("Waiting for current task to complete...")
            try:
                await asyncio.wait_for(
                    self._wait_for_task_completion(),
                    timeout=self.config.shutdown_timeout_seconds,
                )
            except asyncio.TimeoutError:
                logger.warning("Shutdown timeout - task may be orphaned")

        self.status = WorkerStatus.STOPPED
        logger.info(f"Worker {self.config.worker_id} stopped")

    async def _wait_for_task_completion(self):
        """Wait for current task to complete."""
        while self.current_task:
            await asyncio.sleep(0.1)

    async def _main_loop(self):
        """Main worker loop - poll for and execute tasks."""
        logger.info(f"Worker {self.config.worker_id} entering main loop")

        while not self._stop_event.is_set():
            try:
                # Wait for semaphore (concurrent task limit)
                async with self._task_semaphore:
                    if self._stop_event.is_set():
                        break

                    # Poll for task
                    task = await self.queue.dequeue(
                        worker_id=self.config.worker_id,
                        task_types=self.config.task_types,
                    )

                    if task:
                        await self._process_task(task)
                    else:
                        self.status = WorkerStatus.IDLE

            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                self.status = WorkerStatus.ERROR
                await asyncio.sleep(5)  # Back off on error

            # Poll interval
            await asyncio.sleep(self.config.poll_interval_seconds)

    async def _process_task(self, task: Task):
        """Process a single task."""
        self.current_task = task
        self.status = WorkerStatus.PROCESSING

        logger.info(f"Processing task {task.id} (type: {task.task_type})")

        start_time = datetime.utcnow()
        task.status = TaskStatus.RUNNING
        task.started_at = start_time

        try:
            # Get handler
            handler = self._handlers.get(task.task_type)
            if not handler:
                raise ValueError(f"No handler for task type: {task.task_type}")

            # Execute with timeout
            if asyncio.iscoroutinefunction(handler):
                result = await asyncio.wait_for(
                    handler(task),
                    timeout=self.config.task_timeout_seconds,
                )
            else:
                result = handler(task)

            # Mark completed
            await self.queue.complete(task.id, result)

            # Update metrics
            self.metrics.tasks_completed += 1
            processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            self.metrics.total_processing_time_ms += processing_time

            logger.info(f"Task {task.id} completed in {processing_time}ms")

        except asyncio.TimeoutError:
            logger.error(f"Task {task.id} timed out")
            await self.queue.fail(task.id, "Task execution timeout")
            self.metrics.tasks_failed += 1

        except Exception as e:
            logger.error(f"Task {task.id} failed: {e}")
            await self.queue.fail(task.id, str(e))
            self.metrics.tasks_failed += 1

        finally:
            self.metrics.tasks_processed += 1
            self.metrics.last_task_at = datetime.utcnow()
            self.current_task = None
            self.status = WorkerStatus.IDLE

    async def _heartbeat_loop(self):
        """Heartbeat loop for health monitoring."""
        while not self._stop_event.is_set():
            try:
                # Log heartbeat (in production, would publish to Redis/monitoring)
                logger.debug(
                    f"Worker {self.config.worker_id} heartbeat: "
                    f"status={self.status.value}, "
                    f"processed={self.metrics.tasks_processed}"
                )
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")

            await asyncio.sleep(self.config.heartbeat_interval_seconds)

    # Default task handlers

    async def _handle_agent_run(self, task: Task) -> Dict[str, Any]:
        """Handle agent run task."""
        from app.agentic.workflow import WorkflowBuilder, WorkflowConfig, ToolDefinition

        payload = task.payload
        agent_id = task.agent_id
        run_id = task.run_id or task.id

        logger.info(f"Executing agent run {run_id} for agent {agent_id}")

        # Build workflow config
        config = WorkflowConfig(
            agent_id=agent_id,
            tenant_id=task.tenant_id,
            run_id=run_id,
            model=payload.get("model", "claude-sonnet-4-20250514"),
            temperature=payload.get("temperature", 0.7),
            max_tokens=payload.get("max_tokens", 4096),
            max_steps=payload.get("max_steps", 20),
            max_cost_usd=payload.get("max_cost_usd", 1.0),
            system_prompt=payload.get("system_prompt"),
        )

        # Build and execute workflow
        builder = WorkflowBuilder()
        workflow = builder.build(config)

        state = await workflow.run(
            input_text=payload.get("input", ""),
            context=payload.get("context"),
        )

        return {
            "run_id": str(run_id),
            "output": state.get("output"),
            "tokens_input": state.get("tokens_input", 0),
            "tokens_output": state.get("tokens_output", 0),
            "cost_usd": state.get("cost_usd", 0.0),
            "steps_executed": state.get("current_step", 0),
            "error": state.get("error"),
        }

    async def _handle_evaluation(self, task: Task) -> Dict[str, Any]:
        """Handle evaluation task."""
        from app.agentic.eval.runner import EvalRunner

        payload = task.payload
        agent_id = task.agent_id

        logger.info(f"Running evaluation for agent {agent_id}")

        # Run evaluation
        runner = EvalRunner(agent_id=agent_id)
        result = await runner.run_all()

        return {
            "agent_id": str(agent_id),
            "total_cases": result.get("total_cases", 0),
            "passed": result.get("passed", 0),
            "failed": result.get("failed", 0),
            "pass_rate": result.get("pass_rate", 0.0),
        }

    async def _handle_scheduled_job(self, task: Task) -> Dict[str, Any]:
        """Handle scheduled job task."""
        from app.agentic.scheduler.executor import execute_job

        payload = task.payload
        job_id = payload.get("job_id")

        logger.info(f"Executing scheduled job {job_id}")

        result = await execute_job(job_id, payload)

        return {
            "job_id": job_id,
            "status": "completed",
            "result": result,
        }

    def get_status(self) -> Dict[str, Any]:
        """Get worker status and metrics."""
        return {
            "worker_id": self.config.worker_id,
            "worker_type": self.config.worker_type,
            "status": self.status.value,
            "current_task": self.current_task.id if self.current_task else None,
            "metrics": {
                "tasks_processed": self.metrics.tasks_processed,
                "tasks_completed": self.metrics.tasks_completed,
                "tasks_failed": self.metrics.tasks_failed,
                "total_processing_time_ms": self.metrics.total_processing_time_ms,
                "last_task_at": self.metrics.last_task_at.isoformat() if self.metrics.last_task_at else None,
                "uptime_seconds": (datetime.utcnow() - self.metrics.started_at).total_seconds(),
            },
        }


async def run_worker(config: Optional[WorkerConfig] = None):
    """
    Run a worker process.

    This is the entry point for running a worker as a standalone process.
    """
    worker = Worker(config=config)
    await worker.start()


if __name__ == "__main__":
    # Allow running as standalone script
    asyncio.run(run_worker())
