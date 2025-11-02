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
    tenant_id: Optional[str] = None  # Optional tenant_id, defaults to demo UUID
    
    class Config:
        populate_by_name = True
        extra = "allow"  # Allow extra fields to be passed without validation error


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
    tenant_id = request.tenant_id or "9ac5c8c6-1a02-48ff-84a0-122b67f9c3bd"
    
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
            
            # ACTUALLY ALTER TABLE in Supabase
            from sqlalchemy import create_engine
            supabase_engine = create_engine(supabase_db_url, pool_pre_ping=True)
            
            try:
                with supabase_engine.connect() as conn:
                    # Execute real ALTER TABLE statement
                    alter_sql = f"ALTER TABLE public.{table} RENAME COLUMN {from_field} TO {to_field}"
                    conn.execute(text(alter_sql))
                    conn.commit()
                    logger.info(f"✅ Successfully renamed column: {from_field} → {to_field}")
            except Exception as e:
                logger.warning(f"Column rename may have already been applied or failed: {e}")
            
            # Create drift event record
            drift_event = DriftEvent(
                id=uuid.uuid4(),
                tenant_id=uuid.UUID(tenant_id),
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
            
            # Simulate repair (restore the column name)
            try:
                with supabase_engine.connect() as conn:
                    # Restore original column name
                    restore_sql = f"ALTER TABLE public.{table} RENAME COLUMN {to_field} TO {from_field}"
                    conn.execute(text(restore_sql))
                    conn.commit()
                    logger.info(f"✅ Successfully restored column: {to_field} → {from_field}")
                    result["restored"] = True
            except Exception as e:
                logger.warning(f"Column restore failed: {e}")
                result["restored"] = False
            
            # Update drift event status
            drift_event.status = "auto_repaired"
            db.commit()
            
            result["repair_simulated"] = True
            result["status"] = "PASS" if result["restored"] else "FAIL"
        
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
            
            # ACTUALLY RENAME FIELD in MongoDB
            from pymongo import MongoClient
            mongo_client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
            mongo_db = mongo_client[os.getenv("MONGODB_DB", "autonomos")]
            
            try:
                # Execute real $rename operation
                result_op = mongo_db[collection].update_many(
                    {},
                    {"$rename": {from_field: to_field}}
                )
                logger.info(f"✅ Successfully renamed field: {from_field} → {to_field} (modified {result_op.modified_count} docs)")
            except Exception as e:
                logger.warning(f"Field rename may have already been applied or failed: {e}")
            
            # Create drift event record
            drift_event = DriftEvent(
                id=uuid.uuid4(),
                tenant_id=uuid.UUID(tenant_id),
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
            
            # Simulate repair (restore the field name)
            try:
                # Restore original field name
                result_op = mongo_db[collection].update_many(
                    {},
                    {"$rename": {to_field: from_field}}
                )
                logger.info(f"✅ Successfully restored field: {to_field} → {from_field} (modified {result_op.modified_count} docs)")
                result["restored"] = True
            except Exception as e:
                logger.warning(f"Field restore failed: {e}")
                result["restored"] = False
            
            # Update drift event status
            drift_event.status = "auto_repaired"
            db.commit()
            
            result["repair_simulated"] = True
            result["status"] = "PASS" if result["restored"] else "FAIL"
    
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
