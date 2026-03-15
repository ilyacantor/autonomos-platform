"""
Maestra Run Ledger — tracks pipeline run steps with idempotency and downstream invalidation.

Each step has: step_name, status (pending/running/complete/failed),
idempotency_key, inputs_hash, upstream_deps.

All state persisted to SQLite (testing) or PostgreSQL (production).
"""

import json
import uuid
import logging
from datetime import datetime, timezone

import aiosqlite

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = "/tmp/maestra_platform.db"


class RunLedger:
    """
    Tracks pipeline run steps with idempotency and downstream invalidation.

    Idempotency: if a step with the same idempotency_key already exists
    and inputs_hash matches, skip re-execution.

    Downstream invalidation: when a step completes, find all steps
    whose upstream_deps include this step and mark them as "stale".
    """

    def __init__(self, engagement_id: str, db_url: str | None = None):
        self._engagement_id = engagement_id
        self._db_path = db_url or _DEFAULT_DB_PATH
        self._initialized = False

    async def _ensure_tables(self) -> None:
        if self._initialized:
            return
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS run_ledger_steps (
                    step_id TEXT PRIMARY KEY,
                    engagement_id TEXT NOT NULL,
                    step_name TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    idempotency_key TEXT NOT NULL,
                    inputs_hash TEXT NOT NULL,
                    upstream_deps TEXT,
                    outputs_ref TEXT,
                    error TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            await db.commit()
        self._initialized = True

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
        await self._ensure_tables()
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM run_ledger_steps WHERE idempotency_key = ? AND engagement_id = ?",
                (idempotency_key, self._engagement_id),
            )
            existing = await cursor.fetchone()

            if existing is not None:
                existing_dict = dict(existing)
                if existing_dict["inputs_hash"] == inputs_hash:
                    return {
                        "step_id": existing_dict["step_id"],
                        "step_name": existing_dict["step_name"],
                        "status": existing_dict["status"],
                        "is_new": False,
                    }
                # Different hash — update the existing step to pending for re-run
                await db.execute(
                    "UPDATE run_ledger_steps SET inputs_hash = ?, status = 'pending' WHERE step_id = ?",
                    (inputs_hash, existing_dict["step_id"]),
                )
                await db.commit()
                return {
                    "step_id": existing_dict["step_id"],
                    "step_name": existing_dict["step_name"],
                    "status": "pending",
                    "is_new": False,
                }

            step_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc).isoformat()
            deps_json = json.dumps(upstream_deps) if upstream_deps else None

            await db.execute(
                """
                INSERT INTO run_ledger_steps
                    (step_id, engagement_id, step_name, status, idempotency_key,
                     inputs_hash, upstream_deps, created_at)
                VALUES (?, ?, ?, 'pending', ?, ?, ?, ?)
                """,
                (step_id, self._engagement_id, step_name, idempotency_key,
                 inputs_hash, deps_json, now),
            )
            await db.commit()

        return {
            "step_id": step_id,
            "step_name": step_name,
            "status": "pending",
            "is_new": True,
        }

    async def start_step(self, step_id: str) -> dict:
        """Mark step as running. Records started_at."""
        await self._ensure_tables()
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "UPDATE run_ledger_steps SET status = 'running', started_at = ? WHERE step_id = ?",
                (now, step_id),
            )
            await db.commit()
        return await self.get_step(step_id)

    async def complete_step(self, step_id: str, outputs_ref: str | None = None) -> dict:
        """
        Mark step as complete. Records completed_at.
        TRIGGERS downstream invalidation.
        """
        await self._ensure_tables()
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self._db_path) as db:
            if outputs_ref:
                await db.execute(
                    "UPDATE run_ledger_steps SET status = 'complete', completed_at = ?, outputs_ref = ? WHERE step_id = ?",
                    (now, outputs_ref, step_id),
                )
            else:
                await db.execute(
                    "UPDATE run_ledger_steps SET status = 'complete', completed_at = ? WHERE step_id = ?",
                    (now, step_id),
                )
            await db.commit()

        await self.invalidate_downstream(step_id)
        return await self.get_step(step_id)

    async def fail_step(self, step_id: str, error: str) -> dict:
        """Mark step as failed with error message."""
        await self._ensure_tables()
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "UPDATE run_ledger_steps SET status = 'failed', completed_at = ?, error = ? WHERE step_id = ?",
                (now, error, step_id),
            )
            await db.commit()
        return await self.get_step(step_id)

    async def get_step(self, step_id: str) -> dict:
        """Get step by ID."""
        await self._ensure_tables()
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM run_ledger_steps WHERE step_id = ?",
                (step_id,),
            )
            row = await cursor.fetchone()
        if row is None:
            raise ValueError(f"Step not found: step_id={step_id}")
        return dict(row)

    async def list_steps(self, status: str | None = None) -> list[dict]:
        """List steps, optionally by status."""
        await self._ensure_tables()
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            if status:
                cursor = await db.execute(
                    "SELECT * FROM run_ledger_steps WHERE engagement_id = ? AND status = ? ORDER BY created_at",
                    (self._engagement_id, status),
                )
            else:
                cursor = await db.execute(
                    "SELECT * FROM run_ledger_steps WHERE engagement_id = ? ORDER BY created_at",
                    (self._engagement_id,),
                )
            rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get_stale_steps(self) -> list[dict]:
        """Get all steps marked as stale (need re-execution)."""
        return await self.list_steps(status="stale")

    async def invalidate_downstream(self, step_id: str) -> int:
        """
        Find and mark stale all steps that depend on step_id.
        Returns count of invalidated steps.
        """
        await self._ensure_tables()
        count = 0
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            # Find all steps in this engagement that have upstream_deps containing step_id
            cursor = await db.execute(
                "SELECT * FROM run_ledger_steps WHERE engagement_id = ? AND upstream_deps IS NOT NULL",
                (self._engagement_id,),
            )
            rows = await cursor.fetchall()
            for row in rows:
                deps = json.loads(row["upstream_deps"])
                if step_id in deps:
                    await db.execute(
                        "UPDATE run_ledger_steps SET status = 'stale' WHERE step_id = ?",
                        (row["step_id"],),
                    )
                    count += 1
            await db.commit()
        return count
