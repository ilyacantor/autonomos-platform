"""
Fabric Plane Definitions

Defines the enterprise fabric topology for action routing:
- PRESET_1_DIRECT: Direct API calls (development/testing)
- PRESET_8_IPAAS: Route through iPaaS layer (Workato, Tray.io)
- PRESET_9_PLATFORM: Route through Platform layer (Kafka, Event Bus)
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class FabricPreset(str, Enum):
    """Fabric topology presets."""
    PRESET_1_DIRECT = "direct"
    PRESET_8_IPAAS = "ipaas"
    PRESET_9_PLATFORM = "platform"


class ActionType(str, Enum):
    """Types of actions that can be routed."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    QUERY = "query"
    EXECUTE = "execute"
    NOTIFY = "notify"


class TargetSystem(str, Enum):
    """Target systems for action routing."""
    CRM = "crm"
    ERP = "erp"
    HRIS = "hris"
    FINANCE = "finance"
    INVENTORY = "inventory"
    TICKETING = "ticketing"
    ANALYTICS = "analytics"
    CUSTOM = "custom"


@dataclass
class FabricRoute:
    """A route through the fabric to a target system."""
    target_system: TargetSystem
    action_type: ActionType
    
    ipaas_recipe_id: Optional[str] = None
    ipaas_recipe_name: Optional[str] = None
    
    kafka_topic: Optional[str] = None
    kafka_partition_key: Optional[str] = None
    
    direct_endpoint: Optional[str] = None
    direct_method: str = "POST"
    
    timeout_seconds: int = 30
    retry_count: int = 3
    
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FabricPlane:
    """
    A fabric plane defines how actions are routed through the enterprise.
    
    The plane determines whether actions go:
    - Direct: Straight to the target API
    - iPaaS: Through an integration platform (Workato, Tray.io)
    - Platform: Through an event bus (Kafka, Pulsar)
    """
    preset: FabricPreset
    name: str
    description: str
    
    routes: Dict[str, FabricRoute] = field(default_factory=dict)
    
    ipaas_config: Dict[str, Any] = field(default_factory=dict)
    kafka_config: Dict[str, Any] = field(default_factory=dict)
    
    is_active: bool = False
    tenant_id: Optional[str] = None
    
    def get_route(self, target: TargetSystem, action: ActionType) -> Optional[FabricRoute]:
        """Get the route for a target/action combination."""
        key = f"{target.value}:{action.value}"
        return self.routes.get(key)
    
    def add_route(self, route: FabricRoute) -> None:
        """Add a route to the fabric plane."""
        key = f"{route.target_system.value}:{route.action_type.value}"
        self.routes[key] = route


def create_direct_plane(tenant_id: str = "default") -> FabricPlane:
    """Create a direct fabric plane (PRESET_1_DIRECT)."""
    plane = FabricPlane(
        preset=FabricPreset.PRESET_1_DIRECT,
        name="Direct API",
        description="Direct API calls without intermediary layers",
        tenant_id=tenant_id,
    )
    
    plane.add_route(FabricRoute(
        target_system=TargetSystem.CRM,
        action_type=ActionType.UPDATE,
        direct_endpoint="/api/v1/crm/customers/{id}",
        direct_method="PATCH",
    ))
    plane.add_route(FabricRoute(
        target_system=TargetSystem.CRM,
        action_type=ActionType.CREATE,
        direct_endpoint="/api/v1/crm/customers",
        direct_method="POST",
    ))
    plane.add_route(FabricRoute(
        target_system=TargetSystem.CRM,
        action_type=ActionType.READ,
        direct_endpoint="/api/v1/crm/customers/{id}",
        direct_method="GET",
    ))
    
    return plane


def create_ipaas_plane(tenant_id: str = "default") -> FabricPlane:
    """Create an iPaaS fabric plane (PRESET_8_IPAAS)."""
    plane = FabricPlane(
        preset=FabricPreset.PRESET_8_IPAAS,
        name="iPaaS Integration",
        description="Route actions through iPaaS layer (Workato, Tray.io)",
        tenant_id=tenant_id,
        ipaas_config={
            "provider": "workato",
            "workspace_id": None,
            "api_key_secret": "WORKATO_API_KEY",
        },
    )
    
    plane.add_route(FabricRoute(
        target_system=TargetSystem.CRM,
        action_type=ActionType.UPDATE,
        ipaas_recipe_id="recipe_crm_update_customer",
        ipaas_recipe_name="Update Customer in CRM",
    ))
    plane.add_route(FabricRoute(
        target_system=TargetSystem.CRM,
        action_type=ActionType.CREATE,
        ipaas_recipe_id="recipe_crm_create_customer",
        ipaas_recipe_name="Create Customer in CRM",
    ))
    plane.add_route(FabricRoute(
        target_system=TargetSystem.ERP,
        action_type=ActionType.UPDATE,
        ipaas_recipe_id="recipe_erp_update_order",
        ipaas_recipe_name="Update Order in ERP",
    ))
    plane.add_route(FabricRoute(
        target_system=TargetSystem.FINANCE,
        action_type=ActionType.CREATE,
        ipaas_recipe_id="recipe_finance_create_invoice",
        ipaas_recipe_name="Create Invoice in Finance System",
    ))
    
    return plane


