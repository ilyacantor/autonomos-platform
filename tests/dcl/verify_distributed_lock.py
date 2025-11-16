#!/usr/bin/env python3
"""
Standalone verification script for Redis distributed lock implementation.
Tests the atomic Lua script solution for lock release.
"""
import os
import sys
import time
import asyncio
from contextlib import contextmanager

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

def test_sync_lock():
    """Test synchronous distributed lock acquire and release"""
    import redis
    from app.dcl_engine.distributed_lock import RedisDistributedLock
    from app.dcl_engine.app import RedisDecodeWrapper
    
    # Connect to Redis
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        print("❌ REDIS_URL not set")
        return False
    
    # Convert to rediss:// for TLS
    if redis_url.startswith("redis://"):
        redis_url = "rediss://" + redis_url[8:]
    
    client = redis.from_url(redis_url, decode_responses=False, ssl_cert_reqs="required")
    wrapped_client = RedisDecodeWrapper(client)
    
    print("🔒 Testing synchronous distributed lock...")
    
    # Test 1: Acquire and release lock
    lock = RedisDistributedLock(wrapped_client, "test:lock:sync")
    
    try:
        with lock.acquire(timeout=2.0):
            print("✅ Lock acquired successfully (sync)")
            time.sleep(0.1)
            # Lock is automatically released here
        
        print("✅ Lock released successfully (sync)")
        
        # Verify lock was actually released by checking Redis
        lock_value = wrapped_client.get("test:lock:sync")
        if lock_value is None:
            print("✅ Lock key removed from Redis (confirmed)")
        else:
            print(f"❌ Lock key still exists in Redis: {lock_value}")
            return False
            
    except Exception as e:
        print(f"❌ Sync lock test failed: {e}")
        return False
    
    # Test 2: Lock timeout
    print("\n🔒 Testing lock timeout (sync)...")
    lock1 = RedisDistributedLock(wrapped_client, "test:lock:timeout")
    lock2 = RedisDistributedLock(wrapped_client, "test:lock:timeout")
    
    try:
        with lock1.acquire(timeout=1.0):
            print("✅ Lock 1 acquired")
            # Try to acquire same lock with second instance (should timeout)
            try:
                with lock2.acquire(timeout=0.5):
                    print("❌ Lock 2 should not have been acquired!")
                    return False
            except TimeoutError:
                print("✅ Lock 2 correctly timed out")
        
        print("✅ Lock 1 released")
        
        # Now lock2 should be able to acquire
        with lock2.acquire(timeout=1.0):
            print("✅ Lock 2 acquired after lock 1 released")
        
    except Exception as e:
        print(f"❌ Lock timeout test failed: {e}")
        return False
    
    print("\n✅ All synchronous lock tests passed!")
    return True


