"""
Maestra Run Ledger — tracks pipeline run steps with idempotency and downstream invalidation.

Each step has: step_name, status (pending/running/complete/failed),
idempotency_key, inputs_hash, upstream_deps.

All state persisted to Supabase PG (shared run_ledger table with DCL).
"""

import asyncio
import logging
from datetime import datetime, timezone

from app.maestra.db import get_connection, get_tenant_id

logger = logging.getLogger(__name__)


def _row_to_dict(row: dict) -> dict:
    """Convert PG run_ledger row to Maestra's API format."""
    return {
        "step_id": str(row["id"]),
        "engagement_id": row["engagement_id"],
        "step_name": row["step_name"],
        "status": row["status"],
        "idempotency_key": row["idempotency_key"],
        "inputs_hash": row.get("inputs_hash"),
        "upstream_deps": row.get("upstream_deps"),
        "outputs_ref": row.get("outputs_ref"),
        "error": row.get("error"),
        "started_at": row["started_at"].isoformat() if row.get("started_at") else None,
        "completed_at": row["completed_at"].isoformat() if row.get("completed_at") else None,
        "created_at": row["created_at"].isoformat() if row.get("created_at") else "",
    }


class RunLedger:
    """
    Tracks pipeline run steps with idempotency and downstream invalidation.

    Idempotency: if a step with the same idempotency_key already exists
    and inputs_hash matches, skip re-execution.

    Downstream invalidation: when a step completes, find all steps
    whose upstream_deps include this step and mark them as "stale".
    """

    def __init__(self, engagement_id: str):
        self._engagement_id = engagement_id

    async def record_step(
        self,
        step_name: str,
        idempotency_key: str,
        inputs_hash: str,
        upstream_deps: list[str] | None = None,
    ) -> dict:
        """
        Record a pipeline step. If idempotency_key exists and inputs_hash
        matches, return the existing step without re-creating.
        Returns: {"step_id": str, "status": str, "is_new": bool}
        """
        tenant_id = get_tenant_id()
        engagement_id = self._engagement_id

        def _execute():
            conn = get_connection()
            try:
                with conn:
                    with conn.cursor() as cur:
                        # Check for existing step with same idempotency_key
                        cur.execute(
                            "SELECT * FROM run_ledger WHERE idempotency_key = %s AND engagement_id = %s",
                            (idempotency_key, engagement_id),
                        )
                        existing = cur.fetchone()

                        if existing is not None:
                            if existing["inputs_hash"] == inputs_hash:
                                return {
                                    "step_id": str(existing["id"]),
                                    "step_name": existing["step_name"],
                                    "status": existing["status"],
                                    "is_new": False,
                                }
                            # Different hash — update the existing step to pending for re-run
                            cur.execute(
                                "UPDATE run_ledger SET inputs_hash = %s, status = 'pending' WHERE id = %s",
                                (inputs_hash, existing["id"]),
                            )
                            return {
                                "step_id": str(existing["id"]),
                                "step_name": existing["step_name"],
                                "status": "pending",
                                "is_new": False,
                            }

                        # Insert new step
                        now = datetime.now(timezone.utc)
                        cur.execute(
                            """
                            INSERT INTO run_ledger
                                (tenant_id, engagement_id, step_name, status,
                                 idempotency_key, inputs_hash, upstream_deps, created_at)
                            VALUES (%s, %s, %s, 'pending', %s, %s, %s, %s)
                            RETURNING id
                            """,
                            (tenant_id, engagement_id, step_name,
                             idempotency_key, inputs_hash, upstream_deps, now),
                        )
                        new_id = cur.fetchone()["id"]
                        return {
                            "step_id": str(new_id),
                            "step_name": step_name,
                            "status": "pending",
                            "is_new": True,
                        }
            finally:
                conn.close()

        return await asyncio.to_thread(_execute)

    async def start_step(self, step_id: str) -> dict:
        """Mark step as running. Records started_at."""
        now = datetime.now(timezone.utc)

        def _update():
            conn = get_connection()
            try:
                with conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE run_ledger SET status = 'running', started_at = %s WHERE id = %s",
                            (now, step_id),
                        )
            finally:
                conn.close()

        await asyncio.to_thread(_update)
        return await self.get_step(step_id)

    async def complete_step(self, step_id: str, outputs_ref: str | None = None) -> dict:
        """
        Mark step as complete. Records completed_at.
        TRIGGERS downstream invalidation.
        """
        now = datetime.now(timezone.utc)

        def _update():
            conn = get_connection()
            try:
                with conn:
                    with conn.cursor() as cur:
                        if outputs_ref:
                            cur.execute(
                                "UPDATE run_ledger SET status = 'complete', completed_at = %s, outputs_ref = %s WHERE id = %s",
                                (now, outputs_ref, step_id),
                            )
                        else:
                            cur.execute(
                                "UPDATE run_ledger SET status = 'complete', completed_at = %s WHERE id = %s",
                                (now, step_id),
                            )
            finally:
                conn.close()

        await asyncio.to_thread(_update)
        await self.invalidate_downstream(step_id)
        return await self.get_step(step_id)

    async def fail_step(self, step_id: str, error: str) -> dict:
        """Mark step as failed with error message."""
        now = datetime.now(timezone.utc)

        def _update():
            conn = get_connection()
            try:
                with conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE run_ledger SET status = 'failed', completed_at = %s, error = %s WHERE id = %s",
                            (now, error, step_id),
                        )
            finally:
                conn.close()

        await asyncio.to_thread(_update)
        return await self.get_step(step_id)

    async def get_step(self, step_id: str) -> dict:
        """Get step by ID."""
        def _query():
            conn = get_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT * FROM run_ledger WHERE id = %s",
                        (step_id,),
                    )
                    return cur.fetchone()
            finally:
                conn.close()

        row = await asyncio.to_thread(_query)
        if row is None:
            raise ValueError(f"Step not found: step_id={step_id}")
        return _row_to_dict(row)

    async def list_steps(self, status: str | None = None) -> list[dict]:
        """List steps, optionally by status."""
        def _query():
            conn = get_connection()
            try:
                with conn.cursor() as cur:
                    if status:
                        cur.execute(
                            "SELECT * FROM run_ledger WHERE engagement_id = %s AND status = %s ORDER BY created_at",
                            (self._engagement_id, status),
                        )
                    else:
                        cur.execute(
                            "SELECT * FROM run_ledger WHERE engagement_id = %s ORDER BY created_at",
                            (self._engagement_id,),
                        )
                    return cur.fetchall()
            finally:
                conn.close()

        rows = await asyncio.to_thread(_query)
        return [_row_to_dict(r) for r in rows]

    async def get_stale_steps(self) -> list[dict]:
        """Get all steps marked as stale (need re-execution)."""
        return await self.list_steps(status="stale")

    async def invalidate_downstream(self, step_id: str) -> int:
        """
        Find and mark stale all steps that depend on step_id.
        Returns count of invalidated steps.
        """
        def _invalidate():
            conn = get_connection()
            try:
                with conn:
                    with conn.cursor() as cur:
                        # Find steps with upstream_deps containing this step_id
                        cur.execute(
                            """
                            UPDATE run_ledger
                            SET status = 'stale'
                            WHERE engagement_id = %s
                              AND upstream_deps IS NOT NULL
                              AND %s = ANY(upstream_deps)
                            """,
                            (self._engagement_id, step_id),
                        )
                        return cur.rowcount
            finally:
                conn.close()

        return await asyncio.to_thread(_invalidate)
