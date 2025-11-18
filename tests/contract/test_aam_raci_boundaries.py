"""
Contract Tests: AAM RACI Boundary Enforcement

These tests verify that AAM respects RACI boundaries and does not
violate its responsibility scope by accessing mapping registry directly.
"""
import pytest
import inspect


def test_aam_cannot_create_mappings():
    """
    CONTRACT: AAM should NOT have write methods to mapping registry.
    
    RACI Violation: If AAM can create/update/delete mappings directly,
    it violates the boundary where DCL is accountable for mapping decisions.
    
    Expected: AAM has no methods named create_mapping, update_mapping, delete_mapping
    """
    from aam_hybrid.core.canonical_processor import CanonicalProcessor
    from shared.redis_client import get_redis_client
    
    redis_client = get_redis_client()
    processor = CanonicalProcessor(redis_client=redis_client)
    
    # Check that AAM has no direct write methods
    methods = [method for method in dir(processor) if not method.startswith('_')]
    
    # These methods should NOT exist in AAM
    forbidden_methods = ['create_mapping', 'update_mapping', 'delete_mapping', 
                        'save_mapping', 'persist_mapping', 'write_mapping']
    
    violations = [m for m in forbidden_methods if m in methods]
    
    assert len(violations) == 0, (
        f"RACI VIOLATION: AAM has forbidden write methods: {violations}. "
        f"Only DCL should have mapping write access per RACI matrix."
    )
    
    print("✅ PASS: AAM has no direct mapping write methods")


def test_aam_must_use_dcl_client():
    """
    CONTRACT: AAM connectors must use DCLMappingClient, not direct DB access.
    
    RACI Violation: If AAM has direct database session access for mappings,
    it can bypass DCL and violate the architectural boundary.
    
    Expected: AAM uses DCL client, has no direct DB session for mappings
    """
    from services.aam.canonical.mapping_registry import mapping_registry
    
    # Verify mapping_registry uses DCL client
    assert hasattr(mapping_registry, 'dcl_client'), (
        "RACI VIOLATION: mapping_registry missing dcl_client. "
        "AAM must use DCL API for mapping lookups."
    )
    
    # Verify no direct DB session access
    assert not hasattr(mapping_registry, 'db_session'), (
        "RACI VIOLATION: mapping_registry has direct db_session. "
        "AAM must not have direct database access for mappings."
    )
    
    assert not hasattr(mapping_registry, 'session'), (
        "RACI VIOLATION: mapping_registry has direct session. "
        "AAM must not have direct database access for mappings."
    )
    
    print("✅ PASS: AAM uses DCL client, no direct DB access")


def test_aam_has_no_sqlalchemy_mapping_imports():
    """
    CONTRACT: AAM should not import SQLAlchemy models for field_mappings.
    
    RACI Violation: If AAM imports FieldMapping model directly, it can
    query/modify the database bypassing DCL.
    
    Expected: AAM does not import FieldMapping, ConnectorDefinition models
    """
    # Check that AAM files don't import mapping models
    import aam_hybrid.core.canonical_processor as processor_module
    
    source_code = inspect.getsource(processor_module)
    
    # These imports should NOT be present
    forbidden_imports = [
        'from app.models import FieldMapping',
        'from app.models import ConnectorDefinition',
        'import app.models',
    ]
    
    violations = [imp for imp in forbidden_imports if imp in source_code]
    
    assert len(violations) == 0, (
        f"RACI VIOLATION: AAM imports mapping models directly: {violations}. "
        f"AAM must use DCL API, not direct model access."
    )
    
    print("✅ PASS: AAM has no direct SQLAlchemy mapping model imports")


def test_dcl_owns_mapping_registry_storage():
    """
    CONTRACT: Only DCL should have write endpoints for field_mappings table.
    
    RACI Compliance: DCL is accountable for mapping registry storage.
    AAM should only have read access via DCL API.
    
    Expected: DCL has POST /dcl/mappings, AAM has no equivalent
    """
    # Verify DCL has the write endpoint
    from app.dcl_engine.routers import mappings as dcl_mappings
    
    dcl_routes = [route.path for route in dcl_mappings.router.routes]
    
    # DCL should have POST /mappings endpoint
    has_create_endpoint = any('/mappings' in route for route in dcl_routes)
    assert has_create_endpoint, (
        "DCL MISSING: POST /dcl/mappings endpoint not found. "
        "DCL must provide mapping creation API."
    )
    
    # Verify AAM has no equivalent write endpoints
    # (AAM should not have routers for mapping writes)
    import os
    aam_routers_path = 'aam_hybrid/routers'
    
    if os.path.exists(aam_routers_path):
        # If AAM has routers directory, check for mapping write endpoints
        aam_files = [f for f in os.listdir(aam_routers_path) if f.endswith('.py')]
        assert 'mappings.py' not in aam_files, (
            "RACI VIOLATION: AAM has mappings router. "
            "Only DCL should have mapping write endpoints."
        )
    
    print("✅ PASS: DCL owns mapping registry write access")


def test_aam_mapping_registry_is_readonly():
    """
    CONTRACT: AAM's mapping_registry should be read-only (GET operations only).
    
    RACI Compliance: AAM is Responsible for executing transformations,
    but NOT accountable for mapping decisions/storage.
    
    Expected: mapping_registry has get methods, no set/create methods
    
    KNOWN VIOLATION (to be fixed in Phase 1.7):
    - save_mapping() method writes to YAML files (legacy, will be removed)
    """
    from services.aam.canonical.mapping_registry import MappingRegistry
    
    # Get all public methods
    methods = [m for m in dir(MappingRegistry) if not m.startswith('_')]
    
    # Check for read-only pattern (get methods OK, set methods NOT OK)
    write_patterns = ['set_', 'create_', 'update_', 'delete_', 'persist_', 'write_']
    
    violations = []
    for method in methods:
        if any(pattern in method.lower() for pattern in write_patterns):
            violations.append(method)
    
    # Known violation: save_mapping writes to YAML (will be removed in Phase 1.7)
    known_violations = ['save_mapping']
    unexpected_violations = [v for v in violations if v not in known_violations]
    
    assert len(unexpected_violations) == 0, (
        f"RACI VIOLATION: mapping_registry has unexpected write methods: {unexpected_violations}. "
        f"AAM should only READ mappings from DCL, not write them. "
        f"Known violations (to be fixed in Phase 1.7): {known_violations}"
    )
    
    # Log known violations for tracking
    if len(violations) > 0:
        print(f"⚠️  KNOWN VIOLATIONS (Phase 1.7): {violations}")
    
    print("✅ PASS: AAM mapping_registry has no unexpected write methods")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
