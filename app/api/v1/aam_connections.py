"""
AAM Connection Management API Endpoints

Production-ready API endpoints for managing AAM connector connections.
Provides CRUD operations and health checking for all supported connector types.

Supported connector types:
- Salesforce: CRM integration
- Supabase: PostgreSQL database integration
- MongoDB: NoSQL database integration
- FileSource: CSV/JSON/YAML file-based sources
"""

import sys
import logging
from uuid import UUID
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

sys.path.insert(0, 'aam_hybrid')

from core.connection_manager import connection_manager
from shared.models import ConnectionStatus
from connectors import (
    salesforce_adapter,
    supabase_adapter,
    mongodb_adapter,
    filesource_adapter
)
from app.security import get_current_user
from app.models import User

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionCreateRequest(BaseModel):
    """Request model for creating a new connection"""
    name: str = Field(..., description="Human-readable name for the connection", min_length=1, max_length=255)
    source_type: str = Field(..., description="Type of source (Salesforce, Supabase, MongoDB, FileSource)")
    connector_config: Dict[str, Any] = Field(..., description="Connector-specific configuration (credentials, URLs, etc.)")
    
    class Config:
        schema_extra = {
            "example": {
                "name": "Salesforce Production",
                "source_type": "Salesforce",
                "connector_config": {
                    "instance_url": "https://mycompany.salesforce.com",
                    "access_token": "00D..."
                }
            }
        }


class ConnectionResponse(BaseModel):
    """Response model for connection details"""
    id: UUID = Field(..., description="Unique identifier for the connection")
    name: str = Field(..., description="Human-readable connection name")
    source_type: str = Field(..., description="Type of data source")
    status: str = Field(..., description="Current connection status")
    connector_config: Optional[Dict[str, Any]] = Field(None, description="Connector configuration (sanitized)")
    created_at: datetime = Field(..., description="Timestamp when connection was created")
    updated_at: datetime = Field(..., description="Timestamp when connection was last updated")
    last_health_check: Optional[datetime] = Field(None, description="Timestamp of last health check")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Salesforce Production",
                "source_type": "Salesforce",
                "status": "ACTIVE",
                "connector_config": {"instance_url": "https://mycompany.salesforce.com"},
                "created_at": "2025-11-04T12:00:00Z",
                "updated_at": "2025-11-04T12:30:00Z",
                "last_health_check": "2025-11-04T12:30:00Z"
            }
        }


class ConnectionListResponse(BaseModel):
    """Response model for list of connections"""
    connections: List[ConnectionResponse] = Field(..., description="List of connections")
    total: int = Field(..., description="Total number of connections")


class HealthCheckResponse(BaseModel):
    """Response model for health check results"""
    connection_id: UUID = Field(..., description="Connection identifier")
    status: str = Field(..., description="Health status (healthy, degraded, down)")
    response_time_ms: float = Field(..., description="Response time in milliseconds")
    error_message: Optional[str] = Field(None, description="Error message if health check failed")
    checked_at: datetime = Field(..., description="Timestamp when health check was performed")
    connection_status: str = Field(..., description="Updated connection status")


class DeleteResponse(BaseModel):
    """Response model for connection deletion"""
    success: bool = Field(..., description="Whether deletion was successful")
    message: str = Field(..., description="Status message")
    connection_id: UUID = Field(..., description="ID of deleted connection")


def sanitize_config(config: Dict[str, Any], source_type: str) -> Dict[str, Any]:
    """
    Sanitize connector configuration to remove sensitive data from responses.
    
    Args:
        config: Original configuration dictionary
        source_type: Type of connector
        
    Returns:
        Sanitized configuration safe for API responses
    """
    if not config:
        return {}
    
    sanitized = config.copy()
    
    sensitive_keys = [
        'access_token', 'refresh_token', 'api_key', 'secret_key',
        'service_key', 'password', 'private_key', 'client_secret'
    ]
    
    for key in sensitive_keys:
        if key in sanitized:
            sanitized[key] = '***REDACTED***'
    
    return sanitized


