"""
Semantic Cache

Caches LLM responses based on semantic similarity of inputs.
Avoids redundant LLM calls for similar/identical requests.
"""

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """A single cache entry."""
    key: str
    response: Any
    created_at: float
    expires_at: float
    hit_count: int = 0


class SemanticCache:
    """
    In-memory semantic cache for LLM responses.

    Features:
    - Exact match caching based on message hash
    - TTL-based expiration
    - LRU eviction when cache is full
    - Hit rate tracking

    Note: For production, consider Redis-based implementation.
    """

    def __init__(
        self,
        ttl_seconds: int = 3600,
        max_entries: int = 1000,
    ):
        """
        Initialize the cache.

        Args:
            ttl_seconds: Time-to-live for cache entries
            max_entries: Maximum cache entries before eviction
        """
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._cache: dict[str, CacheEntry] = {}
        self._hits = 0
        self._misses = 0

    def _generate_key(
        self,
        messages: list[dict],
        system: Optional[str] = None
    ) -> str:
        """Generate a cache key from messages and system prompt."""
        # Normalize messages for consistent hashing
        normalized = {
            "messages": [
                {"role": m.get("role"), "content": m.get("content")}
                for m in messages
            ],
            "system": system
        }
        content = json.dumps(normalized, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    async def get(
        self,
        messages: list[dict],
        system: Optional[str] = None
    ) -> Optional[Any]:
        """
        Get a cached response.

        Args:
            messages: Conversation messages
            system: System prompt

        Returns:
            Cached response or None
        """
        key = self._generate_key(messages, system)
        entry = self._cache.get(key)

        if entry is None:
            self._misses += 1
            return None

        # Check expiration
        if time.time() > entry.expires_at:
            del self._cache[key]
            self._misses += 1
            return None

        # Update hit count
        entry.hit_count += 1
        self._hits += 1

        logger.debug(f"Cache hit for key {key[:8]}...")
        return entry.response

    async def put(
        self,
        messages: list[dict],
        system: Optional[str],
        response: Any
    ) -> None:
        """
        Store a response in the cache.

        Args:
            messages: Conversation messages
            system: System prompt
            response: Response to cache
        """
        # Evict if cache is full
        if len(self._cache) >= self.max_entries:
            self._evict_lru()

        key = self._generate_key(messages, system)
        now = time.time()

        self._cache[key] = CacheEntry(
            key=key,
            response=response,
            created_at=now,
            expires_at=now + self.ttl_seconds,
        )

        logger.debug(f"Cached response for key {key[:8]}...")

    def _evict_lru(self, count: int = 100):
        """Evict least recently used entries."""
        if not self._cache:
            return

        # Sort by hit count (LFU) then created_at (LRU)
        sorted_entries = sorted(
            self._cache.items(),
            key=lambda x: (x[1].hit_count, x[1].created_at)
        )

        # Remove oldest/least-used entries
        for key, _ in sorted_entries[:count]:
            del self._cache[key]

        logger.debug(f"Evicted {count} cache entries")

    def invalidate(self, messages: list[dict], system: Optional[str] = None):
        """Invalidate a specific cache entry."""
        key = self._generate_key(messages, system)
        if key in self._cache:
            del self._cache[key]

    def clear(self):
        """Clear all cache entries."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    def get_stats(self) -> dict:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0

        return {
            "entries": len(self._cache),
            "max_entries": self.max_entries,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "ttl_seconds": self.ttl_seconds,
        }


class RedisSemanticCache(SemanticCache):
    """
    Redis-backed semantic cache for production use.

    Provides persistence and distributed caching.
    """

    def __init__(
        self,
        redis_url: str,
        ttl_seconds: int = 3600,
        key_prefix: str = "aos:llm_cache:"
    ):
        super().__init__(ttl_seconds=ttl_seconds)
        self.key_prefix = key_prefix

        try:
            import redis.asyncio as redis
            self._redis = redis.from_url(redis_url)
            logger.info("Redis semantic cache initialized")
        except ImportError:
            logger.warning("redis package not installed, falling back to in-memory cache")
            self._redis = None

    async def get(
        self,
        messages: list[dict],
        system: Optional[str] = None
    ) -> Optional[Any]:
        if not self._redis:
            return await super().get(messages, system)

        key = self.key_prefix + self._generate_key(messages, system)

        try:
            data = await self._redis.get(key)
            if data:
                self._hits += 1
                # Deserialize response
                from app.agentic.gateway.client import LLMResponse
                response_data = json.loads(data)
                return LLMResponse(**response_data)
            else:
                self._misses += 1
                return None
        except Exception as e:
            logger.warning(f"Redis get failed: {e}")
            return None

    async def put(
        self,
        messages: list[dict],
        system: Optional[str],
        response: Any
    ) -> None:
        if not self._redis:
            return await super().put(messages, system, response)

        key = self.key_prefix + self._generate_key(messages, system)

        try:
            # Serialize response
            if hasattr(response, '__dict__'):
                data = json.dumps(response.__dict__, default=str)
            else:
                data = json.dumps(response, default=str)

            await self._redis.setex(key, self.ttl_seconds, data)
        except Exception as e:
            logger.warning(f"Redis put failed: {e}")

    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
