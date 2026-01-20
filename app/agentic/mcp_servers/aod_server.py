"""
AOD (Asset & Observability Discovery) MCP Server

Exposes AOD functionality as MCP tools for agent access:
- Asset discovery across systems
- Data lineage tracing
- Sensitivity classification
- Metadata search

Part of "The Moat" - deep data understanding capabilities.
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

AOD_TOOLS = [
    {
        "name": "aod_discover_assets",
        "description": "Discover data assets across all connected systems. Search by name, type, or metadata. Returns matching assets with basic info.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (e.g., 'customer', 'sales report', 'api endpoint')"
                },
                "asset_type": {
                    "type": "string",
                    "enum": ["table", "view", "api", "file", "dashboard", "all"],
                    "description": "Filter by asset type",
                    "default": "all"
                },
                "source_system": {
                    "type": "string",
                    "description": "Filter by source system (e.g., 'salesforce', 'snowflake')"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results to return",
                    "default": 20
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "aod_get_asset_details",
        "description": "Get detailed information about a specific data asset, including schema, statistics, and metadata.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "asset_id": {
                    "type": "string",
                    "description": "Unique asset identifier"
                }
            },
            "required": ["asset_id"]
        }
    },
    {
        "name": "aod_get_lineage",
        "description": "Trace data lineage for an asset - where data comes from (upstream) and where it flows to (downstream).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "asset_id": {
                    "type": "string",
                    "description": "Asset to trace lineage for"
                },
                "direction": {
                    "type": "string",
                    "enum": ["upstream", "downstream", "both"],
                    "description": "Direction to trace",
                    "default": "both"
                },
                "depth": {
                    "type": "integer",
                    "description": "How many levels to trace (1-5)",
                    "default": 2
                }
            },
            "required": ["asset_id"]
        }
    },
    {
        "name": "aod_classify_sensitivity",
        "description": "Get data sensitivity classification for an asset. Identifies PII, financial data, and other sensitive categories.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "asset_id": {
                    "type": "string",
                    "description": "Asset to classify"
                }
            },
            "required": ["asset_id"]
        }
    },
    {
        "name": "aod_search_metadata",
        "description": "Search across all asset metadata including descriptions, tags, owners, and custom properties.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                },
                "filters": {
                    "type": "object",
                    "description": "Additional filters (owner, tag, created_after, etc.)",
                    "properties": {
                        "owner": {"type": "string"},
                        "tag": {"type": "string"},
                        "created_after": {"type": "string"},
                        "updated_after": {"type": "string"}
                    }
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "aod_get_related_assets",
        "description": "Find assets related to a given asset by lineage, schema similarity, or usage patterns.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "asset_id": {
                    "type": "string",
                    "description": "Asset to find relations for"
                },
                "relation_type": {
                    "type": "string",
                    "enum": ["lineage", "similar_schema", "same_owner", "same_source", "all"],
                    "description": "Type of relationship to find",
                    "default": "all"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results",
                    "default": 10
                }
            },
            "required": ["asset_id"]
        }
    },
    {
        "name": "aod_explain_field",
        "description": "Get a detailed explanation of what a field means, its business context, calculation logic, and source.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "asset_id": {
                    "type": "string",
                    "description": "Asset containing the field"
                },
                "field_name": {
                    "type": "string",
                    "description": "Name of the field to explain"
                }
            },
            "required": ["asset_id", "field_name"]
        }
    },
    {
        "name": "aod_get_data_quality",
        "description": "Get data quality metrics for an asset including completeness, freshness, and accuracy scores.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "asset_id": {
                    "type": "string",
                    "description": "Asset to check quality for"
                }
            },
            "required": ["asset_id"]
        }
    }
]


@dataclass
class AODContext:
    """Context for AOD operations."""
    tenant_id: UUID
    user_id: Optional[UUID] = None


class AODMCPServer:
    """
    MCP Server implementation for AOD.

    Provides asset discovery and observability with:
    - Cross-system asset discovery
    - Data lineage tracing
    - Sensitivity classification
    - Semantic field explanations
    """

    def __init__(self, aod_client: Optional[Any] = None):
        """
        Initialize the AOD MCP server.

        Args:
            aod_client: Optional AOD client for actual operations
        """
        self.aod_client = aod_client
        self._tools = {tool["name"]: tool for tool in AOD_TOOLS}

    def get_tools(self) -> list[dict]:
        """Return the list of available tools."""
        return AOD_TOOLS

    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict,
        context: AODContext
    ) -> dict:
        """
        Execute an AOD tool.

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

        logger.info(f"Executing AOD tool: {tool_name} for tenant {context.tenant_id}")

        try:
            if tool_name == "aod_discover_assets":
                return await self._discover_assets(arguments, context)
            elif tool_name == "aod_get_asset_details":
                return await self._get_asset_details(arguments, context)
            elif tool_name == "aod_get_lineage":
                return await self._get_lineage(arguments, context)
            elif tool_name == "aod_classify_sensitivity":
                return await self._classify_sensitivity(arguments, context)
            elif tool_name == "aod_search_metadata":
                return await self._search_metadata(arguments, context)
            elif tool_name == "aod_get_related_assets":
                return await self._get_related_assets(arguments, context)
            elif tool_name == "aod_explain_field":
                return await self._explain_field(arguments, context)
            elif tool_name == "aod_get_data_quality":
                return await self._get_data_quality(arguments, context)
            else:
                return {"error": f"Tool not implemented: {tool_name}", "success": False}

        except Exception as e:
            logger.error(f"AOD tool execution error: {e}")
            return {
                "error": str(e),
                "success": False
            }

    async def _discover_assets(self, args: dict, context: AODContext) -> dict:
        """Discover data assets."""
        query = args.get("query", "")
        asset_type = args.get("asset_type", "all")
        source_system = args.get("source_system")
        limit = min(args.get("limit", 20), 50)

        if self.aod_client:
            assets = await self.aod_client.discover_assets(
                tenant_id=context.tenant_id,
                query=query,
                asset_type=asset_type,
                source_system=source_system,
                limit=limit
            )
        else:
            # Mock asset data
            all_assets = [
                {
                    "id": "asset-001",
                    "name": "customers",
                    "type": "table",
                    "source_system": "postgresql",
                    "description": "Master customer data from CRM",
                    "owner": "data-team",
                    "row_count": 15420,
                    "last_updated": "2026-01-20T08:00:00Z"
                },
                {
                    "id": "asset-002",
                    "name": "Account",
                    "type": "table",
                    "source_system": "salesforce",
                    "description": "Salesforce Account object",
                    "owner": "sales-ops",
                    "row_count": 8540,
                    "last_updated": "2026-01-20T09:00:00Z"
                },
                {
                    "id": "asset-003",
                    "name": "revenue_dashboard",
                    "type": "dashboard",
                    "source_system": "tableau",
                    "description": "Executive revenue overview dashboard",
                    "owner": "analytics",
                    "last_updated": "2026-01-19T15:00:00Z"
                },
                {
                    "id": "asset-004",
                    "name": "orders",
                    "type": "table",
                    "source_system": "postgresql",
                    "description": "Sales orders from ERP system",
                    "owner": "data-team",
                    "row_count": 284567,
                    "last_updated": "2026-01-20T08:15:00Z"
                },
                {
                    "id": "asset-005",
                    "name": "/api/v1/customers",
                    "type": "api",
                    "source_system": "internal",
                    "description": "Customer data REST API endpoint",
                    "owner": "platform-team",
                    "last_updated": "2026-01-15T12:00:00Z"
                },
                {
                    "id": "asset-006",
                    "name": "customer_360",
                    "type": "view",
                    "source_system": "snowflake",
                    "description": "Unified customer view combining CRM, support, and billing",
                    "owner": "analytics",
                    "row_count": 12890,
                    "last_updated": "2026-01-20T00:00:00Z"
                }
            ]

            # Filter by query
            query_lower = query.lower()
            assets = [
                a for a in all_assets
                if query_lower in a["name"].lower() or query_lower in a["description"].lower()
            ]

            # Filter by type
            if asset_type != "all":
                assets = [a for a in assets if a["type"] == asset_type]

            # Filter by source
            if source_system:
                assets = [a for a in assets if a["source_system"] == source_system]

            assets = assets[:limit]

        return {
            "success": True,
            "query": query,
            "assets": assets,
            "count": len(assets)
        }

    async def _get_asset_details(self, args: dict, context: AODContext) -> dict:
        """Get detailed asset information."""
        asset_id = args.get("asset_id")

        if not asset_id:
            return {"error": "asset_id is required", "success": False}

        if self.aod_client:
            details = await self.aod_client.get_asset_details(
                tenant_id=context.tenant_id,
                asset_id=asset_id
            )
        else:
            # Mock details
            details = {
                "id": asset_id,
                "name": "customers",
                "type": "table",
                "source_system": "postgresql",
                "description": "Master customer data synchronized from CRM and enriched with support data",
                "owner": "data-team",
                "schema": {
                    "columns": [
                        {"name": "id", "type": "uuid", "description": "Primary key"},
                        {"name": "email", "type": "varchar", "description": "Customer email", "pii": True},
                        {"name": "name", "type": "varchar", "description": "Full name", "pii": True},
                        {"name": "company", "type": "varchar", "description": "Company name"},
                        {"name": "mrr", "type": "decimal", "description": "Monthly recurring revenue"},
                        {"name": "created_at", "type": "timestamp", "description": "Account creation date"}
                    ]
                },
                "statistics": {
                    "row_count": 15420,
                    "size_bytes": 52428800,
                    "null_percentage": 0.02,
                    "distinct_values": {"company": 8542}
                },
                "metadata": {
                    "tags": ["customer", "crm", "master-data"],
                    "created_at": "2024-06-15T10:00:00Z",
                    "last_updated": "2026-01-20T08:00:00Z",
                    "update_frequency": "hourly"
                }
            }

        return {
            "success": True,
            "asset": details
        }

    async def _get_lineage(self, args: dict, context: AODContext) -> dict:
        """Get data lineage."""
        asset_id = args.get("asset_id")
        direction = args.get("direction", "both")
        depth = min(args.get("depth", 2), 5)

        if not asset_id:
            return {"error": "asset_id is required", "success": False}

        if self.aod_client:
            lineage = await self.aod_client.get_lineage(
                tenant_id=context.tenant_id,
                asset_id=asset_id,
                direction=direction,
                depth=depth
            )
        else:
            # Mock lineage data
            lineage = {
                "asset_id": asset_id,
                "upstream": [
                    {
                        "id": "asset-sf-account",
                        "name": "Salesforce.Account",
                        "type": "table",
                        "source_system": "salesforce",
                        "transformation": "Extract via Fivetran",
                        "fields_used": ["Id", "Name", "BillingCity"],
                        "upstream": [
                            {
                                "id": "ext-sf-api",
                                "name": "Salesforce REST API",
                                "type": "api",
                                "source_system": "salesforce"
                            }
                        ] if depth > 1 else []
                    },
                    {
                        "id": "asset-stripe",
                        "name": "stripe.customers",
                        "type": "table",
                        "source_system": "stripe",
                        "transformation": "Extract via Airbyte",
                        "fields_used": ["email", "metadata"]
                    }
                ] if direction in ["upstream", "both"] else [],
                "downstream": [
                    {
                        "id": "asset-customer-360",
                        "name": "customer_360",
                        "type": "view",
                        "source_system": "snowflake",
                        "transformation": "JOIN on customer_id",
                        "downstream": [
                            {
                                "id": "asset-revenue-dash",
                                "name": "revenue_dashboard",
                                "type": "dashboard",
                                "source_system": "tableau"
                            }
                        ] if depth > 1 else []
                    }
                ] if direction in ["downstream", "both"] else []
            }

        return {
            "success": True,
            "lineage": lineage
        }

    async def _classify_sensitivity(self, args: dict, context: AODContext) -> dict:
        """Classify data sensitivity."""
        asset_id = args.get("asset_id")

        if not asset_id:
            return {"error": "asset_id is required", "success": False}

        if self.aod_client:
            classification = await self.aod_client.classify_sensitivity(
                tenant_id=context.tenant_id,
                asset_id=asset_id
            )
        else:
            # Mock classification
            classification = {
                "asset_id": asset_id,
                "overall_sensitivity": "high",
                "classifications": [
                    {
                        "field": "email",
                        "sensitivity": "high",
                        "categories": ["PII", "Contact Information"],
                        "regulations": ["GDPR", "CCPA"]
                    },
                    {
                        "field": "name",
                        "sensitivity": "high",
                        "categories": ["PII", "Personal Identity"],
                        "regulations": ["GDPR", "CCPA"]
                    },
                    {
                        "field": "mrr",
                        "sensitivity": "medium",
                        "categories": ["Financial", "Business Confidential"],
                        "regulations": []
                    },
                    {
                        "field": "company",
                        "sensitivity": "low",
                        "categories": ["Business"],
                        "regulations": []
                    }
                ],
                "recommendations": [
                    "Enable column-level encryption for email and name fields",
                    "Implement data masking for non-production environments",
                    "Restrict access to users with PII clearance"
                ]
            }

        return {
            "success": True,
            "classification": classification
        }

    async def _search_metadata(self, args: dict, context: AODContext) -> dict:
        """Search asset metadata."""
        query = args.get("query", "")
        filters = args.get("filters", {})

        if not query:
            return {"error": "query is required", "success": False}

        if self.aod_client:
            results = await self.aod_client.search_metadata(
                tenant_id=context.tenant_id,
                query=query,
                filters=filters
            )
        else:
            # Mock search results
            results = [
                {
                    "asset_id": "asset-001",
                    "asset_name": "customers",
                    "match_field": "description",
                    "match_text": "Master customer data from CRM",
                    "relevance_score": 0.95
                },
                {
                    "asset_id": "asset-006",
                    "asset_name": "customer_360",
                    "match_field": "tags",
                    "match_text": "customer",
                    "relevance_score": 0.88
                }
            ]

        return {
            "success": True,
            "query": query,
            "results": results,
            "count": len(results)
        }

    async def _get_related_assets(self, args: dict, context: AODContext) -> dict:
        """Find related assets."""
        asset_id = args.get("asset_id")
        relation_type = args.get("relation_type", "all")
        limit = args.get("limit", 10)

        if not asset_id:
            return {"error": "asset_id is required", "success": False}

        if self.aod_client:
            related = await self.aod_client.get_related_assets(
                tenant_id=context.tenant_id,
                asset_id=asset_id,
                relation_type=relation_type,
                limit=limit
            )
        else:
            # Mock related assets
            related = [
                {
                    "asset_id": "asset-002",
                    "asset_name": "Account",
                    "relation_type": "lineage",
                    "relation_details": "Upstream source"
                },
                {
                    "asset_id": "asset-006",
                    "asset_name": "customer_360",
                    "relation_type": "lineage",
                    "relation_details": "Downstream consumer"
                },
                {
                    "asset_id": "asset-004",
                    "asset_name": "orders",
                    "relation_type": "same_owner",
                    "relation_details": "Owned by data-team"
                }
            ]

        return {
            "success": True,
            "asset_id": asset_id,
            "related": related,
            "count": len(related)
        }

    async def _explain_field(self, args: dict, context: AODContext) -> dict:
        """Explain a field in business terms."""
        asset_id = args.get("asset_id")
        field_name = args.get("field_name")

        if not asset_id or not field_name:
            return {"error": "asset_id and field_name are required", "success": False}

        if self.aod_client:
            explanation = await self.aod_client.explain_field(
                tenant_id=context.tenant_id,
                asset_id=asset_id,
                field_name=field_name
            )
        else:
            # Mock field explanation
            explanations = {
                "mrr": {
                    "field_name": "mrr",
                    "display_name": "Monthly Recurring Revenue",
                    "description": "The predictable revenue generated from active subscriptions each month.",
                    "business_definition": "Sum of all active subscription values normalized to monthly amounts. Excludes one-time fees and usage-based charges.",
                    "calculation": "SUM(subscription_amount * (12 / billing_period_months)) for active subscriptions",
                    "data_type": "decimal(12,2)",
                    "unit": "USD",
                    "source": "Calculated from Stripe subscriptions and manual contracts",
                    "owner": "Finance Team",
                    "related_fields": ["arr", "contract_value", "subscription_status"],
                    "notes": "Updated daily at 00:00 UTC. Historical values are snapshotted monthly."
                },
                "email": {
                    "field_name": "email",
                    "display_name": "Customer Email",
                    "description": "Primary email address for customer communication.",
                    "business_definition": "The main email address associated with a customer account, used for billing and support communications.",
                    "data_type": "varchar(255)",
                    "source": "Salesforce Contact.Email, validated on ingestion",
                    "owner": "Data Team",
                    "sensitivity": "PII - High",
                    "notes": "Must be unique per customer. Validated for format compliance."
                }
            }

            explanation = explanations.get(field_name, {
                "field_name": field_name,
                "description": f"No detailed explanation available for {field_name}",
                "data_type": "unknown"
            })

        return {
            "success": True,
            "explanation": explanation
        }

    async def _get_data_quality(self, args: dict, context: AODContext) -> dict:
        """Get data quality metrics."""
        asset_id = args.get("asset_id")

        if not asset_id:
            return {"error": "asset_id is required", "success": False}

        if self.aod_client:
            quality = await self.aod_client.get_data_quality(
                tenant_id=context.tenant_id,
                asset_id=asset_id
            )
        else:
            # Mock quality metrics
            quality = {
                "asset_id": asset_id,
                "overall_score": 0.94,
                "dimensions": {
                    "completeness": {
                        "score": 0.98,
                        "details": "2% null values across all columns"
                    },
                    "accuracy": {
                        "score": 0.95,
                        "details": "Based on validation rules and cross-system checks"
                    },
                    "freshness": {
                        "score": 0.99,
                        "details": "Last updated 2 hours ago, SLA is 4 hours"
                    },
                    "consistency": {
                        "score": 0.92,
                        "details": "8% records have format inconsistencies in phone field"
                    },
                    "uniqueness": {
                        "score": 0.88,
                        "details": "12% duplicate emails detected"
                    }
                },
                "issues": [
                    {
                        "severity": "medium",
                        "dimension": "uniqueness",
                        "description": "12% of email addresses are duplicated across records",
                        "recommendation": "Implement deduplication logic or merge duplicate records"
                    },
                    {
                        "severity": "low",
                        "dimension": "consistency",
                        "description": "Phone number formats vary (some with country codes, some without)",
                        "recommendation": "Standardize to E.164 format during ingestion"
                    }
                ],
                "last_assessed": "2026-01-20T06:00:00Z"
            }

        return {
            "success": True,
            "quality": quality
        }
