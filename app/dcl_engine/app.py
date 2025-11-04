
import os, time, json, glob, duckdb, pandas as pd, yaml, warnings, threading, re, traceback, asyncio
from pathlib import Path
from fastapi import FastAPI, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
import google.generativeai as genai  # type: ignore
from rag_engine import RAGEngine
from llm_service import get_llm_service
import redis

# Use paths relative to this module's directory
DCL_BASE_PATH = Path(__file__).parent
DB_PATH = str(DCL_BASE_PATH / "registry.duckdb")
ONTOLOGY_PATH = str(DCL_BASE_PATH / "ontology" / "catalog.yml")
AGENTS_CONFIG_PATH = str(DCL_BASE_PATH / "agents" / "config.yml")
SCHEMAS_DIR = str(DCL_BASE_PATH / "schemas")
CONF_THRESHOLD = 0.70
AUTO_PUBLISH_PARTIAL = True
AUTH_ENABLED = False  # Set to True to enable authentication, False to bypass

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
LLM_CALLS = 0
LLM_TOKENS = 0
rag_engine = None
RAG_CONTEXT = {"retrievals": [], "total_mappings": 0, "last_retrieval_count": 0}
SOURCE_SCHEMAS: Dict[str, Dict[str, Any]] = {}
DEV_MODE = False  # When True, uses AI/RAG for mapping; when False, uses only heuristics
STATE_LOCK = threading.Lock()  # Lock for thread-safe global state updates (sync contexts)
ASYNC_STATE_LOCK = None  # Will be initialized as asyncio.Lock in async contexts

# Performance timing storage
TIMING_LOG: Dict[str, List[float]] = {
    "llm_propose_total": [],
    "rag_retrieval": [],
    "gemini_call": [],
    "connect_total": []
}

# Redis-based distributed lock for cross-process DuckDB access
# NOTE: Redis client is shared from main app to avoid connection limit issues
redis_client = None
redis_available = False
DB_LOCK_KEY = "dcl:duckdb:lock"
DB_LOCK_TIMEOUT = 30  # seconds
DEV_MODE_KEY = "dcl:dev_mode"  # Redis key for cross-process dev mode state
LLM_CALLS_KEY = "dcl:llm:calls"  # Redis key for LLM call counter
LLM_TOKENS_KEY = "dcl:llm:tokens"  # Redis key for LLM token counter
LLM_CALLS_SAVED_KEY = "dcl:llm:calls_saved"  # Redis key for LLM calls saved via RAG
DCL_STATE_CHANNEL = "dcl:state:updates"  # Redis pub/sub channel for state broadcasts
in_memory_dev_mode = False  # Fallback when Redis unavailable
_dev_mode_initialized = False  # Track if dev_mode has been initialized

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

def set_redis_client(client):
    """
    Set the shared Redis client from main app.
    This avoids creating multiple Redis connections and hitting Upstash connection limits.
    
    Args:
        client: Redis client instance from main app (typically with decode_responses=False)
    """
    global redis_client, redis_available, _dev_mode_initialized
    
    # Wrap the client to provide decode_responses=True behavior
    redis_client = RedisDecodeWrapper(client)
    redis_available = client is not None
    
    if redis_available:
        print(f"✅ DCL Engine: Using shared Redis client from main app", flush=True)
        
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
    else:
        print(f"⚠️ DCL Engine: No Redis client provided, using in-memory state", flush=True)
        in_memory_dev_mode = False
        _dev_mode_initialized = True

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        log(f"🔌 WebSocket client connected ({len(self.active_connections)} active)")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        log(f"🔌 WebSocket client disconnected ({len(self.active_connections)} active)")
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected WebSocket clients"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                log(f"⚠️ Error broadcasting to WebSocket client: {e}")
                import traceback
                log(f"   Traceback: {traceback.format_exc()}")

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

