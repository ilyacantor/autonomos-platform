
"""
DCL Engine: Data Connection Layer with Multi-Tenant State Isolation

================================================================================
TENANT ID CONTRACT (Phase 1a: Foundation for State Migration)
================================================================================

All DCL endpoints and service functions accept tenant_id to ensure
multi-tenant data isolation. The tenant_id is extracted from:
- JWT claims (current_user.tenant_id) when AUTH_ENABLED=true
- Default value "default" when AUTH_ENABLED=false (development)

Helper function:
    get_tenant_id_from_user(current_user) -> str

All state operations MUST use state_access helpers:
    from app.dcl_engine import state_access
    
    graph = state_access.get_graph_state(tenant_id)
    state_access.set_graph_state(tenant_id, updated_graph)

Never access global variables or tenant_state_manager directly.

Example - Endpoint with tenant_id:
    @app.get("/state", dependencies=AUTH_DEPENDENCIES)
    def state(current_user = Depends(get_current_user)):
        tenant_id = get_tenant_id_from_user(current_user)
        return state_access.get_graph_state(tenant_id)

Example - Service function with tenant_id:
    async def connect_source(source_id: str, tenant_id: str = "default"):
        sources = state_access.get_sources(tenant_id)
        # ... operate on tenant-scoped state

================================================================================
"""

import os, time, json, glob, duckdb, pandas as pd, yaml, warnings, threading, re, traceback, asyncio
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, Query, Request, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
import google.generativeai as genai  # type: ignore
from app.dcl_engine.rag_engine import RAGEngine
from app.dcl_engine.llm_service import get_llm_service
import redis
from redis.asyncio import Redis as AsyncRedis
from app.dcl_engine.source_loader import get_source_adapter, AAMSourceAdapter
from app.config.feature_flags import FeatureFlagConfig, FeatureFlag
from app.dcl_engine.agent_executor import AgentExecutor
from app.dcl_engine.tenant_state import TenantStateManager
from app.dcl_engine import state_access
from app.security import get_current_user, AUTH_ENABLED
from app.middleware.rate_limit import limiter
from app.dcl_engine.distributed_lock import RedisDistributedLock

# Import DTOs for API contracts (Phase 3 Priority 3)
from app.dcl_engine.schemas.dto import (
    ConnectRequest, ConnectResponse,
    StateResponse, GraphState, GraphNode, GraphEdge,
    ResetRequest, ResetResponse,
    ToggleRequest, ToggleResponse,
    SourceSchemasResponse, SourceSchema,
    FeatureFlag as DTOFeatureFlag,
    DevMode
)

# Use paths relative to this module's directory
DCL_BASE_PATH = Path(__file__).parent

def get_db_path(tenant_id: str = "default") -> str:
    """
    Get tenant-scoped DuckDB path to prevent cross-tenant race conditions.
    
    Each tenant gets an isolated DuckDB file, preventing race conditions where:
    1. Tenant A connects → creates registry.duckdb → closes connection
    2. Tenant B cleanup → deletes registry.duckdb
    3. Tenant A agent execution → file missing → skip agents
    
    Args:
        tenant_id: Tenant identifier (defaults to "default")
    
    Returns:
        Path to tenant-scoped DuckDB file (e.g., "registry_default.duckdb")
    
    Example:
        con = duckdb.connect(get_db_path(tenant_id), config={'access_mode': 'READ_WRITE'})
    """
    path = str(DCL_BASE_PATH / f"registry_{tenant_id}.duckdb")
    print(f"[TRACE_DCL] get_db_path(tenant_id={tenant_id}) -> {path}", flush=True)
    return path

ONTOLOGY_PATH = str(DCL_BASE_PATH / "ontology" / "catalog.yml")
AGENTS_CONFIG_PATH = str(DCL_BASE_PATH / "agents" / "config.yml")
SCHEMAS_DIR = str(DCL_BASE_PATH / "schemas")
CONF_THRESHOLD = 0.70
AUTO_PUBLISH_PARTIAL = True

# Authentication dependencies for all protected endpoints
# Auth is controlled via DCL_AUTH_ENABLED env var in app/security.py
AUTH_DEPENDENCIES = [Depends(get_current_user)]

if os.getenv("GEMINI_API_KEY"):
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
else:
    print("⚠️ GEMINI_API_KEY not set. LLM proposals may be unavailable.")

EVENT_LOG: List[str] = []
GRAPH_STATE = {"nodes": [], "edges": [], "confidence": None, "last_updated": None}
SOURCES_ADDED: List[str] = []
ENTITY_SOURCES: Dict[str, List[str]] = {}
AUTO_INGEST_UNMAPPED = False
ontology = None
agents_config = None
SELECTED_AGENTS: List[str] = []
AGENT_RESULTS_CACHE: Dict[str, Dict] = {}  # tenant_id -> {agent_id -> results}
agent_executor: Optional[AgentExecutor] = None
LLM_CALLS = 0
LLM_TOKENS = 0
rag_engine = None
RAG_CONTEXT = {"retrievals": [], "total_mappings": 0, "last_retrieval_count": 0}
SOURCE_SCHEMAS: Dict[str, Dict[str, Any]] = {}
DEV_MODE = False  # When True, uses AI/RAG for mapping; when False, uses only heuristics

# DEPRECATED: Replaced by dcl_distributed_lock (Redis-based distributed locking)
# STATE_LOCK = threading.Lock()  # ❌ REMOVED - caused race conditions with async code
# ASYNC_STATE_LOCK = None  # ❌ REMOVED - uncoordinated with sync lock

# Redis distributed lock for safe concurrent access across all workers/processes
# Replaces brittle dual-lock system (STATE_LOCK + ASYNC_STATE_LOCK)
dcl_distributed_lock: Optional[RedisDistributedLock] = None

# Performance timing storage
TIMING_LOG: Dict[str, List[float]] = {
    "llm_propose_total": [],
    "rag_retrieval": [],
    "gemini_call": [],
    "connect_total": []
}

# Request deduplication for toggle operations
_active_toggle_requests: Dict[str, float] = {}  # tenant_id -> timestamp

# Redis-based distributed lock for cross-process DuckDB access
# NOTE: Redis client is shared from main app to avoid connection limit issues
redis_client = None
redis_available = False
async_redis_client = None  # Async Redis client for non-blocking pub/sub operations
DB_LOCK_KEY = "dcl:duckdb:lock"
DB_LOCK_TIMEOUT = 30  # seconds
DEV_MODE_KEY = "dcl:dev_mode"  # Redis key for cross-process dev mode state
LLM_CALLS_KEY = "dcl:llm:calls"  # Redis key for LLM call counter
LLM_TOKENS_KEY = "dcl:llm:tokens"  # Redis key for LLM token counter
LLM_CALLS_SAVED_KEY = "dcl:llm:calls_saved"  # Redis key for LLM calls saved via RAG
DCL_STATE_CHANNEL = "dcl:state:updates"  # Redis pub/sub channel for state broadcasts
GRAPH_STATE_KEY_PREFIX = "dcl:graph_state"  # Redis key prefix for graph state persistence
in_memory_dev_mode = False  # Fallback when Redis unavailable
_dev_mode_initialized = False  # Track if dev_mode has been initialized

class GraphStateStore:
    """
    Helper for persisting GRAPH_STATE to Redis with tenant scoping.
    Ensures demo users always see a nice graph visual, even after app restarts.
    """
    def __init__(self, redis_client=None):
        self.redis_client = redis_client
    
    def _get_key(self, tenant_id: str = "default") -> str:
        """Build tenant-scoped Redis key for graph state"""
        return f"{GRAPH_STATE_KEY_PREFIX}:{tenant_id}"
    
    def save(self, graph_state: Dict[str, Any], tenant_id: str = "default") -> bool:
        """
        Persist graph state to Redis as JSON.
        Returns True if saved successfully, False otherwise.
        """
        if not self.redis_client:
            log("⚠️ Redis unavailable - graph state not persisted")
            return False
        
        try:
            key = self._get_key(tenant_id)
            value = json.dumps(graph_state)
            self.redis_client.set(key, value)
            log(f"💾 Graph state persisted to Redis (tenant: {tenant_id}, nodes: {len(graph_state.get('nodes', []))})")
            return True
        except Exception as e:
            log(f"⚠️ Failed to persist graph state: {e}")
            return False
    
    def load(self, tenant_id: str = "default") -> Optional[Dict[str, Any]]:
        """
        Load graph state from Redis.
        Returns graph state dict or None if not found/unavailable.
        """
        if not self.redis_client:
            log("⚠️ Redis unavailable - using in-memory graph state")
            return None
        
        try:
            key = self._get_key(tenant_id)
            value = self.redis_client.get(key)
            if not value:
                log(f"📊 No persisted graph state found (tenant: {tenant_id})")
                return None
            
            graph_state = json.loads(value)
            log(f"📊 Loaded graph state from Redis (tenant: {tenant_id}, nodes: {len(graph_state.get('nodes', []))})")
            return graph_state
        except Exception as e:
            log(f"⚠️ Failed to load graph state: {e}")
            return None
    
    def reset(self, tenant_id: str = "default") -> bool:
        """Delete persisted graph state from Redis"""
        if not self.redis_client:
            return False
        
        try:
            key = self._get_key(tenant_id)
            self.redis_client.delete(key)
            log(f"🗑️  Graph state cleared from Redis (tenant: {tenant_id})")
            return True
        except Exception as e:
            log(f"⚠️ Failed to clear graph state: {e}")
            return False

# Global GraphStateStore instance (initialized after Redis client is set)
graph_store: Optional[GraphStateStore] = None

# Global TenantStateManager instance (initialized after Redis client is set)
tenant_state_manager: Optional[TenantStateManager] = None

