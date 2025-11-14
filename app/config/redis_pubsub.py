"""
Production-Ready Redis Pub/Sub Listener for Feature Flags

This module provides a centralized, fault-tolerant pub/sub listener for
cross-worker feature flag cache invalidation with:
- Automatic reconnection with exponential backoff + jitter
- Infinite retry with periodic attempts (never gives up)
- Watchdog for automatic crash recovery
- Thread-safe initialization with asyncio.Lock
- Graceful degradation on Redis failure
- Clear logging for production debugging

Used by both main app and DCL engine to ensure ALL workers receive flag changes.
"""

import asyncio
import json
import logging
import os
import random
from typing import Optional, Callable, Dict, Any
from redis.asyncio import Redis as AsyncRedis

from app.config.feature_flags import FeatureFlagConfig, FeatureFlag

logger = logging.getLogger(__name__)

# Global state for pub/sub listener (with thread-safe lock)
_pubsub_listener_lock = asyncio.Lock()
_pubsub_listener_started = False
_async_redis_client: Optional[AsyncRedis] = None
_listener_task: Optional[asyncio.Task] = None
_watchdog_task: Optional[asyncio.Task] = None
_pubsub_instance = None


async def init_async_redis() -> Optional[AsyncRedis]:
    """
    Initialize async Redis client for non-blocking pub/sub operations.
    
    Returns:
        AsyncRedis client instance or None if Redis URL not available
    """
    import ssl as ssl_module
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        logger.warning("⚠️ REDIS_URL not set - async Redis client unavailable")
        return None
    
    # Convert redis:// to rediss:// for Upstash TLS requirement
    if redis_url.startswith("redis://"):
        redis_url = "rediss://" + redis_url[8:]
        logger.info("🔒 Using TLS/SSL for async Redis connection (rediss:// protocol)")
    
    try:
        # Create async Redis client with decode_responses=True for easier string handling
        # Add SSL parameters for rediss:// connections (Redis Cloud/Upstash)
        # Disable certificate verification for compatibility with managed Redis services
        if redis_url.startswith("rediss://"):
            client = AsyncRedis.from_url(redis_url, decode_responses=True, ssl_cert_reqs=ssl_module.CERT_NONE)
        else:
            client = AsyncRedis.from_url(redis_url, decode_responses=True)
        
        # Test connection
        await client.ping()
        logger.info("✅ Async Redis client initialized for non-blocking pub/sub")
        return client
    except Exception as e:
        logger.warning(f"⚠️ Failed to initialize async Redis client: {e}")
        return None


async def retry_with_backoff(
    func: Callable,
    max_retries: int = 5,
    initial_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    jitter: bool = True
) -> Any:
    """
    Execute a function with exponential backoff retry logic and jitter.
    
    Args:
        func: Async function to execute
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds before first retry
        max_delay: Maximum delay in seconds between retries
        exponential_base: Base for exponential backoff calculation
        jitter: Add random jitter to prevent thundering herd
        
    Returns:
        Result of successful function execution
        
    Raises:
        Exception: Last exception after all retries exhausted
    """
    delay = initial_delay
    last_exception: Optional[Exception] = None
    
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            last_exception = e
            
            if attempt < max_retries - 1:
                actual_delay = delay
                if jitter:
                    actual_delay = delay * (0.5 + random.random())
                
                logger.warning(
                    f"⚠️ Attempt {attempt + 1}/{max_retries} failed: {e}. "
                    f"Retrying in {actual_delay:.1f}s..."
                )
                await asyncio.sleep(actual_delay)
                
                delay = min(delay * exponential_base, max_delay)
            else:
                logger.error(
                    f"❌ All {max_retries} retry attempts failed. Last error: {e}"
                )
    
    if last_exception is None:
        raise RuntimeError(
            f"retry_with_backoff failed but no exception was captured (max_retries={max_retries})"
        )
    
    raise last_exception


