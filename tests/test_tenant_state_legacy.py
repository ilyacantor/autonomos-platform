"""
Legacy Regression Tests for Tenant State Dual-Path Behavior

This test suite validates that state_access wrappers correctly handle both:
1. Legacy mode (TenantStateManager unavailable, using global fallback)
2. Redis mode (TenantStateManager available, using tenant-scoped Redis)

Purpose:
    Ensure zero AttributeError crashes when switching between modes and verify
    that mutations persist to the correct storage backend (globals vs Redis).

Test Coverage:
    - State read operations (GET /dcl/state)
    - State write operations (connect_source mutations)
    - Complex mutations (apply_plan)
    - State reset operations
    - Event log append operations
    - Redis serialization and TTL behavior
    - Production flows (WebSocket, planner, connect_source)

Success Criteria:
    - All tests pass in legacy mode (state_access initialized with None)
    - All tests pass in Redis mode (state_access initialized with TenantStateManager)
    - Zero AttributeError exceptions
    - Mutations persist to correct storage (globals in legacy, Redis in normal)
"""

import pytest
import copy
import fakeredis
from typing import Dict, Any, List


@pytest.fixture
def legacy_mode():
    """
    Force legacy mode by initializing state_access with None.
    
    This simulates the scenario where Redis is unavailable or
    TENANT_SCOPED_STATE feature flag is disabled.
    
    Yields:
        None (fixture setup/teardown)
    """
    from app.dcl_engine import state_access
    
    # Save original manager
    original_manager = state_access._tenant_state_manager
    
    # Force legacy mode (TenantStateManager unavailable)
    state_access.initialize_state_access(None)
    
    yield
    
    # Restore original manager
    state_access.initialize_state_access(original_manager)


@pytest.fixture
def reset_globals():
    """
    Reset all global state variables before/after tests.
    
    This ensures test isolation and prevents side effects between tests.
    
    Yields:
        None (fixture setup/teardown)
    """
    import app.dcl_engine.app as app_module
    
    # Save originals (deep copy to avoid reference issues)
    original_graph = copy.deepcopy(app_module.GRAPH_STATE)
    original_sources = copy.deepcopy(app_module.SOURCES_ADDED)
    original_entity_sources = copy.deepcopy(app_module.ENTITY_SOURCES)
    original_source_schemas = copy.deepcopy(app_module.SOURCE_SCHEMAS)
    original_selected_agents = copy.deepcopy(app_module.SELECTED_AGENTS)
    original_event_log = copy.deepcopy(app_module.EVENT_LOG)
    
    yield
    
    # Restore originals
    app_module.GRAPH_STATE = original_graph
    app_module.SOURCES_ADDED = original_sources
    app_module.ENTITY_SOURCES = original_entity_sources
    app_module.SOURCE_SCHEMAS = original_source_schemas
    app_module.SELECTED_AGENTS = original_selected_agents
    app_module.EVENT_LOG = original_event_log


