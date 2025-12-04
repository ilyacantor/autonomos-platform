import pytest
import httpx
from datetime import date

BASE_URL = "http://localhost:8001"


@pytest.fixture
def demo_tenant_token():
    """
    Demo tenant JWT token for testing.
    In production, this would be obtained via OAuth flow.
    """
    import jwt
    import os
    
    secret_key = os.getenv("SECRET_KEY", "dev-secret-key")
    
    payload = {
        "tenant_id": "demo-tenant",
        "env": "dev",
        "user_id": "test-user",
        "scopes": ["read", "write"]
    }
    
    token = jwt.encode(payload, secret_key, algorithm="HS256")
    return token


@pytest.mark.asyncio
async def test_health_endpoint():
    """Test health endpoint (no auth required)."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "nlp-gateway"


@pytest.mark.asyncio
async def test_finops_summary(demo_tenant_token):
    """Test FinOps summary endpoint."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/v1/finops/summary",
            json={
                "tenant_id": "demo-tenant",
                "env": "dev",
                "from": "2024-11-01",
                "to": "2024-11-07"
            },
            headers={"Authorization": f"Bearer {demo_tenant_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "trace_id" in data
        assert "window" in data
        assert "totals" in data
        assert "actions" in data


@pytest.mark.asyncio
async def test_revops_incident(demo_tenant_token):
    """Test RevOps incident endpoint."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/v1/revops/incident",
            json={
                "tenant_id": "demo-tenant",
                "env": "dev",
                "incident_id": "inc-001"
            },
            headers={"Authorization": f"Bearer {demo_tenant_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "trace_id" in data
        assert data["incident_id"] == "inc-001"
        assert "diagnosis" in data
        assert "resolution" in data


@pytest.mark.asyncio
async def test_aod_dependencies(demo_tenant_token):
    """Test AOD dependencies endpoint."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/v1/aod/dependencies",
            json={
                "tenant_id": "demo-tenant",
                "env": "dev",
                "service": "checkout"
            },
            headers={"Authorization": f"Bearer {demo_tenant_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "trace_id" in data
        assert data["service"] == "checkout"
        assert "dependencies" in data
        assert len(data["dependencies"]) > 0


@pytest.mark.asyncio
async def test_aam_connectors(demo_tenant_token):
    """Test AAM connectors endpoint."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/v1/aam/connectors",
            json={
                "tenant_id": "demo-tenant",
                "env": "dev",
                "status": "All"
            },
            headers={"Authorization": f"Bearer {demo_tenant_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "trace_id" in data
        assert "status_counts" in data
        assert "connectors" in data


@pytest.mark.asyncio
async def test_kb_ingest_and_search(demo_tenant_token):
    """Test KB ingest and search flow."""
    async with httpx.AsyncClient() as client:
        ingest_response = await client.post(
            f"{BASE_URL}/v1/kb/ingest",
            json={
                "tenant_id": "demo-tenant",
                "env": "dev",
                "items": [
                    {
                        "type": "text",
                        "location": "The AutonomOS platform provides automated operations for cloud infrastructure. It includes FinOps for cost optimization, RevOps for revenue operations, and AOD for observability.",
                        "tags": ["platform", "overview"]
                    }
                ],
                "policy": {
                    "chunk": "auto",
                    "max_chunk_tokens": 1200,
                    "redact_pii": True
                }
            },
            headers={"Authorization": f"Bearer {demo_tenant_token}"}
        )
        assert ingest_response.status_code == 200
        ingest_data = ingest_response.json()
        assert "trace_id" in ingest_data
        assert len(ingest_data["ingested"]) > 0
        
        search_response = await client.post(
            f"{BASE_URL}/v1/kb/search",
            json={
                "tenant_id": "demo-tenant",
                "env": "dev",
                "query": "What does AutonomOS provide?",
                "top_k": 5
            },
            headers={"Authorization": f"Bearer {demo_tenant_token}"}
        )
        assert search_response.status_code == 200
        search_data = search_response.json()
        assert "trace_id" in search_data
        assert "matches" in search_data


@pytest.mark.asyncio
async def test_feedback_log(demo_tenant_token):
    """Test feedback logging endpoint."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/v1/feedback/log",
            json={
                "tenant_id": "demo-tenant",
                "env": "dev",
                "turn_id": "turn-123",
                "rating": "up",
                "notes": "Great response!"
            },
            headers={"Authorization": f"Bearer {demo_tenant_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "trace_id" in data
        assert data["ok"] is True
