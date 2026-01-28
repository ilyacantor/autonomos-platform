"""
Flow Monitor API - Phase 4

Real-time flow event monitoring endpoints.
Provides REST snapshots and WebSocket streaming of telemetry events.
"""

import logging
import json
import asyncio
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from redis.asyncio import Redis as AsyncRedis
from datetime import datetime

from app.telemetry.flow_events import (
    FlowEvent,
    AAM_FLOW_STREAM,
    DCL_FLOW_STREAM,
    AGENT_FLOW_STREAM
)
from app.security import get_current_user
from app.schemas import User

logger = logging.getLogger(__name__)

router = APIRouter()

# Global async Redis client for flow monitoring (injected from main)
_async_redis = None

def set_async_redis(redis_client: AsyncRedis):
    """Inject async Redis client from main app"""
    global _async_redis
    _async_redis = redis_client
    logger.info("Async Redis client injected into flow_monitor API")


@router.get("/flow-monitor")
async def get_flow_snapshot(
    tenant_id: str = Query("default", description="Tenant identifier"),
    limit_per_layer: int = Query(100, description="Max events per layer", ge=1, le=500),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Get snapshot of recent flow events across all layers.
    
    Returns last N events from AAM, DCL, and Agent streams.
    Filters by tenant_id for multi-tenancy.
    
    Query Parameters:
    - tenant_id: Filter events by tenant (default: "default")
    - limit_per_layer: Max events per layer (default: 100, max: 500)
    
    Returns:
    {
        "aam_events": [...],
        "dcl_events": [...],
        "agent_events": [...],
        "total_count": int,
        "timestamp": "ISO timestamp"
    }
    """
    if not _async_redis:
        raise HTTPException(status_code=503, detail="Redis not available")
    
    try:
        # Helper function to process stream messages
        def process_stream_messages(messages, tenant_filter: str) -> List[Dict[str, Any]]:
            """Process raw stream messages into event dictionaries"""
            events = []
            for message_id, fields in messages:
                try:
                    # Decode bytes to strings
                    decoded_fields = {}
                    for key, value in fields.items():
                        key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                        value_str = value.decode('utf-8') if isinstance(value, bytes) else value
                        decoded_fields[key_str] = value_str
                    
                    # Parse FlowEvent
                    event = FlowEvent.from_dict(decoded_fields)
                    
                    # Filter by tenant_id
                    if event.tenant_id == tenant_filter:
                        event_dict = event.to_dict()
                        event_dict['stream_id'] = message_id.decode('utf-8') if isinstance(message_id, bytes) else message_id
                        events.append(event_dict)
                
                except Exception as e:
                    logger.warning(f"Failed to parse event: {e}")
                    continue
            
            return events
        
        # Use XREVRANGE to get most recent events (newest first)
        # Syntax: XREVRANGE stream_name + - COUNT limit
        aam_raw = await _async_redis.xrevrange(
            AAM_FLOW_STREAM, 
            '+',  # End (most recent)
            '-',  # Start (oldest)
            count=limit_per_layer
        )
        dcl_raw = await _async_redis.xrevrange(
            DCL_FLOW_STREAM,
            '+',
            '-',
            count=limit_per_layer
        )
        agent_raw = await _async_redis.xrevrange(
            AGENT_FLOW_STREAM,
            '+',
            '-',
            count=limit_per_layer
        )
        
        # Process each stream's messages
        aam_events = process_stream_messages(aam_raw, tenant_id)
        dcl_events = process_stream_messages(dcl_raw, tenant_id)
        agent_events = process_stream_messages(agent_raw, tenant_id)
        
        # Reverse arrays so newest appear last (consistent with WebSocket ordering)
        aam_events.reverse()
        dcl_events.reverse()
        agent_events.reverse()
        
        return JSONResponse({
            "aam_events": aam_events,
            "dcl_events": dcl_events,
            "agent_events": agent_events,
            "total_count": len(aam_events) + len(dcl_events) + len(agent_events),
            "tenant_id": tenant_id,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Failed to fetch flow snapshot: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch flow events: {str(e)}")


@router.websocket("/ws/flow-monitor")
async def flow_monitor_websocket(
    websocket: WebSocket,
    tenant_id: str = Query("default", description="Tenant identifier")
):
    """
    WebSocket endpoint for real-time flow event streaming.
    
    Streams new events from AAM, DCL, and Agent streams as they arrive.
    Uses Redis Streams XREAD with BLOCK for low-latency updates.
    
    Message Format:
    {
        "type": "flow_event",
        "layer": "aam|dcl|agent",
        "event": {...}  // FlowEvent DTO
    }
    """
    await websocket.accept()
    logger.info(f"Flow monitor WebSocket connected (tenant={tenant_id})")
    
    if not _async_redis:
        await websocket.send_json({
            "type": "error",
            "message": "Redis not available"
        })
        await websocket.close()
        return
    
    # Track last seen IDs for each stream
    # Start from 0-0 to begin reading from stream start
    last_ids = {
        AAM_FLOW_STREAM: "0-0",
        DCL_FLOW_STREAM: "0-0",
        AGENT_FLOW_STREAM: "0-0"
    }
    
    try:
        while True:
            # XREAD BLOCK 1000 to wait for new events (1s timeout)
            # This polls Redis and blocks until new events arrive or timeout occurs
            stream_data = await _async_redis.xread(
                streams=last_ids,
                count=10,  # Batch up to 10 messages per stream
                block=1000  # Block for 1 second (1000ms) waiting for new messages
            )
            
            # Process any new events
            if stream_data:
                for stream_name, messages in stream_data:
                    stream_name_str = stream_name.decode('utf-8') if isinstance(stream_name, bytes) else stream_name
                    
                    for message_id, fields in messages:
                        try:
                            # Decode bytes to strings
                            decoded_fields = {}
                            for key, value in fields.items():
                                key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                                value_str = value.decode('utf-8') if isinstance(value, bytes) else value
                                decoded_fields[key_str] = value_str
                            
                            # Parse FlowEvent
                            event = FlowEvent.from_dict(decoded_fields)
                            
                            # Filter by tenant_id
                            if event.tenant_id == tenant_id:
                                # Determine layer
                                layer = "unknown"
                                if stream_name_str == AAM_FLOW_STREAM:
                                    layer = "aam"
                                elif stream_name_str == DCL_FLOW_STREAM:
                                    layer = "dcl"
                                elif stream_name_str == AGENT_FLOW_STREAM:
                                    layer = "agent"
                                
                                # Send event to WebSocket client
                                await websocket.send_json({
                                    "type": "flow_event",
                                    "layer": layer,
                                    "event": event.to_dict()
                                })
                            
                            # Update last seen ID for this stream
                            # This ensures we only get newer messages on next XREAD
                            message_id_str = message_id.decode('utf-8') if isinstance(message_id, bytes) else message_id
                            last_ids[stream_name_str] = message_id_str
                        
                        except Exception as e:
                            logger.warning(f"Failed to process event in WebSocket: {e}")
                            continue
    
    except WebSocketDisconnect:
        logger.info(f"Flow monitor WebSocket disconnected (tenant={tenant_id})")
    except Exception as e:
        logger.error(f"Flow monitor WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except Exception:
            pass  # WebSocket may already be closed
    finally:
        try:
            await websocket.close()
        except Exception:
            pass  # WebSocket may already be closed


@router.post("/flow-monitor/demo")
async def generate_demo_events(
    tenant_id: str = Query("default", description="Tenant identifier"),
    count: int = Query(3, description="Events per layer", ge=1, le=10),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Generate demo flow events for integration testing.
    
    Creates N events in each layer (AAM, DCL, Agent) to test the flow monitor dashboard.
    
    Query Parameters:
    - tenant_id: Tenant to scope events to (default: "default")
    - count: Number of events per layer (default: 3, max: 10)
    
    Returns:
    {
        "message": "Demo events generated",
        "events_per_layer": int,
        "tenant_id": str
    }
    """
    if not _async_redis:
        raise HTTPException(status_code=503, detail="Redis not available")
    
    try:
        from app.telemetry.flow_publisher import FlowEventPublisher
        from app.telemetry.flow_events import FlowEventStage
        import uuid
        
        publisher = FlowEventPublisher(_async_redis)
        
        # Generate AAM events (connection lifecycle)
        for i in range(count):
            connector_name = f"demo-connector-{uuid.uuid4().hex[:8]}"
            await publisher.publish_aam_connection_start(
                connector_name=connector_name,
                tenant_id=tenant_id,
                metadata={"source": "salesforce", "demo": True, "sequence": i+1}
            )
        
        # Generate DCL events (mapping proposals)
        for i in range(count):
            mapping_id = f"demo-mapping-{uuid.uuid4().hex[:8]}"
            await publisher.publish_dcl_mapping_proposed(
                mapping_id=mapping_id,
                tenant_id=tenant_id,
                confidence_score=0.85 + (i * 0.03),
                metadata={"field": f"demo_field_{i+1}", "demo": True}
            )
        
        # Generate Agent events (task dispatch)
        for i in range(count):
            task_id = f"demo-task-{uuid.uuid4().hex[:8]}"
            await publisher.publish_agent_task_dispatched(
                task_id=task_id,
                tenant_id=tenant_id,
                metadata={"workflow_name": f"DemoWorkflow_{i+1}", "demo": True, "sequence": i+1}
            )
        
        return {
            "message": "Demo events generated successfully",
            "events_per_layer": count,
            "tenant_id": tenant_id,
            "total_events": count * 3
        }
    
    except Exception as e:
        logger.error(f"Failed to generate demo events: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate demo events: {str(e)}")