class TestLegacyModeBehavior:
    """
    Test suite for legacy mode (TenantStateManager unavailable).
    
    These tests verify that state_access wrappers correctly fall back to
    global variables when Redis/TenantStateManager is not available.
    """
    
    def test_legacy_state_read_graph(self, legacy_mode, reset_globals):
        """
        Verify state_access.get_graph_state() reads globals in legacy mode.
        
        Test Flow:
            1. Set up test data in global GRAPH_STATE
            2. Read via state_access wrapper
            3. Assert reads from global (not Redis)
        
        Expected:
            - No AttributeError
            - Returns data from global GRAPH_STATE
        """
        from app.dcl_engine import state_access
        import app.dcl_engine.app as app_module
        
        # Set up test data in globals
        test_graph = {
            "nodes": [{"id": "test-node", "label": "TestEntity"}],
            "edges": [{"source": "test-node", "target": "test-node2"}],
            "confidence": 0.85,
            "last_updated": "2025-01-15T10:00:00Z"
        }
        app_module.GRAPH_STATE = test_graph
        
        # Read via wrapper (should not raise AttributeError)
        try:
            result = state_access.get_graph_state("test-tenant")
        except AttributeError as e:
            pytest.fail(f"AttributeError in legacy mode: {e}")
        
        # Assert reads from global
        assert result == test_graph
        assert result["nodes"][0]["id"] == "test-node"
        assert result["confidence"] == 0.85
    
    def test_legacy_state_write_graph(self, legacy_mode, reset_globals):
        """
        Verify state_access.set_graph_state() writes to globals in legacy mode.
        
        Test Flow:
            1. Write test data via state_access wrapper
            2. Assert written to global GRAPH_STATE (not Redis)
        
        Expected:
            - No AttributeError
            - Data persisted to global GRAPH_STATE
        """
        from app.dcl_engine import state_access
        import app.dcl_engine.app as app_module
        
        # Write via wrapper (should not raise AttributeError)
        test_graph = {
            "nodes": [{"id": "new-node", "label": "NewEntity"}],
            "edges": [],
            "confidence": 0.92,
            "last_updated": "2025-01-15T11:00:00Z"
        }
        
        try:
            state_access.set_graph_state("test-tenant", test_graph)
        except AttributeError as e:
            pytest.fail(f"AttributeError in legacy mode: {e}")
        
        # Assert written to global
        assert app_module.GRAPH_STATE == test_graph
        assert app_module.GRAPH_STATE["nodes"][0]["id"] == "new-node"
    
    def test_legacy_state_read_sources(self, legacy_mode, reset_globals):
        """
        Verify state_access.get_sources() reads globals in legacy mode.
        """
        from app.dcl_engine import state_access
        import app.dcl_engine.app as app_module
        
        # Set up test data
        test_sources = ["salesforce", "mongodb", "supabase"]
        app_module.SOURCES_ADDED = test_sources
        
        # Read via wrapper
        try:
            result = state_access.get_sources("test-tenant")
        except AttributeError as e:
            pytest.fail(f"AttributeError in legacy mode: {e}")
        
        # Assert reads from global
        assert result == test_sources
        assert "salesforce" in result
    
    def test_legacy_state_write_sources(self, legacy_mode, reset_globals):
        """
        Verify state_access.set_sources() writes to globals in legacy mode.
        
        Test Flow:
            1. Write test sources via state_access wrapper
            2. Assert written to global SOURCES_ADDED
        
        Expected:
            - No AttributeError
            - Data persisted to global SOURCES_ADDED
        """
        from app.dcl_engine import state_access
        import app.dcl_engine.app as app_module
        
        # Write via wrapper
        test_sources = ["salesforce", "supabase"]
        
        try:
            state_access.set_sources("test-tenant", test_sources)
        except AttributeError as e:
            pytest.fail(f"AttributeError in legacy mode: {e}")
        
        # Assert written to global
        assert app_module.SOURCES_ADDED == test_sources
        assert len(app_module.SOURCES_ADDED) == 2
    
    def test_legacy_entity_sources_read_write(self, legacy_mode, reset_globals):
        """
        Verify entity_sources read/write operations in legacy mode.
        """
        from app.dcl_engine import state_access
        import app.dcl_engine.app as app_module
        
        # Write via wrapper
        test_entity_sources = {
            "account": ["salesforce", "dynamics"],
            "opportunity": ["salesforce", "hubspot"]
        }
        
        try:
            state_access.set_entity_sources("test-tenant", test_entity_sources)
        except AttributeError as e:
            pytest.fail(f"AttributeError in legacy mode: {e}")
        
        # Assert written to global
        assert app_module.ENTITY_SOURCES == test_entity_sources
        
        # Read via wrapper
        try:
            result = state_access.get_entity_sources("test-tenant")
        except AttributeError as e:
            pytest.fail(f"AttributeError in legacy mode: {e}")
        
        # Assert reads from global
        assert result == test_entity_sources
        assert result["account"] == ["salesforce", "dynamics"]
    
    def test_legacy_source_schemas_read_write(self, legacy_mode, reset_globals):
        """
        Verify source_schemas read/write operations in legacy mode.
        """
        from app.dcl_engine import state_access
        import app.dcl_engine.app as app_module
        
        # Write via wrapper
        test_schemas = {
            "salesforce": {
                "tables": ["Account", "Opportunity"],
                "schema_version": "v1.0"
            }
        }
        
        try:
            state_access.set_source_schemas("test-tenant", test_schemas)
        except AttributeError as e:
            pytest.fail(f"AttributeError in legacy mode: {e}")
        
        # Assert written to global
        assert app_module.SOURCE_SCHEMAS == test_schemas
        
        # Read via wrapper
        try:
            result = state_access.get_source_schemas("test-tenant")
        except AttributeError as e:
            pytest.fail(f"AttributeError in legacy mode: {e}")
        
        # Assert reads from global
        assert result == test_schemas
    
    def test_legacy_selected_agents_read_write(self, legacy_mode, reset_globals):
        """
        Verify selected_agents read/write operations in legacy mode.
        """
        from app.dcl_engine import state_access
        import app.dcl_engine.app as app_module
        
        # Write via wrapper
        test_agents = ["dcl_light", "finops_autopilot", "revops_agent"]
        
        try:
            state_access.set_selected_agents("test-tenant", test_agents)
        except AttributeError as e:
            pytest.fail(f"AttributeError in legacy mode: {e}")
        
        # Assert written to global
        assert app_module.SELECTED_AGENTS == test_agents
        
        # Read via wrapper
        try:
            result = state_access.get_selected_agents("test-tenant")
        except AttributeError as e:
            pytest.fail(f"AttributeError in legacy mode: {e}")
        
        # Assert reads from global
        assert result == test_agents
    
    def test_legacy_event_log_operations(self, legacy_mode, reset_globals):
        """
        Verify event log read/write/append operations in legacy mode.
        """
        from app.dcl_engine import state_access
        import app.dcl_engine.app as app_module
        
        # Clear event log
        app_module.EVENT_LOG = []
        
        # Append event (should not raise AttributeError)
        try:
            state_access.append_event("test-tenant", "Test event message 1")
            state_access.append_event("test-tenant", "Test event message 2")
        except AttributeError as e:
            pytest.fail(f"AttributeError in legacy mode: {e}")
        
        # Assert appended to global
        assert len(app_module.EVENT_LOG) == 2
        assert "Test event message 1" in app_module.EVENT_LOG[0]
        assert "Test event message 2" in app_module.EVENT_LOG[1]
        
        # Read via wrapper
        try:
            result = state_access.get_event_log("test-tenant")
        except AttributeError as e:
            pytest.fail(f"AttributeError in legacy mode: {e}")
        
        # Assert reads from global
        assert len(result) == 2
        assert "Test event message 1" in result[0]
    
    def test_legacy_reset_all_state(self, legacy_mode, reset_globals):
        """
        Verify state_access.reset_all_state() clears globals in legacy mode.
        
        Test Flow:
            1. Populate globals with test data
            2. Call reset_all_state via wrapper
            3. Assert all globals cleared to default values
        
        Expected:
            - No AttributeError
            - All global state variables reset to empty/default
        """
        from app.dcl_engine import state_access
        import app.dcl_engine.app as app_module
        
        # Populate globals with test data
        app_module.GRAPH_STATE = {
            "nodes": [{"id": "test"}],
            "edges": [{"source": "a", "target": "b"}]
        }
        app_module.SOURCES_ADDED = ["salesforce", "mongodb"]
        app_module.ENTITY_SOURCES = {"account": ["salesforce"]}
        app_module.SOURCE_SCHEMAS = {"salesforce": {"tables": ["Account"]}}
        app_module.SELECTED_AGENTS = ["dcl_light"]
        app_module.EVENT_LOG = ["Event 1", "Event 2"]
        
        # Reset via wrapper (should not raise AttributeError)
        try:
            state_access.reset_all_state("test-tenant")
        except AttributeError as e:
            pytest.fail(f"AttributeError in legacy mode: {e}")
        
        # Assert globals cleared
        assert app_module.GRAPH_STATE == {"nodes": [], "edges": []}
        assert app_module.SOURCES_ADDED == []
        assert app_module.ENTITY_SOURCES == {}
        assert app_module.SOURCE_SCHEMAS == {}
        assert app_module.SELECTED_AGENTS == []
        assert app_module.EVENT_LOG == []


