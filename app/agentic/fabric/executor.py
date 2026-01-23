"""
Fabric-Aware Action Executor

High-level executor that wraps action routing through the Fabric Plane.
Provides a simple interface for agents to execute actions without
knowing the underlying fabric topology.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from .planes import ActionType, TargetSystem, FabricPreset
from .router import ActionPayload, ActionRouter, RoutedAction, RouteStatus, get_action_router

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of an action execution."""
    success: bool
    action_id: str
    fabric_preset: str
    target_system: str
    action_type: str
    result: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "action_id": self.action_id,
            "fabric_preset": self.fabric_preset,
            "target_system": self.target_system,
            "action_type": self.action_type,
            "result": self.result,
            "error": self.error,
            "duration_ms": self.duration_ms,
        }


class ActionExecutor:
    """
    Fabric-aware action executor for agents.
    
    This executor ensures that all agent actions are routed
    through the appropriate Fabric Plane. Agents cannot call
    target APIs directly - they must go through the fabric.
    
    Example usage:
        executor = ActionExecutor(tenant_id="acme")
        
        result = await executor.update_customer(
            customer_id="cust_123",
            data={"name": "Updated Name", "email": "new@example.com"}
        )
        
        if result.success:
            print(f"Customer updated via {result.fabric_preset}")
    """
    
    def __init__(self, tenant_id: str = "default", agent_id: Optional[str] = None):
        self.tenant_id = tenant_id
        self.agent_id = agent_id
        self._router = get_action_router(tenant_id)
    
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
        Execute an action through the Fabric Plane.
        
        Args:
            target_system: Target system (CRM, ERP, etc.)
            action_type: Type of action (CREATE, UPDATE, etc.)
            entity_id: ID of the entity being acted upon
            entity_type: Type of entity (customer, order, etc.)
            data: Action payload data
            metadata: Additional metadata
        
        Returns:
            ExecutionResult with success status and result/error
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
            target_system=target_system.value,
            action_type=action_type.value,
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
        """Update a customer in the CRM."""
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
        """Create a customer in the CRM."""
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
        """Get a customer from the CRM."""
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
        """Update an order in the ERP."""
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
        """Create an invoice in the finance system."""
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
        """Generate an analytics report."""
        return await self.execute(
            target_system=TargetSystem.ANALYTICS,
            action_type=ActionType.EXECUTE,
            entity_id=report_id,
            entity_type="report",
            data=data,
            metadata=metadata,
        )
    
    def get_active_fabric(self) -> str:
        """Get the currently active fabric preset."""
        return self._router.get_active_preset().value
    
    def set_fabric(self, preset: FabricPreset) -> None:
        """Set the active fabric preset."""
        self._router.set_active_preset(preset)


def get_action_executor(
    tenant_id: str = "default",
    agent_id: Optional[str] = None
) -> ActionExecutor:
    """Get an action executor for a tenant/agent."""
    return ActionExecutor(tenant_id=tenant_id, agent_id=agent_id)
