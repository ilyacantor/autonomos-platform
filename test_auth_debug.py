#!/usr/bin/env python3
"""
Minimal test to debug authentication issue in test harness.
"""
import os
os.environ['DCL_AUTH_ENABLED'] = 'true'

from fastapi.testclient import TestClient
from app.main import app
from tests.conftest import override_get_db, get_auth_headers, TestingSessionLocal
from app.database import get_db
import uuid

# Override database dependency on MAIN app
app.dependency_overrides[get_db] = override_get_db

# Override database dependency on DCL sub-app (CRITICAL!)
try:
    from app.dcl_engine.app import app as dcl_app
    dcl_app.dependency_overrides[get_db] = override_get_db
    print("✓ Overrode database dependency on DCL sub-app")
except Exception as e:
    print(f"✗ Failed to override DCL app: {e}")

client = TestClient(app)

# Generate unique credentials
tenant_name = f"Test-Debug-{uuid.uuid4().hex[:8]}"
email = f"debug-{uuid.uuid4().hex[:8]}@test.com"
password = "testpass123"

print(f"1. Registering user: {email}")
register_response = client.post(
    "/users/register",
    json={
        "name": tenant_name,
        "email": email,
        "password": password
    }
)
print(f"   Status: {register_response.status_code}")
print(f"   Response: {register_response.json()}")

if register_response.status_code != 200:
    print("REGISTRATION FAILED")
    exit(1)

user_data = register_response.json()
user_id = user_data["id"]
tenant_id = user_data["tenant_id"]

print(f"\n2. User created - ID: {user_id}, Tenant: {tenant_id}")

# Login to get token
print(f"\n3. Logging in with email: {email}")
login_response = client.post(
    "/api/v1/auth/login",
    json={
        "email": email,
        "password": password
    }
)
print(f"   Status: {login_response.status_code}")

if login_response.status_code != 200:
    print(f"LOGIN FAILED: {login_response.text}")
    exit(1)

token = login_response.json()["access_token"]
print(f"   Token: {token[:50]}...")

# Verify user exists in database
print(f"\n4. Verifying user in database")
db = TestingSessionLocal()
from app.models import User
from uuid import UUID
db_user = db.query(User).filter(User.id == UUID(user_id)).first()
if db_user:
    print(f"   ✓ User found in DB: {db_user.email}, Tenant: {db_user.tenant_id}")
else:
    print(f"   ✗ User NOT found in DB!")
db.close()

# Test DCL endpoint with auth
print(f"\n5. Testing /dcl/state endpoint")
headers = get_auth_headers(token)
print(f"   Headers: {headers}")

state_response = client.get("/dcl/state", headers=headers)
print(f"   Status: {state_response.status_code}")
if state_response.status_code != 200:
    print(f"   Error: {state_response.text}")
else:
    print(f"   ✓ Success!")

print("\n" + "="*60)
if state_response.status_code == 200:
    print("TEST PASSED: Authentication working correctly")
else:
    print("TEST FAILED: Authentication broken")
    exit(1)
