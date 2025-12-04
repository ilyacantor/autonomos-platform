"""
Tests for health check endpoints (P3-11)

Validates:
- /health/live - Liveness probe
- /health/ready - Readiness probe with dependency checks
- /health/intelligence - DCL intelligence services health
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient


class TestLivenessProbe:
    """Test /health/live endpoint"""
    
    def test_liveness_returns_ok(self, client: TestClient):
        """Liveness probe should always return 200 if process is running"""
        response = client.get("/health/live")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data
        
        # Verify timestamp is ISO format
        timestamp = datetime.fromisoformat(data["timestamp"])
        assert isinstance(timestamp, datetime)


class TestReadinessProbe:
    """Test /health/ready endpoint with dependency validation"""
    
    def test_ready_when_all_dependencies_healthy(self, client: TestClient, db_session):
        """Readiness should return 200 when all dependencies are healthy"""
        with patch("app.main.redis_conn") as mock_redis:
            mock_redis.ping.return_value = True
            
            # Mock circuit breaker states (all CLOSED)
            with patch("app.dcl_engine.services.resilience.get_circuit_breaker_states") as mock_breakers:
                mock_breakers.return_value = {
                    "llm_proposal": {"state": "CLOSED", "failure_count": 0},
                    "rag_lookup": {"state": "CLOSED", "failure_count": 0},
                    "confidence_scoring": {"state": "CLOSED", "failure_count": 0}
                }
                
                response = client.get("/health/ready")
                
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "ready"
                assert data["checks"]["database"]["status"] == "ok"
                assert data["checks"]["redis"]["status"] == "ok"
                assert data["checks"]["circuit_breakers"]["status"] == "ok"
    
    def test_ready_degraded_when_critical_breaker_open(self, client: TestClient, db_session):
        """Readiness should return 503 when critical circuit breakers are open"""
        with patch("app.main.redis_conn") as mock_redis:
            mock_redis.ping.return_value = True
            
            # Mock circuit breaker states (LLM breaker OPEN)
            with patch("app.dcl_engine.services.resilience.get_circuit_breaker_states") as mock_breakers:
                mock_breakers.return_value = {
                    "llm_proposal": {"state": "OPEN", "failure_count": 5},
                    "rag_lookup": {"state": "CLOSED", "failure_count": 0}
                }
                
                response = client.get("/health/ready")
                
                assert response.status_code == 503
                data = response.json()
                assert data["status"] == "degraded"
                assert data["checks"]["circuit_breakers"]["status"] == "degraded"
                assert "llm_proposal" in data["checks"]["circuit_breakers"]["open_breakers"]
    
    def test_ready_degraded_when_database_fails(self, client: TestClient):
        """Readiness should return 503 when database connection fails"""
        with patch("app.main.get_db") as mock_get_db:
            # Mock database session that raises exception
            mock_session = MagicMock()
            mock_session.execute.side_effect = Exception("Connection refused")
            mock_get_db.return_value = iter([mock_session])
            
            with patch("app.main.redis_conn") as mock_redis:
                mock_redis.ping.return_value = True
                
                with patch("app.dcl_engine.services.resilience.get_circuit_breaker_states") as mock_breakers:
                    mock_breakers.return_value = {}
                    
                    response = client.get("/health/ready")
                    
                    assert response.status_code == 503
                    data = response.json()
                    assert data["status"] == "degraded"
                    assert data["checks"]["database"]["status"] == "failed"
    
    def test_ready_degraded_when_redis_fails(self, client: TestClient, db_session):
        """Readiness should return 503 when Redis connection fails"""
        with patch("app.main.redis_conn") as mock_redis:
            mock_redis.ping.side_effect = Exception("Redis unavailable")
            
            with patch("app.dcl_engine.services.resilience.get_circuit_breaker_states") as mock_breakers:
                mock_breakers.return_value = {}
                
                response = client.get("/health/ready")
                
                assert response.status_code == 503
                data = response.json()
                assert data["status"] == "degraded"
                assert data["checks"]["redis"]["status"] == "failed"


class TestIntelligenceHealth:
    """Test /health/intelligence endpoint"""
    
    def test_intelligence_healthy_when_all_services_available(self, client: TestClient):
        """Intelligence health should return healthy when all breakers are CLOSED"""
        with patch("app.dcl_engine.services.resilience.get_circuit_breaker_states") as mock_breakers:
            mock_breakers.return_value = {
                "llm_proposal": {"state": "CLOSED", "failure_count": 0},
                "rag_lookup": {"state": "CLOSED", "failure_count": 0},
                "confidence_scoring": {"state": "CLOSED", "failure_count": 0}
            }
            
            with patch("app.dcl_engine.services.resilience.get_all_bulkheads") as mock_bulkheads:
                mock_bulkheads.return_value = {
                    "llm": {"active_count": 2, "max_concurrent": 10},
                    "database": {"active_count": 5, "max_concurrent": 50},
                    "rag": {"active_count": 1, "max_concurrent": 20}
                }
                
                response = client.get("/health/intelligence")
                
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "healthy"
                assert len(data["open_breakers"]) == 0
                assert data["services"]["llm_proposal"] == "available"
                assert data["services"]["rag_lookup"] == "available"
                assert data["services"]["confidence_scoring"] == "available"
                assert "circuit_breakers" in data
                assert "bulkheads" in data
    
    def test_intelligence_degraded_when_breaker_open(self, client: TestClient):
        """Intelligence health should return degraded when any breaker is OPEN"""
        with patch("app.dcl_engine.services.resilience.get_circuit_breaker_states") as mock_breakers:
            mock_breakers.return_value = {
                "llm_proposal": {"state": "OPEN", "failure_count": 5},
                "rag_lookup": {"state": "CLOSED", "failure_count": 0},
                "confidence_scoring": {"state": "HALF_OPEN", "failure_count": 3}
            }
            
            with patch("app.dcl_engine.services.resilience.get_all_bulkheads") as mock_bulkheads:
                mock_bulkheads.return_value = {
                    "llm": {"active_count": 0, "max_concurrent": 10},
                    "database": {"active_count": 0, "max_concurrent": 50}
                }
                
                response = client.get("/health/intelligence")
                
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "degraded"
                assert "llm_proposal" in data["open_breakers"]
                assert data["services"]["llm_proposal"] == "degraded"
                assert data["services"]["rag_lookup"] == "available"
    
    def test_intelligence_error_when_resilience_module_fails(self, client: TestClient):
        """Intelligence health should return 500 when resilience module fails"""
        with patch("app.dcl_engine.services.resilience.get_circuit_breaker_states") as mock_breakers:
            mock_breakers.side_effect = Exception("Module not initialized")
            
            response = client.get("/health/intelligence")
            
            assert response.status_code == 500
            data = response.json()
            assert data["status"] == "error"
            assert "error" in data
            assert "Module not initialized" in data["error"]


@pytest.fixture
def client():
    """Create test client for FastAPI app"""
    from app.main import app
    from fastapi.testclient import TestClient
    return TestClient(app)


@pytest.fixture
def db_session():
    """Mock database session that succeeds"""
    from unittest.mock import MagicMock
    session = MagicMock()
    session.execute.return_value = None
    
    with patch("app.main.get_db") as mock_get_db:
        mock_get_db.return_value = iter([session])
        yield session
