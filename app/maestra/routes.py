"""
Maestra API Routes — mount at /api/maestra

Provides endpoints for engagement lifecycle, run ledger, constitution,
chat, and human review.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.maestra.engagement import EngagementManager
from app.maestra.run_ledger import RunLedger
from app.maestra.constitution import Constitution
from app.maestra.tools import MaestraTools
from app.maestra.human_review import HumanReviewPipeline
from app.maestra.chat import MaestraChat

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


class ChatRequest(BaseModel):
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
# Chat Endpoint
# ============================================================================

@router.post("/chat")
async def maestra_chat(req: ChatRequest):
    """Process a message in the Maestra orchestration context."""
    try:
        engagement = await _engagement_mgr.get_engagement(req.engagement_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    ledger = RunLedger(req.engagement_id)
    chat = MaestraChat(_engagement_mgr, ledger, _constitution)
    return await chat.process_message(req.message, req.engagement_id, req.session_id)


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
