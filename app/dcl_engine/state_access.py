"""
Centralized State Access Wrapper Module

This module provides guarded access to DCL state variables, automatically
handling the dual-path between TenantStateManager (tenant-scoped Redis)
and global fallback variables (legacy mode).

All DCL code should use these helpers instead of direct tenant_state_manager
or global variable access to ensure correct behavior in both modes.

Usage:
    from app.dcl_engine.state_access import (
        get_graph_state, set_graph_state,
        get_sources, set_sources,
    )
    
    graph = get_graph_state(tenant_id)
    set_graph_state(tenant_id, updated_graph)
"""

from typing import Dict, List, Any, Optional
from app.dcl_engine.tenant_state import TenantStateManager

_tenant_state_manager: Optional[TenantStateManager] = None


def initialize_state_access(manager: Optional[TenantStateManager]) -> None:
    """
    Initialize the state access module with TenantStateManager instance.
    
    Called during DCL Engine startup in app.py set_redis_client().
    
    Args:
        manager: TenantStateManager instance or None if Redis unavailable
    """
    global _tenant_state_manager
    _tenant_state_manager = manager


def get_graph_state(tenant_id: str) -> Dict[str, Any]:
    """
    Get graph state for tenant.
    
    Returns tenant-scoped graph from Redis when TenantStateManager available,
    falls back to global GRAPH_STATE otherwise.
    
    Args:
        tenant_id: Tenant identifier
        
    Returns:
        Dict with keys: nodes, edges, confidence, etc.
    """
    if _tenant_state_manager:
        return _tenant_state_manager.get_graph_state(tenant_id)
    else:
        from app.dcl_engine.app import GRAPH_STATE
        return GRAPH_STATE


def set_graph_state(tenant_id: str, state: Dict[str, Any]) -> None:
    """
    Set graph state for tenant.
    
    Writes to tenant-scoped Redis when TenantStateManager available,
    falls back to global GRAPH_STATE otherwise.
    
    Args:
        tenant_id: Tenant identifier
        state: Graph state dict (nodes, edges, etc.)
    """
    if _tenant_state_manager:
        _tenant_state_manager.set_graph_state(tenant_id, state)
    else:
        import app.dcl_engine.app as app_module
        app_module.GRAPH_STATE = state


def get_sources(tenant_id: str) -> List[str]:
    """Get connected sources list for tenant."""
    if _tenant_state_manager:
        return _tenant_state_manager.get_sources(tenant_id)
    else:
        from app.dcl_engine.app import SOURCES_ADDED
        return SOURCES_ADDED


def set_sources(tenant_id: str, sources: List[str]) -> None:
    """Set connected sources list for tenant."""
    if _tenant_state_manager:
        _tenant_state_manager.set_sources(tenant_id, sources)
    else:
        import app.dcl_engine.app as app_module
        app_module.SOURCES_ADDED = sources


def get_entity_sources(tenant_id: str) -> Dict[str, List[str]]:
    """Get entity-to-sources mapping for tenant."""
    if _tenant_state_manager:
        return _tenant_state_manager.get_entity_sources(tenant_id)
    else:
        from app.dcl_engine.app import ENTITY_SOURCES
        return ENTITY_SOURCES


def set_entity_sources(tenant_id: str, entity_sources: Dict[str, List[str]]) -> None:
    """Set entity-to-sources mapping for tenant."""
    if _tenant_state_manager:
        _tenant_state_manager.set_entity_sources(tenant_id, entity_sources)
    else:
        import app.dcl_engine.app as app_module
        app_module.ENTITY_SOURCES = entity_sources


def get_source_schemas(tenant_id: str) -> Dict[str, Dict[str, Any]]:
    """Get source schemas mapping for tenant."""
    if _tenant_state_manager:
        return _tenant_state_manager.get_source_schemas(tenant_id)
    else:
        from app.dcl_engine.app import SOURCE_SCHEMAS
        return SOURCE_SCHEMAS


def set_source_schemas(tenant_id: str, schemas: Dict[str, Dict[str, Any]]) -> None:
    """Set source schemas mapping for tenant."""
    if _tenant_state_manager:
        _tenant_state_manager.set_source_schemas(tenant_id, schemas)
    else:
        import app.dcl_engine.app as app_module
        app_module.SOURCE_SCHEMAS = schemas


def get_selected_agents(tenant_id: str) -> List[str]:
    """Get selected agents list for tenant."""
    if _tenant_state_manager:
        return _tenant_state_manager.get_selected_agents(tenant_id)
    else:
        from app.dcl_engine.app import SELECTED_AGENTS
        return SELECTED_AGENTS


def set_selected_agents(tenant_id: str, agents: List[str]) -> None:
    """Set selected agents list for tenant."""
    if _tenant_state_manager:
        _tenant_state_manager.set_selected_agents(tenant_id, agents)
    else:
        import app.dcl_engine.app as app_module
        app_module.SELECTED_AGENTS = agents


def get_event_log(tenant_id: str) -> List[str]:
    """Get event log for tenant."""
    if _tenant_state_manager:
        return _tenant_state_manager.get_event_log(tenant_id)
    else:
        from app.dcl_engine.app import EVENT_LOG
        return EVENT_LOG


def set_event_log(tenant_id: str, events: List[str]) -> None:
    """Set event log for tenant."""
    if _tenant_state_manager:
        _tenant_state_manager.set_event_log(tenant_id, events)
    else:
        import app.dcl_engine.app as app_module
        app_module.EVENT_LOG = events


def append_event(tenant_id: str, message: str) -> None:
    """Append event to log for tenant."""
    if _tenant_state_manager:
        _tenant_state_manager.append_event(tenant_id, message)
    else:
        import app.dcl_engine.app as app_module
        if not app_module.EVENT_LOG or app_module.EVENT_LOG[-1] != message:
            app_module.EVENT_LOG.append(message)
        if len(app_module.EVENT_LOG) > 200:
            app_module.EVENT_LOG.pop(0)


def reset_all_state(tenant_id: str) -> None:
    """
    Reset all state variables for tenant.
    
    Clears graph, sources, entities, schemas, agents, and events.
    Used by /dcl/reset endpoint and mode toggle operations.
    
    Args:
        tenant_id: Tenant identifier
    """
    set_graph_state(tenant_id, {"nodes": [], "edges": []})
    set_sources(tenant_id, [])
    set_entity_sources(tenant_id, {})
    set_source_schemas(tenant_id, {})
    set_selected_agents(tenant_id, [])
    set_event_log(tenant_id, [])
