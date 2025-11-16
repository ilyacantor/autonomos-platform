"""
Redis Distributed Lock for DCL Engine State Synchronization

Provides production-grade distributed locking using Redis SETNX mechanism.
Supports both synchronous and asynchronous contexts, enabling safe concurrent
access to DCL graph state and DuckDB operations across multiple workers.

Key Features:
- Cross-process synchronization via Redis
- Automatic lock expiry (prevents deadlocks)
- Retry logic with exponential backoff
- Works for both sync and async code paths
- Single lock replaces dual STATE_LOCK + ASYNC_STATE_LOCK

Architecture Decision:
    Replace uncoordinated in-memory locks (threading.Lock + asyncio.Lock)
    with single Redis distributed lock that synchronizes across all workers.
    
    Before (Race Condition Risk):
        sync code   → threading.Lock()   ╳ NOT coordinated
        async code  → asyncio.Lock()     ╳ 
    
    After (Production Safe):
        sync code   → RedisDistributedLock   ✓ Coordinated via Redis
        async code  → RedisDistributedLock   ✓

Usage:
    # Synchronous context (e.g., add_graph_nodes_for_source)
    with dcl_distributed_lock.acquire(timeout=5.0):
        state_access.set_graph_state(tenant_id, updated_graph)
    
    # Asynchronous context (e.g., ingest_source)
    async with dcl_distributed_lock.acquire_async(timeout=5.0):
        state_access.set_source_schemas(tenant_id, schemas)
"""

import asyncio
import time
import logging
from typing import Optional
from contextlib import contextmanager, asynccontextmanager

logger = logging.getLogger(__name__)


