"""
Fabric Plane Definitions

GLOBAL ARCHITECTURE: FABRIC PLANE MESH

CRITICAL CONSTRAINT: AAM (The Mesh) DOES NOT connect directly to individual 
SaaS applications (e.g., Salesforce, HubSpot) unless running in "Scrappy" mode.
AAM connects ONLY to "Fabric Planes" that aggregate data.

The 4 Fabric Planes:
1. IPAAS: (Workato, MuleSoft) -> Control plane for integration flows
2. API_GATEWAY: (Kong, Apigee) -> Direct managed API access
3. EVENT_BUS: (Kafka, EventBridge) -> Streaming backbone
4. DATA_WAREHOUSE: (Snowflake, BigQuery) -> Source of Truth storage

Enterprise Preset Patterns:
- PRESET_6_SCRAPPY: Direct SaaS connections (only fallback - startups/dev)
- PRESET_7_GATEWAY: API Gateway-centric (Kong/Apigee manages all APIs)
- PRESET_8_IPAAS: iPaaS-centric (Workato/MuleSoft orchestrates)
- PRESET_9_PLATFORM: Event Bus-centric (Kafka/EventBridge streaming)
- PRESET_10_WAREHOUSE: Warehouse-centric (Snowflake/BigQuery as SoT)
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class FabricPreset(str, Enum):
    """
    Enterprise Preset Patterns for Fabric Plane selection.
    
    AAM must support switching logic based on org type:
    - Scrappy orgs -> Direct SaaS connections
    - Gateway-centric -> All via API Gateway
    - iPaaS-centric -> All via integration platform
    - Platform-oriented -> All via event streaming
    - Warehouse-centric -> All via data warehouse
    """
    PRESET_6_SCRAPPY = "scrappy"
    PRESET_7_GATEWAY = "api_gateway"
    PRESET_8_IPAAS = "ipaas"
    PRESET_9_PLATFORM = "event_bus"
    PRESET_10_WAREHOUSE = "data_warehouse"


class ActionType(str, Enum):
    """Types of actions that can be routed through fabric."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    QUERY = "query"
    EXECUTE = "execute"
    NOTIFY = "notify"
    SYNC = "sync"
    INGEST = "ingest"


class TargetSystem(str, Enum):
    """Target systems for action routing."""
    CRM = "crm"
    ERP = "erp"
    HRIS = "hris"
    FINANCE = "finance"
    INVENTORY = "inventory"
    TICKETING = "ticketing"
    ANALYTICS = "analytics"
    DATA_WAREHOUSE = "data_warehouse"
    MARKETING = "marketing"
    SUPPORT = "support"
    CUSTOM = "custom"


@dataclass
class FabricRoute:
    """A route through the fabric plane to a target system."""
    target_system: TargetSystem
    action_type: ActionType
    
    gateway_route_id: Optional[str] = None
    gateway_upstream: Optional[str] = None
    gateway_path: Optional[str] = None
    
    ipaas_recipe_id: Optional[str] = None
    ipaas_recipe_name: Optional[str] = None
    ipaas_webhook_url: Optional[str] = None
    
    kafka_topic: Optional[str] = None
    kafka_partition_key: Optional[str] = None
    
    warehouse_schema: Optional[str] = None
    warehouse_table: Optional[str] = None
    warehouse_operation: Optional[str] = None
    
    direct_endpoint: Optional[str] = None
    direct_method: str = "POST"
    
    timeout_seconds: int = 30
    retry_count: int = 3
    
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FabricPlane:
    """
    A Fabric Plane defines how AAM routes actions through the enterprise.
    
    CRITICAL: AAM owns the connection to Fabric Planes, NOT individual apps.
    AAM must support self-healing of Plane connections.
    
    Plane types:
    - IPAAS: Control plane for integration flows
    - API_GATEWAY: Direct managed API access
    - EVENT_BUS: Streaming backbone
    - DATA_WAREHOUSE: Source of Truth storage
    """
    preset: FabricPreset
    name: str
    description: str
    primary_plane_id: str = ""
    
    routes: Dict[str, FabricRoute] = field(default_factory=dict)
    
    gateway_config: Dict[str, Any] = field(default_factory=dict)
    ipaas_config: Dict[str, Any] = field(default_factory=dict)
    kafka_config: Dict[str, Any] = field(default_factory=dict)
    warehouse_config: Dict[str, Any] = field(default_factory=dict)
    
    is_active: bool = False
    tenant_id: Optional[str] = None
    
    self_healing_enabled: bool = True
    health_check_interval_seconds: int = 60
    last_health_check: Optional[str] = None
    health_status: str = "unknown"
    
    def get_route(self, target: TargetSystem, action: ActionType) -> Optional[FabricRoute]:
        """Get the route for a target/action combination."""
        key = f"{target.value}:{action.value}"
        return self.routes.get(key)
    
    def add_route(self, route: FabricRoute) -> None:
        """Add a route to the fabric plane."""
        key = f"{route.target_system.value}:{route.action_type.value}"
        self.routes[key] = route