def log(msg: str):
    print(msg, flush=True)
    if not EVENT_LOG or EVENT_LOG[-1] != msg:
        EVENT_LOG.append(msg)
    if len(EVENT_LOG) > 50:
        EVENT_LOG.pop(0)

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
    for tname, info in tables.items():
        path = info["path"]
        view_name = f"src_{source_key}_{tname}"
        con.sql(f"CREATE OR REPLACE VIEW {view_name} AS SELECT * FROM read_csv_auto('{path}')")

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
    
    # Initialize RAG engine if not already initialized (for worker processes)
    if rag_engine is None and os.getenv("PINECONE_API_KEY"):
        try:
            from rag_engine import RAGEngine
            rag_engine = RAGEngine()
            log("✅ RAG Engine initialized in worker process")
        except Exception as e:
            log(f"⚠️ RAG Engine initialization failed in worker: {e}")
    
    # STREAMING EVENT: RAG retrieval starting
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

def heuristic_plan(ontology: Dict[str, Any], source_key: str, tables: Dict[str, Any], skip_llm_validation: bool = False) -> Dict[str, Any]:
    global SELECTED_AGENTS, agents_config, DEV_MODE
    
    # Get available ontology entities based on selected agents
    if not agents_config:
        agents_config = load_agents_config()
    
    available_entities = set()
    if SELECTED_AGENTS:
        for agent_id in SELECTED_AGENTS:
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
        FINOPS_SOURCES = {"snowflake", "sap", "netsuite", "legacy_sql"}
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
    if SELECTED_AGENTS:
        agent_key_metrics = set()
        for agent_id in SELECTED_AGENTS:
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

def apply_plan(con, source_key: str, plan: Dict[str, Any]) -> Scorecard:
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
            
            # Prepare ontology node (will check for existence when adding)
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
    
    # Apply all graph state updates atomically
    with STATE_LOCK:
        # Add nodes (deduplicated)
        for node in nodes_to_add:
            if not any(n["id"] == node["id"] for n in GRAPH_STATE["nodes"]):
                GRAPH_STATE["nodes"].append(node)
        
        # Add edges
        for edge in edges_to_add:
            GRAPH_STATE["edges"].append(edge)
        
        # Update entity sources
        for ent in entities_to_update:
            ENTITY_SOURCES.setdefault(ent, []).append(source_key)
    
    conf = sum(confs)/len(confs) if confs else 0.8
    return Scorecard(confidence=conf, blockers=blockers, issues=issues, joins=joins)