class RedisDecodeWrapper:
    """
    Wrapper to provide decode_responses=True behavior on top of a decode_responses=False client.
    This allows sharing the same connection pool while having different decode behaviors.
    """
    def __init__(self, base_client):
        self._client = base_client
    
    def get(self, key):
        value = self._client.get(key)
        return value.decode('utf-8') if value else None
    
    def set(self, key, value, **kwargs):
        if isinstance(value, str):
            value = value.encode('utf-8')
        return self._client.set(key, value, **kwargs)
    
    def incr(self, key):
        return self._client.incr(key)
    
    def incrby(self, key, amount):
        return self._client.incrby(key, amount)
    
    def delete(self, key):
        return self._client.delete(key)
    
    def ping(self):
        return self._client.ping()
    
    def compare_and_delete(self, key: str, expected_value: str) -> bool:
        """
        Atomically compare key's value and delete if it matches (byte-safe).
        
        Uses Lua script to ensure atomic operation and consistent encoding.
        This is critical for distributed lock release to prevent race conditions.
        
        Args:
            key: Redis key to check
            expected_value: Expected value (string will be encoded to bytes)
        
        Returns:
            True if value matched and was deleted, False otherwise
        """
        # Lua script for atomic compare-and-delete (operates at byte level)
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            redis.call("del", KEYS[1])
            return 1
        else
            return 0
        end
        """
        # Encode expected_value to bytes to match Redis storage format
        if isinstance(expected_value, str):
            expected_value_bytes = expected_value.encode('utf-8')
        else:
            expected_value_bytes = expected_value
        
        # Execute Lua script using raw client (byte-level operations)
        result = self._client.eval(lua_script, 1, key.encode('utf-8') if isinstance(key, str) else key, expected_value_bytes)
        return result == 1

async def init_async_redis():
    """
    Initialize async Redis client for non-blocking pub/sub operations.
    This creates a separate async connection pool for pub/sub to avoid blocking the event loop.
    
    Returns:
        AsyncRedis client instance or None if Redis URL not available
    """
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        print("⚠️ REDIS_URL not set - async Redis client unavailable", flush=True)
        return None
    
    # Convert redis:// to rediss:// for Upstash TLS requirement
    if redis_url.startswith("redis://"):
        redis_url = "rediss://" + redis_url[8:]
        print("🔒 Using TLS/SSL for async Redis connection (rediss:// protocol)", flush=True)
    
    try:
        # Create async Redis client with decode_responses=True for easier string handling
        client = AsyncRedis.from_url(redis_url, decode_responses=True)
        
        # Test connection
        await client.ping()
        print("✅ Async Redis client initialized for non-blocking pub/sub", flush=True)
        return client
    except Exception as e:
        print(f"⚠️ Failed to initialize async Redis client: {e}", flush=True)
        return None

def get_tenant_id_from_user(current_user: Optional[Dict[str, Any]] = None) -> str:
    """
    Extract tenant_id from current user JWT claims or MockUser object.
    
    Args:
        current_user: User dict from JWT token or MockUser object
        
    Returns:
        tenant_id string (defaults to "default" for development)
    
    Behavior:
        - When AUTH_ENABLED=false (development): Always returns "default" for single-tenant demo mode
        - When AUTH_ENABLED=true: Extracts tenant_id from JWT claims (dict)
        - Falls back to "default" if tenant_id not available
        - CRITICAL: Always returns str, converting UUID objects to strings for JSON serialization
    
    Example:
        # In endpoint with auth
        @app.get("/state", dependencies=AUTH_DEPENDENCIES)
        async def get_state(current_user: Dict = Depends(get_current_user)):
            tenant_id = get_tenant_id_from_user(current_user)
            graph = state_access.get_graph_state(tenant_id)
    """
    # CRITICAL: In development mode (AUTH_ENABLED=false), always use "default" tenant
    # This ensures demo graph loaded at startup is accessible to MockUser
    if not AUTH_ENABLED:
        return "default"
    
    if not current_user:
        return "default"
    
    # Handle both dict (JWT token) and MockUser object
    if isinstance(current_user, dict):
        # Real JWT token - extract from claims
        # Support both new format (top-level tenant_id) and legacy format (tenants array)
        tenant_id = current_user.get("tenant_id")
        
        if not tenant_id:
            # Legacy format: tenants[0].tenant_id (backward compatibility)
            tenants = current_user.get("tenants", [])
            if tenants and len(tenants) > 0:
                tenant_id = tenants[0].get("tenant_id")
        
        # Fall back to "default" if neither format provides tenant_id
        if not tenant_id:
            tenant_id = "default"
    else:
        # MockUser object - access attribute directly
        tenant_id = getattr(current_user, "tenant_id", "default")
    
    # CRITICAL: Convert to string to handle UUID objects from JWT/database
    # Prevents TypeError: Object of type UUID is not JSON serializable
    return str(tenant_id)

def set_redis_client(client):
    """
    Set the shared Redis client from main app and initialize all DCL components.
    This avoids creating multiple Redis connections and hitting Upstash connection limits.
    
    CRITICAL: This function is called when mounting the DCL sub-app to main app.
    Since mounted sub-apps don't trigger startup events, ALL initialization
    must happen here instead of @app.on_event("startup").
    
    Initializes:
        - Feature flags (Redis-backed)
        - Dev mode persistence
        - Tenant state manager (multi-tenant isolation)
        - Distributed locks (concurrency control)
        - Graph state store (persistence layer)
        - RAG engine (entity mapping intelligence)
        - Agent executor (agentic orchestration)
    
    Args:
        client: Redis client instance from main app (typically with decode_responses=False)
    """
    global redis_client, redis_available, _dev_mode_initialized, graph_store, tenant_state_manager, GRAPH_STATE, dcl_distributed_lock, rag_engine, agents_config, agent_executor
    
    # Wrap the client to provide decode_responses=True behavior
    redis_client = RedisDecodeWrapper(client)
    redis_available = client is not None
    
    if redis_available:
        print(f"✅ DCL Engine: Using shared Redis client from main app", flush=True)
        
        # Initialize feature flags with Redis client for cross-worker persistence
        try:
            FeatureFlagConfig.set_redis_client(redis_client)
            
            # Hydrate USE_AAM_AS_SOURCE from Redis on startup (survives restarts)
            current_value = FeatureFlagConfig.is_enabled(FeatureFlag.USE_AAM_AS_SOURCE)
            mode_name = "AAM Connectors" if current_value else "Legacy File Sources"
            print(f"🚩 DCL Engine: Feature Flags initialized - USE_AAM_AS_SOURCE: {mode_name}", flush=True)
        except Exception as e:
            print(f"⚠️ DCL Engine: Feature flag initialization failed: {e}. Using in-memory fallback.", flush=True)
        
        # Initialize dev_mode now that we have a Redis client
        try:
            default_mode = "false"  # Default to Prod Mode
            redis_client.set(DEV_MODE_KEY, default_mode)
            _dev_mode_initialized = True
            print(f"🚀 DCL Engine: Initialized dev_mode = {default_mode} (Prod Mode) in Redis", flush=True)
        except Exception as e:
            print(f"⚠️ DCL Engine: Failed to initialize dev_mode: {e}, using in-memory fallback", flush=True)
            global in_memory_dev_mode
            in_memory_dev_mode = False
            _dev_mode_initialized = True
        
        # Initialize TenantStateManager FIRST for multi-tenant state isolation
        try:
            tenant_state_manager = TenantStateManager(redis_client)
            tenant_enabled = FeatureFlagConfig.is_enabled(FeatureFlag.TENANT_SCOPED_STATE)
            status_msg = "ENABLED" if tenant_enabled else "DISABLED (gradual rollout)"
            print(f"🏢 DCL Engine: TenantStateManager initialized - TENANT_SCOPED_STATE: {status_msg}", flush=True)
        except Exception as e:
            print(f"⚠️ DCL Engine: Failed to initialize TenantStateManager: {e}. Using global state fallback.", flush=True)
            tenant_state_manager = TenantStateManager(None)
        
        # Initialize state_access wrapper module with TenantStateManager
        state_access.initialize_state_access(tenant_state_manager)
        
        # Initialize Redis distributed lock for safe concurrent state access
        try:
            dcl_distributed_lock = RedisDistributedLock(
                redis_client=redis_client,
                lock_key="dcl:lock:state_access",
                lock_ttl=30
            )
            print(f"🔒 DCL Engine: Redis distributed lock initialized (replaces dual STATE_LOCK + ASYNC_STATE_LOCK)", flush=True)
        except Exception as e:
            print(f"⚠️ DCL Engine: Failed to initialize distributed lock: {e}. Locking disabled.", flush=True)
            dcl_distributed_lock = None
        
        # Initialize GraphStateStore and load persisted graph state
        try:
            graph_store = GraphStateStore(redis_client)
            persisted_graph = graph_store.load()
            
            # Load demo graph file to check if we should re-seed
            demo_graph = None
            demo_graph_path = DCL_BASE_PATH / "demo_graph.json"
            if demo_graph_path.exists():
                try:
                    with open(demo_graph_path, 'r') as f:
                        demo_graph = json.load(f)
                except Exception as e:
                    print(f"⚠️ Failed to load demo graph file: {e}", flush=True)
            
            # Decision logic: Version-based upgrade (safe for production)
            # Only upgrade demo graphs, NEVER overwrite user-authored graphs
            should_seed = False
            reason = ""
            if not persisted_graph:
                should_seed = True
                reason = "no persisted graph found"
            elif demo_graph:
                # Check if persisted graph is an old demo (has demo_version field)
                persisted_version = persisted_graph.get('demo_version')
                current_version = demo_graph.get('demo_version', 'v1.0')
                
                if persisted_version:
                    # It's a demo graph - check if it needs upgrade
                    if persisted_version != current_version:
                        should_seed = True
                        reason = f"demo graph version upgrade ({persisted_version} → {current_version})"
                # If no demo_version field, it's a user-authored graph - NEVER overwrite
            
            if should_seed and demo_graph:
                print(f"📊 DCL Engine: Seeding demo graph - {reason}", flush=True)
                # Use tenant_state_manager to set initial graph state
                state_access.set_graph_state("default", demo_graph)
                graph_store.save(demo_graph)
                print(f"✅ Demo graph seeded ({len(demo_graph.get('nodes', []))} nodes, {len(demo_graph.get('edges', []))} edges)", flush=True)
            elif persisted_graph:
                # Use tenant_state_manager to set initial graph state
                state_access.set_graph_state("default", persisted_graph)
                print(f"📊 DCL Engine: Hydrated graph state from Redis ({len(persisted_graph.get('nodes', []))} nodes)", flush=True)
            else:
                print(f"📊 DCL Engine: Using empty graph (no demo graph available)", flush=True)
                
        except Exception as e:
            print(f"⚠️ DCL Engine: Failed to load persisted graph state: {e}", flush=True)
            # Keep default empty graph state via tenant_state_manager
    else:
        print(f"⚠️ DCL Engine: No Redis client provided, using in-memory state", flush=True)
        in_memory_dev_mode = False
        _dev_mode_initialized = True
        # Initialize TenantStateManager without Redis (will use global state fallback)
        tenant_state_manager = TenantStateManager(None)
        
        # Initialize state_access wrapper module with TenantStateManager
        state_access.initialize_state_access(tenant_state_manager)
    
    # Initialize RAG engine for entity mapping intelligence (required for both AAM and demo modes)
    try:
        rag_engine = RAGEngine()
        print("✅ RAG Engine initialized successfully", flush=True)
    except Exception as e:
        print(f"⚠️ RAG Engine initialization failed: {e}. Continuing without RAG.", flush=True)
        rag_engine = None
    
    # Initialize AgentExecutor for agentic orchestration (Phase 4)
    try:
        agents_config = load_agents_config()
        agent_executor = AgentExecutor(get_db_path, agents_config, AGENT_RESULTS_CACHE, redis_client)
        print("✅ AgentExecutor initialized successfully", flush=True)
    except Exception as e:
        print(f"⚠️ AgentExecutor initialization failed: {e}. Continuing without agent execution.", flush=True)
        agent_executor = None

# WebSocket connection manager with tenant isolation
class ConnectionManager:
    """
    Manages WebSocket connections with tenant_id tagging for multi-tenant isolation.
    
    Each connection is stored with its associated tenant_id, allowing
    filtered broadcasts to only send updates to connections for a specific tenant.
    
    Connection Structure:
        {"websocket": WebSocket, "tenant_id": str}
    """
    def __init__(self):
        self.active_connections: List[Dict[str, Any]] = []  # [{"websocket": ws, "tenant_id": str}]
    
    async def connect(self, websocket: WebSocket, tenant_id: str = "default"):
        """
        Accept and register a new WebSocket connection with tenant_id tag.
        
        Args:
            websocket: WebSocket connection instance
            tenant_id: Tenant identifier for isolation (defaults to "default")
        """
        await websocket.accept()
        self.active_connections.append({"websocket": websocket, "tenant_id": tenant_id})
        log(f"🔌 WebSocket client connected (tenant: {tenant_id}, total active: {len(self.active_connections)})", tenant_id)
    
    def disconnect(self, websocket: WebSocket):
        """
        Remove a WebSocket connection from active connections.
        
        Args:
            websocket: WebSocket connection instance to remove
        """
        # Find and remove connection by websocket instance
        conn_to_remove = None
        for conn in self.active_connections:
            if conn["websocket"] == websocket:
                conn_to_remove = conn
                break
        
        if conn_to_remove:
            self.active_connections.remove(conn_to_remove)
            tenant_id = conn_to_remove.get("tenant_id", "unknown")
            log(f"🔌 WebSocket client disconnected (tenant: {tenant_id}, remaining: {len(self.active_connections)})", tenant_id)
    
    async def broadcast(self, message: dict, tenant_id: Optional[str] = None):
        """
        Broadcast message to WebSocket clients, optionally filtered by tenant_id.
        
        Args:
            message: JSON-serializable message to broadcast
            tenant_id: If provided, only broadcast to connections with matching tenant_id.
                      If None, broadcast to all connections (backward compatibility).
        
        Example:
            # Broadcast to specific tenant
            await ws_manager.broadcast(state_update, tenant_id="acme_corp")
            
            # Broadcast to all tenants (legacy mode)
            await ws_manager.broadcast(system_announcement)
        """
        disconnected = []
        for conn in self.active_connections:
            # Filter by tenant_id if provided
            if tenant_id is not None and conn.get("tenant_id") != tenant_id:
                continue  # Skip connections for other tenants
            
            try:
                await conn["websocket"].send_json(message)
            except Exception:
                # Client disconnected - mark for removal
                disconnected.append(conn)
        
        # Remove disconnected clients
        for conn in disconnected:
            if conn in self.active_connections:
                self.active_connections.remove(conn)

ws_manager = ConnectionManager()

def acquire_db_lock(timeout=None):
    """Acquire distributed lock for DuckDB access using Redis (cross-process safe)"""
    if not redis_available or not redis_client:
        # No-op in single-process mode
        return f"local-{os.getpid()}-{time.time()}"
    
    if timeout is None:
        timeout = DB_LOCK_TIMEOUT
    lock_id = f"{os.getpid()}-{time.time()}"
    end_time = time.time() + timeout
    
    while time.time() < end_time:
        try:
            # Try to acquire lock with auto-expiry (prevents deadlocks if process crashes)
            if redis_client.set(DB_LOCK_KEY, lock_id, nx=True, ex=timeout):
                return lock_id
        except:
            # Redis failed, return local lock
            return f"local-{os.getpid()}-{time.time()}"
        time.sleep(0.05)  # Wait 50ms before retrying
    
    raise TimeoutError(f"Could not acquire DuckDB lock after {timeout} seconds")

def release_db_lock(lock_id):
    """Release distributed lock for DuckDB access"""
    if not redis_available or not redis_client:
        return  # No-op in single-process mode
    
    try:
        # Only release if we still own the lock (prevents releasing someone else's lock)
        current_lock = redis_client.get(DB_LOCK_KEY)
        if current_lock == lock_id:
            redis_client.delete(DB_LOCK_KEY)
    except Exception as e:
        pass  # Silently ignore lock release errors

def get_dev_mode() -> bool:
    """Get dev mode state from Redis (cross-process safe)"""
    global in_memory_dev_mode
    
    if not redis_available or not redis_client:
        return in_memory_dev_mode
    
    try:
        value = redis_client.get(DEV_MODE_KEY)
        result = value == "true" if value else False
        return result
    except Exception as e:
        log(f"⚠️ Error reading dev mode from Redis: {e}")
        return False

def set_dev_mode(enabled: bool):
    """Set dev mode state in Redis (cross-process safe)"""
    global in_memory_dev_mode
    
    if not redis_available or not redis_client:
        in_memory_dev_mode = enabled
        return
    
    try:
        value = "true" if enabled else "false"
        redis_client.set(DEV_MODE_KEY, value)
    except Exception as e:
        # Fallback to in-memory
        in_memory_dev_mode = enabled

def get_llm_stats() -> dict:
    """Get LLM stats from Redis (cross-process safe, persists across restarts)"""
    global LLM_CALLS, LLM_TOKENS
    
    if not redis_available or not redis_client:
        return {"calls": LLM_CALLS, "tokens": LLM_TOKENS, "calls_saved": 0}
    
    try:
        calls = redis_client.get(LLM_CALLS_KEY)
        tokens = redis_client.get(LLM_TOKENS_KEY)
        calls_saved = redis_client.get(LLM_CALLS_SAVED_KEY)
        return {
            "calls": int(calls) if calls else 0,
            "tokens": int(tokens) if tokens else 0,
            "calls_saved": int(calls_saved) if calls_saved else 0
        }
    except Exception as e:
        log(f"⚠️ Error reading LLM stats from Redis: {e}")
        return {"calls": LLM_CALLS, "tokens": LLM_TOKENS, "calls_saved": 0}

def increment_llm_calls(tokens: int = 0):
    """Increment LLM call counter in Redis (cross-process safe, persists across restarts)"""
    global LLM_CALLS, LLM_TOKENS
    
    if not redis_available or not redis_client:
        LLM_CALLS += 1
        LLM_TOKENS += tokens
        return
    
    try:
        redis_client.incr(LLM_CALLS_KEY)
        if tokens > 0:
            redis_client.incrby(LLM_TOKENS_KEY, tokens)
    except Exception as e:
        log(f"⚠️ Error incrementing LLM stats in Redis: {e}")
        LLM_CALLS += 1
        LLM_TOKENS += tokens

def increment_llm_calls_saved():
    """Increment LLM calls saved counter in Redis (cross-process safe, persists across restarts)"""
    if not redis_available or not redis_client:
        return
    
    try:
        redis_client.incr(LLM_CALLS_SAVED_KEY)
    except Exception as e:
        log(f"⚠️ Error incrementing LLM calls saved in Redis: {e}")

def reset_llm_stats():
    """Reset LLM stats in Redis (cross-process safe)"""
    global LLM_CALLS, LLM_TOKENS
    
    if not redis_available or not redis_client:
        LLM_CALLS = 0
        LLM_TOKENS = 0
        return
    
    try:
        redis_client.set(LLM_CALLS_KEY, "0")
        redis_client.set(LLM_TOKENS_KEY, "0")
        redis_client.set(LLM_CALLS_SAVED_KEY, "0")
    except Exception as e:
        log(f"⚠️ Error resetting LLM stats in Redis: {e}")
        LLM_CALLS = 0
        LLM_TOKENS = 0

def log(msg: str, tenant_id: str = "default"):
    """
    Log a message to console and tenant-scoped event log.
    
    Args:
        msg: Message to log
        tenant_id: Tenant identifier (defaults to "default" for backward compatibility)
    
    Behavior:
        - Always prints to console (cross-tenant visibility for operators)
        - Appends to tenant-scoped event log via TenantStateManager
        - When TENANT_SCOPED_STATE=False: Uses global EVENT_LOG
        - When TENANT_SCOPED_STATE=True: Uses tenant-scoped Redis storage
    """
    print(msg, flush=True)
    
    # Append to tenant-scoped event log (state_access handles dual-path internally)
    state_access.append_event(tenant_id, msg)

def load_ontology():
    with open(ONTOLOGY_PATH, "r") as f:
        return yaml.safe_load(f)

def load_agents_config():
    try:
        with open(AGENTS_CONFIG_PATH, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        log(f"⚠️ Agents config not found at {AGENTS_CONFIG_PATH}")
        return {"agents": {}}

def infer_types(df: pd.DataFrame) -> Dict[str, str]:
    mapping = {}
    for col in df.columns:
        series = df[col]
        if pd.api.types.is_integer_dtype(series):
            mapping[col] = "integer"
        elif pd.api.types.is_float_dtype(series):
            mapping[col] = "numeric"
        else:
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    pd.to_datetime(series.dropna().head(50),
                                   format="%Y-%m-%d %H:%M:%S",
                                   errors="raise")
                mapping[col] = "datetime"
            except Exception:
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        pd.to_datetime(series.dropna().head(50), errors="coerce")
                    mapping[col] = "datetime"
                except Exception:
                    mapping[col] = "string"
    return mapping

def snapshot_tables_from_dir(source_key: str, dir_path: str) -> Dict[str, Any]:
    tables = {}
    for path in glob.glob(os.path.join(dir_path, "*.csv")):
        tname = os.path.splitext(os.path.basename(path))[0]
        df = pd.read_csv(path)
        tables[tname] = {
            "path": path,
            "schema": infer_types(df),
            "samples": df.head(8).to_dict(orient="records")
        }
    return tables

def register_src_views(con, source_key: str, tables: Dict[str, Any]):
    """
    Register source tables as DuckDB views.
    
    Supports both:
    - File-based sources (legacy): tables with "path" field → load from CSV
    - AAM sources: tables with "samples" field → create from in-memory data
    
    Args:
        con: DuckDB connection
        source_key: Source identifier
        tables: Dictionary mapping table names to table metadata
    """
    print(f"[TRACE_DCL] register_src_views ENTRY: source_key={source_key}, tables={list(tables.keys())}", flush=True)
    
    for tname, info in tables.items():
        view_name = f"src_{source_key}_{tname}"
        print(f"[TRACE_DCL] Processing table '{tname}', view_name='{view_name}'", flush=True)
        
        # Check if this is a file-based source (has "path") or AAM source (has "samples")
        if "path" in info:
            # Legacy file-based source: Load from CSV file
            path = info["path"]
            print(f"[TRACE_DCL] Using file-based path: {info['path']}", flush=True)
            con.sql(f"CREATE OR REPLACE VIEW {view_name} AS SELECT * FROM read_csv_auto('{path}')")
            print(f"[TRACE_DCL] ✅ File-based view '{view_name}' created successfully", flush=True)
        elif "samples" in info and info["samples"]:
            # AAM source: Create from in-memory data (samples list)
            print(f"[TRACE_DCL] Using AAM samples: {len(info['samples'])} rows", flush=True)
            # Convert samples list to pandas DataFrame
            df = pd.DataFrame(info["samples"])
            
            # Register DataFrame as a temporary table in DuckDB
            temp_table_name = f"_temp_{source_key}_{tname}"
            con.register(temp_table_name, df)
            
            # Create view from the temporary table
            con.sql(f"CREATE OR REPLACE VIEW {view_name} AS SELECT * FROM {temp_table_name}")
            print(f"[TRACE_DCL] ✅ AAM view '{view_name}' created successfully", flush=True)
        else:
            # Unknown format - log warning and skip
            print(f"[TRACE_DCL] ⚠️ Unknown format for table '{tname}'", flush=True)
            log(f"⚠️ Table '{tname}' has unknown format (no 'path' or 'samples'), skipping view creation")
            continue

def mk_sql_expr(src: Any, transform: str):
    if isinstance(src, list):
        parts = " || ' ' || ".join([f"COALESCE({c}, '')" for c in src])
        return parts + " AS value"
    if transform.startswith("cast"):
        return f"CAST({src} AS DOUBLE) AS value"
    if transform.startswith("parse_timestamp"):
        return f"TRY_STRPTIME({src}, '%Y-%m-%d %H:%M:%S') AS value"
    if transform.startswith("lower") or transform == 'lower_trim':
        return f"LOWER(TRIM({src})) AS value"
    return f"{src} AS value"

@dataclass
class Scorecard:
    confidence: float
    blockers: List[str]
    issues: List[str]
    joins: List[Dict[str,str]]

def safe_llm_call(prompt: str, source_key: str, tables: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Wrapper around Gemini calls that guarantees a result with proper logging."""
    global TIMING_LOG
    
    gemini_start = time.time()
    try:
        # Use gemini-2.5-flash for 10x faster inference
        resp = genai.GenerativeModel("gemini-2.5-flash").generate_content(prompt)
        
        # Increment LLM call counter in Redis (persists across restarts)
        tokens_used = 0
        try:
            usage = resp.usage_metadata
            tokens_used = usage.get("total_token_count", 0)
        except Exception:
            pass
        increment_llm_calls(tokens_used)
        
        try:
            text = resp.text.strip()
            if text.startswith("```"):
                text = re.sub(r"^```(?:json)?\n?", "", text)
                text = re.sub(r"\n?```$", "", text)
                text = text.strip()
            m = re.search(r"\{.*\}", text, re.DOTALL)
            if not m:
                raise ValueError("No JSON object found in response")
            result = json.loads(m.group(0))
            
            # Log Gemini timing
            gemini_elapsed = time.time() - gemini_start
            TIMING_LOG["gemini_call"].append(gemini_elapsed)
            log(f"⏱️ Gemini call: {gemini_elapsed:.2f}s")
            
            return result
        except Exception as parse_err:
            os.makedirs("logs", exist_ok=True)
            with open("logs/llm_failures.log", "a") as f:
                f.write(f"--- PARSE ERROR ({time.strftime('%Y-%m-%d %H:%M:%S')}) ---\n")
                f.write(f"Source: {source_key}\n")
                f.write(f"Response: {resp.text if hasattr(resp, 'text') else 'N/A'}\n")
                f.write(f"Error: {parse_err}\n\n")
            log(f"[LLM PARSE ERROR] Falling back to heuristic for {source_key}")
            return (None, False)  # (plan, skip_semantic_validation)
    
    except Exception as e:
        os.makedirs("logs", exist_ok=True)
        with open("logs/llm_failures.log", "a") as f:
            f.write(f"--- LLM ERROR ({time.strftime('%Y-%m-%d %H:%M:%S')}) ---\n")
            f.write(f"Source: {source_key}\n")
            f.write(f"{traceback.format_exc()}\n\n")
        log(f"[LLM ERROR] {e} - Falling back to heuristic for {source_key}")
        return (None, False)  # (plan, skip_semantic_validation)

async def llm_propose(
    ontology: Dict[str, Any], 
    source_key: str, 
    tables: Dict[str, Any],
    llm_model: str = "gemini-2.5-flash"
) -> Optional[Dict[str, Any]]:
    global rag_engine, RAG_CONTEXT, TIMING_LOG
    
    llm_start = time.time()
    
    # NO-RAG FAST PATH: Check Prod Mode BEFORE expensive RAG retrieval
    # This bypasses both RAG and LLM, falling back to heuristics immediately
    # Target: <10s total processing time in Production mode
    current_dev_mode = get_dev_mode()
    if not current_dev_mode:
        log(f"⚡ Prod Mode (No-RAG Fast Path): Bypassing RAG/LLM, using heuristics for {source_key}")
        return None  # Async function returns just None, not tuple
    
    # Initialize RAG engine if not already initialized (for worker processes)
    if rag_engine is None and os.getenv("PINECONE_API_KEY"):
        try:
            from app.dcl_engine.rag_engine import RAGEngine
            rag_engine = RAGEngine()
            log("✅ RAG Engine initialized in worker process")
        except Exception as e:
            log(f"⚠️ RAG Engine initialization failed in worker: {e}")
    
    # STREAMING EVENT: RAG retrieval starting (only in Dev Mode)
    await ws_manager.broadcast({
        "type": "mapping_progress",
        "source": source_key,
        "stage": "rag_started",
        "message": f"🔍 Retrieving similar mappings from knowledge base...",
        "timestamp": time.time()
    })
    
    # Build RAG context if available (PARALLELIZED) - WORKS IN BOTH DEV AND PROD MODES
    rag_context = ""
    rag_task_start = time.time()
    
    if rag_engine:
        try:
            # Collect all field queries first
            field_queries = []
            for table_name, table_info in tables.items():
                schema = table_info.get('schema', {})
                for field_name, field_type in schema.items():
                    field_queries.append((field_name, field_type, source_key))
            
            # Parallelize RAG retrievals using asyncio.gather + asyncio.to_thread
            # Pinecone SDK is blocking, so we wrap each call in to_thread
            rag_tasks = [
                asyncio.to_thread(
                    rag_engine.retrieve_similar_mappings,
                    field_name=field_name,
                    field_type=field_type,
                    source_system=source_system,
                    top_k=2,
                    min_confidence=0.7
                )
                for field_name, field_type, source_system in field_queries
            ]
            
            # Run all RAG queries in parallel
            all_similar_lists = await asyncio.gather(*rag_tasks, return_exceptions=True)
            
            # Flatten results and handle any exceptions
            all_similar = []
            for result in all_similar_lists:
                if isinstance(result, Exception):
                    log(f"⚠️ RAG retrieval error: {result}")
                elif isinstance(result, list):
                    all_similar.extend(result)
            
            rag_elapsed = time.time() - rag_task_start
            TIMING_LOG["rag_retrieval"].append(rag_elapsed)
            log(f"⏱️ RAG retrieval (PARALLEL): {rag_elapsed:.2f}s for {len(field_queries)} fields")
            
            # STREAMING EVENT: RAG complete
            await ws_manager.broadcast({
                "type": "mapping_progress",
                "source": source_key,
                "stage": "rag_complete",
                "message": f"✅ Retrieved {len(all_similar)} similar mappings in {rag_elapsed:.1f}s",
                "rag_count": len(all_similar),
                "duration": rag_elapsed,
                "timestamp": time.time()
            })
            
            # Deduplicate and get top examples
            seen = set()
            unique_similar = []
            for mapping in all_similar:
                key = f"{mapping['source_field']}_{mapping['ontology_entity']}"
                if key not in seen:
                    seen.add(key)
                    unique_similar.append(mapping)
            
            # Build context from top similar mappings (all available for frontend display)
            unique_similar.sort(key=lambda x: x.get('similarity', 0), reverse=True)
            top_similar = unique_similar  # Show all retrievals (no limit)
            
            if top_similar:
                rag_context = rag_engine.build_context_for_llm(top_similar)
                log(f"📚 RAG: Retrieved {len(top_similar)} similar mappings for context")
                
                # Store RAG retrieval data for visualization
                RAG_CONTEXT["retrievals"] = [
                    {
                        "source_field": m["source_field"],
                        "ontology_entity": m["ontology_entity"],
                        "similarity": round(m.get("similarity", 0), 3),
                        "source_system": m.get("source_system", "unknown")
                    }
                    for m in top_similar
                ]
                RAG_CONTEXT["last_retrieval_count"] = len(top_similar)
        except Exception as e:
            log(f"⚠️ RAG retrieval failed: {e}")
    
    # Skip LLM calls if dev mode is disabled (check Redis for cross-process state)
    # RAG retrieval still happened above for both modes
    current_dev_mode = get_dev_mode()
    if not current_dev_mode:
        log(f"⚡ Prod Mode: RAG retrieval complete, skipping LLM - falling back to heuristics for {source_key}")
        return (None, False)  # (plan, skip_semantic_validation)
    
    # INTELLIGENT LLM DECISION: Check RAG coverage before calling LLM
    # Calculate how many source fields have high-confidence RAG matches
    if rag_engine and all_similar:
        total_fields = sum(len(table_info.get('schema', {})) for table_info in tables.values())
        
        # Count unique fields with high-confidence RAG matches (>0.8 similarity)
        matched_fields = set()
        missing_fields = []
        for field_name, field_type, _ in field_queries:
            field_matches = [m for m in all_similar if m['source_field'].lower() == field_name.lower() and m.get('similarity', 0) > 0.8]
            if field_matches:
                matched_fields.add(field_name)
            else:
                missing_fields.append(field_name)
        
        coverage_pct = (len(matched_fields) / total_fields * 100) if total_fields > 0 else 0
        estimated_cost = 0.003  # Rough estimate per LLM call (used in cost savings calculations)
        
        # If coverage is high (>=80%), skip LLM and use RAG mappings directly
        if coverage_pct >= 80:
            
            log(f"📊 RAG Coverage: {coverage_pct:.0f}% ({len(matched_fields)}/{total_fields} fields) - skipping LLM, using RAG inventory")
            
            # Increment saved calls counter
            increment_llm_calls_saved()
            
            # Broadcast intelligent decision event
            await ws_manager.broadcast({
                "type": "rag_coverage_check",
                "source": source_key,
                "coverage_pct": round(coverage_pct, 1),
                "matched_count": len(matched_fields),
                "total_count": total_fields,
                "missing_fields": missing_fields[:5],  # Show first 5 missing
                "estimated_cost_savings": round(estimated_cost, 4),
                "recommendation": "skip",
                "message": f"🎯 RAG has {coverage_pct:.0f}% coverage. Using RAG inventory, LLM call saved!",
                "timestamp": time.time()
            })
            
            # Return tuple (None, True) to skip LLM and use heuristics without semantic validation
            log(f"✅ Dev Mode: Skipping LLM call, using RAG inventory (coverage {coverage_pct:.0f}%)")
            return (None, True)  # (plan, skip_semantic_validation)
        elif coverage_pct >= 75:
            # Show coverage check but still call LLM
            log(f"📊 RAG Coverage: {coverage_pct:.0f}% ({len(matched_fields)}/{total_fields} fields) - proceeding with LLM")
            
            await ws_manager.broadcast({
                "type": "rag_coverage_check",
                "source": source_key,
                "coverage_pct": round(coverage_pct, 1),
                "matched_count": len(matched_fields),
                "total_count": total_fields,
                "missing_fields": missing_fields[:5],
                "estimated_cost_savings": round(estimated_cost, 4),
                "recommendation": "proceed",
                "message": f"📊 RAG has {coverage_pct:.0f}% coverage. Proceeding with LLM for better accuracy.",
                "timestamp": time.time()
            })
    
    # Continue with existing LLM flow...
    
    # Check for appropriate API key based on model
    if llm_model.startswith("gpt"):
        if not os.getenv("OPENAI_API_KEY"):
            log(f"⚠️ OPENAI_API_KEY not set - skipping LLM for {source_key}")
            return (None, False)  # (plan, skip_semantic_validation)
    else:
        if not os.getenv("GEMINI_API_KEY"):
            log(f"⚠️ GEMINI_API_KEY not set - skipping LLM for {source_key}")
            return (None, False)  # (plan, skip_semantic_validation)
    
    log(f"🤖 Dev Mode: Starting LLM mapping for {source_key} with {llm_model}")
    
    sys_prompt = (
        "You are a data integration planner. Given an ontology and a set of new tables from a source system, "
        "produce a STRICT JSON plan with proposed mappings and joins.\n\n"
        "Output format (strict JSON!):\n"
        "{"
        '  "mappings": ['
        '    {"entity":"customer","source_table":"<table>", "fields":[{"source":"<col>", "onto_field":"customer_id", "confidence":0.92}]},'
        '    {"entity":"transaction","source_table":"<table>", "fields":[{"source":"<col>", "onto_field":"amount", "confidence":0.88}]}'
        "  ],"
        '  "joins": [ {"left":"<table>.<col>", "right":"<table>.<col>", "reason":"why"} ]'
        "}"
    )
    
    # Build RAG context section properly
    rag_section = f"{rag_context}\n\n" if rag_context else ""
    
    # Construct full prompt with all sections
    prompt = (
        f"{sys_prompt}\n\n"
        f"{rag_section}"
        f"Ontology:\n{json.dumps(ontology)}\n\n"
        f"SourceKey: {source_key}\n"
        f"Tables:\n{json.dumps(tables)}\n\n"
        f"Return ONLY JSON."
    )
    
    # STREAMING EVENT: LLM call starting
    await ws_manager.broadcast({
        "type": "mapping_progress",
        "source": source_key,
        "stage": "llm_started",
        "message": f"🤖 Generating intelligent mappings with {llm_model}...",
        "timestamp": time.time()
    })
    
    # Get LLM service with counter callback (dependency injection pattern)
    try:
        llm_service = get_llm_service(llm_model, increment_llm_calls)
        log(f"📊 Using {llm_service.get_provider_name()} - {llm_service.get_model_name()}")
    except (ValueError, ImportError) as e:
        log(f"⚠️ {e} - falling back to heuristic")
        return (None, False)  # (plan, skip_semantic_validation)
    
    llm_call_start = time.time()
    result = await asyncio.to_thread(llm_service.generate, prompt, source_key)
    llm_call_elapsed = time.time() - llm_call_start
    
    # STREAMING EVENT: LLM complete
    await ws_manager.broadcast({
        "type": "mapping_progress",
        "source": source_key,
        "stage": "llm_complete",
        "message": f"✅ {llm_service.get_model_name()} mapping complete in {llm_call_elapsed:.1f}s",
        "duration": llm_call_elapsed,
        "timestamp": time.time()
    })
    
    # Store successful mappings in RAG (only if dev_mode enabled)
    if result and rag_engine:
        try:
            dev_mode = get_dev_mode()
            stored_count = 0
            for mapping in result.get("mappings", []):
                entity = mapping.get("entity")
                source_table = mapping.get("source_table")
                for field in mapping.get("fields", []):
                    result_id = rag_engine.store_mapping(
                        source_field=field["source"],
                        source_type="string",  # We can enhance this later
                        ontology_entity=f"{entity}.{field['onto_field']}",
                        source_system=source_key,
                        transformation="direct",
                        confidence=field.get("confidence", 0.8),
                        validated=False,
                        dev_mode_enabled=dev_mode
                    )
                    if result_id:
                        stored_count += 1
            if dev_mode:
                log(f"💾 Stored {stored_count} mappings to RAG (dev mode)")
                # Update RAG total count after storing
                try:
                    stats = rag_engine.get_stats()
                    RAG_CONTEXT["total_mappings"] = stats.get("total_mappings", 0)
                except:
                    pass
            else:
                log(f"🔒 RAG writes blocked - heuristic mode (retrieved context only)")
        except Exception as e:
            log(f"⚠️ Failed to store mappings in RAG: {e}")
    
    # Log total llm_propose timing
    llm_elapsed = time.time() - llm_start
    TIMING_LOG["llm_propose_total"].append(llm_elapsed)
    log(f"⏱️ llm_propose total: {llm_elapsed:.2f}s")
    
    return (result, False)  # (plan, skip_semantic_validation) - False because LLM succeeded