def _get_http_method(action: ActionType) -> str:
    """Map action type to HTTP method."""
    return {
        ActionType.CREATE: "POST",
        ActionType.READ: "GET",
        ActionType.UPDATE: "PATCH",
        ActionType.DELETE: "DELETE",
        ActionType.QUERY: "GET",
        ActionType.EXECUTE: "POST",
        ActionType.NOTIFY: "POST",
        ActionType.SYNC: "POST",
        ActionType.INGEST: "POST",
    }.get(action, "POST")


def create_scrappy_plane(tenant_id: str = "default") -> FabricPlane:
    """
    PRESET_6_SCRAPPY: Direct SaaS connections.
    
    WARNING: This is the ONLY mode where direct app connections are allowed.
    Use only for startups/dev without enterprise fabric infrastructure.
    """
    plane = FabricPlane(
        preset=FabricPreset.PRESET_6_SCRAPPY,
        name="Scrappy Mode (Direct)",
        description="Direct SaaS connections - only fallback for startups/dev without fabric",
        primary_plane_id=f"scrappy_{tenant_id}",
        tenant_id=tenant_id,
        self_healing_enabled=False,
    )
    
    for target in TargetSystem:
        for action in ActionType:
            plane.add_route(FabricRoute(
                target_system=target,
                action_type=action,
                direct_endpoint=f"/api/v1/{target.value}/{{id}}" if action != ActionType.CREATE else f"/api/v1/{target.value}",
                direct_method=_get_http_method(action),
            ))
    
    return plane


def create_gateway_plane(tenant_id: str = "default") -> FabricPlane:
    """
    PRESET_7_GATEWAY: API Gateway-centric.
    
    All traffic flows through managed API Gateway (Kong, Apigee).
    Gateway handles auth, rate limiting, transforms.
    """
    plane = FabricPlane(
        preset=FabricPreset.PRESET_7_GATEWAY,
        name="API Gateway Plane",
        description="Route through API Gateway (Kong, Apigee) - managed API access",
        primary_plane_id=f"gateway_{tenant_id}",
        tenant_id=tenant_id,
        gateway_config={
            "provider": "kong",
            "admin_url": None,
            "proxy_url": None,
            "api_key_secret": "GATEWAY_API_KEY",
            "workspace": "default",
        },
    )
    
    plane.add_route(FabricRoute(
        target_system=TargetSystem.CRM,
        action_type=ActionType.UPDATE,
        gateway_route_id="crm-customer-update",
        gateway_upstream="salesforce-upstream",
        gateway_path="/crm/v1/customers/{id}",
    ))
    plane.add_route(FabricRoute(
        target_system=TargetSystem.CRM,
        action_type=ActionType.CREATE,
        gateway_route_id="crm-customer-create",
        gateway_upstream="salesforce-upstream",
        gateway_path="/crm/v1/customers",
    ))
    plane.add_route(FabricRoute(
        target_system=TargetSystem.CRM,
        action_type=ActionType.READ,
        gateway_route_id="crm-customer-get",
        gateway_upstream="salesforce-upstream",
        gateway_path="/crm/v1/customers/{id}",
    ))
    plane.add_route(FabricRoute(
        target_system=TargetSystem.ERP,
        action_type=ActionType.UPDATE,
        gateway_route_id="erp-order-update",
        gateway_upstream="netsuite-upstream",
        gateway_path="/erp/v1/orders/{id}",
    ))
    plane.add_route(FabricRoute(
        target_system=TargetSystem.FINANCE,
        action_type=ActionType.CREATE,
        gateway_route_id="finance-invoice-create",
        gateway_upstream="stripe-upstream",
        gateway_path="/finance/v1/invoices",
    ))
    
    return plane


