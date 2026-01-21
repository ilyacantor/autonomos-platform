"""
Task Queue for Agent Execution

Redis-backed task queue for horizontal scaling:
- Priority-based task ordering
- Task lifecycle management
- Dead letter queue for failed tasks
- Metrics and monitoring
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")


class TaskStatus(str, Enum):
    """Status of a task in the queue."""
    PENDING = "pending"           # Waiting in queue
    ASSIGNED = "assigned"         # Assigned to a worker
    RUNNING = "running"           # Currently executing
    COMPLETED = "completed"       # Successfully completed
    FAILED = "failed"             # Failed execution
    RETRYING = "retrying"         # Scheduled for retry
    DEAD = "dead"                 # Exceeded retry limit
    CANCELLED = "cancelled"       # Cancelled by user


class TaskPriority(int, Enum):
    """Task priority levels."""
    CRITICAL = 1    # Immediate execution
    HIGH = 2        # High priority
    NORMAL = 5      # Default priority
    LOW = 8         # Low priority
    BACKGROUND = 10 # Background task


@dataclass
class Task:
    """
    A task to be executed by a worker.

    Represents an agent run or other background operation.
    """
    id: str = field(default_factory=lambda: str(uuid4()))

    # Task type and payload
    task_type: str = "agent_run"  # agent_run, evaluation, scheduled_job
    payload: Dict[str, Any] = field(default_factory=dict)

    # Routing
    agent_id: Optional[UUID] = None
    tenant_id: Optional[UUID] = None
    run_id: Optional[UUID] = None

    # Priority and scheduling
    priority: TaskPriority = TaskPriority.NORMAL
    scheduled_at: Optional[datetime] = None

    # Status
    status: TaskStatus = TaskStatus.PENDING
    status_message: Optional[str] = None

    # Assignment
    worker_id: Optional[str] = None
    assigned_at: Optional[datetime] = None

    # Timing
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    timeout_seconds: int = 300

    # Retry configuration
    max_retries: int = 3
    retry_count: int = 0
    retry_delay_seconds: int = 30
    last_error: Optional[str] = None

    # Result
    result: Optional[Any] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_type": self.task_type,
            "payload": self.payload,
            "agent_id": str(self.agent_id) if self.agent_id else None,
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "run_id": str(self.run_id) if self.run_id else None,
            "priority": self.priority.value,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "status": self.status.value,
            "status_message": self.status_message,
            "worker_id": self.worker_id,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "retry_count": self.retry_count,
            "retry_delay_seconds": self.retry_delay_seconds,
            "last_error": self.last_error,
            "result": self.result,
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        return cls(
            id=data.get("id", str(uuid4())),
            task_type=data.get("task_type", "agent_run"),
            payload=data.get("payload", {}),
            agent_id=UUID(data["agent_id"]) if data.get("agent_id") else None,
            tenant_id=UUID(data["tenant_id"]) if data.get("tenant_id") else None,
            run_id=UUID(data["run_id"]) if data.get("run_id") else None,
            priority=TaskPriority(data.get("priority", 5)),
            scheduled_at=datetime.fromisoformat(data["scheduled_at"]) if data.get("scheduled_at") else None,
            status=TaskStatus(data.get("status", "pending")),
            status_message=data.get("status_message"),
            worker_id=data.get("worker_id"),
            assigned_at=datetime.fromisoformat(data["assigned_at"]) if data.get("assigned_at") else None,
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            timeout_seconds=data.get("timeout_seconds", 300),
            max_retries=data.get("max_retries", 3),
            retry_count=data.get("retry_count", 0),
            retry_delay_seconds=data.get("retry_delay_seconds", 30),
            last_error=data.get("last_error"),
            result=data.get("result"),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "Task":
        return cls.from_dict(json.loads(json_str))

    def is_expired(self) -> bool:
        """Check if task has timed out."""
        if self.started_at:
            return datetime.utcnow() > self.started_at + timedelta(seconds=self.timeout_seconds)
        return False

    def should_retry(self) -> bool:
        """Check if task should be retried."""
        return self.retry_count < self.max_retries


class TaskQueue:
    """
    Redis-backed task queue for agent execution.

    Features:
    - Priority-based ordering
    - Delayed/scheduled tasks
    - Dead letter queue
    - Task lifecycle management
    """

    def __init__(self, redis_url: str = REDIS_URL, prefix: str = "aos:tasks"):
        """
        Initialize the task queue.

        Args:
            redis_url: Redis connection URL
            prefix: Key prefix for Redis keys
        """
        self.redis_url = redis_url
        self.prefix = prefix

        # Redis client (lazy initialization)
        self._redis = None

        # Queue names
        self.pending_queue = f"{prefix}:pending"
        self.processing_set = f"{prefix}:processing"
        self.scheduled_zset = f"{prefix}:scheduled"
        self.dead_letter_queue = f"{prefix}:dead"

        # Task storage
        self.task_hash = f"{prefix}:task"

        # In-memory fallback when Redis unavailable
        self._memory_queue: List[Task] = []
        self._memory_tasks: Dict[str, Task] = {}

    async def _get_redis(self):
        """Get or create Redis connection."""
        if self._redis is None:
            try:
                import redis.asyncio as redis
                self._redis = await redis.from_url(self.redis_url)
                logger.info("Connected to Redis for task queue")
            except Exception as e:
                logger.warning(f"Redis unavailable, using in-memory queue: {e}")
                self._redis = None
        return self._redis

    async def enqueue(self, task: Task) -> str:
        """
        Add a task to the queue.

        Args:
            task: Task to enqueue

        Returns:
            Task ID
        """
        redis = await self._get_redis()

        if redis:
            try:
                # Store task data
                await redis.hset(self.task_hash, task.id, task.to_json())

                # Add to appropriate queue based on scheduling
                if task.scheduled_at and task.scheduled_at > datetime.utcnow():
                    # Scheduled task - add to sorted set
                    score = task.scheduled_at.timestamp()
                    await redis.zadd(self.scheduled_zset, {task.id: score})
                else:
                    # Immediate task - add to priority queue
                    # Use list with priority prefix for simple priority support
                    priority_queue = f"{self.pending_queue}:{task.priority.value}"
                    await redis.lpush(priority_queue, task.id)

                logger.debug(f"Enqueued task {task.id} (priority: {task.priority.name})")
                return task.id

            except Exception as e:
                logger.error(f"Failed to enqueue task: {e}")
                # Fall through to memory queue

        # In-memory fallback
        self._memory_tasks[task.id] = task
        self._memory_queue.append(task)
        self._memory_queue.sort(key=lambda t: t.priority.value)
        return task.id

    async def dequeue(self, worker_id: str, task_types: Optional[List[str]] = None) -> Optional[Task]:
        """
        Get the next task from the queue.

        Args:
            worker_id: ID of the worker claiming the task
            task_types: Optional filter for task types

        Returns:
            Task if available, None otherwise
        """
        redis = await self._get_redis()

        if redis:
            try:
                # Check scheduled tasks first
                await self._process_scheduled_tasks()

                # Try each priority level
                for priority in TaskPriority:
                    priority_queue = f"{self.pending_queue}:{priority.value}"
                    task_id = await redis.rpop(priority_queue)

                    if task_id:
                        task_id = task_id.decode() if isinstance(task_id, bytes) else task_id
                        task_json = await redis.hget(self.task_hash, task_id)

                        if task_json:
                            task = Task.from_json(task_json.decode() if isinstance(task_json, bytes) else task_json)

                            # Filter by task type
                            if task_types and task.task_type not in task_types:
                                # Put it back
                                await redis.lpush(priority_queue, task_id)
                                continue

                            # Mark as assigned
                            task.status = TaskStatus.ASSIGNED
                            task.worker_id = worker_id
                            task.assigned_at = datetime.utcnow()

                            await redis.hset(self.task_hash, task_id, task.to_json())
                            await redis.sadd(self.processing_set, task_id)

                            return task

                return None

            except Exception as e:
                logger.error(f"Failed to dequeue task: {e}")
                # Fall through to memory queue

        # In-memory fallback
        if self._memory_queue:
            for i, task in enumerate(self._memory_queue):
                if task_types is None or task.task_type in task_types:
                    task = self._memory_queue.pop(i)
                    task.status = TaskStatus.ASSIGNED
                    task.worker_id = worker_id
                    task.assigned_at = datetime.utcnow()
                    return task
        return None

    async def _process_scheduled_tasks(self):
        """Move due scheduled tasks to the pending queue."""
        redis = await self._get_redis()
        if not redis:
            return

        now = datetime.utcnow().timestamp()

        # Get all due tasks
        due_tasks = await redis.zrangebyscore(self.scheduled_zset, 0, now)

        for task_id in due_tasks:
            task_id = task_id.decode() if isinstance(task_id, bytes) else task_id
            task_json = await redis.hget(self.task_hash, task_id)

            if task_json:
                task = Task.from_json(task_json.decode() if isinstance(task_json, bytes) else task_json)
                priority_queue = f"{self.pending_queue}:{task.priority.value}"
                await redis.lpush(priority_queue, task_id)
                await redis.zrem(self.scheduled_zset, task_id)

    async def complete(self, task_id: str, result: Any = None) -> Optional[Task]:
        """
        Mark a task as completed.

        Args:
            task_id: Task to complete
            result: Task result

        Returns:
            Updated task or None if not found
        """
        redis = await self._get_redis()

        if redis:
            try:
                task_json = await redis.hget(self.task_hash, task_id)
                if not task_json:
                    return None

                task = Task.from_json(task_json.decode() if isinstance(task_json, bytes) else task_json)
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.utcnow()
                task.result = result

                await redis.hset(self.task_hash, task_id, task.to_json())
                await redis.srem(self.processing_set, task_id)

                logger.debug(f"Task {task_id} completed")
                return task

            except Exception as e:
                logger.error(f"Failed to complete task: {e}")

        # In-memory fallback
        task = self._memory_tasks.get(task_id)
        if task:
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            task.result = result
            return task
        return None

    async def fail(self, task_id: str, error: str) -> Optional[Task]:
        """
        Mark a task as failed.

        Will retry if retries remaining, otherwise move to dead letter queue.
        """
        redis = await self._get_redis()

        if redis:
            try:
                task_json = await redis.hget(self.task_hash, task_id)
                if not task_json:
                    return None

                task = Task.from_json(task_json.decode() if isinstance(task_json, bytes) else task_json)
                task.last_error = error
                task.retry_count += 1

                await redis.srem(self.processing_set, task_id)

                if task.should_retry():
                    # Schedule retry
                    task.status = TaskStatus.RETRYING
                    retry_at = datetime.utcnow() + timedelta(seconds=task.retry_delay_seconds)
                    await redis.zadd(self.scheduled_zset, {task_id: retry_at.timestamp()})
                    logger.info(f"Task {task_id} scheduled for retry {task.retry_count}/{task.max_retries}")
                else:
                    # Move to dead letter queue
                    task.status = TaskStatus.DEAD
                    await redis.lpush(self.dead_letter_queue, task_id)
                    logger.warning(f"Task {task_id} moved to dead letter queue after {task.retry_count} retries")

                await redis.hset(self.task_hash, task_id, task.to_json())
                return task

            except Exception as e:
                logger.error(f"Failed to mark task as failed: {e}")

        # In-memory fallback
        task = self._memory_tasks.get(task_id)
        if task:
            task.status = TaskStatus.FAILED
            task.last_error = error
            return task
        return None

    async def cancel(self, task_id: str) -> Optional[Task]:
        """Cancel a pending or assigned task."""
        redis = await self._get_redis()

        if redis:
            try:
                task_json = await redis.hget(self.task_hash, task_id)
                if not task_json:
                    return None

                task = Task.from_json(task_json.decode() if isinstance(task_json, bytes) else task_json)

                if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.DEAD):
                    return task  # Already finished

                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.utcnow()

                # Remove from all queues
                for priority in TaskPriority:
                    await redis.lrem(f"{self.pending_queue}:{priority.value}", 0, task_id)
                await redis.zrem(self.scheduled_zset, task_id)
                await redis.srem(self.processing_set, task_id)

                await redis.hset(self.task_hash, task_id, task.to_json())
                return task

            except Exception as e:
                logger.error(f"Failed to cancel task: {e}")

        # In-memory fallback
        task = self._memory_tasks.get(task_id)
        if task:
            task.status = TaskStatus.CANCELLED
            if task in self._memory_queue:
                self._memory_queue.remove(task)
            return task
        return None

    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        redis = await self._get_redis()

        if redis:
            try:
                task_json = await redis.hget(self.task_hash, task_id)
                if task_json:
                    return Task.from_json(task_json.decode() if isinstance(task_json, bytes) else task_json)
            except Exception as e:
                logger.error(f"Failed to get task: {e}")

        return self._memory_tasks.get(task_id)

    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        redis = await self._get_redis()

        if redis:
            try:
                stats = {
                    "pending": {},
                    "scheduled": await redis.zcard(self.scheduled_zset),
                    "processing": await redis.scard(self.processing_set),
                    "dead": await redis.llen(self.dead_letter_queue),
                }

                total_pending = 0
                for priority in TaskPriority:
                    count = await redis.llen(f"{self.pending_queue}:{priority.value}")
                    stats["pending"][priority.name] = count
                    total_pending += count

                stats["total_pending"] = total_pending

                return stats

            except Exception as e:
                logger.error(f"Failed to get queue stats: {e}")

        # In-memory stats
        return {
            "pending": {"total": len(self._memory_queue)},
            "total_pending": len(self._memory_queue),
            "scheduled": 0,
            "processing": sum(1 for t in self._memory_tasks.values() if t.status == TaskStatus.ASSIGNED),
            "dead": 0,
        }

    async def cleanup_stale_tasks(self, stale_threshold_seconds: int = 3600) -> int:
        """
        Clean up stale processing tasks.

        Tasks that have been processing for longer than the threshold
        are assumed to have failed and are re-queued.
        """
        redis = await self._get_redis()
        if not redis:
            return 0

        try:
            stale_count = 0
            processing_tasks = await redis.smembers(self.processing_set)

            for task_id in processing_tasks:
                task_id = task_id.decode() if isinstance(task_id, bytes) else task_id
                task_json = await redis.hget(self.task_hash, task_id)

                if task_json:
                    task = Task.from_json(task_json.decode() if isinstance(task_json, bytes) else task_json)

                    if task.assigned_at:
                        age = (datetime.utcnow() - task.assigned_at).total_seconds()
                        if age > stale_threshold_seconds:
                            await self.fail(task_id, "Task processing timeout - worker may have crashed")
                            stale_count += 1

            return stale_count

        except Exception as e:
            logger.error(f"Failed to cleanup stale tasks: {e}")
            return 0


# Global task queue instance
_task_queue: Optional[TaskQueue] = None


def get_task_queue() -> TaskQueue:
    """Get the global task queue instance."""
    global _task_queue
    if _task_queue is None:
        _task_queue = TaskQueue()
    return _task_queue
