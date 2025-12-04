"""
AAM Mesh API - Drift Mutation and Repair Endpoints
Provides testing endpoints for schema drift simulation and repair approval
"""
import os
import logging
import uuid
import re
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from pymongo import MongoClient
from app.database import get_db
from app.models import SchemaChange, DriftEvent

logger = logging.getLogger(__name__)

router = APIRouter()

# Security: Allowlists for drift testing
ALLOWED_TABLES = {"accounts", "opportunities", "contacts"}
ALLOWED_COLUMNS = {
    "accounts": {"account_id", "name", "type", "industry", "owner_id", "status", "created_at", "updated_at", "annual_revenue", "employees"},
    "opportunities": {"opportunity_id", "account_id", "name", "stage", "amount", "amount_usd", "currency", "close_date", "owner_id", "probability", "created_at", "updated_at"},
    "contacts": {"contact_id", "account_id", "first_name", "last_name", "email", "phone", "title", "created_at", "updated_at"}
}
ALLOWED_TYPES = {"text", "varchar", "numeric", "integer", "bigint", "timestamp", "date", "boolean", "real"}

def validate_sql_identifier(value: str, context: str = "identifier") -> str:
    """
    Validate and sanitize SQL identifiers to prevent SQL injection
    Only allows alphanumeric characters and underscores
    """
    if not re.match(r'^[a-z_][a-z0-9_]*$', value, re.IGNORECASE):
        raise ValueError(f"Invalid {context}: {value}. Only alphanumeric and underscore allowed.")
    return value

def quote_identifier(identifier: str) -> str:
    """Quote SQL identifier for safe interpolation"""
    # PostgreSQL identifier quoting
    return f'"{identifier}"'


class SupabaseMutateRequest(BaseModel):
    op: str
    table: str
    from_field: Optional[str] = None
    to_field: Optional[str] = None
    type: Optional[str] = None


class MongoMutateRequest(BaseModel):
    op: str
    collection: str
    from_field: Optional[str] = None
    to_field: Optional[str] = None
    path: Optional[str] = None
    type: Optional[str] = None


class RepairApproveRequest(BaseModel):
    ticket_id: str
    apply: bool