def create_ipaas_plane(tenant_id: str = "default") -> FabricPlane:
    """
    PRESET_8_IPAAS: iPaaS-centric.
    
    All traffic flows through integration platform (Workato, MuleSoft).
    iPaaS orchestrates the integration flows and transformations.
    """
    plane = FabricPlane(
        preset=FabricPreset.PRESET_8_IPAAS,
        name="iPaaS Integration Plane",
        description="Route through iPaaS (Workato, MuleSoft) - integration flow orchestration",
        primary_plane_id=f"ipaas_{tenant_id}",
        tenant_id=tenant_id,
        ipaas_config={
            "provider": "workato",
            "workspace_id": None,
            "api_key_secret": "WORKATO_API_KEY",
            "webhook_base_url": None,
        },
    )
    
    plane.add_route(FabricRoute(
        target_system=TargetSystem.CRM,
        action_type=ActionType.UPDATE,
        ipaas_recipe_id="recipe_crm_update_customer",
        ipaas_recipe_name="Update Customer in CRM",
        ipaas_webhook_url="/webhooks/workato/crm/customer/update",
    ))
    plane.add_route(FabricRoute(
        target_system=TargetSystem.CRM,
        action_type=ActionType.CREATE,
        ipaas_recipe_id="recipe_crm_create_customer",
        ipaas_recipe_name="Create Customer in CRM",
        ipaas_webhook_url="/webhooks/workato/crm/customer/create",
    ))
    plane.add_route(FabricRoute(
        target_system=TargetSystem.CRM,
        action_type=ActionType.READ,
        ipaas_recipe_id="recipe_crm_get_customer",
        ipaas_recipe_name="Get Customer from CRM",
        ipaas_webhook_url="/webhooks/workato/crm/customer/get",
    ))
    plane.add_route(FabricRoute(
        target_system=TargetSystem.ERP,
        action_type=ActionType.UPDATE,
        ipaas_recipe_id="recipe_erp_update_order",
        ipaas_recipe_name="Update Order in ERP",
        ipaas_webhook_url="/webhooks/workato/erp/order/update",
    ))
    plane.add_route(FabricRoute(
        target_system=TargetSystem.FINANCE,
        action_type=ActionType.CREATE,
        ipaas_recipe_id="recipe_finance_create_invoice",
        ipaas_recipe_name="Create Invoice",
        ipaas_webhook_url="/webhooks/workato/finance/invoice/create",
    ))
    plane.add_route(FabricRoute(
        target_system=TargetSystem.HRIS,
        action_type=ActionType.UPDATE,
        ipaas_recipe_id="recipe_hris_update_employee",
        ipaas_recipe_name="Update Employee in HRIS",
        ipaas_webhook_url="/webhooks/workato/hris/employee/update",
    ))
    
    return plane


def create_event_bus_plane(tenant_id: str = "default") -> FabricPlane:
    """
    PRESET_9_PLATFORM: Event Bus-centric.
    
    All traffic flows through streaming backbone (Kafka, EventBridge).
    Commands are published as messages, not API calls.
    """
    plane = FabricPlane(
        preset=FabricPreset.PRESET_9_PLATFORM,
        name="Event Bus Streaming Plane",
        description="Route through Event Bus (Kafka, EventBridge) - streaming backbone",
        primary_plane_id=f"eventbus_{tenant_id}",
        tenant_id=tenant_id,
        kafka_config={
            "bootstrap_servers": None,
            "security_protocol": "SASL_SSL",
            "sasl_mechanism": "PLAIN",
            "credentials_secret": "KAFKA_CREDENTIALS",
            "command_topic_prefix": "aos.commands",
            "event_topic_prefix": "aos.events",
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
        kafka_partition_key="tenant_id",
    ))
    plane.add_route(FabricRoute(
        target_system=TargetSystem.CRM,
        action_type=ActionType.DELETE,
        kafka_topic="aos.commands.crm.customer.delete",
        kafka_partition_key="customer_id",
    ))
    plane.add_route(FabricRoute(
        target_system=TargetSystem.ERP,
        action_type=ActionType.UPDATE,
        kafka_topic="aos.commands.erp.order.update",
        kafka_partition_key="order_id",
    ))
    plane.add_route(FabricRoute(
        target_system=TargetSystem.ERP,
        action_type=ActionType.CREATE,
        kafka_topic="aos.commands.erp.order.create",
        kafka_partition_key="tenant_id",
    ))
    plane.add_route(FabricRoute(
        target_system=TargetSystem.FINANCE,
        action_type=ActionType.CREATE,
        kafka_topic="aos.commands.finance.invoice.create",
        kafka_partition_key="tenant_id",
    ))
    plane.add_route(FabricRoute(
        target_system=TargetSystem.ANALYTICS,
        action_type=ActionType.EXECUTE,
        kafka_topic="aos.commands.analytics.report.generate",
        kafka_partition_key="report_id",
    ))
    plane.add_route(FabricRoute(
        target_system=TargetSystem.INVENTORY,
        action_type=ActionType.SYNC,
        kafka_topic="aos.commands.inventory.sync",
        kafka_partition_key="warehouse_id",
    ))
    
    return plane


