"""
Fabric Module

Enterprise fabric topology for action routing.
All agent actions must be routed through the Fabric Plane.

Fabric Presets:
- PRESET_1_DIRECT: Direct API calls (dev/test)
- PRESET_8_IPAAS: Route through iPaaS (Workato, Tray.io)
- PRESET_9_PLATFORM: Route through event bus (Kafka)

Usage:
    from app.agentic.fabric import get_action_executor, FabricPreset
    
    executor = get_action_executor(tenant_id="acme", agent_id="agent_123")
    
    # Set the fabric mode
    executor.set_fabric(FabricPreset.PRESET_8_IPAAS)
    
    # Execute action - automatically routed through iPaaS
    result = await executor.update_customer(
        customer_id="cust_123",
        data={"name": "New Name"}
    )
"""

from .planes import (
    FabricPreset,
    FabricPlane,
    FabricRoute,
    FabricPlaneRegistry,
    ActionType,
    TargetSystem,
    get_fabric_registry,
    create_direct_plane,
    create_ipaas_plane,
    create_platform_plane,
)

from .router import (
    ActionRouter,
    ActionPayload,
    RoutedAction,
    RouteStatus,
    get_action_router,
)

from .executor import (
    ActionExecutor,
    ExecutionResult,
    get_action_executor,
)

__all__ = [
    "FabricPreset",
    "FabricPlane",
    "FabricRoute",
    "FabricPlaneRegistry",
    "ActionType",
    "TargetSystem",
    "get_fabric_registry",
    "create_direct_plane",
    "create_ipaas_plane",
    "create_platform_plane",
    "ActionRouter",
    "ActionPayload",
    "RoutedAction",
    "RouteStatus",
    "get_action_router",
    "ActionExecutor",
    "ExecutionResult",
    "get_action_executor",
]
