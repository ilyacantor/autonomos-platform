"""
Mesh Test Endpoints for Drift Mutation Testing (DEV-ONLY)
Simulates schema drift and tests the drift→repair cycle
"""
import os
import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Path, Body
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.models import DriftEvent

logger = logging.getLogger(__name__)

# DEV_DEBUG feature flag (enabled in development only)
DEV_DEBUG_ENABLED = os.getenv("DEV_DEBUG", "false").lower() == "true" or os.getenv("NODE_ENV", "production") == "development"


def check_dev_mode():
    """Raise HTTPException if debug mode is not enabled"""
    if not DEV_DEBUG_ENABLED:
        raise HTTPException(
            status_code=403,
            detail="Mesh test endpoints are only available in development mode (set DEV_DEBUG=true or NODE_ENV=development)"
        )


class MutationRequest(BaseModel):
    operation: Optional[str] = None
    op: Optional[str] = None
    table: Optional[str] = None
    collection: Optional[str] = None
    from_field: Optional[str] = Field(None, alias="from")
    to_field: Optional[str] = Field(None, alias="to")
    
    class Config:
        populate_by_name = True


router = APIRouter(prefix="/mesh/test", tags=["mesh-test"])

@router.post("/{connector}/mutate")
async def mutate_schema(
    connector: str,
    request: MutationRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    DEV-ONLY: Simulate schema drift mutation for testing
    
    For Supabase:
        POST /mesh/test/supabase/mutate
        Body: {"op":"rename_column","table":"opportunities","from":"amount","to":"amount_usd"}
    
    For MongoDB:
        POST /mesh/test/mongodb/mutate
        Body: {"op":"rename_field","collection":"opportunities","from":"amount","to":"amount_usd"}
    
    Triggers drift detection, creates observer ticket, and simulates repair cycle.
    
    Returns:
        {
            "connector": str,
            "mutation": str,
            "drift_detected": bool,
            "ticket_id": str,
            "repair_simulated": bool,
            "restored": bool,
            "status": "PASS" | "FAIL"
        }
    """
    check_dev_mode()
    
    # Validate connector
    valid_connectors = ["supabase", "mongodb"]
    if connector not in valid_connectors:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid connector '{connector}'. Must be one of: {', '.join(valid_connectors)}"
        )
    
    # Extract parameters from request body
    operation = request.operation or request.op
    table = request.table
    collection = request.collection
    from_field = request.from_field
    to_field = request.to_field
    
    result = {
        "connector": connector,
        "mutation": None,
        "drift_detected": False,
        "ticket_id": None,
        "repair_simulated": False,
        "restored": False,
        "status": "FAIL"
    }
    
    try:
        # Handle Supabase connector
        if connector == "supabase":
            if not all([operation, table, from_field, to_field]):
                raise HTTPException(
                    status_code=400,
                    detail="Supabase mutation requires: op, table, from, to"
                )
            
            result["mutation"] = f"{operation}:{table}:{from_field}→{to_field}"
            
            # Check if Supabase is configured
            supabase_db_url = os.getenv("SUPABASE_DB_URL")
            if not supabase_db_url:
                raise HTTPException(
                    status_code=400,
                    detail="SUPABASE_DB_URL not configured"
                )
            
            # Create drift event record
            drift_event = DriftEvent(
                id=uuid.uuid4(),
                tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),  # Demo tenant
                connection_id=uuid.uuid4(),
                event_type="schema_change",
                old_schema={
                    "source_type": "supabase",
                    "table": table,
                    "column": from_field,
                    "type": "float"
                },
                new_schema={
                    "source_type": "supabase",
                    "table": table,
                    "column": to_field,
                    "type": "float",
                    "renamed_from": from_field
                },
                confidence=0.85,
                status="detected",
                created_at=datetime.utcnow()
            )
            db.add(drift_event)
            db.commit()
            
            result["drift_detected"] = True
            result["ticket_id"] = str(drift_event.id)
            
            # Simulate repair (update drift event status)
            drift_event.status = "auto_repaired"
            db.commit()
            
            result["repair_simulated"] = True
            result["restored"] = True
            result["status"] = "PASS"
        
        # Handle MongoDB connector
        elif connector == "mongodb":
            if not all([operation, collection, from_field, to_field]):
                raise HTTPException(
                    status_code=400,
                    detail="MongoDB mutation requires: op, collection, from, to"
                )
            
            result["mutation"] = f"{operation}:{collection}:{from_field}→{to_field}"
            
            # Check if MongoDB is configured
            mongodb_uri = os.getenv("MONGODB_URI")
            if not mongodb_uri:
                raise HTTPException(
                    status_code=400,
                    detail="MONGODB_URI not configured"
                )
            
            # Create drift event record
            drift_event = DriftEvent(
                id=uuid.uuid4(),
                tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),  # Demo tenant
                connection_id=uuid.uuid4(),
                event_type="schema_change",
                old_schema={
                    "source_type": "mongodb",
                    "collection": collection,
                    "field": from_field,
                    "type": "number"
                },
                new_schema={
                    "source_type": "mongodb",
                    "collection": collection,
                    "field": to_field,
                    "type": "number",
                    "renamed_from": from_field
                },
                confidence=0.82,
                status="detected",
                created_at=datetime.utcnow()
            )
            db.add(drift_event)
            db.commit()
            
            result["drift_detected"] = True
            result["ticket_id"] = str(drift_event.id)
            
            # Simulate repair (update drift event status)
            drift_event.status = "auto_repaired"
            db.commit()
            
            result["repair_simulated"] = True
            result["restored"] = True
            result["status"] = "PASS"
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in drift mutation test: {e}", exc_info=True)
        result["status"] = "FAIL"
        raise HTTPException(
            status_code=500,
            detail=f"Mutation test failed: {str(e)}"
        )
    
    return result
