"""
State management and WebSocket broadcasting for DCL Engine.
Manages global state, event logging, and real-time updates to clients.
"""
import os
import time
import json
import asyncio
import logging
import threading
import duckdb
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import WebSocket

from .utils import DB_PATH, load_ontology, load_agents_config
from .lock_manager import lock_manager
from app.config.feature_flags import FeatureFlagConfig, FeatureFlag


logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and broadcasting."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"🔌 WebSocket client connected ({len(self.active_connections)} active)")

    def disconnect(self, websocket: WebSocket):
        """Unregister a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"🔌 WebSocket client disconnected ({len(self.active_connections)} active)")

    async def broadcast(self, message: dict):
        """Broadcast message to all connected WebSocket clients"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                # Client disconnected - mark for removal
                disconnected.append(connection)

        # Remove disconnected clients
        for connection in disconnected:
            if connection in self.active_connections:
                self.active_connections.remove(connection)


class StateManager:
    """
    Manages global DCL state including graph, sources, events, and RAG context.
    Provides thread-safe access and WebSocket broadcasting.
    """

    def __init__(self):
        # Event log for UI feedback
        self.EVENT_LOG: List[str] = []

        # Graph state
        self.GRAPH_STATE = {"nodes": [], "edges": [], "confidence": None, "last_updated": None}

        # Source tracking
        self.SOURCES_ADDED: List[str] = []
        self.ENTITY_SOURCES: Dict[str, List[str]] = {}
        self.SOURCE_SCHEMAS: Dict[str, Dict[str, Any]] = {}

        # Agent tracking
        self.SELECTED_AGENTS: List[str] = []
        self.AGENT_RESULTS_CACHE: Dict[str, Dict] = {}  # tenant_id -> {agent_id -> results}

        # RAG context
        self.RAG_CONTEXT = {"retrievals": [], "total_mappings": 0, "last_retrieval_count": 0}

        # Feature flags
        self.AUTO_INGEST_UNMAPPED = False

        # Configuration
        self.ontology = None
        self.agents_config = None
        self.agent_executor: Optional[Any] = None
        self.rag_engine: Optional[Any] = None

        # Thread locks
        self.STATE_LOCK = threading.Lock()  # Lock for thread-safe global state updates (sync contexts)
        self.ASYNC_STATE_LOCK = None  # Will be initialized as asyncio.Lock in async contexts

        # Performance timing storage
        self.TIMING_LOG: Dict[str, List[float]] = {
            "llm_propose_total": [],
            "rag_retrieval": [],
            "gemini_call": [],
            "connect_total": []
        }

        # WebSocket manager
        self.ws_manager = ConnectionManager()

    def log(self, msg: str):
        """Log a message to both logger and event log."""
        logger.info(msg)
        if not self.EVENT_LOG or self.EVENT_LOG[-1] != msg:
            self.EVENT_LOG.append(msg)
        if len(self.EVENT_LOG) > 50:
            self.EVENT_LOG.pop(0)

    def reset_state(self, exclude_dev_mode=True):
        """
        Reset DCL state for idempotent /connect operations.
        By default, preserves dev_mode setting and LLM counters across resets.

        Args:
            exclude_dev_mode: If True, dev_mode persists across resets

        Note: LLM counters (calls/tokens) persist across all runs for telemetry tracking,
              similar to "elapsed time until next run". Use reset_llm_stats() endpoint to manually reset.
        """
        self.EVENT_LOG = []
        self.GRAPH_STATE = {"nodes": [], "edges": [], "confidence": None, "last_updated": None}
        self.SOURCES_ADDED = []
        self.ENTITY_SOURCES = {}
        self.SELECTED_AGENTS = []
        self.SOURCE_SCHEMAS = {}
        # LLM stats persist across runs for cumulative tracking (removed reset_llm_stats call)
        # Clear RAG retrievals so they update with fresh data on each connection
        self.RAG_CONTEXT["retrievals"] = []
        self.RAG_CONTEXT["last_retrieval_count"] = 0
        # NOTE: Dev mode and total_mappings are preserved - they persist across connection rebuilds
        self.ontology = load_ontology()
        try:
            os.remove(DB_PATH)
        except FileNotFoundError:
            pass
        self.log("🔄 DCL state cleared (dev_mode preserved). Ready for new connection.")

    async def broadcast_state_change(self, event_type: str = "state_update"):
        """
        Broadcast DCL state changes to WebSocket clients and Redis pub/sub.
        This eliminates polling by pushing updates when state changes.
        """
        try:
            # Update total mappings count from RAG engine
            if self.rag_engine:
                try:
                    stats = self.rag_engine.get_stats()
                    self.RAG_CONTEXT["total_mappings"] = stats.get("total_mappings", 0)
                except Exception as e:
                    logger.warning(f"Failed to get RAG stats: {e}")

            # Include agent consumption metadata
            if not self.agents_config:
                self.agents_config = load_agents_config()

            agent_consumption = {}
            for agent_id, agent_info in self.agents_config.get("agents", {}).items():
                agent_consumption[agent_id] = agent_info.get("consumes", [])

            # Filter graph edges for Sankey rendering - exclude join edges to prevent circular references
            filtered_graph = {
                "nodes": self.GRAPH_STATE["nodes"],
                "edges": [
                    edge for edge in self.GRAPH_STATE["edges"]
                    if edge.get("type") != "join"  # Only keep hierarchy and dataflow edges
                ]
            }

            # Get LLM stats from Redis (includes calls_saved)
            llm_stats = lock_manager.get_llm_stats()

            # Calculate blended confidence
            blended_confidence = self.GRAPH_STATE.get("confidence")

            # Determine source mode from feature flag
            source_mode = "aam_connectors" if FeatureFlagConfig.is_enabled(FeatureFlag.USE_AAM_AS_SOURCE) else "demo_files"

            # Send complete data (frontend has scrolling for unlimited display)
            state_payload = {
                "type": event_type,
                "timestamp": time.time(),
                "data": {
                    "sources": self.SOURCES_ADDED,
                    "agents": self.SELECTED_AGENTS,
                    "devMode": lock_manager.get_dev_mode(),
                    "sourceMode": source_mode,
                    "graph": filtered_graph,  # Send filtered graph instead of raw GRAPH_STATE
                    "llmCalls": llm_stats["calls"],
                    "llmTokens": llm_stats["tokens"],
                    "llmCallsSaved": llm_stats["calls_saved"],
                    "ragContext": {
                        "total_mappings": self.RAG_CONTEXT.get("total_mappings", 0),
                        "last_retrieval_count": self.RAG_CONTEXT.get("last_retrieval_count", 0),
                        "mappings_retrieved": self.RAG_CONTEXT.get("last_retrieval_count", 0),
                        "retrievals": self.RAG_CONTEXT.get("retrievals", [])  # All retrievals (no limit)
                    },
                    "blendedConfidence": blended_confidence,
                    "events": self.EVENT_LOG,  # All events (no limit - frontend has scrolling)
                    "entitySources": self.ENTITY_SOURCES,
                    "agentConsumption": agent_consumption
                }
            }

            # Debug log to verify events are included
            self.log(f"📡 Broadcasting {event_type}: {len(self.EVENT_LOG)} events, {len(self.SOURCES_ADDED)} sources, {self.RAG_CONTEXT.get('total_mappings', 0)} RAG mappings")

            # Broadcast to WebSocket clients
            await self.ws_manager.broadcast(state_payload)

            # Publish to Redis pub/sub for cross-process broadcast (if available)
            if lock_manager.redis_available and lock_manager.redis_client:
                try:
                    # Note: Redis publish requires bytes, not RedisDecodeWrapper methods
                    lock_manager.redis_client._client.publish(
                        lock_manager.DCL_STATE_CHANNEL.encode(),
                        json.dumps(state_payload).encode()
                    )
                except Exception as e:
                    logger.warning(f"Failed to publish state to Redis pub/sub: {e}")

        except Exception as e:
            self.log(f"⚠️ Error broadcasting state change: {e}")

    def save_graph_state(self):
        """
        Persist GRAPH_STATE to DuckDB for state recovery across restarts.
        Creates a graph_state table if it doesn't exist and stores the current state.
        """
        try:
            # Only save if there are nodes (skip empty state saves)
            if not self.GRAPH_STATE.get("nodes"):
                logger.debug("Skipping graph state save - no nodes present")
                return

            lock_id = lock_manager.acquire_db_lock()
            try:
                con = duckdb.connect(DB_PATH, config={'access_mode': 'READ_WRITE'})

                # Create table if it doesn't exist
                con.execute("""
                    CREATE TABLE IF NOT EXISTS dcl_graph_state (
                        id INTEGER PRIMARY KEY,
                        state_json TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Serialize graph state to JSON
                state_json = json.dumps(self.GRAPH_STATE)

                # Upsert the state (always keep only the latest state)
                con.execute("""
                    INSERT OR REPLACE INTO dcl_graph_state (id, state_json, updated_at)
                    VALUES (1, ?, CURRENT_TIMESTAMP)
                """, [state_json])

                con.close()
                logger.info(f"✅ Graph state persisted ({len(self.GRAPH_STATE['nodes'])} nodes, {len(self.GRAPH_STATE['edges'])} edges)")
            finally:
                lock_manager.release_db_lock(lock_id)
        except Exception as e:
            logger.warning(f"⚠️ Failed to save graph state: {e}")

    def restore_graph_state(self):
        """
        Restore GRAPH_STATE from DuckDB on startup.
        If no persisted state exists, keeps the empty initial state.
        """
        try:
            # Check if DB file exists
            if not os.path.exists(DB_PATH):
                logger.info("No persisted DCL database found - starting with empty graph")
                return

            lock_id = lock_manager.acquire_db_lock()
            try:
                con = duckdb.connect(DB_PATH, read_only=True)

                # Check if graph_state table exists
                tables = con.execute("SHOW TABLES").fetchall()
                table_names = [t[0] for t in tables]

                if 'dcl_graph_state' not in table_names:
                    logger.info("No graph state table found - starting with empty graph")
                    con.close()
                    return

                # Fetch the latest state
                result = con.execute("SELECT state_json FROM dcl_graph_state WHERE id = 1").fetchone()
                con.close()

                if result and result[0]:
                    restored_state = json.loads(result[0])
                    self.GRAPH_STATE = restored_state
                    logger.info(f"✅ Graph state restored from database ({len(self.GRAPH_STATE['nodes'])} nodes, {len(self.GRAPH_STATE['edges'])} edges)")
                else:
                    logger.info("No persisted graph state found - starting with empty graph")
            finally:
                lock_manager.release_db_lock(lock_id)
        except Exception as e:
            logger.warning(f"⚠️ Failed to restore graph state: {e} - starting with empty graph")


# Global instance for backward compatibility
state_manager = StateManager()
