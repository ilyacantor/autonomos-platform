"""
Cross-System Lineage Tracer

Traces data lineage across multiple systems and sources:
- Combines lineage from DCL, AOD, and external systems
- Builds unified lineage graphs
- Identifies transformation chains
- Detects impact paths

Part of "The Moat" - deep data understanding capabilities.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


class NodeType(str, Enum):
    """Types of lineage nodes."""
    TABLE = "table"
    VIEW = "view"
    API = "api"
    FILE = "file"
    DASHBOARD = "dashboard"
    REPORT = "report"
    TRANSFORMATION = "transformation"
    EXTERNAL = "external"


class EdgeType(str, Enum):
    """Types of lineage edges."""
    DIRECT = "direct"  # Direct data flow
    TRANSFORM = "transform"  # Data transformation
    AGGREGATE = "aggregate"  # Aggregation
    JOIN = "join"  # Join operation
    FILTER = "filter"  # Filter operation
    API_CALL = "api_call"  # API call
    MANUAL = "manual"  # Manual data entry
    UNKNOWN = "unknown"


@dataclass
class LineageNode:
    """A node in the lineage graph."""
    id: str
    name: str
    node_type: NodeType
    source_system: str
    description: Optional[str] = None
    owner: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.node_type.value,
            "source_system": self.source_system,
            "description": self.description,
            "owner": self.owner,
            "metadata": self.metadata
        }


@dataclass
class LineageEdge:
    """An edge in the lineage graph."""
    source_id: str
    target_id: str
    edge_type: EdgeType
    transformation: Optional[str] = None
    fields_mapped: dict = field(default_factory=dict)  # source_field -> target_field
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "type": self.edge_type.value,
            "transformation": self.transformation,
            "fields_mapped": self.fields_mapped,
            "metadata": self.metadata
        }


@dataclass
class LineageGraph:
    """Complete lineage graph."""
    root_id: str
    nodes: dict[str, LineageNode] = field(default_factory=dict)
    edges: list[LineageEdge] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.utcnow)

    def add_node(self, node: LineageNode) -> None:
        """Add a node to the graph."""
        self.nodes[node.id] = node

    def add_edge(self, edge: LineageEdge) -> None:
        """Add an edge to the graph."""
        self.edges.append(edge)

    def get_upstream(self, node_id: str, depth: int = 1) -> list[LineageNode]:
        """Get upstream nodes (sources) for a given node."""
        if depth <= 0:
            return []

        upstream = []
        for edge in self.edges:
            if edge.target_id == node_id:
                if edge.source_id in self.nodes:
                    upstream.append(self.nodes[edge.source_id])
                    if depth > 1:
                        upstream.extend(self.get_upstream(edge.source_id, depth - 1))

        return upstream

    def get_downstream(self, node_id: str, depth: int = 1) -> list[LineageNode]:
        """Get downstream nodes (consumers) for a given node."""
        if depth <= 0:
            return []

        downstream = []
        for edge in self.edges:
            if edge.source_id == node_id:
                if edge.target_id in self.nodes:
                    downstream.append(self.nodes[edge.target_id])
                    if depth > 1:
                        downstream.extend(self.get_downstream(edge.target_id, depth - 1))

        return downstream

    def get_impact_path(self, node_id: str) -> list[list[LineageNode]]:
        """Get all impact paths from a node to end consumers."""
        paths = []
        self._find_paths(node_id, [], paths)
        return paths

    def _find_paths(
        self,
        node_id: str,
        current_path: list[LineageNode],
        all_paths: list[list[LineageNode]]
    ) -> None:
        """Recursively find all paths to leaf nodes."""
        if node_id not in self.nodes:
            return

        node = self.nodes[node_id]
        current_path = current_path + [node]

        downstream_edges = [e for e in self.edges if e.source_id == node_id]

        if not downstream_edges:
            # Leaf node - record the path
            all_paths.append(current_path)
        else:
            for edge in downstream_edges:
                self._find_paths(edge.target_id, current_path, all_paths)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "root_id": self.root_id,
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "edges": [e.to_dict() for e in self.edges],
            "generated_at": self.generated_at.isoformat(),
            "statistics": {
                "total_nodes": len(self.nodes),
                "total_edges": len(self.edges),
                "upstream_count": len(self.get_upstream(self.root_id, depth=10)),
                "downstream_count": len(self.get_downstream(self.root_id, depth=10))
            }
        }


class CrossSystemLineageTracer:
    """
    Traces data lineage across multiple systems.

    Combines lineage information from:
    - DCL (database-level lineage)
    - AOD (asset-level lineage)
    - External systems (ETL tools, BI platforms)
    """

    def __init__(
        self,
        aod_server: Optional[Any] = None,
        dcl_server: Optional[Any] = None,
        aam_server: Optional[Any] = None
    ):
        """
        Initialize the lineage tracer.

        Args:
            aod_server: AOD MCP server for asset lineage
            dcl_server: DCL MCP server for database lineage
            aam_server: AAM MCP server for connection info
        """
        self.aod_server = aod_server
        self.dcl_server = dcl_server
        self.aam_server = aam_server

        # Cache for lineage graphs
        self._cache: dict[str, LineageGraph] = {}

    async def trace_lineage(
        self,
        asset_id: str,
        tenant_id: UUID,
        direction: str = "both",
        depth: int = 3,
        include_field_level: bool = False
    ) -> LineageGraph:
        """
        Trace lineage for an asset across all connected systems.

        Args:
            asset_id: Asset to trace lineage for
            tenant_id: Tenant ID for access control
            direction: "upstream", "downstream", or "both"
            depth: How many levels to trace (1-10)
            include_field_level: Include field-level lineage

        Returns:
            Complete LineageGraph
        """
        cache_key = f"{tenant_id}:{asset_id}:{direction}:{depth}"

        # Check cache
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            age = (datetime.utcnow() - cached.generated_at).total_seconds()
            if age < 300:  # 5 minute cache
                return cached

        logger.info(f"Tracing lineage for {asset_id}, direction={direction}, depth={depth}")

        # Create the graph
        graph = LineageGraph(root_id=asset_id)

        # Get root node details
        root_node = await self._get_node_details(asset_id, tenant_id)
        if root_node:
            graph.add_node(root_node)

        # Trace in requested directions
        depth = min(depth, 10)  # Cap at 10

        if direction in ["upstream", "both"]:
            await self._trace_upstream(
                graph, asset_id, tenant_id, depth, include_field_level
            )

        if direction in ["downstream", "both"]:
            await self._trace_downstream(
                graph, asset_id, tenant_id, depth, include_field_level
            )

        # Cache result
        self._cache[cache_key] = graph

        return graph

    async def _get_node_details(
        self,
        asset_id: str,
        tenant_id: UUID
    ) -> Optional[LineageNode]:
        """Get details for a single node."""
        if self.aod_server:
            try:
                from app.agentic.mcp_servers.aod_server import AODContext
                context = AODContext(tenant_id=tenant_id)

                result = await self.aod_server.execute_tool(
                    "aod_get_asset_details",
                    {"asset_id": asset_id},
                    context
                )

                if result.get("success"):
                    asset = result.get("asset", {})
                    node_type_str = asset.get("type", "table")
                    try:
                        node_type = NodeType(node_type_str)
                    except ValueError:
                        node_type = NodeType.TABLE

                    return LineageNode(
                        id=asset_id,
                        name=asset.get("name", asset_id),
                        node_type=node_type,
                        source_system=asset.get("source_system", "unknown"),
                        description=asset.get("description"),
                        owner=asset.get("owner"),
                        metadata=asset.get("metadata", {})
                    )
            except Exception as e:
                logger.warning(f"Error getting node details: {e}")

        # Return basic node if no details available
        return LineageNode(
            id=asset_id,
            name=asset_id,
            node_type=NodeType.TABLE,
            source_system="unknown"
        )

    async def _trace_upstream(
        self,
        graph: LineageGraph,
        node_id: str,
        tenant_id: UUID,
        depth: int,
        include_field_level: bool,
        visited: Optional[set] = None
    ) -> None:
        """Trace upstream lineage."""
        if depth <= 0:
            return

        if visited is None:
            visited = set()

        if node_id in visited:
            return
        visited.add(node_id)

        # Get lineage from AOD
        upstream_nodes = []
        if self.aod_server:
            try:
                from app.agentic.mcp_servers.aod_server import AODContext
                context = AODContext(tenant_id=tenant_id)

                result = await self.aod_server.execute_tool(
                    "aod_get_lineage",
                    {"asset_id": node_id, "direction": "upstream", "depth": 1},
                    context
                )

                if result.get("success"):
                    lineage = result.get("lineage", {})
                    upstream_nodes = lineage.get("upstream", [])
            except Exception as e:
                logger.warning(f"Error tracing upstream: {e}")

        # Also check DCL for database-level lineage
        if self.dcl_server:
            try:
                from app.agentic.mcp_servers.dcl_server import DCLContext
                dcl_context = DCLContext(tenant_id=tenant_id)

                result = await self.dcl_server.execute_tool(
                    "dcl_get_lineage",
                    {"table_name": node_id, "direction": "upstream"},
                    dcl_context
                )

                if result.get("success"):
                    dcl_lineage = result.get("lineage", [])
                    for item in dcl_lineage:
                        # Avoid duplicates
                        if not any(n.get("id") == item.get("id") for n in upstream_nodes):
                            upstream_nodes.append(item)
            except Exception as e:
                logger.warning(f"Error getting DCL lineage: {e}")

        # Process upstream nodes
        for upstream in upstream_nodes:
            upstream_id = upstream.get("id", upstream.get("name", "unknown"))

            # Get or create node
            if upstream_id not in graph.nodes:
                node = await self._get_node_details(upstream_id, tenant_id)
                if node:
                    # Update with info from lineage
                    node.name = upstream.get("name", node.name)
                    if upstream.get("type"):
                        try:
                            node.node_type = NodeType(upstream.get("type"))
                        except ValueError:
                            pass
                    if upstream.get("source_system"):
                        node.source_system = upstream.get("source_system")
                    graph.add_node(node)

            # Create edge
            edge_type = EdgeType.DIRECT
            transformation = upstream.get("transformation")
            if transformation:
                if "join" in transformation.lower():
                    edge_type = EdgeType.JOIN
                elif "aggregate" in transformation.lower():
                    edge_type = EdgeType.AGGREGATE
                elif "transform" in transformation.lower():
                    edge_type = EdgeType.TRANSFORM
                elif "extract" in transformation.lower():
                    edge_type = EdgeType.DIRECT
                else:
                    edge_type = EdgeType.TRANSFORM

            # Build field mappings if requested
            fields_mapped = {}
            if include_field_level and upstream.get("fields_used"):
                for field in upstream.get("fields_used", []):
                    fields_mapped[field] = field  # Simple 1:1 mapping

            edge = LineageEdge(
                source_id=upstream_id,
                target_id=node_id,
                edge_type=edge_type,
                transformation=transformation,
                fields_mapped=fields_mapped
            )
            graph.add_edge(edge)

            # Recurse
            if depth > 1:
                await self._trace_upstream(
                    graph, upstream_id, tenant_id, depth - 1,
                    include_field_level, visited
                )

    async def _trace_downstream(
        self,
        graph: LineageGraph,
        node_id: str,
        tenant_id: UUID,
        depth: int,
        include_field_level: bool,
        visited: Optional[set] = None
    ) -> None:
        """Trace downstream lineage."""
        if depth <= 0:
            return

        if visited is None:
            visited = set()

        if node_id in visited:
            return
        visited.add(node_id)

        # Get lineage from AOD
        downstream_nodes = []
        if self.aod_server:
            try:
                from app.agentic.mcp_servers.aod_server import AODContext
                context = AODContext(tenant_id=tenant_id)

                result = await self.aod_server.execute_tool(
                    "aod_get_lineage",
                    {"asset_id": node_id, "direction": "downstream", "depth": 1},
                    context
                )

                if result.get("success"):
                    lineage = result.get("lineage", {})
                    downstream_nodes = lineage.get("downstream", [])
            except Exception as e:
                logger.warning(f"Error tracing downstream: {e}")

        # Also check DCL
        if self.dcl_server:
            try:
                from app.agentic.mcp_servers.dcl_server import DCLContext
                dcl_context = DCLContext(tenant_id=tenant_id)

                result = await self.dcl_server.execute_tool(
                    "dcl_get_lineage",
                    {"table_name": node_id, "direction": "downstream"},
                    dcl_context
                )

                if result.get("success"):
                    dcl_lineage = result.get("lineage", [])
                    for item in dcl_lineage:
                        if not any(n.get("id") == item.get("id") for n in downstream_nodes):
                            downstream_nodes.append(item)
            except Exception as e:
                logger.warning(f"Error getting DCL downstream: {e}")

        # Process downstream nodes
        for downstream in downstream_nodes:
            downstream_id = downstream.get("id", downstream.get("name", "unknown"))

            # Get or create node
            if downstream_id not in graph.nodes:
                node = await self._get_node_details(downstream_id, tenant_id)
                if node:
                    node.name = downstream.get("name", node.name)
                    if downstream.get("type"):
                        try:
                            node.node_type = NodeType(downstream.get("type"))
                        except ValueError:
                            pass
                    if downstream.get("source_system"):
                        node.source_system = downstream.get("source_system")
                    graph.add_node(node)

            # Create edge
            edge_type = EdgeType.DIRECT
            transformation = downstream.get("transformation")
            if transformation:
                if "join" in transformation.lower():
                    edge_type = EdgeType.JOIN
                elif "aggregate" in transformation.lower():
                    edge_type = EdgeType.AGGREGATE
                elif "transform" in transformation.lower():
                    edge_type = EdgeType.TRANSFORM
                else:
                    edge_type = EdgeType.TRANSFORM

            edge = LineageEdge(
                source_id=node_id,
                target_id=downstream_id,
                edge_type=edge_type,
                transformation=transformation
            )
            graph.add_edge(edge)

            # Recurse
            if depth > 1:
                await self._trace_downstream(
                    graph, downstream_id, tenant_id, depth - 1,
                    include_field_level, visited
                )

    async def analyze_impact(
        self,
        asset_id: str,
        tenant_id: UUID,
        change_type: str = "schema_change"
    ) -> dict:
        """
        Analyze impact of a change to an asset.

        Args:
            asset_id: Asset being changed
            tenant_id: Tenant ID
            change_type: Type of change (schema_change, deprecation, etc.)

        Returns:
            Impact analysis including affected assets and severity
        """
        # Get downstream lineage
        graph = await self.trace_lineage(
            asset_id=asset_id,
            tenant_id=tenant_id,
            direction="downstream",
            depth=5
        )

        # Get all impact paths
        impact_paths = graph.get_impact_path(asset_id)

        # Categorize affected assets
        affected_assets = []
        for node_id, node in graph.nodes.items():
            if node_id == asset_id:
                continue

            # Calculate distance from root
            for path in impact_paths:
                if node in path:
                    distance = path.index(node)
                    affected_assets.append({
                        "id": node.id,
                        "name": node.name,
                        "type": node.node_type.value,
                        "source_system": node.source_system,
                        "owner": node.owner,
                        "distance": distance,
                        "severity": "high" if distance <= 1 else ("medium" if distance <= 3 else "low")
                    })
                    break

        # Sort by distance
        affected_assets.sort(key=lambda x: x["distance"])

        # Identify critical paths (to dashboards, APIs)
        critical_assets = [
            a for a in affected_assets
            if a["type"] in ["dashboard", "api", "report"]
        ]

        return {
            "source_asset": asset_id,
            "change_type": change_type,
            "total_affected": len(affected_assets),
            "affected_assets": affected_assets,
            "critical_assets": critical_assets,
            "impact_severity": (
                "critical" if critical_assets else
                ("high" if len(affected_assets) > 10 else
                 ("medium" if len(affected_assets) > 3 else "low"))
            ),
            "recommendations": self._generate_recommendations(
                change_type, affected_assets, critical_assets
            )
        }

    def _generate_recommendations(
        self,
        change_type: str,
        affected_assets: list,
        critical_assets: list
    ) -> list[str]:
        """Generate recommendations based on impact analysis."""
        recommendations = []

        if critical_assets:
            recommendations.append(
                f"Notify owners of {len(critical_assets)} critical downstream assets before making changes"
            )

        if change_type == "schema_change":
            recommendations.append(
                "Consider implementing backward-compatible changes or a migration path"
            )
            if len(affected_assets) > 5:
                recommendations.append(
                    "Schedule changes during low-usage period due to widespread impact"
                )

        if change_type == "deprecation":
            recommendations.append(
                "Create migration guide for downstream consumers"
            )
            recommendations.append(
                "Set deprecation timeline of at least 30 days for affected teams"
            )

        if not recommendations:
            recommendations.append("Change appears to have minimal impact")

        return recommendations

    def clear_cache(self, tenant_id: Optional[UUID] = None) -> int:
        """Clear cached lineage graphs."""
        if tenant_id is None:
            count = len(self._cache)
            self._cache.clear()
            return count

        prefix = f"{tenant_id}:"
        keys_to_remove = [k for k in self._cache if k.startswith(prefix)]
        for key in keys_to_remove:
            del self._cache[key]
        return len(keys_to_remove)


# Global instance
_lineage_tracer: Optional[CrossSystemLineageTracer] = None


def get_lineage_tracer() -> CrossSystemLineageTracer:
    """Get the global lineage tracer instance."""
    global _lineage_tracer
    if _lineage_tracer is None:
        _lineage_tracer = CrossSystemLineageTracer()
    return _lineage_tracer
