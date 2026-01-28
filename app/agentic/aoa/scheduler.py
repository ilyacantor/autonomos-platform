"""
AOA Scheduler - Fabric-Aware Job Scheduling

Provides job scheduling integrated with fabric plane routing:
- Cron-like scheduling for recurring jobs
- One-time delayed execution
- Fabric context injection for all scheduled jobs
- Integration with AOARuntime for task execution

RACI: AOA is RESPONSIBLE for scheduling orchestration.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID, uuid4

from ..fabric.router import FabricContext, get_action_router
from ..fabric.planes import FabricPreset, ActionType, TargetSystem
from ..scaling.task_queue import TaskPriority

from .runtime import AOARuntime, AOATask, AOATaskType, get_aoa_runtime

logger = logging.getLogger(__name__)


class ScheduleType(str, Enum):
    """Types of schedules."""
    ONCE = "once"
    INTERVAL = "interval"
    CRON = "cron"
    DAILY = "daily"
    HOURLY = "hourly"


class JobStatus(str, Enum):
    """Status of a scheduled job."""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


@dataclass
class ScheduleConfig:
    """Configuration for job scheduling."""
    schedule_type: ScheduleType = ScheduleType.ONCE
    
    run_at: Optional[datetime] = None
    
    interval_seconds: Optional[int] = None
    
    cron_expression: Optional[str] = None
    
    hour: Optional[int] = None
    minute: int = 0
    
    max_runs: Optional[int] = None
    run_count: int = 0
    
    timezone: str = "UTC"
    
    def get_next_run_time(self, from_time: Optional[datetime] = None) -> Optional[datetime]:
        """Calculate the next run time based on schedule type."""
        now = from_time or datetime.utcnow()
        
        if self.schedule_type == ScheduleType.ONCE:
            if self.run_at and self.run_at > now:
                return self.run_at
            return None
        
        elif self.schedule_type == ScheduleType.INTERVAL:
            if self.interval_seconds:
                return now + timedelta(seconds=self.interval_seconds)
            return None
        
        elif self.schedule_type == ScheduleType.HOURLY:
            next_run = now.replace(minute=self.minute, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(hours=1)
            return next_run
        
        elif self.schedule_type == ScheduleType.DAILY:
            if self.hour is not None:
                next_run = now.replace(
                    hour=self.hour, minute=self.minute, 
                    second=0, microsecond=0
                )
                if next_run <= now:
                    next_run += timedelta(days=1)
                return next_run
            return None
        
        elif self.schedule_type == ScheduleType.CRON:
            return None
        
        return None


@dataclass
class ScheduledJob:
    """
    A scheduled job with fabric routing metadata.
    
    Jobs are scheduled through AOA and automatically enriched with
    fabric context (Primary_Plane_ID) for proper routing.
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)
    
    task_type: AOATaskType = AOATaskType.SCHEDULED_JOB
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    
    target_system: Optional[TargetSystem] = None
    action_type: Optional[ActionType] = None
    
    primary_plane_id: Optional[str] = None
    fabric_preset: Optional[FabricPreset] = None
    
    agent_id: Optional[UUID] = None
    tenant_id: Optional[UUID] = None
    
    status: JobStatus = JobStatus.PENDING
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    next_run_at: Optional[datetime] = None
    last_run_at: Optional[datetime] = None
    last_run_result: Optional[Dict[str, Any]] = None
    last_error: Optional[str] = None
    
    enabled: bool = True
    
    timeout_seconds: int = 300
    max_retries: int = 3
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_aoa_task(self) -> AOATask:
        """Convert to AOATask for execution."""
        return AOATask(
            task_type=self.task_type,
            payload={
                **self.payload,
                "job_id": self.id,
                "job_name": self.name,
                "run_number": self.schedule.run_count + 1,
            },
            agent_id=self.agent_id,
            tenant_id=self.tenant_id,
            priority=self.priority,
            primary_plane_id=self.primary_plane_id,
            fabric_preset=self.fabric_preset,
            target_system=self.target_system,
            action_type=self.action_type,
            timeout_seconds=self.timeout_seconds,
            max_retries=self.max_retries,
            metadata={
                "scheduled_job_id": self.id,
                "schedule_type": self.schedule.schedule_type.value,
            },
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "schedule_type": self.schedule.schedule_type.value,
            "task_type": self.task_type.value,
            "priority": self.priority.value,
            "primary_plane_id": self.primary_plane_id,
            "fabric_preset": self.fabric_preset.value if self.fabric_preset else None,
            "status": self.status.value,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat(),
            "next_run_at": self.next_run_at.isoformat() if self.next_run_at else None,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "run_count": self.schedule.run_count,
            "max_runs": self.schedule.max_runs,
        }


