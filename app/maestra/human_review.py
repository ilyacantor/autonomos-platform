"""
Maestra Human Review Pipeline — 4-tier classification for human review requests.

Tier 1: Auto-approve (low risk, within policy bounds)
Tier 2: Notify (medium risk, proceed but notify stakeholder)
Tier 3: Approve-then-proceed (high risk, block until approved)
Tier 4: Escalate (critical, requires executive review)

All state persisted to SQLite (testing) or PostgreSQL (production).
"""

import uuid
import logging
from datetime import datetime, timezone

import aiosqlite

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = "/tmp/maestra_platform.db"

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

    def __init__(self, db_url: str | None = None):
        self._db_path = db_url or _DEFAULT_DB_PATH
        self._initialized = False

    async def _ensure_tables(self) -> None:
        if self._initialized:
            return
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS human_reviews (
                    review_id TEXT PRIMARY KEY,
                    engagement_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    context TEXT NOT NULL DEFAULT '{}',
                    tier INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    requested_by TEXT NOT NULL DEFAULT 'maestra',
                    approved_by TEXT,
                    rejected_by TEXT,
                    rejection_reason TEXT,
                    created_at TEXT NOT NULL,
                    resolved_at TEXT
                )
            """)
            await db.commit()
        self._initialized = True

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
        await self._ensure_tables()
        import json

        review_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        # Tier 1 = auto-approved
        status = "approved" if tier == 1 else "pending"
        resolved_at = now if tier == 1 else None

        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                INSERT INTO human_reviews
                    (review_id, engagement_id, action, context, tier, status,
                     requested_by, created_at, resolved_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (review_id, engagement_id, action, json.dumps(context),
                 tier, status, requested_by, now, resolved_at),
            )
            await db.commit()

        return {
            "review_id": review_id,
            "tier": tier,
            "status": status,
        }

    async def approve_review(self, review_id: str, approved_by: str) -> dict:
        """Approve a pending review. Returns updated review."""
        await self._ensure_tables()
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                UPDATE human_reviews
                SET status = 'approved', approved_by = ?, resolved_at = ?
                WHERE review_id = ?
                """,
                (approved_by, now, review_id),
            )
            await db.commit()
        return await self.get_review(review_id)

    async def reject_review(
        self, review_id: str, rejected_by: str, reason: str
    ) -> dict:
        """Reject a pending review. Returns updated review."""
        await self._ensure_tables()
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                UPDATE human_reviews
                SET status = 'rejected', rejected_by = ?, rejection_reason = ?, resolved_at = ?
                WHERE review_id = ?
                """,
                (rejected_by, reason, now, review_id),
            )
            await db.commit()
        return await self.get_review(review_id)

    async def list_pending_reviews(
        self, engagement_id: str | None = None
    ) -> list[dict]:
        """List all pending reviews."""
        await self._ensure_tables()
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            if engagement_id:
                cursor = await db.execute(
                    "SELECT * FROM human_reviews WHERE status = 'pending' AND engagement_id = ? ORDER BY created_at",
                    (engagement_id,),
                )
            else:
                cursor = await db.execute(
                    "SELECT * FROM human_reviews WHERE status = 'pending' ORDER BY created_at"
                )
            rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get_review(self, review_id: str) -> dict:
        """Get review by ID. Raises ValueError if not found."""
        await self._ensure_tables()
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM human_reviews WHERE review_id = ?",
                (review_id,),
            )
            row = await cursor.fetchone()
        if row is None:
            raise ValueError(f"Review not found: review_id={review_id}")
        return dict(row)