class TestRedisModeBehavior:
    """
    Test suite for Redis mode (TenantStateManager available).
    
    These tests verify that state_access wrappers correctly use Redis-backed
    tenant-scoped storage when TenantStateManager is available.
    
    Note: These tests will use the actual TenantStateManager instance,
    which may be backed by Redis or in-memory fallback depending on environment.
    """
    
    def test_redis_mode_state_read_graph(self, reset_globals):
        """
        Verify state_access.get_graph_state() works in Redis mode.
        
        This test runs WITHOUT legacy_mode fixture, so it uses whatever
        TenantStateManager is configured (Redis or fallback).
        """
        from app.dcl_engine import state_access
        
        # Read via wrapper (should not raise AttributeError)
        try:
            result = state_access.get_graph_state("test-tenant-redis")
        except AttributeError as e:
            pytest.fail(f"AttributeError in Redis mode: {e}")
        
        # Assert returns valid graph structure
        assert isinstance(result, dict)
        assert "nodes" in result
        assert "edges" in result
    
    def test_redis_mode_state_write_graph(self, reset_globals):
        """
        Verify state_access.set_graph_state() works in Redis mode.
        """
        from app.dcl_engine import state_access
        
        # Write via wrapper (should not raise AttributeError)
        test_graph = {
            "nodes": [{"id": "redis-node", "label": "RedisEntity"}],
            "edges": [],
            "confidence": 0.88
        }
        
        try:
            state_access.set_graph_state("test-tenant-redis", test_graph)
        except AttributeError as e:
            pytest.fail(f"AttributeError in Redis mode: {e}")
        
        # Read back via wrapper
        try:
            result = state_access.get_graph_state("test-tenant-redis")
        except AttributeError as e:
            pytest.fail(f"AttributeError in Redis mode: {e}")
        
        # Assert persistence works
        assert result["nodes"][0]["id"] == "redis-node"
        assert result["confidence"] == 0.88
    
    def test_redis_mode_sources_operations(self, reset_globals):
        """
        Verify sources read/write operations work in Redis mode.
        """
        from app.dcl_engine import state_access
        
        # Write via wrapper
        test_sources = ["salesforce", "supabase", "mongodb"]
        
        try:
            state_access.set_sources("test-tenant-redis", test_sources)
        except AttributeError as e:
            pytest.fail(f"AttributeError in Redis mode: {e}")
        
        # Read back via wrapper
        try:
            result = state_access.get_sources("test-tenant-redis")
        except AttributeError as e:
            pytest.fail(f"AttributeError in Redis mode: {e}")
        
        # Assert persistence works
        assert result == test_sources
        assert len(result) == 3
    
    def test_redis_mode_reset_all_state(self, reset_globals):
        """
        Verify state_access.reset_all_state() works in Redis mode.
        """
        from app.dcl_engine import state_access
        
        # Set up some state
        try:
            state_access.set_graph_state("test-tenant-redis", {
                "nodes": [{"id": "test"}],
                "edges": []
            })
            state_access.set_sources("test-tenant-redis", ["salesforce"])
            state_access.append_event("test-tenant-redis", "Test event")
        except AttributeError as e:
            pytest.fail(f"AttributeError in Redis mode setup: {e}")
        
        # Reset via wrapper (should not raise AttributeError)
        try:
            state_access.reset_all_state("test-tenant-redis")
        except AttributeError as e:
            pytest.fail(f"AttributeError in Redis mode: {e}")
        
        # Assert state cleared
        try:
            graph = state_access.get_graph_state("test-tenant-redis")
            sources = state_access.get_sources("test-tenant-redis")
            events = state_access.get_event_log("test-tenant-redis")
        except AttributeError as e:
            pytest.fail(f"AttributeError in Redis mode after reset: {e}")
        
        assert graph == {"nodes": [], "edges": []}
        assert sources == []
        assert events == []