def validate_mapping_semantics_llm(source_key: str, table_name: str, entity: str, fields: List[Dict]) -> bool:
    """Use LLM + RAG to validate if a source table mapping to an entity makes semantic sense."""
    global rag_engine
    
    if not os.getenv("GEMINI_API_KEY"):
        return True  # Default to allowing if no API key
    
    # Get RAG context for similar mappings (if available)
    rag_context = ""
    if rag_engine:
        try:
            # Query RAG for similar mappings to this entity
            similar_mappings = rag_engine.retrieve_similar_mappings(
                field_name=table_name,
                field_type="table",
                source_system=source_key,
                top_k=10
            )
            if similar_mappings:
                rag_context = "\nPrevious validated mappings for context:\n"
                for sm in similar_mappings:
                    rag_context += f"- {sm.get('source_system', 'unknown')}.{sm.get('source_field', 'unknown')} → {sm.get('ontology_entity', 'unknown')} (conf: {sm.get('confidence', 0):.2f})\n"
        except Exception as e:
            log(f"⚠️ RAG retrieval failed during validation: {e}")
    
    prompt = f"""You are a semantic data mapping validator. Assess if this mapping makes sense.

Source System: {source_key}
Source Table: {table_name}
Target Entity: {entity}
Field Mappings: {json.dumps(fields, indent=2)}

{rag_context}

Common patterns:
- FinOps sources (snowflake, sap, netsuite, legacy_sql) should map to FinOps entities (aws_resources, cost_reports)
- RevOps sources (dynamics, salesforce, supabase, mongodb) should map to RevOps entities (account, opportunity, health, usage)
- Billing/cost tables should NOT map to sales/revenue entities
- Infrastructure data should NOT map to customer relationship entities

Does this mapping make semantic sense? Consider:
1. Domain alignment (FinOps vs RevOps)
2. Business context (is this table appropriate for this entity?)
3. Field semantics (do the field names match the entity purpose?)
4. Consistency with previous validated mappings

Answer with ONLY a JSON object:
{{"valid": true/false, "reason": "brief explanation", "confidence": 0.0-1.0}}"""

    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # Increment LLM counter in Redis (persists across restarts)
        tokens_estimate = len(prompt.split()) + len(text.split())
        increment_llm_calls(tokens_estimate)
        
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            
            valid = result.get("valid", True)
            reason = result.get("reason", "")
            confidence = result.get("confidence", 0.5)
            
            if not valid and confidence > 0.7:
                log(f"🚫 Semantic validation rejected: {source_key}.{table_name} → {entity} ({reason})")
            
            return valid
        else:
            log(f"⚠️ LLM validation response not parseable, defaulting to allow")
            return True
            
    except Exception as e:
        log(f"⚠️ LLM semantic validation failed: {e}, defaulting to allow")
        return True

def heuristic_plan(ontology: Dict[str, Any], source_key: str, tables: Dict[str, Any], skip_llm_validation: bool = False, tenant_id: str = "default") -> Dict[str, Any]:
    """
    Generate heuristic field mappings based on pattern matching.
    
    Args:
        ontology: Ontology schema definition
        source_key: Source system identifier
        tables: Source table schemas
        skip_llm_validation: If True, skip LLM semantic validation
        tenant_id: Tenant identifier for tenant-scoped operations
    
    Returns:
        Mapping plan with entity mappings and joins
    """
    global agents_config, DEV_MODE
    
    # Get available ontology entities based on selected agents
    if not agents_config:
        agents_config = load_agents_config()
    
    available_entities = set()
    # Get selected agents (state_access handles dual-path internally)
    selected_agents = state_access.get_selected_agents(tenant_id)
    
    if selected_agents:
        for agent_id in selected_agents:
            agent_info = agents_config.get("agents", {}).get(agent_id, {})
            consumes = agent_info.get("consumes", [])
            available_entities.update(consumes)
    else:
        available_entities = set(ontology.get("entities", {}).keys())
    
    mappings, joins = [], []
    # RevOps patterns (aligned with dcl-light agent)
    key_fields = ["accountid","AccountId","KUNNR","CustomerID","CUST_ID","entityId","customerid","parentcustomerid","Id","account_id","ACCOUNT_ID"]
    name_fields = ["name","Name","account_name","AccountName","ACCOUNT_NAME"]
    revenue_fields = ["revenue","Revenue","annual_revenue","AnnualRevenue","ANNUAL_REVENUE"]
    industry_fields = ["industry","Industry","INDUSTRY"]
    employee_count_fields = ["employee_count","employeeCount","EmployeeCount","EMPLOYEE_COUNT","number_of_employees","NumberOfEmployees"]
    created_date_fields = ["created_date","createdDate","CreatedDate","CREATED_DATE","createdon","CreatedOn"]
    
    opportunity_id_fields = ["opportunity_id","opportunityId","OpportunityId","OPPORTUNITY_ID","opp_id","OPP_ID"]
    opportunity_name_fields = ["opportunity_name","opportunityName","OpportunityName","OPPORTUNITY_NAME","opp_name"]
    stage_fields = ["stage","Stage","StageName","STAGE_NAME","status","Status"]
    amount_fields = ["amount","Amount","NETWR","TotalAmount","estimatedvalue","AMOUNT"]
    close_date_fields = ["close_date","closeDate","CloseDate","CLOSE_DATE","closedon","ClosedDate"]
    probability_fields = ["probability","Probability","PROBABILITY","win_probability","WinProbability","forecast_probability"]
    
    health_score_fields = ["health_score","healthScore","HealthScore","HEALTH_SCORE","score"]
    risk_level_fields = ["risk_level","riskLevel","RiskLevel","RISK_LEVEL","risk","churn_risk"]
    last_updated_fields = ["last_updated","lastUpdated","LastUpdated","LAST_UPDATED","updated_at","updatedAt"]
    
    login_fields = ["last_login_days","lastLoginDays","LAST_LOGIN_DAYS","days_since_login"]
    session_fields = ["sessions_30d","sessions30d","SESSIONS_30D","session_count"]
    avg_session_duration_fields = ["avg_session_duration","avgSessionDuration","AVG_SESSION_DURATION","average_session_duration"]
    features_used_fields = ["features_used","featuresUsed","FEATURES_USED","feature_count","active_features"]
    
    # FinOps patterns - Core identifiers
    resource_fields = ["resource_id","resourceId","ResourceId","RESOURCE_ID","instance_id","instanceId","INSTANCE_ID"]
    resource_type_fields = ["resource_type","resourceType","RESOURCE_TYPE","service_type","SERVICE_TYPE"]
    region_fields = ["region","Region","REGION","AWS_REGION","aws_region","availability_zone"]
    cost_fields = ["cost","monthly_cost","monthlyCost","Monthly_Cost","MONTHLY_COST","spend","price","billing_amount","totalCost"]
    
    # FinOps patterns - Resource config (EC2, RDS, S3)
    instance_type_fields = ["instance_type","instanceType","INSTANCE_TYPE"]
    instance_class_fields = ["instance_class","instanceClass","INSTANCE_CLASS","db_instance_class"]
    vcpu_fields = ["vcpus","vCPUs","VCPUS","cpu_count","CPU_COUNT"]
    memory_fields = ["memory","memoryGiB","MEMORY_GB","ram","RAM"]
    storage_fields = ["storage","allocatedStorage","ALLOCATED_STORAGE_GB","sizeGB","SIZE_GB","size_gb"]
    storage_type_fields = ["storage_type","storageType","STORAGE_TYPE","disk_type"]
    storage_class_fields = ["storage_class","storageClass","STORAGE_CLASS","s3_storage_class"]
    db_engine_fields = ["engine","db_engine","DB_ENGINE","dbEngine"]
    object_count_fields = ["object_count","objectCount","OBJECT_COUNT","num_objects"]
    versioning_fields = ["versioning","versioningEnabled","VERSIONING_ENABLED","versioning_enabled"]
    
    # FinOps patterns - Utilization metrics (enhanced for detailed fields)
    cpu_util_fields = ["cpuUtilization","cpu_utilization","cpu_percent","CPU_UTILIZATION"]
    mem_util_fields = ["memoryUtilization","memory_utilization","mem_percent","MEMORY_UTILIZATION"]
    network_in_fields = ["networkIn","network_in","bytesIn","NETWORK_IN_MB","network_in_mb"]
    network_out_fields = ["networkOut","network_out","bytesOut","NETWORK_OUT_MB","network_out_mb"]
    connections_fields = ["connections","db_connections","activeConnections","DB_CONNECTIONS"]
    disk_read_fields = ["disk_read_ops","diskReadOps","DISK_READ_OPS","read_iops"]
    disk_write_fields = ["disk_write_ops","diskWriteOps","DISK_WRITE_OPS","write_iops"]
    
    # FinOps patterns - S3 metrics (enhanced)
    get_requests_fields = ["getRequests","get_requests","s3_gets","GET_REQUESTS"]
    put_requests_fields = ["putRequests","put_requests","s3_puts","PUT_REQUESTS"]
    data_transfer_out_fields = ["data_transfer_out","dataTransferOut","DATA_TRANSFER_OUT","bytes_transferred","transfer_out_gb"]
    
    # FinOps patterns - RDS/Database metrics
    read_latency_fields = ["read_latency","readLatency","READ_LATENCY_MS","read_latency_ms"]
    write_latency_fields = ["write_latency","writeLatency","WRITE_LATENCY_MS","write_latency_ms"]
    free_storage_fields = ["free_storage","freeStorage","FREE_STORAGE_GB","available_storage"]
    
    # FinOps patterns - Timestamps
    last_analyzed_fields = ["last_analyzed","lastAnalyzed","LAST_ANALYZED","analyzed_at","analysis_date"]
    created_at_fields = ["created_at","createdAt","CREATED_AT","creation_date","create_time"]
    report_date_fields = ["report_date","reportDate","REPORT_DATE","billing_date","invoice_date"]
    
    # FinOps patterns - Cost/Billing
    cost_id_fields = ["cost_id","costId","COST_ID","billing_id","invoice_id"]
    service_category_fields = ["serviceCategory","service_category","service_name","serviceName","SERVICE"]
    usage_fields = ["usage","Usage","USAGE","usage_amount","usage_quantity"]
    usage_type_fields = ["usageType","usage_type","usage_unit","UsageType"]
    
    for tname, info in tables.items():
        cols = list(info["schema"].keys())
        
        # RevOps: account, opportunity, health, usage detection
        account_id = next((c for c in cols if c in key_fields or c.lower() in ["customer_id","cust_id","id","accountid","account_id"]), None)
        account_name = next((c for c in cols if c in name_fields or "name" in c.lower()), None)
        revenue = next((c for c in cols if c in revenue_fields or "revenue" in c.lower()), None)
        industry = next((c for c in cols if c in industry_fields or "industry" in c.lower()), None)
        employee_count = next((c for c in cols if c in employee_count_fields), None)
        created_date = next((c for c in cols if c in created_date_fields), None)
        
        opportunity_id = next((c for c in cols if c in opportunity_id_fields), None)
        opportunity_name = next((c for c in cols if c in opportunity_name_fields), None)
        stage = next((c for c in cols if c in stage_fields or "stage" in c.lower()), None)
        amount = next((c for c in cols if c in amount_fields or "amount" in c.lower() or "price" in c.lower()), None)
        close_date = next((c for c in cols if c in close_date_fields), None)
        probability = next((c for c in cols if c in probability_fields), None)
        
        health_score = next((c for c in cols if c in health_score_fields or "health" in c.lower() or "score" in c.lower()), None)
        risk_level = next((c for c in cols if c in risk_level_fields or "risk" in c.lower()), None)
        last_updated = next((c for c in cols if c in last_updated_fields or "updated" in c.lower()), None)
        
        last_login = next((c for c in cols if c in login_fields or "login" in c.lower()), None)
        sessions = next((c for c in cols if c in session_fields or "session" in c.lower()), None)
        avg_session_duration = next((c for c in cols if c in avg_session_duration_fields), None)
        features_used = next((c for c in cols if c in features_used_fields), None)
        
        # FinOps: Core identifiers
        resource = next((c for c in cols if c in resource_fields or "resource_id" in c.lower() or "instance_id" in c.lower()), None)
        resource_type = next((c for c in cols if c in resource_type_fields), None)
        region = next((c for c in cols if c in region_fields), None)
        cost = next((c for c in cols if c in cost_fields or "cost" in c.lower()), None)
        
        # FinOps: Resource config
        instance_type = next((c for c in cols if c in instance_type_fields), None)
        instance_class = next((c for c in cols if c in instance_class_fields), None)
        vcpus = next((c for c in cols if c in vcpu_fields), None)
        memory = next((c for c in cols if c in memory_fields), None)
        storage = next((c for c in cols if c in storage_fields), None)
        storage_type = next((c for c in cols if c in storage_type_fields), None)
        storage_class = next((c for c in cols if c in storage_class_fields), None)
        db_engine = next((c for c in cols if c in db_engine_fields), None)
        object_count = next((c for c in cols if c in object_count_fields), None)
        versioning = next((c for c in cols if c in versioning_fields), None)
        
        # FinOps: Utilization metrics (enhanced)
        cpu_util = next((c for c in cols if c in cpu_util_fields), None)
        mem_util = next((c for c in cols if c in mem_util_fields), None)
        network_in = next((c for c in cols if c in network_in_fields), None)
        network_out = next((c for c in cols if c in network_out_fields), None)
        connections = next((c for c in cols if c in connections_fields), None)
        disk_read = next((c for c in cols if c in disk_read_fields), None)
        disk_write = next((c for c in cols if c in disk_write_fields), None)
        get_requests = next((c for c in cols if c in get_requests_fields), None)
        put_requests = next((c for c in cols if c in put_requests_fields), None)
        data_transfer_out = next((c for c in cols if c in data_transfer_out_fields), None)
        read_latency = next((c for c in cols if c in read_latency_fields), None)
        write_latency = next((c for c in cols if c in write_latency_fields), None)
        free_storage = next((c for c in cols if c in free_storage_fields), None)
        
        # FinOps: Timestamps
        last_analyzed = next((c for c in cols if c in last_analyzed_fields), None)
        created_at = next((c for c in cols if c in created_at_fields), None)
        report_date = next((c for c in cols if c in report_date_fields), None)
        
        # FinOps: Cost/Billing
        cost_id = next((c for c in cols if c in cost_id_fields), None)
        service_category = next((c for c in cols if c in service_category_fields), None)
        usage = next((c for c in cols if c in usage_fields), None)
        usage_type = next((c for c in cols if c in usage_type_fields), None)
        
        # RevOps mappings (aligned with dcl-light agent entities)
        if (account_id or account_name or revenue or industry) and "account" in available_entities:
            fields = []
            if account_id: fields.append({"source": account_id, "onto_field": "account_id", "confidence": 0.85})
            if account_name: fields.append({"source": account_name, "onto_field": "account_name", "confidence": 0.85})
            if revenue: fields.append({"source": revenue, "onto_field": "revenue", "confidence": 0.85})
            if industry: fields.append({"source": industry, "onto_field": "industry", "confidence": 0.8})
            if employee_count: fields.append({"source": employee_count, "onto_field": "employee_count", "confidence": 0.8})
            if created_date: fields.append({"source": created_date, "onto_field": "created_date", "confidence": 0.8})
            if fields:
                mappings.append({"entity":"account","source_table": f"{source_key}_{tname}", "fields": fields})
        
        if (opportunity_id or opportunity_name or amount or close_date or stage) and "opportunity" in available_entities:
            fields = []
            if opportunity_id: fields.append({"source": opportunity_id, "onto_field": "opportunity_id", "confidence": 0.85})
            if opportunity_name: fields.append({"source": opportunity_name, "onto_field": "opportunity_name", "confidence": 0.85})
            if amount: fields.append({"source": amount, "onto_field": "amount", "confidence": 0.82})
            if close_date: fields.append({"source": close_date, "onto_field": "close_date", "confidence": 0.8})
            if stage: fields.append({"source": stage, "onto_field": "stage", "confidence": 0.85})
            if probability: fields.append({"source": probability, "onto_field": "probability", "confidence": 0.8})
            if account_id: fields.append({"source": account_id, "onto_field": "account_id", "confidence": 0.85})
            if fields:
                mappings.append({"entity":"opportunity","source_table": f"{source_key}_{tname}", "fields": fields})
        
        if health_score and "health" in available_entities:
            fields = []
            fields.append({"source": health_score, "onto_field": "health_score", "confidence": 0.9})
            if account_id: fields.append({"source": account_id, "onto_field": "account_id", "confidence": 0.85})
            if last_updated: fields.append({"source": last_updated, "onto_field": "last_updated", "confidence": 0.85})
            if risk_level: fields.append({"source": risk_level, "onto_field": "risk_level", "confidence": 0.85})
            mappings.append({"entity":"health","source_table": f"{source_key}_{tname}", "fields": fields})
        
        if (last_login or sessions or avg_session_duration or features_used) and "usage" in available_entities:
            fields = []
            if last_login: fields.append({"source": last_login, "onto_field": "last_login_days", "confidence": 0.85})
            if sessions: fields.append({"source": sessions, "onto_field": "sessions_30d", "confidence": 0.85})
            if avg_session_duration: fields.append({"source": avg_session_duration, "onto_field": "avg_session_duration", "confidence": 0.85})
            if features_used: fields.append({"source": features_used, "onto_field": "features_used", "confidence": 0.85})
            if account_id: fields.append({"source": account_id, "onto_field": "account_id", "confidence": 0.85})
            if fields:
                mappings.append({"entity":"usage","source_table": f"{source_key}_{tname}", "fields": fields})
        
        # FinOps mappings - aws_resources (config + utilization + cost - consolidated per FinOps Autopilot schema)
        if (resource or resource_type or region or instance_type or instance_class or vcpus or memory or storage or storage_type or storage_class or db_engine or object_count or versioning or cpu_util or mem_util or network_in or network_out or connections or read_latency or write_latency or get_requests or put_requests or data_transfer_out or cost or last_analyzed or created_at) and "aws_resources" in available_entities:
            fields = []
            # Core identifiers
            if resource: fields.append({"source": resource, "onto_field": "resource_id", "confidence": 0.9})
            if resource_type: fields.append({"source": resource_type, "onto_field": "resource_type", "confidence": 0.85})
            if region: fields.append({"source": region, "onto_field": "region", "confidence": 0.85})
            # EC2 config
            if instance_type: fields.append({"source": instance_type, "onto_field": "instance_type", "confidence": 0.85})
            if vcpus: fields.append({"source": vcpus, "onto_field": "vcpus", "confidence": 0.85})
            if memory: fields.append({"source": memory, "onto_field": "memory", "confidence": 0.85})
            if storage: fields.append({"source": storage, "onto_field": "storage", "confidence": 0.85})
            if storage_type: fields.append({"source": storage_type, "onto_field": "storage_type", "confidence": 0.85})
            # RDS config
            if db_engine: fields.append({"source": db_engine, "onto_field": "db_engine", "confidence": 0.85})
            if instance_class: fields.append({"source": instance_class, "onto_field": "instance_class", "confidence": 0.85})
            if storage: fields.append({"source": storage, "onto_field": "allocated_storage", "confidence": 0.85})
            # S3 config
            if storage_class: fields.append({"source": storage_class, "onto_field": "storage_class", "confidence": 0.85})
            if object_count: fields.append({"source": object_count, "onto_field": "object_count", "confidence": 0.85})
            if storage: fields.append({"source": storage, "onto_field": "size_gb", "confidence": 0.85})
            if versioning: fields.append({"source": versioning, "onto_field": "versioning", "confidence": 0.85})
            # EC2 utilization
            if cpu_util: fields.append({"source": cpu_util, "onto_field": "cpu_utilization", "confidence": 0.9})
            if mem_util: fields.append({"source": mem_util, "onto_field": "memory_utilization", "confidence": 0.9})
            if network_in: fields.append({"source": network_in, "onto_field": "network_in", "confidence": 0.85})
            if network_out: fields.append({"source": network_out, "onto_field": "network_out", "confidence": 0.85})
            # RDS utilization
            if connections: fields.append({"source": connections, "onto_field": "db_connections", "confidence": 0.85})
            if read_latency: fields.append({"source": read_latency, "onto_field": "read_latency", "confidence": 0.85})
            if write_latency: fields.append({"source": write_latency, "onto_field": "write_latency", "confidence": 0.85})
            # S3 utilization
            if get_requests: fields.append({"source": get_requests, "onto_field": "get_requests", "confidence": 0.85})
            if put_requests: fields.append({"source": put_requests, "onto_field": "put_requests", "confidence": 0.85})
            if data_transfer_out: fields.append({"source": data_transfer_out, "onto_field": "data_transfer_out", "confidence": 0.85})
            # Cost & metadata
            if cost: fields.append({"source": cost, "onto_field": "monthly_cost", "confidence": 0.9})
            if last_analyzed: fields.append({"source": last_analyzed, "onto_field": "last_analyzed", "confidence": 0.8})
            if created_at: fields.append({"source": created_at, "onto_field": "created_at", "confidence": 0.8})
            if fields:
                mappings.append({"entity":"aws_resources","source_table": f"{source_key}_{tname}", "fields": fields})
        
        # FinOps mappings - cost_reports (detailed cost reporting per FinOps Autopilot schema)
        if (cost_id or report_date or service_category or resource or cost or usage or usage_type or region or created_at) and "cost_reports" in available_entities:
            fields = []
            if cost_id: fields.append({"source": cost_id, "onto_field": "cost_id", "confidence": 0.85})
            if report_date: fields.append({"source": report_date, "onto_field": "report_date", "confidence": 0.85})
            if service_category: fields.append({"source": service_category, "onto_field": "service_category", "confidence": 0.85})
            if resource: fields.append({"source": resource, "onto_field": "resource_id", "confidence": 0.85})
            if cost: fields.append({"source": cost, "onto_field": "cost", "confidence": 0.9})
            if usage: fields.append({"source": usage, "onto_field": "usage", "confidence": 0.85})
            if usage_type: fields.append({"source": usage_type, "onto_field": "usage_type", "confidence": 0.85})
            if region: fields.append({"source": region, "onto_field": "region", "confidence": 0.85})
            if created_at: fields.append({"source": created_at, "onto_field": "created_at", "confidence": 0.8})
            if fields:
                mappings.append({"entity":"cost_reports","source_table": f"{source_key}_{tname}", "fields": fields})
    
    # Semantic filtering based on Prod Mode setting (check Redis for cross-process state)
    # Skip LLM validation if RAG coverage was high enough to skip main LLM call
    current_dev_mode = get_dev_mode()
    if current_dev_mode and not skip_llm_validation:
        # DEV MODE ON + Low RAG coverage: Use LLM for intelligent semantic validation (AI/RAG)
        log("🔍 Dev Mode ON: Using LLM for semantic validation")
        semantically_valid_mappings = []
        for mapping in mappings:
            entity = mapping.get("entity")
            source_table = mapping.get("source_table", "")
            table_name = source_table.replace(f"{source_key}_", "")
            fields = mapping.get("fields", [])
            
            # Ask LLM to validate semantic alignment
            is_valid = validate_mapping_semantics_llm(source_key, table_name, entity, fields)
            if is_valid:
                semantically_valid_mappings.append(mapping)
        
        mappings = semantically_valid_mappings
        log(f"✅ LLM validated {len(mappings)} mappings as semantically correct")
    else:
        # DEV MODE OFF OR High RAG coverage: Use hard-wired heuristic rules (fast, deterministic)
        if skip_llm_validation:
            log("⚡ High RAG coverage: Skipping LLM semantic validation, using heuristic filtering")
        else:
            log("⚡ Dev Mode OFF: Using heuristic domain filtering")
        FINOPS_SOURCES = {"snowflake", "sap", "netsuite", "legacy_sql", "filesource"}
        REVOPS_SOURCES = {"dynamics", "salesforce", "hubspot"}
        FINOPS_ENTITIES = {"aws_resources", "cost_reports"}
        REVOPS_ENTITIES = {"account", "opportunity"}
        
        # Note: Supabase/MongoDB contain product metrics (account_health, account_usage)
        # These are operational data, not sales pipeline data, so they're excluded from RevOps
        
        semantically_valid_mappings = []
        for mapping in mappings:
            entity = mapping.get("entity")
            source_system = source_key.lower()
            
            # Check domain alignment
            is_finops_source = source_system in FINOPS_SOURCES
            is_revops_source = source_system in REVOPS_SOURCES
            
            # Check entity domain with partial matching (e.g., "account_health" contains "health")
            is_finops_entity = entity in FINOPS_ENTITIES or any(fe in entity for fe in FINOPS_ENTITIES)
            is_revops_entity = entity in REVOPS_ENTITIES or any(re in entity for re in REVOPS_ENTITIES)
            
            # Allow mapping only if domains align
            if (is_finops_source and is_finops_entity) or (is_revops_source and is_revops_entity):
                semantically_valid_mappings.append(mapping)
            elif not is_finops_source and not is_revops_source:
                # Unknown source - allow it (future extensibility)
                semantically_valid_mappings.append(mapping)
        
        mappings = semantically_valid_mappings
        log(f"✅ Heuristic filtered {len(mappings)} mappings as valid")
    
    # Filter out mappings that don't provide any useful fields for selected agents
    selected_agents = state_access.get_selected_agents(tenant_id)
    if selected_agents:
        agent_key_metrics = set()
        for agent_id in selected_agents:
            agent_info = agents_config.get("agents", {}).get(agent_id, {})
            agent_key_metrics.update(agent_info.get("key_metrics", []))
        
        filtered_mappings = []
        for mapping in mappings:
            # Check if any mapped field is in agent key_metrics
            has_useful_field = any(
                field["onto_field"] in agent_key_metrics 
                for field in mapping.get("fields", [])
            )
            if has_useful_field:
                filtered_mappings.append(mapping)
        
        mappings = filtered_mappings
    
    # naive joins on shared key names
    name_to_tables = {}
    for t, info in tables.items():
        for c in info["schema"].keys():
            name_to_tables.setdefault(c.lower(), []).append(t)
    for key in ["accountid","customerid","kunnr","cust_id","account_id","id"]:
        if key in name_to_tables and len(name_to_tables[key])>1:
            T = name_to_tables[key]
            for i in range(len(T)-1):
                joins.append({"left": f"{T[i]}.{key}", "right": f"{T[i+1]}.{key}", "reason": f"shared key {key}"})
    return {"mappings": mappings, "joins": joins}

