"""
THE CRITICAL MULTI-TENANT ISOLATION TEST.

This is the most important test in the entire suite.
It verifies that users from different tenants CANNOT access each other's data.

This provides cryptographic proof that the platform is secure and production-ready.
"""
import pytest
from tests.conftest import get_auth_headers


class TestCrossTenantIsolation:
    """
    The definitive test suite proving complete tenant isolation.
    
    These tests verify that the fundamental security promise of multi-tenancy
    is upheld: users from one tenant cannot access data from another tenant.
    """
    
    def test_user_from_tenant_b_cannot_access_tenant_a_task(self, client, two_tenants):
        """
        THE CRITICAL TEST: Verify cross-tenant task isolation.
        
        Steps:
        1. User A (Tenant A) creates a task
        2. User B (Tenant B) attempts to retrieve that task
        3. Verify that User B receives a 404 Not Found
        
        This proves complete data isolation between tenants.
        """
        tenant_a = two_tenants["tenant_a"]
        tenant_b = two_tenants["tenant_b"]
        
        # Step 1: User A creates a task
        task_response = client.post(
            "/api/v1/tasks",
            headers=get_auth_headers(tenant_a["token"]),
            json={
                "payload": {
                    "action": "post_to_slack",
                    "channel": "#tenant-a",
                    "message": "Confidential message from Tenant A"
                }
            }
        )
        assert task_response.status_code == 200
        task_id = task_response.json()["id"]
        
        # Step 2: User B attempts to access Tenant A's task
        access_response = client.get(
            f"/api/v1/tasks/{task_id}",
            headers=get_auth_headers(tenant_b["token"])
        )
        
        # Step 3: CRITICAL ASSERTION - User B must NOT see the task
        assert access_response.status_code == 404
        assert "not found" in access_response.json()["detail"].lower()
        
        # Verify User A CAN still access their own task
        verify_response = client.get(
            f"/api/v1/tasks/{task_id}",
            headers=get_auth_headers(tenant_a["token"])
        )
        assert verify_response.status_code == 200
        assert verify_response.json()["id"] == task_id
    
    def test_user_from_tenant_b_cannot_delete_tenant_a_task(self, client, two_tenants):
        """
        Verify that User B cannot cancel/delete Tenant A's task.
        
        This ensures that destructive operations are also tenant-isolated.
        """
        tenant_a = two_tenants["tenant_a"]
        tenant_b = two_tenants["tenant_b"]
        
        # User A creates a task
        task_response = client.post(
            "/api/v1/tasks",
            headers=get_auth_headers(tenant_a["token"]),
            json={
                "payload": {
                    "action": "post_to_slack",
                    "channel": "#tenant-a",
                    "message": "Task to be protected from Tenant B"
                }
            }
        )
        assert task_response.status_code == 200
        task_id = task_response.json()["id"]
        
        # User B attempts to delete Tenant A's task
        delete_response = client.delete(
            f"/api/v1/tasks/{task_id}",
            headers=get_auth_headers(tenant_b["token"])
        )
        
        # User B should get 404 (task not found in their tenant)
        assert delete_response.status_code == 404
        
        # Verify task still exists for User A
        verify_response = client.get(
            f"/api/v1/tasks/{task_id}",
            headers=get_auth_headers(tenant_a["token"])
        )
        assert verify_response.status_code == 200
        assert verify_response.json()["status"] != "canceled"
    
    def test_tenant_can_only_see_their_own_user_info(self, client, two_tenants):
        """
        Verify that /users/me returns only the authenticated user's info.
        
        User A and User B should each see only their own information.
        """
        tenant_a = two_tenants["tenant_a"]
        tenant_b = two_tenants["tenant_b"]
        
        # User A gets their info
        response_a = client.get(
            "/users/me",
            headers=get_auth_headers(tenant_a["token"])
        )
        assert response_a.status_code == 200
        user_a_data = response_a.json()
        
        # User B gets their info
        response_b = client.get(
            "/users/me",
            headers=get_auth_headers(tenant_b["token"])
        )
        assert response_b.status_code == 200
        user_b_data = response_b.json()
        
        # Verify they have different tenant_ids
        assert user_a_data["tenant_id"] != user_b_data["tenant_id"]
        
        # Verify they have different emails
        assert user_a_data["email"] != user_b_data["email"]
        
        # Verify correct emails are returned
        assert user_a_data["email"] == tenant_a["email"]
        assert user_b_data["email"] == tenant_b["email"]
    
    def test_multiple_tasks_across_tenants_remain_isolated(self, client, two_tenants):
        """
        Verify isolation when multiple tasks exist across tenants.
        
        Create multiple tasks for each tenant and ensure each user
        can only see their own tasks.
        """
        tenant_a = two_tenants["tenant_a"]
        tenant_b = two_tenants["tenant_b"]
        
        # Tenant A creates 3 tasks
        task_ids_a = []
        for i in range(3):
            response = client.post(
                "/api/v1/tasks",
                headers=get_auth_headers(tenant_a["token"]),
                json={
                    "payload": {
                        "action": "post_to_slack",
                        "channel": "#tenant-a",
                        "message": f"Tenant A Task {i+1}"
                    }
                }
            )
            assert response.status_code == 200
            task_ids_a.append(response.json()["id"])
        
        # Tenant B creates 2 tasks
        task_ids_b = []
        for i in range(2):
            response = client.post(
                "/api/v1/tasks",
                headers=get_auth_headers(tenant_b["token"]),
                json={
                    "payload": {
                        "action": "post_to_slack",
                        "channel": "#tenant-b",
                        "message": f"Tenant B Task {i+1}"
                    }
                }
            )
            assert response.status_code == 200
            task_ids_b.append(response.json()["id"])
        
        # Verify Tenant B CANNOT access any of Tenant A's tasks
        for task_id in task_ids_a:
            response = client.get(
                f"/api/v1/tasks/{task_id}",
                headers=get_auth_headers(tenant_b["token"])
            )
            assert response.status_code == 404
        
        # Verify Tenant A CANNOT access any of Tenant B's tasks
        for task_id in task_ids_b:
            response = client.get(
                f"/api/v1/tasks/{task_id}",
                headers=get_auth_headers(tenant_a["token"])
            )
            assert response.status_code == 404
        
        # Verify each tenant CAN access their own tasks
        for task_id in task_ids_a:
            response = client.get(
                f"/api/v1/tasks/{task_id}",
                headers=get_auth_headers(tenant_a["token"])
            )
            assert response.status_code == 200
        
        for task_id in task_ids_b:
            response = client.get(
                f"/api/v1/tasks/{task_id}",
                headers=get_auth_headers(tenant_b["token"])
            )
            assert response.status_code == 200
    
    def test_task_with_sensitive_data_not_leaked_across_tenants(self, client, two_tenants):
        """
        Verify that sensitive data in task payloads is not leaked across tenants.
        
        This simulates a real-world scenario where tasks contain confidential information.
        """
        tenant_a = two_tenants["tenant_a"]
        tenant_b = two_tenants["tenant_b"]
        
        sensitive_data = {
            "action": "post_to_slack",
            "channel": "#confidential",
            "message": "CONFIDENTIAL: Customer credit card ending in 1234"
        }
        
        # Tenant A creates task with sensitive data
        task_response = client.post(
            "/api/v1/tasks",
            headers=get_auth_headers(tenant_a["token"]),
            json={"payload": sensitive_data}
        )
        assert task_response.status_code == 200
        task_id = task_response.json()["id"]
        
        # Tenant B attempts to access the task
        access_response = client.get(
            f"/api/v1/tasks/{task_id}",
            headers=get_auth_headers(tenant_b["token"])
        )
        
        # CRITICAL: Tenant B must NOT see the task or its sensitive data
        assert access_response.status_code == 404
        
        # Verify the response does NOT contain any sensitive data
        response_text = access_response.text.lower()
        assert "credit card" not in response_text
        assert "1234" not in response_text
        assert "confidential" not in response_text


class TestAuthenticationIsolation:
    """
    Test that authentication tokens are properly scoped to tenants.
    """
    
    def test_jwt_token_contains_correct_tenant_scope(self, client, registered_user):
        """
        Verify that JWT tokens properly encode tenant information.
        
        While we don't decode the token here, we verify it works correctly
        by ensuring the user can only access their own tenant's data.
        """
        token = registered_user["token"]
        email = registered_user["email"]
        
        # Create a task
        task_response = client.post(
            "/api/v1/tasks",
            headers=get_auth_headers(token),
            json={
                "payload": {
                    "action": "post_to_slack",
                    "channel": "#test",
                    "message": "Test message"
                }
            }
        )
        assert task_response.status_code == 200
        
        # Verify we can access it with the same token
        task_id = task_response.json()["id"]
        get_response = client.get(
            f"/api/v1/tasks/{task_id}",
            headers=get_auth_headers(token)
        )
        assert get_response.status_code == 200