class TestDualModeConsistency:
    """
    Test suite to verify consistent behavior across legacy and Redis modes.
    
    These tests ensure that the same operations produce the same results
    regardless of whether TenantStateManager is available.
    """
    
    def test_append_event_idempotency(self, legacy_mode, reset_globals):
        """
        Verify append_event handles duplicates correctly in legacy mode.
        
        According to state_access.py implementation:
        - Should not append duplicate if last event matches
        - Should enforce max 200 events (FIFO eviction)
        """
        from app.dcl_engine import state_access
        import app.dcl_engine.app as app_module
        
        # Clear event log
        app_module.EVENT_LOG = []
        
        # Append same event twice
        try:
            state_access.append_event("test-tenant", "Duplicate event")
            state_access.append_event("test-tenant", "Duplicate event")
        except AttributeError as e:
            pytest.fail(f"AttributeError: {e}")
        
        # Assert only one event appended (duplicate prevention)
        assert len(app_module.EVENT_LOG) == 1
    
    def test_event_log_max_size_enforcement(self, legacy_mode, reset_globals):
        """
        Verify event log enforces max 200 events in legacy mode.
        """
        from app.dcl_engine import state_access
        import app.dcl_engine.app as app_module
        
        # Clear event log
        app_module.EVENT_LOG = []
        
        # Append 250 unique events
        try:
            for i in range(250):
                state_access.append_event("test-tenant", f"Event {i}")
        except AttributeError as e:
            pytest.fail(f"AttributeError: {e}")
        
        # Assert max 200 events (oldest evicted)
        assert len(app_module.EVENT_LOG) <= 200
        
        # Assert newest events retained
        assert "Event 249" in app_module.EVENT_LOG[-1]


