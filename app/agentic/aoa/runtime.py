"""
AOA Runtime - Unified Orchestration Layer

Absorbs TaskQueue and WorkerPool functionality into a unified runtime that:
- Provides a single interface for task submission and worker pool management
- Integrates with FabricContext for routing decisions
- Routes tasks through ActionRouter based on fabric preset
- Maintains RACI compliance (AOA is Responsible for runtime orchestration)

This implements the "absorption" pattern - AOA is the high-level API while
scaling/ remains the underlying implementation.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID, uuid4

from ..scaling.task_queue import (
    TaskQueue,
    Task,
    TaskStatus,
    TaskPriority,
    get_task_queue,
)
from ..scaling.pool import (
    WorkerPool,
    PoolConfig,
    ScalingPolicy,
    get_worker_pool,
)
from ..scaling.worker import WorkerConfig, WorkerStatus
from ..fabric.router import (
    ActionRouter,
    FabricContext,
    ActionPayload,
    RoutedAction,
    get_action_router,
)
from ..fabric.planes import FabricPreset, ActionType, TargetSystem
from ..coordination.orchestrator import MultiAgentOrchestrator, get_orchestrator

logger = logging.getLogger(__name__)


class AOATaskType(str, Enum):
    """Types of tasks managed by AOA runtime."""
    AGENT_RUN = "agent_run"
    FABRIC_ACTION = "fabric_action"
    SCHEDULED_JOB = "scheduled_job"
    ORCHESTRATION = "orchestration"
    EVALUATION = "evaluation"
    HEALTH_CHECK = "health_check"


@dataclass
class AOATask:
    """
    Enhanced task model with fabric routing metadata.
    
    Wraps the base Task from scaling/task_queue.py and adds:
    - Primary_Plane_ID for fabric routing awareness
    - FabricContext integration
    - RACI compliance metadata
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    
    task_type: AOATaskType = AOATaskType.AGENT_RUN
    payload: Dict[str, Any] = field(default_factory=dict)
    
    agent_id: Optional[UUID] = None
    tenant_id: Optional[UUID] = None
    run_id: Optional[UUID] = None
    
    priority: TaskPriority = TaskPriority.NORMAL
    scheduled_at: Optional[datetime] = None
    
    status: TaskStatus = TaskStatus.PENDING
    status_message: Optional[str] = None
    
    primary_plane_id: Optional[str] = None
    fabric_preset: Optional[FabricPreset] = None
    fabric_context: Optional[Dict[str, Any]] = None
    
    raci_responsible: str = "AOA"
    raci_accountable: Optional[str] = None
    raci_consulted: List[str] = field(default_factory=list)
    raci_informed: List[str] = field(default_factory=list)
    
    target_system: Optional[TargetSystem] = None
    action_type: Optional[ActionType] = None
    routed_action_id: Optional[str] = None
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    timeout_seconds: int = 300
    
    max_retries: int = 3
    retry_count: int = 0
    last_error: Optional[str] = None
    
    result: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_base_task(self) -> Task:
        """Convert to base Task for queue submission."""
        enriched_payload = {
            **self.payload,
            "primary_plane_id": self.primary_plane_id,
            "fabric_preset": self.fabric_preset.value if self.fabric_preset else None,
            "fabric_context": self.fabric_context,
            "raci_responsible": self.raci_responsible,
            "target_system": self.target_system.value if self.target_system else None,
            "action_type": self.action_type.value if self.action_type else None,
        }
        
        return Task(
            id=self.id,
            task_type=self.task_type.value,
            payload=enriched_payload,
            agent_id=self.agent_id,
            tenant_id=self.tenant_id,
            run_id=self.run_id,
            priority=self.priority,
            scheduled_at=self.scheduled_at,
            status=self.status,
            status_message=self.status_message,
            created_at=self.created_at,
            started_at=self.started_at,
            completed_at=self.completed_at,
            timeout_seconds=self.timeout_seconds,
            max_retries=self.max_retries,
            retry_count=self.retry_count,
            last_error=self.last_error,
            result=self.result,
            metadata={
                **self.metadata,
                "routed_action_id": self.routed_action_id,
                "raci_accountable": self.raci_accountable,
                "raci_consulted": self.raci_consulted,
                "raci_informed": self.raci_informed,
            },
        )
    
    @classmethod
    def from_base_task(cls, task: Task) -> "AOATask":
        """Create AOATask from base Task."""
        payload = task.payload or {}
        metadata = task.metadata or {}
        
        fabric_preset_str = payload.get("fabric_preset")
        fabric_preset = FabricPreset(fabric_preset_str) if fabric_preset_str else None
        
        target_system_str = payload.get("target_system")
        target_system = TargetSystem(target_system_str) if target_system_str else None
        
        action_type_str = payload.get("action_type")
        action_type = ActionType(action_type_str) if action_type_str else None
        
        task_type_str = task.task_type
        try:
            task_type = AOATaskType(task_type_str)
        except ValueError:
            task_type = AOATaskType.AGENT_RUN
        
        return cls(
            id=task.id,
            task_type=task_type,
            payload=payload,
            agent_id=task.agent_id,
            tenant_id=task.tenant_id,
            run_id=task.run_id,
            priority=task.priority,
            scheduled_at=task.scheduled_at,
            status=task.status,
            status_message=task.status_message,
            primary_plane_id=payload.get("primary_plane_id"),
            fabric_preset=fabric_preset,
            fabric_context=payload.get("fabric_context"),
            raci_responsible=payload.get("raci_responsible", "AOA"),
            raci_accountable=metadata.get("raci_accountable"),
            raci_consulted=metadata.get("raci_consulted", []),
            raci_informed=metadata.get("raci_informed", []),
            target_system=target_system,
            action_type=action_type,
            routed_action_id=metadata.get("routed_action_id"),
            created_at=task.created_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
            timeout_seconds=task.timeout_seconds,
            max_retries=task.max_retries,
            retry_count=task.retry_count,
            last_error=task.last_error,
            result=task.result,
            metadata=metadata,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "task_type": self.task_type.value,
            "payload": self.payload,
            "agent_id": str(self.agent_id) if self.agent_id else None,
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "run_id": str(self.run_id) if self.run_id else None,
            "priority": self.priority.value,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "status": self.status.value,
            "status_message": self.status_message,
            "primary_plane_id": self.primary_plane_id,
            "fabric_preset": self.fabric_preset.value if self.fabric_preset else None,
            "fabric_context": self.fabric_context,
            "raci_responsible": self.raci_responsible,
            "raci_accountable": self.raci_accountable,
            "target_system": self.target_system.value if self.target_system else None,
            "action_type": self.action_type.value if self.action_type else None,
            "routed_action_id": self.routed_action_id,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "retry_count": self.retry_count,
            "last_error": self.last_error,
            "result": self.result,
        }


