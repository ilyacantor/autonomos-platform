"""
Maestra API Routes — mount at /api/maestra

Provides endpoints for engagement lifecycle, run ledger, constitution,
chat (general context-aware + COFA-specific), and human review.
"""

import json
import logging
import os
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

import httpx

from app.maestra.engagement import EngagementManager
from app.maestra.run_ledger import RunLedger
from app.maestra.constitution import Constitution
from app.maestra.tools import MaestraTools
from app.maestra.human_review import HumanReviewPipeline
from app.maestra.chat import MaestraChat
from app.maestra.assembler import assemble_prompt_async
from app.agentic.gateway.client import ModelTier, get_ai_gateway

DCL_BASE_URL = os.environ.get("DCL_BASE_URL", "http://localhost:8004")

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/maestra", tags=["Maestra Orchestration"])

# Module-level singletons
_engagement_mgr = EngagementManager()
_constitution = Constitution()
_tools = MaestraTools()
_review_pipeline = HumanReviewPipeline()


# ============================================================================
# Request/Response Models
# ============================================================================

class CreateEngagementRequest(BaseModel):
    engagement_id: str
    entity_a: str
    entity_b: str
    entity_a_name: str
    entity_b_name: str
    created_by: str = "system"


class UpdateStateRequest(BaseModel):
    new_state: str
    updated_by: str = "system"


class RecordStepRequest(BaseModel):
    step_name: str
    idempotency_key: str
    inputs_hash: str
    upstream_deps: list[str] | None = None


class UpdateStepRequest(BaseModel):
    status: str
    outputs_ref: str | None = None
    error: str | None = None


class ContextChatRequest(BaseModel):
    """Request for general-purpose Maestra context-aware chat (WP-1)."""
    message: str
    module_context: str | None = None
    session_id: str


class ChatRequest(BaseModel):
    """Request for COFA engagement-specific chat."""
    message: str
    engagement_id: str
    session_id: str


class CreateReviewRequest(BaseModel):
    engagement_id: str
    action: str
    context: dict = Field(default_factory=dict)
    tier: int
    requested_by: str = "maestra"


class ReviewActionRequest(BaseModel):
    approved_by: str | None = None
    rejected_by: str | None = None
    reason: str | None = None


class ReviewDecideRequest(BaseModel):
    decision: str  # "approve" or "reject"
    reasoning: str
    decided_by: str = "operator"


# ============================================================================
# Engagement Endpoints
# ============================================================================