async def test_async_lock():
    """Test asynchronous distributed lock acquire and release"""
    import redis
    from app.dcl_engine.distributed_lock import RedisDistributedLock
    from app.dcl_engine.app import RedisDecodeWrapper
    
    # Connect to Redis
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        print("❌ REDIS_URL not set")
        return False
    
    # Convert to rediss:// for TLS
    if redis_url.startswith("redis://"):
        redis_url = "rediss://" + redis_url[8:]
    
    client = redis.from_url(redis_url, decode_responses=False, ssl_cert_reqs="required")
    wrapped_client = RedisDecodeWrapper(client)
    
    print("\n🔒 Testing asynchronous distributed lock...")
    
    # Test 1: Acquire and release lock
    lock = RedisDistributedLock(wrapped_client, "test:lock:async")
    
    try:
        async with lock.acquire_async(timeout=2.0):
            print("✅ Lock acquired successfully (async)")
            await asyncio.sleep(0.1)
            # Lock is automatically released here
        
        print("✅ Lock released successfully (async)")
        
        # Verify lock was actually released
        lock_value = wrapped_client.get("test:lock:async")
        if lock_value is None:
            print("✅ Lock key removed from Redis (confirmed)")
        else:
            print(f"❌ Lock key still exists in Redis: {lock_value}")
            return False
            
    except Exception as e:
        print(f"❌ Async lock test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 2: Concurrent lock contention
    print("\n🔒 Testing concurrent lock contention (async)...")
    lock1 = RedisDistributedLock(wrapped_client, "test:lock:concurrent")
    lock2 = RedisDistributedLock(wrapped_client, "test:lock:concurrent")
    
    # Use a flag to detect incorrect concurrent acquisition
    worker2_failed = False
    
    async def worker1():
        async with lock1.acquire_async(timeout=2.0):
            print("✅ Worker 1 acquired lock")
            await asyncio.sleep(0.5)  # Hold lock longer to ensure overlap
            print("✅ Worker 1 releasing lock")
    
    async def worker2():
        nonlocal worker2_failed
        await asyncio.sleep(0.1)  # Let worker 1 acquire first
        try:
            async with lock2.acquire_async(timeout=0.3):
                # This should NOT succeed while worker 1 holds the lock
                print("❌ Worker 2 should not have acquired lock!")
                worker2_failed = True
                return False
        except TimeoutError:
            print("✅ Worker 2 correctly timed out while worker 1 held lock")
        
        # Now try again with longer timeout (worker 1 should have released by now)
        await asyncio.sleep(0.2)
        async with lock2.acquire_async(timeout=1.0):
            print("✅ Worker 2 acquired lock after worker 1 released")
    
    try:
        await asyncio.gather(worker1(), worker2())
        
        if worker2_failed:
            print("❌ CRITICAL: Worker 2 acquired lock concurrently with worker 1!")
            return False
            
    except Exception as e:
        print(f"❌ Concurrent lock test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n✅ All asynchronous lock tests passed!")
    return True


def test_lua_script_encoding():
    """Test that Lua script handles encoding correctly"""
    import redis
    from app.dcl_engine.app import RedisDecodeWrapper
    
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        print("❌ REDIS_URL not set")
        return False
    
    if redis_url.startswith("redis://"):
        redis_url = "rediss://" + redis_url[8:]
    
    client = redis.from_url(redis_url, decode_responses=False, ssl_cert_reqs="required")
    wrapped_client = RedisDecodeWrapper(client)
    
    print("\n🔍 Testing Lua script encoding consistency...")
    
    # Test compare_and_delete with various string formats
    test_key = "test:lua:encoding"
    test_values = [
        "simple_string",
        "string-with-dashes",
        "string_with_1234567890.123",
        f"{time.time()}_{id(wrapped_client)}",  # Lock token format
    ]
    
    for test_value in test_values:
        # Set value using wrapper (encodes string to bytes)
        wrapped_client.set(test_key, test_value, ex=5)
        
        # Try to delete with matching value
        result = wrapped_client.compare_and_delete(test_key, test_value)
        if result:
            print(f"✅ Lua script correctly matched and deleted: {test_value}")
        else:
            print(f"❌ Lua script failed to match: {test_value}")
            return False
    
    # Test that compare_and_delete returns False for non-matching value
    wrapped_client.set(test_key, "actual_value", ex=5)
    result = wrapped_client.compare_and_delete(test_key, "wrong_value")
    if not result:
        print("✅ Lua script correctly rejected non-matching value")
    else:
        print("❌ Lua script incorrectly deleted with wrong value")
        return False
    
    # Cleanup
    wrapped_client.delete(test_key)
    
    print("✅ Lua script encoding test passed!")
    return True


if __name__ == "__main__":
    print("=" * 80)
    print("Redis Distributed Lock Verification")
    print("=" * 80)
    
    # Run sync tests
    sync_passed = test_sync_lock()
    
    # Run async tests
    async_passed = asyncio.run(test_async_lock())
    
    # Run encoding tests
    encoding_passed = test_lua_script_encoding()
    
    print("\n" + "=" * 80)
    print("Test Results Summary")
    print("=" * 80)
    print(f"Synchronous locks:  {'✅ PASSED' if sync_passed else '❌ FAILED'}")
    print(f"Asynchronous locks: {'✅ PASSED' if async_passed else '❌ FAILED'}")
    print(f"Lua script encoding: {'✅ PASSED' if encoding_passed else '❌ FAILED'}")
    print("=" * 80)
    
    if sync_passed and async_passed and encoding_passed:
        print("\n🎉 All distributed lock tests PASSED!")
        sys.exit(0)
    else:
        print("\n❌ Some tests FAILED")
        sys.exit(1)
