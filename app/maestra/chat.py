"""
Maestra Chat — Platform-layer orchestration chat.

This is different from NLQ's Maestra chat (which handles data queries).
Platform Maestra handles: engagement management, pipeline orchestration,
module health, human review requests.
"""

import logging
import time
import uuid
from pathlib import Path

import asyncio

from app.agentic.gateway.client import ModelTier, get_ai_gateway
from app.maestra.db import get_connection, get_tenant_id
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

# Maximum agentic loop iterations (tool call → result → re-call).
# COFA mapping should complete in 1-2 iterations (tool call + final response).
# 3 iterations provides one retry if first attempt is incomplete.
_MAX_TOOL_ITERATIONS = 3


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


def _load_coa_accounts_from_db(entity_id: str) -> list[dict]:
    """Load CoA accounts from the shared Supabase DB for a given entity.

    Returns a list of dicts with account_number and account_name.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT split_part(concept, '.', 2) AS acct_num, "
                "       value #>> '{}' AS acct_name "
                "FROM semantic_triples "
                "WHERE concept LIKE 'coa.%%' AND entity_id = %(eid)s "
                "  AND property = 'account_name' AND is_active = true "
                "ORDER BY split_part(concept, '.', 2)",
                {"eid": entity_id},
            )
            return [
                {
                    "account_number": row["acct_num"],
                    "account_name": row["acct_name"].strip('"'),
                }
                for row in cur.fetchall()
            ]
    finally:
        conn.close()


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
        tenant_id = get_tenant_id()

        # Load CoA accounts from DCL's DB so Maestra knows every account to cover
        acquirer_coa = await asyncio.to_thread(
            _load_coa_accounts_from_db, acquirer_entity_id
        )
        target_coa = await asyncio.to_thread(
            _load_coa_accounts_from_db, target_entity_id
        )
        logger.info(
            "Loaded CoA accounts from DB: acquirer=%d, target=%d",
            len(acquirer_coa), len(target_coa),
        )

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
            acquirer_coa=acquirer_coa,
            target_coa=target_coa,
        )

        # Get tools — only write_cofa_mapping for COFA unification context
        tools = self._tools.get_tools(filter_names=["write_cofa_mapping"])

        # Initialize AI Gateway
        gateway = await get_ai_gateway()

        # Build conversation messages
        messages = [{"role": "user", "content": message}]

        merge_t0 = time.monotonic()

        logger.info(
            "Maestra COFA unification starting — engagement=%s, run_id=%s, "
            "acquirer=%s (%d accts), target=%s (%d accts)",
            engagement_id, run_id, acquirer_entity_id, len(acquirer_coa),
            target_entity_id, len(target_coa),
        )

        # Agentic loop: call LLM, execute tools, feed results back.
        # COFA should complete in 1 LLM call (tool call) + 1 follow-up (text).
        # max_tokens=16000 ensures the full mapping JSON fits without truncation.
        for iteration in range(_MAX_TOOL_ITERATIONS):
            llm_t0 = time.monotonic()
            response = await gateway.complete(
                messages=messages,
                model_tier=ModelTier.BALANCED,
                tools=tools,
                system=system_prompt,
                temperature=0.0,
                max_tokens=16000,
                use_cache=False,
            )
            llm_elapsed = time.monotonic() - llm_t0

            logger.info(
                "Maestra LLM call — iteration=%d, stop_reason=%s, "
                "tool_calls=%d, model=%s, tokens_in=%d, tokens_out=%d, "
                "llm_wall_sec=%.1f, total_wall_sec=%.1f",
                iteration, response.stop_reason, len(response.tool_calls),
                response.model, response.input_tokens, response.output_tokens,
                llm_elapsed, time.monotonic() - merge_t0,
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
                    tool_t0 = time.monotonic()
                    tool_result = await execute_tool_call(
                        tool_name=tool_name,
                        params=tool_params,
                        engagement_id=engagement_id,
                        run_ledger=self._run_ledger,
                    )
                    logger.info(
                        "Maestra tool executed — tool=%s, status=%s, "
                        "tool_wall_sec=%.1f, total_wall_sec=%.1f",
                        tool_name, tool_result.get("status", "unknown"),
                        time.monotonic() - tool_t0, time.monotonic() - merge_t0,
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

            # Append tool results to messages for next LLM iteration
            messages.append({"role": "user", "content": tool_results_for_message})
        else:
            # Exhausted max iterations — this is not a silent fallback, we report it
            logger.warning(
                "Maestra agentic loop exhausted %d iterations — "
                "engagement=%s, run_id=%s, total_wall_sec=%.1f",
                _MAX_TOOL_ITERATIONS, engagement_id, run_id,
                time.monotonic() - merge_t0,
            )

        total_elapsed = time.monotonic() - merge_t0
        logger.info(
            "Maestra COFA unification complete — engagement=%s, run_id=%s, "
            "iterations=%d, tool_calls=%d, total_wall_sec=%.1f",
            engagement_id, run_id, iteration + 1,
            len(tool_call_results), total_elapsed,
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
        acquirer_coa: list[dict] | None = None,
        target_coa: list[dict] | None = None,
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
        ]

        # Inject CoA account lists from DCL as numbered tables for efficient LLM processing
        if acquirer_coa:
            acct_lines = "\n".join(
                f"  {i+1}. {a['account_name']}" for i, a in enumerate(acquirer_coa)
            )
            parts.append(
                f"\n\n# Acquirer CoA ({acquirer_entity_id}) — "
                f"{len(acquirer_coa)} accounts\n"
                f"{acct_lines}\n"
            )

        if target_coa:
            acct_lines = "\n".join(
                f"  {i+1}. {a['account_name']}" for i, a in enumerate(target_coa)
            )
            parts.append(
                f"\n\n# Target CoA ({target_entity_id}) — "
                f"{len(target_coa)} accounts\n"
                f"{acct_lines}\n"
            )

        parts.extend([
            "\n# CRITICAL: Single-Call COFA Unification\n\n",
            "You MUST produce the ENTIRE COFA mapping in ONE `write_cofa_mapping` tool call. "
            "Do NOT output any reasoning text before the tool call — the tool call IS the deliverable.\n\n",
            "## Tool Call Parameters (pre-filled)\n\n",
            f"- engagement_id: \"{engagement_id}\"\n",
            f"- acquirer_entity_id: \"{acquirer_entity_id}\"\n",
            f"- target_entity_id: \"{target_entity_id}\"\n",
            f"- tenant_id: \"{tenant_id}\"\n",
            f"- run_id: \"{run_id}\"\n\n",
            "## Mapping Rules\n\n",
            "- EVERY account from BOTH CoA lists must appear in mappings[]. The COFACompletionGate rejects orphans.\n",
            "- Use exact account_name strings from the lists above.\n",
            "- Entity-specific accounts with no counterpart: use null for the other side.\n",
            "- Many-to-one mappings allowed (multiple source accounts → one unified account).\n",
            "- Keep mapping_basis values SHORT (e.g. \"exact match\", \"semantic: both are revenue\", \"hierarchy: subcategory\").\n\n",
            "## Conflict Detection\n\n",
            "- Identify conflicts from the entity policies (recognition timing, measurement basis, classification, scope).\n",
            "- Each conflict needs: conflict_id (COFA-NNN), conflict_type, severity, dollar_impact, description, "
            "acquirer_treatment, target_treatment, resolution_status (\"unresolved\").\n",
            "- If an entity policy has Explicit Gaps, flag those items with resolution_status=\"deferred\".\n",
            "- Do NOT infer accounting treatment from general GAAP training data. Absence of policy = halt, not guess.\n\n",
            "## Output Compactness\n\n",
            "- No reasoning text. No explanation. Just the tool call.\n",
            "- Keep description strings under 80 characters.\n",
            "- Use concise mapping_basis values.\n",
        ])
        return "".join(parts)
