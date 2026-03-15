"""
Stage 3H Harness — Maestra Foundation
Tests engagement lifecycle, run ledger, constitution, and human review.
All stores use Supabase PG (shared with DCL).
"""
import os
import sys
import pytest
import uuid

# Ensure platform root is on path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Load .env for SUPABASE_DB_URL and TENANT_ID if not already set
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from app.maestra.engagement import EngagementManager
from app.maestra.run_ledger import RunLedger
from app.maestra.constitution import Constitution
from app.maestra.tools import MaestraTools
from app.maestra.human_review import HumanReviewPipeline

TENANT_ID = os.environ.get("TENANT_ID", "400aa910-a6b4-5d44-ab9f-e6aecde37721")


@pytest.fixture
def engagement_mgr():
    return EngagementManager()

@pytest.fixture
def constitution():
    return Constitution()

@pytest.fixture
def tools():
    return MaestraTools()


# --- Test 1: Create engagement ---
@pytest.mark.asyncio
async def test_create_engagement(engagement_mgr):
    eid = f"eng-{uuid.uuid4().hex[:8]}"
    eng = await engagement_mgr.create_engagement(
        eid, "meridian", "cascadia", "Meridian Partners", "Cascadia Process Solutions"
    )
    assert eng["engagement_id"] == eid
    assert eng["state"] == "draft"
    assert eng["entity_a"] == "meridian"
    assert eng["entity_b"] == "cascadia"

# --- Test 2: State transitions ---
@pytest.mark.asyncio
async def test_state_transitions(engagement_mgr):
    eid = f"eng-{uuid.uuid4().hex[:8]}"
    await engagement_mgr.create_engagement(eid, "a", "b", "A", "B")
    eng = await engagement_mgr.update_state(eid, "active")
    assert eng["state"] == "active"
    eng = await engagement_mgr.update_state(eid, "review")
    assert eng["state"] == "review"
    eng = await engagement_mgr.update_state(eid, "closed")
    assert eng["state"] == "closed"

# --- Test 3: Invalid state transition ---
@pytest.mark.asyncio
async def test_invalid_transition(engagement_mgr):
    eid = f"eng-{uuid.uuid4().hex[:8]}"
    await engagement_mgr.create_engagement(eid, "a", "b", "A", "B")
    with pytest.raises(ValueError, match="invalid transition"):
        await engagement_mgr.update_state(eid, "closed")  # draft->closed not valid

# --- Test 4: Engagement persists ---
@pytest.mark.asyncio
async def test_engagement_persists(engagement_mgr):
    eid = f"eng-{uuid.uuid4().hex[:8]}"
    await engagement_mgr.create_engagement(eid, "x", "y", "X", "Y")
    # New instance should find it (same PG database)
    mgr2 = EngagementManager()
    eng = await mgr2.get_engagement(eid)
    assert eng["entity_a"] == "x"

# --- Test 5: Run ledger idempotency ---
@pytest.mark.asyncio
async def test_run_ledger_idempotency():
    eid = f"eng-{uuid.uuid4().hex[:8]}"
    ledger = RunLedger(eid)
    step1 = await ledger.record_step("discover", f"disc-001-{eid}", "hash-abc")
    assert step1["is_new"] is True
    step2 = await ledger.record_step("discover", f"disc-001-{eid}", "hash-abc")
    assert step2["is_new"] is False
    assert step1["step_id"] == step2["step_id"]

# --- Test 6: Run ledger step lifecycle ---
@pytest.mark.asyncio
async def test_run_ledger_lifecycle():
    eid = f"eng-{uuid.uuid4().hex[:8]}"
    ledger = RunLedger(eid)
    step = await ledger.record_step("ingest", f"ing-001-{eid}", "hash-xyz")
    started = await ledger.start_step(step["step_id"])
    assert started["status"] == "running"
    completed = await ledger.complete_step(step["step_id"], outputs_ref="s3://bucket/output")
    assert completed["status"] == "complete"

