"""
DCL (Data Connectivity Layer) MCP Server

Exposes DCL functionality as MCP tools for agent access:
- Table listing and metadata
- Schema inspection
- Query execution with guardrails
- Data lineage tracing

Implements ARB Condition 2: Metadata RAG instead of raw schema dumps.
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

DCL_TOOLS = [
    {
        "name": "dcl_list_tables",
        "description": "List available tables/datasets in the data lake. Returns table names, descriptions, and basic metadata. Use this to discover what data is available before querying.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "filter": {
                    "type": "string",
                    "description": "Optional filter pattern (e.g., 'sales*', '*customer*')"
                },
                "include_metadata": {
                    "type": "boolean",
                    "description": "Include row counts and last updated timestamps",
                    "default": True
                }
            },
            "required": []
        }
    },
    {
        "name": "dcl_get_schema",
        "description": "Get the schema (columns, types, descriptions) for a specific table. Use this to understand table structure before writing queries.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "table_name": {
                    "type": "string",
                    "description": "Name of the table to get schema for"
                },
                "include_stats": {
                    "type": "boolean",
                    "description": "Include column statistics (null counts, distinct values)",
                    "default": False
                }
            },
            "required": ["table_name"]
        }
    },
    {
        "name": "dcl_query",
        "description": "Execute a read-only SQL query against the data lake. Returns results as structured data. Has automatic limits and timeout protections.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "SQL query to execute (SELECT only, no modifications)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum rows to return (default 100, max 1000)",
                    "default": 100
                },
                "timeout_seconds": {
                    "type": "integer",
                    "description": "Query timeout in seconds (default 30, max 120)",
                    "default": 30
                }
            },
            "required": ["sql"]
        }
    },
    {
        "name": "dcl_get_lineage",
        "description": "Trace the data lineage for a table - where the data comes from and how it was transformed.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "table_name": {
                    "type": "string",
                    "description": "Name of the table to trace lineage for"
                },
                "depth": {
                    "type": "integer",
                    "description": "How many levels of lineage to trace (default 2, max 5)",
                    "default": 2
                }
            },
            "required": ["table_name"]
        }
    },
    {
        "name": "dcl_get_metadata",
        "description": "Get detailed metadata about the data lake environment, including freshness, quality metrics, and statistics.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "table_name": {
                    "type": "string",
                    "description": "Specific table to get metadata for (optional, omit for overview)"
                },
                "metric_type": {
                    "type": "string",
                    "enum": ["freshness", "quality", "volume", "all"],
                    "description": "Type of metrics to retrieve",
                    "default": "all"
                }
            },
            "required": []
        }
    },
    {
        "name": "dcl_search_fields",
        "description": "Search for fields/columns across all tables by name or description. Implements ARB Condition 2: Metadata RAG for finding relevant fields without dumping all schemas.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "search_term": {
                    "type": "string",
                    "description": "Search term to find matching fields (e.g., 'email', 'revenue', 'customer_id')"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results to return",
                    "default": 20
                }
            },
            "required": ["search_term"]
        }
    }
]


@dataclass
class DCLContext:
    """Context for DCL operations."""
    tenant_id: UUID
    user_id: Optional[UUID] = None
    environment: str = "production"


class DCLMCPServer:
    """
    MCP Server implementation for DCL.

    Provides data lake access with:
    - Read-only query execution
    - Schema and metadata discovery
    - Field search (Metadata RAG)
    - Data lineage
    """

    def __init__(self, dcl_client: Optional[Any] = None):
        """
        Initialize the DCL MCP server.

        Args:
            dcl_client: Optional DCL client for actual data access
        """
        self.dcl_client = dcl_client
        self._tools = {tool["name"]: tool for tool in DCL_TOOLS}

    def get_tools(self) -> list[dict]:
        """Return the list of available tools."""
        return DCL_TOOLS

    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict,
        context: DCLContext
    ) -> dict:
        """
        Execute a DCL tool.

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

        logger.info(f"Executing DCL tool: {tool_name} for tenant {context.tenant_id}")

        try:
            if tool_name == "dcl_list_tables":
                return await self._list_tables(arguments, context)
            elif tool_name == "dcl_get_schema":
                return await self._get_schema(arguments, context)
            elif tool_name == "dcl_query":
                return await self._execute_query(arguments, context)
            elif tool_name == "dcl_get_lineage":
                return await self._get_lineage(arguments, context)
            elif tool_name == "dcl_get_metadata":
                return await self._get_metadata(arguments, context)
            elif tool_name == "dcl_search_fields":
                return await self._search_fields(arguments, context)
            else:
                return {"error": f"Tool not implemented: {tool_name}", "success": False}

        except Exception as e:
            logger.error(f"DCL tool execution error: {e}")
            return {
                "error": str(e),
                "success": False
            }

    async def _list_tables(self, args: dict, context: DCLContext) -> dict:
        """List available tables."""
        filter_pattern = args.get("filter")
        include_metadata = args.get("include_metadata", True)

        if self.dcl_client:
            # Real implementation would call DCL API
            tables = await self.dcl_client.list_tables(
                tenant_id=context.tenant_id,
                filter=filter_pattern
            )
        else:
            # Mock data for testing
            tables = [
                {
                    "name": "customers",
                    "description": "Customer master data from CRM",
                    "row_count": 15420 if include_metadata else None,
                    "last_updated": "2026-01-19T14:30:00Z" if include_metadata else None
                },
                {
                    "name": "orders",
                    "description": "Sales orders from ERP",
                    "row_count": 284567 if include_metadata else None,
                    "last_updated": "2026-01-20T08:15:00Z" if include_metadata else None
                },
                {
                    "name": "products",
                    "description": "Product catalog",
                    "row_count": 3421 if include_metadata else None,
                    "last_updated": "2026-01-18T22:00:00Z" if include_metadata else None
                },
                {
                    "name": "contacts",
                    "description": "Contact information from Salesforce",
                    "row_count": 42890 if include_metadata else None,
                    "last_updated": "2026-01-20T09:00:00Z" if include_metadata else None
                },
                {
                    "name": "revenue_summary",
                    "description": "Aggregated revenue metrics by month",
                    "row_count": 156 if include_metadata else None,
                    "last_updated": "2026-01-20T00:00:00Z" if include_metadata else None
                }
            ]

            # Apply filter if provided
            if filter_pattern:
                import fnmatch
                tables = [t for t in tables if fnmatch.fnmatch(t["name"], filter_pattern)]

        return {
            "success": True,
            "tables": tables,
            "count": len(tables)
        }

    async def _get_schema(self, args: dict, context: DCLContext) -> dict:
        """Get table schema."""
        table_name = args.get("table_name")
        include_stats = args.get("include_stats", False)

        if not table_name:
            return {"error": "table_name is required", "success": False}

        if self.dcl_client:
            schema = await self.dcl_client.get_schema(
                tenant_id=context.tenant_id,
                table_name=table_name
            )
        else:
            # Mock schemas
            schemas = {
                "customers": {
                    "columns": [
                        {"name": "id", "type": "UUID", "description": "Primary key", "nullable": False},
                        {"name": "email", "type": "VARCHAR(255)", "description": "Customer email address", "nullable": False},
                        {"name": "name", "type": "VARCHAR(255)", "description": "Customer full name", "nullable": True},
                        {"name": "company", "type": "VARCHAR(255)", "description": "Company name", "nullable": True},
                        {"name": "created_at", "type": "TIMESTAMP", "description": "Record creation time", "nullable": False},
                        {"name": "updated_at", "type": "TIMESTAMP", "description": "Last update time", "nullable": False}
                    ]
                },
                "orders": {
                    "columns": [
                        {"name": "id", "type": "UUID", "description": "Order ID", "nullable": False},
                        {"name": "customer_id", "type": "UUID", "description": "Reference to customers table", "nullable": False},
                        {"name": "order_date", "type": "DATE", "description": "Date order was placed", "nullable": False},
                        {"name": "total_amount", "type": "DECIMAL(12,2)", "description": "Order total in USD", "nullable": False},
                        {"name": "status", "type": "VARCHAR(50)", "description": "Order status (pending, shipped, delivered)", "nullable": False}
                    ]
                },
                "products": {
                    "columns": [
                        {"name": "id", "type": "UUID", "description": "Product ID", "nullable": False},
                        {"name": "sku", "type": "VARCHAR(100)", "description": "Stock keeping unit", "nullable": False},
                        {"name": "name", "type": "VARCHAR(255)", "description": "Product name", "nullable": False},
                        {"name": "category", "type": "VARCHAR(100)", "description": "Product category", "nullable": True},
                        {"name": "price", "type": "DECIMAL(10,2)", "description": "Unit price in USD", "nullable": False}
                    ]
                }
            }

            schema = schemas.get(table_name, {"columns": []})

            if not schema["columns"]:
                return {"error": f"Table not found: {table_name}", "success": False}

        return {
            "success": True,
            "table_name": table_name,
            "schema": schema
        }

    async def _execute_query(self, args: dict, context: DCLContext) -> dict:
        """Execute a SQL query."""
        sql = args.get("sql", "").strip()
        limit = min(args.get("limit", 100), 1000)
        timeout = min(args.get("timeout_seconds", 30), 120)

        if not sql:
            return {"error": "sql is required", "success": False}

        # Security checks
        sql_upper = sql.upper()

        # Block write operations
        forbidden_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE", "ALTER", "CREATE", "GRANT", "REVOKE"]
        for keyword in forbidden_keywords:
            if keyword in sql_upper:
                return {
                    "error": f"Write operations are not allowed: {keyword} detected",
                    "success": False
                }

        # Block dangerous patterns
        if "--" in sql or "/*" in sql or ";" in sql[:-1]:
            return {
                "error": "Potential SQL injection detected",
                "success": False
            }

        if self.dcl_client:
            results = await self.dcl_client.execute_query(
                tenant_id=context.tenant_id,
                sql=sql,
                limit=limit,
                timeout=timeout
            )
        else:
            # Mock query results
            results = {
                "columns": ["id", "name", "value"],
                "rows": [
                    {"id": 1, "name": "Item A", "value": 100.00},
                    {"id": 2, "name": "Item B", "value": 250.50},
                    {"id": 3, "name": "Item C", "value": 75.25}
                ],
                "row_count": 3,
                "execution_time_ms": 45
            }

        return {
            "success": True,
            "results": results
        }

    async def _get_lineage(self, args: dict, context: DCLContext) -> dict:
        """Get data lineage for a table."""
        table_name = args.get("table_name")
        depth = min(args.get("depth", 2), 5)

        if not table_name:
            return {"error": "table_name is required", "success": False}

        if self.dcl_client:
            lineage = await self.dcl_client.get_lineage(
                tenant_id=context.tenant_id,
                table_name=table_name,
                depth=depth
            )
        else:
            # Mock lineage data
            lineage = {
                "table": table_name,
                "upstream": [
                    {
                        "table": "raw_crm_accounts",
                        "source": "Salesforce",
                        "transformation": "Extract & normalize",
                        "upstream": [
                            {
                                "table": "Salesforce.Account",
                                "source": "Salesforce API",
                                "transformation": "Direct extract"
                            }
                        ] if depth > 1 else []
                    }
                ],
                "downstream": [
                    {
                        "table": "customer_360",
                        "transformation": "Join with orders"
                    }
                ]
            }

        return {
            "success": True,
            "lineage": lineage
        }

    async def _get_metadata(self, args: dict, context: DCLContext) -> dict:
        """Get metadata and metrics."""
        table_name = args.get("table_name")
        metric_type = args.get("metric_type", "all")

        if self.dcl_client:
            metadata = await self.dcl_client.get_metadata(
                tenant_id=context.tenant_id,
                table_name=table_name,
                metric_type=metric_type
            )
        else:
            # Mock metadata
            if table_name:
                metadata = {
                    "table": table_name,
                    "freshness": {
                        "last_updated": "2026-01-20T08:15:00Z",
                        "update_frequency": "hourly",
                        "staleness_hours": 2
                    } if metric_type in ["freshness", "all"] else None,
                    "quality": {
                        "completeness": 0.98,
                        "accuracy_score": 0.95,
                        "null_percentage": 0.02
                    } if metric_type in ["quality", "all"] else None,
                    "volume": {
                        "row_count": 15420,
                        "size_bytes": 52428800,
                        "growth_rate_daily": 0.02
                    } if metric_type in ["volume", "all"] else None
                }
            else:
                metadata = {
                    "overview": {
                        "total_tables": 5,
                        "total_rows": 346444,
                        "total_size_gb": 2.4,
                        "last_sync": "2026-01-20T09:00:00Z"
                    }
                }

        return {
            "success": True,
            "metadata": metadata
        }

    async def _search_fields(self, args: dict, context: DCLContext) -> dict:
        """
        Search for fields across tables - Metadata RAG implementation.

        ARB Condition 2: Instead of dumping all schemas, we search
        for relevant fields and return only matching results.
        """
        search_term = args.get("search_term", "").lower()
        limit = min(args.get("limit", 20), 50)

        if not search_term:
            return {"error": "search_term is required", "success": False}

        if self.dcl_client:
            # Real implementation would use vector search
            results = await self.dcl_client.search_fields(
                tenant_id=context.tenant_id,
                search_term=search_term,
                limit=limit
            )
        else:
            # Mock field search (simulated RAG)
            all_fields = [
                {"table": "customers", "field": "email", "type": "VARCHAR(255)", "description": "Customer email address"},
                {"table": "customers", "field": "customer_id", "type": "UUID", "description": "Unique customer identifier"},
                {"table": "customers", "field": "name", "type": "VARCHAR(255)", "description": "Customer full name"},
                {"table": "orders", "field": "customer_id", "type": "UUID", "description": "Reference to customer"},
                {"table": "orders", "field": "order_total", "type": "DECIMAL", "description": "Total order value"},
                {"table": "orders", "field": "order_date", "type": "DATE", "description": "Date of order placement"},
                {"table": "contacts", "field": "email", "type": "VARCHAR(255)", "description": "Contact email"},
                {"table": "contacts", "field": "phone", "type": "VARCHAR(50)", "description": "Contact phone number"},
                {"table": "products", "field": "product_id", "type": "UUID", "description": "Product identifier"},
                {"table": "products", "field": "price", "type": "DECIMAL", "description": "Product price"},
                {"table": "revenue_summary", "field": "total_revenue", "type": "DECIMAL", "description": "Total revenue amount"},
                {"table": "revenue_summary", "field": "month", "type": "DATE", "description": "Revenue month"},
            ]

            # Simple search matching
            results = [
                f for f in all_fields
                if search_term in f["field"].lower() or search_term in f["description"].lower()
            ][:limit]

        return {
            "success": True,
            "search_term": search_term,
            "results": results,
            "count": len(results)
        }
