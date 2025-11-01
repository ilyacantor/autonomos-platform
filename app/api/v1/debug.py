"""
Debug endpoints for development/testing (DEV-ONLY)
"""
import os
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.database import get_db
from app.models import CanonicalStream

router = APIRouter(prefix="/debug", tags=["debug"])

# DEV_DEBUG feature flag (enabled in development only)
DEV_DEBUG_ENABLED = os.getenv("DEV_DEBUG", "false").lower() == "true" or os.getenv("NODE_ENV", "production") == "development"


def check_dev_mode():
    """Raise HTTPException if debug mode is not enabled"""
    if not DEV_DEBUG_ENABLED:
        raise HTTPException(
            status_code=403,
            detail="Debug endpoints are only available in development mode (set DEV_DEBUG=true or NODE_ENV=development)"
        )


@router.get("/last-canonical")
async def get_last_canonical_events(
    entity: str = Query(..., description="Entity type (account, opportunity, contact)"),
    limit: int = Query(1, ge=1, le=100, description="Number of most recent events to return"),
    db: Session = Depends(get_db)
):
    """
    DEV-ONLY: Retrieve the most recent canonical events for a given entity type
    
    Returns the last N canonical events with full event data including:
    - Entity-specific fields (opportunity_id, account_id, name, etc.)
    - Metadata (trace_id, emitted_at, source_system)
    
    Only enabled when DEV_DEBUG=true or NODE_ENV=development
    """
    check_dev_mode()
    
    # Validate entity type
    valid_entities = ["account", "opportunity", "contact"]
    if entity not in valid_entities:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid entity type '{entity}'. Must be one of: {', '.join(valid_entities)}"
        )
    
    # Query the canonical_streams table for the last N events
    events = (
        db.query(CanonicalStream)
        .filter(CanonicalStream.entity == entity)
        .order_by(desc(CanonicalStream.emitted_at))
        .limit(limit)
        .all()
    )
    
    if not events:
        return []
    
    # Format response according to spec
    results = []
    for event in events:
        # Extract metadata
        meta = event.meta or {}
        source = event.source or {}
        data = event.data or {}
        
        # Build response object based on entity type
        if entity == "opportunity":
            formatted = {
                "opportunity_id": data.get("opportunity_id"),
                "account_id": data.get("account_id"),
                "name": data.get("name"),
                "stage": data.get("stage"),
                "amount": data.get("amount"),
                "currency": data.get("currency"),
                "close_date": data.get("close_date"),
                "owner_id": data.get("owner_id"),
                "probability": data.get("probability"),
                "emitted_at": event.emitted_at.isoformat() if event.emitted_at else None,
                "trace_id": meta.get("trace_id"),
                "source_system": source.get("system", "unknown")
            }
        elif entity == "account":
            formatted = {
                "account_id": data.get("account_id"),
                "name": data.get("name"),
                "industry": data.get("industry"),
                "annual_revenue": data.get("annual_revenue"),
                "employee_count": data.get("employee_count"),
                "website": data.get("website"),
                "emitted_at": event.emitted_at.isoformat() if event.emitted_at else None,
                "trace_id": meta.get("trace_id"),
                "source_system": source.get("system", "unknown")
            }
        elif entity == "contact":
            formatted = {
                "contact_id": data.get("contact_id"),
                "account_id": data.get("account_id"),
                "first_name": data.get("first_name"),
                "last_name": data.get("last_name"),
                "email": data.get("email"),
                "phone": data.get("phone"),
                "title": data.get("title"),
                "emitted_at": event.emitted_at.isoformat() if event.emitted_at else None,
                "trace_id": meta.get("trace_id"),
                "source_system": source.get("system", "unknown")
            }
        else:
            formatted = {
                "data": data,
                "emitted_at": event.emitted_at.isoformat() if event.emitted_at else None,
                "trace_id": meta.get("trace_id"),
                "source_system": source.get("system", "unknown")
            }
        
        results.append(formatted)
    
    return results
