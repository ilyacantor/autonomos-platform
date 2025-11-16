"""
Shared pytest fixtures for AutonomOS multi-tenant testing.
"""
import os
import uuid

# CRITICAL: Enable authentication for tests BEFORE importing app modules
# This must be set before app.security is loaded to properly validate JWT tokens
# Without this, all requests use MockUser and security tests cannot function
os.environ['DCL_AUTH_ENABLED'] = 'true'

# CRITICAL P0 FIX: Disable AAM mode for tests
# AAM connector mode is incomplete - doesn't create graph nodes/edges (no DuckDB materialized views)
# Tests expect legacy file source mode which creates proper graph structures via agents
# Environment variables have highest precedence in FeatureFlagConfig (app/config/feature_flags.py)
os.environ['FEATURE_USE_AAM_AS_SOURCE'] = 'false'

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import get_db
from app.models import Base
from app.config import settings
import warnings


# ===== CRITICAL DATABASE SAFETY =====
# Tests MUST use isolated database to prevent production data corruption.
# Set TEST_DATABASE_URL environment variable to a separate test database.
# If not set, tests will use in-memory SQLite with limited functionality.

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

if TEST_DATABASE_URL is None:
    warnings.warn(
        "\n"
        "=" * 80 + "\n"
        "CRITICAL WARNING: TEST_DATABASE_URL not set!\n"
        "=" * 80 + "\n"
        "Many tests will SKIP or FAIL due to missing database.\n"
        "For full PostgreSQL testing, set TEST_DATABASE_URL to an isolated database.\n"
        "\n"
        "Example:\n"
        "  export TEST_DATABASE_URL='postgresql://user:pass@localhost/test_db'\n"
        "\n"
        "NEVER point TEST_DATABASE_URL at production DATABASE_URL!\n"
        "Running tests against shared data WILL cause corruption.\n"
        "=" * 80 + "\n",
        UserWarning,
        stacklevel=2
    )
    # Use in-memory SQLite as safe fallback
    # NOTE: SQLite has limited compatibility with PostgreSQL-specific features
    # (e.g., UUID columns). Many tests will skip or fail.
    TEST_DATABASE_URL = "sqlite:///:memory:"
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False}  # Required for SQLite
    )
    # Skip table creation for SQLite - models use PostgreSQL-specific types (UUID)
    # Tests requiring database will fail gracefully
else:
    # Verify TEST_DATABASE_URL is not accidentally pointing at production
    if TEST_DATABASE_URL == settings.DATABASE_URL:
        raise RuntimeError(
            "FATAL: TEST_DATABASE_URL points to production DATABASE_URL!\n"
            "Running tests would corrupt shared data.\n"
            "Set TEST_DATABASE_URL to a separate isolated test database."
        )
    engine = create_engine(TEST_DATABASE_URL)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    db = None
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        if db is not None:
            db.close()


# ===== LAZY APP LOADING FIXTURE =====
# App is loaded lazily to prevent module-level import hangs during test collection.
# This ensures pytest --collect-only works without starting the full FastAPI app.

@pytest.fixture(scope="session")
def app():
    """
    Lazy-load FastAPI app for testing.
    
    CRITICAL: App is loaded at fixture execution time, NOT at module import time.
    This prevents hangs during test collection (pytest --collect-only).
    
    The app is loaded once per test session and reused across all tests.
    
    IMPORTANT: Overrides database dependency on BOTH main app and DCL sub-app.
    The DCL endpoints are mounted as a sub-application at /dcl, which has its own
    dependency injection context. Without overriding both, DCL endpoints will use
    production database while other endpoints use test database.
    """
    from app.main import app as _app
    
    # Override database dependency on main app
    _app.dependency_overrides[get_db] = override_get_db
    
    # Override database dependency on DCL sub-app (mounted at /dcl)
    # DCL is a mounted FastAPI sub-application with separate dependency context
    try:
        from app.dcl_engine.app import app as dcl_app
        dcl_app.dependency_overrides[get_db] = override_get_db
    except Exception as e:
        warnings.warn(f"Could not override DCL app dependencies: {e}")
    
    return _app

@pytest.fixture(scope="function")
def client(app):
    """
    Create a test client for making API requests.
    Each test gets a fresh client.
    
    Args:
        app: Lazy-loaded FastAPI app fixture
    """
    return TestClient(app)

@pytest.fixture(scope="function")
def unique_tenant_name():
    """Generate a unique tenant name for each test."""
    return f"Test-Tenant-{uuid.uuid4().hex[:8]}"

