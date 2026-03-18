"""
Maestra Tool Executor — executes tool calls returned by the chat handler.

For write_cofa_mapping: POSTs to DCL and resolves source_run_tag.
Run ledger lifecycle is managed by chat.py (wrapping the full agentic loop),
NOT here — this module only handles the DCL interaction.
"""

import logging
import os

import httpx

logger = logging.getLogger(__name__)

DCL_BASE_URL = os.environ.get("DCL_BASE_URL", "http://localhost:8004")


async def _resolve_source_run_tag(client: httpx.AsyncClient) -> str | None:
    """Fetch the Farm-originated source_run_tag from DCL merge overview.

    Returns the tag string, or None if the merge overview doesn't have one.
    Raises on network/HTTP errors — caller decides whether to tolerate.
    """
    resp = await client.get(f"{DCL_BASE_URL}/api/dcl/merge/overview", timeout=10.0)
    if resp.status_code != 200:
        logger.warning(
            "DCL merge overview returned HTTP %d — source_run_tag unavailable",
            resp.status_code,
        )
        return None
    data = resp.json()
    tag = data.get("source_run_tag")
    if isinstance(tag, str):
        return tag
    if isinstance(tag, dict):
        # Multiple entities — return first non-null tag
        for v in tag.values():
            if v:
                return v
    return None


async def execute_tool_call(
    tool_name: str,
    params: dict,
    engagement_id: str,
) -> dict:
    """Execute a Maestra tool call and return the result."""

    if tool_name == "write_cofa_mapping":
        return await _execute_write_cofa_mapping(params, engagement_id)

    # For other tools, return a not-implemented marker
    return {"status": "not_implemented", "tool": tool_name}


async def _execute_write_cofa_mapping(
    params: dict,
    engagement_id: str,
) -> dict:
    """Execute write_cofa_mapping: POST to DCL, resolve source_run_tag.

    Returns result dict including source_run_tag for chat.py to use
    as outputs_ref when completing the run ledger step.
    """

    run_id = params.get("run_id", "")

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{DCL_BASE_URL}/api/dcl/cofa-mapping",
            json=params,
        )

        if resp.status_code in (200, 201):
            result = resp.json()
            # Resolve the Farm-originated source_run_tag for operator display.
            # Network errors here must not abort the successful COFA write —
            # the tag is optional metadata for the run ledger.
            try:
                source_tag = await _resolve_source_run_tag(client)
            except Exception as exc:
                logger.error(
                    "source_run_tag resolution failed after successful COFA write: "
                    "%s: %s — GET %s/api/dcl/merge/overview",
                    type(exc).__name__, exc, DCL_BASE_URL,
                )
                source_tag = None
            return {
                "status": "success",
                "source_run_tag": source_tag,
                **result,
            }
        else:
            error_detail = resp.text[:500]
            error_msg = (
                f"write_cofa_mapping DCL POST failed: HTTP {resp.status_code} "
                f"— POST {DCL_BASE_URL}/api/dcl/cofa-mapping "
                f"— engagement_id={engagement_id}, run_id={run_id} "
                f"— response: {error_detail}"
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg)
