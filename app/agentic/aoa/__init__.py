"""
AOA (Agentic Orchestration Architecture) Module

Unified orchestration layer that absorbs TaskQueue and WorkerPool functionality:
- Provides a single interface for task submission and worker pool management
- Integrates with FabricContext for routing decisions
- Routes tasks through ActionRouter based on fabric preset
- Maintains RACI compliance (AOA is Responsible for runtime orchestration)

This module implements the "absorption" pattern - AOA is the high-level API while
app/agentic/scaling/ remains the underlying implementation.

Key Components:
- AOARuntime: Unified runtime combining queue + pool management
- AOAScheduler: Fabric-aware job scheduling
- AOATask: Enhanced task model with fabric routing metadata (Primary_Plane_ID)

Usage:
    from app.agentic.aoa import get_aoa_runtime, get_aoa_scheduler, AOATask
    
    # Get runtime
    runtime = get_aoa_runtime(tenant_id="acme")
    
    # Check fabric context
    context = runtime.get_fabric_context()
    print(f"Primary Plane: {context.primary_plane_id}")
    
    # Submit a task with fabric routing
    task = AOATask(
        task_type=AOATaskType.AGENT_RUN,
        payload={"action": "process_data"},
        priority=TaskPriority.HIGH,
    )
    task_id = await runtime.submit_task(task)
    
    # Schedule a recurring job
    scheduler = get_aoa_scheduler(tenant_id="acme")
    job = await scheduler.schedule_interval(
        name="hourly_sync",
        interval_seconds=3600,
        payload={"sync_type": "full"},
    )

RACI Compliance:
- AOA is RESPONSIBLE for runtime orchestration
- AOA delegates to scaling/ for actual queue and pool implementation
- All tasks are enriched with fabric context for proper routing
"""

from .runtime import (
    AOARuntime,
    AOARuntimeConfig,
    AOATask,
    AOATaskType,
    get_aoa_runtime,
)

from .scheduler import (
    AOAScheduler,
    AOASchedulerConfig,
    ScheduledJob,
    ScheduleConfig,
    ScheduleType,
    JobStatus,
    get_aoa_scheduler,
)

from ..scaling.task_queue import TaskStatus, TaskPriority
from ..fabric.router import FabricContext
from ..fabric.planes import FabricPreset, ActionType, TargetSystem

__all__ = [
    "AOARuntime",
    "AOARuntimeConfig",
    "AOATask",
    "AOATaskType",
    "get_aoa_runtime",
    "AOAScheduler",
    "AOASchedulerConfig",
    "ScheduledJob",
    "ScheduleConfig",
    "ScheduleType",
    "JobStatus",
    "get_aoa_scheduler",
    "TaskStatus",
    "TaskPriority",
    "FabricContext",
    "FabricPreset",
    "ActionType",
    "TargetSystem",
]
