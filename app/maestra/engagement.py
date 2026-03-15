"""
Maestra Engagement Manager — manages M&A engagement lifecycle in the Platform layer.

Engagement states: draft -> active -> review -> closed
All state persisted to SQLite (testing) or PostgreSQL (production).
"""

import uuid
import logging
from datetime import datetime, timezone

import aiosqlite

logger = logging.getLogger(__name__)

# Shared default DB path for cross-instance persistence in tests
_DEFAULT_DB_PATH = "/tmp/maestra_platform.db"

VALID_TRANSITIONS = {
    "draft": {"active"},
    "active": {"review"},
    "review": {"closed", "active"},
    "closed": set(),
}


class EngagementManager:
    """
    Manages M&A engagement lifecycle in the Platform layer.

    Engagement states: draft -> active -> review -> closed
    Each engagement has entity_a, entity_b, and a set of enabled modules.
    """

    def __init__(self, db_url: str | None = None):
        """
        Initialize with database connection.
        Uses PG (same as Platform's main DB) or SQLite for testing.
        """
        self._db_path = db_url or _DEFAULT_DB_PATH
        self._initialized = False

    async def _ensure_tables(self) -> None:
        if self._initialized:
            return
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS engagements (
                    engagement_id TEXT PRIMARY KEY,
                    entity_a TEXT NOT NULL,
                    entity_b TEXT NOT NULL,
                    entity_a_name TEXT NOT NULL,
                    entity_b_name TEXT NOT NULL,
                    state TEXT NOT NULL DEFAULT 'draft',
                    created_by TEXT NOT NULL DEFAULT 'system',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            await db.commit()
        self._initialized = True

    async def create_engagement(
        self,
        engagement_id: str,
        entity_a: str,
        entity_b: str,
        entity_a_name: str,
        entity_b_name: str,
        created_by: str = "system",
    ) -> dict:
        """
        Create a new engagement. Initial state = "draft".
        Returns engagement dict.
        """
        await self._ensure_tables()
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                INSERT INTO engagements
                    (engagement_id, entity_a, entity_b, entity_a_name, entity_b_name,
                     state, created_by, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 'draft', ?, ?, ?)
                """,
                (engagement_id, entity_a, entity_b, entity_a_name, entity_b_name,
                 created_by, now, now),
            )
            await db.commit()

        return {
            "engagement_id": engagement_id,
            "entity_a": entity_a,
            "entity_b": entity_b,
            "entity_a_name": entity_a_name,
            "entity_b_name": entity_b_name,
            "state": "draft",
            "created_by": created_by,
            "created_at": now,
            "updated_at": now,
        }

    async def get_engagement(self, engagement_id: str) -> dict:
        """Get engagement by ID. Raises ValueError if not found."""
        await self._ensure_tables()
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM engagements WHERE engagement_id = ?",
                (engagement_id,),
            )
            row = await cursor.fetchone()
        if row is None:
            raise ValueError(
                f"Engagement not found: engagement_id={engagement_id}"
            )
        return dict(row)

    async def update_state(
        self,
        engagement_id: str,
        new_state: str,
        updated_by: str = "system",
    ) -> dict:
        """
        Transition engagement state.
        Valid transitions: draft->active, active->review, review->closed, review->active.
        Raises ValueError on invalid transition.
        """
        eng = await self.get_engagement(engagement_id)
        current = eng["state"]
        allowed = VALID_TRANSITIONS.get(current, set())
        if new_state not in allowed:
            raise ValueError(
                f"invalid transition: cannot move from '{current}' to '{new_state}'. "
                f"Allowed transitions from '{current}': {sorted(allowed) if allowed else 'none'}"
            )
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "UPDATE engagements SET state = ?, updated_at = ? WHERE engagement_id = ?",
                (new_state, now, engagement_id),
            )
            await db.commit()
        eng["state"] = new_state
        eng["updated_at"] = now
        return eng

    async def list_engagements(self, state: str | None = None) -> list[dict]:
        """List all engagements, optionally filtered by state."""
        await self._ensure_tables()
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            if state:
                cursor = await db.execute(
                    "SELECT * FROM engagements WHERE state = ? ORDER BY created_at",
                    (state,),
                )
            else:
                cursor = await db.execute(
                    "SELECT * FROM engagements ORDER BY created_at"
                )
            rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get_active_engagement(self) -> dict | None:
        """Get the currently active engagement (at most one)."""
        results = await self.list_engagements(state="active")
        return results[0] if results else None
