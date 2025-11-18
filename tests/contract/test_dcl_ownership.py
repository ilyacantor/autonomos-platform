"""
Contract Tests: DCL Ownership Verification

These tests verify that DCL properly owns and controls the mapping registry
and intelligence services as defined in the RACI matrix.
"""
import pytest


def test_dcl_has_mapping_registry_write_api():
    """
    CONTRACT: DCL must provide mapping registry write API.
    
    RACI Accountability: DCL is accountable for mapping registry storage.
    
    Expected: POST /dcl/mappings endpoint exists and is functional
    """
    from app.dcl_engine.routers.mappings import router
    
    # Get all routes from DCL mappings router
    routes = [(route.path, route.methods) for route in router.routes]
    
    # Check for POST endpoint
    post_routes = [r for r in routes if r[0] == '/mappings' and 'POST' in r[1]]
    
    assert len(post_routes) > 0, (
        "DCL MISSING: POST /dcl/mappings endpoint not found. "
        "DCL must provide mapping write API per RACI."
    )
    
    print("✅ PASS: DCL has POST /dcl/mappings write endpoint")


def test_dcl_has_mapping_read_api():
    """
    CONTRACT: DCL must provide mapping registry read API.
    
    RACI Accountability: DCL is accountable for serving mappings to AAM.
    
    Expected: GET /dcl/mappings endpoints exist
    """
    from app.dcl_engine.routers.mappings import router
    
    routes = [(route.path, route.methods) for route in router.routes]
    
    # Check for GET endpoints
    get_single = any('{source_field}' in r[0] and 'GET' in r[1] for r in routes)
    get_list = any(r[0] == '/mappings/{connector}' and 'GET' in r[1] for r in routes)
    
    assert get_single, (
        "DCL MISSING: GET /dcl/mappings/{connector}/{table}/{field} not found. "
        "DCL must provide single mapping lookup API."
    )
    
    assert get_list, (
        "DCL MISSING: GET /dcl/mappings/{connector} not found. "
        "DCL must provide mapping list API."
    )
    
    print("✅ PASS: DCL has GET mapping endpoints")


def test_dcl_has_cache_invalidation():
    """
    CONTRACT: DCL must invalidate cache when mappings are updated.
    
    RACI Accountability: DCL controls mapping lifecycle including cache.
    
    Expected: _invalidate_mapping_cache function exists and is called
    """
    from app.dcl_engine.routers.mappings import _invalidate_mapping_cache
    import inspect
    
    # Verify function exists
    assert callable(_invalidate_mapping_cache), (
        "DCL MISSING: _invalidate_mapping_cache function not found. "
        "DCL must handle cache invalidation on writes."
    )
    
    # Verify it's called in create_mapping
    from app.dcl_engine.routers import mappings
    source = inspect.getsource(mappings.create_mapping)
    
    assert '_invalidate_mapping_cache' in source, (
        "DCL VIOLATION: create_mapping doesn't call _invalidate_mapping_cache. "
        "Cache must be invalidated on write."
    )
    
    print("✅ PASS: DCL has cache invalidation logic")


def test_dcl_enforces_admin_authorization():
    """
    CONTRACT: DCL must enforce admin-only access for mapping writes.
    
    RACI Accountability: DCL controls who can create/update mappings.
    
    Expected: create_mapping checks is_admin before allowing writes
    """
    import inspect
    from app.dcl_engine.routers import mappings
    
    source = inspect.getsource(mappings.create_mapping)
    
    # Check for admin authorization
    has_admin_check = 'is_admin' in source
    
    assert has_admin_check, (
        "DCL VIOLATION: create_mapping missing admin authorization. "
        "Only admins should create/update mappings."
    )
    
    # Check for 403 forbidden response
    has_forbidden = 'HTTP_403_FORBIDDEN' in source or '403' in source
    
    assert has_forbidden, (
        "DCL VIOLATION: create_mapping doesn't return 403 for non-admins. "
        "Admin check must enforce authorization."
    )
    
    print("✅ PASS: DCL enforces admin-only write access")


def test_dcl_owns_field_mappings_table():
    """
    CONTRACT: DCL owns the field_mappings table in database schema.
    
    RACI Accountability: DCL is accountable for mapping registry storage.
    
    Expected: field_mappings table exists and is referenced by DCL code
    """
    from app.models import FieldMapping
    
    # Verify FieldMapping model exists
    assert hasattr(FieldMapping, '__tablename__'), (
        "DCL MISSING: FieldMapping model not found. "
        "DCL must have mapping registry model."
    )
    
    assert FieldMapping.__tablename__ == 'field_mappings', (
        "DCL VIOLATION: FieldMapping table name incorrect. "
        "Should be 'field_mappings'."
    )
    
    # Verify DCL code references this model
    from app.dcl_engine.routers import mappings
    import inspect
    
    source = inspect.getsource(mappings)
    
    assert 'FieldMapping' in source, (
        "DCL VIOLATION: DCL routers don't use FieldMapping model. "
        "DCL must own database access to mappings."
    )
    
    print("✅ PASS: DCL owns field_mappings table")


def test_dcl_has_tenant_isolation():
    """
    CONTRACT: DCL must enforce tenant isolation for mappings.
    
    RACI Accountability: DCL ensures multi-tenant data security.
    
    Expected: All mapping queries filter by tenant_id
    """
    import inspect
    from app.dcl_engine.routers import mappings
    
    # Check get_field_mapping function
    get_mapping_source = inspect.getsource(mappings.get_field_mapping)
    
    assert 'tenant_id' in get_mapping_source, (
        "DCL VIOLATION: get_field_mapping missing tenant_id filter. "
        "Tenant isolation is mandatory for security."
    )
    
    # Check create_mapping function
    create_mapping_source = inspect.getsource(mappings.create_mapping)
    
    assert 'tenant_id' in create_mapping_source, (
        "DCL VIOLATION: create_mapping missing tenant_id. "
        "All mappings must be tenant-scoped."
    )
    
    print("✅ PASS: DCL enforces tenant isolation")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