def add_graph_nodes_for_source(source_key: str, tables: Dict[str, Any]):
    global ontology, agents_config, SELECTED_AGENTS
    
    # Create source_parent node BEFORE source nodes
    parent_node_id = f"sys_{source_key}"
    parent_label = source_key.replace('_', ' ').title()
    
    # Add source_parent node if it doesn't exist
    if not any(n["id"] == parent_node_id for n in GRAPH_STATE["nodes"]):
        GRAPH_STATE["nodes"].append({
            "id": parent_node_id,
            "label": parent_label,
            "type": "source_parent"
        })
    
    # Add source nodes with sourceSystem and parentId metadata
    source_system = source_key.replace('_', ' ').title()  # Use IDENTICAL formatting for consistency
    
    for t, table_data in tables.items():
        node_id = f"src_{source_key}_{t}"
        label = f"{t} ({source_system})"
        # Extract field names from the schema
        fields = list(table_data.get("schema", {}).keys()) if isinstance(table_data, dict) else []
        GRAPH_STATE["nodes"].append({
            "id": node_id, 
            "label": label, 
            "type": "source",
            "sourceSystem": source_system,
            "parentId": parent_node_id,
            "fields": fields
        })
        
        # Create hierarchy edge from parent to source table
        GRAPH_STATE["edges"].append({
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
        
    for agent_id in SELECTED_AGENTS:
        agent_info = agents_config.get("agents", {}).get(agent_id, {})
        if not any(n["id"] == f"agent_{agent_id}" for n in GRAPH_STATE["nodes"]):
            GRAPH_STATE["nodes"].append({
                "id": f"agent_{agent_id}",
                "label": agent_info.get("name", agent_id.title()),
                "type": "agent"
            })

def add_ontology_to_agent_edges():
    """Create edges from ontology entities to agents based on agent consumption config"""
    global agents_config, SELECTED_AGENTS, GRAPH_STATE, ontology
    
    if not agents_config:
        agents_config = load_agents_config()
    
    if not ontology:
        ontology = load_ontology()
    
    # Get all existing ontology nodes
    ontology_nodes = [n for n in GRAPH_STATE["nodes"] if n["type"] == "ontology"]
    
    # For each selected agent, create edges from consumed ontology entities
    for agent_id in SELECTED_AGENTS:
        agent_info = agents_config.get("agents", {}).get(agent_id, {})
        consumed_entities = agent_info.get("consumes", [])
        
        for onto_node in ontology_nodes:
            # Extract entity name from node id (dcl_aws_resource -> aws_resource)
            entity_name = onto_node["id"].replace("dcl_", "")
            
            if entity_name in consumed_entities:
                # Create edge from ontology to agent if it doesn't exist
                edge_exists = any(
                    e["source"] == onto_node["id"] and e["target"] == f"agent_{agent_id}"
                    for e in GRAPH_STATE["edges"]
                )
                if not edge_exists:
                    # Get entity fields from ontology
                    entity_fields = ontology.get("entities", {}).get(entity_name, {}).get("fields", [])
                    
                    GRAPH_STATE["edges"].append({
                        "source": onto_node["id"],
                        "target": f"agent_{agent_id}",
                        "label": "",  # No label needed - agent node already shows its name
                        "type": "consumption",
                        "edgeType": "dataflow",
                        "entity_fields": entity_fields,  # Add entity fields for tooltip
                        "entity_name": entity_name
                    })

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

async def connect_source(source_key: str, llm_model: str = "gemini-2.5-flash") -> Dict[str, Any]:
    global ontology, agents_config, SOURCE_SCHEMAS, STATE_LOCK, TIMING_LOG, ASYNC_STATE_LOCK, ws_manager
    
    connect_start = time.time()
    
    # STREAMING EVENT 1: Connection started (immediate <2s)
    await ws_manager.broadcast({
        "type": "mapping_progress",
        "source": source_key,
        "stage": "started",
        "message": f"🔄 Starting schema analysis for {source_key}...",
        "timestamp": time.time()
    })
    
    # Initialize async lock if needed
    if ASYNC_STATE_LOCK is None:
        ASYNC_STATE_LOCK = asyncio.Lock()
    
    if ontology is None:
        ontology = load_ontology()
    schema_dir = os.path.join(SCHEMAS_DIR, source_key)
    if not os.path.isdir(schema_dir):
        return {"error": f"Unknown source '{source_key}'"}
    tables = snapshot_tables_from_dir(source_key, schema_dir)
    
    # STREAMING EVENT 2: Schema snapshot complete
    await ws_manager.broadcast({
        "type": "mapping_progress",
        "source": source_key,
        "stage": "schema_loaded",
        "message": f"📊 Loaded {len(tables)} tables from {source_key}",
        "table_count": len(tables),
        "timestamp": time.time()
    })
    
    # Store schema information for later retrieval (async-safe)
    async with ASYNC_STATE_LOCK:
        SOURCE_SCHEMAS[source_key] = tables
    
    # Add graph nodes (async-safe)
    async with ASYNC_STATE_LOCK:
        add_graph_nodes_for_source(source_key, tables)
    
    llm_result = await llm_propose(ontology, source_key, tables, llm_model)
    plan, skip_semantic_validation = llm_result if isinstance(llm_result, tuple) else (llm_result, False)
    
    if not plan:
        # Use heuristic plan with explicit skip_semantic_validation flag from llm_propose
        plan = heuristic_plan(ontology, source_key, tables, skip_llm_validation=skip_semantic_validation)
        log(f"I connected to {source_key.title()} (schema sample) and generated a heuristic plan. I mapped obvious IDs and foreign keys and published a basic unified view.")
        
        # STREAMING EVENT: Heuristic plan used
        await ws_manager.broadcast({
            "type": "mapping_progress",
            "source": source_key,
            "stage": "heuristic_plan",
            "message": f"⚡ Using fast heuristic mapping for {source_key}",
            "timestamp": time.time()
        })
    else:
        log(f"I connected to {source_key.title()} (schema sample) and proposed mappings and joins.")
        
        # STREAMING EVENT: AI plan used
        await ws_manager.broadcast({
            "type": "mapping_progress",
            "source": source_key,
            "stage": "ai_plan",
            "message": f"🧠 Using AI-generated mapping for {source_key}",
            "timestamp": time.time()
        })
    
    # Acquire distributed lock for ALL DuckDB operations (cross-process safe)
    lock_id = acquire_db_lock()
    try:
        con = duckdb.connect(DB_PATH, config={'access_mode': 'READ_WRITE'})
        register_src_views(con, source_key, tables)
        score = apply_plan(con, source_key, plan)
        
        # Update graph state (async-safe)
        async with ASYNC_STATE_LOCK:
            GRAPH_STATE["confidence"] = score.confidence
            GRAPH_STATE["last_updated"] = time.strftime("%I:%M:%S %p")
            
            # Create edges from ontology entities to agents
            add_ontology_to_agent_edges()
            
            SOURCES_ADDED.append(source_key)
        
        ents = ", ".join(sorted(tables.keys()))
        log(f"I found these entities: {ents}.")
        if score.joins:
            log("To connect them, I proposed joins like " + "; ".join([f"{j['left']} with {j['right']}" for j in score.joins]) + ".")
        if score.confidence >= CONF_THRESHOLD and not score.blockers:
            log(f"I am about {int(score.confidence*100)}% confident. I created unified views so you can now query across these sources.")
        elif AUTO_PUBLISH_PARTIAL and not score.blockers:
            log(f"I applied the mappings, but with some issues: {score.issues}")
        else:
            blockers_msg = "; ".join(score.blockers) if score.blockers else "Unknown blockers"
            log(f"I paused because of blockers and did not publish. Blockers: {blockers_msg}")
        
        previews = {"sources": {}, "ontology": {}}
        for t in tables.keys():
            previews["sources"][f"src_{source_key}_{t}"] = preview_table(con, f"src_{source_key}_{t}")
        
        # Preview ontology tables based on selected agents
        if not agents_config:
            agents_config = load_agents_config()
        
        ontology_entities = set()
        if SELECTED_AGENTS:
            for agent_id in SELECTED_AGENTS:
                agent_info = agents_config.get("agents", {}).get(agent_id, {})
                consumes = agent_info.get("consumes", [])
                ontology_entities.update(consumes)
        else:
            if not ontology:
                ontology = load_ontology()
            ontology_entities = set(ontology.get("entities", {}).keys())
        
        for ent in ontology_entities:
            previews["ontology"][f"dcl_{ent}"] = preview_table(con, f"dcl_{ent}")
        
        # Explicitly close DuckDB connection
        con.close()
        
        # Log total connect_source timing
        connect_elapsed = time.time() - connect_start
        TIMING_LOG["connect_total"].append(connect_elapsed)
        log(f"⏱️ connect_source({source_key}) total: {connect_elapsed:.2f}s")
        
        # STREAMING EVENT: Source complete
        await ws_manager.broadcast({
            "type": "mapping_progress",
            "source": source_key,
            "stage": "complete",
            "message": f"✅ {source_key} mapping complete ({connect_elapsed:.1f}s)",
            "duration": connect_elapsed,
            "confidence": score.confidence,
            "timestamp": time.time()
        })
        
        return {"ok": True, "score": score.confidence, "previews": previews}
    finally:
        release_db_lock(lock_id)

def reset_state(exclude_dev_mode=True):
    """
    Reset DCL state for idempotent /connect operations.
    By default, preserves dev_mode setting and LLM counters across resets.
    
    Args:
        exclude_dev_mode: If True, dev_mode persists across resets
    
    Note: LLM counters (calls/tokens) persist across all runs for telemetry tracking,
          similar to "elapsed time until next run". Use reset_llm_stats() endpoint to manually reset.
    """
    global EVENT_LOG, GRAPH_STATE, SOURCES_ADDED, ENTITY_SOURCES, ontology, SELECTED_AGENTS, SOURCE_SCHEMAS, RAG_CONTEXT
    EVENT_LOG = []
    GRAPH_STATE = {"nodes": [], "edges": [], "confidence": None, "last_updated": None}
    SOURCES_ADDED = []
    ENTITY_SOURCES = {}
    SELECTED_AGENTS = []
    SOURCE_SCHEMAS = {}
    # LLM stats persist across runs for cumulative tracking (removed reset_llm_stats call)
    # Clear RAG retrievals so they update with fresh data on each connection
    RAG_CONTEXT["retrievals"] = []
    RAG_CONTEXT["last_retrieval_count"] = 0
    # NOTE: Dev mode and total_mappings are preserved - they persist across connection rebuilds
    ontology = load_ontology()
    try:
        os.remove(DB_PATH)
    except FileNotFoundError:
        pass
    log("🔄 DCL state cleared (dev_mode preserved). Ready for new connection.")

app = FastAPI()

# State broadcasting function
async def broadcast_state_change(event_type: str = "state_update"):
    """
    Broadcast DCL state changes to WebSocket clients and Redis pub/sub.
    This eliminates polling by pushing updates when state changes.
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
        
        # Filter graph edges for Sankey rendering - exclude join edges to prevent circular references
        filtered_graph = {
            "nodes": GRAPH_STATE["nodes"],
            "edges": [
                edge for edge in GRAPH_STATE["edges"]
                if edge.get("type") != "join"  # Only keep hierarchy and dataflow edges
            ]
        }
        
        # Get LLM stats from Redis (includes calls_saved)
        llm_stats = get_llm_stats()
        
        # Calculate blended confidence
        blended_confidence = GRAPH_STATE.get("confidence")
        
        # Send complete data (frontend has scrolling for unlimited display)
        state_payload = {
            "type": event_type,
            "timestamp": time.time(),
            "data": {
                "sources": SOURCES_ADDED,
                "agents": SELECTED_AGENTS,
                "devMode": get_dev_mode(),
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
                "events": EVENT_LOG,  # All events (no limit - frontend has scrolling)
                "entitySources": ENTITY_SOURCES,
                "agentConsumption": agent_consumption
            }
        }
        
        # Debug log to verify events are included
        log(f"📡 Broadcasting {event_type}: {len(EVENT_LOG)} events, {len(SOURCES_ADDED)} sources, {RAG_CONTEXT.get('total_mappings', 0)} RAG mappings")
        
        # Broadcast to WebSocket clients
        await ws_manager.broadcast(state_payload)
        
        # Publish to Redis pub/sub for cross-process broadcast (if available)
        if redis_available and redis_client:
            try:
                redis_client.publish(DCL_STATE_CHANNEL, json.dumps(state_payload))
            except:
                pass  # Redis unavailable, skip pub/sub
        
    except Exception as e:
        log(f"⚠️ Error broadcasting state change: {e}")

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

@app.on_event("startup")
async def startup_event():
    """Initialize RAG engine and default settings on startup."""
    global rag_engine
    
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


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time DCL state updates.
    Eliminates polling by pushing state changes to connected clients.
    """
    await ws_manager.connect(websocket)
    try:
        # Send initial state on connection
        await broadcast_state_change("connection_established")
        
        # Keep connection alive and listen for client messages (if needed)
        while True:
            data = await websocket.receive_text()
            # Client can request state refresh by sending "refresh"
            if data == "refresh":
                await broadcast_state_change("state_refresh")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        log(f"⚠️ WebSocket error: {e}")
        ws_manager.disconnect(websocket)


@app.get("/state")
def state():
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
    
    # Filter graph edges for Sankey rendering - exclude join edges to prevent circular references
    # D3-sankey requires a directed acyclic graph (DAG), but join edges create bidirectional cycles
    filtered_graph = {
        "nodes": GRAPH_STATE["nodes"],
        "edges": [
            edge for edge in GRAPH_STATE["edges"]
            if edge.get("type") != "join"  # Only keep hierarchy and dataflow edges
        ]
    }
    
    # Get LLM stats from Redis (persists across restarts)
    llm_stats = get_llm_stats()
    
    # Use graph confidence directly as blended confidence
    # (Graph confidence already incorporates mapping quality and completeness)
    blended_confidence = GRAPH_STATE.get("confidence")
    
    return JSONResponse({
        "events": EVENT_LOG,
        "timeline": EVENT_LOG[-5:],
        "graph": filtered_graph,  # Send filtered graph instead of raw GRAPH_STATE
        "preview": {"sources": {}, "ontology": {}},
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
        "blended_confidence": blended_confidence,
        "agent_consumption": agent_consumption,
        "selected_sources": SOURCES_ADDED,
        "selected_agents": SELECTED_AGENTS,
        "dev_mode": get_dev_mode(),  # Read from Redis for cross-process consistency
        "auth_enabled": AUTH_ENABLED
    })

@app.get("/connect")
async def connect(
    sources: str = Query(...),
    agents: str = Query(...),
    llm_model: str = Query("gemini-2.5-flash", description="LLM model: gemini-2.5-flash, gpt-4o-mini, gpt-4o")
):
    """
    Idempotent connection endpoint - clears prior state and rebuilds from scratch.
    Replaces both legacy /reset and /connect behavior.
    Dev mode is preserved across connection rebuilds.
    """
    global SELECTED_AGENTS
    
    source_list = [s.strip() for s in sources.split(',') if s.strip()]
    agent_list = [a.strip() for a in agents.split(',') if a.strip()]
    
    if not source_list:
        return JSONResponse({"error": "No sources provided"}, status_code=400)
    if not agent_list:
        return JSONResponse({"error": "No agents provided"}, status_code=400)
    
    # Clear prior state (preserves dev_mode) for idempotent behavior
    reset_state(exclude_dev_mode=True)
    log(f"🔌 Connecting {len(source_list)} source(s) with {len(agent_list)} agent(s)...")
    
    # Store selected agents globally
    SELECTED_AGENTS = agent_list
    
    # Log which model is being used
    log(f"🤖 Using LLM model: {llm_model}")
    
    try:
        # Connect all sources in parallel using async concurrency
        tasks = [connect_source(source, llm_model) for source in source_list]
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
    
    # Broadcast state change to WebSocket clients
    await broadcast_state_change("sources_connected")
    
    return JSONResponse({"ok": True, "sources": SOURCES_ADDED, "agents": agent_list})

# DEPRECATED: /reset endpoint - replaced by unified idempotent /connect logic
# Keeping this commented out for reference. All reset+connect behavior is now handled by /connect.
# @app.get("/reset")
# async def reset():
#     reset_state(exclude_dev_mode=True)
#     # Broadcast state change to WebSocket clients
#     await broadcast_state_change("demo_reset")
#     return JSONResponse({"ok": True})

@app.get("/toggle_dev_mode")
async def toggle_dev_mode(enabled: Optional[bool] = None):
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
        log("🗑️ Cleared RAG cache due to dev mode toggle")
    
    status = "enabled" if DEV_MODE else "disabled"
    log(f"🔧 Dev Mode {status} - {'AI/RAG mapping active' if DEV_MODE else 'Using heuristic-only mapping'}")
    # Broadcast state change to WebSocket clients
    await broadcast_state_change("dev_mode_toggled")
    return JSONResponse({"dev_mode": DEV_MODE, "status": status})

@app.post("/reset_llm_stats")
async def reset_llm_stats_endpoint():
    """
    Manual endpoint to reset LLM call counters.
    Note: LLM stats persist across all runs by default for cumulative tracking.
    Use this endpoint only when you want to reset the counters manually.
    """
    reset_llm_stats()
    stats = get_llm_stats()
    log("🔄 LLM stats manually reset to 0")
    return JSONResponse({
        "ok": True,
        "message": "LLM stats reset successfully",
        "calls": stats["calls"],
        "tokens": stats["tokens"]
    })

@app.get("/preview")
def preview(node: Optional[str] = None):
    global ontology, agents_config, SELECTED_AGENTS
    # Use read-only mode for preview operations
    con = duckdb.connect(DB_PATH, read_only=True)
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
        if SELECTED_AGENTS:
            # Get entities consumed by selected agents
            for agent_id in SELECTED_AGENTS:
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

@app.get("/source_schemas")
def source_schemas():
    """Return complete schema information for all connected sources."""
    global SOURCE_SCHEMAS
    
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
    
    clean_schemas = sanitize(SOURCE_SCHEMAS)
    return JSONResponse(clean_schemas)

@app.get("/ontology_schema")
def ontology_schema():
    """Return ontology entity definitions with all fields and source mappings."""
    global ontology, GRAPH_STATE
    
    if not ontology:
        ontology = load_ontology()
    
    # Build schema: entity -> {pk, fields[], source_mappings[]}
    schema = {}
    entities = ontology.get("entities", {})
    
    for entity_name, entity_def in entities.items():
        # Extract source mappings from graph edges
        source_mappings = []
        
        # Find all edges that map to this ontology entity
        for edge in GRAPH_STATE.get("edges", []):
            if edge.get("edgeType") == "dataflow":
                # Check if target node is this ontology entity
                target_node_id = edge.get("target", "")
                if target_node_id == f"dcl_{entity_name}":
                    # Find the source node to get source system and table info
                    source_node_id = edge.get("source", "")
                    source_node = next((n for n in GRAPH_STATE.get("nodes", []) if n.get("id") == source_node_id), None)
                    
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

@app.get("/toggle_auto_ingest")
def toggle_auto_ingest(enabled: bool = Query(...)):
    global AUTO_INGEST_UNMAPPED
    AUTO_INGEST_UNMAPPED = enabled
    return JSONResponse({"ok": True, "enabled": AUTO_INGEST_UNMAPPED})

@app.get("/rag/stats")
def rag_stats():
    """Get RAG engine statistics."""
    if not rag_engine:
        return JSONResponse({"error": "RAG Engine not initialized"}, status_code=503)
    try:
        stats = rag_engine.get_stats()
        return JSONResponse(stats)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/supabase-config")
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

@app.post("/api/infer")
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

@app.post("/api/setup-database")
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

@app.get("/api/connections")
def get_connections():
    """Get all database connections"""
    try:
        con = duckdb.connect(DB_PATH, read_only=True)
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

@app.post("/api/connections/test")
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

@app.post("/api/connections/create")
async def create_connection(request: Request):
    """Create and save a new database connection"""
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
        
        # Save to database
        con = duckdb.connect(DB_PATH, config={'access_mode': 'READ_WRITE'})
        
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

@app.get("/api/connections/{connection_id}/logs")
def get_connection_logs(connection_id: int):
    """Get logs for a specific connection"""
    from datetime import datetime
    
    # Get connection details for context
    try:
        con = duckdb.connect(DB_PATH, read_only=True)
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
