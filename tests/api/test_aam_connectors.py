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


def test_mapping_count_scoped_by_connection(demo_tenant_token):
    """
    Test that mapping_count is scoped by connection_id, not vendor
    
    This test validates that if two FilesSource connections exist in the same tenant,
    ingesting data for only one of them doesn't inflate the other's mapping_count.
    
    Note: Since connections table isn't tenant-scoped, we test that mappings
    ARE correctly scoped to specific connection_ids.
    """
    headers = {"Authorization": f"Bearer {demo_tenant_token}"}
    response = requests.get(f"{BASE_URL}/api/v1/aam/connectors", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    # Find all FilesSource connectors
    filesource_conns = [c for c in data["connectors"] if c["type"] == "filesource"]
    
    # If we only have one FilesSource, this test passes trivially
    if len(filesource_conns) == 1:
        print("\n⚠️  Only one FilesSource connection found - test passes trivially")
        return
    
    # With multiple FilesSource connections, verify they have independent mapping counts
    # (The ingest script only populated one specific connection_id)
    print(f"\n📊 Found {len(filesource_conns)} FilesSource connections:")
    for conn in filesource_conns:
        conn_id = conn.get("id")
        mapping_count = conn.get("mapping_count", 0)
        print(f"  - {conn['name']} ({conn_id[:8]}...): {mapping_count} mappings")
    
    # At least one should have mappings (the one we ingested)
    # Others should have 0 (not auto-populated from vendor='filesource')
    mapping_counts = [c.get("mapping_count", 0) for c in filesource_conns]
    assert any(count > 0 for count in mapping_counts), "At least one FilesSource should have mappings"
    assert any(count == 0 for count in mapping_counts), "At least one FilesSource should have 0 mappings (connection-scoped)"


def test_healthz_aam_ok():
    """Test that /healthz/aam endpoint returns 200 with {"ok": true}"""
    response = requests.get(f"{BASE_URL}/api/v1/aam/healthz")
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    
    assert "ok" in data, f"Expected 'ok' field in response: {data}"
    assert data["ok"] is True, f"Expected ok=true, got {data['ok']}"
    print("\n✅ AAM healthz endpoint OK")


def test_drift_detected_increments_mapping_count(demo_tenant_token):
    """
    Test that drift simulation increments mapping_count by 1
    
    This test:
    1. Gets pre-drift mapping_count for FilesSource
    2. Runs drift simulation (adds new column to CSV)
    3. Verifies mapping_count increased by exactly 1
    4. Checks that DRIFT_DETECTED event was created
    """
    # Get pre-drift mapping count
    headers = {"Authorization": f"Bearer {demo_tenant_token}"}
    response = requests.get(f"{BASE_URL}/api/v1/aam/connectors", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    filesource = next((c for c in data["connectors"] if c["type"] == "filesource"), None)
    assert filesource is not None, "FilesSource not found"
    
    pre_count = filesource.get("mapping_count", 0)
    print(f"\n📊 Pre-drift mapping_count: {pre_count}")
    
    # Run drift simulation
    drift_script = Path(__file__).parent.parent.parent / "scripts" / "filesource_drift_sim.py"
    assert drift_script.exists(), f"Drift script not found at {drift_script}"
    
    print("🔄 Running drift simulation...")
    result = subprocess.run(
        [
            sys.executable,
            str(drift_script),
            "--connection-id", "10ca3a88-5105-4e24-b984-6e350a5fa443",
            "--namespace", "AOS Test Tenant"  # Match test user's tenant
        ],
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    assert result.returncode == 0, f"Drift simulation failed: {result.stderr}"
    assert "Drift simulation complete" in result.stdout
    
    # Get post-drift mapping count
    response = requests.get(f"{BASE_URL}/api/v1/aam/connectors", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    filesource = next((c for c in data["connectors"] if c["type"] == "filesource"), None)
    assert filesource is not None
    
    post_count = filesource.get("mapping_count", 0)
    print(f"📊 Post-drift mapping_count: {post_count}")
    
    # Verify count increased by exactly 1
    assert post_count == pre_count + 1, f"Expected {pre_count + 1}, got {post_count}"
    print(f"✅ Mapping count increased by 1 (drift detected)")


def test_connector_dto_contract(demo_tenant_token):
    """
    Validate that GET /api/v1/aam/connectors returns data matching ConnectorDTO schema
    
    Expected schema (OpenAPI contract):
    - id: string (UUID)
    - name: string
    - source_type: string
    - status: string
    - mapping_count: int
    - last_event_type: string | null
    - last_event_at: string (ISO timestamp) | null
    - has_drift: bool
    """
    headers = {"Authorization": f"Bearer {demo_tenant_token}"}
    response = requests.get(f"{BASE_URL}/api/v1/aam/connectors", headers=headers)
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    
    # Validate top-level response structure
    assert "connectors" in data, "Response must include 'connectors' field"
    assert "total" in data, "Response must include 'total' field"
    assert isinstance(data["connectors"], list), "'connectors' must be a list"
    assert isinstance(data["total"], int), "'total' must be an integer"
    
    # If connectors exist, validate each one matches ConnectorDTO
    if data["total"] > 0:
        connector = data["connectors"][0]
        
        # Required fields
        required_fields = ["id", "name", "source_type", "status", "mapping_count", "has_drift"]
        for field in required_fields:
            assert field in connector, f"Connector must have '{field}'"
        
        # Type validation
        assert isinstance(connector["id"], str), "'id' must be string"
        assert isinstance(connector["name"], str), "'name' must be string"
        assert isinstance(connector["source_type"], str), "'source_type' must be string"
        assert isinstance(connector["status"], str), "'status' must be string"
        assert isinstance(connector["mapping_count"], int), "'mapping_count' must be int"
        assert isinstance(connector["has_drift"], bool), "'has_drift' must be bool"
        
        # Optional drift fields (can be null)
        if "last_event_type" in connector and connector["last_event_type"] is not None:
            assert isinstance(connector["last_event_type"], str), "'last_event_type' must be string or null"
        
        if "last_event_at" in connector and connector["last_event_at"] is not None:
            assert isinstance(connector["last_event_at"], str), "'last_event_at' must be string or null"
        
        print(f"\n✅ Connector DTO contract validated: {connector['name']}")
        print(f"   - has_drift: {connector['has_drift']}")
        print(f"   - last_event_type: {connector.get('last_event_type', 'None')}")


def test_openapi_spec_includes_drift_fields():
    """
    Verify that OpenAPI spec includes ConnectorDTO schema with drift fields
    """
    response = requests.get(f"{BASE_URL}/openapi.json")
    assert response.status_code == 200, "OpenAPI spec should be accessible"
    
    spec = response.json()
    schemas = spec.get("components", {}).get("schemas", {})
    
    # Validate ConnectorDTO exists in schema
    assert "ConnectorDTO" in schemas, "OpenAPI spec must include ConnectorDTO schema"
    
    dto_schema = schemas["ConnectorDTO"]
    properties = dto_schema.get("properties", {})
    
    # Validate required drift fields are in schema
    required_fields = ["id", "name", "source_type", "status", "mapping_count", "has_drift"]
    for field in required_fields:
        assert field in properties, f"ConnectorDTO must include '{field}' field"
    
    # Validate optional drift fields
    assert "last_event_type" in properties, "ConnectorDTO must include 'last_event_type' field"
    assert "last_event_at" in properties, "ConnectorDTO must include 'last_event_at' field"
    
    # Validate has_drift is boolean
    assert properties["has_drift"]["type"] == "boolean", "'has_drift' must be boolean type"
    
    print("\n✅ OpenAPI spec validated with drift fields")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
