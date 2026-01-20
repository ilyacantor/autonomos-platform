"""
Job Queue

Redis-backed job queue for scheduled agent executions.
Supports priority queuing, retries, and dead letter handling.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


@dataclass
class QueuedJob:
    """A job in the queue."""
    queue_id: str
    job_id: str
    execution_id: str
    tenant_id: str
    agent_id: str
    input_rendered: str
    priority: int = 0  # Higher = more urgent
    scheduled_for: datetime = None
    attempt: int = 1
    max_attempts: int = 3
    timeout_seconds: int = 300
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.scheduled_for is None:
            self.scheduled_for = datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "queue_id": self.queue_id,
            "job_id": self.job_id,
            "execution_id": self.execution_id,
            "tenant_id": self.tenant_id,
            "agent_id": self.agent_id,
            "input_rendered": self.input_rendered,
            "priority": self.priority,
            "scheduled_for": self.scheduled_for.isoformat(),
            "attempt": self.attempt,
            "max_attempts": self.max_attempts,
            "timeout_seconds": self.timeout_seconds,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "QueuedJob":
        return cls(
            queue_id=data["queue_id"],
            job_id=data["job_id"],
            execution_id=data["execution_id"],
            tenant_id=data["tenant_id"],
            agent_id=data["agent_id"],
            input_rendered=data["input_rendered"],
            priority=data.get("priority", 0),
            scheduled_for=datetime.fromisoformat(data["scheduled_for"]),
            attempt=data.get("attempt", 1),
            max_attempts=data.get("max_attempts", 3),
            timeout_seconds=data.get("timeout_seconds", 300),
            created_at=datetime.fromisoformat(data["created_at"]),
        )


class JobQueue:
    """
    Job queue for scheduled executions.

    In-memory implementation with optional Redis backend.
    """

    def __init__(self, redis_client: Optional[Any] = None):
        """
        Initialize the job queue.

        Args:
            redis_client: Optional Redis client for persistence
        """
        self.redis = redis_client
        self._queue: List[QueuedJob] = []
        self._processing: Dict[str, QueuedJob] = {}
        self._dead_letter: List[QueuedJob] = []
        self._lock = asyncio.Lock()

        # Queue names for Redis
        self.pending_queue = "scheduler:pending"
        self.processing_set = "scheduler:processing"
        self.dead_letter_queue = "scheduler:dead_letter"

    async def enqueue(self, job: QueuedJob) -> str:
        """
        Add a job to the queue.

        Returns:
            Queue ID of the enqueued job
        """
        if self.redis:
            return await self._redis_enqueue(job)
        else:
            return await self._memory_enqueue(job)

    async def _memory_enqueue(self, job: QueuedJob) -> str:
        """In-memory enqueue."""
        async with self._lock:
            # Insert by priority and scheduled time
            inserted = False
            for i, existing in enumerate(self._queue):
                if (job.priority > existing.priority or
                    (job.priority == existing.priority and
                     job.scheduled_for < existing.scheduled_for)):
                    self._queue.insert(i, job)
                    inserted = True
                    break

            if not inserted:
                self._queue.append(job)

            logger.info(f"Enqueued job {job.job_id} (queue_id: {job.queue_id})")
            return job.queue_id

    async def _redis_enqueue(self, job: QueuedJob) -> str:
        """Redis-backed enqueue using sorted set."""
        # Score = priority * 10^12 + (max_timestamp - scheduled_for)
        # This ensures higher priority jobs come first, then earlier times
        max_ts = datetime(2100, 1, 1).timestamp()
        score = job.priority * 10**12 + (max_ts - job.scheduled_for.timestamp())

        await self.redis.zadd(
            self.pending_queue,
            {json.dumps(job.to_dict()): score}
        )

        logger.info(f"Enqueued job {job.job_id} to Redis (queue_id: {job.queue_id})")
        return job.queue_id

    async def dequeue(self, count: int = 1) -> List[QueuedJob]:
        """
        Get jobs ready to execute.

        Args:
            count: Maximum number of jobs to dequeue

        Returns:
            List of jobs ready to execute
        """
        if self.redis:
            return await self._redis_dequeue(count)
        else:
            return await self._memory_dequeue(count)

    async def _memory_dequeue(self, count: int) -> List[QueuedJob]:
        """In-memory dequeue."""
        async with self._lock:
            now = datetime.utcnow()
            ready = []

            for job in self._queue[:]:
                if job.scheduled_for <= now and len(ready) < count:
                    self._queue.remove(job)
                    self._processing[job.queue_id] = job
                    ready.append(job)

            return ready

    async def _redis_dequeue(self, count: int) -> List[QueuedJob]:
        """Redis-backed dequeue."""
        now = datetime.utcnow()
        ready = []

        # Get top items from sorted set
        items = await self.redis.zrange(self.pending_queue, 0, count - 1)

        for item in items:
            job = QueuedJob.from_dict(json.loads(item))

            if job.scheduled_for <= now:
                # Move to processing
                await self.redis.zrem(self.pending_queue, item)
                await self.redis.hset(
                    self.processing_set,
                    job.queue_id,
                    json.dumps(job.to_dict())
                )
                ready.append(job)

        return ready

    async def complete(self, queue_id: str, success: bool, error: Optional[str] = None) -> bool:
        """
        Mark a job as completed.

        Args:
            queue_id: Queue ID of the job
            success: Whether execution succeeded
            error: Error message if failed

        Returns:
            True if job was found and updated
        """
        if self.redis:
            return await self._redis_complete(queue_id, success, error)
        else:
            return await self._memory_complete(queue_id, success, error)

    async def _memory_complete(
        self,
        queue_id: str,
        success: bool,
        error: Optional[str]
    ) -> bool:
        """In-memory complete."""
        async with self._lock:
            job = self._processing.pop(queue_id, None)
            if not job:
                return False

            if success:
                logger.info(f"Job {job.job_id} completed successfully")
            else:
                logger.warning(f"Job {job.job_id} failed: {error}")

                # Retry or dead letter
                if job.attempt < job.max_attempts:
                    job.attempt += 1
                    job.scheduled_for = datetime.utcnow() + timedelta(
                        seconds=60 * job.attempt  # Exponential backoff
                    )
                    self._queue.append(job)
                    logger.info(f"Job {job.job_id} scheduled for retry (attempt {job.attempt})")
                else:
                    self._dead_letter.append(job)
                    logger.error(f"Job {job.job_id} moved to dead letter queue")

            return True

    async def _redis_complete(
        self,
        queue_id: str,
        success: bool,
        error: Optional[str]
    ) -> bool:
        """Redis-backed complete."""
        job_data = await self.redis.hget(self.processing_set, queue_id)
        if not job_data:
            return False

        job = QueuedJob.from_dict(json.loads(job_data))
        await self.redis.hdel(self.processing_set, queue_id)

        if not success and job.attempt < job.max_attempts:
            # Retry
            job.attempt += 1
            job.scheduled_for = datetime.utcnow() + timedelta(seconds=60 * job.attempt)
            await self._redis_enqueue(job)
        elif not success:
            # Dead letter
            await self.redis.lpush(
                self.dead_letter_queue,
                json.dumps(job.to_dict())
            )

        return True

    async def get_stats(self) -> dict:
        """Get queue statistics."""
        if self.redis:
            pending = await self.redis.zcard(self.pending_queue)
            processing = await self.redis.hlen(self.processing_set)
            dead_letter = await self.redis.llen(self.dead_letter_queue)
        else:
            pending = len(self._queue)
            processing = len(self._processing)
            dead_letter = len(self._dead_letter)

        return {
            "pending": pending,
            "processing": processing,
            "dead_letter": dead_letter,
            "total": pending + processing,
        }

    async def get_pending(self, limit: int = 100) -> List[QueuedJob]:
        """Get pending jobs."""
        if self.redis:
            items = await self.redis.zrange(self.pending_queue, 0, limit - 1)
            return [QueuedJob.from_dict(json.loads(item)) for item in items]
        else:
            return self._queue[:limit]

    async def get_dead_letter(self, limit: int = 100) -> List[QueuedJob]:
        """Get dead letter jobs."""
        if self.redis:
            items = await self.redis.lrange(self.dead_letter_queue, 0, limit - 1)
            return [QueuedJob.from_dict(json.loads(item)) for item in items]
        else:
            return self._dead_letter[:limit]

    async def retry_dead_letter(self, queue_id: str) -> bool:
        """Retry a job from the dead letter queue."""
        async with self._lock:
            for i, job in enumerate(self._dead_letter):
                if job.queue_id == queue_id:
                    self._dead_letter.pop(i)
                    job.attempt = 1
                    job.scheduled_for = datetime.utcnow()
                    await self.enqueue(job)
                    return True
            return False

    async def cancel(self, queue_id: str) -> bool:
        """Cancel a pending job."""
        if self.redis:
            # Find and remove from pending
            items = await self.redis.zrange(self.pending_queue, 0, -1)
            for item in items:
                job = QueuedJob.from_dict(json.loads(item))
                if job.queue_id == queue_id:
                    await self.redis.zrem(self.pending_queue, item)
                    return True
            return False
        else:
            async with self._lock:
                for i, job in enumerate(self._queue):
                    if job.queue_id == queue_id:
                        self._queue.pop(i)
                        return True
                return False


# Global instance
_job_queue: Optional[JobQueue] = None


def get_job_queue() -> JobQueue:
    """Get the global job queue instance."""
    global _job_queue
    if _job_queue is None:
        _job_queue = JobQueue()
    return _job_queue


async def init_job_queue(redis_client: Optional[Any] = None) -> JobQueue:
    """Initialize the global job queue with optional Redis."""
    global _job_queue
    _job_queue = JobQueue(redis_client)
    return _job_queue
