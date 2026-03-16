"""
Maestra Chat — Platform-layer orchestration chat.

This is different from NLQ's Maestra chat (which handles data queries).
Platform Maestra handles: engagement management, pipeline orchestration,
module health, human review requests.
"""

import logging
import uuid
from pathlib import Path

from app.agentic.gateway.client import ModelTier, get_ai_gateway
from app.maestra.engagement import EngagementManager
from app.maestra.run_ledger import RunLedger
from app.maestra.constitution import Constitution
from app.maestra.tools import MaestraTools
from app.maestra.tool_executor import execute_tool_call

logger = logging.getLogger(__name__)

# Layer 0 accounting axioms — loaded once at import time.
# These are non-negotiable; if the file is missing the system cannot reason safely.
_AXIOMS_PATH = Path(__file__).parent / "constitution" / "LAYER_0_ACCOUNTING_AXIOMS.md"
if not _AXIOMS_PATH.exists():
    raise FileNotFoundError(
        f"Layer 0 accounting axioms not found at {_AXIOMS_PATH} — "
        f"Maestra cannot operate without foundational axioms"
    )
_LAYER_0_AXIOMS = _AXIOMS_PATH.read_text(encoding="utf-8")

# Layer 3 entity policy documents directory
_POLICIES_DIR = Path(__file__).parent / "constitution" / "policies"

# Maximum agentic loop iterations (tool call → result → re-call)
_MAX_TOOL_ITERATIONS = 5


def load_entity_policies(entity_a_id: str, entity_b_id: str) -> list[str]:
    """
    Load Layer 3 entity policy documents for the engagement's entity pair.

    Returns a list of context strings to inject between Layers 0-2 and Layer 4.
    If a policy file is not found for an entity, a no-GAAP-inference warning
    is returned instead — the agent must not infer accounting policies from
    GAAP training data when no explicit policy document exists.
    """
    context_parts: list[str] = []
    for label, entity_id in [("Entity A", entity_a_id), ("Entity B", entity_b_id)]:
        if not entity_id:
            continue
        policy_path = _POLICIES_DIR / f"{entity_id}_policy.md"
        if policy_path.exists():
            content = policy_path.read_text(encoding="utf-8")
            context_parts.append(
                f"## {label} Policy: {entity_id}\n\n{content}"
            )
            logger.info(
                "Loaded Layer 3 policy for %s (%s): %s",
                label, entity_id, policy_path,
            )
        else:
            warning = (
                f"## {label} Policy: {entity_id}\n\n"
                f"**WARNING: No Layer 3 policy document found for entity '{entity_id}'.**\n\n"
                f"Do not infer accounting policies from GAAP training data. "
                f"Any accounting treatment question for this entity must be flagged as "
                f"'policy not documented' and escalated for human review. "
                f"Per Axiom 7 (No GAAP Inference), absence of a policy means halt — not guess."
            )
            context_parts.append(warning)
            logger.warning(
                "No Layer 3 policy document for %s (%s) at %s — "
                "injecting no-GAAP-fallback warning into context",
                label, entity_id, policy_path,
            )
    return context_parts


