"""
Flow Event Publisher - Phase 4

Redis Streams publisher for telemetry events.
Provides async publishing with proper error handling and tenant scoping.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from redis.asyncio import Redis

from .flow_events import (
    FlowEvent,
    FlowEventLayer,
    FlowEventStage,
    FlowEventStatus,
    LAYER_TO_STREAM
)

logger = logging.getLogger(__name__)


class FlowEventPublisher:
    """
    Publishes flow events to Redis Streams for real-time monitoring.
    
    Each layer (AAM, DCL, Agent) gets its own stream for separation of concerns.
    Events are ordered within each stream using XADD with auto-generated IDs.
    """
    
    def __init__(self, redis_client: Redis):
        """
        Initialize publisher with Redis connection.
        
        Args:
            redis_client: Async Redis client for stream operations
        """
        self.redis = redis_client
        logger.info("FlowEventPublisher initialized")
    
    async def publish(
        self,
        layer: FlowEventLayer,
        stage: FlowEventStage,
        status: FlowEventStatus,
        entity_id: str,
        tenant_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[int] = None
    ) -> str:
        """
        Publish a flow event to the appropriate Redis Stream.
        
        Args:
            layer: Which architectural layer (AAM, DCL, Agent)
            stage: Processing stage
            status: Event status
            entity_id: Entity being processed (connector, mapping, task)
            tenant_id: Tenant identifier
            metadata: Optional layer-specific details
            duration_ms: Optional operation duration
            
        Returns:
            Event ID (UUID) of published event
        """
        try:
            # Create event
            event = FlowEvent(
                event_id=str(uuid.uuid4()),
                entity_id=entity_id,
                layer=layer,
                stage=stage,
                status=status,
                tenant_id=tenant_id,
                timestamp=datetime.utcnow(),
                duration_ms=duration_ms,
                metadata=metadata or {}
            )
            
            # Serialize to dict
            event_data = event.to_dict()
            
            # Get stream key for this layer
            stream_key = LAYER_TO_STREAM[layer]
            
            # Publish to Redis Stream with XADD
            stream_id = await self.redis.xadd(
                name=stream_key,
                fields=event_data,
                maxlen=10000,  # Keep last 10k events per stream (prevent unbounded growth)
                approximate=True  # Allow Redis to trim approximately for performance
            )
            
            logger.debug(
                f"Published {layer.value} event: {stage.value} "
                f"(entity={entity_id}, tenant={tenant_id}, stream_id={stream_id})"
            )
            
            return event.event_id
            
        except Exception as e:
            # Log error but don't fail the main operation
            # Telemetry should never break business logic
            logger.error(
                f"Failed to publish flow event: {layer.value}.{stage.value} "
                f"for entity {entity_id}: {str(e)}"
            )
            return ""
    
    async def publish_aam_connection_start(
        self,
        connector_name: str,
        tenant_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Convenience method: AAM connection started"""
        return await self.publish(
            layer=FlowEventLayer.AAM,
            stage=FlowEventStage.CONNECTION_START,
            status=FlowEventStatus.IN_PROGRESS,
            entity_id=connector_name,
            tenant_id=tenant_id,
            metadata=metadata
        )
    
    async def publish_aam_connection_success(
        self,
        connector_name: str,
        tenant_id: str,
        duration_ms: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Convenience method: AAM connection succeeded"""
        return await self.publish(
            layer=FlowEventLayer.AAM,
            stage=FlowEventStage.CONNECTION_SUCCESS,
            status=FlowEventStatus.SUCCESS,
            entity_id=connector_name,
            tenant_id=tenant_id,
            duration_ms=duration_ms,
            metadata=metadata
        )
    
    async def publish_aam_schema_drift(
        self,
        connector_name: str,
        tenant_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Convenience method: AAM detected schema drift"""
        return await self.publish(
            layer=FlowEventLayer.AAM,
            stage=FlowEventStage.SCHEMA_DRIFT_DETECTED,
            status=FlowEventStatus.PENDING,
            entity_id=connector_name,
            tenant_id=tenant_id,
            metadata=metadata
        )
    
    async def publish_dcl_mapping_proposed(
        self,
        mapping_id: str,
        tenant_id: str,
        confidence_score: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Convenience method: DCL proposed a mapping"""
        enriched_metadata = metadata or {}
        enriched_metadata['confidence_score'] = confidence_score
        
        return await self.publish(
            layer=FlowEventLayer.DCL,
            stage=FlowEventStage.MAPPING_PROPOSED,
            status=FlowEventStatus.SUCCESS,
            entity_id=mapping_id,
            tenant_id=tenant_id,
            metadata=enriched_metadata
        )
    
    async def publish_dcl_rag_cache_hit(
        self,
        mapping_key: str,
        tenant_id: str,
        similarity_score: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Convenience method: DCL RAG cache hit"""
        enriched_metadata = metadata or {}
        enriched_metadata['similarity_score'] = similarity_score
        
        return await self.publish(
            layer=FlowEventLayer.DCL,
            stage=FlowEventStage.RAG_CACHE_HIT,
            status=FlowEventStatus.SUCCESS,
            entity_id=mapping_key,
            tenant_id=tenant_id,
            metadata=enriched_metadata
        )
    
    async def publish_agent_task_dispatched(
        self,
        task_id: str,
        tenant_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Convenience method: Agent task dispatched"""
        return await self.publish(
            layer=FlowEventLayer.AGENT,
            stage=FlowEventStage.TASK_DISPATCHED,
            status=FlowEventStatus.IN_PROGRESS,
            entity_id=task_id,
            tenant_id=tenant_id,
            metadata=metadata
        )
    
    async def publish_agent_task_completed(
        self,
        task_id: str,
        tenant_id: str,
        duration_ms: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Convenience method: Agent task completed successfully"""
        return await self.publish(
            layer=FlowEventLayer.AGENT,
            stage=FlowEventStage.TASK_COMPLETED,
            status=FlowEventStatus.SUCCESS,
            entity_id=task_id,
            tenant_id=tenant_id,
            duration_ms=duration_ms,
            metadata=metadata
        )
    
    async def publish_agent_fallback_invoked(
        self,
        task_id: str,
        tenant_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Convenience method: Agent invoked fallback (degraded mode)"""
        return await self.publish(
            layer=FlowEventLayer.AGENT,
            stage=FlowEventStage.FALLBACK_INVOKED,
            status=FlowEventStatus.DEGRADED,
            entity_id=task_id,
            tenant_id=tenant_id,
            metadata=metadata
        )