def create_platform_plane(tenant_id: str = "default") -> FabricPlane:
    """Create a platform fabric plane (PRESET_9_PLATFORM)."""
    plane = FabricPlane(
        preset=FabricPreset.PRESET_9_PLATFORM,
        name="Platform Event Bus",
        description="Route actions through event bus (Kafka, Pulsar)",
        tenant_id=tenant_id,
        kafka_config={
            "bootstrap_servers": None,
            "security_protocol": "SASL_SSL",
            "sasl_mechanism": "PLAIN",
            "credentials_secret": "KAFKA_CREDENTIALS",
        },
    )
    
    plane.add_route(FabricRoute(
        target_system=TargetSystem.CRM,
        action_type=ActionType.UPDATE,
        kafka_topic="aos.commands.crm.customer.update",
        kafka_partition_key="customer_id",
    ))
    plane.add_route(FabricRoute(
        target_system=TargetSystem.CRM,
        action_type=ActionType.CREATE,
        kafka_topic="aos.commands.crm.customer.create",
        kafka_partition_key="customer_id",
    ))
    plane.add_route(FabricRoute(
        target_system=TargetSystem.ERP,
        action_type=ActionType.UPDATE,
        kafka_topic="aos.commands.erp.order.update",
        kafka_partition_key="order_id",
    ))
    plane.add_route(FabricRoute(
        target_system=TargetSystem.ANALYTICS,
        action_type=ActionType.EXECUTE,
        kafka_topic="aos.commands.analytics.report.generate",
        kafka_partition_key="report_id",
    ))
    
    return plane


class FabricPlaneRegistry:
    """
    Registry of fabric planes for a tenant.
    
    Manages which fabric plane is active and provides
    routing resolution.
    """
    
    def __init__(self, tenant_id: str = "default"):
        self.tenant_id = tenant_id
        self._planes: Dict[FabricPreset, FabricPlane] = {}
        self._active_preset: FabricPreset = FabricPreset.PRESET_1_DIRECT
        
        self._planes[FabricPreset.PRESET_1_DIRECT] = create_direct_plane(tenant_id)
        self._planes[FabricPreset.PRESET_8_IPAAS] = create_ipaas_plane(tenant_id)
        self._planes[FabricPreset.PRESET_9_PLATFORM] = create_platform_plane(tenant_id)
    
    def get_active_plane(self) -> FabricPlane:
        """Get the currently active fabric plane."""
        return self._planes[self._active_preset]
    
    def set_active_preset(self, preset: FabricPreset) -> None:
        """Set the active fabric preset."""
        if preset not in self._planes:
            raise ValueError(f"Unknown fabric preset: {preset}")
        
        for p in self._planes.values():
            p.is_active = False
        
        self._active_preset = preset
        self._planes[preset].is_active = True
        logger.info(f"Fabric plane switched to {preset.value} for tenant {self.tenant_id}")
    
    def get_plane(self, preset: FabricPreset) -> Optional[FabricPlane]:
        """Get a specific fabric plane."""
        return self._planes.get(preset)
    
    def list_planes(self) -> List[FabricPlane]:
        """List all available fabric planes."""
        return list(self._planes.values())
    
    def configure_ipaas(
        self,
        provider: str,
        workspace_id: str,
        api_key_secret: str = "WORKATO_API_KEY"
    ) -> None:
        """Configure the iPaaS plane."""
        plane = self._planes[FabricPreset.PRESET_8_IPAAS]
        plane.ipaas_config.update({
            "provider": provider,
            "workspace_id": workspace_id,
            "api_key_secret": api_key_secret,
        })
    
    def configure_kafka(
        self,
        bootstrap_servers: str,
        security_protocol: str = "SASL_SSL",
        credentials_secret: str = "KAFKA_CREDENTIALS"
    ) -> None:
        """Configure the platform/Kafka plane."""
        plane = self._planes[FabricPreset.PRESET_9_PLATFORM]
        plane.kafka_config.update({
            "bootstrap_servers": bootstrap_servers,
            "security_protocol": security_protocol,
            "credentials_secret": credentials_secret,
        })


_plane_registries: Dict[str, FabricPlaneRegistry] = {}


def get_fabric_registry(tenant_id: str = "default") -> FabricPlaneRegistry:
    """Get or create a fabric plane registry for a tenant."""
    if tenant_id not in _plane_registries:
        _plane_registries[tenant_id] = FabricPlaneRegistry(tenant_id)
    return _plane_registries[tenant_id]