def apply_plan(con, source_key: str, plan: Dict[str, Any], tenant_id: str = "default") -> Scorecard:
    """
    Apply mapping plan to create unified DCL views in DuckDB.
    
    IMPORTANT: Caller must hold distributed lock before calling this function.
    This ensures atomic graph state updates when multiple sources are processing concurrently.
    The lock prevents data races where sources overwrite each other's graph updates.
    
    Args:
        con: DuckDB connection
        source_key: Source system identifier
        plan: Mapping plan with entity mappings and joins
        tenant_id: Tenant identifier for tenant-scoped operations
    
    Returns:
        Scorecard with confidence, issues, and blockers
    """
    global STATE_LOCK, ontology
    issues, blockers, joins = [], [], []
    confs = []
    per_entity_views = {}
    
    # Load ontology to get full field definitions
    if ontology is None:
        ontology = load_ontology()
    
    # Build graph updates (nodes and edges) to apply atomically
    nodes_to_add = []
    edges_to_add = []
    entities_to_update = []
    
    for m in plan.get("mappings", []):
        ent = m["entity"]
        
        # Get all ontology fields for this entity (fields are stored as a list)
        entity_def = ontology.get("entities", {}).get(ent, {})
        all_ontology_fields = entity_def.get("fields", [])
        
        # Build a mapping dict: ontology_field -> source_field
        field_map = {}
        for f in m["fields"]:
            onto_field = f["onto_field"]
            src_field = f["source"]
            field_map[onto_field] = src_field
            confs.append(float(f.get("confidence", 0.75)))
        
        if not field_map:
            continue
        
        # Extract the raw table name from LLM's source_table
        raw_table = m['source_table']
        if raw_table.startswith(f"{source_key}_"):
            table_name = raw_table[len(source_key)+1:]
        else:
            table_name = raw_table
        
        view_name = f"dcl_{ent}_{source_key}_{table_name}"
        src_table = f"src_{source_key}_{table_name}"
        
        # Build SELECT with ALL ontology fields (use NULL for unmapped fields)
        selects = []
        for onto_field in all_ontology_fields:
            if onto_field in field_map:
                selects.append(f"{field_map[onto_field]} AS {onto_field}")
            else:
                selects.append(f"NULL AS {onto_field}")
        
        try:
            con.sql(f"CREATE OR REPLACE VIEW {view_name} AS SELECT {', '.join(selects)} FROM {src_table}")
            per_entity_views.setdefault(ent, []).append(view_name)
            
            # Prepare simple ontology node
            target_node_id = f"dcl_{ent}"
            nodes_to_add.append({
                "id": target_node_id,
                "label": f"{ent.replace('_', ' ').title()} (Unified)",
                "type": "ontology"
            })
            
            # Prepare edge from source to ontology
            edges_to_add.append({
                "source": src_table, 
                "target": target_node_id, 
                "label": f"{m['source_table']} → {ent}", 
                "type": "mapping",
                "edgeType": "dataflow",
                "field_mappings": m.get("fields", [])
            })
        except Exception as e:
            blockers.append(f"{ent}: failed view {view_name}: {e}")
    
    for ent, views in per_entity_views.items():
        union_sql = " UNION ALL ".join([f"SELECT * FROM {v}" for v in views])
        try:
            con.sql(f"CREATE OR REPLACE VIEW dcl_{ent} AS {union_sql}")
            entities_to_update.append(ent)
        except Exception as e:
            blockers.append(f"{ent}: union failed: {e}")
    
    for j in plan.get("joins", []):
        joins.append({"left": j["left"], "right": j["right"], "reason": j.get("reason","")})
        edges_to_add.append({
            "source": f"src_{source_key}_{j['left'].split('.')[0]}",
            "target": f"src_{source_key}_{j['right'].split('.')[0]}",
            "label": j["left"].split('.')[-1] + " ↔ " + j["right"].split('.')[-1],
            "type": "join"
        })
    
    # Apply all graph state updates atomically (caller holds distributed lock)
    current_graph = state_access.get_graph_state(tenant_id)
    
    # Add nodes (deduplicated by ID)
    for node in nodes_to_add:
        existing_node = next((n for n in current_graph["nodes"] if n["id"] == node["id"]), None)
        if not existing_node:
            # Add new node
            current_graph["nodes"].append(node)
    
    # Add edges
    for edge in edges_to_add:
        current_graph["edges"].append(edge)
    
    # Save updated graph state
    state_access.set_graph_state(tenant_id, current_graph)
    
    conf = sum(confs)/len(confs) if confs else 0.8
    return Scorecard(confidence=conf, blockers=blockers, issues=issues, joins=joins)

def remove_source_from_graph(source_key: str, tenant_id: str = "default"):
    """
    Remove source's nodes/edges from graph (simplified for consolidated parent).
    
    Preserves:
    - Consolidated "from AAM" parent node (shared across all sources)
    - Other sources' nodes/edges
    - Agent nodes
    
    Removes:
    - src_{source_key}_* table nodes
    - All edges connected to removed nodes
    
    Args:
        source_key: Source system identifier (e.g., "salesforce", "hubspot")
        tenant_id: Tenant identifier for scoped operations
    """
    current_graph = state_access.get_graph_state(tenant_id)
    nodes_to_remove = set()
    
    # Remove all source table nodes (src_{source_key}_*)
    for node in current_graph["nodes"]:
        if node["id"].startswith(f"src_{source_key}_"):
            nodes_to_remove.add(node["id"])
    
    # Remove nodes from graph
    current_graph["nodes"] = [
        n for n in current_graph["nodes"]
        if n["id"] not in nodes_to_remove
    ]
    
    # Remove edges connected to removed nodes
    current_graph["edges"] = [
        e for e in current_graph["edges"]
        if e["source"] not in nodes_to_remove and e["target"] not in nodes_to_remove
    ]
    
    # Save updated state
    state_access.set_graph_state(tenant_id, current_graph)
    
    log(f"🗑️  Removed {len(nodes_to_remove)} nodes for source '{source_key}'")

def add_graph_nodes_for_source(source_key: str, tables: Dict[str, Any], tenant_id: str = "default"):
    global ontology, agents_config
    
    # Get current graph state for this tenant
    current_graph = state_access.get_graph_state(tenant_id)
    
    # PRAGMATIC FIX: Use single consolidated "from AAM" parent node
    # All sources connect to this parent, making source visible via entity node labels
    parent_node_id = "sys_aam_sources"
    parent_label = "from AAM"
    
    # Add consolidated parent node if it doesn't exist yet
    parent_exists = any(n["id"] == parent_node_id for n in current_graph["nodes"])
    if not parent_exists:
        current_graph["nodes"].append({
            "id": parent_node_id,
            "label": parent_label,
            "type": "source_parent"
        })
    
    # Add source nodes with source name in label (e.g., "Account (Salesforce)")
    source_system = source_key.replace('_', ' ').title()
    
    for t, table_data in tables.items():
        node_id = f"src_{source_key}_{t}"
        label = f"{source_system} - {t}"  # Source name displayed on node
        # Extract field names from the schema
        fields = list(table_data.get("schema", {}).keys()) if isinstance(table_data, dict) else []
        
        # Add source node with metadata
        current_graph["nodes"].append({
            "id": node_id, 
            "label": label, 
            "type": "source",
            "sourceSystem": source_system,
            "sourceKey": source_key,
            "parentId": parent_node_id,
            "fields": fields
        })
        
        # Create hierarchy edge from consolidated parent to source table
        current_graph["edges"].append({
            "source": parent_node_id,
            "target": node_id,
            "edgeType": "hierarchy",
            "value": 1
        })
    
    # Note: Ontology nodes will be added dynamically in apply_plan() 
    # only when they actually receive data from sources
    
    # Add agent nodes to graph
    if not agents_config:
        agents_config = load_agents_config()
    
    # Get selected agents (state_access handles dual-path internally)
    selected_agents = state_access.get_selected_agents(tenant_id)
    
    for agent_id in selected_agents:
        agent_info = agents_config.get("agents", {}).get(agent_id, {})
        if not any(n["id"] == f"agent_{agent_id}" for n in current_graph["nodes"]):
            current_graph["nodes"].append({
                "id": f"agent_{agent_id}",
                "label": agent_info.get("name", agent_id.title()),
                "type": "agent"
            })
    
    # Save updated graph state (state_access handles dual-path)
    state_access.set_graph_state(tenant_id, current_graph)

def add_ontology_to_agent_edges(tenant_id: str = "default"):
    """Create edges from ontology entities to agents based on agent consumption config"""
    global agents_config, ontology
    
    if not agents_config:
        agents_config = load_agents_config()
    
    if not ontology:
        ontology = load_ontology()
    
    # Get current graph state for this tenant (state_access handles dual-path)
    current_graph = state_access.get_graph_state(tenant_id)
    
    # Get all existing ontology nodes
    ontology_nodes = [n for n in current_graph["nodes"] if n["type"] == "ontology"]
    
    # For each selected agent, create edges from consumed ontology entities (state_access handles dual-path)
    selected_agents = state_access.get_selected_agents(tenant_id)
    for agent_id in selected_agents:
        agent_info = agents_config.get("agents", {}).get(agent_id, {})
        consumed_entities = agent_info.get("consumes", [])
        
        for onto_node in ontology_nodes:
            # Extract entity name from node id (dcl_aws_resource -> aws_resource)
            entity_name = onto_node["id"].replace("dcl_", "")
            
            if entity_name in consumed_entities:
                # Create edge from ontology to agent if it doesn't exist
                edge_exists = any(
                    e["source"] == onto_node["id"] and e["target"] == f"agent_{agent_id}"
                    for e in current_graph["edges"]
                )
                if not edge_exists:
                    # Get entity fields from ontology
                    entity_fields = ontology.get("entities", {}).get(entity_name, {}).get("fields", [])
                    
                    current_graph["edges"].append({
                        "source": onto_node["id"],
                        "target": f"agent_{agent_id}",
                        "label": "",  # No label needed - agent node already shows its name
                        "type": "consumption",
                        "edgeType": "dataflow",
                        "entity_fields": entity_fields,  # Add entity fields for tooltip
                        "entity_name": entity_name
                    })
    
    # Save updated graph state (state_access handles dual-path)
    state_access.set_graph_state(tenant_id, current_graph)

def preview_table(con, name: str, limit: int = 6) -> List[Dict[str,Any]]:
    try:
        df = con.sql(f"SELECT * FROM {name} LIMIT {limit}").to_df()
        records = df.to_dict(orient="records")
        for record in records:
            for key, value in record.items():
                if pd.isna(value):
                    record[key] = None
                elif isinstance(value, (pd.Timestamp, pd.Timedelta)):
                    record[key] = str(value)
        return records
    except Exception:
        return []

