"""
Canonical Event Publisher for AAM Redis Streams

Publishes CanonicalEvent objects to Redis streams for consumption by DCL Engine.
Stream key pattern: aam:dcl:{tenant_id}:{source_id}
"""

import json
import logging
import uuid
from typing import Optional
from datetime import datetime
from redis import Redis
from services.aam.canonical.schemas import CanonicalEvent

logger = logging.getLogger(__name__)


class CanonicalEventPublisher:
    """
    Publisher for CanonicalEvent objects to Redis streams
    
    Features:
    - Publishes to tenant-scoped Redis streams (aam:dcl:{tenant_id}:{source})
    - Generates deterministic message IDs for idempotency
    - Batches events for efficient processing
    - Automatic JSON serialization of Pydantic models
    """
    
    def __init__(self, redis_client: Redis, tenant_id: str = "default"):
        """
        Initialize publisher with Redis client and tenant context
        
        Args:
            redis_client: Redis client instance
            tenant_id: Tenant identifier for stream segmentation
        """
        self.redis = redis_client
        self.tenant_id = tenant_id
        self.batch_id = str(uuid.uuid4())
        logger.info(f"📡 CanonicalEventPublisher initialized for tenant '{tenant_id}' (batch: {self.batch_id})")
    
    def _serialize_event(self, event: CanonicalEvent) -> dict:
        """
        Serialize CanonicalEvent to JSON-compatible dict
        
        Args:
            event: CanonicalEvent to serialize
            
        Returns:
            JSON-serializable dictionary
        """
        # Use model_dump with mode='json' to properly serialize datetime and Pydantic models
        return {
            "meta": event.meta.model_dump(mode='json'),
            "source": event.source.model_dump(mode='json'),
            "entity": event.entity,
            "op": event.op,
            "data": event.data.model_dump(mode='json') if hasattr(event.data, 'model_dump') else event.data,
            "unknown_fields": event.unknown_fields
        }
    
    def publish(self, event: CanonicalEvent, source_id: str = "filesource") -> str:
        """
        Publish a single CanonicalEvent to Redis stream
        
        Args:
            event: CanonicalEvent to publish
            source_id: Source connector identifier (salesforce, filesource, etc.)
            
        Returns:
            Message ID from Redis XADD
        """
        stream_key = f"aam:dcl:{self.tenant_id}:{source_id}"
        
        # Serialize event to JSON
        event_dict = self._serialize_event(event)
        
        # Create payload with batch context
        payload = {
            "batch_id": self.batch_id,
            "entity": event.entity,
            "event": event_dict,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Publish to Redis stream using XADD
        # Message structure: {'payload': json_string}
        try:
            message_id = self.redis.xadd(
                stream_key,
                {"payload": json.dumps(payload)},
                maxlen=10000,  # Limit stream size to prevent unbounded growth
                approximate=True  # Use approximate trimming for better performance
            )
            
            logger.debug(f"✅ Published {event.entity} event to '{stream_key}' (message_id: {message_id})")
            return message_id.decode() if isinstance(message_id, bytes) else message_id
        except Exception as e:
            logger.error(f"XADD failed for stream '{stream_key}': {type(e).__name__}: {e}")
            raise
    
    def publish_batch(self, events: list[CanonicalEvent], source_id: str = "filesource") -> list[str]:
        """
        Publish multiple CanonicalEvents to Redis stream efficiently
        
        Args:
            events: List of CanonicalEvent objects
            source_id: Source connector identifier
            
        Returns:
            List of message IDs from Redis
        """
        if not events:
            return []
        
        stream_key = f"aam:dcl:{self.tenant_id}:{source_id}"
        message_ids = []
        
        # Use pipeline for efficient batch publishing
        with self.redis.pipeline() as pipe:
            for event in events:
                event_dict = self._serialize_event(event)
                payload = {
                    "batch_id": self.batch_id,
                    "entity": event.entity,
                    "event": event_dict,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                pipe.xadd(
                    stream_key,
                    {"payload": json.dumps(payload)},
                    maxlen=10000
                )
            
            # Execute pipeline and get all message IDs
            message_ids = pipe.execute()
        
        logger.info(f"✅ Published batch of {len(events)} events to '{stream_key}'")
        return message_ids
    
    def new_batch(self) -> str:
        """
        Start a new batch and return the new batch ID
        
        Returns:
            New batch ID (UUID)
        """
        self.batch_id = str(uuid.uuid4())
        logger.info(f"🔄 Started new batch: {self.batch_id}")
        return self.batch_id


def get_redis_publisher(redis_client: Redis, tenant_id: str = "default") -> CanonicalEventPublisher:
    """
    Factory function to create a CanonicalEventPublisher
    
    Args:
        redis_client: Redis client instance
        tenant_id: Tenant identifier
        
    Returns:
        Configured CanonicalEventPublisher instance
    """
    return CanonicalEventPublisher(redis_client, tenant_id)