class MaestraChat:
    """
    Maestra chat endpoint — Platform-layer orchestration chat.

    This is different from NLQ's Maestra chat (which handles data queries).
    Platform Maestra handles: engagement management, pipeline orchestration,
    module health, human review requests.
    """

    def __init__(
        self,
        engagement_manager: EngagementManager,
        run_ledger: RunLedger,
        constitution: Constitution,
    ):
        self._engagement_manager = engagement_manager
        self._run_ledger = run_ledger
        self._constitution = constitution
        self._tools = MaestraTools()

    async def process_message(
        self,
        message: str,
        engagement_id: str,
        session_id: str,
    ) -> dict:
        """
        Process a user message in the Maestra orchestration context.

        Calls the LLM with full context (axioms, constitution, entity policies)
        and executes tool calls in an agentic loop until the LLM is done.

        Returns:
        {
            "response": str,
            "tool_calls": [{"tool": str, "params": dict, "result": dict}],
            "requires_review": bool,
            "review_items": [dict]
        }
        """
        # Verify engagement exists
        engagement = await self._engagement_manager.get_engagement(engagement_id)

        # Check constitution compliance for the message intent
        compliance = self._constitution.check_compliance(message)

        tool_call_results: list[dict] = []
        review_items: list[dict] = []
        requires_review = False

        if not compliance["compliant"]:
            return {
                "response": (
                    f"Cannot process request — constitution violation detected: "
                    f"{'; '.join(compliance['violations'])}"
                ),
                "tool_calls": [],
                "requires_review": True,
                "review_items": [
                    {
                        "type": "constitution_violation",
                        "violations": compliance["violations"],
                        "original_message": message,
                    }
                ],
            }

        if compliance["warnings"]:
            requires_review = True
            review_items.extend(
                {"type": "warning", "message": w} for w in compliance["warnings"]
            )

        # Load Layer 3 entity policy documents
        acquirer_entity_id = engagement.get("entity_a", "")
        target_entity_id = engagement.get("entity_b", "")
        entity_policies = load_entity_policies(acquirer_entity_id, target_entity_id)

        # Generate a unique run_id for this COFA unification run
        run_id = str(uuid.uuid4())
        tenant_id = engagement.get("tenant_id", "")

        # Build system prompt: Layer 0 axioms + constitution + entity policies + instructions
        constitution_rules = self._constitution.get_rules()
        system_prompt = self._build_system_prompt(
            constitution_rules=constitution_rules,
            entity_policies=entity_policies,
            engagement_id=engagement_id,
            acquirer_entity_id=acquirer_entity_id,
            target_entity_id=target_entity_id,
            tenant_id=tenant_id,
            run_id=run_id,
            engagement_state=engagement.get("state", "unknown"),
        )

        # Get tools — only write_cofa_mapping for COFA unification context
        tools = self._tools.get_tools(filter_names=["write_cofa_mapping"])

        # Initialize AI Gateway
        gateway = await get_ai_gateway()

        # Build conversation messages
        messages = [{"role": "user", "content": message}]

        logger.info(
            "Maestra COFA unification starting — engagement=%s, run_id=%s, "
            "acquirer=%s, target=%s",
            engagement_id, run_id, acquirer_entity_id, target_entity_id,
        )

        # Agentic loop: call LLM, execute tools, feed results back
        for iteration in range(_MAX_TOOL_ITERATIONS):
            response = await gateway.complete(
                messages=messages,
                model_tier=ModelTier.BALANCED,
                tools=tools,
                system=system_prompt,
                temperature=0.2,
                max_tokens=8192,
                use_cache=False,
            )

            logger.info(
                "Maestra LLM response — iteration=%d, stop_reason=%s, "
                "tool_calls=%d, model=%s, tokens_in=%d, tokens_out=%d",
                iteration, response.stop_reason, len(response.tool_calls),
                response.model, response.input_tokens, response.output_tokens,
            )

            if response.stop_reason != "tool_use" or not response.tool_calls:
                # LLM is done — return final response
                break

            # Build assistant message with tool_use blocks for conversation history
            assistant_content = []
            if response.content:
                assistant_content.append({"type": "text", "text": response.content})
            for tc in response.tool_calls:
                assistant_content.append({
                    "type": "tool_use",
                    "id": tc["id"],
                    "name": tc["name"],
                    "input": tc["input"],
                })
            messages.append({"role": "assistant", "content": assistant_content})

            # Execute each tool call and collect results
            tool_results_for_message = []
            for tc in response.tool_calls:
                tool_name = tc["name"]
                tool_params = tc["input"]
                tool_call_id = tc["id"]

                # Validate the tool call
                validation = self._tools.validate_tool_call(tool_name, tool_params)
                if not validation["valid"]:
                    logger.warning(
                        "Maestra tool call validation failed: %s — %s",
                        tool_name, validation["error"],
                    )
                    tool_result = {"status": "validation_error", "error": validation["error"]}
                else:
                    # Execute the tool
                    tool_result = await execute_tool_call(
                        tool_name=tool_name,
                        params=tool_params,
                        engagement_id=engagement_id,
                        run_ledger=self._run_ledger,
                    )

                tool_call_results.append({
                    "tool": tool_name,
                    "params": tool_params,
                    "result": tool_result,
                })

                tool_results_for_message.append({
                    "type": "tool_result",
                    "tool_use_id": tool_call_id,
                    "content": str(tool_result),
                })

                logger.info(
                    "Maestra tool executed — tool=%s, status=%s",
                    tool_name, tool_result.get("status", "unknown"),
                )

            # Append tool results to messages for next LLM iteration
            messages.append({"role": "user", "content": tool_results_for_message})
        else:
            # Exhausted max iterations — this is not a silent fallback, we report it
            logger.warning(
                "Maestra agentic loop exhausted %d iterations — "
                "engagement=%s, run_id=%s",
                _MAX_TOOL_ITERATIONS, engagement_id, run_id,
            )

        return {
            "response": response.content,
            "tool_calls": tool_call_results,
            "requires_review": requires_review,
            "review_items": review_items,
            "context_layers": {
                "layer_3_entity_policies": entity_policies,
            },
            "run_id": run_id,
        }

    def _build_system_prompt(
        self,
        constitution_rules: list[str],
        entity_policies: list[str],
        engagement_id: str,
        acquirer_entity_id: str,
        target_entity_id: str,
        tenant_id: str,
        run_id: str,
        engagement_state: str,
    ) -> str:
        """Assemble the full system prompt for COFA unification."""
        parts = [
            "# Layer 0: Accounting Axioms (Immutable)\n\n",
            _LAYER_0_AXIOMS,
            "\n\n# Layer 2: Constitution Rules\n\n",
            "\n".join(f"- {rule}" for rule in constitution_rules),
            "\n\n# Layer 3: Entity Accounting Policies\n\n",
            "\n\n".join(entity_policies) if entity_policies else "(No entity policies loaded)",
            "\n\n# Engagement Context\n\n",
            f"- Engagement ID: {engagement_id}\n",
            f"- Engagement state: {engagement_state}\n",
            f"- Acquirer entity ID: {acquirer_entity_id}\n",
            f"- Target entity ID: {target_entity_id}\n",
            f"- Tenant ID: {tenant_id}\n",
            f"- Run ID: {run_id}\n",
            "\n# Instructions\n\n",
            "You are performing COFA (Chart of Accounts) unification for a merger/acquisition engagement. "
            "Analyze the acquirer and target entity accounting policies, identify conflicts in accounting "
            "treatment, map accounts to a unified chart of accounts, and write the results using the "
            "`write_cofa_mapping` tool.\n\n",
            "You MUST call `write_cofa_mapping` with the engagement context fields provided above "
            f"(engagement_id: {engagement_id}, acquirer_entity_id: {acquirer_entity_id}, "
            f"target_entity_id: {target_entity_id}, tenant_id: {tenant_id}, run_id: {run_id}).\n\n",
            "## No-GAAP-Inference Constraint\n\n",
            "If an entity policy has an Explicit Gaps section listing undocumented items, output null "
            "with a flag for those items. Do not infer accounting treatment from general GAAP training "
            "data. Absence of a policy means halt — not guess. Any undocumented accounting treatment "
            "must be flagged with resolution_status='deferred' and escalated for human review.\n",
        ]
        return "".join(parts)