def create_warehouse_plane(tenant_id: str = "default") -> FabricPlane:
    """
    PRESET_10_WAREHOUSE: Warehouse-centric.
    
    Data Warehouse is the Source of Truth (Snowflake, BigQuery).
    Actions are written to staging tables, then synced via Reverse ETL.
    """
    plane = FabricPlane(
        preset=FabricPreset.PRESET_10_WAREHOUSE,
        name="Data Warehouse Plane (Reverse ETL)",
        description="Route through Data Warehouse (Snowflake, BigQuery) - Source of Truth",
        primary_plane_id=f"warehouse_{tenant_id}",
        tenant_id=tenant_id,
        warehouse_config={
            "provider": "snowflake",
            "connection_secret": "WAREHOUSE_CONNECTION_URL",
            "staging_schema": "aos_staging",
            "sync_interval_minutes": 5,
            "batch_size": 1000,
        },
    )
    
    plane.add_route(FabricRoute(
        target_system=TargetSystem.CRM,
        action_type=ActionType.UPDATE,
        warehouse_schema="aos_staging",
        warehouse_table="stg_crm_customer_updates",
        warehouse_operation="UPSERT",
    ))
    plane.add_route(FabricRoute(
        target_system=TargetSystem.CRM,
        action_type=ActionType.CREATE,
        warehouse_schema="aos_staging",
        warehouse_table="stg_crm_customer_creates",
        warehouse_operation="INSERT",
    ))
    plane.add_route(FabricRoute(
        target_system=TargetSystem.ERP,
        action_type=ActionType.UPDATE,
        warehouse_schema="aos_staging",
        warehouse_table="stg_erp_order_updates",
        warehouse_operation="UPSERT",
    ))
    plane.add_route(FabricRoute(
        target_system=TargetSystem.FINANCE,
        action_type=ActionType.CREATE,
        warehouse_schema="aos_staging",
        warehouse_table="stg_finance_invoices",
        warehouse_operation="INSERT",
    ))
    plane.add_route(FabricRoute(
        target_system=TargetSystem.ANALYTICS,
        action_type=ActionType.EXECUTE,
        warehouse_schema="aos_staging",
        warehouse_table="stg_analytics_jobs",
        warehouse_operation="INSERT",
    ))
    plane.add_route(FabricRoute(
        target_system=TargetSystem.DATA_WAREHOUSE,
        action_type=ActionType.INGEST,
        warehouse_schema="aos_staging",
        warehouse_table="stg_ingest_queue",
        warehouse_operation="INSERT",
    ))
    
    return plane


