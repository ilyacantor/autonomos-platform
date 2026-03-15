"""
Maestra Chat — Platform-layer orchestration chat.

This is different from NLQ's Maestra chat (which handles data queries).
Platform Maestra handles: engagement management, pipeline orchestration,
module health, human review requests.
"""

import logging

from app.maestra.engagement import EngagementManager
from app.maestra.run_ledger import RunLedger
from app.maestra.constitution import Constitution

logger = logging.getLogger(__name__)


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
        }
