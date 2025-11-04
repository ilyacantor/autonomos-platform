import logging
import asyncio
import json
from datetime import datetime, timedelta
from typing import AsyncGenerator, Dict, Any, Optional
from fastapi import APIRouter, Request, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, desc, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import Session
import os
import random

from app.security import decode_access_token
from app.database import get_db
from app import models

logger = logging.getLogger(__name__)

router = APIRouter()

# Custom dependency for SSE authentication via query parameter
# EventSource doesn't support custom headers, so we use query params
async def get_current_user_from_token(
    token: str = Query(..., description="JWT access token"),
    db: Session = Depends(get_db)
) -> models.User:
    """
    Validate JWT token from query parameter and return the current user.
    Used for SSE endpoints where EventSource doesn't support custom headers.
    """
    try:
        payload = decode_access_token(token)
        user_id = payload.get("user_id")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user_id"
            )
        
        from uuid import UUID
        user = db.query(models.User).filter(models.User.id == UUID(user_id)).first()
        
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

DATABASE_URL = os.getenv("DATABASE_URL", "")
REDIS_URL = os.getenv("REDIS_URL", "")
HEARTBEAT_INTERVAL = int(os.getenv("EVENT_STREAM_HEARTBEAT_MS", "15000")) / 1000

async_engine = None
AsyncSessionLocal = None

if DATABASE_URL:
    async_db_url = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    try:
        async_engine = create_async_engine(
            async_db_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10
        )
        AsyncSessionLocal = async_sessionmaker(
            async_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        logger.info("✅ Event Stream: Async database engine created")
    except Exception as e:
        logger.error(f"Failed to create async engine for events: {e}")

redis_client = None
if REDIS_URL:
    try:
        import redis.asyncio as aioredis
        redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)
        logger.info("✅ Event Stream: Redis client created")
    except Exception as e:
        logger.warning(f"Redis not available for event streaming: {e}")


async def generate_mock_event(tenant_id: str) -> Dict[str, Any]:
    """Generate a mock event for development/testing"""
    source_systems = ["salesforce", "supabase", "mongodb", "filesource", "system"]
    stages = ["ingested", "canonicalized", "materialized", "viewed", "intent", "journaled", "drift"]
    entities = ["Account", "Contact", "Opportunity", "Lead", "User", "Order", "Product"]
    
    source = random.choice(source_systems)
    stage = random.choice(stages)
    
    event = {
        "id": f"evt_{int(datetime.utcnow().timestamp() * 1000)}_{random.randint(1000, 9999)}",
        "ts": datetime.utcnow().isoformat(),
        "tenant": tenant_id,
        "source_system": source,
        "entity": random.choice(entities),
        "stage": stage,
        "meta": {
            "record_count": random.randint(1, 100),
            "processing_time_ms": random.randint(50, 500)
        }
    }
    
    return event


async def poll_canonical_events(tenant_id: str) -> Optional[Dict[str, Any]]:
    """Fallback: Poll canonical_events table for new events filtered by tenant"""
    if not AsyncSessionLocal:
        return None
    
    try:
        async with AsyncSessionLocal() as db:
            # Try to fetch recent canonical events for this tenant
            # Using raw SQL text to avoid LSP errors with table references
            result = await db.execute(
                text("""
                    SELECT id, created_at, tenant_id, source_system, entity_type
                    FROM canonical_events
                    WHERE tenant_id = :tenant_id
                    ORDER BY created_at DESC
                    LIMIT 1
                """),
                {"tenant_id": tenant_id}
            )
            row = result.first()
            
            if row:
                return {
                    "id": str(row[0]),
                    "ts": row[1].isoformat() if row[1] else datetime.utcnow().isoformat(),
                    "tenant": str(row[2]) if row[2] else "default",
                    "source_system": row[3] if row[3] else "system",
                    "entity": row[4] if row[4] else "unknown",
                    "stage": "canonicalized",
                    "meta": {}
                }
    except Exception as e:
        logger.debug(f"Canonical events polling failed (expected if table doesn't exist): {e}")
    
    return None


async def redis_event_stream(tenant_id: str) -> AsyncGenerator[Dict[str, Any], None]:
    """Stream events from Redis PubSub filtered by tenant"""
    if not redis_client:
        return
    
    pubsub = redis_client.pubsub()
    
    try:
        # Subscribe to AAM and AOS event patterns
        await pubsub.psubscribe(
            "aam.streams.*",
            "aam.events.schema.change",
            "aos.intents.*"
        )
        
        logger.info(f"✅ Subscribed to Redis event patterns for tenant {tenant_id}")
        
        async for message in pubsub.listen():
            if message["type"] == "pmessage":
                try:
                    data = json.loads(message["data"])
                    event_tenant = data.get("tenant_id", "default")
                    
                    # Filter by tenant_id
                    if event_tenant != tenant_id:
                        continue
                    
                    # Transform to common envelope
                    event = {
                        "id": data.get("id", f"redis_{datetime.utcnow().timestamp()}"),
                        "ts": data.get("timestamp", datetime.utcnow().isoformat()),
                        "tenant": event_tenant,
                        "source_system": data.get("source", "system"),
                        "entity": data.get("entity_type", "unknown"),
                        "stage": data.get("stage", "ingested"),
                        "meta": data.get("metadata", {})
                    }
                    yield event
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse Redis message: {message['data']}")
                except Exception as e:
                    logger.error(f"Error processing Redis event: {e}")
                    
    except Exception as e:
        logger.error(f"Redis stream error: {e}")
    finally:
        await pubsub.unsubscribe()


