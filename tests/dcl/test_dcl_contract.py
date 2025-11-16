"""
DCL Contract Testing (Snapshot Tests)

CRITICAL: These tests capture the exact response structure of DCL endpoints
and FAIL when the structure changes. This catches regressions like:
- Serialization issues (ORJSONResponse breaking JSON structure)
- Field removals or renames
- Type changes in response payloads
- Unexpected null/missing fields

Snapshot Testing with Syrupy:
- First run: Creates baseline snapshot files in __snapshots__/
- Subsequent runs: Compares current output to snapshot, fails on mismatch
- Update snapshots: pytest --snapshot-update

Coverage:
- /dcl/state endpoint (graph state structure)
- Node and edge structure
- Metadata fields (confidence, sources, etc.)
"""

import pytest
from syrupy.assertion import SnapshotAssertion


class TestDCLStateContract:
    """
    Contract tests for /dcl/state endpoint.
    
    These tests ensure the response structure remains stable across changes.
    ANY modification to the graph state schema will cause these tests to FAIL,
    forcing explicit review and snapshot update.
    """
    
    def test_empty_graph_state_structure(self, dcl_reset_state, snapshot: SnapshotAssertion):
        """
        Test: Empty graph state has correct structure.
        
        Validates that a fresh tenant with no connected sources returns:
        - Empty nodes list
        - Empty edges list
        - Null/default metadata fields
        
        Catches: Missing required fields, incorrect null handling
        """
        client, headers, tenant_id = dcl_reset_state
        
        # Fetch state for empty graph
        response = client.get("/dcl/state", headers=headers)
        
        assert response.status_code == 200, f"State endpoint failed: {response.text}"
        state = response.json()
        
        # Assert structure matches snapshot
        assert state == snapshot
        
        # Critical assertions (structure validation)
        assert "graph" in state, "Missing 'graph' field"
        assert "nodes" in state["graph"], "Missing 'nodes' field in graph"
        assert "edges" in state["graph"], "Missing 'edges' field in graph"
        assert isinstance(state["graph"]["nodes"], list), "nodes must be a list"
        assert isinstance(state["graph"]["edges"], list), "edges must be a list"
        assert len(state["graph"]["nodes"]) == 0, "Empty graph should have 0 nodes"
        assert len(state["graph"]["edges"]) == 0, "Empty graph should have 0 edges"
    
    def test_graph_state_with_sources_structure(self, dcl_graph_with_sources, snapshot: SnapshotAssertion):
        """
        Test: Graph state with connected sources has correct structure.
        
        Validates that after connecting sources (salesforce, hubspot):
        - Nodes contain entity mappings
        - Edges contain relationships
        - Metadata fields are populated
        - Source tracking is correct
        
        Catches: Serialization issues, incorrect graph construction
        """
        client, headers, tenant_id, expected_graph = dcl_graph_with_sources
        
        # Fetch current state
        response = client.get("/dcl/state", headers=headers)
        
        assert response.status_code == 200, f"State endpoint failed: {response.text}"
        state = response.json()
        
        # Assert structure matches snapshot
        assert state == snapshot
        
        # Critical assertions (non-empty graph validation)
        assert "graph" in state, "Missing 'graph' field"
        assert "nodes" in state["graph"], "Missing 'nodes' field in graph"
        assert "edges" in state["graph"], "Missing 'edges' field in graph"
        assert len(state["graph"]["nodes"]) > 0, "Graph should have nodes after connecting sources"
        
        # Validate node structure (first node as example)
        if len(state["graph"]["nodes"]) > 0:
            node = state["graph"]["nodes"][0]
            assert "id" in node, "Node missing 'id' field"
            assert "label" in node, "Node missing 'label' field"
            assert "type" in node, "Node missing 'type' field"
    
    def test_graph_state_metadata_fields(self, dcl_graph_with_sources, snapshot: SnapshotAssertion):
        """
        Test: Graph state metadata fields are present and typed correctly.
        
        Validates metadata that should exist in graph state:
        - confidence scores
        - last_updated timestamps
        - source tracking
        - entity counts
        
        Catches: Missing metadata, incorrect types
        """
        client, headers, tenant_id, expected_graph = dcl_graph_with_sources
        
        response = client.get("/dcl/state", headers=headers)
        
        assert response.status_code == 200
        state = response.json()
        
        # Snapshot full state including metadata
        assert state == snapshot
        
        # Type validation for common metadata fields
        if "confidence" in state and state["confidence"] is not None:
            assert isinstance(state["confidence"], (int, float)), "Confidence must be numeric"
        
        if "last_updated" in state and state["last_updated"] is not None:
            assert isinstance(state["last_updated"], str), "last_updated must be string (ISO timestamp)"


class TestDCLSourceSchemasContract:
    """
    Contract tests for source schema endpoints.
    
    Validates the structure of source schema responses to catch:
    - Schema format changes
    - Missing field definitions
    - Type information loss
    """
    
    def test_source_schemas_empty_structure(self, dcl_reset_state, snapshot: SnapshotAssertion):
        """
        Test: Source schemas endpoint structure with no sources.
        
        Validates empty schema response structure.
        """
        client, headers, tenant_id = dcl_reset_state
        
        response = client.get("/dcl/source_schemas", headers=headers)
        
        assert response.status_code == 200
        schemas = response.json()
        
        # Snapshot the structure
        assert schemas == snapshot
        
        # Should be an empty dict or have expected structure
        assert isinstance(schemas, dict), "Source schemas must be a dict"
    
    def test_source_schemas_with_sources_structure(self, dcl_graph_with_sources, snapshot: SnapshotAssertion):
        """
        Test: Source schemas endpoint structure with connected sources.
        
        Validates schema structure includes:
        - Field definitions
        - Type information
        - Entity mappings
        """
        client, headers, tenant_id, expected_graph = dcl_graph_with_sources
        
        response = client.get("/dcl/source_schemas", headers=headers)
        
        assert response.status_code == 200
        schemas = response.json()
        
        # Snapshot the structure
        assert schemas == snapshot
        
        # Validate structure (should have entries for connected sources)
        assert isinstance(schemas, dict), "Source schemas must be a dict"
        
        # If sources are present, validate schema structure
        for source_id, schema in schemas.items():
            assert isinstance(schema, dict), f"Schema for {source_id} must be a dict"


class TestDCLConnectEndpointContract:
    """
    Contract tests for source connection endpoints.
    
    Validates the response structure when connecting data sources.
    """
    
    def test_connect_source_response_structure(self, dcl_reset_state, snapshot: SnapshotAssertion):
        """
        Test: /dcl/connect endpoint response structure.
        
        Validates the response when connecting a source:
        - Success indicators
        - Graph update information
        - Entity mappings created
        """
        client, headers, tenant_id = dcl_reset_state
        
        # Connect a source
        response = client.get(
            "/dcl/connect",
            params={"source_id": "salesforce"},
            headers=headers
        )
        
        assert response.status_code == 200, f"Connect failed: {response.text}"
        result = response.json()
        
        # Snapshot the response structure
        assert result == snapshot
        
        # Validate presence of key response fields
        assert "message" in result or "status" in result or "graph" in result, \
            "Connect response missing expected fields"
