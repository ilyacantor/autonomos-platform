"""
Shared pytest fixtures for AutonomOS multi-tenant testing.
"""
import os
import uuid

# CRITICAL: Enable authentication for tests BEFORE importing app modules
# This must be set before app.security is loaded to properly validate JWT tokens
# Without this, all requests use MockUser and security tests cannot function
os.environ['DCL_AUTH_ENABLED'] = 'true'

# CRITICAL: Disable rate limiting for tests BEFORE importing app modules
# This prevents 429 Rate Limit errors during rapid automated testing
# SlowAPI rate limiter checks for TESTING environment variable
os.environ['TESTING'] = 'true'

# NOTE: FEATURE_USE_AAM_AS_SOURCE is NOT set globally (removed to restore AAM test coverage)
# Tests can opt into AAM or demo_files mode via fixtures:
# - Use demo_files_mode fixture for tests needing consistent CSV data
# - Use aam_mode fixture for tests validating AAM behavior
# - Default: Tests use whatever mode is currently configured

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
    
    # CRITICAL: Disable rate limiting for tests
    # This prevents 429 errors during rapid automated testing
    # SlowAPI stores rate limiter in app.state.limiter
    try:
        from slowapi import Limiter
        from slowapi.util import get_remote_address
        # Replace production limiter with unlimited test limiter
        _app.state.limiter = Limiter(
            key_func=get_remote_address,
            default_limits=["999999999/minute"]  # Effectively unlimited
        )
        print("[TEST_SETUP] ✅ Rate limiting disabled for test suite", flush=True)
    except Exception as e:
        warnings.warn(f"Could not disable rate limiter: {e}")
    
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

def register_user(client: TestClient, tenant_name: str, email: str, password: str = "testpass123", is_admin: bool = False):
    """
    Helper function to register a new user and tenant.
    Returns the registration response.
    
    Args:
        is_admin: If True, grants admin privileges to the user (for integration tests needing POST /dcl/mappings)
    """
    response = client.post(
        "/users/register",
        json={
            "name": tenant_name,
            "email": email,
            "password": password
        }
    )
    
    # Grant admin privileges if requested (test environment only)
    if is_admin and response.status_code == 201:
        from app.database import get_db
        from app.models import User
        db = next(get_db())
        try:
            user = db.query(User).filter(User.email == email).first()
            if user:
                user.is_admin = 'true'
                db.commit()
        finally:
            db.close()
    
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

def create_test_connector_and_schema(tenant_id: str, connector_name: str = "test_connector"):
    """
    Helper function to create test connector and entity schema in database.
    Returns (connector_id, entity_schema_id).
    
    Used by integration tests to set up mapping registry prerequisites.
    
    IMPORTANT: Uses TestingSessionLocal() to access test database, not production get_db().
    """
    from app.models import ConnectorDefinition, EntitySchema
    import uuid
    
    db = TestingSessionLocal()
    try:
        # Create entity schema with unique name to avoid constraint violations
        unique_suffix = str(uuid.uuid4())[:8]
        entity_schema = EntitySchema(
            id=str(uuid.uuid4()),
            entity_name=f"test_entity_{unique_suffix}",
            entity_version="1.0.0",
            schema_definition={"type": "object", "properties": {}},
            description="Test entity schema"
        )
        db.add(entity_schema)
        db.flush()
        
        # Create connector definition
        connector = ConnectorDefinition(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            connector_name=connector_name,
            connector_type="api",
            description=f"Test {connector_name} connector",
            metadata={},
            status="active"
        )
        db.add(connector)
        db.commit()
        
        return (str(connector.id), str(entity_schema.id))
    finally:
        db.close()

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
    print(f"\n[AUTH_DEBUG] Attempting registration:", flush=True)
    print(f"[AUTH_DEBUG]   URL: /users/register", flush=True)
    print(f"[AUTH_DEBUG]   Tenant: {tenant_name}", flush=True)
    print(f"[AUTH_DEBUG]   Email: {email}", flush=True)
    
    register_response = register_user(client, tenant_name, email, password)
    
    print(f"[AUTH_DEBUG] Registration response:", flush=True)
    print(f"[AUTH_DEBUG]   Status Code: {register_response.status_code}", flush=True)
    print(f"[AUTH_DEBUG]   Response Body: {register_response.text}", flush=True)
    
    assert register_response.status_code == 200, \
        f"Registration failed: {register_response.status_code} - {register_response.text}"
    
    # Login to get token
    print(f"\n[AUTH_DEBUG] Attempting login:", flush=True)
    print(f"[AUTH_DEBUG]   URL: /api/v1/auth/login", flush=True)
    print(f"[AUTH_DEBUG]   Email: {email}", flush=True)
    
    # Get detailed login response
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password}
    )
    
    print(f"[AUTH_DEBUG] Login response:", flush=True)
    print(f"[AUTH_DEBUG]   Status Code: {login_response.status_code}", flush=True)
    print(f"[AUTH_DEBUG]   Response Body: {login_response.text}", flush=True)
    
    if login_response.status_code == 200:
        token = login_response.json().get("access_token")
        print(f"[AUTH_DEBUG]   Token extracted: {'YES' if token else 'NO'}", flush=True)
    else:
        token = None
        print(f"[AUTH_DEBUG]   Login FAILED - no token", flush=True)
    
    assert token is not None, \
        f"Login failed to return token: {login_response.status_code} - {login_response.text}"
    
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