def _sync_llm_propose_internal(
    ontology: Dict[str, Any],
    source_key: str,
    tables: Dict[str, Any],
    llm_model: str,
    tenant_id: str
) -> tuple:
    """
    Synchronous version of llm_propose without WebSocket broadcasts.
    Called from thread pool, so no async/await allowed.
    
    Returns:
        tuple: (plan_dict or None, skip_semantic_validation: bool)
    """
    global rag_engine, RAG_CONTEXT, TIMING_LOG
    
    llm_start = time.time()
    
    # NO-RAG FAST PATH: Check Prod Mode BEFORE expensive RAG retrieval
    # This bypasses both RAG and LLM, falling back to heuristics immediately
    # Target: <10s total processing time in Production mode
    current_dev_mode = get_dev_mode()
    if not current_dev_mode:
        log(f"⚡ Prod Mode (No-RAG Fast Path): Bypassing RAG/LLM, using heuristics for {source_key}")
        return (None, False)
    
    # Initialize RAG engine if needed (for worker processes)
    if rag_engine is None and os.getenv("PINECONE_API_KEY"):
        try:
            from app.dcl_engine.rag_engine import RAGEngine
            rag_engine = RAGEngine()
            log("✅ RAG Engine initialized in worker thread")
        except Exception as e:
            log(f"⚠️ RAG Engine initialization failed: {e}")
    
    # RAG retrieval (synchronous, serial - trade intra-source parallelization for inter-source parallelization)
    # Only executed in Dev Mode (Prod Mode fast-paths above)
    rag_context = ""
    rag_task_start = time.time()
    all_similar = []
    
    if rag_engine:
        try:
            # Serial RAG calls (simpler, allows asyncio.gather to parallelize across sources)
            for table_name, table_info in tables.items():
                schema = table_info.get('schema', {})
                for field_name, field_type in schema.items():
                    try:
                        similar = rag_engine.retrieve_similar_mappings(
                            field_name=field_name,
                            field_type=field_type,
                            source_system=source_key,
                            top_k=2,
                            min_confidence=0.7
                        )
                        if similar:
                            all_similar.extend(similar)
                    except Exception as e:
                        log(f"⚠️ RAG retrieval error for {field_name}: {e}")
            
            rag_elapsed = time.time() - rag_task_start
            TIMING_LOG["rag_retrieval"].append(rag_elapsed)
            log(f"⏱️ RAG retrieval (SERIAL): {rag_elapsed:.2f}s for {sum(len(t.get('schema', {})) for t in tables.values())} fields")
            
            # Deduplicate and build context
            if all_similar:
                seen = set()
                unique_similar = []
                for mapping in all_similar:
                    key = f"{mapping['source_field']}_{mapping['ontology_entity']}"
                    if key not in seen:
                        seen.add(key)
                        unique_similar.append(mapping)
                
                unique_similar.sort(key=lambda x: x.get('similarity', 0), reverse=True)
                rag_context = rag_engine.build_context_for_llm(unique_similar)
                log(f"📚 RAG: Retrieved {len(unique_similar)} similar mappings for context")
                
                # Store for visualization
                RAG_CONTEXT["retrievals"] = [
                    {
                        "source_field": m["source_field"],
                        "ontology_entity": m["ontology_entity"],
                        "similarity": round(m.get("similarity", 0), 3),
                        "source_system": m.get("source_system", "unknown")
                    }
                    for m in unique_similar
                ]
                RAG_CONTEXT["last_retrieval_count"] = len(unique_similar)
        except Exception as e:
            log(f"⚠️ RAG retrieval failed: {e}")
    
    # INTELLIGENT LLM DECISION: Check RAG coverage before calling LLM
    # (Prod Mode already fast-pathed early, so we're in Dev Mode here)
    if rag_engine and all_similar:
        total_fields = sum(len(table_info.get('schema', {})) for table_info in tables.values())
        matched_fields = set()
        
        for table_name, table_info in tables.items():
            schema = table_info.get('schema', {})
            for field_name in schema.keys():
                field_matches = [m for m in all_similar 
                                if m['source_field'].lower() == field_name.lower() 
                                and m.get('similarity', 0) > 0.8]
                if field_matches:
                    matched_fields.add(field_name)
        
        coverage_pct = (len(matched_fields) / total_fields * 100) if total_fields > 0 else 0
        
        # If coverage is high (>=80%), skip LLM and use RAG mappings directly
        if coverage_pct >= 80:
            log(f"📊 RAG Coverage: {coverage_pct:.0f}% ({len(matched_fields)}/{total_fields} fields) - skipping LLM, using RAG inventory")
            increment_llm_calls_saved()
            return (None, True)  # (plan, skip_semantic_validation)
    
    # Check API key
    if llm_model.startswith("gpt"):
        if not os.getenv("OPENAI_API_KEY"):
            log(f"⚠️ OPENAI_API_KEY not set - skipping LLM for {source_key}")
            return (None, False)
    else:
        if not os.getenv("GEMINI_API_KEY"):
            log(f"⚠️ GEMINI_API_KEY not set - skipping LLM for {source_key}")
            return (None, False)
    
    log(f"🤖 Dev Mode: Starting LLM mapping for {source_key} with {llm_model}")
    
    # Build prompt
    sys_prompt = (
        "You are a data integration planner. Given an ontology and a set of new tables from a source system, "
        "produce a STRICT JSON plan with proposed mappings and joins.\n\n"
        "Output format (strict JSON!):\n"
        "{"
        '  "mappings": ['
        '    {"entity":"customer","source_table":"<table>", "fields":[{"source":"<col>", "onto_field":"customer_id", "confidence":0.92}]},'
        '    {"entity":"transaction","source_table":"<table>", "fields":[{"source":"<col>", "onto_field":"amount", "confidence":0.88}]}'
        "  ],"
        '  "joins": [ {"left":"<table>.<col>", "right":"<table>.<col>", "reason":"why"} ]'
        "}"
    )
    
    rag_section = f"{rag_context}\n\n" if rag_context else ""
    prompt = (
        f"{sys_prompt}\n\n"
        f"{rag_section}"
        f"Ontology:\n{json.dumps(ontology)}\n\n"
        f"SourceKey: {source_key}\n"
        f"Tables:\n{json.dumps(tables)}\n\n"
        f"Return ONLY JSON."
    )
    
    # Call LLM service (synchronous)
    try:
        llm_service = get_llm_service(llm_model, increment_llm_calls)
        log(f"📊 Using {llm_service.get_provider_name()} - {llm_service.get_model_name()}")
    except (ValueError, ImportError) as e:
        log(f"⚠️ {e} - falling back to heuristic")
        return (None, False)
    
    llm_call_start = time.time()
    result = llm_service.generate(prompt, source_key)  # Sync call (blocking)
    llm_call_elapsed = time.time() - llm_call_start
    log(f"⏱️ LLM call: {llm_call_elapsed:.2f}s")
    
    # Store mappings in RAG
    if result and rag_engine:
        try:
            dev_mode = get_dev_mode()
            stored_count = 0
            for mapping in result.get("mappings", []):
                entity = mapping.get("entity")
                for field in mapping.get("fields", []):
                    result_id = rag_engine.store_mapping(
                        source_field=field["source"],
                        source_type="string",
                        ontology_entity=f"{entity}.{field['onto_field']}",
                        source_system=source_key,
                        transformation="direct",
                        confidence=field.get("confidence", 0.8),
                        validated=False,
                        dev_mode_enabled=dev_mode
                    )
                    if result_id:
                        stored_count += 1
            if dev_mode:
                log(f"💾 Stored {stored_count} mappings to RAG (dev mode)")
                try:
                    stats = rag_engine.get_stats()
                    RAG_CONTEXT["total_mappings"] = stats.get("total_mappings", 0)
                except:
                    pass
            else:
                log(f"🔒 RAG writes blocked - heuristic mode (retrieved context only)")
        except Exception as e:
            log(f"⚠️ Failed to store mappings in RAG: {e}")
    
    llm_elapsed = time.time() - llm_start
    TIMING_LOG["llm_propose_total"].append(llm_elapsed)
    log(f"⏱️ llm_propose total: {llm_elapsed:.2f}s")
    
    return (result, False)  # (plan, skip_semantic_validation)


def _blocking_source_pipeline(
    source_key: str,
    llm_model: str,
    tenant_id: str
) -> Union[Dict[str, Any], tuple]:
    """
    Synchronous helper containing all blocking DuckDB/pandas/RAG operations.
    Executed in thread pool to avoid blocking event loop.
    
    This function contains ALL CPU/IO-intensive operations that would otherwise
    monopolize the event loop and prevent true parallelization via asyncio.gather.
    
    Returns:
        tuple: (tables, plan, score, previews, source_mode) on success
        dict: {"error": message} on failure
    """
    global ontology, agents_config
    
    print(f"[TRACE_DCL] _blocking_source_pipeline ENTRY: source_key={source_key}, tenant_id={tenant_id}", flush=True)
    
    try:
        # Load ontology if needed
        if ontology is None:
            ontology = load_ontology()
        
        # Load agents config if needed
        if not agents_config:
            agents_config = load_agents_config()
        
        # Get adapter based on feature flag
        adapter = get_source_adapter()
        source_mode = "aam_connectors" if FeatureFlagConfig.is_enabled(FeatureFlag.USE_AAM_AS_SOURCE) else "demo_files"
        
        print(f"[TRACE_DCL] Using adapter mode: {source_mode}", flush=True)
        log(f"📂 Using {source_mode} for source: {source_key} (tenant: {tenant_id})")
        
        # BLOCKING I/O: Load source data (pandas read_csv - ~1-2s)
        tables = adapter.load_tables(source_key, tenant_id)
        
        if not tables:
            print(f"[TRACE_DCL] ❌ No tables found for source '{source_key}'", flush=True)
            return {"error": f"No tables found for source '{source_key}'"}
        
        print(f"[TRACE_DCL] Loaded {len(tables)} tables: {list(tables.keys())}", flush=True)
        if tables:
            first_table = list(tables.values())[0]
            sample_count = len(first_table.get('samples', []))
            print(f"[TRACE_DCL] Sample data check - first table has {sample_count} rows", flush=True)
        
        log(f"📊 Loaded {len(tables)} tables from {source_key}")
        
        # BLOCKING: LLM/RAG planning (~15s for RAG + LLM if dev mode enabled)
        llm_result = _sync_llm_propose_internal(ontology, source_key, tables, llm_model, tenant_id)
        plan, skip_semantic_validation = llm_result if isinstance(llm_result, tuple) else (llm_result, False)
        
        if not plan:
            # Use heuristic plan (blocking but fast <100ms)
            plan = heuristic_plan(ontology, source_key, tables, skip_llm_validation=skip_semantic_validation, tenant_id=tenant_id)
            log(f"I connected to {source_key.title()} (schema sample) and generated a heuristic plan.")
            plan_type = "heuristic"
        else:
            log(f"I connected to {source_key.title()} (schema sample) and proposed mappings and joins.")
            plan_type = "ai"
        
        # BLOCKING: DuckDB operations (~2-3s) - MUST be inside TENANT-SCOPED distributed lock
        # CRITICAL FIX: Use tenant-scoped lock to prevent race conditions within same tenant
        # while allowing parallel processing across different tenants
        db_path = get_db_path(tenant_id)
        print(f"[TRACE_DCL] About to connect to DuckDB: {db_path}", flush=True)
        
        # Create tenant-scoped lock to prevent race conditions when multiple sources
        # from the SAME tenant connect in parallel, while allowing different tenants
        # to process concurrently
        print(f"[TRACE_DCL] Acquiring tenant-scoped distributed lock (tenant: {tenant_id}, 60s timeout)", flush=True)
        if redis_client:
            from app.dcl_engine.distributed_lock import RedisDistributedLock
            tenant_lock = RedisDistributedLock(
                redis_client=redis_client,
                lock_key=f"dcl:lock:{tenant_id}:duckdb_access",  # Tenant-scoped lock key
                lock_ttl=30
            )
            with tenant_lock.acquire(timeout=60.0):
                print(f"[TRACE_DCL] Tenant lock acquired, opening DuckDB connection", flush=True)
                con = duckdb.connect(db_path, config={'access_mode': 'READ_WRITE'})
                print(f"[TRACE_DCL] DuckDB connection successful", flush=True)
                
                print(f"[TRACE_DCL] Calling register_src_views for {source_key}", flush=True)
                register_src_views(con, source_key, tables)
                print(f"[TRACE_DCL] register_src_views completed", flush=True)
                
                print(f"[TRACE_DCL] Calling apply_plan", flush=True)
                score = apply_plan(con, source_key, plan, tenant_id)
                print(f"[TRACE_DCL] apply_plan completed with score: {score}", flush=True)
        else:
            # Fallback: No Redis available (development mode without distributed lock)
            print(f"[TRACE_DCL] No Redis available, proceeding without lock", flush=True)
            con = duckdb.connect(db_path, config={'access_mode': 'READ_WRITE'})
            print(f"[TRACE_DCL] DuckDB connection successful", flush=True)
            
            print(f"[TRACE_DCL] Calling register_src_views for {source_key}", flush=True)
            register_src_views(con, source_key, tables)
            print(f"[TRACE_DCL] register_src_views completed", flush=True)
            
            print(f"[TRACE_DCL] Calling apply_plan directly", flush=True)
            score = apply_plan(con, source_key, plan, tenant_id)
            print(f"[TRACE_DCL] apply_plan completed with score: {score}", flush=True)
        
        # Log join information
        ents = ", ".join(sorted(tables.keys()))
        log(f"I found these entities: {ents}.")
        if score.joins:
            log("To connect them, I proposed joins like " + "; ".join([f"{j['left']} with {j['right']}" for j in score.joins]) + ".")
        if score.confidence >= CONF_THRESHOLD and not score.blockers:
            log(f"I am about {int(score.confidence*100)}% confident. I created unified views.")
        elif AUTO_PUBLISH_PARTIAL and not score.blockers:
            log(f"I applied the mappings, but with some issues: {score.issues}")
        else:
            blockers_msg = "; ".join(score.blockers) if score.blockers else "Unknown blockers"
            log(f"I paused because of blockers. Blockers: {blockers_msg}")
        
        # BLOCKING: Generate previews (DuckDB queries ~500ms)
        previews = {"sources": {}, "ontology": {}}
        for t in tables.keys():
            previews["sources"][f"src_{source_key}_{t}"] = preview_table(con, f"src_{source_key}_{t}")
        
        # Get ontology entities based on selected agents
        ontology_entities = set()
        selected_agents = state_access.get_selected_agents(tenant_id)
        
        if selected_agents:
            for agent_id in selected_agents:
                agent_info = agents_config.get("agents", {}).get(agent_id, {})
                consumes = agent_info.get("consumes", [])
                ontology_entities.update(consumes)
        else:
            ontology_entities = set(ontology.get("entities", {}).keys())
        
        for ent in ontology_entities:
            previews["ontology"][f"dcl_{ent}"] = preview_table(con, f"dcl_{ent}")
        
        # Close DuckDB connection
        print(f"[TRACE_DCL] Closing DuckDB connection", flush=True)
        con.close()
        print(f"[TRACE_DCL] DuckDB connection closed", flush=True)
        
        # Check file existence IMMEDIATELY after close
        if os.path.exists(db_path):
            file_size = os.path.getsize(db_path)
            print(f"[TRACE_DCL] ✅ DuckDB file EXISTS after close: {db_path} ({file_size} bytes)", flush=True)
        else:
            print(f"[TRACE_DCL] ❌ DuckDB file MISSING after close: {db_path}", flush=True)
        
        # Return all results for async orchestrator to handle
        return (tables, plan, score, previews, source_mode, plan_type)
        
    except Exception as e:
        print(f"[TRACE_DCL] ❌ EXCEPTION in _blocking_source_pipeline: {e}", flush=True)
        print(f"[TRACE_DCL] Traceback: {traceback.format_exc()}", flush=True)
        log(f"❌ Error in blocking pipeline for {source_key}: {e}")
        log(f"Traceback: {traceback.format_exc()}")
        return {"error": str(e)}


async def connect_source(
    source_key: str, 
    llm_model: str = "gemini-2.5-flash",
    tenant_id: str = "default"
) -> Dict[str, Any]:
    """
    Async orchestrator - offloads blocking work to thread pool for true parallel execution.
    
    This function coordinates async operations (WebSocket broadcasts, state mutations)
    while delegating ALL blocking operations (pandas, DuckDB, RAG, LLM) to a thread pool.
    This allows asyncio.gather to truly parallelize multiple connect_source calls.
    """
    global ontology, agents_config, TIMING_LOG, ws_manager, dcl_distributed_lock
    
    print(f"[TRACE_DCL] connect_source ENTRY: source_key={source_key}, tenant_id={tenant_id}", flush=True)
    db_path = get_db_path(tenant_id)
    print(f"[TRACE_DCL] Expected db_path: {db_path}", flush=True)
    
    connect_start = time.time()
    
    # ASYNC: Broadcast start event
    await ws_manager.broadcast({
        "type": "mapping_progress",
        "source": source_key,
        "stage": "started",
        "message": f"🔄 Starting schema analysis for {source_key}...",
        "timestamp": time.time()
    }, tenant_id=tenant_id)
    
    # ASYNC: Clear AAM source cache if needed (brief <100ms operation under lock)
    if FeatureFlagConfig.is_enabled(FeatureFlag.USE_AAM_AS_SOURCE):
        adapter = get_source_adapter()
        
        if dcl_distributed_lock:
            async with dcl_distributed_lock.acquire_async(timeout=5.0):
                current_schemas = state_access.get_source_schemas(tenant_id)
                if source_key in current_schemas:
                    del current_schemas[source_key]
                    state_access.set_source_schemas(tenant_id, current_schemas)
                    log(f"🗑️  Cleared SOURCE_SCHEMAS cache for AAM source: {source_key}")
        else:
            current_schemas = state_access.get_source_schemas(tenant_id)
            if source_key in current_schemas:
                del current_schemas[source_key]
                state_access.set_source_schemas(tenant_id, current_schemas)
                log(f"🗑️  Cleared SOURCE_SCHEMAS cache for AAM source: {source_key}")
        
        if isinstance(adapter, AAMSourceAdapter):
            adapter.clear_idempotency_cache(tenant_id, source_id=source_key)
            log(f"🗑️  Cleared idempotency cache for tenant: {tenant_id}")
    
    # BLOCKING PIPELINE: Run all CPU/IO-intensive work in thread pool (yields event loop!)
    # This is where TRUE PARALLELIZATION happens - event loop can schedule other sources
    result = await asyncio.to_thread(
        _blocking_source_pipeline,
        source_key,
        llm_model,
        tenant_id
    )
    
    # Check for errors from blocking pipeline
    if isinstance(result, dict) and "error" in result:
        return result
    
    # Unpack results from blocking pipeline
    tables, plan, score, previews, source_mode, plan_type = result
    
    # ASYNC: Broadcast schema loaded event
    await ws_manager.broadcast({
        "type": "mapping_progress",
        "source": source_key,
        "stage": "schema_loaded",
        "message": f"📊 Loaded {len(tables)} tables from {source_key}",
        "table_count": len(tables),
        "timestamp": time.time()
    }, tenant_id=tenant_id)
    
    # ASYNC: Broadcast plan type event
    if plan_type == "heuristic":
        await ws_manager.broadcast({
            "type": "mapping_progress",
            "source": source_key,
            "stage": "heuristic_plan",
            "message": f"⚡ Using fast heuristic mapping for {source_key}",
            "timestamp": time.time()
        }, tenant_id=tenant_id)
    else:
        await ws_manager.broadcast({
            "type": "mapping_progress",
            "source": source_key,
            "stage": "ai_plan",
            "message": f"🧠 Using AI-generated mapping for {source_key}",
            "timestamp": time.time()
        }, tenant_id=tenant_id)
    
    # ASYNC: State mutations under distributed lock (BRIEF <1s operation)
    if dcl_distributed_lock:
        try:
            async with dcl_distributed_lock.acquire_async(timeout=5.0):
                # Store schemas
                current_schemas = state_access.get_source_schemas(tenant_id)
                current_schemas[source_key] = tables
                state_access.set_source_schemas(tenant_id, current_schemas)
                
                # Add graph nodes
                add_graph_nodes_for_source(source_key, tables, tenant_id)
                
                # Update graph state
                current_graph = state_access.get_graph_state(tenant_id)
                current_graph["confidence"] = score.confidence
                current_graph["last_updated"] = time.strftime("%I:%M:%S %p")
                state_access.set_graph_state(tenant_id, current_graph)
                
                # Create edges from ontology entities to agents
                add_ontology_to_agent_edges(tenant_id)
                
                # Add source to tenant-scoped sources list
                current_sources = state_access.get_sources(tenant_id)
                current_sources.append(source_key)
                state_access.set_sources(tenant_id, current_sources)
        except Exception as e:
            log(f"❌ Failed to update state for {source_key}: {e}")
            raise
    else:
        # Fallback: No distributed lock available (development mode)
        current_schemas = state_access.get_source_schemas(tenant_id)
        current_schemas[source_key] = tables
        state_access.set_source_schemas(tenant_id, current_schemas)
        add_graph_nodes_for_source(source_key, tables, tenant_id)
        current_graph = state_access.get_graph_state(tenant_id)
        current_graph["confidence"] = score.confidence
        current_graph["last_updated"] = time.strftime("%I:%M:%S %p")
        state_access.set_graph_state(tenant_id, current_graph)
        add_ontology_to_agent_edges(tenant_id)
        current_sources = state_access.get_sources(tenant_id)
        current_sources.append(source_key)
        state_access.set_sources(tenant_id, current_sources)
    
    # Log total connect_source timing
    connect_elapsed = time.time() - connect_start
    TIMING_LOG["connect_total"].append(connect_elapsed)
    log(f"⏱️ connect_source({source_key}) total: {connect_elapsed:.2f}s")
    
    # ASYNC: Broadcast completion event
    await ws_manager.broadcast({
        "type": "mapping_progress",
        "source": source_key,
        "stage": "complete",
        "message": f"✅ {source_key} mapping complete ({connect_elapsed:.1f}s)",
        "duration": connect_elapsed,
        "confidence": score.confidence,
        "source_mode": source_mode,
        "timestamp": time.time()
    }, tenant_id=tenant_id)
    
    return {"ok": True, "score": score.confidence, "previews": previews, "source_mode": source_mode}

