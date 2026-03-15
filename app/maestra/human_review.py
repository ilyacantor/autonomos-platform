"""
Maestra Human Review Pipeline — 4-tier classification for human review requests.

Tier 1: Auto-approve (low risk, within policy bounds)
Tier 2: Notify (medium risk, proceed but notify stakeholder)
Tier 3: Approve-then-proceed (high risk, block until approved)
Tier 4: Escalate (critical, requires executive review)

All state persisted to Supabase PG (human_reviews table).
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

from app.maestra.db import get_connection, get_tenant_id

logger = logging.getLogger(__name__)

# Action patterns mapped to tiers
_TIER_RULES: list[tuple[int, list[str]]] = [
    (4, ["delete_engagement", "override_constitution", "emergency_shutdown"]),
    (3, ["merge_entities", "approve_cofa", "cross_entity", "modify_raci"]),
    (2, ["update_pipeline", "change_config", "add_module"]),
    (1, ["log_entry", "check_status", "read_data", "view_report"]),
]


class HumanReviewPipeline:
    """
    4-tier classification for human review requests.

    Tier 1: Auto-approve (low risk, within policy bounds)
    Tier 2: Notify (medium risk, proceed but notify stakeholder)
    Tier 3: Approve-then-proceed (high risk, block until approved)
    Tier 4: Escalate (critical, requires executive review)
    """

    def __init__(self):
        pass

    async def classify_review(self, action: str, context: dict) -> dict:
        """
        Classify a review request into a tier.
        Returns: {"tier": int, "classification": str, "reason": str,
                  "auto_action": str | None}
        """
        action_lower = action.lower()
        tier = 2  # default to medium

        for rule_tier, patterns in _TIER_RULES:
            for pattern in patterns:
                if pattern in action_lower:
                    tier = rule_tier
                    break
            else:
                continue
            break

        classifications = {
            1: "auto_approve",
            2: "notify",
            3: "approve_then_proceed",
            4: "escalate",
        }
        reasons = {
            1: "Low-risk action within policy bounds",
            2: "Medium-risk action — proceed with notification",
            3: "High-risk action — requires explicit approval before proceeding",
            4: "Critical action — requires executive review and escalation",
        }
        auto_actions = {
            1: "approved",
            2: None,
            3: None,
            4: None,
        }

        return {
            "tier": tier,
            "classification": classifications[tier],
            "reason": reasons[tier],
            "auto_action": auto_actions[tier],
        }

    async def create_review(
        self,
        engagement_id: str,
        action: str,
        context: dict,
        tier: int,
        requested_by: str = "maestra",
    ) -> dict:
        """
        Create a human review request.
        Tier 1: auto-approved, logged.
        Tier 2-4: pending until human acts.
        Returns: {"review_id": str, "tier": int, "status": str}
        """
        tenant_id = get_tenant_id()
        now = datetime.now(timezone.utc)

        # Tier 1 = auto-approved
        status = "approved" if tier == 1 else "pending"
        resolved_at = now if tier == 1 else None

        def _insert():
            conn = get_connection()
            try:
                with conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            INSERT INTO human_reviews
                                (tenant_id, engagement_id, action, context, tier, status,
                                 requested_by, created_at, resolved_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            RETURNING id
                            """,
                            (tenant_id, engagement_id, action, json.dumps(context),
                             tier, status, requested_by, now, resolved_at),
                        )
                        return str(cur.fetchone()["id"])
            finally:
                conn.close()

        review_id = await asyncio.to_thread(_insert)

        return {
            "review_id": review_id,
            "tier": tier,
            "status": status,
        }

    async def approve_review(self, review_id: str, approved_by: str) -> dict:
        """Approve a pending review. Returns updated review."""
        now = datetime.now(timezone.utc)

        def _update():
            conn = get_connection()
            try:
                with conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            UPDATE human_reviews
                            SET status = 'approved', approved_by = %s, resolved_at = %s
                            WHERE id = %s
                            """,
                            (approved_by, now, review_id),
                        )
            finally:
                conn.close()

        await asyncio.to_thread(_update)
        return await self.get_review(review_id)

    async def reject_review(
        self, review_id: str, rejected_by: str, reason: str
    ) -> dict:
        """Reject a pending review. Returns updated review."""
        now = datetime.now(timezone.utc)

        def _update():
            conn = get_connection()
            try:
                with conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            UPDATE human_reviews
                            SET status = 'rejected', rejected_by = %s,
                                rejection_reason = %s, resolved_at = %s
                            WHERE id = %s
                            """,
                            (rejected_by, reason, now, review_id),
                        )
            finally:
                conn.close()

        await asyncio.to_thread(_update)
        return await self.get_review(review_id)

    async def list_pending_reviews(
        self, engagement_id: str | None = None
    ) -> list[dict]:
        """List all pending reviews."""
        tenant_id = get_tenant_id()

        def _query():
            conn = get_connection()
            try:
                with conn.cursor() as cur:
                    if engagement_id:
                        cur.execute(
                            """
                            SELECT * FROM human_reviews
                            WHERE tenant_id = %s AND status = 'pending' AND engagement_id = %s
                            ORDER BY created_at
                            """,
                            (tenant_id, engagement_id),
                        )
                    else:
                        cur.execute(
                            """
                            SELECT * FROM human_reviews
                            WHERE tenant_id = %s AND status = 'pending'
                            ORDER BY created_at
                            """,
                            (tenant_id,),
                        )
                    return cur.fetchall()
            finally:
                conn.close()

        rows = await asyncio.to_thread(_query)
        return [_review_row_to_dict(r) for r in rows]

    async def get_review(self, review_id: str) -> dict:
        """Get review by ID. Raises ValueError if not found."""
        def _query():
            conn = get_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT * FROM human_reviews WHERE id = %s",
                        (review_id,),
                    )
                    return cur.fetchone()
            finally:
                conn.close()

        row = await asyncio.to_thread(_query)
        if row is None:
            raise ValueError(f"Review not found: review_id={review_id}")
        return _review_row_to_dict(row)


def _review_row_to_dict(row: dict) -> dict:
    """Convert PG human_reviews row to Maestra's API format."""
    context = row.get("context") or {}
    if isinstance(context, str):
        context = json.loads(context)
    return {
        "review_id": str(row["id"]),
        "engagement_id": row["engagement_id"],
        "action": row["action"],
        "context": context,
        "tier": row["tier"],
        "status": row["status"],
        "requested_by": row["requested_by"],
        "approved_by": row.get("approved_by"),
        "rejected_by": row.get("rejected_by"),
        "rejection_reason": row.get("rejection_reason"),
        "created_at": row["created_at"].isoformat() if row.get("created_at") else "",
        "resolved_at": row["resolved_at"].isoformat() if row.get("resolved_at") else None,
    }
