"""
Tool Bundle Registry

Manages tool bundles and their permissions:
- Bundle registration and discovery
- Permission-based access control
- Version management
- Agent capability mapping
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import uuid4

logger = logging.getLogger(__name__)


class ToolPermission(str, Enum):
    """Permission levels for tools."""
    READ = "read"              # Read-only operations
    WRITE = "write"            # Can modify data
    EXECUTE = "execute"        # Can run code/commands
    ADMIN = "admin"            # Full access
    EXTERNAL = "external"      # Can call external APIs
    SENSITIVE = "sensitive"    # Access to sensitive data


class ToolCategory(str, Enum):
    """Categories of tools."""
    DATA = "data"              # Data retrieval/manipulation
    CODE = "code"              # Code execution
    COMMUNICATION = "communication"  # Email, messaging
    FILE = "file"              # File operations
    SEARCH = "search"          # Search capabilities
    ANALYSIS = "analysis"      # Data analysis
    APPROVAL = "approval"      # Approval workflows
    INTEGRATION = "integration"  # External integrations


@dataclass
class Tool:
    """A single tool definition."""

    tool_id: str
    name: str
    description: str
    category: ToolCategory

    # Permissions required to use this tool
    required_permissions: Set[ToolPermission] = field(default_factory=set)

    # Schema for input/output
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None

    # Execution
    handler: Optional[Callable] = None
    async_handler: Optional[Callable] = None

    # Metadata
    version: str = "1.0.0"
    deprecated: bool = False
    replacement_tool_id: Optional[str] = None

    # Cost tracking
    cost_per_invocation: float = 0.0
    cost_per_token: float = 0.0

    # Rate limiting
    max_invocations_per_minute: int = 60
    max_invocations_per_hour: int = 1000

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "required_permissions": [p.value for p in self.required_permissions],
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "version": self.version,
            "deprecated": self.deprecated,
            "replacement_tool_id": self.replacement_tool_id,
            "cost_per_invocation": self.cost_per_invocation,
            "cost_per_token": self.cost_per_token,
            "max_invocations_per_minute": self.max_invocations_per_minute,
            "created_at": self.created_at.isoformat(),
        }

    async def invoke(self, **kwargs) -> Any:
        """Invoke the tool."""
        if self.async_handler:
            return await self.async_handler(**kwargs)
        elif self.handler:
            return self.handler(**kwargs)
        else:
            raise NotImplementedError(f"Tool {self.name} has no handler")


@dataclass
class ToolBundle:
    """A bundle of related tools."""

    bundle_id: str
    name: str
    description: str
    tenant_id: str

    # Tools in this bundle
    tools: List[Tool] = field(default_factory=list)

    # Bundle metadata
    category: ToolCategory = ToolCategory.DATA
    version: str = "1.0.0"
    is_preset: bool = False

    # Access control
    allowed_agent_types: Set[str] = field(default_factory=lambda: {"worker", "specialist", "planner"})
    required_capabilities: Set[str] = field(default_factory=set)

    # Policy
    requires_approval: bool = False
    audit_all_invocations: bool = False

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def add_tool(self, tool: Tool) -> None:
        """Add a tool to the bundle."""
        self.tools.append(tool)
        self.updated_at = datetime.utcnow()

    def remove_tool(self, tool_id: str) -> bool:
        """Remove a tool from the bundle."""
        for i, tool in enumerate(self.tools):
            if tool.tool_id == tool_id:
                self.tools.pop(i)
                self.updated_at = datetime.utcnow()
                return True
        return False

    def get_tool(self, tool_id: str) -> Optional[Tool]:
        """Get a tool by ID."""
        for tool in self.tools:
            if tool.tool_id == tool_id:
                return tool
        return None

    def get_tools_by_category(self, category: ToolCategory) -> List[Tool]:
        """Get all tools in a category."""
        return [t for t in self.tools if t.category == category]

    def to_dict(self) -> dict:
        return {
            "bundle_id": self.bundle_id,
            "name": self.name,
            "description": self.description,
            "tenant_id": self.tenant_id,
            "tools": [t.to_dict() for t in self.tools],
            "category": self.category.value,
            "version": self.version,
            "is_preset": self.is_preset,
            "allowed_agent_types": list(self.allowed_agent_types),
            "required_capabilities": list(self.required_capabilities),
            "requires_approval": self.requires_approval,
            "audit_all_invocations": self.audit_all_invocations,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class BundleRegistry:
    """
    Registry for tool bundles.

    Manages bundle registration, discovery, and access control.
    """

    def __init__(self):
        """Initialize the registry."""
        # Storage keyed by tenant_id -> bundle_id -> bundle
        self._bundles: Dict[str, Dict[str, ToolBundle]] = {}

        # Global preset bundles (shared across tenants)
        self._preset_bundles: Dict[str, ToolBundle] = {}

        # Tool invocation tracking
        self._invocation_counts: Dict[str, Dict[str, int]] = {}  # tool_id -> hour -> count

    def register_bundle(self, bundle: ToolBundle) -> None:
        """Register a tool bundle."""
        if bundle.is_preset:
            self._preset_bundles[bundle.bundle_id] = bundle
        else:
            if bundle.tenant_id not in self._bundles:
                self._bundles[bundle.tenant_id] = {}
            self._bundles[bundle.tenant_id][bundle.bundle_id] = bundle

        logger.info(f"Registered bundle: {bundle.name} ({bundle.bundle_id})")

    def unregister_bundle(self, bundle_id: str, tenant_id: str) -> bool:
        """Unregister a bundle."""
        if tenant_id in self._bundles and bundle_id in self._bundles[tenant_id]:
            del self._bundles[tenant_id][bundle_id]
            return True
        return False

    def get_bundle(
        self,
        bundle_id: str,
        tenant_id: str,
        include_presets: bool = True,
    ) -> Optional[ToolBundle]:
        """Get a bundle by ID."""
        # Check tenant bundles
        if tenant_id in self._bundles and bundle_id in self._bundles[tenant_id]:
            return self._bundles[tenant_id][bundle_id]

        # Check preset bundles
        if include_presets and bundle_id in self._preset_bundles:
            return self._preset_bundles[bundle_id]

        return None

    def list_bundles(
        self,
        tenant_id: str,
        category: Optional[ToolCategory] = None,
        include_presets: bool = True,
    ) -> List[ToolBundle]:
        """List all available bundles for a tenant."""
        bundles = []

        # Add tenant bundles
        if tenant_id in self._bundles:
            bundles.extend(self._bundles[tenant_id].values())

        # Add preset bundles
        if include_presets:
            bundles.extend(self._preset_bundles.values())

        # Filter by category
        if category:
            bundles = [b for b in bundles if b.category == category]

        return bundles

    def get_bundles_for_agent(
        self,
        agent_type: str,
        capabilities: Set[str],
        tenant_id: str,
    ) -> List[ToolBundle]:
        """Get bundles available to an agent based on its type and capabilities."""
        all_bundles = self.list_bundles(tenant_id)

        available = []
        for bundle in all_bundles:
            # Check agent type
            if agent_type not in bundle.allowed_agent_types:
                continue

            # Check capabilities
            if bundle.required_capabilities and not bundle.required_capabilities.issubset(capabilities):
                continue

            available.append(bundle)

        return available

    def get_tool(
        self,
        tool_id: str,
        tenant_id: str,
    ) -> Optional[Tool]:
        """Get a tool by ID across all bundles."""
        for bundle in self.list_bundles(tenant_id):
            tool = bundle.get_tool(tool_id)
            if tool:
                return tool
        return None

    async def invoke_tool(
        self,
        tool_id: str,
        tenant_id: str,
        agent_id: str,
        **kwargs,
    ) -> Any:
        """Invoke a tool."""
        tool = self.get_tool(tool_id, tenant_id)
        if not tool:
            raise ValueError(f"Tool not found: {tool_id}")

        if tool.deprecated:
            logger.warning(
                f"Invoking deprecated tool {tool_id}. "
                f"Use {tool.replacement_tool_id} instead."
            )

        # Track invocation
        self._track_invocation(tool_id)

        # Invoke the tool
        try:
            result = await tool.invoke(**kwargs)
            return result
        except Exception as e:
            logger.error(f"Tool invocation failed: {tool_id} - {e}")
            raise

    def _track_invocation(self, tool_id: str) -> None:
        """Track tool invocation for rate limiting."""
        hour = datetime.utcnow().strftime("%Y-%m-%d-%H")

        if tool_id not in self._invocation_counts:
            self._invocation_counts[tool_id] = {}

        counts = self._invocation_counts[tool_id]
        counts[hour] = counts.get(hour, 0) + 1

        # Clean old entries
        if len(counts) > 24:
            oldest = sorted(counts.keys())[0]
            del counts[oldest]

    def get_tool_stats(self, tool_id: str) -> Dict[str, Any]:
        """Get invocation stats for a tool."""
        counts = self._invocation_counts.get(tool_id, {})
        total = sum(counts.values())
        current_hour = datetime.utcnow().strftime("%Y-%m-%d-%H")

        return {
            "tool_id": tool_id,
            "total_invocations": total,
            "current_hour": counts.get(current_hour, 0),
            "hourly_breakdown": counts,
        }


# Global instance
_bundle_registry: Optional[BundleRegistry] = None


def get_bundle_registry() -> BundleRegistry:
    """Get the global bundle registry."""
    global _bundle_registry
    if _bundle_registry is None:
        _bundle_registry = BundleRegistry()
        # Register preset bundles
        from app.agentic.bundles.presets import get_preset_bundles
        for bundle in get_preset_bundles():
            _bundle_registry.register_bundle(bundle)
    return _bundle_registry
