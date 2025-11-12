"""
Event Bus - Redis Pub/Sub Implementation
Provides async messaging for inter-service communication
"""
import json
import asyncio
import redis.asyncio as redis
from typing import Callable, Any, Dict
from aam_hybrid.shared.config import settings
import logging

logger = logging.getLogger(__name__)


class EventBus:
    """
    Async Redis Pub/Sub Event Bus (Singleton with Task Tracking)
    
    Channels:
    - aam:drift_detected: Schema Observer -> RAG Engine
    - aam:repair_proposed: RAG Engine -> Drift Repair Agent
    - aam:status_update: All services -> Control Plane
    
    Features:
    - Idempotent connect() - safe to call multiple times
    - Single listener task handles all subscriptions
    - Proper task cancellation on shutdown
    """
    
    def __init__(self):
        self.redis_client: redis.Redis = None
        self.pubsub = None
        self.listeners: Dict[str, Callable] = {}
        self.listener_task: asyncio.Task = None
        self._connected: bool = False
        
    async def connect(self):
        """Initialize Redis connection (idempotent - safe to call multiple times)"""
        if self._connected:
            logger.debug("Event Bus already connected, skipping reconnect")
            return
        
        # Handle TLS for Upstash Redis (same as main app)
        redis_url = settings.REDIS_URL
        if redis_url and redis_url.startswith("redis://"):
            redis_url = "rediss://" + redis_url[8:]
            logger.debug("🔒 Using TLS/SSL for Event Bus Redis connection")
        
        self.redis_client = redis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        self.pubsub = self.redis_client.pubsub()
        self._connected = True
        logger.info("Event Bus connected to Redis")
    
    async def disconnect(self):
        """Close Redis connection and cancel listener task"""
        # Cancel listener task first
        if self.listener_task:
            self.listener_task.cancel()
            try:
                await self.listener_task
            except asyncio.CancelledError:
                logger.debug("Listener task cancelled successfully")
            self.listener_task = None
        
        # Close connections
        if self.pubsub:
            await self.pubsub.close()
        if self.redis_client:
            await self.redis_client.close()
        
        self._connected = False
        logger.info("Event Bus disconnected")
    
    async def publish(self, channel: str, message: Dict[str, Any]):
        """
        Publish message to a channel
        
        Args:
            channel: Channel name (e.g., 'aam:drift_detected')
            message: Dictionary payload (will be JSON serialized)
        """
        try:
            message_json = json.dumps(message, default=str)
            await self.redis_client.publish(channel, message_json)
            logger.info(f"📡 Published to {channel}: {message.get('connection_id', 'N/A')}")
        except Exception as e:
            logger.error(f"Failed to publish to {channel}: {e}")
            raise
    
    async def subscribe(self, channel: str, handler: Callable):
        """
        Subscribe to a channel with a handler function
        
        Args:
            channel: Channel name
            handler: Async function to handle messages
        """
        await self.pubsub.subscribe(channel)
        self.listeners[channel] = handler
        logger.info(f"📥 Subscribed to {channel}")
    
    async def start_listening(self):
        """
        Start the listener task (idempotent - safe to call multiple times)
        Creates a single background task to handle all subscriptions
        """
        if self.listener_task is None:
            self.listener_task = asyncio.create_task(self.listen())
            logger.info("🎧 Event Bus listener task started")
        else:
            logger.debug("Listener task already running")
    
    async def listen(self):
        """
        Start listening for messages
        Should be run as a background task
        """
        logger.info("Event Bus listening for messages...")
        try:
            async for message in self.pubsub.listen():
                if message['type'] == 'message':
                    channel = message['channel']
                    data = json.loads(message['data'])
                    
                    handler = self.listeners.get(channel)
                    if handler:
                        try:
                            await handler(data)
                        except Exception as e:
                            logger.error(f"Handler error for {channel}: {e}")
        except asyncio.CancelledError:
            logger.info("Event Bus listener cancelled")
        except Exception as e:
            logger.error(f"Event Bus listener error: {e}")


# Singleton instance
event_bus = EventBus()