async def feature_flag_pubsub_listener(on_flag_change: Optional[Callable] = None):
    """
    Production-ready async pub/sub listener for feature flag changes.
    
    Features:
    - Infinite reconnection with exponential backoff + jitter
    - Non-blocking async operations
    - Graceful error handling
    - Cross-worker cache invalidation
    - Never permanently quits - always attempts to reconnect
    
    Args:
        on_flag_change: Optional callback function(flag_name, flag_value) 
                       called when a flag changes
    """
    global _async_redis_client, _pubsub_instance
    
    if _async_redis_client is None:
        _async_redis_client = await init_async_redis()
    
    if not _async_redis_client:
        logger.warning("⚠️ Async Redis not available - pub/sub listener disabled")
        return
    
    reconnect_attempts = 0
    max_fast_reconnect_attempts = 5
    in_periodic_retry_mode = False
    
    while True:
        try:
            assert _async_redis_client is not None, "Redis client became None unexpectedly"
            
            _pubsub_instance = _async_redis_client.pubsub()
            
            async def subscribe_operation():
                assert _pubsub_instance is not None
                await _pubsub_instance.subscribe(FeatureFlagConfig._pubsub_channel)
            
            await retry_with_backoff(subscribe_operation, max_retries=3, jitter=True)
            
            logger.info(
                f"📡 [ASYNC] Subscribed to {FeatureFlagConfig._pubsub_channel} "
                f"for flag changes"
            )
            logger.info("✅ Pub/sub listener running in NON-BLOCKING mode (production-ready)")
            
            if in_periodic_retry_mode:
                logger.info("✅ Recovered from periodic retry mode - back to normal operation")
                in_periodic_retry_mode = False
            
            reconnect_attempts = 0
            
            async for message in _pubsub_instance.listen():
                try:
                    if message['type'] == 'message':
                        data = message['data']
                        
                        payload = json.loads(data)
                        flag_name = payload.get('flag')
                        flag_value = payload.get('value')
                        
                        logger.info(f"📨 [ASYNC] Received flag change: {flag_name}={flag_value}")
                        
                        if on_flag_change:
                            try:
                                if asyncio.iscoroutinefunction(on_flag_change):
                                    await on_flag_change(flag_name, flag_value)
                                else:
                                    on_flag_change(flag_name, flag_value)
                            except Exception as e:
                                logger.error(f"⚠️ Error in on_flag_change callback: {e}")
                
                except json.JSONDecodeError as e:
                    logger.warning(f"⚠️ Invalid JSON in pub/sub message: {e}")
                except Exception as e:
                    logger.warning(f"⚠️ Error processing pub/sub message: {e}")
        
        except asyncio.CancelledError:
            logger.info("🛑 Pub/sub listener cancelled (shutdown)")
            break
        
        except Exception as e:
            reconnect_attempts += 1
            
            if reconnect_attempts >= max_fast_reconnect_attempts and not in_periodic_retry_mode:
                logger.critical(
                    f"🚨 CRITICAL: Pub/sub listener failed after {max_fast_reconnect_attempts} fast reconnection attempts. "
                    f"Entering PERIODIC RETRY MODE (60s intervals). "
                    f"Feature flag changes will NOT propagate until Redis recovers. "
                    f"Last error: {e}"
                )
                in_periodic_retry_mode = True
            
            if in_periodic_retry_mode:
                base_delay = 60.0
                backoff_delay = base_delay * (0.8 + random.random() * 0.4)
                logger.warning(
                    f"⚠️ [PERIODIC RETRY {reconnect_attempts}] Reconnecting in {backoff_delay:.1f}s... (Error: {e})"
                )
            else:
                base_delay = min(2 ** reconnect_attempts, 30)
                backoff_delay = base_delay * (0.5 + random.random())
                logger.error(
                    f"⚠️ Pub/sub listener crashed (attempt {reconnect_attempts}/{max_fast_reconnect_attempts}): {e}"
                )
                logger.info(f"🔄 Reconnecting in {backoff_delay:.1f}s...")
            
            await asyncio.sleep(backoff_delay)
            
            try:
                if _async_redis_client:
                    await _async_redis_client.close()
                _async_redis_client = await init_async_redis()
                
                if not _async_redis_client:
                    logger.error("❌ Failed to reconnect to Redis - will retry")
                    
            except Exception as reconnect_error:
                logger.error(f"❌ Redis reconnection failed: {reconnect_error} - will retry")
    
    if _pubsub_instance:
        try:
            await _pubsub_instance.close()
            logger.info("✅ Pub/sub instance closed")
        except Exception as cleanup_error:
            logger.warning(f"⚠️ Error closing pub/sub instance: {cleanup_error}")
    
    if _async_redis_client:
        try:
            await _async_redis_client.close()
            logger.info("✅ Pub/sub listener cleaned up successfully")
        except Exception as cleanup_error:
            logger.warning(f"⚠️ Error during pub/sub cleanup: {cleanup_error}")


