from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from aam_hybrid.shared import (
    settings, get_db, init_db, HealthResponse,
    ConnectionCreate, ConnectionResponse, SyncTrigger
)
from .service import (
    onboard_connection,
    trigger_connection_sync,
    get_connection_by_id,
    list_connections
)
from .startup_check import validate_configuration

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AAM Orchestrator",
    description="Central orchestration service for Adaptive API Mesh",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize database and validate configuration on startup"""
    logger.info("Validating configuration...")
    validate_configuration()
    
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized successfully")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(service="orchestrator")


@app.post("/connections/onboard", response_model=ConnectionResponse, status_code=201)
async def create_connection(
    connection_data: ConnectionCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Onboard a new connection to AAM
    
    Flow:
    1. Retrieve credentials from Auth Broker
    2. Create source in Airbyte
    3. Discover schema
    4. Create connection with discovered catalog
    5. Store in Registry with version 1 catalog
    
    Args:
        connection_data: Connection configuration
    
    Returns:
        AAM Connection object with IDs
    """
    try:
        connection = await onboard_connection(db, connection_data)
        return connection
    except Exception as e:
        logger.error(f"Connection onboarding failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/connections", response_model=list[ConnectionResponse])
async def get_connections(db: AsyncSession = Depends(get_db)):
    """
    List all connections
    
    Returns:
        List of all AAM connections
    """
    try:
        connections = await list_connections(db)
        return connections
    except Exception as e:
        logger.error(f"Failed to list connections: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/connections/{connection_id}", response_model=ConnectionResponse)
async def get_connection(connection_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get connection by ID
    
    Args:
        connection_id: AAM connection UUID
    
    Returns:
        Connection details
    """
    try:
        connection = await get_connection_by_id(db, connection_id)
        if not connection:
            raise HTTPException(status_code=404, detail=f"Connection not found: {connection_id}")
        return connection
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get connection {connection_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/connections/{connection_id}/sync")
async def trigger_sync(
    connection_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger a sync for a connection
    
    Args:
        connection_id: AAM connection UUID
    
    Returns:
        Job trigger confirmation
    """
    try:
        result = await trigger_connection_sync(db, connection_id)
        return result
    except Exception as e:
        logger.error(f"Failed to trigger sync for {connection_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.SERVICE_PORT_ORCHESTRATOR)