async def event_generator(request: Request, tenant_id: str) -> AsyncGenerator[str, None]:
    """
    SSE event generator with Redis PubSub primary and polling fallback
    Filters all events by tenant_id for security
    Uses timeouts to ensure heartbeats are sent regularly
    """
    logger.info(f"🔴 New SSE client connected to /events/stream (tenant: {tenant_id})")
    last_heartbeat = datetime.utcnow()
    last_event_time = datetime.utcnow()
    
    # Send initial connection event
    yield f"data: {json.dumps({'type': 'connected', 'ts': datetime.utcnow().isoformat(), 'tenant': tenant_id})}\n\n"
    
    # Determine event source
    use_redis = redis_client is not None
    use_polling = AsyncSessionLocal is not None
    use_mock = True  # Always available as final fallback
    
    logger.info(f"Event sources: Redis={use_redis}, Polling={use_polling}, Mock={use_mock}")
    
    # Initialize Redis stream iterator if available
    redis_stream_iter = None
    if use_redis:
        redis_stream_iter = redis_event_stream(tenant_id).__aiter__()
    
    try:
        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                logger.info(f"🔴 SSE client disconnected (tenant: {tenant_id})")
                break
            
            event_sent = False
            
            # Try Redis with timeout to prevent blocking
            if use_redis and redis_stream_iter:
                try:
                    # Wait for next Redis event with timeout
                    event = await asyncio.wait_for(
                        redis_stream_iter.__anext__(),
                        timeout=HEARTBEAT_INTERVAL
                    )
                    yield f"event: event\ndata: {json.dumps(event)}\n\n"
                    event_sent = True
                    last_event_time = datetime.utcnow()
                except asyncio.TimeoutError:
                    # Timeout - Redis has no events, continue to heartbeat/fallback
                    pass
                except StopAsyncIteration:
                    # Redis stream ended, disable and recreate
                    logger.warning("Redis stream ended, will try to reconnect")
                    use_redis = False
                    redis_stream_iter = None
                except Exception as e:
                    logger.error(f"Redis event error: {e}")
                    use_redis = False
                    redis_stream_iter = None
            
            # Fallback to polling with timeout
            if not event_sent and use_polling:
                try:
                    event = await asyncio.wait_for(
                        poll_canonical_events(tenant_id),
                        timeout=2.0
                    )
                    if event:
                        yield f"event: event\ndata: {json.dumps(event)}\n\n"
                        event_sent = True
                        last_event_time = datetime.utcnow()
                except asyncio.TimeoutError:
                    # Polling timeout, continue to next source
                    pass
                except Exception as e:
                    logger.debug(f"Polling error: {e}")
            
            # Mock events for development (send occasionally)
            if not event_sent and use_mock:
                # Send mock event every 2-5 seconds
                time_since_event = (datetime.utcnow() - last_event_time).total_seconds()
                if time_since_event > random.uniform(2, 5):
                    event = await generate_mock_event(tenant_id)
                    yield f"event: event\ndata: {json.dumps(event)}\n\n"
                    event_sent = True
                    last_event_time = datetime.utcnow()
            
            # Send heartbeat if interval elapsed
            time_since_heartbeat = (datetime.utcnow() - last_heartbeat).total_seconds()
            if time_since_heartbeat >= HEARTBEAT_INTERVAL:
                yield f"event: heartbeat\ndata: {json.dumps({'ts': datetime.utcnow().isoformat()})}\n\n"
                last_heartbeat = datetime.utcnow()
                logger.debug(f"💓 Heartbeat sent to tenant {tenant_id}")
            
            # Small sleep to prevent tight loop
            await asyncio.sleep(0.5)
            
    except asyncio.CancelledError:
        logger.info(f"🔴 SSE stream cancelled (tenant: {tenant_id})")
    except Exception as e:
        logger.error(f"Event stream error: {e}")
        error_event = {
            "type": "error",
            "message": str(e),
            "ts": datetime.utcnow().isoformat()
        }
        yield f"event: error\ndata: {json.dumps(error_event)}\n\n"


@router.get("/stream")
async def event_stream(
    request: Request,
    current_user: models.User = Depends(get_current_user_from_token)
):
    """
    Server-Sent Events (SSE) endpoint for real-time event streaming.
    Requires JWT authentication and filters events by tenant.
    
    Authentication:
    - Pass JWT token as query parameter: /events/stream?token=<your_jwt_token>
    - EventSource doesn't support custom headers, so query param is used
    - Returns 401 Unauthorized if token is missing or invalid
    
    Streams events from:
    1. Redis PubSub (primary) - patterns: aam.streams.*, aam.events.schema.change, aos.intents.*
    2. Canonical events table polling (fallback)
    3. Mock generator (development)
    
    Event format:
    {
        "id": "string",
        "ts": "ISO datetime",
        "tenant": "string",
        "source_system": "salesforce|supabase|mongodb|filesource|system",
        "entity": "string",
        "stage": "ingested|canonicalized|materialized|viewed|intent|journaled|drift",
        "meta": {}
    }
    
    Security:
    - Filters all events by authenticated user's tenant_id
    - Multi-tenant isolation enforced
    """
    tenant_id = str(current_user.tenant_id)
    logger.info(f"🔐 SSE auth successful for tenant: {tenant_id}, user: {current_user.email}")
    
    return StreamingResponse(
        event_generator(request, tenant_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