@pytest.fixture(scope="function")
def populate_aam_redis_data(request):
    """
    Populate Redis with AAM test data for the test tenant.
    
    This fixture enables tests to run with AAM-mode data by populating
    Redis streams before the test executes.
    
    Usage:
        @pytest.mark.parametrize("populate_aam_redis_data", [["salesforce", "hubspot"]], indirect=True)
        def test_with_aam_data(dcl_reset_state, populate_aam_redis_data):
            # Test will have AAM data in Redis streams
            client, headers, tenant_id = dcl_reset_state
            # ... test code ...
    
    Args:
        request: Pytest request object with:
            - request.param: List of source IDs to populate (default: ['salesforce', 'hubspot'])
            - request.tenant_id: Tenant ID (set by dcl_reset_state fixture)
    
    Yields:
        List of populated stream keys
    """
    from shared.redis_client import get_redis_client
    from tests.fixtures.aam_data import (
        get_salesforce_aam_data,
        get_hubspot_aam_data,
        get_dynamics_aam_data
    )
    import json
    
    # Get tenant_id from test context (set by dcl_reset_state fixture)
    tenant_id = getattr(request, 'tenant_id', 'test-tenant-default')
    
    # Map source names to data functions
    data_functions = {
        'salesforce': get_salesforce_aam_data,
        'hubspot': get_hubspot_aam_data,
        'dynamics': get_dynamics_aam_data
    }
    
    # Get sources to populate (passed as parameter)
    sources = getattr(request, 'param', ['salesforce', 'hubspot'])
    
    redis_client = get_redis_client()
    populated_streams = []
    
    try:
        # Populate each source
        for source_id in sources:
            if source_id not in data_functions:
                warnings.warn(f"Unknown source '{source_id}' - skipping AAM data population")
                continue
                
            stream_key = f"aam:dcl:{tenant_id}:{source_id}"
            
            # Get test data for this source
            events = data_functions[source_id]()
            
            # Add each event to Redis stream
            for event in events:
                message_id = redis_client._client.xadd(
                    stream_key,
                    {'payload': json.dumps(event)}
                )
                print(f"[TEST_SETUP] Added AAM event to {stream_key}: {message_id}", flush=True)
            
            populated_streams.append(stream_key)
            print(f"[TEST_SETUP] ✅ Populated {len(events)} events in stream {stream_key}", flush=True)
        
        yield populated_streams
        
    finally:
        # Cleanup: Delete test streams
        for stream_key in populated_streams:
            try:
                redis_client._client.delete(stream_key)
                print(f"[TEST_CLEANUP] Deleted stream {stream_key}", flush=True)
            except Exception as e:
                print(f"[TEST_CLEANUP] Failed to delete stream {stream_key}: {e}", flush=True)


# ===== FEATURE FLAG MODE FIXTURES =====

@pytest.fixture(scope="function")
def demo_files_mode():
    """
    Force demo_files mode for tests that need consistent CSV data.
    
    This fixture:
    1. Saves the current FEATURE_USE_AAM_AS_SOURCE ENV value
    2. Sets the ENV variable to 'false' (demo_files mode) for the test
    3. Restores the original value after the test completes
    
    Usage:
        def test_dcl_with_csv_data(dcl_reset_state, demo_files_mode):
            # This test will use CSV demo files regardless of global config
            client, headers, tenant_id = dcl_reset_state
            # Test uses CSV files from app/dcl_engine/schemas/
    
    Why: DCL workflow tests expect consistent CSV schema/data and should not
    be affected by AAM connector state. This fixture ensures they always use
    the known-good CSV files.
    
    Implementation: Sets ENV variable directly (highest precedence level)
    to guarantee it works even without Redis availability.
    """
    import os
    
    # Save current ENV value (may be None)
    env_var = "FEATURE_USE_AAM_AS_SOURCE"
    original_value = os.environ.get(env_var)
    
    # Force demo_files mode (False) via ENV variable
    os.environ[env_var] = 'false'
    print(f"[TEST_SETUP] ✅ demo_files_mode: Set {env_var}=false", flush=True)
    
    yield
    
    # Restore original value
    if original_value is None:
        # Was not set before, remove it
        os.environ.pop(env_var, None)
        print(f"[TEST_CLEANUP] ✅ demo_files_mode: Removed {env_var}", flush=True)
    else:
        # Restore original value
        os.environ[env_var] = original_value
        print(f"[TEST_CLEANUP] ✅ demo_files_mode: Restored {env_var}={original_value}", flush=True)