@router.post("/test/supabase/mutate")
async def supabase_mutate(
    request: SupabaseMutateRequest,
    db: Session = Depends(get_db)
):
    """
    Execute schema mutation on Supabase (Postgres) for drift testing
    
    Operations:
    - rename_column: Rename a column
    - add_column: Add a new column
    - change_type: Change column type
    """
    supabase_db_url = os.getenv("SUPABASE_DB_URL", "")
    if not supabase_db_url:
        raise HTTPException(status_code=500, detail="SUPABASE_DB_URL not configured")
    
    schema = os.getenv("SUPABASE_SCHEMA", "public")
    
    # Security: Validate all inputs
    try:
        validate_sql_identifier(request.table, "table")
        if request.table not in ALLOWED_TABLES:
            raise ValueError(f"Table '{request.table}' not in allowlist")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    try:
        engine = create_engine(supabase_db_url, pool_pre_ping=True)
        
        with engine.connect() as conn:
            if request.op == "rename_column":
                if not request.from_field or not request.to_field:
                    raise HTTPException(status_code=400, detail="from_field and to_field required for rename_column")
                
                # Security: Validate column names
                validate_sql_identifier(request.from_field, "from_field")
                validate_sql_identifier(request.to_field, "to_field")
                if request.from_field not in ALLOWED_COLUMNS.get(request.table, set()):
                    raise HTTPException(status_code=400, detail=f"Column '{request.from_field}' not allowed for table '{request.table}'")
                
                # Use quoted identifiers to prevent SQL injection
                quoted_table = quote_identifier(request.table)
                quoted_from = quote_identifier(request.from_field)
                quoted_to = quote_identifier(request.to_field)
                
                sql = text(f'ALTER TABLE {schema}.{quoted_table} RENAME COLUMN {quoted_from} TO {quoted_to}')
                conn.execute(sql)
                conn.commit()
                
                change_details = {
                    "operation": "rename_column",
                    "table": request.table,
                    "from": request.from_field,
                    "to": request.to_field
                }
                
            elif request.op == "add_column":
                if not request.to_field or not request.type:
                    raise HTTPException(status_code=400, detail="to_field and type required for add_column")
                
                # Security: Validate inputs
                validate_sql_identifier(request.to_field, "to_field")
                validate_sql_identifier(request.type, "type")
                if request.type.lower() not in ALLOWED_TYPES:
                    raise HTTPException(status_code=400, detail=f"Type '{request.type}' not in allowlist")
                
                quoted_table = quote_identifier(request.table)
                quoted_column = quote_identifier(request.to_field)
                
                sql = text(f'ALTER TABLE {schema}.{quoted_table} ADD COLUMN {quoted_column} {request.type}')
                conn.execute(sql)
                conn.commit()
                
                change_details = {
                    "operation": "add_column",
                    "table": request.table,
                    "column": request.to_field,
                    "type": request.type
                }
                
            elif request.op == "change_type":
                if not request.from_field or not request.type:
                    raise HTTPException(status_code=400, detail="from_field and type required for change_type")
                
                # Security: Validate inputs
                validate_sql_identifier(request.from_field, "from_field")
                validate_sql_identifier(request.type, "type")
                if request.from_field not in ALLOWED_COLUMNS.get(request.table, set()):
                    raise HTTPException(status_code=400, detail=f"Column '{request.from_field}' not allowed for table '{request.table}'")
                if request.type.lower() not in ALLOWED_TYPES:
                    raise HTTPException(status_code=400, detail=f"Type '{request.type}' not in allowlist")
                
                quoted_table = quote_identifier(request.table)
                quoted_column = quote_identifier(request.from_field)
                
                sql = text(f'ALTER TABLE {schema}.{quoted_table} ALTER COLUMN {quoted_column} TYPE {request.type}')
                conn.execute(sql)
                conn.commit()
                
                change_details = {
                    "operation": "change_type",
                    "table": request.table,
                    "column": request.from_field,
                    "new_type": request.type
                }
                
            else:
                raise HTTPException(status_code=400, detail=f"Unknown operation: {request.op}")
        
        # Record schema change
        drift_event_id = str(uuid.uuid4())
        schema_change = SchemaChange(
            id=uuid.UUID(drift_event_id),
            tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            connection_id=uuid.uuid4(),
            change_type=request.op,
            details=change_details,
            applied_at=datetime.utcnow()
        )
        
        db.add(schema_change)
        db.commit()
        
        logger.info(f"✅ Supabase schema mutation applied: {request.op} on {request.table}")
        
        return {
            "status": "ok",
            "drift_event_id": drift_event_id,
            "operation": request.op,
            "table": request.table,
            "details": change_details
        }
        
    except Exception as e:
        logger.error(f"Failed to execute Supabase mutation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test/mongo/mutate")