@dataclass
class AOARuntimeConfig:
    """Configuration for AOA Runtime."""
    runtime_id: str = field(default_factory=lambda: f"aoa-runtime-{uuid4().hex[:8]}")
    
    pool_config: PoolConfig = field(default_factory=PoolConfig)
    
    default_fabric_preset: FabricPreset = FabricPreset.PRESET_6_SCRAPPY
    enable_fabric_routing: bool = True
    
    enable_auto_scaling: bool = True
    health_check_interval_seconds: float = 30.0
    metrics_interval_seconds: float = 60.0
    
    enable_orchestrator_integration: bool = True


class AOARuntime:
    """
    Unified AOA Runtime combining TaskQueue and WorkerPool management.
    
    RACI: AOA is RESPONSIBLE for runtime orchestration. This class provides:
    - Unified task submission with fabric routing
    - Worker pool management with auto-scaling
    - Health monitoring and metrics
    - Integration with MultiAgentOrchestrator
    
    The AOA Runtime absorbs the functionality of:
    - TaskQueue: For priority-based task queuing
    - WorkerPool: For worker management and scaling
    
    All tasks are enriched with fabric context (Primary_Plane_ID) to ensure
    proper routing through the Fabric Plane Mesh.
    """
    
    def __init__(
        self,
        config: Optional[AOARuntimeConfig] = None,
        task_queue: Optional[TaskQueue] = None,
        worker_pool: Optional[WorkerPool] = None,
        tenant_id: str = "default",
    ):
        """
        Initialize the AOA Runtime.
        
        Args:
            config: Runtime configuration
            task_queue: Optional custom task queue (uses global if not provided)
            worker_pool: Optional custom worker pool (uses global if not provided)
            tenant_id: Tenant ID for fabric routing
        """
        self.config = config or AOARuntimeConfig()
        self.tenant_id = tenant_id
        
        self._queue = task_queue or get_task_queue()
        self._pool = worker_pool or get_worker_pool()
        
        self._router = get_action_router(tenant_id)
        
        self._orchestrator: Optional[MultiAgentOrchestrator] = None
        if self.config.enable_orchestrator_integration:
            self._orchestrator = get_orchestrator()
        
        self._running = False
        self._stop_event = asyncio.Event()
        
        self._task_handlers: Dict[AOATaskType, Callable] = {}
        self._register_default_handlers()
        
        self._metrics_history: List[Dict[str, Any]] = []
        
        logger.info(f"AOA Runtime initialized: {self.config.runtime_id}")
    
    def _register_default_handlers(self) -> None:
        """Register default task handlers."""
        self.register_handler(AOATaskType.FABRIC_ACTION, self._handle_fabric_action)
        self.register_handler(AOATaskType.HEALTH_CHECK, self._handle_health_check)
    
    def register_handler(
        self,
        task_type: AOATaskType,
        handler: Callable[[AOATask], Any],
    ) -> None:
        """
        Register a handler for a task type.
        
        Args:
            task_type: Type of task to handle
            handler: Async function that processes the task
        """
        self._task_handlers[task_type] = handler
        logger.info(f"Registered AOA handler for task type: {task_type.value}")
    
    def get_fabric_context(self) -> FabricContext:
        """
        Get the current fabric context.
        
        Returns the active fabric plane context that agents need to
        include Primary_Plane_ID in their task submissions.
        """
        return self._router.get_fabric_context()
    
    def set_fabric_preset(self, preset: FabricPreset) -> None:
        """
        Set the active fabric preset.
        
        Changes how tasks are routed through the Fabric Plane Mesh.
        """
        self._router.set_active_preset(preset)
        logger.info(f"AOA Runtime fabric preset changed to: {preset.value}")
    
    async def submit_task(
        self,
        task: AOATask,
        enrich_fabric_context: bool = True,
    ) -> str:
        """
        Submit a task to the AOA runtime.
        
        Args:
            task: AOATask to submit
            enrich_fabric_context: Whether to enrich task with fabric context
            
        Returns:
            Task ID
        """
        if enrich_fabric_context and self.config.enable_fabric_routing:
            context = self.get_fabric_context()
            task.primary_plane_id = context.primary_plane_id
            task.fabric_preset = context.fabric_preset
            task.fabric_context = context.to_dict()
        
        base_task = task.to_base_task()
        task_id = await self._queue.enqueue(base_task)
        
        logger.debug(
            f"AOA task submitted: {task_id} (type={task.task_type.value}, "
            f"plane={task.primary_plane_id}, priority={task.priority.name})"
        )
        
        return task_id
    
    async def submit_fabric_action(
        self,
        target_system: TargetSystem,
        action_type: ActionType,
        entity_id: Optional[str] = None,
        entity_type: str = "unknown",
        data: Optional[Dict[str, Any]] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        agent_id: Optional[UUID] = None,
    ) -> str:
        """
        Submit a fabric action task.
        
        Creates an AOATask that will be routed through the Fabric Plane Mesh.
        
        Args:
            target_system: Target system for the action
            action_type: Type of action
            entity_id: Optional entity ID
            entity_type: Entity type
            data: Action data payload
            priority: Task priority
            agent_id: Optional agent ID
            
        Returns:
            Task ID
        """
        task = AOATask(
            task_type=AOATaskType.FABRIC_ACTION,
            payload={
                "entity_id": entity_id,
                "entity_type": entity_type,
                "data": data or {},
            },
            target_system=target_system,
            action_type=action_type,
            priority=priority,
            agent_id=agent_id,
        )
        
        return await self.submit_task(task)
    
    async def get_task(self, task_id: str) -> Optional[AOATask]:
        """
        Get a task by ID.
        
        Args:
            task_id: Task ID
            
        Returns:
            AOATask if found, None otherwise
        """
        base_task = await self._queue.get_task(task_id)
        if base_task:
            return AOATask.from_base_task(base_task)
        return None
    
    async def cancel_task(self, task_id: str) -> Optional[AOATask]:
        """
        Cancel a task.
        
        Args:
            task_id: Task ID to cancel
            
        Returns:
            Cancelled AOATask if found, None otherwise
        """
        base_task = await self._queue.cancel(task_id)
        if base_task:
            return AOATask.from_base_task(base_task)
        return None
    
    async def _handle_fabric_action(self, task: AOATask) -> Dict[str, Any]:
        """Handle a fabric action task by routing through ActionRouter."""
        if not task.target_system or not task.action_type:
            raise ValueError("Fabric action requires target_system and action_type")
        
        payload = ActionPayload(
            target_system=task.target_system,
            action_type=task.action_type,
            entity_id=task.payload.get("entity_id"),
            entity_type=task.payload.get("entity_type", "unknown"),
            data=task.payload.get("data", {}),
            metadata={
                "aoa_task_id": task.id,
                "raci_responsible": task.raci_responsible,
            },
        )
        
        routed = await self._router.route(
            payload=payload,
            agent_id=str(task.agent_id) if task.agent_id else None,
        )
        
        task.routed_action_id = routed.id
        
        return routed.to_dict()
    
    async def _handle_health_check(self, task: AOATask) -> Dict[str, Any]:
        """Handle a health check task."""
        return {
            "runtime_id": self.config.runtime_id,
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "fabric_context": self.get_fabric_context().to_dict(),
        }
    
    async def start(self) -> None:
        """Start the AOA runtime."""
        logger.info(f"Starting AOA Runtime: {self.config.runtime_id}")
        
        self._running = True
        self._stop_event.clear()
        
        if self.config.enable_auto_scaling:
            self._pool.config.scaling_policy = ScalingPolicy.AUTO
        
        await asyncio.gather(
            self._health_check_loop(),
            self._metrics_loop(),
        )
    
    async def stop(self) -> None:
        """Stop the AOA runtime gracefully."""
        logger.info(f"Stopping AOA Runtime: {self.config.runtime_id}")
        
        self._running = False
        self._stop_event.set()
        
        await self._pool.stop()
        
        logger.info(f"AOA Runtime stopped: {self.config.runtime_id}")
    
    async def _health_check_loop(self) -> None:
        """Health check loop for runtime monitoring."""
        while not self._stop_event.is_set():
            try:
                context = self.get_fabric_context()
                logger.debug(
                    f"AOA Runtime health: plane={context.primary_plane_id}, "
                    f"preset={context.fabric_preset.value}"
                )
            except Exception as e:
                logger.error(f"AOA Runtime health check error: {e}")
            
            await asyncio.sleep(self.config.health_check_interval_seconds)
    
    async def _metrics_loop(self) -> None:
        """Metrics collection loop."""
        while not self._stop_event.is_set():
            try:
                metrics = await self.get_metrics()
                self._metrics_history.append(metrics)
                
                if len(self._metrics_history) > 100:
                    self._metrics_history = self._metrics_history[-100:]
            except Exception as e:
                logger.error(f"AOA Runtime metrics error: {e}")
            
            await asyncio.sleep(self.config.metrics_interval_seconds)
    
    async def scale_workers(self, target_count: int) -> int:
        """
        Scale the worker pool to target count.
        
        Args:
            target_count: Target number of workers
            
        Returns:
            Actual number of workers after scaling
        """
        return await self._pool.scale_to(target_count)
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive runtime metrics."""
        queue_stats = await self._queue.get_queue_stats()
        pool_metrics = await self._pool.get_metrics()
        fabric_context = self.get_fabric_context()
        
        return {
            "runtime_id": self.config.runtime_id,
            "tenant_id": self.tenant_id,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "running" if self._running else "stopped",
            "fabric": {
                "primary_plane_id": fabric_context.primary_plane_id,
                "preset": fabric_context.fabric_preset.value,
                "is_direct_allowed": fabric_context.is_direct_allowed,
            },
            "queue": queue_stats,
            "pool": pool_metrics,
            "handlers_registered": list(self._task_handlers.keys()),
        }
    
    def get_worker_status(self) -> List[Dict[str, Any]]:
        """Get status of all workers in the pool."""
        return self._pool.get_worker_status()
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        return await self._queue.get_queue_stats()
    
    async def cleanup_stale_tasks(self, stale_threshold_seconds: int = 3600) -> int:
        """
        Clean up stale tasks.
        
        Args:
            stale_threshold_seconds: Threshold for considering a task stale
            
        Returns:
            Number of cleaned up tasks
        """
        return await self._queue.cleanup_stale_tasks(stale_threshold_seconds)


_aoa_runtime: Optional[AOARuntime] = None


def get_aoa_runtime(tenant_id: str = "default") -> AOARuntime:
    """
    Get the global AOA Runtime instance.
    
    Args:
        tenant_id: Tenant ID for fabric routing
        
    Returns:
        AOARuntime instance
    """
    global _aoa_runtime
    if _aoa_runtime is None:
        _aoa_runtime = AOARuntime(tenant_id=tenant_id)
    return _aoa_runtime
