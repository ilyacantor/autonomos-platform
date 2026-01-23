"""
Agent Registry

Central registry for agent inventory and metadata management:
- Agent discovery and inventory
- Agent metadata and ownership tracking
- Trust tier management
- Domain classification
"""

from app.agentic.registry.models import (
    AgentRecord,
    AgentMetadata,
    AgentOwnership,
    TrustTier,
    AgentDomain,
    AgentStatus,
)
from app.agentic.registry.inventory import (
    AgentInventory,
    InventoryFilter,
    InventoryStats,
    get_agent_inventory,
)
from app.agentic.registry.ownership import (
    OwnershipManager,
    OwnershipTransfer,
    get_ownership_manager,
)

__all__ = [
    # Models
    "AgentRecord",
    "AgentMetadata",
    "AgentOwnership",
    "TrustTier",
    "AgentDomain",
    "AgentStatus",
    # Inventory
    "AgentInventory",
    "InventoryFilter",
    "InventoryStats",
    "get_agent_inventory",
    # Ownership
    "OwnershipManager",
    "OwnershipTransfer",
    "get_ownership_manager",
]