@router.post("/engagements")
async def create_engagement(req: CreateEngagementRequest):
    """Create a new M&A engagement."""
    try:
        result = await _engagement_mgr.create_engagement(
            req.engagement_id, req.entity_a, req.entity_b,
            req.entity_a_name, req.entity_b_name, req.created_by,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/engagements")
async def list_engagements(state: str | None = None):
    """List all engagements, optionally filtered by state."""
    return await _engagement_mgr.list_engagements(state=state)


@router.get("/engagements/active")
async def get_active_engagement():
    """Get the currently active engagement."""
    result = await _engagement_mgr.get_active_engagement()
    if result is None:
        raise HTTPException(status_code=404, detail="No active engagement found")
    return result


@router.get("/engagements/{engagement_id}")
async def get_engagement(engagement_id: str):
    """Get engagement by ID."""
    try:
        return await _engagement_mgr.get_engagement(engagement_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/engagements/{engagement_id}/state")
async def update_engagement_state(engagement_id: str, req: UpdateStateRequest):
    """Transition engagement state."""
    try:
        return await _engagement_mgr.update_state(
            engagement_id, req.new_state, req.updated_by,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Run Ledger Endpoints
# ============================================================================

@router.get("/run-ledger")
async def list_all_ledger_steps(status: str | None = None):
    """List run ledger steps across all engagements."""
    engagements = await _engagement_mgr.list_engagements()
    all_steps = []
    for eng in engagements:
        eid = eng.get("engagement_id") or eng.get("id")
        if not eid:
            continue
        ledger = RunLedger(str(eid))
        steps = await ledger.list_steps(status=status)
        all_steps.extend(steps)
    return all_steps


@router.get("/run-ledger/{engagement_id}")
async def list_ledger_steps(engagement_id: str, status: str | None = None):
    """List run ledger steps for an engagement."""
    ledger = RunLedger(engagement_id)
    return await ledger.list_steps(status=status)


@router.post("/run-ledger/{engagement_id}/steps")
async def record_ledger_step(engagement_id: str, req: RecordStepRequest):
    """Record a pipeline step."""
    ledger = RunLedger(engagement_id)
    return await ledger.record_step(
        req.step_name, req.idempotency_key, req.inputs_hash,
        req.upstream_deps,
    )


@router.patch("/run-ledger/steps/{step_id}")
async def update_ledger_step(step_id: str, req: UpdateStepRequest):
    """Update a step's status with downstream invalidation.

    When status transitions to 'complete' or 'failed', downstream steps
    that depend on this step are marked as 'stale'.
    """
    # Look up the step to find its engagement_id
    import asyncio
    from app.maestra.db import get_connection

    def _find_engagement():
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT engagement_id FROM run_ledger WHERE id = %s",
                    (step_id,),
                )
                row = cur.fetchone()
                return row["engagement_id"] if row else None
        finally:
            conn.close()

    engagement_id = await asyncio.to_thread(_find_engagement)
    if engagement_id is None:
        raise HTTPException(
            status_code=404,
            detail=f"Step not found: step_id={step_id}",
        )

    ledger = RunLedger(engagement_id)

    if req.status == "running":
        return await ledger.start_step(step_id)
    elif req.status == "complete":
        return await ledger.complete_step(step_id, outputs_ref=req.outputs_ref)
    elif req.status == "failed":
        if not req.error:
            raise HTTPException(
                status_code=400,
                detail="error field is required when setting status to 'failed'",
            )
        return await ledger.fail_step(step_id, req.error)
    elif req.status == "stale":
        # Manual downstream invalidation
        def _mark_stale():
            conn = get_connection()
            try:
                with conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE run_ledger SET status = 'stale' WHERE id = %s",
                            (step_id,),
                        )
            finally:
                conn.close()
        await asyncio.to_thread(_mark_stale)
        return await ledger.get_step(step_id)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status: '{req.status}'. Must be one of: running, complete, failed, stale",
        )


# ============================================================================
# Chat Endpoint — General-purpose context-aware (WP-1)
# ============================================================================