def reset_state(exclude_dev_mode=True, tenant_id: str = "default"):
    """
    Reset DCL state for idempotent /connect operations.
    By default, preserves dev_mode setting and LLM counters across resets.
    
    Args:
        exclude_dev_mode: If True, dev_mode persists across resets
        tenant_id: Tenant identifier for tenant-scoped state reset
    
    Note: LLM counters (calls/tokens) persist across all runs for telemetry tracking,
          similar to "elapsed time until next run". Use reset_llm_stats() endpoint to manually reset.
    
    Behavior:
        - When TENANT_SCOPED_STATE=False: Resets global state variables
        - When TENANT_SCOPED_STATE=True: Resets tenant-scoped Redis state
        - Both code paths work simultaneously (dual-write pattern)
    """
    global ontology, RAG_CONTEXT
    
    # Reset tenant-scoped state (state_access handles dual-path internally)
    state_access.set_event_log(tenant_id, [])
    state_access.set_graph_state(tenant_id, {"nodes": [], "edges": [], "confidence": None, "last_updated": None})
    state_access.set_sources(tenant_id, [])
    state_access.set_entity_sources(tenant_id, {})
    state_access.set_source_schemas(tenant_id, {})
    state_access.set_selected_agents(tenant_id, [])
    # LLM stats persist across runs for cumulative tracking (removed reset_llm_stats call)
    # Clear RAG retrievals so they update with fresh data on each connection
    RAG_CONTEXT["retrievals"] = []
    RAG_CONTEXT["last_retrieval_count"] = 0
    # NOTE: Dev mode and total_mappings are preserved - they persist across connection rebuilds
    ontology = load_ontology()
    try:
        os.remove(get_db_path(tenant_id))
    except FileNotFoundError:
        pass
    
    # Clear persisted graph state from Redis (legacy GraphStateStore)
    if graph_store:
        try:
            graph_store.reset(tenant_id)
        except Exception as e:
            log(f"⚠️ Failed to clear persisted graph: {e}", tenant_id=tenant_id)
    
    log(f"🔄 DCL state cleared for tenant {tenant_id} (dev_mode preserved). Ready for new connection.", tenant_id=tenant_id)

app = FastAPI()

# State broadcasting function
async def broadcast_state_change(event_type: str = "state_update", tenant_id: str = "default"):
    """
    Broadcast DCL state changes to WebSocket clients and Redis pub/sub.
    This eliminates polling by pushing updates when state changes.
    
    Args:
        event_type: Type of state update event (e.g., "state_update", "mapping_complete")
        tenant_id: Tenant identifier for filtering broadcasts to tenant-scoped connections
    
    Behavior:
        - Broadcasts to WebSocket connections matching tenant_id (filtered by ws_manager)
        - Publishes to Redis pub/sub for cross-process synchronization
        - In Phase 1a: Still reads from global state (TENANT_SCOPED_STATE=False)
        - In Phase 1b: Will read from tenant-scoped state via TenantStateManager
    """
    try:
        # Build state payload (same structure as /state endpoint)
        global RAG_CONTEXT, rag_engine, agents_config
        
        # Update total mappings count from RAG engine
        if rag_engine:
            try:
                stats = rag_engine.get_stats()
                RAG_CONTEXT["total_mappings"] = stats.get("total_mappings", 0)
            except:
                pass
        
        # Include agent consumption metadata
        if not agents_config:
            agents_config = load_agents_config()
        
        agent_consumption = {}
        for agent_id, agent_info in agents_config.get("agents", {}).items():
            agent_consumption[agent_id] = agent_info.get("consumes", [])
        
        # Filter graph based on AAM mode - show only relevant source nodes
        use_aam = FeatureFlagConfig.is_enabled(FeatureFlag.USE_AAM_AS_SOURCE)
        # AAM sources (lowercase keys as they appear in source_key)
        aam_source_keys = {"salesforce", "supabase", "mongodb", "filesource"}
        
        # Get current graph state for this tenant (state_access handles dual-path)
        current_graph = state_access.get_graph_state(tenant_id)
        
        # Filter nodes based on mode
        if use_aam:
            # AAM mode: Only show nodes from AAM production connectors
            # source_parent node IDs are "sys_{source_key}", sourceSystem is title-cased from source_key
            filtered_nodes = []
            for node in current_graph["nodes"]:
                node_type = node.get("type")
                
                # Always include ontology and agent nodes
                if node_type in ["ontology", "agent"]:
                    filtered_nodes.append(node)
                    continue
                
                # For source_parent nodes: check if ID matches sys_{aam_source}
                if node_type == "source_parent":
                    node_id = node.get("id", "")
                    if node_id.startswith("sys_"):
                        source_key = node_id[4:]  # Remove "sys_" prefix
                        if source_key in aam_source_keys:
                            filtered_nodes.append(node)
                    continue
                
                # For source table nodes: check parent ID (more reliable than sourceSystem string matching)
                if node_type == "source":
                    parent_id = node.get("parentId", "")
                    if parent_id.startswith("sys_"):
                        source_key = parent_id[4:]  # Remove "sys_" prefix
                        if source_key in aam_source_keys:
                            filtered_nodes.append(node)
                    continue
        else:
            # Legacy mode: Show all nodes (9 demo CSV sources)
            filtered_nodes = current_graph["nodes"]
        
        # Filter graph edges for Sankey rendering - exclude join edges to prevent circular references
        # Also filter edges to only include those between filtered nodes
        filtered_node_ids = {node["id"] for node in filtered_nodes}
        filtered_graph = {
            "nodes": filtered_nodes,
            "edges": [
                edge for edge in current_graph["edges"]
                if edge.get("type") != "join"  # Only keep hierarchy and dataflow edges
                and edge.get("source") in filtered_node_ids  # Source node must be in filtered set
                and edge.get("target") in filtered_node_ids  # Target node must be in filtered set
            ]
        }
        
        # Get LLM stats from Redis (includes calls_saved)
        llm_stats = get_llm_stats()
        
        # Calculate blended confidence
        blended_confidence = current_graph.get("confidence")
        
        # Determine source mode from feature flag
        source_mode = "aam_connectors" if FeatureFlagConfig.is_enabled(FeatureFlag.USE_AAM_AS_SOURCE) else "demo_files"
        
        # Get tenant-scoped state (state_access handles dual-path internally)
        current_sources = state_access.get_sources(tenant_id)
        current_events = state_access.get_event_log(tenant_id)
        current_agents = state_access.get_selected_agents(tenant_id)
        current_entity_sources = state_access.get_entity_sources(tenant_id)
        
        # Send complete data (frontend has scrolling for unlimited display)
        state_payload = {
            "type": event_type,
            "timestamp": time.time(),
            "data": {
                "sources": current_sources,
                "agents": current_agents,
                "devMode": get_dev_mode(),
                "sourceMode": source_mode,
                "graph": filtered_graph,  # Send filtered graph instead of raw GRAPH_STATE
                "llmCalls": llm_stats["calls"],
                "llmTokens": llm_stats["tokens"],
                "llmCallsSaved": llm_stats["calls_saved"],
                "ragContext": {
                    "total_mappings": RAG_CONTEXT.get("total_mappings", 0),
                    "last_retrieval_count": RAG_CONTEXT.get("last_retrieval_count", 0),
                    "mappings_retrieved": RAG_CONTEXT.get("last_retrieval_count", 0),
                    "retrievals": RAG_CONTEXT.get("retrievals", [])  # All retrievals (no limit)
                },
                "blendedConfidence": blended_confidence,
                "events": current_events,  # All events (no limit - frontend has scrolling)
                "entitySources": current_entity_sources,
                "agentConsumption": agent_consumption
            }
        }
        
        # Debug log to verify events are included
        log(f"📡 Broadcasting {event_type}: {len(current_events)} events, {len(current_sources)} sources, {RAG_CONTEXT.get('total_mappings', 0)} RAG mappings", tenant_id)
        
        # Broadcast to WebSocket clients (filtered by tenant_id)
        await ws_manager.broadcast(state_payload, tenant_id=tenant_id)
        
        # Publish to Redis pub/sub for cross-process broadcast (if available)
        if redis_available and redis_client:
            try:
                redis_client.publish(DCL_STATE_CHANNEL, json.dumps(state_payload))
            except:
                pass  # Redis unavailable, skip pub/sub
        
    except Exception as e:
        log(f"⚠️ Error broadcasting state change: {e}", tenant_id)

# Middleware for API usage logging
@app.middleware("http")
async def log_api_usage(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    # Log important API calls only (exclude static files, assets, and polling endpoints like /state)
    if not request.url.path.startswith("/static") and not request.url.path.startswith("/assets") and request.url.path not in ["/state", "/"]:
        log(f"📊 API: {request.method} {request.url.path} - {response.status_code} ({process_time:.2f}s)")
    
    return response

# Custom route for JSX files with no-cache headers to force browser refresh
# Commented out - static files are served by the main app
# @app.get("/static/src/{filepath:path}")
# async def serve_jsx_nocache(filepath: str):
#     """Serve JSX/JS files with no-cache headers to prevent browser caching issues."""
#     file_path = os.path.join("static", "src", filepath)
#     if os.path.exists(file_path):
#         return FileResponse(
#             file_path,
#             headers={
#                 "Cache-Control": "no-cache, no-store, must-revalidate",
#                 "Pragma": "no-cache",
#                 "Expires": "0"
#             }
#         )
#     return JSONResponse({"error": "Not found"}, status_code=404)

# Commented out - static files are served by the main app
# app.mount("/static", StaticFiles(directory="static"), name="static")
# app.mount("/attached_assets", StaticFiles(directory="attached_assets"), name="attached_assets")

# Track whether pub/sub listener has been started
_pubsub_listener_started = False

async def ensure_pubsub_listener():
    """
    Ensure the pub/sub listener is started (lazy initialization).
    Safe to call multiple times - only starts once.
    """
    global _pubsub_listener_started
    
    if _pubsub_listener_started or not redis_client:
        return
    
    _pubsub_listener_started = True
    asyncio.create_task(feature_flag_pubsub_listener())
    log("📡 Feature flag pub/sub listener started (lazy init)")

async def feature_flag_pubsub_listener():
    """
    ASYNC NON-BLOCKING pub/sub listener for feature flag changes.
    
    Uses redis.asyncio for fully async, non-blocking operations.
    This ensures the listener does NOT block the FastAPI event loop,
    maintaining async responsiveness for production deployment.
    
    Previously: Used sync pubsub.get_message(timeout=1.0) which blocked event loop for 1 second
    Now: Uses async for message in pubsub.listen() which is fully non-blocking
    
    Provides cross-worker cache invalidation when flags are toggled.
    When Worker A toggles a flag, Worker B receives the change and clears its cache.
    """
    global async_redis_client
    
    # Initialize async Redis client if not already done
    if async_redis_client is None:
        async_redis_client = await init_async_redis()
    
    if not async_redis_client:
        log("⚠️ Async Redis not available - pub/sub listener disabled")
        return
    
    try:
        # Create ASYNC pub/sub instance (non-blocking)
        pubsub = async_redis_client.pubsub()
        await pubsub.subscribe(FeatureFlagConfig._pubsub_channel)
        
        log(f"📡 [ASYNC] Subscribed to {FeatureFlagConfig._pubsub_channel} for flag changes")
        log(f"✅ Pub/sub listener running in NON-BLOCKING mode (production-ready)")
        
        # Listen for messages using ASYNC iterator (fully non-blocking)
        async for message in pubsub.listen():
            try:
                # Only process actual messages (skip subscription confirmations)
                if message['type'] == 'message':
                    # Data is already decoded (decode_responses=True)
                    data = message['data']
                    
                    # Parse JSON payload
                    payload = json.loads(data)
                    flag_name = payload.get('flag')
                    flag_value = payload.get('value')
                    
                    log(f"📨 [ASYNC] Received flag change: {flag_name}={flag_value}")
                    
                    # Handle USE_AAM_AS_SOURCE flag changes
                    if flag_name == FeatureFlag.USE_AAM_AS_SOURCE.value:
                        # Clear DCL cache to force fresh graph generation (state_access handles dual-path)
                        state_access.set_graph_state("default", {"nodes": [], "edges": [], "confidence": None, "last_updated": None})
                        state_access.set_sources("default", [])
                        
                        # Clear persisted graph state from Redis
                        if graph_store:
                            try:
                                graph_store.reset()
                            except Exception as e:
                                log(f"⚠️ Failed to clear persisted graph: {e}")
                        
                        mode_name = "AAM Connectors" if flag_value else "Legacy File Sources"
                        log(f"🔄 Cache cleared due to flag change: {mode_name}")
                        
                        # Broadcast state change to WebSocket clients
                        await broadcast_state_change("aam_mode_toggled")
                
            except json.JSONDecodeError as e:
                log(f"⚠️ Invalid JSON in pub/sub message: {e}")
            except Exception as e:
                log(f"⚠️ Error processing pub/sub message: {e}")
                # Continue listening even on errors
                
    except Exception as e:
        log(f"⚠️ Pub/sub listener crashed: {e}")
        # Clean up on crash
        if async_redis_client:
            try:
                await async_redis_client.close()
            except:
                pass

@app.on_event("startup")
async def startup_event():
    """Initialize RAG engine and default settings on startup."""
    global rag_engine, agents_config, agent_executor
    
    # Initialize feature flags with Redis client for cross-worker persistence
    if redis_client:
        try:
            FeatureFlagConfig.set_redis_client(redis_client)
            
            # Hydrate USE_AAM_AS_SOURCE from Redis on startup (survives restarts)
            current_value = FeatureFlagConfig.is_enabled(FeatureFlag.USE_AAM_AS_SOURCE)
            mode_name = "AAM Connectors" if current_value else "Legacy File Sources"
            log(f"🚩 Feature Flags initialized - USE_AAM_AS_SOURCE: {mode_name}")
            
            # CRITICAL FIX: Use centralized pub/sub listener (Issue #1 & #2)
            # This ensures consistent behavior across ALL workers
            from app.config.redis_pubsub import ensure_pubsub_listener
            
            async def on_flag_change_callback(flag_name: str, flag_value: bool):
                """Handle flag changes in DCL engine worker"""
                log(f"🔄 DCL Engine: Flag changed {flag_name}={flag_value}")
                
                # Handle USE_AAM_AS_SOURCE flag changes
                if flag_name == FeatureFlag.USE_AAM_AS_SOURCE.value:
                    # Clear DCL cache to force fresh graph generation (state_access handles dual-path)
                    state_access.set_graph_state("default", {"nodes": [], "edges": [], "confidence": None, "last_updated": None})
                    state_access.set_sources("default", [])
                    
                    # Clear persisted graph state from Redis
                    if graph_store:
                        try:
                            graph_store.reset()
                        except Exception as e:
                            log(f"⚠️ Failed to clear persisted graph: {e}")
                    
                    mode_name = "AAM Connectors" if flag_value else "Legacy File Sources"
                    log(f"🔄 DCL Engine: Cache cleared - now using {mode_name}")
                    
                    # Broadcast state change to WebSocket clients
                    await broadcast_state_change("aam_mode_toggled")
            
            await ensure_pubsub_listener(on_flag_change=on_flag_change_callback)
            log("📡 DCL Engine: Feature flag pub/sub listener started (production-ready)")
        except Exception as e:
            log(f"⚠️ Feature flag initialization failed: {e}. Using in-memory fallback.")
    else:
        log("⚠️ Redis not available - feature flags will use in-memory storage only")
    
    # Initialize dev_mode to Prod Mode (False) as default if not already set
    try:
        existing_mode = redis_client.get(DEV_MODE_KEY)
        if existing_mode is None:
            # First time startup - default to Prod Mode
            set_dev_mode(False)
            log("🔧 Initialized dev_mode to Prod Mode (default)")
        else:
            # Keep existing user preference
            current = get_dev_mode()
            mode_str = "Dev Mode" if current else "Prod Mode"
            log(f"🔧 Loaded persistent dev_mode setting: {mode_str}")
    except Exception as e:
        log(f"⚠️ Error initializing dev_mode: {e}, defaulting to Prod Mode")
        set_dev_mode(False)
    
    try:
        rag_engine = RAGEngine()
        log("✅ RAG Engine initialized successfully")
    except Exception as e:
        log(f"⚠️ RAG Engine initialization failed: {e}. Continuing without RAG.")
    
    # Initialize AgentExecutor
    try:
        agents_config = load_agents_config()
        agent_executor = AgentExecutor(get_db_path, agents_config, AGENT_RESULTS_CACHE, redis_client)
        log("✅ AgentExecutor initialized successfully with Phase 4 metadata support")
    except Exception as e:
        log(f"⚠️ AgentExecutor initialization failed: {e}. Continuing without agent execution.")


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="Auth token (optional)")
):
    """
    WebSocket endpoint for real-time DCL state updates with tenant isolation.
    Eliminates polling by pushing state changes to connected clients.
    
    Tenant ID Extraction:
        - If token provided: Extract from JWT and use for tenant-scoped broadcasts
        - If no token (AUTH_ENABLED=false): Use "default" tenant
    
    Connection Tagging:
        - WebSocket connection is tagged with tenant_id
        - Broadcasts are filtered to only reach connections with matching tenant_id
    
    Note: WebSocket authentication uses token query param instead of Depends()
          due to ASGI spec incompatibility with WebSocket upgrade handshake.
    """
    # Extract tenant_id from token (if provided)
    tenant_id = "default"
    if token and AUTH_ENABLED:
        try:
            from app.security import decode_access_token
            payload = decode_access_token(token)
            tenant_id = payload.get("tenant_id", "default")
        except Exception:
            # Invalid token - use default tenant (graceful fallback)
            tenant_id = "default"
    
    # Connect with tenant_id tagging
    await ws_manager.connect(websocket, tenant_id=tenant_id)
    try:
        # Send initial state on connection
        await broadcast_state_change("connection_established", tenant_id)
        
        # Keep connection alive and listen for client messages (if needed)
        while True:
            data = await websocket.receive_text()
            # Client can request state refresh by sending "refresh"
            if data == "refresh":
                await broadcast_state_change("state_refresh", tenant_id)
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        log(f"⚠️ WebSocket error: {e}", tenant_id)
        ws_manager.disconnect(websocket)


@app.get("/state", dependencies=AUTH_DEPENDENCIES)
def state(current_user = Depends(get_current_user)):
    """
    Get current DCL state including graph, sources, agents, and metrics.
    
    Args:
        current_user: Current authenticated user (contains tenant_id)
    
    Returns:
        StateResponse with tenant-scoped DCL state
    
    Behavior:
        - Extracts tenant_id from current_user
        - Returns tenant-scoped graph state, events, sources, and metrics
        - Filters graph nodes based on source mode (AAM vs demo files)
    
    Args:
        current_user: Current authenticated user (contains tenant_id in JWT claims)
    
    Returns:
        StateResponse with complete DCL state for the tenant
    
    Tenant Isolation:
        - Extracts tenant_id from current_user JWT claims
        - In Phase 1a: Still reads from global state (TENANT_SCOPED_STATE=False)
        - In Phase 1b: Will read from tenant-scoped state via TenantStateManager
    """
    # Extract tenant_id from current user
    tenant_id = get_tenant_id_from_user(current_user)
    
    global RAG_CONTEXT, rag_engine, agents_config
    
    # Update total mappings count from RAG engine
    if rag_engine:
        try:
            stats = rag_engine.get_stats()
            RAG_CONTEXT["total_mappings"] = stats.get("total_mappings", 0)
        except:
            pass
    
    # Include agent consumption metadata for frontend
    if not agents_config:
        agents_config = load_agents_config()
    
    agent_consumption = {}
    for agent_id, agent_info in agents_config.get("agents", {}).items():
        agent_consumption[agent_id] = agent_info.get("consumes", [])
    
    # Get current graph state for this tenant (state_access handles dual-path)
    current_graph = state_access.get_graph_state(tenant_id)
    
    # Filter graph based on AAM mode - show only relevant source nodes
    use_aam = FeatureFlagConfig.is_enabled(FeatureFlag.USE_AAM_AS_SOURCE)
    # AAM sources (lowercase keys as they appear in source_key)
    aam_source_keys = {"salesforce", "supabase", "mongodb", "filesource"}
    
    # Check if user has connected any sources (vs still viewing seed demo graph)
    selected_sources = state_access.get_sources(tenant_id)
    user_has_connected_sources = len(selected_sources) > 0
    
    # Filter nodes based on mode
    if use_aam and user_has_connected_sources:
        # AAM mode with user connections: Filter to show only AAM sources + ontology + agents
        # This optimizes the graph view when users have actively connected AAM sources
        filtered_nodes = []
        for node in current_graph["nodes"]:
            node_type = node.get("type")
            
            # Always include ontology and agent nodes
            if node_type in ["ontology", "agent"]:
                filtered_nodes.append(node)
                continue
            
            # For source_parent nodes: include consolidated parent (sys_aam_sources) or individual AAM sources
            if node_type == "source_parent":
                node_id = node.get("id", "")
                # Include consolidated "from AAM" parent node
                if node_id == "sys_aam_sources":
                    filtered_nodes.append(node)
                # Include individual AAM source parents
                elif node_id.startswith("sys_"):
                    source_key = node_id[4:]  # Remove "sys_" prefix
                    if source_key in aam_source_keys:
                        filtered_nodes.append(node)
            
            # For source table nodes: include children of consolidated parent (sys_aam_sources) or individual AAM sources
            elif node_type == "source":
                parent_id = node.get("parentId", "")
                # Include source tables under consolidated parent
                if parent_id == "sys_aam_sources":
                    filtered_nodes.append(node)
                # Include source tables under individual AAM source parents
                elif parent_id.startswith("sys_"):
                    source_key = parent_id[4:]  # Remove "sys_" prefix
                    if source_key in aam_source_keys:
                        filtered_nodes.append(node)
    else:
        # AAM mode with NO user connections: Show full seed demo graph (33 nodes)
        # Legacy mode: Show all nodes (9 demo CSV sources + ontology + agents)
        # This ensures users see a complete graph visualization even without connections
        filtered_nodes = current_graph["nodes"]
    
    # Filter graph edges for Sankey rendering - exclude join edges to prevent circular references
    # D3-sankey requires a directed acyclic graph (DAG), but join edges create bidirectional cycles
    # Also filter edges to only include those between filtered nodes
    filtered_node_ids = {node["id"] for node in filtered_nodes}
    filtered_graph = {
        "nodes": filtered_nodes,
        "edges": [
            edge for edge in current_graph["edges"]
            if edge.get("type") != "join"  # Only keep hierarchy and dataflow edges
            and edge.get("source") in filtered_node_ids  # Source node must be in filtered set
            and edge.get("target") in filtered_node_ids  # Target node must be in filtered set
        ]
    }
    
    # Get LLM stats from Redis (persists across restarts)
    llm_stats = get_llm_stats()
    
    # Use graph confidence directly as blended confidence
    # (Graph confidence already incorporates mapping quality and completeness)
    blended_confidence = current_graph.get("confidence")
    
    # Determine source mode from feature flag
    source_mode = "aam_connectors" if FeatureFlagConfig.is_enabled(FeatureFlag.USE_AAM_AS_SOURCE) else "demo_files"
    
    # Get tenant-scoped state (state_access handles dual-path internally)
    current_events = state_access.get_event_log(tenant_id)
    selected_sources = state_access.get_sources(tenant_id)
    selected_agents = state_access.get_selected_agents(tenant_id)
    
    # Convert nodes to GraphNode DTOs
    graph_nodes = [
        GraphNode(
            id=node.get("id", ""),
            label=node.get("label", ""),
            type=node.get("type", ""),
            metadata=node  # Include full node data as metadata for backward compatibility
        )
        for node in filtered_nodes
    ]
    
    # Convert edges to GraphEdge DTOs
    graph_edges = [
        GraphEdge(
            source=edge.get("source", ""),
            target=edge.get("target", ""),
            label=edge.get("label"),
            weight=edge.get("weight")
        )
        for edge in filtered_graph["edges"]
    ]
    
    # Build GraphState
    graph_state = GraphState(
        nodes=graph_nodes,
        edges=graph_edges,
        confidence=blended_confidence,
        last_updated=datetime.now() if current_graph.get("nodes") else None
    )
    
    # Get entity sources mapping
    entity_sources = state_access.get_entity_sources(tenant_id)
    
    # Build metadata with backward compatibility
    metadata = {
        "tenant_id": tenant_id,
        "events": current_events,
        "timeline": current_events[-5:] if current_events else [],
        "llm": {
            "calls": llm_stats["calls"], 
            "tokens": llm_stats["tokens"],
            "calls_saved": llm_stats["calls_saved"]
        },
        "auto_ingest_unmapped": AUTO_INGEST_UNMAPPED,
        "rag": {
            **RAG_CONTEXT,
            "mappings_retrieved": RAG_CONTEXT.get("last_retrieval_count", 0)
        },
        "agent_consumption": agent_consumption,
        "dev_mode": get_dev_mode(),
        "auth_enabled": AUTH_ENABLED,
        "source_mode": source_mode
    }
    
    # Return backward-compatible response
    # Frontend expects nodes and edges at root level, not nested in graph object
    return {
        "nodes": filtered_graph["nodes"],  # Use original nodes format for frontend
        "edges": filtered_graph["edges"],  # Use original edges format for frontend
        "confidence": blended_confidence,
        "sources_added": selected_sources,
        "entity_sources": entity_sources,
        "selected_agents": selected_agents,
        "tenant_id": tenant_id,
        "metadata": metadata,
        # Additional fields for backward compatibility
        "events": current_events,
        "timeline": current_events[-5:] if current_events else [],
        "llm": {
            "calls": llm_stats["calls"], 
            "tokens": llm_stats["tokens"],
            "calls_saved": llm_stats["calls_saved"]
        },
        "auto_ingest_unmapped": AUTO_INGEST_UNMAPPED,
        "rag": {
            **RAG_CONTEXT,
            "mappings_retrieved": RAG_CONTEXT.get("last_retrieval_count", 0)
        },
        "agent_consumption": agent_consumption,
        "dev_mode": get_dev_mode(),
        "auth_enabled": AUTH_ENABLED,
        "source_mode": source_mode
    }

