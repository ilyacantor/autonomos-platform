"""
Fabric-Aware Action Executor

High-level executor that routes agent actions through the Fabric Plane Mesh.
Provides a simple interface for agents without exposing fabric complexity.

CRITICAL: Agents cannot connect directly to SaaS apps. All actions
must route through the active Fabric Plane based on Enterprise Preset.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .planes import ActionType, TargetSystem, FabricPreset
from .router import (
    ActionPayload,
    ActionRouter,
    RoutedAction,
    RouteStatus,
    FabricContext,
    get_action_router,
)

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of an action execution through the Fabric Plane."""
    success: bool
    action_id: str
    fabric_preset: str
    primary_plane_id: str
    target_system: str
    action_type: str
    execution_path: str
    result: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "action_id": self.action_id,
            "fabric_preset": self.fabric_preset,
            "primary_plane_id": self.primary_plane_id,
            "target_system": self.target_system,
            "action_type": self.action_type,
            "execution_path": self.execution_path,
            "result": self.result,
            "error": self.error,
            "duration_ms": self.duration_ms,
        }


class ActionExecutor:
    """
    Fabric-aware action executor for AOA agents.
    
    CRITICAL CONSTRAINT: Agents are FORBIDDEN from direct P2P connections
    to SaaS apps. All actions MUST route through the Fabric Plane Mesh.
    
    The executor abstracts the execution path based on Enterprise Preset:
    - PRESET_7_GATEWAY: Route through managed API Gateway
    - PRESET_8_IPAAS: Trigger integration recipes
    - PRESET_9_PLATFORM: Publish to event bus
    - PRESET_10_WAREHOUSE: Insert to staging tables
    - PRESET_6_SCRAPPY: Direct API (only fallback)
    
    Usage:
        executor = ActionExecutor(tenant_id="acme", agent_id="agent_123")
        
        # Get fabric context for agent awareness
        context = executor.get_fabric_context()
        print(f"Routing via: {context.primary_plane_id}")
        
        # Execute action - automatically routed through fabric
        result = await executor.update_customer(
            customer_id="cust_123",
            data={"name": "Updated Name"}
        )
    """
    
    def __init__(self, tenant_id: str = "default", agent_id: Optional[str] = None):
        self.tenant_id = tenant_id
        self.agent_id = agent_id
        self._router = get_action_router(tenant_id)
    
    def get_fabric_context(self) -> FabricContext:
        """
        Get the fabric context for agent awareness.
        
        Agents MUST include Primary_Plane_ID so they know where commands go.
        """
        return self._router.get_fabric_context()
    
    async def execute(
        self,
        target_system: TargetSystem,
        action_type: ActionType,
        entity_id: Optional[str] = None,
        entity_type: str = "unknown",
        data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """
        Execute an action through the Fabric Plane Mesh.
        
        The action will be routed based on the active Enterprise Preset.
        Direct SaaS connections are FORBIDDEN unless in Scrappy mode.
        """
        start_time = datetime.utcnow()
        
        payload = ActionPayload(
            target_system=target_system,
            action_type=action_type,
            entity_id=entity_id,
            entity_type=entity_type,
            data=data or {},
            metadata=metadata or {},
        )
        
        routed = await self._router.route(
            payload=payload,
            agent_id=self.agent_id,
        )
        
        end_time = datetime.utcnow()
        duration_ms = (end_time - start_time).total_seconds() * 1000
        
        return ExecutionResult(
            success=routed.status == RouteStatus.COMPLETED,
            action_id=routed.id,
            fabric_preset=routed.fabric_preset.value if routed.fabric_preset else "unknown",
            primary_plane_id=routed.primary_plane_id or "unknown",
            target_system=target_system.value,
            action_type=action_type.value,
            execution_path=routed.execution_path or "unknown",
            result=routed.result,
            error=routed.error,
            duration_ms=duration_ms,
        )
    
    async def update_customer(
        self,
        customer_id: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """Update a customer in the CRM (routed through fabric)."""
        return await self.execute(
            target_system=TargetSystem.CRM,
            action_type=ActionType.UPDATE,
            entity_id=customer_id,
            entity_type="customer",
            data=data,
            metadata=metadata,
        )
    
    async def create_customer(
        self,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """Create a customer in the CRM (routed through fabric)."""
        return await self.execute(
            target_system=TargetSystem.CRM,
            action_type=ActionType.CREATE,
            entity_type="customer",
            data=data,
            metadata=metadata,
        )
    
    async def get_customer(
        self,
        customer_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """Get a customer from the CRM (routed through fabric)."""
        return await self.execute(
            target_system=TargetSystem.CRM,
            action_type=ActionType.READ,
            entity_id=customer_id,
            entity_type="customer",
            metadata=metadata,
        )
    
    async def update_order(
        self,
        order_id: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """Update an order in the ERP (routed through fabric)."""
        return await self.execute(
            target_system=TargetSystem.ERP,
            action_type=ActionType.UPDATE,
            entity_id=order_id,
            entity_type="order",
            data=data,
            metadata=metadata,
        )
    
    async def create_invoice(
        self,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """Create an invoice in the finance system (routed through fabric)."""
        return await self.execute(
            target_system=TargetSystem.FINANCE,
            action_type=ActionType.CREATE,
            entity_type="invoice",
            data=data,
            metadata=metadata,
        )
    
    async def generate_report(
        self,
        report_id: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """Generate an analytics report (routed through fabric)."""
        return await self.execute(
            target_system=TargetSystem.ANALYTICS,
            action_type=ActionType.EXECUTE,
            entity_id=report_id,
            entity_type="report",
            data=data,
            metadata=metadata,
        )
    
    async def sync_inventory(
        self,
        warehouse_id: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """Sync inventory data (routed through fabric)."""
        return await self.execute(
            target_system=TargetSystem.INVENTORY,
            action_type=ActionType.SYNC,
            entity_id=warehouse_id,
            entity_type="inventory",
            data=data,
            metadata=metadata,
        )
    
    def get_active_fabric(self) -> str:
        """Get the currently active fabric preset name."""
        return self._router.get_active_preset().value
    
    def get_primary_plane_id(self) -> str:
        """Get the primary plane ID for the active fabric."""
        return self.get_fabric_context().primary_plane_id
    
    def set_fabric(self, preset: FabricPreset) -> None:
        """Set the active fabric preset."""
        self._router.set_active_preset(preset)
    
    def is_direct_allowed(self) -> bool:
        """Check if direct SaaS connections are allowed."""
        return self.get_fabric_context().is_direct_allowed


def get_action_executor(
    tenant_id: str = "default",
    agent_id: Optional[str] = None
) -> ActionExecutor:
    """Get an action executor for a tenant/agent."""
    return ActionExecutor(tenant_id=tenant_id, agent_id=agent_id)
