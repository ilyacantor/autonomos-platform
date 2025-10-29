import logging
import uuid
import sys
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared import (
    airbyte_client,
    Connection,
    SyncCatalogVersion,
    ConnectionStatus,
    CatalogUpdate
)

logger = logging.getLogger(__name__)


async def apply_catalog_update(
    db: AsyncSession,
    catalog_update: CatalogUpdate
) -> dict:
    """
    Apply a new syncCatalog to heal connection drift
    
    Implementation Flow:
    1. Retrieve connection from Registry
    2. Update status to HEALING
    3. Call Airbyte API to update connection
    4. Insert new catalog version
    5. Update status to ACTIVE
    
    Args:
        db: Database session
        catalog_update: Update payload with connection ID and new catalog
    
    Returns:
        Update result with new version number
    """
    logger.info(f"Starting catalog update for connection: {catalog_update.connection_id}")
    
    result = await db.execute(
        select(Connection).where(Connection.id == catalog_update.connection_id)
    )
    connection = result.scalar_one_or_none()
    
    if not connection:
        raise Exception(f"Connection not found: {catalog_update.connection_id}")
    
    if not connection.airbyte_connection_id:
        raise Exception(f"Connection has no Airbyte connection ID: {catalog_update.connection_id}")
    
    try:
        connection.status = ConnectionStatus.HEALING
        await db.commit()
        
        logger.info(f"Connection status set to HEALING")
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update status: {e}")
        raise
    
    try:
        await airbyte_client.update_connection(
            connection_id=str(connection.airbyte_connection_id),
            sync_catalog=catalog_update.new_sync_catalog
        )
        
        logger.info("Airbyte connection catalog updated successfully")
    except Exception as e:
        connection.status = ConnectionStatus.FAILED
        await db.commit()
        logger.error(f"Failed to update Airbyte connection: {e}")
        raise Exception(f"Airbyte catalog update failed: {e}")
    
    try:
        version_result = await db.execute(
            select(func.max(SyncCatalogVersion.version_number))
            .where(SyncCatalogVersion.connection_id == catalog_update.connection_id)
        )
        current_version = version_result.scalar() or 0
        new_version_number = current_version + 1
        
        new_catalog_version = SyncCatalogVersion(
            connection_id=catalog_update.connection_id,
            sync_catalog=catalog_update.new_sync_catalog,
            version_number=new_version_number
        )
        
        db.add(new_catalog_version)
        
        connection.status = ConnectionStatus.ACTIVE
        
        await db.commit()
        
        logger.info(f"Catalog version {new_version_number} created, status set to ACTIVE")
        
        return {
            "connection_id": str(catalog_update.connection_id),
            "previous_version": current_version,
            "new_version": new_version_number,
            "status": "success",
            "message": "Catalog updated and versioned successfully"
        }
    
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to version catalog: {e}")
        raise Exception(f"Registry versioning failed: {e}")
