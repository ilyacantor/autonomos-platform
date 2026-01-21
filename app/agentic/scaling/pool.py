"""
Worker Pool Management

Manages a pool of workers for horizontal scaling:
- Dynamic worker scaling
- Load balancing
- Health monitoring
- Auto-recovery
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from .task_queue import TaskQueue, get_task_queue
from .worker import Worker, WorkerConfig, WorkerStatus

logger = logging.getLogger(__name__)


class ScalingPolicy(str, Enum):
    """Scaling policy for the worker pool."""
    FIXED = "fixed"           # Fixed number of workers
    AUTO = "auto"             # Auto-scale based on queue depth
    MANUAL = "manual"         # Manual scaling only


@dataclass
class PoolConfig:
    """Configuration for a worker pool."""
    # Identity
    pool_id: str = field(default_factory=lambda: f"pool-{uuid4().hex[:8]}")
    pool_name: str = "default"

    # Worker configuration
    worker_config: WorkerConfig = field(default_factory=WorkerConfig)

    # Scaling
    scaling_policy: ScalingPolicy = ScalingPolicy.FIXED
    min_workers: int = 1
    max_workers: int = 10
    initial_workers: int = 2

    # Auto-scaling thresholds
    scale_up_threshold: int = 10      # Queue depth to trigger scale up
    scale_down_threshold: int = 2     # Queue depth to trigger scale down
    scale_up_cooldown_seconds: int = 60
    scale_down_cooldown_seconds: int = 300

    # Health check
    health_check_interval_seconds: float = 30.0
    unhealthy_threshold: int = 3      # Consecutive failures before restart

    # Monitoring
    metrics_interval_seconds: float = 60.0


@dataclass
class WorkerInfo:
    """Information about a worker in the pool."""
    worker_id: str
    worker: Worker
    status: WorkerStatus = WorkerStatus.STOPPED
    started_at: Optional[datetime] = None
    last_health_check: Optional[datetime] = None
    consecutive_failures: int = 0
    task: Optional[asyncio.Task] = None


class WorkerPool:
    """
    Worker pool for managing multiple workers.

    Features:
    - Dynamic scaling
    - Health monitoring
    - Auto-recovery
    - Load balancing
    """

    def __init__(
        self,
        config: Optional[PoolConfig] = None,
        task_queue: Optional[TaskQueue] = None,
    ):
        """
        Initialize the worker pool.

        Args:
            config: Pool configuration
            task_queue: Task queue for workers
        """
        self.config = config or PoolConfig()
        self.queue = task_queue or get_task_queue()

        # Workers
        self._workers: Dict[str, WorkerInfo] = {}
        self._worker_lock = asyncio.Lock()

        # Scaling state
        self._last_scale_up: Optional[datetime] = None
        self._last_scale_down: Optional[datetime] = None

        # Control
        self._running = False
        self._stop_event = asyncio.Event()

        # Metrics
        self._metrics_history: List[Dict[str, Any]] = []

    async def start(self):
        """Start the worker pool."""
        logger.info(f"Starting worker pool {self.config.pool_id}")

        self._running = True
        self._stop_event.clear()

        # Start initial workers
        for i in range(self.config.initial_workers):
            await self._add_worker()

        # Start management loops
        await asyncio.gather(
            self._health_check_loop(),
            self._scaling_loop(),
            self._metrics_loop(),
        )

    async def stop(self):
        """Stop the worker pool gracefully."""
        logger.info(f"Stopping worker pool {self.config.pool_id}")

        self._running = False
        self._stop_event.set()

        # Stop all workers
        async with self._worker_lock:
            for worker_info in self._workers.values():
                await self._stop_worker(worker_info)

            self._workers.clear()

        logger.info(f"Worker pool {self.config.pool_id} stopped")

    async def _add_worker(self) -> Optional[str]:
        """Add a new worker to the pool."""
        async with self._worker_lock:
            if len(self._workers) >= self.config.max_workers:
                logger.warning("Cannot add worker - max workers reached")
                return None

            # Create worker config
            worker_id = f"{self.config.pool_id}-worker-{len(self._workers)}"
            worker_config = WorkerConfig(
                worker_id=worker_id,
                **{k: v for k, v in self.config.worker_config.__dict__.items() if k != "worker_id"}
            )

            # Create worker
            worker = Worker(config=worker_config, task_queue=self.queue)

            # Create task to run worker
            task = asyncio.create_task(worker.start())

            # Track worker
            worker_info = WorkerInfo(
                worker_id=worker_id,
                worker=worker,
                status=WorkerStatus.STARTING,
                started_at=datetime.utcnow(),
                task=task,
            )
            self._workers[worker_id] = worker_info

            logger.info(f"Added worker {worker_id} to pool")
            return worker_id

    async def _remove_worker(self, worker_id: str) -> bool:
        """Remove a worker from the pool."""
        async with self._worker_lock:
            if worker_id not in self._workers:
                return False

            if len(self._workers) <= self.config.min_workers:
                logger.warning("Cannot remove worker - min workers reached")
                return False

            worker_info = self._workers[worker_id]
            await self._stop_worker(worker_info)
            del self._workers[worker_id]

            logger.info(f"Removed worker {worker_id} from pool")
            return True

    async def _stop_worker(self, worker_info: WorkerInfo):
        """Stop a worker."""
        try:
            await worker_info.worker.stop()
            if worker_info.task:
                worker_info.task.cancel()
                try:
                    await worker_info.task
                except asyncio.CancelledError:
                    pass
        except Exception as e:
            logger.error(f"Error stopping worker {worker_info.worker_id}: {e}")

    async def _restart_worker(self, worker_id: str):
        """Restart a worker."""
        async with self._worker_lock:
            if worker_id not in self._workers:
                return

            worker_info = self._workers[worker_id]

            # Stop old worker
            await self._stop_worker(worker_info)

            # Create new worker
            worker = Worker(
                config=worker_info.worker.config,
                task_queue=self.queue,
            )

            task = asyncio.create_task(worker.start())

            # Update worker info
            worker_info.worker = worker
            worker_info.status = WorkerStatus.STARTING
            worker_info.started_at = datetime.utcnow()
            worker_info.consecutive_failures = 0
            worker_info.task = task

            logger.info(f"Restarted worker {worker_id}")

    async def _health_check_loop(self):
        """Health check loop for workers."""
        while not self._stop_event.is_set():
            try:
                async with self._worker_lock:
                    for worker_id, worker_info in list(self._workers.items()):
                        # Update status from worker
                        worker_info.status = worker_info.worker.status
                        worker_info.last_health_check = datetime.utcnow()

                        # Check for unhealthy workers
                        if worker_info.status == WorkerStatus.ERROR:
                            worker_info.consecutive_failures += 1

                            if worker_info.consecutive_failures >= self.config.unhealthy_threshold:
                                logger.warning(f"Worker {worker_id} is unhealthy, restarting...")
                                asyncio.create_task(self._restart_worker(worker_id))
                        else:
                            worker_info.consecutive_failures = 0

            except Exception as e:
                logger.error(f"Health check error: {e}")

            await asyncio.sleep(self.config.health_check_interval_seconds)

    async def _scaling_loop(self):
        """Auto-scaling loop."""
        if self.config.scaling_policy != ScalingPolicy.AUTO:
            return

        while not self._stop_event.is_set():
            try:
                # Get queue stats
                stats = await self.queue.get_queue_stats()
                queue_depth = stats.get("total_pending", 0)

                now = datetime.utcnow()
                worker_count = len(self._workers)

                # Scale up check
                if queue_depth > self.config.scale_up_threshold:
                    if worker_count < self.config.max_workers:
                        if self._can_scale_up(now):
                            await self._add_worker()
                            self._last_scale_up = now
                            logger.info(f"Scaled up: queue_depth={queue_depth}, workers={worker_count + 1}")

                # Scale down check
                elif queue_depth < self.config.scale_down_threshold:
                    if worker_count > self.config.min_workers:
                        if self._can_scale_down(now):
                            # Find idle worker to remove
                            idle_worker = self._find_idle_worker()
                            if idle_worker:
                                await self._remove_worker(idle_worker)
                                self._last_scale_down = now
                                logger.info(f"Scaled down: queue_depth={queue_depth}, workers={worker_count - 1}")

            except Exception as e:
                logger.error(f"Scaling error: {e}")

            await asyncio.sleep(10)  # Check every 10 seconds

    def _can_scale_up(self, now: datetime) -> bool:
        """Check if we can scale up (cooldown)."""
        if self._last_scale_up is None:
            return True
        return (now - self._last_scale_up).total_seconds() > self.config.scale_up_cooldown_seconds

    def _can_scale_down(self, now: datetime) -> bool:
        """Check if we can scale down (cooldown)."""
        if self._last_scale_down is None:
            return True
        return (now - self._last_scale_down).total_seconds() > self.config.scale_down_cooldown_seconds

    def _find_idle_worker(self) -> Optional[str]:
        """Find an idle worker to remove."""
        for worker_id, worker_info in self._workers.items():
            if worker_info.status == WorkerStatus.IDLE:
                return worker_id
        return None

    async def _metrics_loop(self):
        """Metrics collection loop."""
        while not self._stop_event.is_set():
            try:
                metrics = await self.get_metrics()
                self._metrics_history.append(metrics)

                # Keep last 100 metrics
                if len(self._metrics_history) > 100:
                    self._metrics_history = self._metrics_history[-100:]

            except Exception as e:
                logger.error(f"Metrics error: {e}")

            await asyncio.sleep(self.config.metrics_interval_seconds)

    async def scale_to(self, target_workers: int) -> int:
        """
        Scale to a specific number of workers.

        Args:
            target_workers: Target number of workers

        Returns:
            Actual number of workers after scaling
        """
        target_workers = max(self.config.min_workers, min(self.config.max_workers, target_workers))
        current_workers = len(self._workers)

        if target_workers > current_workers:
            # Scale up
            for _ in range(target_workers - current_workers):
                await self._add_worker()
        elif target_workers < current_workers:
            # Scale down
            for _ in range(current_workers - target_workers):
                idle_worker = self._find_idle_worker()
                if idle_worker:
                    await self._remove_worker(idle_worker)

        return len(self._workers)

    async def get_metrics(self) -> Dict[str, Any]:
        """Get pool metrics."""
        queue_stats = await self.queue.get_queue_stats()

        worker_metrics = []
        total_processed = 0
        total_completed = 0
        total_failed = 0

        async with self._worker_lock:
            for worker_info in self._workers.values():
                status = worker_info.worker.get_status()
                worker_metrics.append(status)

                metrics = status.get("metrics", {})
                total_processed += metrics.get("tasks_processed", 0)
                total_completed += metrics.get("tasks_completed", 0)
                total_failed += metrics.get("tasks_failed", 0)

        return {
            "pool_id": self.config.pool_id,
            "timestamp": datetime.utcnow().isoformat(),
            "workers": {
                "total": len(self._workers),
                "idle": sum(1 for w in self._workers.values() if w.status == WorkerStatus.IDLE),
                "processing": sum(1 for w in self._workers.values() if w.status == WorkerStatus.PROCESSING),
                "error": sum(1 for w in self._workers.values() if w.status == WorkerStatus.ERROR),
            },
            "queue": queue_stats,
            "totals": {
                "tasks_processed": total_processed,
                "tasks_completed": total_completed,
                "tasks_failed": total_failed,
            },
            "worker_details": worker_metrics,
        }

    def get_worker_status(self) -> List[Dict[str, Any]]:
        """Get status of all workers."""
        return [
            {
                "worker_id": worker_info.worker_id,
                "status": worker_info.status.value,
                "started_at": worker_info.started_at.isoformat() if worker_info.started_at else None,
                "last_health_check": worker_info.last_health_check.isoformat() if worker_info.last_health_check else None,
                "consecutive_failures": worker_info.consecutive_failures,
            }
            for worker_info in self._workers.values()
        ]


# Global worker pool instance
_worker_pool: Optional[WorkerPool] = None


def get_worker_pool() -> WorkerPool:
    """Get the global worker pool instance."""
    global _worker_pool
    if _worker_pool is None:
        _worker_pool = WorkerPool()
    return _worker_pool


async def run_pool(config: Optional[PoolConfig] = None):
    """
    Run a worker pool.

    Entry point for running a pool as a standalone process.
    """
    pool = WorkerPool(config=config)
    await pool.start()


if __name__ == "__main__":
    asyncio.run(run_pool())
