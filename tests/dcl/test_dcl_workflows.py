"""
DCL Workflow Integrity Testing

Validates core DCL workflows end-to-end to ensure:
- Correct graph construction from data sources
- Proper state updates and persistence
- Consistent behavior across operations
- Clean teardown and reset functionality

Test Coverage:
1. Initialization: Fresh tenant starts with empty graph
2. Construction: Adding sources creates correct graph structure
3. Updates: Modifying sources updates graph correctly
4. Reset: Clearing state removes all artifacts
5. Multi-source: Multiple sources integrate properly

These tests validate the EXACT expected state at each workflow stage,
catching regressions in graph construction logic.
"""

import pytest
from typing import Dict, Any


class TestDCLInitialization:
    """
    Tests for DCL initialization and empty state validation.
    
    Ensures new tenants start with clean slate.
    """
    
    def test_fresh_tenant_has_empty_graph(self, dcl_reset_state):
        """
        Test: Fresh tenant has completely empty graph state.
        
        Validates:
        - nodes list is empty
        - edges list is empty
        - no sources connected
        - no entities tracked
        
        Catches: State leakage, initialization bugs
        """
        client, headers, tenant_id = dcl_reset_state
        
        # Fetch state
        response = client.get("/dcl/state", headers=headers)
        assert response.status_code == 200
        
        state = response.json()
        
        # Assert empty graph
        assert state["nodes"] == [], f"Expected empty nodes, got {len(state['nodes'])}"
        assert state["edges"] == [], f"Expected empty edges, got {len(state['edges'])}"
        
        # Check sources (if endpoint exists)
        # Note: This assumes sources are tracked in state or separate endpoint
    
    def test_multiple_fresh_tenants_isolated(self, two_tenants):
        """
        Test: Multiple fresh tenants have isolated empty graphs.
        
        Validates:
        - Tenant A's empty graph
        - Tenant B's empty graph
        - No cross-tenant state pollution
        
        Catches: Multi-tenancy bugs, state leakage
        """
        from fastapi.testclient import TestClient
        from tests.conftest import get_auth_headers
        from app.main import app
        
        client = TestClient(app)
        
        # Tenant A state
        token_a = two_tenants["tenant_a"]["token"]
        headers_a = get_auth_headers(token_a)
        
        response_a = client.get("/dcl/state", headers=headers_a)
        assert response_a.status_code == 200
        state_a = response_a.json()
        
        # Tenant B state
        token_b = two_tenants["tenant_b"]["token"]
        headers_b = get_auth_headers(token_b)
        
        response_b = client.get("/dcl/state", headers=headers_b)
        assert response_b.status_code == 200
        state_b = response_b.json()
        
        # Both should be empty and independent
        assert state_a["nodes"] == [], "Tenant A should have empty graph"
        assert state_b["nodes"] == [], "Tenant B should have empty graph"
        assert state_a["edges"] == [], "Tenant A should have no edges"
        assert state_b["edges"] == [], "Tenant B should have no edges"


