#!/usr/bin/env python3
"""
Debug script to monitor async lock behavior in detail.
"""
import os
import sys
import asyncio
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

async def debug_async_lock():
    """Debug async lock with detailed Redis monitoring"""
    import redis
    from app.dcl_engine.distributed_lock import RedisDistributedLock
    from app.dcl_engine.app import RedisDecodeWrapper
    
    # Connect to Redis
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        print("❌ REDIS_URL not set")
        return False
    
    if redis_url.startswith("redis://"):
        redis_url = "rediss://" + redis_url[8:]
    
    client = redis.from_url(redis_url, decode_responses=False, ssl_cert_reqs="required")
    wrapped_client = RedisDecodeWrapper(client)
    
    print("🔍 Debugging async lock with detailed monitoring...")
    
    lock_key = "test:lock:debug"
    lock1 = RedisDistributedLock(wrapped_client, lock_key)
    lock2 = RedisDistributedLock(wrapped_client, lock_key)
    
    # Clean up any existing lock
    wrapped_client.delete(lock_key)
    
    events = []
    
    async def worker1():
        events.append(f"[{time.time():.3f}] Worker 1: Attempting to acquire lock...")
        async with lock1.acquire_async(timeout=2.0):
            lock_value = wrapped_client.get(lock_key)
            events.append(f"[{time.time():.3f}] Worker 1: ✅ ACQUIRED lock (value={lock_value})")
            await asyncio.sleep(0.5)
            events.append(f"[{time.time():.3f}] Worker 1: Releasing lock...")
        events.append(f"[{time.time():.3f}] Worker 1: Released lock")
    
    async def worker2():
        await asyncio.sleep(0.1)
        events.append(f"[{time.time():.3f}] Worker 2: Attempting to acquire lock...")
        try:
            async with lock2.acquire_async(timeout=0.3):
                lock_value = wrapped_client.get(lock_key)
                events.append(f"[{time.time():.3f}] Worker 2: ❌ ACQUIRED lock (value={lock_value}) - SHOULD NOT HAPPEN!")
                return False
        except TimeoutError as e:
            events.append(f"[{time.time():.3f}] Worker 2: ✅ Timed out (expected): {e}")
        
        # Wait for worker1 to release
        await asyncio.sleep(0.3)
        events.append(f"[{time.time():.3f}] Worker 2: Attempting to acquire lock (2nd try)...")
        async with lock2.acquire_async(timeout=1.0):
            lock_value = wrapped_client.get(lock_key)
            events.append(f"[{time.time():.3f}] Worker 2: ✅ ACQUIRED lock (value={lock_value})")
        events.append(f"[{time.time():.3f}] Worker 2: Released lock")
    
    # Run workers concurrently
    try:
        await asyncio.gather(worker1(), worker2())
    except Exception as e:
        events.append(f"[{time.time():.3f}] ❌ Exception: {e}")
        import traceback
        traceback.print_exc()
    
    # Print all events in chronological order
    print("\n📊 Event Timeline:")
    print("=" * 80)
    for event in events:
        print(event)
    print("=" * 80)
    
    # Check final state
    final_lock_value = wrapped_client.get(lock_key)
    if final_lock_value is None:
        print("\n✅ Lock correctly released (no key in Redis)")
    else:
        print(f"\n❌ Lock key still exists: {final_lock_value}")
    
    # Check if worker2 incorrectly acquired lock
    worker2_acquired_during_worker1 = any("Worker 2: ❌ ACQUIRED" in event for event in events)
    if worker2_acquired_during_worker1:
        print("\n❌ CRITICAL BUG: Worker 2 acquired lock while Worker 1 held it!")
        return False
    else:
        print("\n✅ Mutual exclusion correctly enforced")
        return True

if __name__ == "__main__":
    result = asyncio.run(debug_async_lock())
    sys.exit(0 if result else 1)