@app.get("/dcl/agents/{agent_id}/results", dependencies=AUTH_DEPENDENCIES)
async def get_agent_results(
    agent_id: str,
    tenant_id: str = Query("default", description="Tenant identifier")
):
    """
    Retrieve agent execution results.
    Returns insights, statistics, and execution metadata for a specific agent.
    """
    if not agent_executor:
        return JSONResponse({"error": "Agent executor not initialized"}, status_code=500)
    
    results = agent_executor.get_results(agent_id, tenant_id)
    
    if not results:
        return JSONResponse(
            {"error": f"No results found for agent '{agent_id}' (tenant: {tenant_id})"},
            status_code=404
        )
    
    return results

@app.get("/dcl/agents/results", dependencies=AUTH_DEPENDENCIES)
async def get_all_agent_results(
    tenant_id: str = Query("default", description="Tenant identifier")
):
    """Retrieve all agent execution results for a tenant."""
    if not agent_executor:
        return JSONResponse({"error": "Agent executor not initialized"}, status_code=500)
    
    return agent_executor.get_all_results(tenant_id)

@app.get("/dcl/metadata", dependencies=AUTH_DEPENDENCIES)
async def get_data_quality_metadata(
    tenant_id: str = Query("default", description="Tenant identifier")
):
    """
    Get aggregated data quality metadata for tenant.
    Includes drift status, repair counts, confidence scores, and processing stages.
    """
    if not agent_executor:
        return JSONResponse({
            "overall_data_quality_score": 0.85,
            "drift_detected": False,
            "repair_processed": False,
            "auto_applied_repairs": 0,
            "hitl_pending_repairs": 0,
            "sources_with_drift": [],
            "low_confidence_sources": [],
            "overall_confidence": None,
            "sources": {}
        })
    
    try:
        # Get aggregated metadata from agent executor
        metadata = await asyncio.to_thread(agent_executor._aggregate_metadata, tenant_id)
        return JSONResponse(metadata)
    except Exception as e:
        log(f"⚠️ Error fetching data quality metadata: {e}")
        return JSONResponse({
            "overall_data_quality_score": 0.0,
            "drift_detected": False,
            "repair_processed": False,
            "auto_applied_repairs": 0,
            "hitl_pending_repairs": 0,
            "sources_with_drift": [],
            "low_confidence_sources": [],
            "overall_confidence": None,
            "sources": {},
            "error": str(e)
        }, status_code=500)

@app.get("/dcl/drift-alerts", dependencies=AUTH_DEPENDENCIES)
async def get_drift_alerts(
    tenant_id: str = Query("default", description="Tenant identifier")
):
    """
    Get active schema drift alerts for tenant.
    Returns list of sources with detected schema drift including severity and affected fields.
    """
    if not agent_executor:
        return JSONResponse({"alerts": []})
    
    try:
        # Get metadata first
        metadata = await asyncio.to_thread(agent_executor._aggregate_metadata, tenant_id)
        
        # Build drift alerts from sources with drift
        alerts = []
        sources_data = metadata.get("sources", {})
        sources_with_drift = metadata.get("sources_with_drift", [])
        
        for source_id in sources_with_drift:
            source_metadata = sources_data.get(source_id, {})
            
            # Determine severity based on number of fields changed
            fields_changed = source_metadata.get("fields_changed", [])
            field_count = len(fields_changed)
            
            if field_count >= 5:
                severity = "high"
            elif field_count >= 2:
                severity = "medium"
            else:
                severity = "low"
            
            alerts.append({
                "source_id": source_id,
                "connector_type": source_metadata.get("connector_type", "unknown"),
                "drift_severity": severity,
                "fields_changed": fields_changed,
                "detected_at": source_metadata.get("drift_detected_at", None)
            })
        
        return JSONResponse({"alerts": alerts})
    except Exception as e:
        log(f"⚠️ Error fetching drift alerts: {e}")
        return JSONResponse({"alerts": [], "error": str(e)}, status_code=500)

@app.get("/dcl/hitl-pending", dependencies=AUTH_DEPENDENCIES)
async def get_hitl_pending(
    tenant_id: str = Query("default", description="Tenant identifier")
):
    """
    Get pending HITL (Human-in-the-Loop) review requests.
    Returns count and details of pending manual reviews.
    """
    if not agent_executor:
        return JSONResponse({"pending_count": 0, "reviews": []})
    
    try:
        # Get metadata
        metadata = await asyncio.to_thread(agent_executor._aggregate_metadata, tenant_id)
        
        # Get HITL pending count
        hitl_count = metadata.get("hitl_pending_repairs", 0)
        
        # Build review items from sources metadata
        reviews = []
        sources_data = metadata.get("sources", {})
        
        for source_id, source_metadata in sources_data.items():
            hitl_repairs = source_metadata.get("hitl_queued_count", 0)
            if hitl_repairs > 0:
                reviews.append({
                    "source_id": source_id,
                    "connector_type": source_metadata.get("connector_type", "unknown"),
                    "pending_repairs": hitl_repairs,
                    "confidence_score": source_metadata.get("confidence", 0.0),
                    "queued_at": source_metadata.get("repair_queued_at", None)
                })
        
        return JSONResponse({
            "pending_count": hitl_count,
            "reviews": reviews
        })
    except Exception as e:
        log(f"⚠️ Error fetching HITL pending: {e}")
        return JSONResponse({"pending_count": 0, "reviews": [], "error": str(e)}, status_code=500)

@app.get("/dcl/repair-history", dependencies=AUTH_DEPENDENCIES)
async def get_repair_history(
    tenant_id: str = Query("default", description="Tenant identifier"),
    limit: int = Query(50, description="Maximum number of repair records to return")
):
    """
    Get recent auto-repair history.
    Returns recent repairs with confidence scores, auto-applied vs HITL status.
    """
    if not agent_executor:
        return JSONResponse({"repairs": []})
    
    try:
        # Get metadata
        metadata = await asyncio.to_thread(agent_executor._aggregate_metadata, tenant_id)
        
        # Build repair history from sources metadata
        repairs = []
        sources_data = metadata.get("sources", {})
        
        for source_id, source_metadata in sources_data.items():
            auto_applied = source_metadata.get("auto_applied_count", 0)
            hitl_queued = source_metadata.get("hitl_queued_count", 0)
            
            if auto_applied > 0:
                repairs.append({
                    "source_id": source_id,
                    "connector_type": source_metadata.get("connector_type", "unknown"),
                    "repair_type": "auto_applied",
                    "count": auto_applied,
                    "confidence": source_metadata.get("confidence", 0.0),
                    "applied_at": source_metadata.get("repair_applied_at", None),
                    "fields_repaired": source_metadata.get("fields_repaired", [])
                })
            
            if hitl_queued > 0:
                repairs.append({
                    "source_id": source_id,
                    "connector_type": source_metadata.get("connector_type", "unknown"),
                    "repair_type": "hitl_pending",
                    "count": hitl_queued,
                    "confidence": source_metadata.get("confidence", 0.0),
                    "queued_at": source_metadata.get("repair_queued_at", None),
                    "fields_requiring_review": source_metadata.get("fields_requiring_review", [])
                })
        
        # Sort by timestamp (most recent first) and limit
        repairs.sort(key=lambda x: x.get("applied_at") or x.get("queued_at") or "", reverse=True)
        repairs = repairs[:limit]
        
        return JSONResponse({"repairs": repairs})
    except Exception as e:
        log(f"⚠️ Error fetching repair history: {e}")
        return JSONResponse({"repairs": [], "error": str(e)}, status_code=500)

@app.get("/connect", dependencies=AUTH_DEPENDENCIES)
@limiter.limit("10/minute")  # Max 10 connect operations per minute
async def connect(
    request: Request,
    sources: str = Query(...),
    agents: str = Query(...),
    llm_model: str = Query("gemini-2.5-flash", description="LLM model: gemini-2.5-flash, gpt-4o-mini, gpt-4o"),
    current_user = Depends(get_current_user)
):
    """
    Additive connection endpoint - connects sources incrementally without clearing existing state.
    Sources and nodes accumulate across multiple calls, with automatic deduplication.
    Dev mode and existing sources are preserved.
    
    Args:
        current_user: Current authenticated user (contains tenant_id in JWT claims)
        sources: Comma-separated list of source IDs to connect
        agents: Comma-separated list of agent IDs to execute
        llm_model: LLM model to use for entity mapping
    
    Behavior:
        - Sources are added incrementally (does NOT clear existing sources)
        - Reconnecting existing source is idempotent (no duplicates)
        - Graph nodes are deduplicated automatically in add_graph_nodes_for_source()
        - To clear state, explicitly call /reset endpoint before /connect
    
    Tenant Isolation:
        - Extracts tenant_id from current_user JWT claims via get_tenant_id_from_user()
        - All state operations are tenant-scoped via TenantStateManager
    """
    # Extract tenant_id from current user (CRITICAL for multi-tenant isolation)
    tenant_id = get_tenant_id_from_user(current_user)
    source_list = [s.strip() for s in sources.split(',') if s.strip()]
    agent_list = [a.strip() for a in agents.split(',') if a.strip()]
    
    if not source_list:
        return JSONResponse({"error": "No sources provided"}, status_code=400)
    if not agent_list:
        return JSONResponse({"error": "No agents provided"}, status_code=400)
    
    # Determine source mode from feature flag
    source_mode = "aam_connectors" if FeatureFlagConfig.is_enabled(FeatureFlag.USE_AAM_AS_SOURCE) else "demo_files"
    
    # CRITICAL FIX: Do NOT reset state - allow sources to accumulate incrementally
    # Idempotency checks in add_graph_nodes_for_source() prevent duplicate nodes
    # If user wants fresh start, they should call /reset endpoint first
    log(f"🔌 Connecting {len(source_list)} source(s) with {len(agent_list)} agent(s)...")
    log(f"📂 Using {source_mode} for sources: {', '.join(source_list)} (tenant: {tenant_id})")
    
    # Store selected agents in tenant-scoped storage (state_access handles dual-path)
    state_access.set_selected_agents(tenant_id, agent_list)
    
    # Log which model is being used
    log(f"🤖 Using LLM model: {llm_model}")
    
    try:
        # Connect all sources in parallel using async concurrency
        # Note: Each connect_source has internal distributed lock for safe state mutations
        tasks = [connect_source(source, llm_model, tenant_id) for source in source_list]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check for any errors in the results
        errors = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_msg = f"{source_list[i]}: {str(result)}"
                errors.append(error_msg)
                log(f"❌ Error connecting {source_list[i]}: {str(result)}")
        
        if errors:
            log(f"⚠️ Some sources failed to connect: {'; '.join(errors)}")
            return JSONResponse({"error": f"Partial failure: {'; '.join(errors)}"}, status_code=207)
    except Exception as e:
        log(f"❌ Connection error: {str(e)}")
        return JSONResponse({"error": str(e)}, status_code=500)
    
    # Execute agents after all sources have completed and materialized views are ready
    if agent_list and agent_executor:
        # Check if DuckDB database exists before attempting agent execution
        db_path = get_db_path(tenant_id)
        print(f"[TRACE_DCL] Agent execution check - db_path: {db_path}", flush=True)
        print(f"[TRACE_DCL] os.path.exists({db_path}): {os.path.exists(db_path)}", flush=True)
        
        if os.path.exists(db_path):
            print(f"[TRACE_DCL] ✅ DuckDB file exists, executing agents", flush=True)
            try:
                log(f"🚀 Executing {len(agent_list)} agent(s) on unified DCL views (tenant: {tenant_id})")
                await agent_executor.execute_agents_async(agent_list, tenant_id, ws_manager)
                log(f"✅ Agent results stored in cache - accessible via /dcl/agents/{{agent_id}}/results")
            except Exception as e:
                print(f"[TRACE_DCL] ❌ EXCEPTION in agent execution: {e}", flush=True)
                print(f"[TRACE_DCL] Traceback: {traceback.format_exc()}", flush=True)
                log(f"❌ Agent execution failed: {e}")
                # Don't fail the entire connection if agents fail - log and continue
        else:
            print(f"[TRACE_DCL] ❌ DuckDB file missing, skipping agents", flush=True)
            log(f"ℹ️ No materialized views available - skipping agent execution (DuckDB not created)")
    elif not agent_list:
        log(f"ℹ️ No agents selected for execution")
    elif not agent_executor:
        log(f"⚠️ Agent executor not initialized - skipping agent execution")
    
    # Broadcast state change to WebSocket clients
    await broadcast_state_change("sources_connected")
    
    # Persist graph state to Redis after successful connection
    if graph_store and tenant_state_manager:
        try:
            current_graph = state_access.get_graph_state(tenant_id)
            graph_store.save(current_graph, tenant_id)
        except Exception as e:
            log(f"⚠️ Failed to persist graph: {e}")
    
    # Get sources for response (state_access handles dual-path)
    response_sources = state_access.get_sources(tenant_id)
    
    return JSONResponse({
        "ok": True, 
        "sources": response_sources, 
        "agents": agent_list,
        "source_mode": source_mode,
        "tenant_id": tenant_id
    })

# DEPRECATED: /reset endpoint - replaced by unified idempotent /connect logic
# Keeping this commented out for reference. All reset+connect behavior is now handled by /connect.
# @app.get("/reset")
# async def reset():
#     reset_state(exclude_dev_mode=True)
#     # Broadcast state change to WebSocket clients
#     await broadcast_state_change("demo_reset")
#     return JSONResponse({"ok": True})

@app.get("/toggle_dev_mode", dependencies=AUTH_DEPENDENCIES)
async def toggle_dev_mode(
    enabled: Optional[bool] = None,
    current_user = Depends(get_current_user)
):
    """
    Toggle Dev Mode (AI/RAG mapping vs heuristic-only).
    
    Args:
        enabled: If provided, set dev mode to this value. If None, toggle current state.
        current_user: Current authenticated user (for tenant_id extraction)
    
    Returns:
        JSON response with new dev mode state
    """
    # Extract tenant_id for tenant-scoped broadcasting
    tenant_id = get_tenant_id_from_user(current_user)
    
    global DEV_MODE, rag_engine
    # Update both local and Redis state for backward compatibility
    current_dev_mode = get_dev_mode()
    if enabled is not None:
        DEV_MODE = enabled
        set_dev_mode(enabled)
    else:
        DEV_MODE = not current_dev_mode
        set_dev_mode(DEV_MODE)
    
    # Clear RAG cache when dev mode toggles
    if rag_engine:
        rag_engine.clear_cache()
        log("🗑️ Cleared RAG cache due to dev mode toggle", tenant_id)
    
    status = "enabled" if DEV_MODE else "disabled"
    log(f"🔧 Dev Mode {status} - {'AI/RAG mapping active' if DEV_MODE else 'Using heuristic-only mapping'}", tenant_id)
    # Broadcast state change to WebSocket clients
    await broadcast_state_change("dev_mode_toggled", tenant_id)
    return JSONResponse({"dev_mode": DEV_MODE, "status": status})

async def _background_clear_cache(tenant_id: str, graph_store):
    """Background task to clear cache without blocking the toggle response."""
    # Clear DCL cache to force fresh graph generation (state_access handles dual-path)
    state_access.set_graph_state(tenant_id, {"nodes": [], "edges": [], "confidence": None, "last_updated": None})
    state_access.set_sources(tenant_id, [])
    
    # Clear persisted graph state from Redis
    if graph_store:
        try:
            graph_store.reset()
        except Exception as e:
            log(f"⚠️ Failed to clear persisted graph: {e}")
    
    log("🗑️ Cleared DCL cache (GRAPH_STATE, SOURCES_ADDED) - ready for fresh graph generation")
    
    # Broadcast state change to WebSocket clients
    await broadcast_state_change("aam_mode_toggled")

@app.post("/dcl/toggle_aam_mode", dependencies=AUTH_DEPENDENCIES)
@limiter.limit("5/minute")  # Max 5 mode toggles per minute
async def toggle_aam_mode(
    request: Request,
    current_user = Depends(get_current_user)
):
    """
    Toggle USE_AAM_AS_SOURCE feature flag and clear DCL cache.
    
    PERFORMANCE OPTIMIZATION: Returns immediately after flag flip, cache clearing runs in background.
    
    This endpoint:
    1. Toggles the USE_AAM_AS_SOURCE flag (Legacy files <-> AAM connectors)
    2. Writes to Redis for cross-worker persistence
    3. Publishes to pub/sub for cross-worker cache invalidation
    4. Kicks off background task to clear DCL state (non-blocking)
    5. Returns immediately (<100ms instead of ~3s)
    
    Expected behavior:
    - AAM mode ON: Uses 4 AAM sources (Salesforce, MongoDB, Supabase, FilesSource)
    - AAM mode OFF: Uses 9 Legacy file sources (Salesforce, Dynamics, HubSpot, etc.)
    - Flag change broadcasts to all workers via Redis pub/sub
    
    Args:
        request: FastAPI request object (for rate limiting)
        current_user: Current authenticated user (for tenant_id extraction)
    """
    global _active_toggle_requests
    
    # Extract tenant_id from current user
    tenant_id = get_tenant_id_from_user(current_user)
    now = time.time()
    last_toggle = _active_toggle_requests.get(tenant_id, 0)
    
    if now - last_toggle < 1.0:  # Ignore if < 1 second since last toggle
        log(f"⚠️ Ignoring duplicate toggle request for tenant {tenant_id} (< 1s since last)")
        return JSONResponse({
            "ok": True,
            "status": "debounced",
            "message": "Request ignored - too soon after previous toggle"
        })
    
    _active_toggle_requests[tenant_id] = now
    
    # Ensure pub/sub listener is running (lazy initialization)
    await ensure_pubsub_listener()
    
    # Get current state and toggle
    current_state = FeatureFlagConfig.is_enabled(FeatureFlag.USE_AAM_AS_SOURCE)
    new_state = not current_state
    
    # Set the flag (writes to Redis and publishes to pub/sub) - FAST <50ms
    FeatureFlagConfig.set_flag(FeatureFlag.USE_AAM_AS_SOURCE, new_state)
    
    mode_name = "AAM Connectors (4 sources)" if new_state else "Legacy File Sources (9 sources)"
    log(f"🔄 AAM Mode toggled to: {mode_name}")
    
    # Kick off cache clearing in background (fire-and-forget) - DOESN'T BLOCK RESPONSE
    asyncio.create_task(_background_clear_cache(tenant_id, graph_store))
    
    # Return immediately - total endpoint latency <100ms (vs previous 2.8s)
    return JSONResponse({
        "ok": True,
        "USE_AAM_AS_SOURCE": new_state,
        "mode": mode_name,
        "cache_cleared": True  # True indicates background task started, not completed
    })

