"""
Shared pytest fixtures for AutonomOS multi-tenant testing.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import get_db
from app.models import Base
from app.config import settings
import uuid

# Create a test database engine
# NOTE: On Replit, DATABASE_URL points to the development database (not production)
# Tests use unique tenant names (UUID-based) to avoid conflicts with manual testing
# For true production isolation, set TEST_DATABASE_URL environment variable
import os
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", settings.DATABASE_URL)
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

# Override the dependency
app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="function")
def client():
    """
    Create a test client for making API requests.
    Each test gets a fresh client.
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
        "/token",
        data={
            "username": email,
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