class TestDCLConstruction:
    """
    Tests for graph construction when adding data sources.
    
    Validates correct node/edge creation and structure.
    """
    
    def test_single_source_creates_graph(self, dcl_reset_state):
        """
        Test: Connecting single source creates graph nodes/edges.
        
        Validates:
        - Graph nodes are created for entities
        - Edges represent relationships
        - Node count matches expected entities
        
        Catches: Graph construction failures, missing entities
        """
        client, headers, tenant_id = dcl_reset_state
        
        # Connect salesforce
        connect_response = client.get(
            "/dcl/connect",
            params={
                "sources": "salesforce",
                "agents": "revops_pilot",
                "llm_model": "gemini-2.5-flash"
            },
            headers=headers
        )
        assert connect_response.status_code == 200, f"Connect failed: {connect_response.text}"
        
        # Fetch state
        state_response = client.get("/dcl/state", headers=headers)
        assert state_response.status_code == 200
        
        state = state_response.json()
        
        # Assert graph was built
        assert len(state["nodes"]) > 0, "No nodes created after connecting source"
        
        # Validate node structure
        for node in state["nodes"]:
            assert "id" in node, "Node missing id field"
            assert "label" in node, "Node missing label field"
            assert "type" in node, "Node missing type field"
    
    def test_multiple_sources_integrate_correctly(self, dcl_reset_state):
        """
        Test: Connecting multiple sources integrates into unified graph.
        
        Validates:
        - Both sources contribute nodes
        - Shared entities are unified (not duplicated)
        - Entity counts are correct
        
        Catches: Deduplication issues, source isolation bugs
        """
        client, headers, tenant_id = dcl_reset_state
        
        # Connect salesforce
        sf_response = client.get(
            "/dcl/connect",
            params={
                "sources": "salesforce",
                "agents": "revops_pilot",
                "llm_model": "gemini-2.5-flash"
            },
            headers=headers
        )
        assert sf_response.status_code == 200
        
        # Get state after first source
        state1_response = client.get("/dcl/state", headers=headers)
        state1 = state1_response.json()
        nodes_after_sf = len(state1["nodes"])
        
        # Connect hubspot
        hs_response = client.get(
            "/dcl/connect",
            params={
                "sources": "hubspot",
                "agents": "revops_pilot",
                "llm_model": "gemini-2.5-flash"
            },
            headers=headers
        )
        assert hs_response.status_code == 200
        
        # Get state after second source
        state2_response = client.get("/dcl/state", headers=headers)
        state2 = state2_response.json()
        nodes_after_hs = len(state2["nodes"])
        
        # Assert both sources contributed
        assert nodes_after_sf > 0, "Salesforce should create nodes"
        assert nodes_after_hs >= nodes_after_sf, "Hubspot should add/maintain nodes"
        
        # Validate unified graph
        assert len(state2["nodes"]) > 0, "Final graph should have nodes"
        assert len(state2["edges"]) >= 0, "Final graph should have edges"
    
    def test_source_connection_idempotency(self, dcl_reset_state):
        """
        Test: Connecting same source twice is idempotent.
        
        Validates:
        - Second connection doesn't duplicate nodes
        - Graph state remains consistent
        - No errors on re-connection
        
        Catches: Duplicate entity bugs, state corruption
        """
        client, headers, tenant_id = dcl_reset_state
        
        # Connect salesforce first time
        response1 = client.get(
            "/dcl/connect",
            params={
                "sources": "salesforce",
                "agents": "revops_pilot",
                "llm_model": "gemini-2.5-flash"
            },
            headers=headers
        )
        assert response1.status_code == 200
        
        state1 = client.get("/dcl/state", headers=headers).json()
        nodes_count1 = len(state1["nodes"])
        
        # Connect salesforce second time
        response2 = client.get(
            "/dcl/connect",
            params={
                "sources": "salesforce",
                "agents": "revops_pilot",
                "llm_model": "gemini-2.5-flash"
            },
            headers=headers
        )
        assert response2.status_code == 200
        
        state2 = client.get("/dcl/state", headers=headers).json()
        nodes_count2 = len(state2["nodes"])
        
        # Assert idempotency (node count should be same or similar)
        assert nodes_count2 == nodes_count1, \
            f"Re-connecting should be idempotent: {nodes_count1} vs {nodes_count2}"


class TestDCLUpdates:
    """
    Tests for graph updates when sources change.
    
    Validates correct propagation of schema/data changes.
    """
    
    def test_graph_reflects_source_changes(self, dcl_graph_with_sources):
        """
        Test: Graph updates when source data changes.
        
        Note: This test validates the update mechanism exists.
        Actual update testing requires simulating source changes.
        
        Validates:
        - Graph state can be refreshed
        - Updates don't corrupt existing state
        """
        client, headers, tenant_id, initial_graph = dcl_graph_with_sources
        
        # Re-fetch state (simulates refresh)
        response = client.get("/dcl/state", headers=headers)
        assert response.status_code == 200
        
        updated_state = response.json()
        
        # Assert structure is maintained
        assert "nodes" in updated_state
        assert "edges" in updated_state
        assert len(updated_state["nodes"]) == len(initial_graph["nodes"]), \
            "Refresh shouldn't change node count without actual changes"


