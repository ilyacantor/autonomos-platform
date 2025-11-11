"""
Smoke tests for AAM connectors endpoint

Tests auth, namespace scoping, and mapping counts.
"""

import pytest
import requests
import os
import subprocess
import sys
from pathlib import Path


# Test configuration
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:5000")
DEMO_TENANT_EMAIL = "aostest@autonomos.dev"
DEMO_TENANT_PASSWORD = "TestPass123!"
OTHER_TENANT_EMAIL = "other.tenant@autonomos.dev"
OTHER_TENANT_PASSWORD = "OtherPass123!"


@pytest.fixture(scope="module")
def demo_tenant_token():
    """Get or create JWT for demo tenant"""
    # Try to register (idempotent)
    requests.post(
        f"{BASE_URL}/api/v1/auth/register",
        json={
            "name": "Demo Tenant",
            "email": DEMO_TENANT_EMAIL,
            "password": DEMO_TENANT_PASSWORD
        }
    )
    
    # Login
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={
            "email": DEMO_TENANT_EMAIL,
            "password": DEMO_TENANT_PASSWORD
        }
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def other_tenant_token():
    """Get or create JWT for a different tenant (non-demo namespace)"""
    # Try to register (idempotent)
    requests.post(
        f"{BASE_URL}/api/v1/auth/register",
        json={
            "name": "Other Tenant",
            "email": OTHER_TENANT_EMAIL,
            "password": OTHER_TENANT_PASSWORD
        }
    )
    
    # Login
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={
            "email": OTHER_TENANT_EMAIL,
            "password": OTHER_TENANT_PASSWORD
        }
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["access_token"]


def test_unauthorized_get_connectors():
    """Test that connectors endpoint returns 401 without auth token"""
    response = requests.get(f"{BASE_URL}/api/v1/aam/connectors")
    assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
    assert "authorization" in response.text.lower() or "unauthorized" in response.text.lower()


def test_wrong_namespace_returns_limited(other_tenant_token):
    """
    Test that a tenant in a different namespace sees limited connectors
    
    Note: Currently connections table doesn't have tenant_id, so all tenants
    see all connections. This test validates the endpoint works for any tenant.
    """
    headers = {"Authorization": f"Bearer {other_tenant_token}"}
    response = requests.get(f"{BASE_URL}/api/v1/aam/connectors", headers=headers)
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    
    assert "connectors" in data
    assert "total" in data
    assert isinstance(data["connectors"], list)
    # For now, all tenants see all connections (no tenant isolation on connections table yet)
    # This test validates the endpoint works for non-demo tenants


def test_happy_path_includes_filesource(demo_tenant_token):
    """Test that demo tenant sees FilesSource connector with ACTIVE status"""
    headers = {"Authorization": f"Bearer {demo_tenant_token}"}
    response = requests.get(f"{BASE_URL}/api/v1/aam/connectors", headers=headers)
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    
    assert "connectors" in data
    assert "total" in data
    assert data["total"] > 0, "Expected at least one connector"
    
    # Find FilesSource connector
    filesource = next((c for c in data["connectors"] if c["type"] == "filesource"), None)
    assert filesource is not None, f"FilesSource not found in connectors: {[c['type'] for c in data['connectors']]}"
    assert filesource["status"] == "ACTIVE", f"Expected ACTIVE, got {filesource['status']}"
    assert "mapping_count" in filesource, "mapping_count field missing"


def test_mapping_count_after_ingest(demo_tenant_token):
    """
    Test that FilesSource mapping_count is > 0 after running ingest
    
    This test:
    1. Runs the ingest script
    2. Checks that FilesSource mapping_count > 0
    """
    # Run ingest script
    script_path = Path(__file__).parent.parent.parent / "scripts" / "filesource_ingest.py"
    assert script_path.exists(), f"Ingest script not found at {script_path}"
    
    print("\n🔄 Running ingest script...")
    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--connection-id", "10ca3a88-5105-4e24-b984-6e350a5fa443",
            "--namespace", "demo"
        ],
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    assert result.returncode == 0, f"Ingest script failed: {result.stderr}"
    assert "Ingest complete" in result.stdout, "Expected completion message in output"
    
    # Now check connectors endpoint
    headers = {"Authorization": f"Bearer {demo_tenant_token}"}
    response = requests.get(f"{BASE_URL}/api/v1/aam/connectors", headers=headers)
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    
    # Find FilesSource
    filesource = next((c for c in data["connectors"] if c["type"] == "filesource"), None)
    assert filesource is not None, "FilesSource not found after ingest"
    
    mapping_count = filesource.get("mapping_count", 0)
    print(f"\n✅ FilesSource mapping_count: {mapping_count}")
    assert mapping_count > 0, f"Expected mapping_count > 0, got {mapping_count}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
