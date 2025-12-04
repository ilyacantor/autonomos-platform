"""
Smoke tests for AAM Connections and NLP Persona Routing.

Tests for:
- Tenant guards on AAM connectors endpoint
- Connectors list returning database rows
- NLP persona routing with auto classification
"""
import pytest
from tests.conftest import register_user, login_user, get_auth_headers


class TestAAMConnectorsTenantGuard:
    """Test suite for AAM connectors tenant authentication."""
    
    def test_aam_connectors_list_requires_tenant(self, client, unique_tenant_name, unique_email):
        """Test that /api/v1/aam/connectors returns 401 without JWT."""
        # Try to access without JWT token
        response = client.get("/api/v1/aam/connectors")
        
        # Should return 401 Unauthorized (middleware catches this before endpoint)
        assert response.status_code == 401
        assert "authorization" in response.json()["detail"].lower() or "missing tenant_id" in response.json()["detail"].lower()
    
    def test_aam_connectors_list_with_jwt_returns_200(self, client, unique_tenant_name, unique_email):
        """Test that /api/v1/aam/connectors returns 200 with valid JWT."""
        # Register and login to get JWT
        register_user(client, unique_tenant_name, unique_email, "testpass123")
        token = login_user(client, unique_email, "testpass123")
        headers = get_auth_headers(token)
        
        # Access with JWT token
        response = client.get("/api/v1/aam/connectors", headers=headers)
        
        # Should return 200 OK
        assert response.status_code == 200
        data = response.json()
        assert "connectors" in data
        assert "total" in data
        assert isinstance(data["connectors"], list)


class TestAAMConnectorsList:
    """Test suite for AAM connectors list endpoint."""
    
    def test_aam_connectors_list_returns_rows(self, client, unique_tenant_name, unique_email):
        """Test that /api/v1/aam/connectors returns existing connector rows."""
        # Register and login
        register_user(client, unique_tenant_name, unique_email, "testpass123")
        token = login_user(client, unique_email, "testpass123")
        headers = get_auth_headers(token)
        
        # Get connectors list
        response = client.get("/api/v1/aam/connectors", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        # Should return a list (may be empty for new tenant, or have seeded data)
        assert isinstance(data["connectors"], list)
        assert data["total"] == len(data["connectors"])
        
        # If connectors exist, verify structure
        if len(data["connectors"]) > 0:
            connector = data["connectors"][0]
            assert "id" in connector
            assert "name" in connector
            assert "type" in connector
            assert "status" in connector
            assert "mapping_count" in connector


class TestNLPPersonaRouting:
    """Test suite for NLP persona routing and classification."""
    
    def test_nlp_query_with_explicit_persona_returns_same_persona(self, client):
        """Test that POST /nlp/v1/query with persona=coo returns resolved_persona='coo'."""
        # Send query with explicit persona
        response = client.post(
            "/nlp/v1/query",
            json={
                "query": "Show me the cloud spend",
                "persona": "coo"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "response" in data
        assert "resolved_persona" in data
        assert "routing" in data
        
        # Verify persona matches
        assert data["resolved_persona"] == "coo"
        
        # Verify routing metadata
        assert "tags" in data["routing"]
        assert "classification_confidence" in data["routing"]
        assert data["routing"]["classification_confidence"] == 1.0  # Explicit persona = 100% confidence
    
    def test_nlp_query_auto_classification_with_keywords(self, client):
        """Test that POST /nlp/v1/query with persona=auto classifies based on keywords."""
        # Send query with COO keywords
        response = client.post(
            "/nlp/v1/query",
            json={
                "query": "What is our cloud spend and budget variance?",
                "persona": "auto"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should classify as COO based on "spend" and "budget" keywords
        assert data["resolved_persona"] == "coo"
        
        # Should have matched keywords
        assert len(data["routing"]["matched_keywords"]) > 0
        assert any(kw in ["spend", "budget", "cloud"] for kw in data["routing"]["matched_keywords"])
        
        # Confidence should be > 0 since keywords matched
        assert data["routing"]["classification_confidence"] > 0.0
    
    def test_nlp_query_auto_classification_no_keywords(self, client):
        """Test that POST /nlp/v1/query with persona=auto falls back to default when no keywords match."""
        # Send query with no persona-specific keywords
        response = client.post(
            "/nlp/v1/query",
            json={
                "query": "Hello, how are you?",
                "persona": "auto"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should fall back to default persona (CTO)
        assert data["resolved_persona"] == "cto"
        
        # Should have zero confidence since no keywords matched
        assert data["routing"]["classification_confidence"] == 0.0
        assert len(data["routing"]["matched_keywords"]) == 0
    
    def test_nlp_query_includes_persona_tags(self, client):
        """Test that NLP query response includes correct persona tags."""
        # Test CTO persona tags
        response_cto = client.post(
            "/nlp/v1/query",
            json={"query": "Show connector drift", "persona": "cto"}
        )
        assert response_cto.status_code == 200
        assert "kb:persona:cto" in response_cto.json()["routing"]["tags"]
        assert "kb:global" in response_cto.json()["routing"]["tags"]
        
        # Test COO persona tags (should include finops)
        response_coo = client.post(
            "/nlp/v1/query",
            json={"query": "Show cloud spend", "persona": "coo"}
        )
        assert response_coo.status_code == 200
        assert "kb:persona:coo" in response_coo.json()["routing"]["tags"]
        assert "kb:finops" in response_coo.json()["routing"]["tags"]
        assert "kb:global" in response_coo.json()["routing"]["tags"]
