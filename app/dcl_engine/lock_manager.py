"""
Redis lock and state management for DCL Engine.
Provides distributed locking for DuckDB access and manages dev mode state.
"""
import os
import time
import logging
import redis
from typing import Optional


logger = logging.getLogger(__name__)

# Redis keys
DB_LOCK_KEY = "dcl:duckdb:lock"
DB_LOCK_TIMEOUT = 30  # seconds
DEV_MODE_KEY = "dcl:dev_mode"  # Redis key for cross-process dev mode state
LLM_CALLS_KEY = "dcl:llm:calls"  # Redis key for LLM call counter
LLM_TOKENS_KEY = "dcl:llm:tokens"  # Redis key for LLM token counter
LLM_CALLS_SAVED_KEY = "dcl:llm:calls_saved"  # Redis key for LLM calls saved via RAG
DCL_STATE_CHANNEL = "dcl:state:updates"  # Redis pub/sub channel for state broadcasts


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


class LockManager:
    """
    Manages distributed locks and state using Redis.
    Provides thread-safe access to DuckDB and manages dev mode state.
    """

    def __init__(self):
        self.redis_client: Optional[RedisDecodeWrapper] = None
        self.redis_available = False
        self.in_memory_dev_mode = False
        self._dev_mode_initialized = False
        self.LLM_CALLS = 0
        self.LLM_TOKENS = 0

    def set_redis_client(self, client):
        """
        Set the shared Redis client from main app.
        This avoids creating multiple Redis connections and hitting Upstash connection limits.

        Args:
            client: Redis client instance from main app (typically with decode_responses=False)
        """
        # Wrap the client to provide decode_responses=True behavior
        self.redis_client = RedisDecodeWrapper(client)
        self.redis_available = client is not None

        if self.redis_available:
            logger.info(f"✅ DCL Engine: Using shared Redis client from main app")

            # Initialize dev_mode now that we have a Redis client
            try:
                default_mode = "false"  # Default to Prod Mode
                self.redis_client.set(DEV_MODE_KEY, default_mode)
                self._dev_mode_initialized = True
                logger.info(f"🚀 DCL Engine: Initialized dev_mode = {default_mode} (Prod Mode) in Redis")
            except Exception as e:
                logger.warning(f"⚠️ DCL Engine: Failed to initialize dev_mode: {e}, using in-memory fallback")
                self.in_memory_dev_mode = False
                self._dev_mode_initialized = True
        else:
            logger.warning(f"⚠️ DCL Engine: No Redis client provided, using in-memory state")
            self.in_memory_dev_mode = False
            self._dev_mode_initialized = True

    def acquire_db_lock(self, timeout=None):
        """Acquire distributed lock for DuckDB access using Redis (cross-process safe)"""
        if not self.redis_available or not self.redis_client:
            # No-op in single-process mode
            return f"local-{os.getpid()}-{time.time()}"

        if timeout is None:
            timeout = DB_LOCK_TIMEOUT
        lock_id = f"{os.getpid()}-{time.time()}"
        end_time = time.time() + timeout

        while time.time() < end_time:
            try:
                # Try to acquire lock with auto-expiry (prevents deadlocks if process crashes)
                if self.redis_client.set(DB_LOCK_KEY, lock_id, nx=True, ex=timeout):
                    return lock_id
            except (redis.RedisError, redis.ConnectionError, AttributeError) as e:
                # Redis failed, fall back to local lock
                logger.warning(f"Redis lock acquisition failed: {e}. Using local lock.", exc_info=True)
                return f"local-{os.getpid()}-{time.time()}"
            time.sleep(0.05)  # Wait 50ms before retrying

        raise TimeoutError(f"Could not acquire DuckDB lock after {timeout} seconds")

    def release_db_lock(self, lock_id):
        """Release distributed lock for DuckDB access"""
        if not self.redis_available or not self.redis_client:
            return  # No-op in single-process mode

        try:
            # Only release if we still own the lock (prevents releasing someone else's lock)
            current_lock = self.redis_client.get(DB_LOCK_KEY)
            if current_lock == lock_id:
                self.redis_client.delete(DB_LOCK_KEY)
        except Exception:
            pass  # Silently ignore lock release errors

    def get_dev_mode(self) -> bool:
        """Get dev mode state from Redis (cross-process safe)"""
        if not self.redis_available or not self.redis_client:
            return self.in_memory_dev_mode

        try:
            value = self.redis_client.get(DEV_MODE_KEY)
            result = value == "true" if value else False
            return result
        except Exception as e:
            logger.warning(f"⚠️ Error reading dev mode from Redis: {e}")
            return False

    def set_dev_mode(self, enabled: bool):
        """Set dev mode state in Redis (cross-process safe)"""
        if not self.redis_available or not self.redis_client:
            self.in_memory_dev_mode = enabled
            return

        try:
            value = "true" if enabled else "false"
            self.redis_client.set(DEV_MODE_KEY, value)
        except Exception:
            # Fallback to in-memory
            self.in_memory_dev_mode = enabled

    def get_llm_stats(self) -> dict:
        """Get LLM stats from Redis (cross-process safe, persists across restarts)"""
        if not self.redis_available or not self.redis_client:
            return {"calls": self.LLM_CALLS, "tokens": self.LLM_TOKENS, "calls_saved": 0}

        try:
            calls = self.redis_client.get(LLM_CALLS_KEY)
            tokens = self.redis_client.get(LLM_TOKENS_KEY)
            calls_saved = self.redis_client.get(LLM_CALLS_SAVED_KEY)
            return {
                "calls": int(calls) if calls else 0,
                "tokens": int(tokens) if tokens else 0,
                "calls_saved": int(calls_saved) if calls_saved else 0
            }
        except Exception as e:
            logger.warning(f"⚠️ Error reading LLM stats from Redis: {e}")
            return {"calls": self.LLM_CALLS, "tokens": self.LLM_TOKENS, "calls_saved": 0}

    def increment_llm_calls(self, tokens: int = 0):
        """Increment LLM call counter in Redis (cross-process safe, persists across restarts)"""
        if not self.redis_available or not self.redis_client:
            self.LLM_CALLS += 1
            self.LLM_TOKENS += tokens
            return

        try:
            self.redis_client.incr(LLM_CALLS_KEY)
            if tokens > 0:
                self.redis_client.incrby(LLM_TOKENS_KEY, tokens)
        except Exception as e:
            logger.warning(f"⚠️ Error incrementing LLM stats in Redis: {e}")
            self.LLM_CALLS += 1
            self.LLM_TOKENS += tokens

    def increment_llm_calls_saved(self):
        """Increment LLM calls saved counter in Redis (cross-process safe, persists across restarts)"""
        if not self.redis_available or not self.redis_client:
            return

        try:
            self.redis_client.incr(LLM_CALLS_SAVED_KEY)
        except Exception as e:
            logger.warning(f"⚠️ Error incrementing LLM calls saved in Redis: {e}")

    def reset_llm_stats(self):
        """Reset LLM stats in Redis (cross-process safe)"""
        if not self.redis_available or not self.redis_client:
            self.LLM_CALLS = 0
            self.LLM_TOKENS = 0
            return

        try:
            self.redis_client.set(LLM_CALLS_KEY, "0")
            self.redis_client.set(LLM_TOKENS_KEY, "0")
            self.redis_client.set(LLM_CALLS_SAVED_KEY, "0")
        except Exception as e:
            logger.warning(f"⚠️ Error resetting LLM stats in Redis: {e}")
            self.LLM_CALLS = 0
            self.LLM_TOKENS = 0


# Global instance for backward compatibility
lock_manager = LockManager()