class RedisDistributedLock:
    """
    Production-grade distributed lock using Redis SETNX mechanism.
    
    This lock ensures safe concurrent access to DCL state and DuckDB across
    multiple processes/workers. It replaces the brittle dual-lock system
    (STATE_LOCK + ASYNC_STATE_LOCK) with a single coordinated lock.
    
    Implementation:
        - Uses Redis SET with NX (Not eXists) option for atomic acquisition
        - Automatic expiry prevents deadlocks if holder crashes
        - Retry logic with exponential backoff for lock contention
        - Works seamlessly for both sync and async code
    
    Lock Key Pattern:
        dcl:lock:state_access
    
    Safety Features:
        - Lock expiry (default 30s) prevents deadlocks
        - Unique lock token prevents accidental release by other processes
        - Graceful degradation if Redis unavailable (logs warning, continues)
    
    Example:
        lock = RedisDistributedLock(redis_client, lock_key="dcl:lock:state_access")
        
        # Sync usage
        with lock.acquire(timeout=5.0):
            # Critical section - guaranteed exclusive access
            update_graph_state()
        
        # Async usage
        async with lock.acquire_async(timeout=5.0):
            # Critical section - guaranteed exclusive access
            await update_graph_state()
    """
    
    def __init__(
        self,
        redis_client,
        lock_key: str = "dcl:lock:state_access",
        lock_ttl: int = 30,
        retry_interval: float = 0.1,
        max_retries: int = 50
    ):
        """
        Initialize distributed lock.
        
        Args:
            redis_client: Redis client instance (can be None for graceful degradation)
            lock_key: Redis key for the lock (default: "dcl:lock:state_access")
            lock_ttl: Lock expiry in seconds (default: 30s, prevents deadlocks)
            retry_interval: Initial retry delay in seconds (default: 0.1s)
            max_retries: Maximum retry attempts (default: 50, total ~5s)
        """
        self.redis = redis_client
        self.redis_available = redis_client is not None
        self.lock_key = lock_key
        self.lock_ttl = lock_ttl
        self.retry_interval = retry_interval
        self.max_retries = max_retries
    
    @contextmanager
    def acquire(self, timeout: float = 5.0):
        """
        Acquire lock in synchronous context.
        
        Args:
            timeout: Maximum wait time in seconds (default: 5.0s)
        
        Yields:
            None (context manager)
        
        Raises:
            TimeoutError: If lock not acquired within timeout
        
        Example:
            with lock.acquire(timeout=5.0):
                # Critical section - safe concurrent access
                update_graph_state()
        """
        if not self.redis_available:
            logger.warning(
                f"⚠️ RedisDistributedLock: Redis unavailable, lock disabled (graceful degradation)"
            )
            yield  # Continue without locking (development fallback)
            return
        
        lock_token = f"{time.time()}_{id(self)}"  # Unique token for this lock holder
        acquired = False
        start_time = time.time()
        retry_delay = self.retry_interval
        
        try:
            # Attempt to acquire lock with retry logic
            for attempt in range(self.max_retries):
                # Redis SET with NX (Not eXists) option - atomic test-and-set
                acquired = self.redis.set(
                    self.lock_key,
                    lock_token,
                    nx=True,  # Only set if key does not exist
                    ex=self.lock_ttl  # Automatic expiry after TTL seconds
                )
                
                if acquired:
                    logger.debug(
                        f"🔒 RedisDistributedLock acquired: {self.lock_key} "
                        f"(attempt {attempt + 1}, token={lock_token[:16]}...)"
                    )
                    break
                
                # Lock held by another process - check timeout
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    raise TimeoutError(
                        f"Failed to acquire lock {self.lock_key} after {timeout}s "
                        f"({attempt + 1} attempts). Lock held by another process."
                    )
                
                # Exponential backoff (capped at 1s)
                time.sleep(min(retry_delay, 1.0))
                retry_delay *= 1.5
            
            if not acquired:
                raise TimeoutError(
                    f"Failed to acquire lock {self.lock_key} after {self.max_retries} retries"
                )
            
            # Critical section - lock is held
            yield
        
        finally:
            # Release lock if we acquired it
            if acquired:
                try:
                    # Atomic compare-and-delete using Lua script (byte-safe, no race conditions)
                    # This ensures we only release the lock if we still own it
                    if self.redis.compare_and_delete(self.lock_key, lock_token):
                        logger.debug(
                            f"🔓 RedisDistributedLock released: {self.lock_key}"
                        )
                    else:
                        logger.warning(
                            f"⚠️ Lock token mismatch or lock expired for {self.lock_key}"
                        )
                except Exception as e:
                    logger.error(
                        f"❌ RedisDistributedLock release failed for {self.lock_key}: {e}"
                    )
    
    @asynccontextmanager
    async def acquire_async(self, timeout: float = 5.0):
        """
        Acquire lock in asynchronous context.
        
        Args:
            timeout: Maximum wait time in seconds (default: 5.0s)
        
        Yields:
            None (async context manager)
        
        Raises:
            TimeoutError: If lock not acquired within timeout
        
        Example:
            async with lock.acquire_async(timeout=5.0):
                # Critical section - safe concurrent access
                await update_graph_state_async()
        """
        if not self.redis_available:
            logger.warning(
                f"⚠️ RedisDistributedLock: Redis unavailable, lock disabled (graceful degradation)"
            )
            yield  # Continue without locking (development fallback)
            return
        
        lock_token = f"{time.time()}_{id(self)}"  # Unique token for this lock holder
        acquired = False
        start_time = time.time()
        retry_delay = self.retry_interval
        
        try:
            # Attempt to acquire lock with retry logic
            for attempt in range(self.max_retries):
                # Redis SET with NX (Not eXists) option - atomic test-and-set
                acquired = self.redis.set(
                    self.lock_key,
                    lock_token,
                    nx=True,  # Only set if key does not exist
                    ex=self.lock_ttl  # Automatic expiry after TTL seconds
                )
                
                if acquired:
                    logger.debug(
                        f"🔒 RedisDistributedLock acquired (async): {self.lock_key} "
                        f"(attempt {attempt + 1}, token={lock_token[:16]}...)"
                    )
                    break
                
                # Lock held by another process - check timeout
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    raise TimeoutError(
                        f"Failed to acquire lock {self.lock_key} after {timeout}s "
                        f"({attempt + 1} attempts). Lock held by another process."
                    )
                
                # Exponential backoff (capped at 1s) - use asyncio.sleep for async contexts
                await asyncio.sleep(min(retry_delay, 1.0))
                retry_delay *= 1.5
            
            if not acquired:
                raise TimeoutError(
                    f"Failed to acquire lock {self.lock_key} after {self.max_retries} retries"
                )
            
            # Critical section - lock is held
            yield
        
        finally:
            # Release lock if we acquired it
            if acquired:
                try:
                    # Atomic compare-and-delete using Lua script (byte-safe, no race conditions)
                    # This ensures we only release the lock if we still own it
                    if self.redis.compare_and_delete(self.lock_key, lock_token):
                        logger.debug(
                            f"🔓 RedisDistributedLock released (async): {self.lock_key}"
                        )
                    else:
                        logger.warning(
                            f"⚠️ Lock token mismatch or lock expired (async) for {self.lock_key}"
                        )
                except Exception as e:
                    logger.error(
                        f"❌ RedisDistributedLock release failed for {self.lock_key}: {e}"
                    )
