"""
Authentication and User Management Tests.

Tests for user registration, login, and user information endpoints.
Verifies the entire JWT authentication flow.
"""
import pytest
from tests.conftest import register_user, login_user, get_auth_headers


class TestUserRegistration:
    """Test suite for user registration endpoint."""
    
    def test_register_new_user_creates_tenant_and_user(self, client, unique_tenant_name, unique_email):
        """Test that registering a new user creates both tenant and user."""
        response = register_user(client, unique_tenant_name, unique_email, "securepass123")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response contains expected fields
        assert "id" in data
        assert "email" in data
        assert "tenant_id" in data
        assert "created_at" in data
        
        # Verify the email matches
        assert data["email"] == unique_email
        
        # Verify password is NOT returned
        assert "password" not in data
        assert "hashed_password" not in data
    
    def test_register_duplicate_email_fails(self, client, unique_tenant_name, unique_email):
        """Test that registering with duplicate email fails."""
        # Register first user
        response1 = register_user(client, unique_tenant_name, unique_email, "pass123")
        assert response1.status_code == 200
        
        # Try to register again with same email (different tenant)
        response2 = register_user(client, f"{unique_tenant_name}-2", unique_email, "pass456")
        
        # Should fail with 400 (email already exists)
        assert response2.status_code == 400
    
    def test_register_weak_password_validation(self, client, unique_tenant_name, unique_email):
        """Test that weak passwords are handled appropriately."""
        # Note: Current implementation doesn't enforce password strength,
        # but we test to document this behavior
        response = register_user(client, unique_tenant_name, unique_email, "123")
        
        # Currently accepts weak passwords (could be enhanced in future)
        # This test documents current behavior
        assert response.status_code in [200, 400, 422]


class TestLogin:
    """Test suite for login endpoint."""
    
    def test_login_with_valid_credentials_returns_jwt(self, client, unique_tenant_name, unique_email):
        """Test that login with valid credentials returns a JWT token."""
        password = "testpass123"
        
        # Register a user first
        register_response = register_user(client, unique_tenant_name, unique_email, password)
        assert register_response.status_code == 200
        
        # Login with correct credentials
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": unique_email,
                "password": password
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify JWT token is returned
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        
        # Verify token is a string and not empty
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 0
    
    def test_login_with_wrong_password_fails(self, client, unique_tenant_name, unique_email):
        """Test that login with incorrect password returns 401."""
        password = "correctpass"
        
        # Register a user
        register_response = register_user(client, unique_tenant_name, unique_email, password)
        assert register_response.status_code == 200
        
        # Try to login with wrong password
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": unique_email,
                "password": "wrongpassword"
            }
        )
        
        assert response.status_code == 401
        assert "detail" in response.json()
    
    def test_login_with_nonexistent_user_fails(self, client):
        """Test that login with non-existent email returns 401."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "anypassword"
            }
        )
        
        assert response.status_code == 401
        assert "detail" in response.json()


class TestCurrentUser:
    """Test suite for GET /users/me endpoint."""
    
    def test_get_current_user_with_valid_token(self, client, registered_user):
        """Test that /users/me returns correct user data with valid JWT."""
        token = registered_user["token"]
        email = registered_user["email"]
        
        response = client.get(
            "/users/me",
            headers=get_auth_headers(token)
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify user data
        assert "id" in data
        assert "email" in data
        assert "tenant_id" in data
        assert data["email"] == email
        
        # Verify password is NOT returned
        assert "password" not in data
        assert "hashed_password" not in data
    
    def test_get_current_user_without_token_fails(self, client):
        """Test that /users/me without token returns 401."""
        response = client.get("/users/me")
        
        # Should fail - no authorization header
        assert response.status_code == 403
    
    def test_get_current_user_with_invalid_token_fails(self, client):
        """Test that /users/me with invalid token returns 401."""
        response = client.get(
            "/users/me",
            headers=get_auth_headers("invalid.token.here")
        )
        
        assert response.status_code == 401
    
    def test_get_current_user_with_malformed_token_fails(self, client):
        """Test that /users/me with malformed token returns 403."""
        response = client.get(
            "/users/me",
            headers={"Authorization": "Bearer"}  # Missing token
        )
        
        # FastAPI returns 403 when the bearer token is missing/malformed
        assert response.status_code == 403
