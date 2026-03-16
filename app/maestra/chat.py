"""
Maestra Chat — Platform-layer orchestration chat.

This is different from NLQ's Maestra chat (which handles data queries).
Platform Maestra handles: engagement management, pipeline orchestration,
module health, human review requests.
"""

import logging
from pathlib import Path

from app.maestra.engagement import EngagementManager
from app.maestra.run_ledger import RunLedger
from app.maestra.constitution import Constitution

logger = logging.getLogger(__name__)

# Layer 3 entity policy documents directory
_POLICIES_DIR = Path(__file__).parent / "constitution" / "policies"


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

    async def process_message(
        self,
        message: str,
        engagement_id: str,
        session_id: str,
    ) -> dict:
        """
        Process a user message in the Maestra orchestration context.

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

        tool_calls: list[dict] = []
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

        # Load Layer 3 entity policy documents for context assembly.
        # These inject AFTER Layers 0-2 (constitution, P&L/BS rules, COFA ontology)
        # and BEFORE Layer 4 (industry profile), per v7 §3.4.
        entity_policies = load_entity_policies(
            engagement.get("entity_a", ""),
            engagement.get("entity_b", ""),
        )

        response = (
            f"Acknowledged. Engagement '{engagement['engagement_id']}' "
            f"is in state '{engagement['state']}'. "
            f"Processing: {message}"
        )

        return {
            "response": response,
            "tool_calls": tool_calls,
            "requires_review": requires_review,
            "review_items": review_items,
            "context_layers": {
                "layer_3_entity_policies": entity_policies,
            },
        }