def get_connector_adapter(source_type: str):
    """
    Get the appropriate connector adapter for the given source type.
    
    Args:
        source_type: Type of data source
        
    Returns:
        Connector adapter module
        
    Raises:
        HTTPException: If source type is not supported
    """
    adapters = {
        'Salesforce': salesforce_adapter,
        'salesforce': salesforce_adapter,
        'Supabase': supabase_adapter,
        'supabase': supabase_adapter,
        'MongoDB': mongodb_adapter,
        'mongodb': mongodb_adapter,
        'FileSource': filesource_adapter,
        'filesource': filesource_adapter,
    }
    
    adapter = adapters.get(source_type)
    if not adapter:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported source type: {source_type}. Supported types: Salesforce, Supabase, MongoDB, FileSource"
        )
    
    return adapter


@router.post(
    "/connections",
    response_model=ConnectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new connector",
    description="Register a new data source connector with the AAM system. "
                "The connector configuration will be validated before registration."
)
async def create_connection(
    request: ConnectionCreateRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Register a new connector connection.
    
    This endpoint:
    1. Validates the connector configuration
    2. Registers the connection in the database
    3. Returns the connection details with assigned ID
    
    **Authentication Required**: Bearer token in Authorization header
    
    **Supported Source Types**:
    - Salesforce: Requires instance_url and access_token
    - Supabase: Requires url and service_key
    - MongoDB: Requires connection_string and database
    - FileSource: Requires file_path and format
    """
    try:
        adapter = get_connector_adapter(request.source_type)
        
        is_valid = await adapter.validate_config(request.connector_config)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid connector configuration for {request.source_type}. "
                       f"Please check the configuration format and required fields."
            )
        
        connection = await connection_manager.register_connector(
            name=request.name,
            source_type=request.source_type,
            config=request.connector_config
        )
        
        logger.info(
            f"User {current_user.email} created connection: {connection.name} "
            f"(id: {connection.id}, type: {connection.source_type})"
        )
        
        return ConnectionResponse(
            id=connection.id,
            name=connection.name,
            source_type=connection.source_type,
            status=connection.status.value,
            connector_config=sanitize_config(connection.connector_config, connection.source_type),
            created_at=connection.created_at,
            updated_at=connection.updated_at,
            last_health_check=connection.last_health_check
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating connection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create connection: {str(e)}"
        )


@router.get(
    "/connections",
    response_model=ConnectionListResponse,
    summary="List all connections",
    description="Retrieve a list of all registered connections with optional filtering by source type and status."
)
async def list_connections(
    source_type: Optional[str] = Query(None, description="Filter by source type (Salesforce, Supabase, MongoDB, FileSource)"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (PENDING, ACTIVE, FAILED, HEALING, INACTIVE)"),
    current_user: User = Depends(get_current_user)
):
    """
    List all registered connections.
    
    This endpoint returns all connections registered in the AAM system,
    with optional filtering by source type and connection status.
    
    **Authentication Required**: Bearer token in Authorization header
    
    **Query Parameters**:
    - source_type: Filter by connector type
    - status: Filter by connection status
    """
    try:
        connection_status = None
        if status_filter:
            try:
                connection_status = ConnectionStatus(status_filter)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status filter: {status_filter}. "
                           f"Valid values: PENDING, ACTIVE, FAILED, HEALING, INACTIVE"
                )
        
        connections = await connection_manager.list_connections(
            source_type=source_type,
            status=connection_status
        )
        
        response_connections = [
            ConnectionResponse(
                id=conn.id,
                name=conn.name,
                source_type=conn.source_type,
                status=conn.status.value,
                connector_config=sanitize_config(conn.connector_config, conn.source_type),
                created_at=conn.created_at,
                updated_at=conn.updated_at,
                last_health_check=conn.last_health_check
            )
            for conn in connections
        ]
        
        logger.info(
            f"User {current_user.email} listed {len(connections)} connections "
            f"(source_type={source_type}, status={status_filter})"
        )
        
        return ConnectionListResponse(
            connections=response_connections,
            total=len(response_connections)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing connections: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list connections: {str(e)}"
        )


@router.get(
    "/connections/{connection_id}",
    response_model=ConnectionResponse,
    summary="Get connection details",
    description="Retrieve detailed information about a specific connection by its ID."
)
async def get_connection(
    connection_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed information about a specific connection.
    
    This endpoint retrieves full details about a connection including
    its configuration (with sensitive data sanitized), status, and timestamps.
    
    **Authentication Required**: Bearer token in Authorization header
    
    **Path Parameters**:
    - connection_id: UUID of the connection to retrieve
    """
    try:
        connection = await connection_manager.get_connection(connection_id)
        
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connection not found: {connection_id}"
            )
        
        logger.info(
            f"User {current_user.email} retrieved connection: {connection.name} "
            f"(id: {connection_id})"
        )
        
        return ConnectionResponse(
            id=connection.id,
            name=connection.name,
            source_type=connection.source_type,
            status=connection.status.value,
            connector_config=sanitize_config(connection.connector_config, connection.source_type),
            created_at=connection.created_at,
            updated_at=connection.updated_at,
            last_health_check=connection.last_health_check
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving connection {connection_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve connection: {str(e)}"
        )


@router.post(
    "/connections/{connection_id}/health-check",
    response_model=HealthCheckResponse,
    summary="Run health check",
    description="Execute a health check on the specified connection and update its status based on the results."
)
async def run_health_check(
    connection_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """
    Run a health check on a connection.
    
    This endpoint:
    1. Retrieves the connection details
    2. Executes the appropriate connector's health check
    3. Updates the connection status based on results
    4. Returns the health check results
    
    **Authentication Required**: Bearer token in Authorization header
    
    **Path Parameters**:
    - connection_id: UUID of the connection to check
    
    **Health Status Values**:
    - healthy: Connection is working normally
    - degraded: Connection is slow but functional
    - down: Connection is not accessible
    """
    try:
        connection = await connection_manager.get_connection(connection_id)
        
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connection not found: {connection_id}"
            )
        
        adapter = get_connector_adapter(connection.source_type)
        
        health_result = await adapter.health_check(connection.connector_config)
        
        health_status = health_result.get('status', 'down')
        
        if health_status == 'healthy':
            new_status = ConnectionStatus.ACTIVE
        elif health_status == 'degraded':
            new_status = ConnectionStatus.HEALING
        else:
            new_status = ConnectionStatus.FAILED
        
        updated_connection = await connection_manager.update_health_status(
            connection_id=connection_id,
            status=new_status
        )
        
        if not updated_connection:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update connection health status"
            )
        
        logger.info(
            f"User {current_user.email} ran health check on connection: {connection.name} "
            f"(id: {connection_id}, status: {health_status}, new_status: {new_status.value})"
        )
        
        return HealthCheckResponse(
            connection_id=connection_id,
            status=health_status,
            response_time_ms=health_result.get('response_time_ms', 0),
            error_message=health_result.get('error_message'),
            checked_at=datetime.utcnow(),
            connection_status=new_status.value
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running health check on connection {connection_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run health check: {str(e)}"
        )


@router.delete(
    "/connections/{connection_id}",
    response_model=DeleteResponse,
    summary="Delete connection",
    description="Deregister and delete a connection from the AAM system. "
                "This will cascade delete all related catalog versions and job history."
)
async def delete_connection(
    connection_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """
    Delete a connection.
    
    This endpoint permanently removes a connection from the AAM system.
    All related data (catalog versions, job history) will be cascade deleted.
    
    **Authentication Required**: Bearer token in Authorization header
    
    **Path Parameters**:
    - connection_id: UUID of the connection to delete
    
    **Warning**: This operation cannot be undone.
    """
    try:
        connection = await connection_manager.get_connection(connection_id)
        
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connection not found: {connection_id}"
            )
        
        connection_name = connection.name
        
        deleted = await connection_manager.delete_connection(connection_id)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete connection"
            )
        
        logger.info(
            f"User {current_user.email} deleted connection: {connection_name} "
            f"(id: {connection_id})"
        )
        
        return DeleteResponse(
            success=True,
            message=f"Connection '{connection_name}' successfully deleted",
            connection_id=connection_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting connection {connection_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete connection: {str(e)}"
        )
