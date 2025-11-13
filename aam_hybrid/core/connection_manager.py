"""
AAM Connection Lifecycle Manager

Manages the lifecycle of all AAM connector connections including:
- Registration of new connectors (Salesforce, Supabase, MongoDB, FileSource)
- Connection status tracking and updates
- Health check management
- Connection CRUD operations

All operations are async to support the async database layer.
"""

import uuid
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared import Connection, ConnectionStatus
from shared.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages the full lifecycle of AAM connections.
    
    Responsibilities:
    - Register new connectors with configuration
    - Track connection health and status
    - Provide CRUD operations for connections
    - Update health check timestamps
    """
    
    def __init__(self):
        """Initialize the connection manager."""
        logger.info("ConnectionManager initialized")
    
    async def register_connector(
        self,
        name: str,
        source_type: str,
        tenant_id: uuid.UUID,
        config: Optional[Dict[str, Any]] = None
    ) -> Connection:
        """
        Register a new connector connection in the database.
        
        Args:
            name: Human-readable name for the connection
            source_type: Type of source (e.g., 'Salesforce', 'Supabase', 'MongoDB', 'FileSource')
            tenant_id: UUID of the tenant that owns this connection
            config: Connector-specific configuration stored in JSONB field
            
        Returns:
            Connection: The newly created connection object
            
        Raises:
            Exception: If database operation fails
        """
        async with AsyncSessionLocal() as session:
            try:
                connection = Connection(
                    name=name,
                    source_type=source_type,
                    tenant_id=tenant_id,
                    connector_config=config or {},
                    status=ConnectionStatus.PENDING
                )
                
                session.add(connection)
                await session.commit()
                await session.refresh(connection)
                
                logger.info(
                    f"Registered new connector: {name} (type: {source_type}, id: {connection.id})"
                )
                
                return connection
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to register connector {name}: {e}")
                raise
    
    async def get_connection(self, connection_id: uuid.UUID) -> Optional[Connection]:
        """
        Retrieve a connection by its ID.
        
        Args:
            connection_id: UUID of the connection to retrieve
            
        Returns:
            Connection object if found, None otherwise
        """
        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(
                    select(Connection).where(Connection.id == connection_id)
                )
                connection = result.scalar_one_or_none()
                
                if connection:
                    logger.debug(f"Retrieved connection: {connection.name} ({connection_id})")
                else:
                    logger.warning(f"Connection not found: {connection_id}")
                
                return connection
                
            except Exception as e:
                logger.error(f"Error retrieving connection {connection_id}: {e}")
                raise
    
    async def list_connections(
        self,
        source_type: Optional[str] = None,
        status: Optional[ConnectionStatus] = None
    ) -> List[Connection]:
        """
        List all connections with optional filtering.
        
        Args:
            source_type: Optional filter by source type
            status: Optional filter by connection status
            
        Returns:
            List of Connection objects matching the filters
        """
        async with AsyncSessionLocal() as session:
            try:
                query = select(Connection)
                
                if source_type:
                    query = query.where(Connection.source_type == source_type)
                
                if status:
                    query = query.where(Connection.status == status)
                
                query = query.order_by(Connection.created_at.desc())
                
                result = await session.execute(query)
                connections = result.scalars().all()
                
                logger.info(
                    f"Listed {len(connections)} connections "
                    f"(source_type={source_type}, status={status})"
                )
                
                return list(connections)
                
            except Exception as e:
                logger.error(f"Error listing connections: {e}")
                raise
    
    async def update_status(
        self,
        connection_id: uuid.UUID,
        status: ConnectionStatus
    ) -> Optional[Connection]:
        """
        Update the status of a connection.
        
        Args:
            connection_id: UUID of the connection to update
            status: New ConnectionStatus value
            
        Returns:
            Updated Connection object if found, None otherwise
        """
        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(
                    select(Connection).where(Connection.id == connection_id)
                )
                connection = result.scalar_one_or_none()
                
                if not connection:
                    logger.warning(f"Cannot update status: connection {connection_id} not found")
                    return None
                
                connection.status = status
                connection.updated_at = datetime.utcnow()
                
                await session.commit()
                await session.refresh(connection)
                
                logger.info(
                    f"Updated connection {connection.name} ({connection_id}) status to {status.value}"
                )
                
                return connection
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Error updating connection status {connection_id}: {e}")
                raise
    
    async def update_health_status(
        self,
        connection_id: uuid.UUID,
        status: ConnectionStatus
    ) -> Optional[Connection]:
        """
        Update health check status and timestamp for a connection.
        
        This method updates both the connection status and the last_health_check
        timestamp to track when the health check was performed.
        
        Args:
            connection_id: UUID of the connection to update
            status: New ConnectionStatus value (typically ACTIVE, FAILED, or HEALING)
            
        Returns:
            Updated Connection object if found, None otherwise
        """
        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(
                    select(Connection).where(Connection.id == connection_id)
                )
                connection = result.scalar_one_or_none()
                
                if not connection:
                    logger.warning(
                        f"Cannot update health status: connection {connection_id} not found"
                    )
                    return None
                
                connection.status = status
                connection.last_health_check = datetime.utcnow()
                connection.updated_at = datetime.utcnow()
                
                await session.commit()
                await session.refresh(connection)
                
                logger.info(
                    f"Updated health status for {connection.name} ({connection_id}): "
                    f"{status.value} at {connection.last_health_check}"
                )
                
                return connection
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Error updating health status for {connection_id}: {e}")
                raise
    
    async def update_config(
        self,
        connection_id: uuid.UUID,
        config: Dict[str, Any]
    ) -> Optional[Connection]:
        """
        Update the connector configuration for a connection.
        
        Args:
            connection_id: UUID of the connection to update
            config: New connector-specific configuration
            
        Returns:
            Updated Connection object if found, None otherwise
        """
        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(
                    select(Connection).where(Connection.id == connection_id)
                )
                connection = result.scalar_one_or_none()
                
                if not connection:
                    logger.warning(f"Cannot update config: connection {connection_id} not found")
                    return None
                
                connection.connector_config = config
                connection.updated_at = datetime.utcnow()
                
                await session.commit()
                await session.refresh(connection)
                
                logger.info(f"Updated config for connection {connection.name} ({connection_id})")
                
                return connection
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Error updating connection config {connection_id}: {e}")
                raise
    
    async def delete_connection(self, connection_id: uuid.UUID) -> bool:
        """
        Delete a connection from the database.
        
        This will also cascade delete related catalog versions and job history
        due to the CASCADE configuration in the model relationships.
        
        Args:
            connection_id: UUID of the connection to delete
            
        Returns:
            True if connection was deleted, False if not found
        """
        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(
                    select(Connection).where(Connection.id == connection_id)
                )
                connection = result.scalar_one_or_none()
                
                if not connection:
                    logger.warning(f"Cannot delete: connection {connection_id} not found")
                    return False
                
                connection_name = connection.name
                
                await session.delete(connection)
                await session.commit()
                
                logger.info(
                    f"Deleted connection {connection_name} ({connection_id}) "
                    f"and all related records"
                )
                
                return True
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Error deleting connection {connection_id}: {e}")
                raise
    
    async def connect(self, connection_id: uuid.UUID) -> Optional[Connection]:
        """
        Activate a connection by transitioning it to ACTIVE status.
        
        This is a lifecycle method that represents establishing a connection
        to the external data source.
        
        Args:
            connection_id: UUID of the connection to activate
            
        Returns:
            Updated Connection object if successful, None otherwise
        """
        logger.info(f"Connecting to connection {connection_id}")
        return await self.update_status(connection_id, ConnectionStatus.ACTIVE)
    
    async def disconnect(self, connection_id: uuid.UUID) -> Optional[Connection]:
        """
        Deactivate a connection by transitioning it to INACTIVE status.
        
        This is a lifecycle method that represents gracefully disconnecting
        from the external data source.
        
        Args:
            connection_id: UUID of the connection to deactivate
            
        Returns:
            Updated Connection object if successful, None otherwise
        """
        logger.info(f"Disconnecting connection {connection_id}")
        return await self.update_status(connection_id, ConnectionStatus.INACTIVE)
    
    async def reconnect(self, connection_id: uuid.UUID) -> Optional[Connection]:
        """
        Reconnect a failed or inactive connection.
        
        This transitions the connection through HEALING status before
        attempting to restore it to ACTIVE.
        
        Args:
            connection_id: UUID of the connection to reconnect
            
        Returns:
            Updated Connection object if successful, None otherwise
        """
        logger.info(f"Reconnecting connection {connection_id}")
        
        await self.update_status(connection_id, ConnectionStatus.HEALING)
        
        return await self.update_status(connection_id, ConnectionStatus.ACTIVE)
    
    async def get_connections_by_type(self, source_type: str) -> List[Connection]:
        """
        Get all connections for a specific source type.
        
        Args:
            source_type: Type of source to filter by
            
        Returns:
            List of connections matching the source type
        """
        return await self.list_connections(source_type=source_type)
    
    async def get_active_connections(self) -> List[Connection]:
        """
        Get all currently active connections.
        
        Returns:
            List of connections with ACTIVE status
        """
        return await self.list_connections(status=ConnectionStatus.ACTIVE)
    
    async def get_failed_connections(self) -> List[Connection]:
        """
        Get all failed connections that may need attention.
        
        Returns:
            List of connections with FAILED status
        """
        return await self.list_connections(status=ConnectionStatus.FAILED)


connection_manager = ConnectionManager()