async def listener_watchdog(on_flag_change: Optional[Callable] = None):
    """
    Watchdog task that monitors the listener and restarts it if it crashes.
    
    This ensures the listener is always running, even if it crashes unexpectedly.
    Runs indefinitely until cancelled.
    
    Args:
        on_flag_change: Callback to pass to restarted listener
    """
    global _listener_task
    
    logger.info("🐕 Listener watchdog started")
    
    while True:
        try:
            if _listener_task is None or _listener_task.done():
                if _listener_task and _listener_task.done():
                    try:
                        _listener_task.result()
                    except Exception as e:
                        logger.error(f"🚨 Listener task crashed: {e}")
                
                logger.warning("🔄 Watchdog restarting crashed listener...")
                _listener_task = asyncio.create_task(
                    feature_flag_pubsub_listener(on_flag_change),
                    name="feature_flag_pubsub_listener"
                )
                logger.info("✅ Watchdog restarted listener task")
            
            await asyncio.sleep(10)
        
        except asyncio.CancelledError:
            logger.info("🛑 Watchdog cancelled (shutdown)")
            break
        except Exception as e:
            logger.error(f"⚠️ Watchdog error: {e} - continuing...")
            await asyncio.sleep(5)


async def ensure_pubsub_listener(on_flag_change: Optional[Callable] = None):
    """
    Ensure the pub/sub listener is started (singleton pattern with lock).
    Safe to call multiple times - only starts once per worker.
    Uses asyncio.Lock to prevent race conditions.
    
    Args:
        on_flag_change: Optional callback function(flag_name, flag_value)
                       called when a flag changes
    """
    global _pubsub_listener_started, _listener_task, _watchdog_task
    
    async with _pubsub_listener_lock:
        if _pubsub_listener_started:
            logger.debug("📡 Pub/sub listener already started (singleton)")
            return
        
        _pubsub_listener_started = True
        
        _listener_task = asyncio.create_task(
            feature_flag_pubsub_listener(on_flag_change),
            name="feature_flag_pubsub_listener"
        )
        
        _watchdog_task = asyncio.create_task(
            listener_watchdog(on_flag_change),
            name="listener_watchdog"
        )
        
        logger.info("📡 Feature flag pub/sub listener + watchdog started (singleton, locked)")


async def stop_pubsub_listener():
    """
    Stop the pub/sub listener and watchdog gracefully during shutdown.
    
    Features:
    - Cancels tasks with timeout
    - Closes pubsub connection cleanly
    - Comprehensive error handling
    - Detailed shutdown logging
    """
    global _pubsub_listener_started, _listener_task, _watchdog_task, _async_redis_client, _pubsub_instance
    
    logger.info("🛑 Initiating graceful pub/sub shutdown...")
    
    if _watchdog_task:
        logger.info("🛑 Stopping watchdog...")
        _watchdog_task.cancel()
        try:
            await asyncio.wait_for(_watchdog_task, timeout=5.0)
        except asyncio.CancelledError:
            logger.info("✅ Watchdog stopped successfully")
        except asyncio.TimeoutError:
            logger.warning("⚠️ Watchdog stop timed out after 5s")
        except Exception as e:
            logger.warning(f"⚠️ Error stopping watchdog: {e}")
    
    if _listener_task:
        logger.info("🛑 Stopping pub/sub listener...")
        _listener_task.cancel()
        try:
            await asyncio.wait_for(_listener_task, timeout=10.0)
        except asyncio.CancelledError:
            logger.info("✅ Pub/sub listener stopped successfully")
        except asyncio.TimeoutError:
            logger.warning("⚠️ Pub/sub listener stop timed out after 10s")
        except Exception as e:
            logger.warning(f"⚠️ Error stopping pub/sub listener: {e}")
    
    if _pubsub_instance:
        try:
            await _pubsub_instance.close()
            logger.info("✅ Pub/sub instance closed")
        except Exception as e:
            logger.warning(f"⚠️ Error closing pub/sub instance: {e}")
    
    if _async_redis_client:
        try:
            await _async_redis_client.close()
            logger.info("✅ Async Redis client closed")
        except Exception as e:
            logger.warning(f"⚠️ Error closing async Redis client: {e}")
    
    _pubsub_listener_started = False
    _listener_task = None
    _watchdog_task = None
    _async_redis_client = None
    _pubsub_instance = None
    
    logger.info("✅ Pub/sub shutdown complete")