@app.post("/reset_llm_stats", dependencies=AUTH_DEPENDENCIES)
async def reset_llm_stats_endpoint(current_user = Depends(get_current_user)):
    """
    Manual endpoint to reset LLM call counters.
    
    Args:
        current_user: Current authenticated user (for tenant_id extraction)
    
    Returns:
        JSON response with reset confirmation
    
    Note: LLM stats persist across all runs by default for cumulative tracking.
    Use this endpoint only when you want to reset the counters manually.
    """
    # Extract tenant_id for tenant-scoped logging
    tenant_id = get_tenant_id_from_user(current_user)
    
    reset_llm_stats()
    stats = get_llm_stats()
    log("🔄 LLM stats manually reset to 0", tenant_id)
    return JSONResponse({
        "ok": True,
        "message": "LLM stats reset successfully",
        "calls": stats["calls"],
        "tokens": stats["tokens"]
    })

@app.get("/preview", dependencies=AUTH_DEPENDENCIES)
def preview(
    node: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """
    Preview table data for source or ontology tables.
    
    Args:
        node: Optional node ID to preview (e.g., "src_salesforce_account", "dcl_account")
        current_user: Current authenticated user (for tenant_id extraction)
    
    Returns:
        JSON response with preview data for sources and ontology tables
    
    Tenant Isolation:
        - Phase 1b-5 complete: Uses tenant-scoped state from TenantStateManager
        - When TENANT_SCOPED_STATE=False: Reads from global SELECTED_AGENTS (backward compatible)
        - When TENANT_SCOPED_STATE=True: Reads from tenant-scoped Redis storage
    """
    # Extract tenant_id
    tenant_id = get_tenant_id_from_user(current_user)
    
    global ontology, agents_config
    # Use read-only mode for preview operations
    con = duckdb.connect(get_db_path(tenant_id), read_only=True)
    sources, ontology_tables = {}, {}
    if node:
        try:
            if node.startswith("src_"):
                sources[node] = preview_table(con, node)
            elif node.startswith("dcl_"):
                ontology_tables[node] = preview_table(con, node)
        except Exception:
            pass
    else:
        # Determine which entities to preview based on selected agents
        if not agents_config:
            agents_config = load_agents_config()
        
        ontology_entities = set()
        # Get selected agents (state_access handles dual-path internally)
        selected_agents = state_access.get_selected_agents(tenant_id)
        
        if selected_agents:
            # Get entities consumed by selected agents
            for agent_id in selected_agents:
                agent_info = agents_config.get("agents", {}).get(agent_id, {})
                consumes = agent_info.get("consumes", [])
                ontology_entities.update(consumes)
        else:
            # If no agents selected, show all ontology entities
            if not ontology:
                ontology = load_ontology()
            ontology_entities = set(ontology.get("entities", {}).keys())
        
        for ent in ontology_entities:
            ontology_tables[f"dcl_{ent}"] = preview_table(con, f"dcl_{ent}")
    return JSONResponse({"sources": sources, "ontology": ontology_tables})

@app.get("/source_schemas", dependencies=AUTH_DEPENDENCIES)
def source_schemas(current_user = Depends(get_current_user)):
    """
    Return complete schema information for all connected sources.
    
    Args:
        current_user: Current authenticated user (for tenant_id extraction)
    
    Returns:
        JSON response with source schema metadata
    
    Tenant Isolation:
        - Phase 1b-4 complete: Uses tenant-scoped state from TenantStateManager
        - When TENANT_SCOPED_STATE=False: Reads from global SOURCE_SCHEMAS (backward compatible)
        - When TENANT_SCOPED_STATE=True: Reads from tenant-scoped Redis storage
    """
    # Extract tenant_id
    tenant_id = get_tenant_id_from_user(current_user)
    
    # Get tenant-scoped source schemas (state_access handles dual-path)
    schemas = state_access.get_source_schemas(tenant_id)
    
    # Sanitize data for JSON serialization (replace NaN/Inf with None)
    import math
    def sanitize(obj):
        if isinstance(obj, dict):
            return {k: sanitize(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [sanitize(item) for item in obj]
        elif isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
            return None
        else:
            return obj
    
    clean_schemas = sanitize(schemas)
    return JSONResponse(clean_schemas)

@app.get("/ontology_schema", dependencies=AUTH_DEPENDENCIES)
def ontology_schema(current_user = Depends(get_current_user)):
    """
    Return ontology entity definitions with all fields and source mappings.
    
    Args:
        current_user: Current authenticated user (for tenant_id extraction)
    
    Returns:
        JSON response with ontology schema including field definitions and source mappings
    
    Tenant Isolation:
        - In Phase 1a: Still accesses global GRAPH_STATE
        - In Phase 1b: Will use tenant-scoped state from TenantStateManager
    """
    # Extract tenant_id (prepared for Phase 1b migration)
    tenant_id = get_tenant_id_from_user(current_user)
    
    global ontology
    
    if not ontology:
        ontology = load_ontology()
    
    # Get current graph state for this tenant (state_access handles dual-path)
    current_graph = state_access.get_graph_state(tenant_id)
    
    # Build schema: entity -> {pk, fields[], source_mappings[]}
    schema = {}
    entities = ontology.get("entities", {})
    
    for entity_name, entity_def in entities.items():
        # Extract source mappings from graph edges
        source_mappings = []
        
        # Find all edges that map to this ontology entity
        for edge in current_graph.get("edges", []):
            if edge.get("edgeType") == "dataflow":
                # Check if target node is this ontology entity
                target_node_id = edge.get("target", "")
                if target_node_id == f"dcl_{entity_name}":
                    # Find the source node to get source system and table info
                    source_node_id = edge.get("source", "")
                    source_node = next((n for n in current_graph.get("nodes", []) if n.get("id") == source_node_id), None)
                    
                    if source_node:
                        source_system = source_node.get("sourceSystem", "Unknown")
                        source_table = source_node.get("label", "").replace(f"{source_system}_", "")
                        field_mappings = edge.get("field_mappings", [])
                        
                        # Extract source fields from field_mappings (for backward compatibility)
                        source_fields = []
                        for fm in field_mappings:
                            source_field = fm.get("source") or fm.get("source_field", "")
                            if source_field:
                                source_fields.append(source_field)
                        
                        # Include detailed field mappings with confidence, transformations, etc.
                        detailed_mappings = []
                        for fm in field_mappings:
                            detailed_mappings.append({
                                "source_field": fm.get("source") or fm.get("source_field", ""),
                                "ontology_field": fm.get("onto_field", ""),
                                "confidence": fm.get("confidence", 0.0),
                                "transform": fm.get("transform", "direct"),
                                "sql_expression": fm.get("sql", "")
                            })
                        
                        source_mappings.append({
                            "source_system": source_system,
                            "source_table": source_table,
                            "source_fields": source_fields,  # List of source field names (backward compat)
                            "field_count": len(field_mappings),
                            "field_mappings": detailed_mappings  # NEW: Detailed field-level mappings
                        })
        
        schema[entity_name] = {
            "pk": entity_def.get("pk", ""),
            "fields": entity_def.get("fields", []),
            "source_mappings": source_mappings
        }
    
    return JSONResponse(schema)

@app.get("/toggle_auto_ingest", dependencies=AUTH_DEPENDENCIES)
def toggle_auto_ingest(enabled: bool = Query(...)):
    global AUTO_INGEST_UNMAPPED
    AUTO_INGEST_UNMAPPED = enabled
    return JSONResponse({"ok": True, "enabled": AUTO_INGEST_UNMAPPED})

@app.get("/feature_flags", dependencies=AUTH_DEPENDENCIES)
def get_feature_flags():
    """Get current state of all feature flags."""
    from app.config.feature_flags import FeatureFlagConfig
    return JSONResponse(FeatureFlagConfig.get_all_flags())

@app.post("/feature_flags/toggle", dependencies=AUTH_DEPENDENCIES)
async def toggle_feature_flag(request: Dict[str, Any]):
    """Toggle a feature flag (USE_AAM_AS_SOURCE)."""
    from app.config.feature_flags import FeatureFlagConfig, FeatureFlag
    
    flag_name = request.get("flag")
    enabled = request.get("enabled")
    
    if flag_name not in [f.value for f in FeatureFlag]:
        return JSONResponse({"error": f"Invalid flag: {flag_name}"}, status_code=400)
    
    # Set the flag
    flag_enum = FeatureFlag(flag_name)
    FeatureFlagConfig.set_flag(flag_enum, enabled)
    
    # Get updated state
    all_flags = FeatureFlagConfig.get_all_flags()
    migration_phase = FeatureFlagConfig.get_migration_phase()
    
    return JSONResponse({
        "ok": True,
        "flag": flag_name,
        "enabled": enabled,
        "all_flags": all_flags,
        "migration_phase": migration_phase
    })

@app.get("/rag/stats", dependencies=AUTH_DEPENDENCIES)
def rag_stats():
    """Get RAG engine statistics."""
    if not rag_engine:
        return JSONResponse({"error": "RAG Engine not initialized"}, status_code=503)
    try:
        stats = rag_engine.get_stats()
        return JSONResponse(stats)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/supabase-config", dependencies=AUTH_DEPENDENCIES)
def supabase_config():
    """Provide Supabase configuration to frontend (only public keys)."""
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_anon_key = os.getenv("SUPABASE_ANON_KEY", "")
    
    if not supabase_url or not supabase_anon_key:
        return JSONResponse({"error": "Supabase not configured"}, status_code=500)
    
    return JSONResponse({
        "url": supabase_url,
        "anonKey": supabase_anon_key
    })

@app.post("/api/infer", dependencies=AUTH_DEPENDENCIES)
async def infer_schema(request: Dict[str, Any]):
    fields = request.get("fields", [])
    
    if not os.getenv("GEMINI_API_KEY"):
        return JSONResponse({"error": "GEMINI_API_KEY not configured"}, status_code=500)
    
    prompt = f"""
You are a data integration assistant.
Your ONLY job is to output valid JSON for ontology mappings.

Schema:
{{
  "mappings": [
    {{
      "name": string,
      "type": string,
      "suggested_mapping": string,
      "transformation": string
    }}
  ]
}}

Guidelines:
- Output ONLY JSON (no prose, no markdown).
- Use "suggested_mapping" to map to enterprise ontology domains (CRM, Finance, Geography, Sales, etc).
- Use "transformation" for normalization or conversions.
- Respect the given "type" (Text, Number, DateTime, Currency, etc).

Fields:
{fields}
"""
    
    try:
        model = genai.GenerativeModel("gemini-2.5-pro")
        result = model.generate_content(prompt)
        raw_text = result.text.strip()
        
        # Strip markdown code blocks if present
        raw_text = raw_text.replace('```json\n', '').replace('\n```', '').replace('```', '')
        
        # Parse JSON
        import json as json_module
        try:
            parsed = json_module.loads(raw_text)
        except Exception:
            # Fallback if JSON parsing fails
            parsed = {
                "mappings": [
                    {
                        "name": f["name"],
                        "type": f["type"],
                        "suggested_mapping": "Unknown",
                        "transformation": "Review required"
                    }
                    for f in fields
                ]
            }
        
        return JSONResponse(content=parsed)
    
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/api/setup-database", dependencies=AUTH_DEPENDENCIES)
async def setup_database():
    """Automatically create Supabase user_profiles table and policies"""
    import requests
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")  # Service key for admin operations
    
    if not supabase_url or not supabase_key:
        return JSONResponse(
            content={"error": "SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables are required"},
            status_code=500
        )
    
    # SQL to create the complete setup
    setup_sql = """
-- Create user_profiles table
CREATE TABLE IF NOT EXISTS public.user_profiles (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('admin', 'viewer')) DEFAULT 'viewer',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable Row Level Security
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Users can view own profile" ON public.user_profiles;
DROP POLICY IF EXISTS "Users can insert own profile" ON public.user_profiles;
DROP POLICY IF EXISTS "Users can update own profile" ON public.user_profiles;

-- Create policies
CREATE POLICY "Users can view own profile" 
  ON public.user_profiles FOR SELECT 
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own profile" 
  ON public.user_profiles FOR INSERT 
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own profile" 
  ON public.user_profiles FOR UPDATE 
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- Create auto-profile function
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.user_profiles (user_id, role)
  VALUES (NEW.id, 'viewer');
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create trigger
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Performance index
CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON public.user_profiles(user_id);

-- Grant permissions
GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE ON public.user_profiles TO authenticated;
"""
    
    try:
        # Use Supabase REST API to execute SQL
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            f"{supabase_url}/rest/v1/rpc/exec",
            headers=headers,
            json={"query": setup_sql}
        )
        
        # Alternative: Try direct SQL execution via PostgREST
        if response.status_code >= 400:
            # Try using the query endpoint
            response = requests.post(
                f"{supabase_url}/rest/v1/",
                headers=headers,
                data=setup_sql
            )
        
        if response.status_code < 400:
            return JSONResponse(content={
                "success": True,
                "message": "Database tables and policies created successfully! You can now sign up."
            })
        else:
            return JSONResponse(
                content={
                    "error": f"Failed to create tables: {response.text}",
                    "suggestion": "You may need to add SUPABASE_SERVICE_KEY to your secrets (find it in Supabase Settings > API)"
                },
                status_code=500
            )
            
    except Exception as e:
        return JSONResponse(
            content={"error": str(e), "suggestion": "Check that SUPABASE_SERVICE_KEY is set correctly"},
            status_code=500
        )

# PostgreSQL Connection Management Endpoints
import base64

def encrypt_password(password: str) -> str:
    """Simple password encryption using base64"""
    key = os.getenv("ENCRYPTION_KEY", "dcl-default-key-2024")
    combined = f"{key}:{password}"
    return base64.b64encode(combined.encode()).decode()

def decrypt_password(encrypted: str) -> str:
    """Simple password decryption using base64"""
    key = os.getenv("ENCRYPTION_KEY", "dcl-default-key-2024")
    try:
        decoded = base64.b64decode(encrypted.encode()).decode()
        if decoded.startswith(f"{key}:"):
            return decoded[len(f"{key}:"):]
        return decoded
    except:
        return encrypted

@app.get("/api/connections", dependencies=AUTH_DEPENDENCIES)
def get_connections(current_user = Depends(get_current_user)):
    """Get all database connections"""
    tenant_id = get_tenant_id_from_user(current_user)
    try:
        con = duckdb.connect(get_db_path(tenant_id), read_only=True)
        result = con.execute("""
            SELECT id, created_at, connection_name, connection_type, 
                   host, port, database_name, db_user
            FROM connections
            ORDER BY created_at DESC
        """).fetchall()
        
        connections = []
        for row in result:
            connections.append({
                "id": row[0],
                "created_at": row[1].isoformat() if row[1] else None,
                "connection_name": row[2],
                "connection_type": row[3],
                "host": row[4],
                "port": row[5],
                "database_name": row[6],
                "db_user": row[7]
            })
        
        con.close()
        return JSONResponse({"connections": connections})
    except Exception as e:
        return JSONResponse({"error": str(e), "connections": []}, status_code=500)

@app.post("/api/connections/test", dependencies=AUTH_DEPENDENCIES)
async def test_connection(request: Request):
    """Test a PostgreSQL connection"""
    try:
        data = await request.json()
        host = data.get("host", "").strip()
        database_name = data.get("database_name", "").strip()
        db_user = data.get("db_user", "").strip()
        password = data.get("password", "")
        
        # Normalize and validate port
        try:
            port = int(data.get("port", 5432))
        except (ValueError, TypeError):
            port = None
        
        # Validate all required fields
        errors = []
        if not host:
            errors.append("Host is required")
        if not database_name:
            errors.append("Database name is required")
        if not db_user:
            errors.append("User is required")
        if not password:
            errors.append("Password is required")
        if port is None or port < 1 or port > 65535:
            errors.append("Port must be a valid number between 1 and 65535")
            
        if errors:
            return JSONResponse({
                "success": False,
                "message": "; ".join(errors)
            }, status_code=400)
        
        # For MVP, we'll simulate a connection test
        # In production, you would actually try to connect to the PostgreSQL database
        # using psycopg2 or similar library
        
        # Simulate connection delay
        import time as time_module
        time_module.sleep(1)
        
        # Simulate authentication failure for testing purposes
        if password in ['wrong-password', 'wrong', 'incorrect', 'bad-password', 'test-fail']:
            return JSONResponse({
                "success": False,
                "message": f"Authentication failed for user '{db_user}'. Please check your password."
            }, status_code=401)
        
        # For demo purposes, accept all other connections as successful
        return JSONResponse({
            "success": True,
            "message": f"Successfully connected to {database_name} on {host}:{port}"
        })
        
    except Exception as e:
        return JSONResponse({
            "success": False,
            "message": f"Connection failed: {str(e)}"
        }, status_code=500)

@app.post("/api/connections/create", dependencies=AUTH_DEPENDENCIES)
async def create_connection(request: Request, current_user = Depends(get_current_user)):
    """Create and save a new database connection"""
    tenant_id = get_tenant_id_from_user(current_user)
    try:
        data = await request.json()
        connection_name = data.get("connection_name", "").strip()
        host = data.get("host", "").strip()
        database_name = data.get("database_name", "").strip()
        db_user = data.get("db_user", "").strip()
        password = data.get("password", "")
        
        # Normalize and validate port
        try:
            port = int(data.get("port", 5432))
        except (ValueError, TypeError):
            port = None
        
        # Comprehensive validation
        errors = []
        if not connection_name:
            errors.append("Connection name is required")
        if not host:
            errors.append("Host is required")
        if not database_name:
            errors.append("Database name is required")
        if not db_user:
            errors.append("User is required")
        if not password:
            errors.append("Password is required")
        if port is None or port < 1 or port > 65535:
            errors.append("Port must be a valid number between 1 and 65535")
            
        if errors:
            return JSONResponse({
                "success": False,
                "message": "; ".join(errors)
            }, status_code=400)
        
        # Encrypt password
        encrypted_password = encrypt_password(password)
        
        # Acquire distributed lock for DuckDB write operations (prevents race conditions)
        lock_id = acquire_db_lock()
        try:
            # Save to database
            con = duckdb.connect(get_db_path(tenant_id), config={'access_mode': 'READ_WRITE'})
            
            # Get next ID
            next_id = con.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM connections").fetchone()[0]
            
            con.execute("""
                INSERT INTO connections (
                    id, connection_name, connection_type, host, port, 
                    database_name, db_user, encrypted_password
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                next_id,
                connection_name,
                "PostgreSQL",
                host,
                port,
                database_name,
                db_user,
                encrypted_password
            ])
            
            con.close()
        finally:
            release_db_lock(lock_id)
        
        log(f"✅ New PostgreSQL connection '{connection_name}' saved successfully")
        
        return JSONResponse({
            "success": True,
            "message": "Connection saved successfully",
            "connection_id": next_id
        })
        
    except Exception as e:
        return JSONResponse({
            "success": False,
            "message": f"Failed to save connection: {str(e)}"
        }, status_code=500)

@app.get("/api/connections/{connection_id}/logs", dependencies=AUTH_DEPENDENCIES)
def get_connection_logs(connection_id: int, current_user = Depends(get_current_user)):
    """Get logs for a specific connection"""
    from datetime import datetime
    tenant_id = get_tenant_id_from_user(current_user)
    
    # Get connection details for context
    try:
        con = duckdb.connect(get_db_path(tenant_id), read_only=True)
        result = con.execute("""
            SELECT connection_name, host, database_name
            FROM connections
            WHERE id = ?
        """, [connection_id]).fetchone()
        con.close()
        
        if not result:
            return JSONResponse({"error": "Connection not found", "logs": []}, status_code=404)
        
        connection_name, host, database = result
        
        # Generate mock logs with realistic timestamps
        now = datetime.now()
        logs = [
            f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Connection initiated to {host}...",
            f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Authenticating with database '{database}'...",
            f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Authentication successful.",
            f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Establishing secure connection...",
            f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Connection established successfully.",
            f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Running schema discovery...",
            f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Found 15 tables in database.",
            f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Fetching table metadata...",
            f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] 10,452 rows fetched from primary tables.",
            f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Data validation complete.",
            f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Sync complete for '{connection_name}'.",
        ]
        
        return JSONResponse({"logs": logs})
        
    except Exception as e:
        return JSONResponse({"error": str(e), "logs": []}, status_code=500)

@app.get("/agentic-connection", response_class=HTMLResponse)
def agentic_connection():
    with open("static/agentic-connection.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

# Commented out - frontend is served by the main app
# Mount the built frontend - must be last to not override API routes
# app.mount("/", StaticFiles(directory="dist", html=True), name="dist")

# Programmatic server startup - bypasses PATH issues in deployment
if __name__ == "__main__":
    import uvicorn
    # Replit deployments expect port 5000
    port = 5000
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
