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

    def get_tools(self) -> list[dict]:
        """Return tool definitions in Claude tool format."""
        tools = []
        for defn in self.TOOL_DEFINITIONS:
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