@pytest.fixture(scope="function")
def unique_email():
    """Generate a unique email address for each test."""
    return f"user-{uuid.uuid4().hex[:8]}@test.com"

def register_user(client: TestClient, tenant_name: str, email: str, password: str = "testpass123"):
    """
    Helper function to register a new user and tenant.
    Returns the registration response.
    """
    response = client.post(
        "/users/register",
        json={
            "name": tenant_name,
            "email": email,
            "password": password
        }
    )
    return response

def login_user(client: TestClient, email: str, password: str = "testpass123"):
    """
    Helper function to login a user and get JWT token.
    Returns the token string.
    """
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": password
        }
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    return None

def get_auth_headers(token: str):
    """
    Helper function to create authorization headers.
    """
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(scope="function")
def registered_user(client, unique_tenant_name, unique_email):
    """
    Fixture that provides a registered user with credentials.
    Returns a dict with tenant_name, email, password, and token.
    """
    tenant_name = unique_tenant_name
    email = unique_email
    password = "testpass123"
    
    # Register the user
    register_response = register_user(client, tenant_name, email, password)
    assert register_response.status_code == 200
    
    # Login to get token
    token = login_user(client, email, password)
    assert token is not None
    
    return {
        "tenant_name": tenant_name,
        "email": email,
        "password": password,
        "token": token,
        "user_data": register_response.json()
    }

@pytest.fixture(scope="function")
def two_tenants(client):
    """
    Fixture that provides two completely separate tenants with users.
    This is critical for testing cross-tenant isolation.
    """
    # Create Tenant A with User A
    tenant_a_name = f"Tenant-A-{uuid.uuid4().hex[:8]}"
    email_a = f"user-a-{uuid.uuid4().hex[:8]}@test.com"
    password_a = "testpass123"
    
    register_a = register_user(client, tenant_a_name, email_a, password_a)
    assert register_a.status_code == 200
    token_a = login_user(client, email_a, password_a)
    assert token_a is not None
    
    # Create Tenant B with User B
    tenant_b_name = f"Tenant-B-{uuid.uuid4().hex[:8]}"
    email_b = f"user-b-{uuid.uuid4().hex[:8]}@test.com"
    password_b = "testpass456"
    
    register_b = register_user(client, tenant_b_name, email_b, password_b)
    assert register_b.status_code == 200
    token_b = login_user(client, email_b, password_b)
    assert token_b is not None
    
    return {
        "tenant_a": {
            "name": tenant_a_name,
            "email": email_a,
            "password": password_a,
            "token": token_a,
            "user_data": register_a.json()
        },
        "tenant_b": {
            "name": tenant_b_name,
            "email": email_b,
            "password": password_b,
            "token": token_b,
            "user_data": register_b.json()
        }
    }


@pytest.fixture(scope="function")
def mock_redis():
    """
    Mock Redis client for Phase 4 testing.
    
    Provides in-memory Redis-like behavior without requiring
    an actual Redis instance for unit tests.
    """
    from unittest.mock import MagicMock
    
    mock = MagicMock()
    
    storage = {}
    
    def mock_set(key, value, ex=None):
        storage[key] = value
        return True
    
    def mock_setex(key, time, value):
        storage[key] = value
        return True
    
    def mock_get(key):
        return storage.get(key)
    
    def mock_delete(key):
        if key in storage:
            del storage[key]
        return 1
    
    def mock_exists(key):
        return 1 if key in storage else 0
    
    def mock_xadd(stream_name, fields, id='*', maxlen=None):
        if stream_name not in storage:
            storage[stream_name] = []
        storage[stream_name].append(fields)
        return f"{len(storage[stream_name])}-0"
    
    mock.set = mock_set
    mock.setex = mock_setex
    mock.get = mock_get
    mock.delete = mock_delete
    mock.exists = mock_exists
    mock.xadd = mock_xadd
    
    return mock


