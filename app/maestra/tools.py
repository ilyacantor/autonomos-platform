"""
Maestra Tool Definitions — actions Maestra can take and their parameters.
"""

import logging

logger = logging.getLogger(__name__)


class MaestraTools:
    """
    Tool definitions for Maestra agent.

    These define what actions Maestra can take and their parameters.
    """

    TOOL_DEFINITIONS = [
        {
            "name": "check_module_status",
            "description": "Check health and readiness of an AOS module",
            "parameters": {"module": "str (aod|aam|dcl|nlq|farm)"},
        },
        {
            "name": "trigger_pipeline_run",
            "description": "Trigger a pipeline run for specified entities",
            "parameters": {
                "entities": "list[str]",
                "run_type": "str (full|incremental)",
            },
        },
        {
            "name": "get_engagement_state",
            "description": "Get current engagement state and progress",
            "parameters": {"engagement_id": "str"},
        },
        {
            "name": "request_human_review",
            "description": "Escalate a decision for human review",
            "parameters": {
                "decision_type": "str",
                "context": "dict",
                "urgency": "str (low|medium|high|critical)",
            },
        },
        {
            "name": "update_run_ledger",
            "description": "Record a step completion or failure in the run ledger",
            "parameters": {
                "step_name": "str",
                "status": "str",
                "outputs_ref": "str|None",
            },
        },
        {
            "name": "write_cofa_mapping",
            "description": "Write COFA mapping table, conflict register, and unified account structure to DCL. Called after COFA unification reasoning is complete. Posts structured mapping data to DCL's /api/dcl/cofa-mapping endpoint.",
            "parameters": {
                "engagement_id": "str (required)",
                "acquirer_entity_id": "str (required)",
                "target_entity_id": "str (required)",
                "tenant_id": "str (required)",
                "run_id": "str (required)",
                "mappings": "list[dict] (required) — each with unified_account, acquirer_account, target_account, confidence, mapping_basis",
                "conflicts": "list[dict] (required) — each with conflict_id, conflict_type, severity, dollar_impact, description, acquirer_treatment, target_treatment, resolution_status",
                "unified_accounts": "list[dict] (required) — each with account_name, account_type, hierarchy_parent, source_entities",
            },
        },
    ]

    # Explicit JSON Schema for write_cofa_mapping — the generic builder
    # can't express nested arrays/objects, and the LLM needs precise types.
    _WRITE_COFA_MAPPING_SCHEMA: dict = {
        "type": "object",
        "properties": {
            "engagement_id": {"type": "string", "description": "Engagement identifier"},
            "acquirer_entity_id": {"type": "string", "description": "Acquirer entity identifier"},
            "target_entity_id": {"type": "string", "description": "Target entity identifier"},
            "tenant_id": {"type": "string", "description": "Tenant identifier"},
            "run_id": {"type": "string", "description": "Unique run identifier (uuid4)"},
            "mappings": {
                "type": "array",
                "description": "Account mapping rows — one per unified account",
                "items": {
                    "type": "object",
                    "properties": {
                        "unified_account": {"type": "string"},
                        "acquirer_account": {"type": "string"},
                        "target_account": {"type": "string"},
                        "confidence": {"type": "number", "description": "0-1 confidence score"},
                        "mapping_basis": {"type": "string", "description": "Rationale for the mapping"},
                    },
                    "required": ["unified_account", "acquirer_account", "target_account", "confidence", "mapping_basis"],
                },
            },
            "conflicts": {
                "type": "array",
                "description": "COFA conflicts detected between acquirer and target accounting policies",
                "items": {
                    "type": "object",
                    "properties": {
                        "conflict_id": {"type": "string"},
                        "conflict_type": {"type": "string"},
                        "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                        "dollar_impact": {"type": "number", "description": "Estimated dollar impact"},
                        "description": {"type": "string"},
                        "acquirer_treatment": {"type": "string"},
                        "target_treatment": {"type": "string"},
                        "resolution_status": {"type": "string", "enum": ["unresolved", "resolved", "deferred"]},
                    },
                    "required": ["conflict_id", "conflict_type", "severity", "dollar_impact", "description",
                                 "acquirer_treatment", "target_treatment", "resolution_status"],
                },
            },
            "unified_accounts": {
                "type": "array",
                "description": "Unified chart of accounts structure",
                "items": {
                    "type": "object",
                    "properties": {
                        "account_name": {"type": "string"},
                        "account_type": {"type": "string"},
                        "hierarchy_parent": {"type": "string"},
                        "source_entities": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Entity IDs that contribute to this account",
                        },
                    },
                    "required": ["account_name", "account_type", "hierarchy_parent", "source_entities"],
                },
            },
        },
        "required": ["engagement_id", "acquirer_entity_id", "target_entity_id",
                      "tenant_id", "run_id", "mappings", "conflicts", "unified_accounts"],
    }

    def get_tools(self, filter_names: list[str] | None = None) -> list[dict]:
        """
        Return tool definitions in Claude tool format.

        Args:
            filter_names: If provided, only return tools whose name is in this list.
        """
        tools = []
        for defn in self.TOOL_DEFINITIONS:
            if filter_names and defn["name"] not in filter_names:
                continue

            # Use explicit schema for write_cofa_mapping
            if defn["name"] == "write_cofa_mapping":
                tools.append({
                    "name": defn["name"],
                    "description": defn["description"],
                    "input_schema": self._WRITE_COFA_MAPPING_SCHEMA,
                })
                continue

            # Generic builder for simple string-param tools
            tool = {
                "name": defn["name"],
                "description": defn["description"],
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            }
            for param_name, param_desc in defn["parameters"].items():
                tool["input_schema"]["properties"][param_name] = {
                    "type": "string",
                    "description": param_desc,
                }
                tool["input_schema"]["required"].append(param_name)
            tools.append(tool)
        return tools

    def validate_tool_call(self, tool_name: str, params: dict) -> dict:
        """Validate a tool call against its definition."""
        defn = None
        for d in self.TOOL_DEFINITIONS:
            if d["name"] == tool_name:
                defn = d
                break

        if defn is None:
            return {
                "valid": False,
                "error": f"Unknown tool: {tool_name}. "
                         f"Available tools: {[d['name'] for d in self.TOOL_DEFINITIONS]}",
            }

        missing = []
        for param_name in defn["parameters"]:
            if "None" not in defn["parameters"][param_name] and param_name not in params:
                missing.append(param_name)

        if missing:
            return {
                "valid": False,
                "error": f"Missing required parameters for {tool_name}: {missing}",
            }

        return {"valid": True, "error": None}