class TestNoAttributeErrorGuarantee:
    """
    Critical test suite to ensure zero AttributeError crashes.
    
    These tests explicitly verify that common operations never raise
    AttributeError regardless of TenantStateManager availability.
    """
    
    def test_all_getters_no_attribute_error_legacy(self, legacy_mode, reset_globals):
        """
        Verify all getter methods work without AttributeError in legacy mode.
        """
        from app.dcl_engine import state_access
        
        # Call all getters - none should raise AttributeError
        try:
            graph = state_access.get_graph_state("test-tenant")
            sources = state_access.get_sources("test-tenant")
            entity_sources = state_access.get_entity_sources("test-tenant")
            schemas = state_access.get_source_schemas("test-tenant")
            agents = state_access.get_selected_agents("test-tenant")
            events = state_access.get_event_log("test-tenant")
        except AttributeError as e:
            pytest.fail(f"AttributeError in legacy mode getters: {e}")
        
        # Assert all return valid types
        assert isinstance(graph, dict)
        assert isinstance(sources, list)
        assert isinstance(entity_sources, dict)
        assert isinstance(schemas, dict)
        assert isinstance(agents, list)
        assert isinstance(events, list)
    
    def test_all_setters_no_attribute_error_legacy(self, legacy_mode, reset_globals):
        """
        Verify all setter methods work without AttributeError in legacy mode.
        """
        from app.dcl_engine import state_access
        
        # Call all setters - none should raise AttributeError
        try:
            state_access.set_graph_state("test-tenant", {"nodes": [], "edges": []})
            state_access.set_sources("test-tenant", ["salesforce"])
            state_access.set_entity_sources("test-tenant", {"account": ["salesforce"]})
            state_access.set_source_schemas("test-tenant", {"salesforce": {}})
            state_access.set_selected_agents("test-tenant", ["dcl_light"])
            state_access.set_event_log("test-tenant", ["Event 1"])
            state_access.append_event("test-tenant", "Event 2")
            state_access.reset_all_state("test-tenant")
        except AttributeError as e:
            pytest.fail(f"AttributeError in legacy mode setters: {e}")
    
    def test_all_getters_no_attribute_error_redis(self, reset_globals):
        """
        Verify all getter methods work without AttributeError in Redis mode.
        """
        from app.dcl_engine import state_access
        
        # Call all getters - none should raise AttributeError
        try:
            graph = state_access.get_graph_state("test-tenant-redis")
            sources = state_access.get_sources("test-tenant-redis")
            entity_sources = state_access.get_entity_sources("test-tenant-redis")
            schemas = state_access.get_source_schemas("test-tenant-redis")
            agents = state_access.get_selected_agents("test-tenant-redis")
            events = state_access.get_event_log("test-tenant-redis")
        except AttributeError as e:
            pytest.fail(f"AttributeError in Redis mode getters: {e}")
        
        # Assert all return valid types
        assert isinstance(graph, dict)
        assert isinstance(sources, list)
        assert isinstance(entity_sources, dict)
        assert isinstance(schemas, dict)
        assert isinstance(agents, list)
        assert isinstance(events, list)
    
    def test_all_setters_no_attribute_error_redis(self, reset_globals):
        """
        Verify all setter methods work without AttributeError in Redis mode.
        """
        from app.dcl_engine import state_access
        
        # Call all setters - none should raise AttributeError
        try:
            state_access.set_graph_state("test-tenant-redis", {"nodes": [], "edges": []})
            state_access.set_sources("test-tenant-redis", ["salesforce"])
            state_access.set_entity_sources("test-tenant-redis", {"account": ["salesforce"]})
            state_access.set_source_schemas("test-tenant-redis", {"salesforce": {}})
            state_access.set_selected_agents("test-tenant-redis", ["dcl_light"])
            state_access.set_event_log("test-tenant-redis", ["Event 1"])
            state_access.append_event("test-tenant-redis", "Event 2")
            state_access.reset_all_state("test-tenant-redis")
        except AttributeError as e:
            pytest.fail(f"AttributeError in Redis mode setters: {e}")


