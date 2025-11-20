"""Token bucket rate limiter implementation."""
import asyncio
import time
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""
    capacity: int
    refill_rate: float  # tokens per second
    tokens: float
    last_refill: float
    
    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens from the bucket."""
        # Refill tokens based on time elapsed
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now
        
        # Check if we have enough tokens
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def time_until_tokens(self, tokens: int = 1) -> float:
        """Calculate time until enough tokens are available."""
        if self.tokens >= tokens:
            return 0.0
        
        needed = tokens - self.tokens
        return needed / self.refill_rate


class RateLimiter:
    """Per-tenant rate limiter using token buckets."""
    
    def __init__(self):
        self.buckets: Dict[Tuple[str, str], TokenBucket] = {}
        self.lock = asyncio.Lock()
    
    def _get_bucket_key(self, service_id: str, tenant_id: Optional[str]) -> Tuple[str, str]:
        """Generate bucket key for service/tenant combination."""
        return (service_id, tenant_id or "default")
    
    async def check_rate_limit(
        self,
        service_id: str,
        tenant_id: Optional[str],
        max_rps: int,
        burst: int
    ) -> Tuple[bool, Optional[float]]:
        """
        Check if request is within rate limit.
        Returns (allowed, retry_after_seconds).
        """
        async with self.lock:
            key = self._get_bucket_key(service_id, tenant_id)
            
            # Get or create bucket
            if key not in self.buckets:
                self.buckets[key] = TokenBucket(
                    capacity=burst,
                    refill_rate=max_rps,
                    tokens=burst,
                    last_refill=time.time()
                )
            
            bucket = self.buckets[key]
            
            # Try to consume a token
            if bucket.consume():
                return (True, None)
            else:
                retry_after = bucket.time_until_tokens()
                return (False, retry_after)
    
    def reset_bucket(self, service_id: str, tenant_id: Optional[str]):
        """Reset a specific rate limit bucket."""
        key = self._get_bucket_key(service_id, tenant_id)
        if key in self.buckets:
            del self.buckets[key]
    
    def get_metrics(self, service_id: str, tenant_id: Optional[str]) -> Dict[str, Any]:
        """Get current metrics for a bucket."""
        key = self._get_bucket_key(service_id, tenant_id)
        if key in self.buckets:
            bucket = self.buckets[key]
            return {
                "tokens_available": bucket.tokens,
                "capacity": bucket.capacity,
                "refill_rate": bucket.refill_rate,
                "utilization": 1.0 - (bucket.tokens / bucket.capacity)
            }
        return {"tokens_available": 0, "capacity": 0, "refill_rate": 0, "utilization": 0}


class AdaptiveRateLimiter(RateLimiter):
    """Rate limiter that adapts based on chaos level."""
    
    def __init__(self, chaos_engine):
        super().__init__()
        self.chaos_engine = chaos_engine
    
    async def check_rate_limit(
        self,
        service_id: str,
        tenant_id: Optional[str],
        max_rps: int,
        burst: int
    ) -> Tuple[bool, Optional[float]]:
        """Check rate limit with chaos adjustment."""
        # Apply chaos multiplier
        multiplier = self.chaos_engine.get_rate_limit_adjustment()
        adjusted_rps = int(max_rps * multiplier)
        adjusted_burst = int(burst * multiplier)
        
        # Ensure minimum values
        adjusted_rps = max(1, adjusted_rps)
        adjusted_burst = max(1, adjusted_burst)
        
        return await super().check_rate_limit(
            service_id,
            tenant_id,
            adjusted_rps,
            adjusted_burst
        )