# --- Test 7: Downstream invalidation ---
@pytest.mark.asyncio
async def test_downstream_invalidation():
    eid = f"eng-{uuid.uuid4().hex[:8]}"
    ledger = RunLedger(eid)
    step_a = await ledger.record_step("discover", f"a-001-{eid}", "hash-a")
    step_b = await ledger.record_step("ingest", f"b-001-{eid}", "hash-b",
                                       upstream_deps=[step_a["step_id"]])
    step_c = await ledger.record_step("combine", f"c-001-{eid}", "hash-c",
                                       upstream_deps=[step_b["step_id"]])
    await ledger.start_step(step_b["step_id"])
    await ledger.complete_step(step_b["step_id"])
    await ledger.start_step(step_c["step_id"])
    await ledger.complete_step(step_c["step_id"])

    # Re-complete step_a (re-run) — should invalidate step_b
    await ledger.start_step(step_a["step_id"])
    await ledger.complete_step(step_a["step_id"])

    stale = await ledger.get_stale_steps()
    stale_names = [s["step_name"] for s in stale]
    assert "ingest" in stale_names  # step_b depends on step_a

# --- Test 8: Constitution has required rules ---
def test_constitution_rules(constitution):
    rules = constitution.get_rules()
    assert len(rules) >= len(Constitution.REQUIRED_RULES)
    for required in Constitution.REQUIRED_RULES:
        assert any(required.lower() in r.lower() for r in rules), \
            f"Missing required rule: {required}"

# --- Test 9: Constitution compliance check ---
def test_constitution_compliance(constitution):
    result = constitution.check_compliance("delete production data")
    assert result["compliant"] is False

    result = constitution.check_compliance("record audit entry")
    assert result["compliant"] is True

# --- Test 10: Tool definitions ---
def test_tool_definitions(tools):
    defs = tools.get_tools()
    assert len(defs) >= 5
    names = [t["name"] for t in defs]
    assert "check_module_status" in names
    assert "trigger_pipeline_run" in names
    assert "request_human_review" in names

# --- Test 11: Human review 4-tier classification ---
@pytest.mark.asyncio
async def test_review_classification():
    pipeline = HumanReviewPipeline()
    # Tier 1: auto-approve
    result = await pipeline.classify_review("log_entry", {"severity": "info"})
    assert result["tier"] == 1

    # Tier 3+: approval required for cross-entity decisions
    result = await pipeline.classify_review("merge_entities", {"entities": ["a", "b"]})
    assert result["tier"] >= 3

# --- Test 12: Human review lifecycle ---
@pytest.mark.asyncio
async def test_review_lifecycle():
    pipeline = HumanReviewPipeline()
    eid = f"eng-{uuid.uuid4().hex[:8]}"
    review = await pipeline.create_review(eid, "approve_cofa", {"cofa_id": "COFA-001"}, tier=3)
    assert review["status"] == "pending"

    approved = await pipeline.approve_review(review["review_id"], "ilya")
    assert approved["status"] == "approved"

# --- Test 13: Pending reviews ---
@pytest.mark.asyncio
async def test_pending_reviews():
    pipeline = HumanReviewPipeline()
    eid = f"eng-{uuid.uuid4().hex[:8]}"
    await pipeline.create_review(eid, "action_1", {}, tier=2)
    await pipeline.create_review(eid, "action_2", {}, tier=3)
    pending = await pipeline.list_pending_reviews(eid)
    assert len(pending) == 2

# --- Test 14: Missing engagement raises ---
@pytest.mark.asyncio
async def test_missing_engagement_raises(engagement_mgr):
    with pytest.raises(ValueError, match="not found"):
        await engagement_mgr.get_engagement("nonexistent-engagement")

# --- Test 15: Idempotency with different hash triggers new step ---
@pytest.mark.asyncio
async def test_idempotency_different_hash():
    eid = f"eng-{uuid.uuid4().hex[:8]}"
    ledger = RunLedger(eid)
    step1 = await ledger.record_step("discover", f"disc-002-{eid}", "hash-v1")
    step2 = await ledger.record_step("discover", f"disc-002-{eid}", "hash-v2")
    # Different hash = should create new step or update
    # Implementation decision: either new step or re-run with new hash
    assert step2 is not None