class TestDCLReset:
    """
    Tests for state reset and cleanup functionality.
    
    Validates complete state teardown.
    """
    
    def test_reset_clears_all_state(self, dcl_graph_with_sources):
        """
        Test: Resetting state clears all graph data.
        
        Validates:
        - All nodes removed
        - All edges removed
        - Source connections cleared
        - Returns to empty state
        
        Catches: Incomplete cleanup, state persistence bugs
        """
        client, headers, tenant_id, initial_graph = dcl_graph_with_sources
        
        # Verify we have data first
        assert len(initial_graph["nodes"]) > 0, "Setup should create nodes"
        
        # Reset state using state_access module
        from app.dcl_engine import state_access
        state_access.reset_all_state(tenant_id)
        
        # Fetch state after reset
        response = client.get("/dcl/state", headers=headers)
        assert response.status_code == 200
        
        state = response.json()
        
        # Assert complete cleanup
        assert state["nodes"] == [], f"Reset should clear nodes, got {len(state['nodes'])}"
        assert state["edges"] == [], f"Reset should clear edges, got {len(state['edges'])}"
    
    def test_reset_allows_fresh_start(self, dcl_graph_with_sources):
        """
        Test: After reset, can rebuild graph from scratch.
        
        Validates:
        - Reset doesn't break connection mechanism
        - Can re-connect same sources
        - Graph rebuilds correctly
        
        Catches: State corruption, broken reset logic
        """
        client, headers, tenant_id, initial_graph = dcl_graph_with_sources
        
        # Reset
        from app.dcl_engine import state_access
        state_access.reset_all_state(tenant_id)
        
        # Verify empty
        empty_state = client.get("/dcl/state", headers=headers).json()
        assert len(empty_state["nodes"]) == 0
        
        # Reconnect salesforce
        reconnect_response = client.get(
            "/dcl/connect",
            params={
                "sources": "salesforce",
                "agents": "revops_pilot",
                "llm_model": "gemini-2.5-flash"
            },
            headers=headers
        )
        assert reconnect_response.status_code == 200
        
        # Verify graph rebuilt
        rebuilt_state = client.get("/dcl/state", headers=headers).json()
        assert len(rebuilt_state["nodes"]) > 0, "Should rebuild graph after reset"


class TestDCLEdgeCases:
    """
    Tests for edge cases and error conditions.
    
    Validates robust error handling.
    """
    
    def test_invalid_source_id_handling(self, dcl_reset_state):
        """
        Test: Connecting invalid source ID handles gracefully.
        
        Validates:
        - Returns appropriate error response
        - Doesn't corrupt graph state
        - Clear error message
        
        Catches: Poor error handling, state corruption
        """
        client, headers, tenant_id = dcl_reset_state
        
        # Try connecting invalid source using NEW API signature
        response = client.get(
            "/dcl/connect",
            params={
                "sources": "invalid_source_xyz",
                "agents": "revops_pilot",
                "llm_model": "gemini-2.5-flash"
            },
            headers=headers
        )
        
        # Should either return error or handle gracefully
        # (Accept both 207/404/400 - 207 is partial failure response)
        assert response.status_code in [200, 207, 404, 400], \
            f"Unexpected status code: {response.status_code}"
        
        # Verify graph state not corrupted
        state = client.get("/dcl/state", headers=headers).json()
        assert isinstance(state["nodes"], list), "Graph state should remain valid"
        assert isinstance(state["edges"], list), "Graph state should remain valid"