class FabricPlaneRegistry:
    """
    Registry of Fabric Planes for a tenant.
    
    AAM owns the connection to Fabric Planes (not individual apps).
    This registry manages:
    - Active plane selection based on Enterprise Preset
    - Self-healing of plane connections
    - Routing resolution
    """
    
    def __init__(self, tenant_id: str = "default"):
        self.tenant_id = tenant_id
        self._planes: Dict[FabricPreset, FabricPlane] = {}
        self._active_preset: FabricPreset = FabricPreset.PRESET_6_SCRAPPY
        
        self._planes[FabricPreset.PRESET_6_SCRAPPY] = create_scrappy_plane(tenant_id)
        self._planes[FabricPreset.PRESET_7_GATEWAY] = create_gateway_plane(tenant_id)
        self._planes[FabricPreset.PRESET_8_IPAAS] = create_ipaas_plane(tenant_id)
        self._planes[FabricPreset.PRESET_9_PLATFORM] = create_event_bus_plane(tenant_id)
        self._planes[FabricPreset.PRESET_10_WAREHOUSE] = create_warehouse_plane(tenant_id)
    
    def get_active_plane(self) -> FabricPlane:
        """Get the currently active fabric plane."""
        return self._planes[self._active_preset]
    
    def get_primary_plane_id(self) -> str:
        """Get the primary plane ID for agent context."""
        return self._planes[self._active_preset].primary_plane_id
    
    def set_active_preset(self, preset: FabricPreset) -> None:
        """Set the active fabric preset."""
        if preset not in self._planes:
            raise ValueError(f"Unknown fabric preset: {preset}")
        
        for p in self._planes.values():
            p.is_active = False
        
        self._active_preset = preset
        self._planes[preset].is_active = True
        logger.info(
            f"Fabric plane switched to {preset.value} "
            f"(plane_id={self._planes[preset].primary_plane_id}) "
            f"for tenant {self.tenant_id}"
        )
    
    def get_plane(self, preset: FabricPreset) -> Optional[FabricPlane]:
        """Get a specific fabric plane."""
        return self._planes.get(preset)
    
    def list_planes(self) -> List[FabricPlane]:
        """List all available fabric planes."""
        return list(self._planes.values())
    
    def is_direct_allowed(self) -> bool:
        """Check if direct SaaS connections are allowed (only in SCRAPPY)."""
        return self._active_preset == FabricPreset.PRESET_6_SCRAPPY
    
    def configure_gateway(
        self,
        provider: str,
        admin_url: str,
        proxy_url: str,
        api_key_secret: str = "GATEWAY_API_KEY"
    ) -> None:
        """Configure the API Gateway plane."""
        plane = self._planes[FabricPreset.PRESET_7_GATEWAY]
        plane.gateway_config.update({
            "provider": provider,
            "admin_url": admin_url,
            "proxy_url": proxy_url,
            "api_key_secret": api_key_secret,
        })
    
    def configure_ipaas(
        self,
        provider: str,
        workspace_id: str,
        webhook_base_url: str,
        api_key_secret: str = "WORKATO_API_KEY"
    ) -> None:
        """Configure the iPaaS plane."""
        plane = self._planes[FabricPreset.PRESET_8_IPAAS]
        plane.ipaas_config.update({
            "provider": provider,
            "workspace_id": workspace_id,
            "webhook_base_url": webhook_base_url,
            "api_key_secret": api_key_secret,
        })
    
    def configure_event_bus(
        self,
        bootstrap_servers: str,
        security_protocol: str = "SASL_SSL",
        credentials_secret: str = "KAFKA_CREDENTIALS"
    ) -> None:
        """Configure the Event Bus/Kafka plane."""
        plane = self._planes[FabricPreset.PRESET_9_PLATFORM]
        plane.kafka_config.update({
            "bootstrap_servers": bootstrap_servers,
            "security_protocol": security_protocol,
            "credentials_secret": credentials_secret,
        })
    
    def configure_warehouse(
        self,
        provider: str,
        connection_secret: str,
        staging_schema: str = "aos_staging",
        sync_interval_minutes: int = 5
    ) -> None:
        """Configure the Warehouse/Reverse ETL plane."""
        plane = self._planes[FabricPreset.PRESET_10_WAREHOUSE]
        plane.warehouse_config.update({
            "provider": provider,
            "connection_secret": connection_secret,
            "staging_schema": staging_schema,
            "sync_interval_minutes": sync_interval_minutes,
        })


_plane_registries: Dict[str, FabricPlaneRegistry] = {}


def get_fabric_registry(tenant_id: str = "default") -> FabricPlaneRegistry:
    """Get or create a fabric plane registry for a tenant."""
    if tenant_id not in _plane_registries:
        _plane_registries[tenant_id] = FabricPlaneRegistry(tenant_id)
    return _plane_registries[tenant_id]
