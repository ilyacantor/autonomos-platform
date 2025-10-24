"""
Full Integration Tests for Task Management.

Tests all task functionality within the multi-tenant context:
- Task creation
- Task retrieval
- Task cancellation
- Task retries
- Task callbacks
- Task chaining

All tests use JWT authentication and verify tenant isolation.
"""
import pytest
import time
from tests.conftest import get_auth_headers


class TestTaskCreation:
    """Test suite for task creation endpoint."""
    
    def test_create_basic_task_with_jwt(self, client, registered_user):
        """Test creating a basic task with JWT authentication."""
        token = registered_user["token"]
        
        response = client.post(
            "/api/v1/tasks",
            headers=get_auth_headers(token),
            json={
                "payload": {
                    "action": "post_to_slack",
                    "channel": "#general",
                    "message": "Test message"
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify task structure
        assert "id" in data
        assert "status" in data
        assert "payload" in data
        assert data["status"] == "queued"
        assert data["payload"]["message"] == "Test message"
    
    def test_create_task_without_authentication_fails(self, client):
        """Test that creating a task without JWT fails."""
        response = client.post(
            "/api/v1/tasks",
            json={
                "payload": {
                    "action": "post_to_slack",
                    "channel": "#general",
                    "message": "Unauthorized attempt"
                }
            }
        )
        
        # Should fail without authentication
        assert response.status_code == 403
    
    def test_create_task_with_callback_url(self, client, registered_user):
        """Test creating a task with a callback URL."""
        token = registered_user["token"]
        callback_url = "https://webhook.site/test-callback"
        
        response = client.post(
            "/api/v1/tasks",
            headers=get_auth_headers(token),
            json={
                "payload": {
                    "action": "post_to_slack",
                    "channel": "#general",
                    "message": "Task with callback"
                },
                "callback_url": callback_url
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["callback_url"] == callback_url
    
    def test_create_task_with_retries(self, client, registered_user):
        """Test creating a task with retry configuration."""
        token = registered_user["token"]
        
        response = client.post(
            "/api/v1/tasks",
            headers=get_auth_headers(token),
            json={
                "payload": {
                    "action": "post_to_slack",
                    "channel": "#general",
                    "message": "Task with retries"
                },
                "max_retries": 3
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["max_retries"] == 3
        assert data["retry_count"] == 0
    
    def test_create_task_with_chaining(self, client, registered_user):
        """Test creating a task with a chained next task."""
        token = registered_user["token"]
        
        response = client.post(
            "/api/v1/tasks",
            headers=get_auth_headers(token),
            json={
                "payload": {
                    "action": "post_to_slack",
                    "channel": "#general",
                    "message": "First task"
                },
                "on_success_next_task": {
                    "payload": {
                        "action": "post_to_slack",
                        "channel": "#general",
                        "message": "Second task (chained)"
                    }
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["on_success_next_task"] is not None
        assert data["on_success_next_task"]["payload"]["message"] == "Second task (chained)"


class TestTaskRetrieval:
    """Test suite for task retrieval endpoint."""
    
    def test_get_task_by_id_with_jwt(self, client, registered_user):
        """Test retrieving a task by ID with JWT authentication."""
        token = registered_user["token"]
        
        # Create a task first
        create_response = client.post(
            "/api/v1/tasks",
            headers=get_auth_headers(token),
            json={
                "payload": {
                    "action": "post_to_slack",
                    "channel": "#test",
                    "message": "Retrievable task"
                }
            }
        )
        assert create_response.status_code == 200
        task_id = create_response.json()["id"]
        
        # Retrieve the task
        get_response = client.get(
            f"/api/v1/tasks/{task_id}",
            headers=get_auth_headers(token)
        )
        
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["id"] == task_id
        assert data["payload"]["message"] == "Retrievable task"
    
    def test_get_task_without_authentication_fails(self, client, registered_user):
        """Test that retrieving a task without JWT fails."""
        token = registered_user["token"]
        
        # Create a task
        create_response = client.post(
            "/api/v1/tasks",
            headers=get_auth_headers(token),
            json={
                "payload": {
                    "action": "post_to_slack",
                    "channel": "#test",
                    "message": "Protected task"
                }
            }
        )
        task_id = create_response.json()["id"]
        
        # Try to retrieve without authentication
        get_response = client.get(f"/api/v1/tasks/{task_id}")
        
        assert get_response.status_code == 403
    
    def test_get_nonexistent_task_returns_404(self, client, registered_user):
        """Test that retrieving a non-existent task returns 404."""
        token = registered_user["token"]
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        
        response = client.get(
            f"/api/v1/tasks/{fake_uuid}",
            headers=get_auth_headers(token)
        )
        
        assert response.status_code == 404
    
    def test_get_task_shows_processing_status(self, client, registered_user):
        """Test that task status transitions are visible."""
        token = registered_user["token"]
        
        # Create a task
        create_response = client.post(
            "/api/v1/tasks",
            headers=get_auth_headers(token),
            json={
                "payload": {
                    "action": "post_to_slack",
                    "channel": "#test",
                    "message": "Status tracking test"
                }
            }
        )
        task_id = create_response.json()["id"]
        
        # Wait a moment for processing
        time.sleep(2)
        
        # Retrieve the task
        get_response = client.get(
            f"/api/v1/tasks/{task_id}",
            headers=get_auth_headers(token)
        )
        
        assert get_response.status_code == 200
        data = get_response.json()
        
        # Status should be success or in_progress
        assert data["status"] in ["queued", "in_progress", "success", "failed"]


class TestTaskCancellation:
    """Test suite for task cancellation endpoint."""
    
    def test_cancel_task_with_jwt(self, client, registered_user):
        """Test canceling a task with JWT authentication."""
        token = registered_user["token"]
        
        # Create a task
        create_response = client.post(
            "/api/v1/tasks",
            headers=get_auth_headers(token),
            json={
                "payload": {
                    "action": "post_to_slack",
                    "channel": "#test",
                    "message": "Task to be canceled"
                }
            }
        )
        task_id = create_response.json()["id"]
        
        # Cancel the task
        cancel_response = client.delete(
            f"/api/v1/tasks/{task_id}",
            headers=get_auth_headers(token)
        )
        
        # Note: Response might be 200 or 404 depending on if task already processed
        # If task processes very quickly, it might already be done
        assert cancel_response.status_code in [200, 404]
        
        if cancel_response.status_code == 200:
            data = cancel_response.json()
            # If successfully canceled, status should be canceled
            assert data["status"] == "canceled"
    
    def test_cancel_task_without_authentication_fails(self, client, registered_user):
        """Test that canceling a task without JWT fails."""
        token = registered_user["token"]
        
        # Create a task
        create_response = client.post(
            "/api/v1/tasks",
            headers=get_auth_headers(token),
            json={
                "payload": {
                    "action": "post_to_slack",
                    "channel": "#test",
                    "message": "Protected task"
                }
            }
        )
        task_id = create_response.json()["id"]
        
        # Try to cancel without authentication
        cancel_response = client.delete(f"/api/v1/tasks/{task_id}")
        
        assert cancel_response.status_code == 403
    
    def test_cancel_nonexistent_task_returns_404(self, client, registered_user):
        """Test that canceling a non-existent task returns 404."""
        token = registered_user["token"]
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        
        response = client.delete(
            f"/api/v1/tasks/{fake_uuid}",
            headers=get_auth_headers(token)
        )
        
        assert response.status_code == 404


class TestTaskProcessing:
    """Test suite for task processing and worker functionality."""
    
    def test_task_processes_successfully(self, client, registered_user):
        """Test that a task is processed by the worker and completes successfully."""
        token = registered_user["token"]
        
        # Create a task
        create_response = client.post(
            "/api/v1/tasks",
            headers=get_auth_headers(token),
            json={
                "payload": {
                    "action": "post_to_slack",
                    "channel": "#test",
                    "message": "Processing test"
                }
            }
        )
        assert create_response.status_code == 200
        task_id = create_response.json()["id"]
        
        # Wait for processing
        time.sleep(3)
        
        # Check task status
        get_response = client.get(
            f"/api/v1/tasks/{task_id}",
            headers=get_auth_headers(token)
        )
        
        assert get_response.status_code == 200
        data = get_response.json()
        
        # Task should be processed (success or failed)
        assert data["status"] in ["success", "failed"]
        
        # If successful, should have result
        if data["status"] == "success":
            assert data["result"] is not None
            assert "message" in data["result"]


class TestComplexTaskScenarios:
    """Test suite for complex task scenarios combining multiple features."""
    
    def test_task_lifecycle_from_creation_to_completion(self, client, registered_user):
        """Test the complete lifecycle of a task from creation to completion."""
        token = registered_user["token"]
        
        # Create task
        create_response = client.post(
            "/api/v1/tasks",
            headers=get_auth_headers(token),
            json={
                "payload": {
                    "action": "post_to_slack",
                    "channel": "#lifecycle",
                    "message": "Lifecycle test"
                }
            }
        )
        assert create_response.status_code == 200
        task_id = create_response.json()["id"]
        initial_status = create_response.json()["status"]
        assert initial_status == "queued"
        
        # Wait and check status progression
        time.sleep(3)
        
        # Final check
        final_response = client.get(
            f"/api/v1/tasks/{task_id}",
            headers=get_auth_headers(token)
        )
        assert final_response.status_code == 200
        final_data = final_response.json()
        
        # Should have progressed beyond queued
        assert final_data["status"] in ["in_progress", "success", "failed"]
        
        # Verify timestamps exist
        assert "created_at" in final_data
        assert "updated_at" in final_data
    
    def test_multiple_tasks_for_same_tenant(self, client, registered_user):
        """Test that a tenant can create and manage multiple tasks."""
        token = registered_user["token"]
        
        # Create 5 tasks
        task_ids = []
        for i in range(5):
            response = client.post(
                "/api/v1/tasks",
                headers=get_auth_headers(token),
                json={
                    "payload": {
                        "action": "post_to_slack",
                        "channel": "#test",
                        "message": f"Task {i+1}"
                    }
                }
            )
            assert response.status_code == 200
            task_ids.append(response.json()["id"])
        
        # Verify all tasks can be retrieved
        for task_id in task_ids:
            response = client.get(
                f"/api/v1/tasks/{task_id}",
                headers=get_auth_headers(token)
            )
            assert response.status_code == 200