@pytest.fixture(scope="function")
def aam_mode(request):
    """
    Enable AAM mode for tests that validate AAM behavior.
    
    This fixture:
    1. Saves the current FEATURE_USE_AAM_AS_SOURCE ENV value
    2. Sets the ENV variable to 'true' (AAM mode) for the test
    3. Ensures Redis streams are populated with test data (if tenant_id available)
    4. Restores the original value after the test completes
    
    Usage:
        def test_aam_connector_behavior(dcl_reset_state, aam_mode):
            # This test will use AAM connectors with Redis streams
            client, headers, tenant_id = dcl_reset_state
            # Test validates AAM-specific behavior
            
            # IMPORTANT: Assert the flag is enabled to catch regressions
            from app.config.feature_flags import FeatureFlagConfig, FeatureFlag
            assert FeatureFlagConfig.is_enabled(FeatureFlag.USE_AAM_AS_SOURCE)
    
    Why: AAM tests need to validate AAM connector behavior, drift detection,
    and canonical event processing. This fixture ensures they run in AAM mode
    with properly populated Redis streams.
    
    Implementation: Sets ENV variable directly (highest precedence level)
    to guarantee it works even without Redis availability.
    """
    import os
    from shared.redis_client import get_redis_client
    from tests.fixtures.aam_data import get_salesforce_aam_data, get_hubspot_aam_data
    import json
    
    # Save current ENV value (may be None)
    env_var = "FEATURE_USE_AAM_AS_SOURCE"
    original_value = os.environ.get(env_var)
    
    # Force AAM mode (True) via ENV variable
    os.environ[env_var] = 'true'
    print(f"[TEST_SETUP] ✅ aam_mode: Set {env_var}=true", flush=True)
    
    # Populate Redis streams if tenant_id is available
    populated_streams = []
    tenant_id = getattr(request, 'tenant_id', None)
    
    if tenant_id:
        try:
            redis_client = get_redis_client()
            
            # Populate Salesforce stream
            sf_stream = f"aam:dcl:{tenant_id}:salesforce"
            for event in get_salesforce_aam_data():
                redis_client._client.xadd(sf_stream, {'payload': json.dumps(event)})
            populated_streams.append(sf_stream)
            print(f"[TEST_SETUP] ✅ aam_mode: Populated stream {sf_stream}", flush=True)
            
            # Populate HubSpot stream
            hs_stream = f"aam:dcl:{tenant_id}:hubspot"
            for event in get_hubspot_aam_data():
                redis_client._client.xadd(hs_stream, {'payload': json.dumps(event)})
            populated_streams.append(hs_stream)
            print(f"[TEST_SETUP] ✅ aam_mode: Populated stream {hs_stream}", flush=True)
            
        except Exception as e:
            print(f"[TEST_SETUP] ⚠️ aam_mode: Failed to populate Redis streams: {e}", flush=True)
    
    yield
    
    # Cleanup: Delete test streams
    if populated_streams:
        try:
            redis_client = get_redis_client()
            for stream_key in populated_streams:
                redis_client._client.delete(stream_key)
                print(f"[TEST_CLEANUP] ✅ aam_mode: Deleted stream {stream_key}", flush=True)
        except Exception as e:
            print(f"[TEST_CLEANUP] ⚠️ aam_mode: Failed to delete streams: {e}", flush=True)
    
    # Restore original ENV value
    if original_value is None:
        # Was not set before, remove it
        os.environ.pop(env_var, None)
        print(f"[TEST_CLEANUP] ✅ aam_mode: Removed {env_var}", flush=True)
    else:
        # Restore original value
        os.environ[env_var] = original_value
        print(f"[TEST_CLEANUP] ✅ aam_mode: Restored {env_var}={original_value}", flush=True)


# ===== DCL FIXTURES REMOVED =====
# DCL v1 was removed. DCL v2 is now an external service.
# Legacy DCL fixtures (dcl_client, dcl_reset_state, dcl_graph_with_sources) 
# were deleted as part of the DCL v1 removal migration.


# ===== BULK MAPPING JOB TEST FIXTURES =====

@pytest.fixture
def redis_client():
    """Redis client fixture for testing"""
    from shared.redis_client import get_redis_client
    return get_redis_client()


@pytest.fixture
def job_state(redis_client):
    """BulkMappingJobState fixture"""
    if redis_client is None:
        pytest.skip("Redis not available for job state tests")
    from services.mapping_intelligence.job_state import BulkMappingJobState
    return BulkMappingJobState(redis_client)


@pytest.fixture
def test_tenant_id():
    """Test tenant ID fixture"""
    return "test-tenant-123"


@pytest.fixture
def test_connector_ids():
    """Test connector IDs fixture"""
    return ["conn-1", "conn-2", "conn-3"]


@pytest.fixture
async def clean_redis_state(redis_client, test_tenant_id):
    """Clean Redis state before/after tests"""
    if redis_client is None:
        pytest.skip("Redis not available for state cleanup")
    
    # Clean before
    pattern = f"job:*:tenant:{test_tenant_id}:*"
    for key in redis_client.scan_iter(match=pattern):
        redis_client.delete(key)
    
    yield
    
    # Clean after
    for key in redis_client.scan_iter(match=pattern):
        redis_client.delete(key)
