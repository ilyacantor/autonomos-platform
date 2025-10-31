"""
FileSource Connector API Endpoints
Provides replay and discovery endpoints for CSV-based ingestion
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from services.aam.connectors.filesource.connector import FileSourceConnector

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/replay")
async def replay_filesource(
    entity: Optional[str] = Query(None, description="Filter by entity: account, opportunity, contact"),
    system: Optional[str] = Query(None, description="Filter by system: salesforce, hubspot, dynamics, etc."),
    tenant_id: str = Query("demo-tenant", description="Tenant identifier"),
    db: Session = Depends(get_db)
):
    """
    Replay FileSource CSV files
    
    Discovers CSV files from mock_sources/, applies mapping registry,
    and emits canonical events to database streams.
    
    Query Parameters:
    - entity: Filter by entity type (account, opportunity, contact) - optional
    - system: Filter by source system (salesforce, hubspot, etc.) - optional
    - tenant_id: Tenant identifier - default "demo-tenant"
    
    Returns:
        Ingestion statistics including files processed and record counts
    """
    try:
        connector = FileSourceConnector(db=db, tenant_id=tenant_id)
        
        logger.info(f"Starting FileSource replay: entity={entity}, system={system}, tenant={tenant_id}")
        
        # Replay with optional filters
        stats = connector.replay_entity(entity=entity, system=system)
        
        logger.info(f"FileSource replay complete: {stats['total_records']} records from {stats['files_processed']} files")
        
        return {
            "success": True,
            "message": f"Replayed {stats['total_records']} records from {stats['files_processed']} files",
            "stats": stats
        }
    
    except Exception as e:
        logger.error(f"FileSource replay failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Replay failed: {str(e)}")


@router.get("/discover")
async def discover_filesource(db: Session = Depends(get_db)):
    """
    Discover available CSV files in mock_sources/
    
    Returns:
        List of discovered files with entity and system information
    """
    try:
        connector = FileSourceConnector(db=db)
        discovered = connector.discover_csv_files()
        
        return {
            "success": True,
            "files_count": len(discovered),
            "files": discovered
        }
    
    except Exception as e:
        logger.error(f"FileSource discovery failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Discovery failed: {str(e)}")


@router.get("/status")
async def filesource_status():
    """
    Get FileSource connector status
    
    Returns:
        Status information about the FileSource connector
    """
    return {
        "success": True,
        "status": "active",
        "feature_enabled": True,
        "sources_directory": "mock_sources/",
        "supported_entities": ["account", "opportunity", "contact"],
        "supported_systems": ["salesforce", "hubspot", "dynamics", "pipedrive", "zendesk"]
    }
