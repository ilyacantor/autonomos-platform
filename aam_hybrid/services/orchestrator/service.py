import logging
import httpx
import uuid
import sys
from pathlib import Path
from typing import List, Optional, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from fastapi import WebSocket

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared import (
    settings,
    airbyte_client,
    Connection,
    SyncCatalogVersion,
    JobHistory,
    ConnectionStatus,
    JobStatus,
    ConnectionCreate,
    ConnectionResponse
)

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    WebSocket Connection Manager
    Manages active WebSocket connections and broadcasts status updates
    """
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"✅ WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        self.active_connections.discard(websocket)
        logger.info(f"❌ WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected WebSocket clients"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.active_connections.discard(conn)


# Global manager instance
manager = ConnectionManager()


async def handle_status_update(event_data: dict):
    """
    Handle status update events from event bus
    Broadcast to all WebSocket clients
    
    Args:
        event_data: StatusUpdate event data
    """
    try:
        logger.info(f"📡 Broadcasting status update: {event_data.get('status')}")
        await manager.broadcast(event_data)
    except Exception as e:
        logger.error(f"Error broadcasting status update: {e}")


async def onboard_connection(
    db: AsyncSession,
    connection_data: ConnectionCreate
) -> ConnectionResponse:
    """
    Onboard a new connection to AAM
    
    Implementation Flow:
    1. Call Auth Broker to get credentials
    2. Get source definition ID from Airbyte
    3. Create source in Airbyte
    4. Discover schema from source
    5. Create connection in Airbyte
    6. Store in Registry with initial catalog version
    
    Args:
        db: Database session
        connection_data: Connection configuration
    
    Returns:
        Created connection object
    """
    logger.info(f"Starting onboarding for: {connection_data.connection_name}")
    
    try:
        async with httpx.AsyncClient() as client:
            auth_broker_url = f"http://localhost:{settings.SERVICE_PORT_AUTH_BROKER}"
            response = await client.get(
                f"{auth_broker_url}/credentials/{connection_data.source_type.lower()}/{connection_data.credential_id}"
            )
            response.raise_for_status()
            source_config = response.json()
        
        logger.info("Retrieved credentials from Auth Broker")
    except Exception as e:
        logger.error(f"Failed to retrieve credentials: {e}")
        raise Exception(f"Auth Broker error: {e}")
    
    try:
        source_definition_id = await airbyte_client.get_source_definition_id(connection_data.source_type)
        if not source_definition_id:
            raise Exception(f"Source definition not found for: {connection_data.source_type}")
        
        logger.info(f"Source definition ID: {source_definition_id}")
    except Exception as e:
        logger.error(f"Failed to get source definition: {e}")
        raise
    
    if not settings.AIRBYTE_WORKSPACE_ID:
        raise Exception("AIRBYTE_WORKSPACE_ID not configured")
    
    if not settings.AIRBYTE_DESTINATION_ID:
        raise Exception("AIRBYTE_DESTINATION_ID not configured")
    
    try:
        source_result = await airbyte_client.create_source(
            workspace_id=settings.AIRBYTE_WORKSPACE_ID,
            source_definition_id=source_definition_id,
            connection_configuration=source_config,
            name=connection_data.connection_name
        )
        
        airbyte_source_id = source_result.get("sourceId")
        if not airbyte_source_id:
            raise Exception("No sourceId returned from Airbyte")
        logger.info(f"Created Airbyte source: {airbyte_source_id}")
    except Exception as e:
        logger.error(f"Failed to create Airbyte source: {e}")
        raise Exception(f"Airbyte source creation failed: {e}")
    
    try:
        schema_result = await airbyte_client.discover_schema(airbyte_source_id)
        sync_catalog = schema_result.get("catalog", {})
        
        logger.info(f"Discovered schema with {len(sync_catalog.get('streams', []))} streams")
    except Exception as e:
        logger.error(f"Failed to discover schema: {e}")
        raise Exception(f"Schema discovery failed: {e}")
    
    try:
        connection_result = await airbyte_client.create_connection(
            source_id=airbyte_source_id,
            destination_id=settings.AIRBYTE_DESTINATION_ID,
            sync_catalog=sync_catalog,
            name=f"{connection_data.connection_name} Connection"
        )
        
        airbyte_connection_id = connection_result.get("connectionId")
        logger.info(f"Created Airbyte connection: {airbyte_connection_id}")
    except Exception as e:
        logger.error(f"Failed to create Airbyte connection: {e}")
        raise Exception(f"Airbyte connection creation failed: {e}")
    
    try:
        connection = Connection(
            name=connection_data.connection_name,
            source_type=connection_data.source_type,
            airbyte_source_id=uuid.UUID(airbyte_source_id),
            airbyte_connection_id=uuid.UUID(airbyte_connection_id),
            status=ConnectionStatus.ACTIVE
        )
        
        db.add(connection)
        await db.flush()
        
        catalog_version = SyncCatalogVersion(
            connection_id=connection.id,
            sync_catalog=sync_catalog,
            version_number=1
        )
        
        db.add(catalog_version)
        await db.commit()
        await db.refresh(connection)
        
        logger.info(f"Connection onboarded successfully: {connection.id}")
        
        return ConnectionResponse.model_validate(connection)
    
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to store connection in registry: {e}")
        raise Exception(f"Registry update failed: {e}")


async def get_connection_by_id(
    db: AsyncSession,
    connection_id: str
) -> Optional[ConnectionResponse]:
    """Get connection by ID"""
    try:
        connection_uuid = uuid.UUID(connection_id)
    except ValueError:
        return None
    
    result = await db.execute(
        select(Connection).where(Connection.id == connection_uuid)
    )
    connection = result.scalar_one_or_none()
    
    if connection:
        return ConnectionResponse.model_validate(connection)
    return None


async def list_connections(db: AsyncSession) -> List[ConnectionResponse]:
    """List all connections"""
    result = await db.execute(select(Connection))
    connections = result.scalars().all()
    
    return [ConnectionResponse.model_validate(conn) for conn in connections]


async def trigger_connection_sync(
    db: AsyncSession,
    connection_id: str
) -> dict:
    """
    Trigger a sync for a connection
    
    Args:
        db: Database session
        connection_id: AAM connection UUID
    
    Returns:
        Job trigger response
    """
    connection = await get_connection_by_id(db, connection_id)
    if not connection:
        raise Exception(f"Connection not found: {connection_id}")
    
    if not connection.airbyte_connection_id:
        raise Exception(f"Connection has no Airbyte connection ID: {connection_id}")
    
    try:
        sync_result = await airbyte_client.trigger_sync(str(connection.airbyte_connection_id))
        
        job_id = sync_result.get("jobId")
        
        job = JobHistory(
            connection_id=uuid.UUID(connection_id),
            airbyte_job_id=job_id,
            status=JobStatus.RUNNING
        )
        
        db.add(job)
        await db.commit()
        
        logger.info(f"Sync triggered for connection {connection_id}, job: {job_id}")
        
        return {
            "connection_id": connection_id,
            "job_id": job_id,
            "status": "triggered",
            "message": "Sync job started successfully"
        }
    
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to trigger sync: {e}")
        raise
