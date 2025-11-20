"""Rate limiting policies for AAM connectors."""
import time
import asyncio
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class RatePolicy:
    """Rate limiting policy configuration."""
    max_requests_per_second: int = 10
    burst_size: int = 20
    backoff_multiplier: float = 2.0
    max_backoff_seconds: float = 60.0
    retry_after_header: bool = True  # Honor Retry-After headers


class TokenBucket:
    """Token bucket for rate limiting."""
    
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
        self.lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens from the bucket."""
        async with self.lock:
            now = time.time()
            elapsed = now - self.last_refill
            
            # Refill tokens
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.refill_rate
            )
            self.last_refill = now
            
            # Check if we have enough tokens
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    async def wait_for_tokens(self, tokens: int = 1) -> float:
        """Wait until tokens are available and return wait time."""
        start = time.time()
        
        while True:
            if await self.acquire(tokens):
                return time.time() - start
            
            # Calculate wait time
            async with self.lock:
                needed = tokens - self.tokens
                wait_time = needed / self.refill_rate
            
            await asyncio.sleep(min(wait_time, 0.1))


class AdaptiveRateLimiter:
    """Adaptive rate limiter that adjusts based on server responses."""
    
    def __init__(self):
        self.buckets: Dict[str, TokenBucket] = {}
        self.backoff_until: Dict[str, float] = defaultdict(float)
        self.consecutive_errors: Dict[str, int] = defaultdict(int)
    
    def get_bucket(self, connector_id: str, policy: RatePolicy) -> TokenBucket:
        """Get or create a token bucket for a connector."""
        if connector_id not in self.buckets:
            self.buckets[connector_id] = TokenBucket(
                capacity=policy.burst_size,
                refill_rate=policy.max_requests_per_second
            )
        return self.buckets[connector_id]
    
    async def acquire(self, connector_id: str, policy: RatePolicy) -> bool:
        """Acquire permission to make a request."""
        # Check if we're in backoff
        if time.time() < self.backoff_until[connector_id]:
            return False
        
        # Try to acquire from token bucket
        bucket = self.get_bucket(connector_id, policy)
        return await bucket.acquire()
    
    async def wait_and_acquire(self, connector_id: str, policy: RatePolicy) -> float:
        """Wait for permission and return wait time."""
        # Wait for backoff if needed
        backoff_wait = self.backoff_until[connector_id] - time.time()
        if backoff_wait > 0:
            await asyncio.sleep(backoff_wait)
        
        # Wait for token
        bucket = self.get_bucket(connector_id, policy)
        return await bucket.wait_for_tokens()
    
    def record_success(self, connector_id: str):
        """Record a successful request."""
        self.consecutive_errors[connector_id] = 0
    
    def record_rate_limit(
        self,
        connector_id: str,
        policy: RatePolicy,
        retry_after: Optional[float] = None
    ):
        """Record a rate limit error and apply backoff."""
        self.consecutive_errors[connector_id] += 1
        
        if retry_after and policy.retry_after_header:
            # Use server-provided retry delay
            self.backoff_until[connector_id] = time.time() + retry_after
        else:
            # Calculate exponential backoff
            backoff = min(
                policy.backoff_multiplier ** self.consecutive_errors[connector_id],
                policy.max_backoff_seconds
            )
            self.backoff_until[connector_id] = time.time() + backoff
    
    def record_error(self, connector_id: str):
        """Record a general error."""
        self.consecutive_errors[connector_id] += 1
    
    def reset(self, connector_id: str):
        """Reset rate limiting state for a connector."""
        if connector_id in self.buckets:
            del self.buckets[connector_id]
        self.backoff_until[connector_id] = 0
        self.consecutive_errors[connector_id] = 0
    
    def get_stats(self, connector_id: str) -> Dict[str, Any]:
        """Get rate limiting stats for a connector."""
        bucket = self.buckets.get(connector_id)
        return {
            "tokens_available": bucket.tokens if bucket else 0,
            "capacity": bucket.capacity if bucket else 0,
            "consecutive_errors": self.consecutive_errors[connector_id],
            "backoff_until": self.backoff_until[connector_id],
            "in_backoff": time.time() < self.backoff_until[connector_id]
        }