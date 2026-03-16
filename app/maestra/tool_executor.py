"""
Maestra Tool Executor — executes tool calls returned by the chat handler.

For write_cofa_mapping: POSTs to DCL and logs to run ledger.
"""

import hashlib
import logging
import os

import httpx

from app.maestra.run_ledger import RunLedger

logger = logging.getLogger(__name__)

DCL_BASE_URL = os.environ.get("DCL_BASE_URL", "http://localhost:8004")


async def execute_tool_call(
    tool_name: str,
    params: dict,
    engagement_id: str,
    run_ledger: RunLedger,
) -> dict:
    """Execute a Maestra tool call and return the result."""

    if tool_name == "write_cofa_mapping":
        return await _execute_write_cofa_mapping(params, engagement_id, run_ledger)

    # For other tools, return a not-implemented marker
    return {"status": "not_implemented", "tool": tool_name}


async def _execute_write_cofa_mapping(
    params: dict,
    engagement_id: str,
    run_ledger: RunLedger,
) -> dict:
    """Execute write_cofa_mapping: POST to DCL and log to run ledger."""

    run_id = params.get("run_id", "")
    idempotency_key = f"{engagement_id}:cofa-map:{run_id}"
    inputs_hash = hashlib.sha256(
        str(sorted(params.items())).encode()
    ).hexdigest()[:16]

    # Record step as pending, then start it
    step = await run_ledger.record_step(
        step_name="cofa-map",
        idempotency_key=idempotency_key,
        inputs_hash=inputs_hash,
        upstream_deps=["ingest"],
    )
    step_id = step["step_id"]
    await run_ledger.start_step(step_id)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{DCL_BASE_URL}/api/dcl/cofa-mapping",
                json=params,
            )

        if resp.status_code in (200, 201):
            result = resp.json()
            await run_ledger.complete_step(
                step_id,
                outputs_ref=f"semantic_triples:run_id={run_id}",
            )
            return {
                "status": "success",
                "step_id": step_id,
                **result,
            }
        else:
            error_detail = resp.text[:500]
            await run_ledger.fail_step(step_id, error_detail)
            return {
                "status": "failed",
                "step_id": step_id,
                "error": error_detail,
                "http_status": resp.status_code,
            }

    except Exception as e:
        error_msg = (
            f"write_cofa_mapping failed: {type(e).__name__}: {e} "
            f"— POST {DCL_BASE_URL}/api/dcl/cofa-mapping "
            f"— engagement_id={engagement_id}, run_id={run_id}"
        )
        logger.error(error_msg)
        await run_ledger.fail_step(step_id, error_msg)
        raise  # Do NOT swallow — HARNESS_RULES A1