@pytest.fixture(scope="function")
def mock_duckdb():
    """
    Mock DuckDB connection for Phase 4 testing.
    
    Returns an in-memory DuckDB instance for testing
    without persisting data to disk.
    """
    import duckdb
    
    conn = duckdb.connect(':memory:')
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS dcl_metadata (
            tenant_id VARCHAR NOT NULL,
            source_id VARCHAR NOT NULL,
            metadata_json JSON NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    yield conn
    
    conn.close()


@pytest.fixture(scope="function")
def sample_canonical_event():
    """
    Sample CanonicalEvent with Phase 4 metadata for testing.
    
    Returns a valid EntityEvent with all Phase 4 fields populated:
    - schema_fingerprint
    - field_mappings
    - drift_status
    - repair_summary
    - data_lineage
    """
    from app.contracts.canonical_event import (
        EntityEvent, EventType, CanonicalEntityType,
        SchemaFingerprint, FieldMapping, DriftStatus,
        RepairSummary, DataLineage
    )
    from datetime import datetime
    
    fingerprint = SchemaFingerprint(
        fingerprint_hash="abc123def456",
        field_count=5,
        field_names=["id", "name", "amount", "stage", "close_date"],
        schema_version="v1.0",
        connector_name="salesforce",
        entity_type="Opportunity"
    )
    
    field_mapping = FieldMapping(
        source_field="Amount",
        canonical_field="amount",
        source_type="decimal",
        canonical_type="float",
        mapping_method="exact",
        confidence_score=0.95,
        transformation_function=None,
        semantic_similarity=None,
        human_verified=False
    )
    
    drift_status = DriftStatus(
        drift_detected=False,
        drift_event_id=None,
        drift_severity=None,
        drift_type=None,
        repair_attempted=False,
        repair_successful=False,
        requires_human_review=False
    )
    
    repair_summary = RepairSummary(
        repair_processed=False,
        auto_applied_count=0,
        hitl_queued_count=0,
        rejected_count=0,
        overall_confidence=None
    )
    
    lineage = DataLineage(
        source_system="Salesforce",
        source_connector_id="sf-conn-001",
        processing_stages=["ingestion", "normalization", "validation"],
        transformations_applied=["snake_case", "type_inference"],
        processor_version="1.0",
        data_quality_score=0.95
    )
    
    return EntityEvent(
        event_id="test-evt-001",
        event_type=EventType.ENTITY_CREATED,
        connector_name="salesforce",
        connector_id="sf-conn-001",
        entity_type=CanonicalEntityType.OPPORTUNITY,
        entity_id="SF-OPP-001",
        tenant_id="test-tenant-123",
        schema_fingerprint=fingerprint,
        payload={
            "opportunity_id": "SF-OPP-001",
            "name": "Test Deal",
            "amount": 50000.0,
            "stage": "Prospecting",
            "close_date": "2025-12-31"
        },
        field_mappings=[field_mapping],
        overall_confidence=0.95,
        raw_data=None,
        drift_status=drift_status,
        repair_summary=repair_summary,
        data_lineage=lineage
    )


@pytest.fixture(scope="function")
def sample_drift_scenario():
    """
    Sample drift scenario with old and new schema fingerprints.
    
    Returns a dict with:
    - old_fingerprint: Historical schema
    - new_fingerprint: Current schema with drift
    - expected_drift: Expected drift details
    """
    from app.contracts.canonical_event import SchemaFingerprint
    
    old_fingerprint = SchemaFingerprint(
        fingerprint_hash="old-hash-123",
        field_count=5,
        field_names=["id", "name", "amount", "stage", "close_date"],
        schema_version="v1.0",
        connector_name="salesforce",
        entity_type="Opportunity"
    )
    
    new_fingerprint = SchemaFingerprint(
        fingerprint_hash="new-hash-456",
        field_count=6,
        field_names=["id", "name", "amount", "stage", "close_date", "owner_id"],
        schema_version="v1.1",
        connector_name="salesforce",
        entity_type="Opportunity"
    )
    
    return {
        "old_fingerprint": old_fingerprint,
        "new_fingerprint": new_fingerprint,
        "expected_drift": {
            "added_fields": ["owner_id"],
            "removed_fields": [],
            "severity": "low"
        }
    }


@pytest.fixture(scope="function")
def mock_llm_response():
    """
    Mock LLM API response for repair agent testing.
    
    Returns a realistic LLM field mapping suggestion that
    the RepairAgent would receive from OpenAI/Gemini.
    """
    return {
        "field_name": "closeDate",
        "suggested_mapping": "close_date",
        "confidence": 0.92,
        "confidence_reason": "Strong semantic similarity: closeDate → close_date. Common CRM field pattern.",
        "transformation": "direct",
        "metadata": {
            "llm_model": "gemini-2.5-flash",
            "reasoning": "Field name suggests a date field for opportunity closure. Standard snake_case conversion."
        }
    }


# ===== DCL-SPECIFIC FIXTURES (Phase 2 Test Harness) =====

@pytest.fixture(scope="function")
def dcl_client(app, registered_user):
    """
    Fixture that provides a TestClient configured for DCL endpoint testing.
    
    Returns a tuple: (client, auth_headers, tenant_id)
    - client: FastAPI TestClient instance
    - auth_headers: Authorization headers with JWT token
    - tenant_id: Tenant ID extracted from registered user
    
    Args:
        app: Lazy-loaded FastAPI app fixture
        registered_user: Registered user fixture
    
    Usage:
        def test_dcl_state(dcl_client):
            client, headers, tenant_id = dcl_client
            response = client.get("/dcl/state", headers=headers)
            assert response.status_code == 200
    """
    client = TestClient(app)
    token = registered_user["token"]
    headers = get_auth_headers(token)
    
    # Extract tenant_id from user_data (UUID)
    user_data = registered_user["user_data"]
    tenant_id = str(user_data["tenant_id"])
    
    return (client, headers, tenant_id)


@pytest.fixture(scope="function")
def dcl_reset_state(dcl_client):
    """
    Fixture that resets DCL graph state before and after each test.
    
    This ensures test isolation and prevents state leakage between tests.
    Clears all DCL state including:
    - Graph nodes and edges
    - Source connections
    - Entity mappings
    - Agent state
    - Redis keys for tenant
    
    CRITICAL: This fixture must be used for all DCL state tests to prevent
    race conditions and ensure reproducibility.
    
    Usage:
        def test_something(dcl_reset_state):
            client, headers, tenant_id = dcl_reset_state
            # Test runs with clean slate
            # State automatically cleared after test completes
    """
    client, headers, tenant_id = dcl_client
    
    # Reset state before test
    from app.dcl_engine import state_access
    state_access.reset_all_state(tenant_id)
    
    # Clear Redis keys for this tenant (prevent cross-test state bleed)
    try:
        from shared.redis_client import get_redis_client
        redis_client = get_redis_client()
        
        # Clear all tenant-scoped Redis keys
        # Pattern: dcl:{tenant_id}:*
        pattern = f"dcl:{tenant_id}:*"
        cursor = 0
        while True:
            cursor, keys = redis_client.scan(cursor, match=pattern, count=100)
            if keys:
                redis_client.delete(*keys)
            if cursor == 0:
                break
    except Exception as e:
        # If Redis is unavailable, log warning but don't fail test
        # (tests may run without Redis in some environments)
        warnings.warn(f"Failed to clear Redis keys for tenant {tenant_id}: {e}")
    
    # Yield to test
    yield (client, headers, tenant_id)
    
    # Reset state after test (cleanup)
    state_access.reset_all_state(tenant_id)
    
    # Clear Redis keys after test
    try:
        from shared.redis_client import get_redis_client
        redis_client = get_redis_client()
        pattern = f"dcl:{tenant_id}:*"
        cursor = 0
        while True:
            cursor, keys = redis_client.scan(cursor, match=pattern, count=100)
            if keys:
                redis_client.delete(*keys)
            if cursor == 0:
                break
    except Exception:
        pass  # Silent cleanup failure


@pytest.fixture(scope="function")
def dcl_graph_with_sources(dcl_reset_state):
    """
    Fixture that provides a DCL client with known working graph state.
    
    Creates a reproducible graph state with:
    - 2 connected sources (salesforce, hubspot)
    - Graph nodes and edges representing entity mappings
    - Known entity sources for validation
    
    This is the baseline state used for contract/snapshot testing.
    
    Returns: (client, headers, tenant_id, expected_graph)
    
    UPDATED: Uses new /dcl/connect API signature (sources + agents parameters).
    """
    client, headers, tenant_id = dcl_reset_state
    
    # Connect sources using NEW API signature (sources + agents)
    # API expects comma-separated lists: sources=salesforce,hubspot&agents=revops_pilot
    connect_response = client.get(
        "/dcl/connect",
        params={
            "sources": "salesforce,hubspot",
            "agents": "revops_pilot",
            "llm_model": "gemini-2.5-flash"
        },
        headers=headers
    )
    
    # Verify sources connected successfully
    assert connect_response.status_code == 200, f"Connection failed: {connect_response.text}"
    
    # Fetch current graph state for baseline
    state_response = client.get("/dcl/state", headers=headers)
    assert state_response.status_code == 200
    expected_graph = state_response.json()
    
    return (client, headers, tenant_id, expected_graph)
