"""
Maestra Engagement Manager — manages M&A engagement lifecycle in the Platform layer.

Engagement states: draft -> active -> review -> closed
All state persisted to Supabase PG (shared engagement_state table with DCL).
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

from app.maestra.db import get_connection, get_tenant_id

logger = logging.getLogger(__name__)

VALID_TRANSITIONS = {
    "draft": {"active"},
    "active": {"review"},
    "review": {"closed", "active"},
    "closed": set(),
}


def _row_to_dict(row: dict) -> dict:
    """Convert PG engagement_state row to Maestra's API format."""
    config = row.get("config") or {}
    if isinstance(config, str):
        config = json.loads(config)
    return {
        "engagement_id": row["engagement_id"],
        "entity_a": row["entity_a_id"],
        "entity_b": row.get("entity_b_id") or "",
        "entity_a_name": config.get("entity_a_name", ""),
        "entity_b_name": config.get("entity_b_name", ""),
        "state": row["status"],
        "created_by": config.get("created_by", "system"),
        "created_at": row["created_at"].isoformat() if row.get("created_at") else "",
        "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else "",
    }


class EngagementManager:
    """
    Manages M&A engagement lifecycle in the Platform layer.

    Engagement states: draft -> active -> review -> closed
    Each engagement has entity_a, entity_b, and a set of enabled modules.
    """

    def __init__(self):
        pass

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
        tenant_id = get_tenant_id()
        now = datetime.now(timezone.utc)
        config = {
            "entity_a_name": entity_a_name,
            "entity_b_name": entity_b_name,
            "created_by": created_by,
        }

        def _insert():
            conn = get_connection()
            try:
                with conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            INSERT INTO engagement_state
                                (tenant_id, engagement_id, entity_a_id, entity_b_id,
                                 status, config, created_at, updated_at)
                            VALUES (%s, %s, %s, %s, 'draft', %s, %s, %s)
                            """,
                            (tenant_id, engagement_id, entity_a, entity_b,
                             json.dumps(config), now, now),
                        )
            finally:
                conn.close()

        await asyncio.to_thread(_insert)

        return {
            "engagement_id": engagement_id,
            "entity_a": entity_a,
            "entity_b": entity_b,
            "entity_a_name": entity_a_name,
            "entity_b_name": entity_b_name,
            "state": "draft",
            "created_by": created_by,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

    async def get_engagement(self, engagement_id: str) -> dict:
        """Get engagement by ID. Raises ValueError if not found."""
        def _query():
            conn = get_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT * FROM engagement_state WHERE engagement_id = %s",
                        (engagement_id,),
                    )
                    return cur.fetchone()
            finally:
                conn.close()

        row = await asyncio.to_thread(_query)
        if row is None:
            raise ValueError(
                f"Engagement not found: engagement_id={engagement_id}"
            )
        return _row_to_dict(row)

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
        now = datetime.now(timezone.utc)

        def _update():
            conn = get_connection()
            try:
                with conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE engagement_state SET status = %s, updated_at = %s WHERE engagement_id = %s",
                            (new_state, now, engagement_id),
                        )
            finally:
                conn.close()

        await asyncio.to_thread(_update)
        eng["state"] = new_state
        eng["updated_at"] = now.isoformat()
        return eng

    async def list_engagements(self, state: str | None = None) -> list[dict]:
        """List all engagements, optionally filtered by state."""
        tenant_id = get_tenant_id()

        def _query():
            conn = get_connection()
            try:
                with conn.cursor() as cur:
                    if state:
                        cur.execute(
                            "SELECT * FROM engagement_state WHERE tenant_id = %s AND status = %s ORDER BY created_at",
                            (tenant_id, state),
                        )
                    else:
                        cur.execute(
                            "SELECT * FROM engagement_state WHERE tenant_id = %s ORDER BY created_at",
                            (tenant_id,),
                        )
                    return cur.fetchall()
            finally:
                conn.close()

        rows = await asyncio.to_thread(_query)
        return [_row_to_dict(r) for r in rows]

    async def get_active_engagement(self) -> dict | None:
        """Get the currently active engagement (at most one)."""
        results = await self.list_engagements(state="active")
        return results[0] if results else None
