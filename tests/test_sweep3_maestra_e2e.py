"""
Sweep 3 — Maestra → DCL End-to-End Integration Test

Verifies the Maestra orchestration layer works end-to-end:
engagement lifecycle, chat, run ledger, constitution, and human review.

Requires: Platform running on port 8006, DCL running on port 8004.
"""

import uuid
import pytest
import httpx

PLATFORM_BASE = "http://localhost:8006"
ENGAGEMENT_ID = f"sweep3-{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="module")
def client():
    return httpx.Client(base_url=PLATFORM_BASE, timeout=30.0)


# --- Test 1: Create engagement ---
def test_create_engagement(client):
    """POST /api/maestra/engagements creates an engagement with entity_a/entity_b."""
    resp = client.post(
        "/api/maestra/engagements",
        json={
            "engagement_id": ENGAGEMENT_ID,
            "entity_a": "meridian",
            "entity_b": "cascadia",
            "entity_a_name": "Meridian Partners",
            "entity_b_name": "Cascadia Process Solutions",
            "created_by": "sweep3",
        },
    )
    assert resp.status_code == 200, f"Create engagement failed: {resp.text}"
    data = resp.json()
    assert data["engagement_id"] == ENGAGEMENT_ID
    assert data["entity_a"] == "meridian"
    assert data["entity_b"] == "cascadia"
    assert data["state"] == "draft"


# --- Test 2: Chat query ---
def test_chat_query(client):
    """POST /api/maestra/chat accepts a message and returns a response."""
    resp = client.post(
        "/api/maestra/chat",
        json={
            "message": "What is meridian's revenue?",
            "engagement_id": ENGAGEMENT_ID,
            "session_id": f"session-{ENGAGEMENT_ID}",
        },
    )
    assert resp.status_code == 200, f"Chat failed: {resp.text}"
    data = resp.json()
    assert "response" in data
    assert isinstance(data["response"], str)
    assert len(data["response"]) > 0


# --- Test 3: Run ledger records steps ---
def test_run_ledger(client):
    """Run ledger records pipeline steps for an engagement."""
    # Record a step
    resp = client.post(
        f"/api/maestra/run-ledger/{ENGAGEMENT_ID}/steps",
        json={
            "step_name": "sweep3_test_step",
            "idempotency_key": f"sweep3-{uuid.uuid4().hex[:8]}",
            "inputs_hash": "abc123",
            "upstream_deps": [],
        },
    )
    assert resp.status_code == 200, f"Record step failed: {resp.text}"

    # List steps — should have at least 1
    resp = client.get(f"/api/maestra/run-ledger/{ENGAGEMENT_ID}")
    assert resp.status_code == 200
    steps = resp.json()
    assert len(steps) >= 1, f"Expected at least 1 step, got {len(steps)}"


# --- Test 4: Constitution endpoint ---
def test_constitution(client):
    """GET /api/maestra/constitution returns rules including fabrication prohibition."""
    resp = client.get("/api/maestra/constitution")
    assert resp.status_code == 200
    data = resp.json()
    assert "rules" in data
    assert data["count"] > 0

    rules_text = " ".join(data["rules"]).lower()
    # Constitution must include accounting/fabrication-related rules
    assert any(
        keyword in rules_text
        for keyword in ["fallback", "error", "audit", "fabricat", "silent"]
    ), f"Constitution missing fabrication/error rules: {data['rules']}"


# --- Test 5: Human review round-trip ---
def test_human_review_roundtrip(client):
    """Create review → list pending → approve → status changes."""
    # Create a tier-2 review (tier 1 auto-approves)
    resp = client.post(
        "/api/maestra/reviews",
        json={
            "engagement_id": ENGAGEMENT_ID,
            "action": "approve_cofa_adjustment",
            "context": {"adjustment_id": "sweep3-test", "amount": 100.0},
            "tier": 2,
            "requested_by": "sweep3",
        },
    )
    assert resp.status_code == 200, f"Create review failed: {resp.text}"
    review = resp.json()
    review_id = review["review_id"]
    assert review["status"] == "pending"

    # List pending reviews
    resp = client.get("/api/maestra/reviews", params={"status": "pending"})
    assert resp.status_code == 200
    pending = resp.json()
    found = [r for r in pending if r["review_id"] == review_id]
    assert len(found) == 1, f"Review {review_id} not in pending list"

    # Approve the review
    resp = client.patch(
        f"/api/maestra/reviews/{review_id}/approve",
        json={"approved_by": "sweep3_tester"},
    )
    assert resp.status_code == 200, f"Approve review failed: {resp.text}"
    approved = resp.json()
    assert approved["status"] == "approved"