async def mongo_mutate(
    request: MongoMutateRequest,
    db: Session = Depends(get_db)
):
    """
    Execute schema mutation on MongoDB for drift testing
    
    Operations:
    - rename_field: Rename a field across all documents
    - add_field: Add a new field with default value
    - coerce_type: Change field type
    """
    mongo_uri = os.getenv("MONGODB_URI", "")
    if not mongo_uri:
        raise HTTPException(status_code=500, detail="MONGODB_URI not configured")
    
    mongo_db_name = os.getenv("MONGODB_DB", "autonomos")
    
    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        mongo_db = client[mongo_db_name]
        collection = mongo_db[request.collection]
        
        if request.op == "rename_field":
            if not request.from_field or not request.to_field:
                raise HTTPException(status_code=400, detail="from_field and to_field required for rename_field")
            
            # Rename field in all documents
            result = collection.update_many(
                {request.from_field: {"$exists": True}},
                {"$rename": {request.from_field: request.to_field}}
            )
            
            change_details = {
                "operation": "rename_field",
                "collection": request.collection,
                "from": request.from_field,
                "to": request.to_field,
                "modified_count": result.modified_count
            }
            
        elif request.op == "add_field":
            if not request.to_field:
                raise HTTPException(status_code=400, detail="to_field required for add_field")
            
            default_value = None
            if request.type == "string":
                default_value = ""
            elif request.type == "number":
                default_value = 0
            elif request.type == "boolean":
                default_value = False
            
            # Add field to all documents that don't have it
            result = collection.update_many(
                {request.to_field: {"$exists": False}},
                {"$set": {request.to_field: default_value}}
            )
            
            change_details = {
                "operation": "add_field",
                "collection": request.collection,
                "field": request.to_field,
                "type": request.type,
                "modified_count": result.modified_count
            }
            
        elif request.op == "coerce_type":
            if not request.from_field or not request.type:
                raise HTTPException(status_code=400, detail="from_field and type required for coerce_type")
            
            change_details = {
                "operation": "coerce_type",
                "collection": request.collection,
                "field": request.from_field,
                "new_type": request.type,
                "note": "Type coercion in MongoDB is application-level, not enforced at DB level"
            }
            
        else:
            raise HTTPException(status_code=400, detail=f"Unknown operation: {request.op}")
        
        # Record schema change
        drift_event_id = str(uuid.uuid4())
        schema_change = SchemaChange(
            id=uuid.UUID(drift_event_id),
            tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            connection_id=uuid.uuid4(),
            change_type=request.op,
            details=change_details,
            applied_at=datetime.utcnow()
        )
        
        db.add(schema_change)
        db.commit()
        
        client.close()
        
        logger.info(f"✅ MongoDB schema mutation applied: {request.op} on {request.collection}")
        
        return {
            "status": "ok",
            "drift_event_id": drift_event_id,
            "operation": request.op,
            "collection": request.collection,
            "details": change_details
        }
        
    except Exception as e:
        logger.error(f"Failed to execute MongoDB mutation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/repair/approve")
async def repair_approve(
    request: RepairApproveRequest,
    db: Session = Depends(get_db)
):
    """
    Approve or reject a drift repair ticket
    
    If apply=true and confidence >= 0.85:
    - Auto-apply mapping patch
    - Update mapping registry
    """
    try:
        # Look up drift event
        drift_event = db.query(DriftEvent).filter(
            DriftEvent.id == uuid.UUID(request.ticket_id)
        ).first()
        
        if not drift_event:
            raise HTTPException(status_code=404, detail=f"Drift event {request.ticket_id} not found")
        
        confidence = drift_event.confidence or 0.0
        
        if request.apply:
            # Check confidence threshold
            if confidence >= 0.85:
                # Auto-apply mapping patch
                drift_event.status = "applied"
                
                # In a real implementation, this would update the mapping registry
                # For now, just mark as applied
                logger.info(f"✅ Auto-applied drift repair ticket {request.ticket_id} (confidence={confidence})")
                
                status_result = "applied"
            else:
                # Confidence too low for auto-apply
                drift_event.status = "rejected_low_confidence"
                logger.warning(f"⚠️ Rejected drift repair ticket {request.ticket_id} (confidence={confidence} < 0.85)")
                
                status_result = "rejected"
        else:
            # User manually rejected
            drift_event.status = "rejected_manual"
            logger.info(f"❌ Manually rejected drift repair ticket {request.ticket_id}")
            
            status_result = "rejected"
        
        db.commit()
        
        return {
            "status": status_result,
            "ticket_id": request.ticket_id,
            "confidence": confidence,
            "drift_status": drift_event.status
        }
        
    except Exception as e:
        logger.error(f"Failed to approve repair: {e}")
        raise HTTPException(status_code=500, detail=str(e))