@router.post("/chat")
async def maestra_context_chat(req: ContextChatRequest):
    """General-purpose Maestra chat with context assembly.

    Assembles constitution + module doc + triple store data into a grounded
    prompt, sends to Claude via the existing AI Gateway, and streams the
    response back as Server-Sent Events.
    """
    # Assemble the full context prompt (constitution + module doc + triples).
    system_prompt, matched_domains, entity_id = await assemble_prompt_async(
        req.message, req.module_context,
    )

    logger.info(
        "Maestra context chat — session=%s, module=%s, domains=%s, entity=%s",
        req.session_id, req.module_context, matched_domains, entity_id,
    )

    # Call Claude via the existing AI Gateway (reuses Platform's LLM infra).
    gateway = await get_ai_gateway()
    response = await gateway.complete(
        messages=[{"role": "user", "content": req.message}],
        system=system_prompt,
        model_tier=ModelTier.BALANCED,
        temperature=0.3,
        max_tokens=4096,
        use_cache=False,
    )

    logger.info(
        "Maestra LLM response — model=%s, tokens_in=%d, tokens_out=%d, "
        "latency=%dms",
        response.model, response.input_tokens, response.output_tokens,
        response.latency_ms,
    )

    async def generate_sse() -> AsyncGenerator[str, None]:
        """Yield SSE events for the Maestra response."""
        yield f"data: {json.dumps({'type': 'content', 'text': response.content})}\n\n"
        yield (
            f"data: {json.dumps({'type': 'done', 'model': response.model, 'domains': matched_domains, 'entity': entity_id, 'tokens': {'input': response.input_tokens, 'output': response.output_tokens}})}\n\n"
        )

    return StreamingResponse(
        generate_sse(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ============================================================================
# COFA Chat Endpoint — Engagement-specific
# ============================================================================

@router.post("/cofa-chat")
async def maestra_cofa_chat(req: ChatRequest):
    """Process a message in the Maestra COFA unification context.

    This is the engagement-specific chat that drives COFA mapping with tools.
    Requires an active engagement with entity_a and entity_b.
    """
    try:
        engagement = await _engagement_mgr.get_engagement(req.engagement_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    ledger = RunLedger(req.engagement_id)
    chat = MaestraChat(_engagement_mgr, ledger, _constitution)
    try:
        return await chat.process_message(req.message, req.engagement_id, req.session_id)
    except httpx.ConnectError as e:
        raise HTTPException(
            status_code=502,
            detail=(
                f"Cannot reach DCL at {DCL_BASE_URL} — {e}. "
                f"Check DCL_BASE_URL environment variable."
            ),
        )
    except httpx.TimeoutException as e:
        raise HTTPException(
            status_code=504,
            detail=f"DCL request timed out at {DCL_BASE_URL} — {e}",
        )


# ============================================================================
# Constitution Endpoint
# ============================================================================

@router.get("/constitution")
async def get_constitution():
    """Get constitution rules."""
    return {
        "rules": _constitution.get_rules(),
        "count": len(_constitution.get_rules()),
    }


# ============================================================================
# Human Review Endpoints
# ============================================================================

@router.post("/reviews")
async def create_review(req: CreateReviewRequest):
    """Create a human review request."""
    return await _review_pipeline.create_review(
        req.engagement_id, req.action, req.context, req.tier, req.requested_by,
    )


@router.get("/reviews")
async def list_reviews(
    engagement_id: str | None = None,
    status: str | None = None,
):
    """List reviews, optionally filtered."""
    if status == "pending" or status is None:
        return await _review_pipeline.list_pending_reviews(engagement_id)
    raise HTTPException(status_code=400, detail=f"Unsupported status filter: {status}")


@router.get("/review-queue")
async def review_queue(engagement_id: str | None = None):
    """Get pending reviews (spec-aligned alias for GET /reviews?status=pending)."""
    return await _review_pipeline.list_pending_reviews(engagement_id)


@router.post("/review/{review_id}/decide")
async def decide_review(review_id: str, req: ReviewDecideRequest):
    """Unified review decision endpoint. Accepts {decision: "approve"|"reject", reasoning: "..."}."""
    if req.decision not in ("approve", "reject"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid decision: '{req.decision}'. Must be 'approve' or 'reject'.",
        )

    try:
        if req.decision == "approve":
            return await _review_pipeline.approve_review(review_id, req.decided_by)
        else:
            return await _review_pipeline.reject_review(review_id, req.decided_by, req.reasoning)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/reviews/{review_id}/approve")
async def approve_review(review_id: str, req: ReviewActionRequest):
    """Approve a pending review."""
    if not req.approved_by:
        raise HTTPException(status_code=400, detail="approved_by is required")
    try:
        return await _review_pipeline.approve_review(review_id, req.approved_by)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/reviews/{review_id}/reject")
async def reject_review(review_id: str, req: ReviewActionRequest):
    """Reject a pending review."""
    if not req.rejected_by or not req.reason:
        raise HTTPException(
            status_code=400, detail="rejected_by and reason are required"
        )
    try:
        return await _review_pipeline.reject_review(
            review_id, req.rejected_by, req.reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================================
# Run Stats Endpoint — enriched data from DCL for operator display
# ============================================================================

@router.get("/run-stats/{engagement_id}")
async def get_run_stats(
    engagement_id: str,
    source_run_tag: str | None = None,
    step_type: str | None = None,
):
    """Fetch enriched run statistics from DCL for operator display.

    Returns triple count, top-level domain breakdown, conflict count,
    and COFA-specific fields (mapped_count, resolved_count, conflict_count).

    For cofa-map steps, triple count comes from /api/dcl/merge/overview
    (total_cofa_count) because COFA triples have no source_run_tag.
    """
    stats: dict = {
        "source_run_tag": source_run_tag,
        "triple_count": 0,
        "domain_count": 0,
        "entity_count": 0,
        "domain_breakdown": {},
        "conflict_count": 0,
        "conflicts_resolved": 0,
        "conflicts_pending": 0,
        "mapped_count": 0,
        "resolved_count": 0,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        if step_type == "cofa-map":
            # COFA triples have no source_run_tag — use merge overview
            resp = await client.get(
                f"{DCL_BASE_URL}/api/dcl/merge/overview",
            )
            if resp.status_code == 200:
                data = resp.json()
                overview = data.get("overview", {})
                stats["triple_count"] = overview.get("total_cofa_count", 0)
                stats["mapped_count"] = data.get("mapped_count", 0)
                stats["resolved_count"] = data.get("resolved_count", 0)
                stats["conflict_count"] = data.get("conflict_count", 0)
                stats["conflicts_pending"] = stats["conflict_count"] - stats["resolved_count"]
                stats["conflicts_resolved"] = stats["resolved_count"]
                stats["entity_count"] = len(overview.get("entities", []))
            else:
                error_detail = resp.text[:300]
                raise HTTPException(
                    status_code=502,
                    detail=(
                        f"DCL merge overview unavailable: HTTP {resp.status_code} "
                        f"— GET {DCL_BASE_URL}/api/dcl/merge/overview "
                        f"— response: {error_detail}"
                    ),
                )
        else:
            # Standard triples overview with optional source_run_tag filter
            params: dict = {}
            if source_run_tag:
                params["source_run_tag"] = source_run_tag
            resp = await client.get(
                f"{DCL_BASE_URL}/api/dcl/triples/overview",
                params=params,
            )
            if resp.status_code == 200:
                data = resp.json()
                stats["triple_count"] = data.get("total_triples", 0)
                stats["entity_count"] = len(data.get("entities", []))

                # Top-level domain breakdown (already grouped by split_part)
                domains_list = data.get("domains", [])
                domain_breakdown: dict[str, int] = {}
                for d in domains_list:
                    domain_name = d.get("domain", "")
                    if domain_name:
                        domain_breakdown[domain_name] = d.get("count", 0)
                stats["domain_breakdown"] = domain_breakdown
                stats["domain_count"] = len(domain_breakdown)

                # Conflict count from cofa_conflict triples.
                # COFA conflicts are engagement-level artifacts (written by the
                # mapping engine, not Farm ingest), so they don't carry the same
                # source_run_tag.  Always fetch conflicts globally.
                if source_run_tag:
                    global_resp = await client.get(
                        f"{DCL_BASE_URL}/api/dcl/triples/overview",
                    )
                    if global_resp.status_code == 200:
                        stats["conflict_count"] = global_resp.json().get("conflict_count", 0)
                    else:
                        logger.error(
                            "DCL triples/overview (global) returned HTTP %d — "
                            "conflict count unavailable for engagement=%s",
                            global_resp.status_code, engagement_id,
                        )
                else:
                    stats["conflict_count"] = data.get("conflict_count", 0)
                stats["conflicts_pending"] = stats["conflict_count"]
            else:
                error_detail = resp.text[:300]
                raise HTTPException(
                    status_code=502,
                    detail=(
                        f"DCL triples overview unavailable: HTTP {resp.status_code} "
                        f"— GET {DCL_BASE_URL}/api/dcl/triples/overview "
                        f"— response: {error_detail}"
                    ),
                )

    # Supplement conflict count from local review queue
    reviews = await _review_pipeline.list_pending_reviews(engagement_id)
    if reviews:
        resolved = sum(1 for r in reviews if r.get("status") == "approved")
        stats["conflicts_resolved"] = max(stats["conflicts_resolved"], resolved)
        if stats["conflict_count"] == 0:
            stats["conflict_count"] = len(reviews)
            stats["conflicts_pending"] = len(reviews) - resolved

    return stats


# ============================================================================
# Status Endpoint (for cross-module orchestration)
# ============================================================================

@router.get("/status")
async def maestra_status():
    """Orchestration status endpoint for cross-module health checks."""
    active = await _engagement_mgr.get_active_engagement()
    pending_reviews = await _review_pipeline.list_pending_reviews()
    tools = _tools.get_tools()

    return {
        "status": "operational",
        "active_engagement": active,
        "pending_reviews_count": len(pending_reviews),
        "available_tools": len(tools),
        "constitution_rules": len(_constitution.get_rules()),
    }
