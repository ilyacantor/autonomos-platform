"""
Horizontal Scaling Infrastructure

Enterprise-grade scaling for agent execution:
- Redis-backed task queue
- Worker pool management
- Load balancing
- Auto-scaling support
"""

from .task_queue import (
    TaskQueue,
    Task,
    TaskStatus,
    TaskPriority,
    get_task_queue,
)
from .worker import (
    Worker,
    WorkerStatus,
    WorkerConfig,
)
from .pool import (
    WorkerPool,
    PoolConfig,
    ScalingPolicy,
    get_worker_pool,
)

__all__ = [
    # Task Queue
    "TaskQueue",
    "Task",
    "TaskStatus",
    "TaskPriority",
    "get_task_queue",
    # Worker
    "Worker",
    "WorkerStatus",
    "WorkerConfig",
    # Pool
    "WorkerPool",
    "PoolConfig",
    "ScalingPolicy",
    "get_worker_pool",
]
