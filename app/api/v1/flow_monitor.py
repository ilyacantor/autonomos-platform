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
        # Read from all three streams
        streams = {
            AAM_FLOW_STREAM: "0",  # Start from beginning
            DCL_FLOW_STREAM: "0",
            AGENT_FLOW_STREAM: "0"
        }
        
        # XREAD with COUNT to get last N messages
        stream_data = await _async_redis.xread(
            streams=streams,
            count=limit_per_layer,
            block=None  # Non-blocking for snapshot
        )
        
        aam_events = []
        dcl_events = []
        agent_events = []
        
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
                        event_dict = event.to_dict()
                        event_dict['stream_id'] = message_id.decode('utf-8') if isinstance(message_id, bytes) else message_id
                        
                        # Route to appropriate list
                        if stream_name_str == AAM_FLOW_STREAM:
                            aam_events.append(event_dict)
                        elif stream_name_str == DCL_FLOW_STREAM:
                            dcl_events.append(event_dict)
                        elif stream_name_str == AGENT_FLOW_STREAM:
                            agent_events.append(event_dict)
                
                except Exception as e:
                    logger.warning(f"Failed to parse event: {e}")
                    continue
        
        # Sort by timestamp (most recent first)
        aam_events.sort(key=lambda e: e['timestamp'], reverse=True)
        dcl_events.sort(key=lambda e: e['timestamp'], reverse=True)
        agent_events.sort(key=lambda e: e['timestamp'], reverse=True)
        
        # Limit to requested count
        aam_events = aam_events[:limit_per_layer]
        dcl_events = dcl_events[:limit_per_layer]
        agent_events = agent_events[:limit_per_layer]
        
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
    last_ids = {
        AAM_FLOW_STREAM: "$",  # $ = only new messages
        DCL_FLOW_STREAM: "$",
        AGENT_FLOW_STREAM: "$"
    }
    
    try:
        while True:
            try:
                # XREAD with BLOCK for real-time streaming (1 second timeout)
                stream_data = await _async_redis.xread(
                    streams=last_ids,
                    count=10,  # Batch up to 10 messages
                    block=1000  # Block for 1 second waiting for new messages
                )
                
                if stream_data:
                    for stream_name, messages in stream_data:
                        stream_name_str = stream_name.decode('utf-8') if isinstance(stream_name, bytes) else stream_name
                        
                        for message_id, fields in messages:
                            try:
                                # Decode fields
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
                                    
                                    # Send to WebSocket
                                    await websocket.send_json({
                                        "type": "flow_event",
                                        "layer": layer,
                                        "event": event.to_dict()
                                    })
                                
                                # Update last seen ID for this stream
                                last_ids[stream_name_str] = message_id.decode('utf-8') if isinstance(message_id, bytes) else message_id
                            
                            except Exception as e:
                                logger.warning(f"Failed to process event: {e}")
                                continue
                
                # Check if client is still connected
                await asyncio.sleep(0.01)  # Small yield to check for disconnections
            
            except WebSocketDisconnect:
                logger.info(f"Flow monitor WebSocket disconnected (tenant={tenant_id})")
                break
            except Exception as e:
                logger.error(f"Error in flow monitor WebSocket: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })
                await asyncio.sleep(1)  # Back off on errors
    
    except Exception as e:
        logger.error(f"Flow monitor WebSocket error: {e}")
    finally:
        try:
            await websocket.close()
        except:
            pass