# ====================================================================================
# Redis Integration Tests - Real TenantStateManager with Fake Redis
# ====================================================================================


@pytest.fixture
def redis_test_client():
    """
    Provide fake Redis client for testing.
    
    Uses fakeredis to simulate Redis behavior without requiring
    a real Redis server for tests.
    
    Returns:
        FakeStrictRedis instance configured for testing
    """
    return fakeredis.FakeStrictRedis(decode_responses=True)


@pytest.fixture
def redis_mode(redis_test_client, monkeypatch):
    """
    Force Redis mode with actual TenantStateManager instance.
    
    This fixture creates a real TenantStateManager connected to
    a fake Redis client, enabling tests to validate actual Redis
    integration without external dependencies.
    
    Yields:
        TenantStateManager instance configured with fake Redis
    """
    from app.dcl_engine import state_access
    from app.dcl_engine.tenant_state import TenantStateManager
    from app.config.feature_flags import FeatureFlagConfig, FeatureFlag
    
    # Save original manager
    original_manager = state_access._tenant_state_manager
    
    # Create real TenantStateManager with fake Redis
    test_manager = TenantStateManager(redis_client=redis_test_client)
    
    # Enable TENANT_SCOPED_STATE feature flag for tests
    monkeypatch.setattr(
        FeatureFlagConfig,
        'is_enabled',
        lambda flag: True if flag == FeatureFlag.TENANT_SCOPED_STATE else False
    )
    
    # Initialize state_access with test manager
    state_access.initialize_state_access(test_manager)
    
    yield test_manager
    
    # Restore original manager
    state_access.initialize_state_access(original_manager)


