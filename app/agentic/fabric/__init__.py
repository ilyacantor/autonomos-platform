"""
Fabric Plane Mesh Module

GLOBAL ARCHITECTURE: FABRIC PLANE MESH

CRITICAL CONSTRAINT: AAM (The Mesh) DOES NOT connect directly to individual
SaaS applications. AAM connects ONLY to "Fabric Planes" that aggregate data.

The 4 Fabric Planes:
1. IPAAS: (Workato, MuleSoft) -> Control plane for integration flows
2. API_GATEWAY: (Kong, Apigee) -> Direct managed API access
3. EVENT_BUS: (Kafka, EventBridge) -> Streaming backbone
4. DATA_WAREHOUSE: (Snowflake, BigQuery) -> Source of Truth storage

Enterprise Preset Patterns:
- PRESET_6_SCRAPPY: Direct SaaS connections (only fallback)
- PRESET_7_GATEWAY: API Gateway-centric
- PRESET_8_IPAAS: iPaaS-centric
- PRESET_9_PLATFORM: Event Bus-centric
- PRESET_10_WAREHOUSE: Warehouse-centric

Usage:
    from app.agentic.fabric import get_action_executor, FabricPreset
    
    # Create executor with fabric context
    executor = get_action_executor(tenant_id="acme", agent_id="agent_123")
    
    # Check current fabric plane
    context = executor.get_fabric_context()
    print(f"Primary Plane: {context.primary_plane_id}")
    print(f"Direct allowed: {context.is_direct_allowed}")
    
    # Switch to iPaaS mode
    executor.set_fabric(FabricPreset.PRESET_8_IPAAS)
    
    # Execute action - automatically routed through iPaaS
    result = await executor.update_customer(
        customer_id="cust_123",
        data={"name": "New Name"}
    )
    # Result will show: routed_via="ipaas", execution_path="ipaas_recipe"
"""

from .planes import (
    FabricPreset,
    FabricPlane,
    FabricRoute,
    FabricPlaneRegistry,
    ActionType,
    TargetSystem,
    get_fabric_registry,
    create_scrappy_plane,
    create_gateway_plane,
    create_ipaas_plane,
    create_event_bus_plane,
    create_warehouse_plane,
)

from .router import (
    ActionRouter,
    ActionPayload,
    RoutedAction,
    RouteStatus,
    FabricContext,
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
    "create_scrappy_plane",
    "create_gateway_plane",
    "create_ipaas_plane",
    "create_event_bus_plane",
    "create_warehouse_plane",
    "ActionRouter",
    "ActionPayload",
    "RoutedAction",
    "RouteStatus",
    "FabricContext",
    "get_action_router",
    "ActionExecutor",
    "ExecutionResult",
    "get_action_executor",
]
