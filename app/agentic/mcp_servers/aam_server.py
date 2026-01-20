"""
AAM (Asset Automation Manager) MCP Server

Exposes AAM functionality as MCP tools for agent access:
- Connection management and monitoring
- Sync status and history
- Field mappings
- Schema drift detection and repair
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


# =============================================================================
# Tool Definitions (MCP Format)
# =============================================================================

AAM_TOOLS = [
    {
        "name": "aam_list_connections",
        "description": "List all configured data connections (sources and destinations). Shows connection names, types, and current status.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "status_filter": {
                    "type": "string",
                    "enum": ["all", "active", "paused", "error"],
                    "description": "Filter connections by status",
                    "default": "all"
                },
                "type_filter": {
                    "type": "string",
                    "description": "Filter by connection type (e.g., 'salesforce', 'postgresql')"
                }
            },
            "required": []
        }
    },
    {
        "name": "aam_get_connection_status",
        "description": "Get detailed status for a specific connection including last sync time, error details, and health metrics.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "connection_name": {
                    "type": "string",
                    "description": "Name of the connection to check"
                }
            },
            "required": ["connection_name"]
        }
    },
    {
        "name": "aam_get_sync_history",
        "description": "Get the sync history for a connection - when syncs occurred, their duration, and records processed.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "connection_name": {
                    "type": "string",
                    "description": "Name of the connection"
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of recent syncs to return",
                    "default": 10
                }
            },
            "required": ["connection_name"]
        }
    },
    {
        "name": "aam_get_field_mappings",
        "description": "Get the field mappings for a connection - which source fields map to which destination columns.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "connection_name": {
                    "type": "string",
                    "description": "Name of the connection"
                },
                "object_name": {
                    "type": "string",
                    "description": "Specific object/table to get mappings for (optional)"
                }
            },
            "required": ["connection_name"]
        }
    },
    {
        "name": "aam_get_sync_metrics",
        "description": "Get aggregated sync metrics including data volume, API usage, and error rates.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "connection_name": {
                    "type": "string",
                    "description": "Specific connection (optional, omit for all connections)"
                },
                "time_range": {
                    "type": "string",
                    "enum": ["24h", "7d", "30d"],
                    "description": "Time range for metrics",
                    "default": "7d"
                }
            },
            "required": []
        }
    },
    {
        "name": "aam_detect_drift",
        "description": "Detect schema drift - changes in source schema that may affect data sync. Returns list of detected drift issues.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "connection_name": {
                    "type": "string",
                    "description": "Specific connection to check (optional, omit to check all)"
                }
            },
            "required": []
        }
    },
    {
        "name": "aam_update_connection",
        "description": "Update connection settings such as pause/resume sync, update schedule, or modify settings. REQUIRES APPROVAL for state changes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "connection_name": {
                    "type": "string",
                    "description": "Name of the connection to update"
                },
                "action": {
                    "type": "string",
                    "enum": ["pause", "resume", "update_schedule", "trigger_sync"],
                    "description": "Action to perform"
                },
                "schedule": {
                    "type": "string",
                    "description": "New sync schedule (cron format), required for update_schedule action"
                }
            },
            "required": ["connection_name", "action"]
        }
    },
    {
        "name": "aam_create_connection",
        "description": "Create a new data connection. REQUIRES APPROVAL. Validates connection parameters before creation.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Unique name for the connection"
                },
                "type": {
                    "type": "string",
                    "enum": ["salesforce", "hubspot", "postgresql", "mysql", "snowflake", "bigquery"],
                    "description": "Connection type"
                },
                "config": {
                    "type": "object",
                    "description": "Connection configuration (credentials, endpoints, etc.)"
                }
            },
            "required": ["name", "type", "config"]
        }
    },
    {
        "name": "aam_repair_drift",
        "description": "Repair detected schema drift by updating mappings to match new source schema. REQUIRES APPROVAL.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "connection_name": {
                    "type": "string",
                    "description": "Connection with drift to repair"
                },
                "drift_id": {
                    "type": "string",
                    "description": "Specific drift issue ID to repair (from detect_drift)"
                },
                "strategy": {
                    "type": "string",
                    "enum": ["auto", "add_columns", "ignore", "manual"],
                    "description": "Repair strategy",
                    "default": "auto"
                }
            },
            "required": ["connection_name"]
        }
    }
]

# Tools that require approval
AAM_APPROVAL_REQUIRED = [
    "aam_update_connection",
    "aam_create_connection",
    "aam_repair_drift"
]


@dataclass
class AAMContext:
    """Context for AAM operations."""
    tenant_id: UUID
    user_id: Optional[UUID] = None


class AAMMCPServer:
    """
    MCP Server implementation for AAM.

    Provides connection management with:
    - Read-only monitoring and discovery
    - Write operations with approval requirements
    - Schema drift detection and repair
    """

    def __init__(self, aam_client: Optional[Any] = None):
        """
        Initialize the AAM MCP server.

        Args:
            aam_client: Optional AAM client for actual operations
        """
        self.aam_client = aam_client
        self._tools = {tool["name"]: tool for tool in AAM_TOOLS}

    def get_tools(self) -> list[dict]:
        """Return the list of available tools."""
        return AAM_TOOLS

    def requires_approval(self, tool_name: str) -> bool:
        """Check if a tool requires human approval."""
        return tool_name in AAM_APPROVAL_REQUIRED

    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict,
        context: AAMContext
    ) -> dict:
        """
        Execute an AAM tool.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments
            context: Execution context with tenant info

        Returns:
            Tool execution result
        """
        if tool_name not in self._tools:
            return {
                "error": f"Unknown tool: {tool_name}",
                "success": False
            }

        logger.info(f"Executing AAM tool: {tool_name} for tenant {context.tenant_id}")

        try:
            if tool_name == "aam_list_connections":
                return await self._list_connections(arguments, context)
            elif tool_name == "aam_get_connection_status":
                return await self._get_connection_status(arguments, context)
            elif tool_name == "aam_get_sync_history":
                return await self._get_sync_history(arguments, context)
            elif tool_name == "aam_get_field_mappings":
                return await self._get_field_mappings(arguments, context)
            elif tool_name == "aam_get_sync_metrics":
                return await self._get_sync_metrics(arguments, context)
            elif tool_name == "aam_detect_drift":
                return await self._detect_drift(arguments, context)
            elif tool_name == "aam_update_connection":
                return await self._update_connection(arguments, context)
            elif tool_name == "aam_create_connection":
                return await self._create_connection(arguments, context)
            elif tool_name == "aam_repair_drift":
                return await self._repair_drift(arguments, context)
            else:
                return {"error": f"Tool not implemented: {tool_name}", "success": False}

        except Exception as e:
            logger.error(f"AAM tool execution error: {e}")
            return {
                "error": str(e),
                "success": False
            }

    async def _list_connections(self, args: dict, context: AAMContext) -> dict:
        """List configured connections."""
        status_filter = args.get("status_filter", "all")
        type_filter = args.get("type_filter")

        if self.aam_client:
            connections = await self.aam_client.list_connections(
                tenant_id=context.tenant_id
            )
        else:
            # Mock data
            connections = [
                {
                    "name": "salesforce-production",
                    "type": "salesforce",
                    "status": "active",
                    "last_sync": "2026-01-20T08:00:00Z",
                    "objects_synced": ["Account", "Contact", "Opportunity", "Lead"]
                },
                {
                    "name": "hubspot-marketing",
                    "type": "hubspot",
                    "status": "active",
                    "last_sync": "2026-01-20T07:30:00Z",
                    "objects_synced": ["Contact", "Company", "Deal"]
                },
                {
                    "name": "postgres-analytics",
                    "type": "postgresql",
                    "status": "active",
                    "last_sync": "2026-01-20T09:00:00Z",
                    "objects_synced": ["orders", "products", "customers"]
                },
                {
                    "name": "legacy-mysql",
                    "type": "mysql",
                    "status": "paused",
                    "last_sync": "2026-01-15T12:00:00Z",
                    "objects_synced": ["transactions"]
                }
            ]

        # Apply filters
        if status_filter != "all":
            connections = [c for c in connections if c["status"] == status_filter]
        if type_filter:
            connections = [c for c in connections if c["type"] == type_filter]

        return {
            "success": True,
            "connections": connections,
            "count": len(connections)
        }

    async def _get_connection_status(self, args: dict, context: AAMContext) -> dict:
        """Get detailed connection status."""
        connection_name = args.get("connection_name")

        if not connection_name:
            return {"error": "connection_name is required", "success": False}

        if self.aam_client:
            status = await self.aam_client.get_connection_status(
                tenant_id=context.tenant_id,
                connection_name=connection_name
            )
        else:
            # Mock status
            statuses = {
                "salesforce-production": {
                    "name": "salesforce-production",
                    "type": "salesforce",
                    "status": "active",
                    "health": "healthy",
                    "last_sync": {
                        "timestamp": "2026-01-20T08:00:00Z",
                        "duration_seconds": 145,
                        "records_synced": 1250,
                        "status": "success"
                    },
                    "next_sync": "2026-01-20T09:00:00Z",
                    "sync_schedule": "0 * * * *",
                    "api_usage": {
                        "calls_today": 1520,
                        "limit": 100000,
                        "percentage_used": 1.52
                    },
                    "errors_24h": 0
                },
                "hubspot-marketing": {
                    "name": "hubspot-marketing",
                    "type": "hubspot",
                    "status": "active",
                    "health": "healthy",
                    "last_sync": {
                        "timestamp": "2026-01-20T07:30:00Z",
                        "duration_seconds": 89,
                        "records_synced": 580,
                        "status": "success"
                    },
                    "next_sync": "2026-01-20T08:30:00Z",
                    "sync_schedule": "30 * * * *",
                    "api_usage": {
                        "calls_today": 890,
                        "limit": 500000,
                        "percentage_used": 0.18
                    },
                    "errors_24h": 0
                }
            }

            status = statuses.get(connection_name)
            if not status:
                return {"error": f"Connection not found: {connection_name}", "success": False}

        return {
            "success": True,
            "status": status
        }

    async def _get_sync_history(self, args: dict, context: AAMContext) -> dict:
        """Get sync history for a connection."""
        connection_name = args.get("connection_name")
        limit = args.get("limit", 10)

        if not connection_name:
            return {"error": "connection_name is required", "success": False}

        if self.aam_client:
            history = await self.aam_client.get_sync_history(
                tenant_id=context.tenant_id,
                connection_name=connection_name,
                limit=limit
            )
        else:
            # Mock history
            history = [
                {
                    "timestamp": "2026-01-20T08:00:00Z",
                    "status": "success",
                    "duration_seconds": 145,
                    "records_synced": 1250,
                    "records_updated": 89,
                    "records_created": 12
                },
                {
                    "timestamp": "2026-01-20T07:00:00Z",
                    "status": "success",
                    "duration_seconds": 132,
                    "records_synced": 1180,
                    "records_updated": 45,
                    "records_created": 8
                },
                {
                    "timestamp": "2026-01-20T06:00:00Z",
                    "status": "success",
                    "duration_seconds": 156,
                    "records_synced": 1320,
                    "records_updated": 112,
                    "records_created": 15
                }
            ][:limit]

        return {
            "success": True,
            "connection_name": connection_name,
            "history": history,
            "count": len(history)
        }

    async def _get_field_mappings(self, args: dict, context: AAMContext) -> dict:
        """Get field mappings for a connection."""
        connection_name = args.get("connection_name")
        object_name = args.get("object_name")

        if not connection_name:
            return {"error": "connection_name is required", "success": False}

        if self.aam_client:
            mappings = await self.aam_client.get_field_mappings(
                tenant_id=context.tenant_id,
                connection_name=connection_name,
                object_name=object_name
            )
        else:
            # Mock mappings
            mappings = {
                "Account": [
                    {"source_field": "Id", "destination_field": "sf_account_id", "type": "string"},
                    {"source_field": "Name", "destination_field": "account_name", "type": "string"},
                    {"source_field": "BillingCity", "destination_field": "city", "type": "string"},
                    {"source_field": "AnnualRevenue", "destination_field": "annual_revenue", "type": "decimal"},
                    {"source_field": "CreatedDate", "destination_field": "created_at", "type": "timestamp"}
                ],
                "Contact": [
                    {"source_field": "Id", "destination_field": "sf_contact_id", "type": "string"},
                    {"source_field": "Email", "destination_field": "email", "type": "string"},
                    {"source_field": "FirstName", "destination_field": "first_name", "type": "string"},
                    {"source_field": "LastName", "destination_field": "last_name", "type": "string"},
                    {"source_field": "AccountId", "destination_field": "sf_account_id", "type": "string"}
                ]
            }

            if object_name:
                mappings = {object_name: mappings.get(object_name, [])}

        return {
            "success": True,
            "connection_name": connection_name,
            "mappings": mappings
        }

    async def _get_sync_metrics(self, args: dict, context: AAMContext) -> dict:
        """Get aggregated sync metrics."""
        connection_name = args.get("connection_name")
        time_range = args.get("time_range", "7d")

        if self.aam_client:
            metrics = await self.aam_client.get_sync_metrics(
                tenant_id=context.tenant_id,
                connection_name=connection_name,
                time_range=time_range
            )
        else:
            # Mock metrics
            if connection_name:
                metrics = {
                    "connection": connection_name,
                    "time_range": time_range,
                    "total_syncs": 168,
                    "successful_syncs": 167,
                    "failed_syncs": 1,
                    "total_records_synced": 185420,
                    "total_api_calls": 12500,
                    "average_sync_duration_seconds": 142,
                    "data_volume_mb": 450
                }
            else:
                metrics = {
                    "time_range": time_range,
                    "connections": [
                        {"name": "salesforce-production", "records_synced": 185420, "api_calls": 12500},
                        {"name": "hubspot-marketing", "records_synced": 42890, "api_calls": 8200},
                        {"name": "postgres-analytics", "records_synced": 320000, "api_calls": 1500}
                    ],
                    "total_records_synced": 548310,
                    "total_api_calls": 22200,
                    "total_data_volume_mb": 1250
                }

        return {
            "success": True,
            "metrics": metrics
        }

    async def _detect_drift(self, args: dict, context: AAMContext) -> dict:
        """Detect schema drift."""
        connection_name = args.get("connection_name")

        if self.aam_client:
            drift = await self.aam_client.detect_drift(
                tenant_id=context.tenant_id,
                connection_name=connection_name
            )
        else:
            # Mock drift detection
            drift_issues = []

            if not connection_name or connection_name == "hubspot-marketing":
                drift_issues.append({
                    "id": "drift-001",
                    "connection": "hubspot-marketing",
                    "object": "Contact",
                    "type": "new_field",
                    "details": {
                        "field_name": "custom_score",
                        "field_type": "number",
                        "detected_at": "2026-01-19T15:30:00Z"
                    },
                    "severity": "low",
                    "suggested_action": "Add new column to destination"
                })

        return {
            "success": True,
            "drift_detected": len(drift_issues) > 0,
            "issues": drift_issues,
            "count": len(drift_issues)
        }

    async def _update_connection(self, args: dict, context: AAMContext) -> dict:
        """Update connection settings (requires approval)."""
        connection_name = args.get("connection_name")
        action = args.get("action")
        schedule = args.get("schedule")

        if not connection_name:
            return {"error": "connection_name is required", "success": False}
        if not action:
            return {"error": "action is required", "success": False}

        if action == "update_schedule" and not schedule:
            return {"error": "schedule is required for update_schedule action", "success": False}

        if self.aam_client:
            result = await self.aam_client.update_connection(
                tenant_id=context.tenant_id,
                connection_name=connection_name,
                action=action,
                schedule=schedule
            )
        else:
            # Mock update
            result = {
                "connection": connection_name,
                "action": action,
                "status": "completed",
                "message": f"Connection {connection_name} {action}d successfully"
            }

        return {
            "success": True,
            "result": result
        }

    async def _create_connection(self, args: dict, context: AAMContext) -> dict:
        """Create a new connection (requires approval)."""
        name = args.get("name")
        conn_type = args.get("type")
        config = args.get("config", {})

        if not name:
            return {"error": "name is required", "success": False}
        if not conn_type:
            return {"error": "type is required", "success": False}

        if self.aam_client:
            result = await self.aam_client.create_connection(
                tenant_id=context.tenant_id,
                name=name,
                type=conn_type,
                config=config
            )
        else:
            # Mock creation
            result = {
                "name": name,
                "type": conn_type,
                "status": "created",
                "message": f"Connection {name} created successfully. Please configure credentials."
            }

        return {
            "success": True,
            "result": result
        }

    async def _repair_drift(self, args: dict, context: AAMContext) -> dict:
        """Repair schema drift (requires approval)."""
        connection_name = args.get("connection_name")
        drift_id = args.get("drift_id")
        strategy = args.get("strategy", "auto")

        if not connection_name:
            return {"error": "connection_name is required", "success": False}

        if self.aam_client:
            result = await self.aam_client.repair_drift(
                tenant_id=context.tenant_id,
                connection_name=connection_name,
                drift_id=drift_id,
                strategy=strategy
            )
        else:
            # Mock repair
            result = {
                "connection": connection_name,
                "drift_id": drift_id,
                "strategy": strategy,
                "status": "repaired",
                "actions_taken": [
                    "Added column 'custom_score' to destination table",
                    "Updated field mappings",
                    "Triggered backfill sync"
                ]
            }

        return {
            "success": True,
            "result": result
        }
