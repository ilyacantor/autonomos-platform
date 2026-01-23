"""
Action Router

Routes agent actions through the active Fabric Plane.

CRITICAL CONSTRAINT: AAM (The Mesh) DOES NOT connect directly to individual
SaaS applications unless in "Scrappy" mode. All actions must route through
Fabric Planes that aggregate data.

Execution paths based on Enterprise Preset:
- PRESET_6_SCRAPPY: Direct REST API calls (only fallback)
- PRESET_7_GATEWAY: Route through API Gateway (Kong, Apigee)
- PRESET_8_IPAAS: Trigger integration recipes (Workato, MuleSoft)
- PRESET_9_PLATFORM: Publish to Event Bus (Kafka, EventBridge)
- PRESET_10_WAREHOUSE: Insert to staging tables (Snowflake, BigQuery)
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
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
    BLOCKED = "blocked"


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
class FabricContext:
    """
    Context about the active Fabric Plane for agent awareness.
    
    Agents MUST include Primary_Plane_ID to know where to send commands.
    """
    primary_plane_id: str
    fabric_preset: FabricPreset
    is_direct_allowed: bool
    tenant_id: str
    plane_name: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary_plane_id": self.primary_plane_id,
            "fabric_preset": self.fabric_preset.value,
            "is_direct_allowed": self.is_direct_allowed,
            "tenant_id": self.tenant_id,
            "plane_name": self.plane_name,
        }


@dataclass
class RoutedAction:
    """A routed action with tracking information."""
    id: str = field(default_factory=lambda: str(uuid4()))
    
    payload: ActionPayload = field(default_factory=lambda: ActionPayload(
        target_system=TargetSystem.CUSTOM,
        action_type=ActionType.EXECUTE
    ))
    route: Optional[FabricRoute] = None
    fabric_preset: Optional[FabricPreset] = None
    primary_plane_id: Optional[str] = None
    
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
    
    execution_path: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "payload": self.payload.to_dict(),
            "fabric_preset": self.fabric_preset.value if self.fabric_preset else None,
            "primary_plane_id": self.primary_plane_id,
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
            "execution_path": self.execution_path,
        }


class ActionRouter:
    """
    Routes agent actions through the Fabric Plane Mesh.
    
    CRITICAL: AAM owns the connection to Fabric Planes, NOT individual apps.
    When an agent wants to execute an action, it MUST route through the
    active Fabric Plane based on the Enterprise Preset Pattern.
    
    Execution paths:
    - PRESET_7_GATEWAY: Route through managed API Gateway
    - PRESET_8_IPAAS: Trigger integration recipe via webhook
    - PRESET_9_PLATFORM: Publish command message to Kafka
    - PRESET_10_WAREHOUSE: Insert to reverse ETL staging table
    - PRESET_6_SCRAPPY: Direct API call (only fallback option)
    """
    
    def __init__(self, tenant_id: str = "default"):
        self.tenant_id = tenant_id
        self._registry = get_fabric_registry(tenant_id)
        self._action_log: Dict[str, RoutedAction] = {}
    
    def get_fabric_context(self) -> FabricContext:
        """
        Get the fabric context for agent awareness.
        
        Agents MUST include Primary_Plane_ID to know where to route actions.
        """
        plane = self._registry.get_active_plane()
        return FabricContext(
            primary_plane_id=plane.primary_plane_id,
            fabric_preset=plane.preset,
            is_direct_allowed=self._registry.is_direct_allowed(),
            tenant_id=self.tenant_id,
            plane_name=plane.name,
        )
    
    async def route(
        self,
        payload: ActionPayload,
        agent_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> RoutedAction:
        """
        Route an action through the active Fabric Plane.
        
        The action will be routed based on the Enterprise Preset Pattern.
        Direct API calls are FORBIDDEN unless in SCRAPPY mode.
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
            action.primary_plane_id = plane.primary_plane_id
            
            route = plane.get_route(payload.target_system, payload.action_type)
            if not route:
                action.status = RouteStatus.FAILED
                action.error = (
                    f"No route found for {payload.target_system.value}:{payload.action_type.value} "
                    f"in fabric plane {plane.preset.value}"
                )
                logger.warning(f"No fabric route: {action.error}")
                return action
            
            action.route = route
            action.status = RouteStatus.ROUTING
            action.routed_at = datetime.utcnow()
            
            if plane.preset == FabricPreset.PRESET_7_GATEWAY:
                result = await self._execute_gateway(action, route, plane)
                action.execution_path = "api_gateway"
            elif plane.preset == FabricPreset.PRESET_8_IPAAS:
                result = await self._execute_ipaas(action, route, plane)
                action.execution_path = "ipaas_recipe"
            elif plane.preset == FabricPreset.PRESET_9_PLATFORM:
                result = await self._execute_event_bus(action, route, plane)
                action.execution_path = "kafka_topic"
            elif plane.preset == FabricPreset.PRESET_10_WAREHOUSE:
                result = await self._execute_warehouse(action, route, plane)
                action.execution_path = "staging_table"
            elif plane.preset == FabricPreset.PRESET_6_SCRAPPY:
                result = await self._execute_scrappy(action, route)
                action.execution_path = "direct_api"
            else:
                raise ValueError(f"Unknown fabric preset: {plane.preset}")
            
            action.result = result
            action.status = RouteStatus.COMPLETED
            action.completed_at = datetime.utcnow()
            
            logger.info(
                f"Action {action.id} completed via {plane.preset.value} "
                f"(plane_id={plane.primary_plane_id}): "
                f"{payload.target_system.value}:{payload.action_type.value}"
            )
            
        except asyncio.TimeoutError:
            action.status = RouteStatus.TIMEOUT
            timeout_secs = action.route.timeout_seconds if action.route else 30
            action.error = f"Action timed out after {timeout_secs}s"
            logger.error(f"Action {action.id} timeout: {action.error}")
            
        except Exception as e:
            action.status = RouteStatus.FAILED
            action.error = str(e)
            logger.error(f"Action {action.id} failed: {e}")
        
        return action
    
    async def _execute_gateway(
        self,
        action: RoutedAction,
        route: FabricRoute,
        plane: FabricPlane
    ) -> Dict[str, Any]:
        """
        Execute action via API Gateway (Kong, Apigee).
        
        Routes through managed gateway with auth, rate limiting, transforms.
        Gateway handles the actual connection to the target app.
        """
        action.status = RouteStatus.EXECUTING
        
        gateway_path = route.gateway_path or ""
        if action.payload.entity_id and "{id}" in gateway_path:
            gateway_path = gateway_path.replace("{id}", action.payload.entity_id)
        
        gateway_request = {
            "route_id": route.gateway_route_id,
            "upstream": route.gateway_upstream,
            "path": gateway_path,
            "method": route.direct_method,
            "payload": action.payload.data,
            "headers": {
                "X-Correlation-ID": action.correlation_id,
                "X-Agent-ID": action.agent_id,
                "X-Tenant-ID": action.tenant_id,
            },
        }
        
        logger.info(
            f"Gateway execution: route={route.gateway_route_id} "
            f"upstream={route.gateway_upstream} path={gateway_path}"
        )
        
        return {
            "routed_via": "api_gateway",
            "provider": plane.gateway_config.get("provider", "kong"),
            "route_id": route.gateway_route_id,
            "upstream": route.gateway_upstream,
            "path": gateway_path,
            "request": gateway_request,
            "execution_mode": "gateway_proxy",
        }
    
    async def _execute_ipaas(
        self,
        action: RoutedAction,
        route: FabricRoute,
        plane: FabricPlane
    ) -> Dict[str, Any]:
        """
        Execute action via iPaaS recipe trigger.
        
        Triggers the Integration Recipe via webhook/signal.
        iPaaS handles the orchestration and connection to target app.
        """
        action.status = RouteStatus.EXECUTING
        
        recipe_payload = {
            "recipe_id": route.ipaas_recipe_id,
            "recipe_name": route.ipaas_recipe_name,
            "webhook_url": route.ipaas_webhook_url,
            "input": {
                "entity_id": action.payload.entity_id,
                "entity_type": action.payload.entity_type,
                "action_type": action.payload.action_type.value,
                "data": action.payload.data,
                "correlation_id": action.correlation_id,
                "agent_id": action.agent_id,
            },
            "metadata": {
                "tenant_id": action.tenant_id,
                "primary_plane_id": plane.primary_plane_id,
                "timestamp": datetime.utcnow().isoformat(),
            },
        }
        
        logger.info(
            f"iPaaS execution: recipe={route.ipaas_recipe_id} "
            f"({route.ipaas_recipe_name}) via {route.ipaas_webhook_url}"
        )
        
        return {
            "routed_via": "ipaas",
            "provider": plane.ipaas_config.get("provider", "workato"),
            "recipe_id": route.ipaas_recipe_id,
            "recipe_name": route.ipaas_recipe_name,
            "webhook_url": route.ipaas_webhook_url,
            "payload": recipe_payload,
            "execution_mode": "webhook_trigger",
        }
    
    async def _execute_event_bus(
        self,
        action: RoutedAction,
        route: FabricRoute,
        plane: FabricPlane
    ) -> Dict[str, Any]:
        """
        Execute action via Event Bus (Kafka, EventBridge).
        
        Publishes a Command Message to the designated topic.
        The streaming backbone handles delivery to consumers.
        """
        action.status = RouteStatus.EXECUTING
        
        partition_key = action.payload.entity_id or action.id
        
        command_message = {
            "command_id": str(uuid4()),
            "command_type": f"{action.payload.target_system.value}.{action.payload.action_type.value}",
            "entity_id": action.payload.entity_id,
            "entity_type": action.payload.entity_type,
            "payload": action.payload.data,
            "metadata": {
                "agent_id": action.agent_id,
                "tenant_id": action.tenant_id,
                "correlation_id": action.correlation_id,
                "primary_plane_id": plane.primary_plane_id,
                "timestamp": datetime.utcnow().isoformat(),
                "source": "aos_agent",
            },
        }
        
        logger.info(
            f"Event Bus execution: topic={route.kafka_topic} "
            f"partition_key={partition_key} command_type={command_message['command_type']}"
        )
        
        return {
            "routed_via": "event_bus",
            "topic": route.kafka_topic,
            "partition_key": partition_key,
            "command_message": command_message,
            "execution_mode": "kafka_publish",
        }
    
    async def _execute_warehouse(
        self,
        action: RoutedAction,
        route: FabricRoute,
        plane: FabricPlane
    ) -> Dict[str, Any]:
        """
        Execute action via Warehouse (Reverse ETL).
        
        Writes to a staging table that syncs to target via Reverse ETL.
        Data Warehouse is the Source of Truth.
        """
        action.status = RouteStatus.EXECUTING
        
        staging_record = {
            "id": str(uuid4()),
            "entity_id": action.payload.entity_id,
            "entity_type": action.payload.entity_type,
            "action_type": action.payload.action_type.value,
            "payload": json.dumps(action.payload.data),
            "agent_id": action.agent_id,
            "tenant_id": action.tenant_id,
            "correlation_id": action.correlation_id,
            "primary_plane_id": plane.primary_plane_id,
            "status": "pending_sync",
            "created_at": datetime.utcnow().isoformat(),
        }
        
        full_table_name = f"{route.warehouse_schema}.{route.warehouse_table}"
        
        logger.info(
            f"Warehouse execution: {route.warehouse_operation} into "
            f"{full_table_name} for entity {action.payload.entity_id}"
        )
        
        return {
            "routed_via": "data_warehouse",
            "provider": plane.warehouse_config.get("provider", "snowflake"),
            "schema": route.warehouse_schema,
            "table": route.warehouse_table,
            "full_table_name": full_table_name,
            "operation": route.warehouse_operation,
            "staging_record": staging_record,
            "sync_interval_minutes": plane.warehouse_config.get("sync_interval_minutes", 5),
            "execution_mode": "reverse_etl",
        }
    
    async def _execute_scrappy(
        self,
        action: RoutedAction,
        route: FabricRoute
    ) -> Dict[str, Any]:
        """
        Execute action via direct REST API call.
        
        WARNING: This is the ONLY execution path where direct SaaS
        connections are allowed. Only use in Scrappy mode.
        """
        action.status = RouteStatus.EXECUTING
        
        endpoint = route.direct_endpoint or ""
        if action.payload.entity_id and "{id}" in endpoint:
            endpoint = endpoint.replace("{id}", action.payload.entity_id)
        
        logger.info(
            f"Scrappy (direct) execution: {route.direct_method} {endpoint} "
            f"(entity: {action.payload.entity_type})"
        )
        
        return {
            "routed_via": "scrappy",
            "method": route.direct_method,
            "endpoint": endpoint,
            "payload": action.payload.data,
            "execution_mode": "direct_rest_api",
            "warning": "Direct SaaS connection - only allowed in Scrappy mode",
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
