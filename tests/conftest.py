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
    try:
        db = TestingSessionLocal()
        yield db
    finally:
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