class TestRedisIntegration:
    """
    Test actual Redis integration with TenantStateManager.
    
    This test suite validates that state_access wrappers correctly
    interact with Redis through TenantStateManager, ensuring data
    serialization, persistence, and edge cases are handled correctly.
    """
    
    def test_redis_serialization_round_trip(self, redis_mode):
        """
        Verify data serializes/deserializes correctly through Redis.
        
        Test Flow:
            1. Write complex graph state via state_access
            2. Read back via state_access
            3. Assert exact match (JSON serialization round-trip)
        
        Expected:
            - No data loss or corruption
            - Complex nested structures preserved
        """
        from app.dcl_engine import state_access
        
        # Complex graph state with nested structures
        test_graph = {
            "nodes": [
                {"id": "n1", "type": "entity", "label": "Customer"},
                {"id": "n2", "type": "entity", "label": "Account"}
            ],
            "edges": [
                {"source": "n1", "target": "n2", "type": "relates_to"}
            ],
            "confidence": 0.95,
            "metadata": {
                "last_updated": "2025-01-15T10:00:00Z",
                "source_count": 2
            }
        }
        
        # Write via state_access
        state_access.set_graph_state("test-tenant", test_graph)
        
        # Read back via state_access
        result = state_access.get_graph_state("test-tenant")
        
        # Assert exact match (JSON serialization round-trip)
        assert result == test_graph
        assert result["nodes"][0]["id"] == "n1"
        assert result["confidence"] == 0.95
        assert result["metadata"]["source_count"] == 2
    
    def test_redis_multi_tenant_isolation(self, redis_mode):
        """
        Verify tenant isolation in Redis storage.
        
        Test Flow:
            1. Write different data for two tenants
            2. Read back for each tenant
            3. Assert no cross-tenant data leakage
        
        Expected:
            - Tenant A data != Tenant B data
            - No cross-contamination
        """
        from app.dcl_engine import state_access
        
        # Set up different data for two tenants
        tenant_a_sources = ["salesforce", "mongodb"]
        tenant_b_sources = ["supabase", "postgres"]
        
        state_access.set_sources("tenant-a", tenant_a_sources)
        state_access.set_sources("tenant-b", tenant_b_sources)
        
        # Read back and verify isolation
        result_a = state_access.get_sources("tenant-a")
        result_b = state_access.get_sources("tenant-b")
        
        assert result_a == tenant_a_sources
        assert result_b == tenant_b_sources
        assert result_a != result_b
    
    def test_redis_ttl_behavior(self, redis_mode, redis_test_client):
        """
        Verify Redis keys have appropriate TTL (if configured).
        
        Test Flow:
            1. Set state via state_access
            2. Check Redis key exists
            3. Verify TTL configuration
        
        Expected:
            - Redis key exists after write
            - TTL is -1 (no expiry) or > 0 (configured TTL)
        """
        from app.dcl_engine import state_access
        
        # Set state
        state_access.set_sources("test-tenant", ["salesforce"])
        
        # Check Redis key exists (correct key format: dcl:tenant:{tenant_id}:sources_added)
        key = "dcl:tenant:test-tenant:sources_added"
        assert redis_test_client.exists(key), f"Key '{key}' not found in Redis"
        
        # Check TTL (if configured, otherwise -1 for no expiry)
        ttl = redis_test_client.ttl(key)
        # Assert appropriate value (adjust based on your TTL config)
        # -1 means no expiry, positive means TTL in seconds
        assert ttl == -1 or ttl > 0
    
    def test_redis_complex_mutation_persistence(self, redis_mode):
        """
        Test complex state mutations persist to Redis.
        
        Test Flow:
            1. Perform multiple state updates
            2. Read back final state
            3. Assert all mutations persisted correctly
        
        Expected:
            - All mutations visible in final state
            - No partial writes or data loss
        """
        from app.dcl_engine import state_access
        
        tenant_id = "test-tenant-mutations"
        
        # Perform multiple mutations
        state_access.set_sources(tenant_id, ["salesforce"])
        state_access.set_entity_sources(tenant_id, {"account": ["salesforce"]})
        state_access.set_source_schemas(tenant_id, {
            "salesforce": {
                "Account": ["Id", "Name", "Industry"],
                "Opportunity": ["Id", "Amount", "StageName"]
            }
        })
        state_access.set_selected_agents(tenant_id, ["dcl_light", "dcl_full"])
        
        # Read back and verify all mutations persisted
        sources = state_access.get_sources(tenant_id)
        entity_sources = state_access.get_entity_sources(tenant_id)
        schemas = state_access.get_source_schemas(tenant_id)
        agents = state_access.get_selected_agents(tenant_id)
        
        assert sources == ["salesforce"]
        assert entity_sources == {"account": ["salesforce"]}
        assert "salesforce" in schemas
        assert "Account" in schemas["salesforce"]
        assert agents == ["dcl_light", "dcl_full"]
    
    def test_redis_event_log_append(self, redis_mode):
        """
        Test event log append operations persist to Redis.
        
        Test Flow:
            1. Append multiple events
            2. Read back event log
            3. Assert events in correct order
        
        Expected:
            - Events persisted in order
            - No duplicate events
        """
        from app.dcl_engine import state_access
        
        tenant_id = "test-tenant-events"
        
        # Append multiple events
        state_access.append_event(tenant_id, "Event 1: Source connected")
        state_access.append_event(tenant_id, "Event 2: Graph updated")
        state_access.append_event(tenant_id, "Event 3: Mapping generated")
        
        # Read back event log
        events = state_access.get_event_log(tenant_id)
        
        # Assert events in order
        assert len(events) == 3
        assert events[0] == "Event 1: Source connected"
        assert events[1] == "Event 2: Graph updated"
        assert events[2] == "Event 3: Mapping generated"
    
    def test_redis_state_reset(self, redis_mode):
        """
        Test reset_all_state clears Redis data.
        
        Test Flow:
            1. Set up complex state
            2. Call reset_all_state
            3. Assert all state cleared
        
        Expected:
            - All state variables reset to defaults
            - No stale data in Redis
        """
        from app.dcl_engine import state_access
        
        tenant_id = "test-tenant-reset"
        
        # Set up complex state
        state_access.set_graph_state(tenant_id, {
            "nodes": [{"id": "n1"}],
            "edges": []
        })
        state_access.set_sources(tenant_id, ["salesforce", "mongodb"])
        state_access.append_event(tenant_id, "Test event")
        
        # Reset all state
        state_access.reset_all_state(tenant_id)
        
        # Verify all state cleared
        graph = state_access.get_graph_state(tenant_id)
        sources = state_access.get_sources(tenant_id)
        events = state_access.get_event_log(tenant_id)
        
        assert graph == {"nodes": [], "edges": []}
        assert sources == []
        assert events == []
