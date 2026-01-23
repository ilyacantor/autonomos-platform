"""
Action Router

Routes agent actions through the active Fabric Plane.
Ensures all actions respect the enterprise fabric topology.
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from .planes import (
    FabricPlane,
    FabricPreset,
    FabricRoute,
    FabricPlaneRegistry,
    ActionType,
    TargetSystem,
    get_fabric_registry,
)

logger = logging.getLogger(__name__)


class RouteStatus(str, Enum):
    """Status of a routed action."""
    PENDING = "pending"
    ROUTING = "routing"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class ActionPayload:
    """Payload for an action to be routed."""
    target_system: TargetSystem
    action_type: ActionType
    entity_id: Optional[str] = None
    entity_type: str = "unknown"
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_system": self.target_system.value,
            "action_type": self.action_type.value,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "data": self.data,
            "metadata": self.metadata,
        }


@dataclass
class RoutedAction:
    """A routed action with tracking information."""
    id: str = field(default_factory=lambda: str(uuid4()))
    
    payload: ActionPayload = field(default_factory=ActionPayload)
    route: Optional[FabricRoute] = None
    fabric_preset: Optional[FabricPreset] = None
    
    status: RouteStatus = RouteStatus.PENDING
    status_message: Optional[str] = None
    
    agent_id: Optional[str] = None
    tenant_id: str = "default"
    correlation_id: Optional[str] = None
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    routed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    result: Optional[Any] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "payload": self.payload.to_dict(),
            "fabric_preset": self.fabric_preset.value if self.fabric_preset else None,
            "status": self.status.value,
            "status_message": self.status_message,
            "agent_id": self.agent_id,
            "tenant_id": self.tenant_id,
            "correlation_id": self.correlation_id,
            "created_at": self.created_at.isoformat(),
            "routed_at": self.routed_at.isoformat() if self.routed_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error": self.error,
        }


class ActionRouter:
    """
    Routes agent actions through the Fabric Plane topology.
    
    When an agent wants to execute an action (e.g., "Update Customer"),
    it cannot call the target API directly. Instead, it must route
    the command through the active Fabric Plane:
    
    - PRESET_1_DIRECT: Call API directly (dev/test only)
    - PRESET_8_IPAAS: Trigger iPaaS recipe (Workato, Tray.io)
    - PRESET_9_PLATFORM: Publish to Kafka command topic
    """
    
    def __init__(self, tenant_id: str = "default"):
        self.tenant_id = tenant_id
        self._registry = get_fabric_registry(tenant_id)
        self._action_log: Dict[str, RoutedAction] = {}
        self._ipaas_client: Optional[Any] = None
        self._kafka_producer: Optional[Any] = None
    
    async def route(
        self,
        payload: ActionPayload,
        agent_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> RoutedAction:
        """
        Route an action through the active Fabric Plane.
        
        Args:
            payload: The action payload to route
            agent_id: ID of the agent initiating the action
            correlation_id: Correlation ID for tracking
        
        Returns:
            RoutedAction with execution result
        """
        action = RoutedAction(
            payload=payload,
            agent_id=agent_id,
            tenant_id=self.tenant_id,
            correlation_id=correlation_id or str(uuid4()),
        )
        
        self._action_log[action.id] = action
        
        try:
            plane = self._registry.get_active_plane()
            action.fabric_preset = plane.preset
            
            route = plane.get_route(payload.target_system, payload.action_type)
            if not route:
                action.status = RouteStatus.FAILED
                action.error = f"No route found for {payload.target_system.value}:{payload.action_type.value}"
                logger.warning(f"No fabric route: {action.error}")
                return action
            
            action.route = route
            action.status = RouteStatus.ROUTING
            action.routed_at = datetime.utcnow()
            
            if plane.preset == FabricPreset.PRESET_1_DIRECT:
                result = await self._execute_direct(action, route)
            elif plane.preset == FabricPreset.PRESET_8_IPAAS:
                result = await self._execute_ipaas(action, route, plane)
            elif plane.preset == FabricPreset.PRESET_9_PLATFORM:
                result = await self._execute_platform(action, route, plane)
            else:
                raise ValueError(f"Unknown fabric preset: {plane.preset}")
            
            action.result = result
            action.status = RouteStatus.COMPLETED
            action.completed_at = datetime.utcnow()
            
            logger.info(
                f"Action {action.id} completed via {plane.preset.value}: "
                f"{payload.target_system.value}:{payload.action_type.value}"
            )
            
        except asyncio.TimeoutError:
            action.status = RouteStatus.TIMEOUT
            action.error = f"Action timed out after {route.timeout_seconds if route else 30}s"
            logger.error(f"Action {action.id} timeout: {action.error}")
            
        except Exception as e:
            action.status = RouteStatus.FAILED
            action.error = str(e)
            logger.error(f"Action {action.id} failed: {e}")
        
        return action
    
    async def _execute_direct(
        self,
        action: RoutedAction,
        route: FabricRoute
    ) -> Dict[str, Any]:
        """Execute action via direct API call."""
        action.status = RouteStatus.EXECUTING
        
        endpoint = route.direct_endpoint
        if action.payload.entity_id and "{id}" in endpoint:
            endpoint = endpoint.replace("{id}", action.payload.entity_id)
        
        logger.info(
            f"Direct execution: {route.direct_method} {endpoint} "
            f"(entity: {action.payload.entity_type})"
        )
        
        return {
            "routed_via": "direct",
            "method": route.direct_method,
            "endpoint": endpoint,
            "payload": action.payload.data,
            "simulated": True,
        }
    
    async def _execute_ipaas(
        self,
        action: RoutedAction,
        route: FabricRoute,
        plane: FabricPlane
    ) -> Dict[str, Any]:
        """Execute action via iPaaS recipe trigger."""
        action.status = RouteStatus.EXECUTING
        
        recipe_payload = {
            "recipe_id": route.ipaas_recipe_id,
            "recipe_name": route.ipaas_recipe_name,
            "input": {
                "entity_id": action.payload.entity_id,
                "entity_type": action.payload.entity_type,
                "data": action.payload.data,
                "correlation_id": action.correlation_id,
            },
            "metadata": {
                "agent_id": action.agent_id,
                "tenant_id": action.tenant_id,
                "timestamp": datetime.utcnow().isoformat(),
            },
        }
        
        logger.info(
            f"iPaaS execution: recipe={route.ipaas_recipe_id} "
            f"({route.ipaas_recipe_name})"
        )
        
        return {
            "routed_via": "ipaas",
            "provider": plane.ipaas_config.get("provider", "workato"),
            "recipe_id": route.ipaas_recipe_id,
            "recipe_name": route.ipaas_recipe_name,
            "payload": recipe_payload,
            "simulated": True,
        }
    
    async def _execute_platform(
        self,
        action: RoutedAction,
        route: FabricRoute,
        plane: FabricPlane
    ) -> Dict[str, Any]:
        """Execute action via Kafka/event bus publish."""
        action.status = RouteStatus.EXECUTING
        
        partition_key = action.payload.entity_id or action.id
        
        event = {
            "event_id": str(uuid4()),
            "event_type": f"{action.payload.target_system.value}.{action.payload.action_type.value}",
            "entity_id": action.payload.entity_id,
            "entity_type": action.payload.entity_type,
            "data": action.payload.data,
            "metadata": {
                "agent_id": action.agent_id,
                "tenant_id": action.tenant_id,
                "correlation_id": action.correlation_id,
                "timestamp": datetime.utcnow().isoformat(),
            },
        }
        
        logger.info(
            f"Platform execution: topic={route.kafka_topic} "
            f"partition_key={partition_key}"
        )
        
        return {
            "routed_via": "platform",
            "topic": route.kafka_topic,
            "partition_key": partition_key,
            "event": event,
            "simulated": True,
        }
    
    def get_action(self, action_id: str) -> Optional[RoutedAction]:
        """Get a routed action by ID."""
        return self._action_log.get(action_id)
    
    def list_actions(
        self,
        agent_id: Optional[str] = None,
        status: Optional[RouteStatus] = None,
        limit: int = 100
    ) -> List[RoutedAction]:
        """List routed actions with optional filtering."""
        actions = list(self._action_log.values())
        
        if agent_id:
            actions = [a for a in actions if a.agent_id == agent_id]
        if status:
            actions = [a for a in actions if a.status == status]
        
        actions.sort(key=lambda a: a.created_at, reverse=True)
        return actions[:limit]
    
    def get_active_preset(self) -> FabricPreset:
        """Get the currently active fabric preset."""
        return self._registry.get_active_plane().preset
    
    def set_active_preset(self, preset: FabricPreset) -> None:
        """Set the active fabric preset."""
        self._registry.set_active_preset(preset)


_routers: Dict[str, ActionRouter] = {}


def get_action_router(tenant_id: str = "default") -> ActionRouter:
    """Get or create an action router for a tenant."""
    if tenant_id not in _routers:
        _routers[tenant_id] = ActionRouter(tenant_id)
    return _routers[tenant_id]