@dataclass
class AOASchedulerConfig:
    """Configuration for AOA Scheduler."""
    scheduler_id: str = field(default_factory=lambda: f"aoa-scheduler-{uuid4().hex[:8]}")
    
    check_interval_seconds: float = 10.0
    
    max_concurrent_jobs: int = 10
    
    enrich_fabric_context: bool = True
    default_fabric_preset: FabricPreset = FabricPreset.PRESET_6_SCRAPPY
    
    enable_health_checks: bool = True
    health_check_interval_seconds: float = 60.0


class AOAScheduler:
    """
    Fabric-aware job scheduler for AOA.
    
    RACI: AOA is RESPONSIBLE for scheduling orchestration.
    
    Features:
    - Cron-like scheduling for recurring jobs
    - One-time delayed execution
    - Fabric context injection (Primary_Plane_ID)
    - Integration with AOARuntime
    - Health monitoring
    
    All scheduled jobs are enriched with fabric context to ensure
    proper routing through the Fabric Plane Mesh.
    """
    
    def __init__(
        self,
        config: Optional[AOASchedulerConfig] = None,
        runtime: Optional[AOARuntime] = None,
        tenant_id: str = "default",
    ):
        """
        Initialize the AOA Scheduler.
        
        Args:
            config: Scheduler configuration
            runtime: Optional AOARuntime (uses global if not provided)
            tenant_id: Tenant ID for fabric routing
        """
        self.config = config or AOASchedulerConfig()
        self.tenant_id = tenant_id
        
        self._runtime = runtime or get_aoa_runtime(tenant_id)
        self._router = get_action_router(tenant_id)
        
        self._jobs: Dict[str, ScheduledJob] = {}
        self._job_lock = asyncio.Lock()
        
        self._running = False
        self._stop_event = asyncio.Event()
        
        self._execution_semaphore = asyncio.Semaphore(self.config.max_concurrent_jobs)
        
        self._job_handlers: Dict[str, Callable] = {}
        
        logger.info(f"AOA Scheduler initialized: {self.config.scheduler_id}")
    
    def get_fabric_context(self) -> FabricContext:
        """Get the current fabric context for job enrichment."""
        return self._router.get_fabric_context()
    
    async def schedule_job(
        self,
        name: str,
        schedule: ScheduleConfig,
        payload: Optional[Dict[str, Any]] = None,
        task_type: AOATaskType = AOATaskType.SCHEDULED_JOB,
        priority: TaskPriority = TaskPriority.NORMAL,
        target_system: Optional[TargetSystem] = None,
        action_type: Optional[ActionType] = None,
        description: str = "",
        agent_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ScheduledJob:
        """
        Schedule a new job.
        
        Args:
            name: Job name
            schedule: Schedule configuration
            payload: Job payload
            task_type: Type of task
            priority: Task priority
            target_system: Optional target system for fabric routing
            action_type: Optional action type for fabric routing
            description: Job description
            agent_id: Optional agent ID
            metadata: Optional metadata
            
        Returns:
            Created ScheduledJob
        """
        context = self.get_fabric_context()
        
        job = ScheduledJob(
            name=name,
            description=description,
            schedule=schedule,
            task_type=task_type,
            payload=payload or {},
            priority=priority,
            target_system=target_system,
            action_type=action_type,
            primary_plane_id=context.primary_plane_id if self.config.enrich_fabric_context else None,
            fabric_preset=context.fabric_preset if self.config.enrich_fabric_context else None,
            agent_id=agent_id,
            tenant_id=UUID(self.tenant_id) if self.tenant_id != "default" else None,
            status=JobStatus.SCHEDULED,
            metadata=metadata or {},
        )
        
        job.next_run_at = schedule.get_next_run_time()
        
        async with self._job_lock:
            self._jobs[job.id] = job
        
        logger.info(
            f"Job scheduled: {job.name} (id={job.id}, type={schedule.schedule_type.value}, "
            f"next_run={job.next_run_at}, plane={job.primary_plane_id})"
        )
        
        return job
    
    async def schedule_once(
        self,
        name: str,
        run_at: datetime,
        payload: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> ScheduledJob:
        """
        Schedule a one-time job.
        
        Args:
            name: Job name
            run_at: When to run the job
            payload: Job payload
            **kwargs: Additional job options
            
        Returns:
            Created ScheduledJob
        """
        schedule = ScheduleConfig(
            schedule_type=ScheduleType.ONCE,
            run_at=run_at,
        )
        return await self.schedule_job(name, schedule, payload, **kwargs)
    
    async def schedule_interval(
        self,
        name: str,
        interval_seconds: int,
        payload: Optional[Dict[str, Any]] = None,
        max_runs: Optional[int] = None,
        **kwargs,
    ) -> ScheduledJob:
        """
        Schedule a recurring job at fixed intervals.
        
        Args:
            name: Job name
            interval_seconds: Interval between runs in seconds
            payload: Job payload
            max_runs: Maximum number of runs (None for unlimited)
            **kwargs: Additional job options
            
        Returns:
            Created ScheduledJob
        """
        schedule = ScheduleConfig(
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=interval_seconds,
            max_runs=max_runs,
        )
        return await self.schedule_job(name, schedule, payload, **kwargs)
    
    async def schedule_daily(
        self,
        name: str,
        hour: int,
        minute: int = 0,
        payload: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> ScheduledJob:
        """
        Schedule a daily job.
        
        Args:
            name: Job name
            hour: Hour to run (0-23)
            minute: Minute to run (0-59)
            payload: Job payload
            **kwargs: Additional job options
            
        Returns:
            Created ScheduledJob
        """
        schedule = ScheduleConfig(
            schedule_type=ScheduleType.DAILY,
            hour=hour,
            minute=minute,
        )
        return await self.schedule_job(name, schedule, payload, **kwargs)
    
    async def schedule_hourly(
        self,
        name: str,
        minute: int = 0,
        payload: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> ScheduledJob:
        """
        Schedule an hourly job.
        
        Args:
            name: Job name
            minute: Minute of each hour to run (0-59)
            payload: Job payload
            **kwargs: Additional job options
            
        Returns:
            Created ScheduledJob
        """
        schedule = ScheduleConfig(
            schedule_type=ScheduleType.HOURLY,
            minute=minute,
        )
        return await self.schedule_job(name, schedule, payload, **kwargs)
    
    async def cancel_job(self, job_id: str) -> Optional[ScheduledJob]:
        """
        Cancel a scheduled job.
        
        Args:
            job_id: Job ID to cancel
            
        Returns:
            Cancelled job if found, None otherwise
        """
        async with self._job_lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = JobStatus.CANCELLED
                job.enabled = False
                logger.info(f"Job cancelled: {job.name} (id={job_id})")
            return job
    
    async def pause_job(self, job_id: str) -> Optional[ScheduledJob]:
        """
        Pause a scheduled job.
        
        Args:
            job_id: Job ID to pause
            
        Returns:
            Paused job if found, None otherwise
        """
        async with self._job_lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = JobStatus.PAUSED
                job.enabled = False
                logger.info(f"Job paused: {job.name} (id={job_id})")
            return job
    
    async def resume_job(self, job_id: str) -> Optional[ScheduledJob]:
        """
        Resume a paused job.
        
        Args:
            job_id: Job ID to resume
            
        Returns:
            Resumed job if found, None otherwise
        """
        async with self._job_lock:
            job = self._jobs.get(job_id)
            if job and job.status == JobStatus.PAUSED:
                job.status = JobStatus.SCHEDULED
                job.enabled = True
                job.next_run_at = job.schedule.get_next_run_time()
                logger.info(f"Job resumed: {job.name} (id={job_id})")
            return job
    
    async def get_job(self, job_id: str) -> Optional[ScheduledJob]:
        """Get a job by ID."""
        return self._jobs.get(job_id)
    
    def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        enabled: Optional[bool] = None,
    ) -> List[ScheduledJob]:
        """
        List jobs with optional filtering.
        
        Args:
            status: Filter by status
            enabled: Filter by enabled state
            
        Returns:
            List of matching jobs
        """
        jobs = list(self._jobs.values())
        
        if status:
            jobs = [j for j in jobs if j.status == status]
        if enabled is not None:
            jobs = [j for j in jobs if j.enabled == enabled]
        
        jobs.sort(key=lambda j: j.next_run_at or datetime.max)
        return jobs
    
    async def _run_job(self, job: ScheduledJob) -> None:
        """Execute a scheduled job."""
        async with self._execution_semaphore:
            try:
                job.status = JobStatus.RUNNING
                job.last_run_at = datetime.utcnow()
                
                if self.config.enrich_fabric_context:
                    context = self.get_fabric_context()
                    job.primary_plane_id = context.primary_plane_id
                    job.fabric_preset = context.fabric_preset
                
                task = job.to_aoa_task()
                task_id = await self._runtime.submit_task(task)
                
                job.last_run_result = {
                    "task_id": task_id,
                    "submitted_at": datetime.utcnow().isoformat(),
                    "primary_plane_id": job.primary_plane_id,
                }
                job.schedule.run_count += 1
                job.status = JobStatus.COMPLETED
                
                logger.info(
                    f"Job executed: {job.name} (id={job.id}, task={task_id}, "
                    f"run={job.schedule.run_count})"
                )
                
            except Exception as e:
                job.status = JobStatus.FAILED
                job.last_error = str(e)
                logger.error(f"Job execution failed: {job.name} (id={job.id}): {e}")
            
            finally:
                if job.schedule.max_runs and job.schedule.run_count >= job.schedule.max_runs:
                    job.enabled = False
                    job.next_run_at = None
                    logger.info(f"Job reached max runs: {job.name} (id={job.id})")
                elif job.enabled and job.status != JobStatus.CANCELLED:
                    job.next_run_at = job.schedule.get_next_run_time()
                    if job.status != JobStatus.FAILED:
                        job.status = JobStatus.SCHEDULED
    
    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        while not self._stop_event.is_set():
            try:
                now = datetime.utcnow()
                due_jobs = []
                
                async with self._job_lock:
                    for job in self._jobs.values():
                        if (job.enabled and 
                            job.status == JobStatus.SCHEDULED and
                            job.next_run_at and 
                            job.next_run_at <= now):
                            due_jobs.append(job)
                
                if due_jobs:
                    await asyncio.gather(
                        *[self._run_job(job) for job in due_jobs],
                        return_exceptions=True,
                    )
                
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
            
            await asyncio.sleep(self.config.check_interval_seconds)
    
    async def _health_check_loop(self) -> None:
        """Health check loop."""
        while not self._stop_event.is_set():
            try:
                context = self.get_fabric_context()
                job_count = len(self._jobs)
                active_jobs = len([j for j in self._jobs.values() if j.enabled])
                
                logger.debug(
                    f"AOA Scheduler health: jobs={job_count}, active={active_jobs}, "
                    f"plane={context.primary_plane_id}"
                )
            except Exception as e:
                logger.error(f"Scheduler health check error: {e}")
            
            await asyncio.sleep(self.config.health_check_interval_seconds)
    
    async def start(self) -> None:
        """Start the scheduler."""
        logger.info(f"Starting AOA Scheduler: {self.config.scheduler_id}")
        
        self._running = True
        self._stop_event.clear()
        
        tasks = [self._scheduler_loop()]
        if self.config.enable_health_checks:
            tasks.append(self._health_check_loop())
        
        await asyncio.gather(*tasks)
    
    async def stop(self) -> None:
        """Stop the scheduler gracefully."""
        logger.info(f"Stopping AOA Scheduler: {self.config.scheduler_id}")
        
        self._running = False
        self._stop_event.set()
        
        logger.info(f"AOA Scheduler stopped: {self.config.scheduler_id}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        jobs = list(self._jobs.values())
        
        by_status = {}
        for job in jobs:
            by_status[job.status.value] = by_status.get(job.status.value, 0) + 1
        
        by_type = {}
        for job in jobs:
            by_type[job.schedule.schedule_type.value] = by_type.get(
                job.schedule.schedule_type.value, 0
            ) + 1
        
        total_runs = sum(j.schedule.run_count for j in jobs)
        
        context = self.get_fabric_context()
        
        return {
            "scheduler_id": self.config.scheduler_id,
            "running": self._running,
            "total_jobs": len(jobs),
            "active_jobs": len([j for j in jobs if j.enabled]),
            "by_status": by_status,
            "by_schedule_type": by_type,
            "total_runs": total_runs,
            "fabric_context": context.to_dict(),
        }


_aoa_scheduler: Optional[AOAScheduler] = None


def get_aoa_scheduler(tenant_id: str = "default") -> AOAScheduler:
    """
    Get the global AOA Scheduler instance.
    
    Args:
        tenant_id: Tenant ID for fabric routing
        
    Returns:
        AOAScheduler instance
    """
    global _aoa_scheduler
    if _aoa_scheduler is None:
        _aoa_scheduler = AOAScheduler(tenant_id=tenant_id)
    return _aoa_scheduler
