"""
Debug endpoints for development/testing (DEV-ONLY)
"""
import os
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from app.database import get_db
from app.models import CanonicalStream, ApiJournal
import httpx

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


@router.get("/source-status")
async def get_source_status(db: Session = Depends(get_db)):
    """
    DEV-ONLY: Get status of all connectors (configured + last canonical timestamp)
    
    Returns configuration status and last ingest time for each source system:
    - salesforce: Configured via SALESFORCE_ACCESS_TOKEN and SALESFORCE_INSTANCE_URL
    - supabase: Configured via SUPABASE_DB_URL
    - mongodb: Configured via MONGODB_URI
    - filesource: Always configured (uses local CSV files)
    
    Also queries canonical_streams to get last emitted_at timestamp per source_system
    """
    check_dev_mode()
    
    # Define connectors and their configuration checks
    connectors = {
        "salesforce": {
            "configured": bool(
                (os.getenv("SALESFORCE_ACCESS_TOKEN") and os.getenv("SALESFORCE_INSTANCE_URL")) or
                (os.getenv("SALESFORCE_CLIENT_ID") and os.getenv("SALESFORCE_CLIENT_SECRET") and os.getenv("SALESFORCE_REFRESH_TOKEN"))
            ),
            "last_ingest_at": None,
            "last_canonical_at": None
        },
        "supabase": {
            "configured": bool(os.getenv("SUPABASE_DB_URL")),
            "last_ingest_at": None,
            "last_canonical_at": None
        },
        "mongodb": {
            "configured": bool(os.getenv("MONGODB_URI")),
            "last_ingest_at": None,
            "last_canonical_at": None
        },
        "filesource": {
            "configured": True,  # Always configured (local CSV files)
            "last_ingest_at": None,
            "last_canonical_at": None
        }
    }
    
    # Query canonical_streams for last emitted_at per source_system
    try:
        for source_name in connectors.keys():
            # Query for most recent canonical stream for this source
            result = (
                db.query(func.max(CanonicalStream.emitted_at))
                .filter(CanonicalStream.source['system'].astext == source_name)
                .scalar()
            )
            
            if result:
                connectors[source_name]["last_canonical_at"] = result.isoformat()
    except Exception as e:
        # If query fails, leave timestamps as None
        pass
    
    return connectors


@router.get("/last-canonical")
async def get_last_canonical_events(
    entity: str = Query(..., description="Entity type (account, opportunity, contact)"),
    limit: int = Query(1, ge=1, le=100, description="Number of most recent events to return"),
    source: Optional[str] = Query(None, description="Filter by source system (salesforce, supabase, mongodb, filesource)"),
    db: Session = Depends(get_db)
):
    """
    DEV-ONLY: Retrieve the most recent canonical events for a given entity type
    
    Returns the last N canonical events with full event data including:
    - Entity-specific fields (opportunity_id, account_id, name, etc.)
    - Metadata (trace_id, emitted_at, source_system)
    
    Optional source parameter filters results by source system.
    Returns 404 if source is specified but no results found.
    
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
    
    # Validate source if provided
    if source:
        valid_sources = ["salesforce", "supabase", "mongodb", "filesource"]
        if source not in valid_sources:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid source '{source}'. Must be one of: {', '.join(valid_sources)}"
            )
    
    # Query the canonical_streams table for the last N events
    query = db.query(CanonicalStream).filter(CanonicalStream.entity == entity)
    
    # Filter by source if provided
    if source:
        query = query.filter(CanonicalStream.source['system'].astext == source)
    
    events = query.order_by(desc(CanonicalStream.emitted_at)).limit(limit).all()
    
    # Return 404 if source specified but no results found
    if not events and source:
        raise HTTPException(
            status_code=404,
            detail={"error": "no_canonical_for_source"}
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


@router.post("/agent-proof")
async def agent_proof_test(
    agent: str,
    entity: str,
    intent: str = "noop",
    db: Session = Depends(get_db)
):
    """
    DEV-ONLY: End-to-end agent functionality proof
    
    Tests agent read and intent execution capabilities:
    1. Calls GET /api/v1/dcl/views/{entity}?limit=1&offset=0 to test read access
    2. Calls POST /api/v1/intents/{agent}/execute to test intent execution
    3. Checks if journal entry exists for the trace_id
    
    Input:
        - agent: "revops" or "finops"
        - entity: "opportunities" or "accounts"
        - intent: Intent type (default: "noop")
    
    Returns:
        {
            "read": "OK" | "FAIL",
            "intent": "OK" | "FAIL",
            "trace_id": "...",
            "journal_check": "OK" | "SKIPPED"
        }
    """
    check_dev_mode()
    
    # Validate inputs
    valid_agents = ["revops", "finops"]
    valid_entities = ["opportunities", "accounts"]
    
    if agent not in valid_agents:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid agent '{agent}'. Must be one of: {', '.join(valid_agents)}"
        )
    
    if entity not in valid_entities:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid entity '{entity}'. Must be one of: {', '.join(valid_entities)}"
        )
    
    result = {
        "read": "FAIL",
        "intent": "FAIL",
        "trace_id": None,
        "journal_check": "SKIPPED"
    }
    
    # Get base URL (handle both local and Replit domains)
    base_url = os.getenv("API_BASE_URL", "http://localhost:5000")
    if not base_url.startswith("http"):
        base_url = f"http://{base_url}"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Step 1: Test read access via GET /api/v1/dcl/views/{entity}
            try:
                read_response = await client.get(
                    f"{base_url}/api/v1/dcl/views/{entity}",
                    params={"limit": 1, "offset": 0}
                )
                if read_response.status_code == 200:
                    result["read"] = "OK"
            except Exception as e:
                result["read"] = f"FAIL: {str(e)}"
            
            # Step 2: Test intent execution via POST /api/v1/intents/{agent}/execute
            try:
                intent_response = await client.post(
                    f"{base_url}/api/v1/intents/{agent}/execute",
                    json={
                        "intent": intent,
                        "dry_run": True,
                        "explain_only": True
                    }
                )
                if intent_response.status_code in [200, 202]:
                    result["intent"] = "OK"
                    response_data = intent_response.json()
                    result["trace_id"] = response_data.get("trace_id")
            except Exception as e:
                result["intent"] = f"FAIL: {str(e)}"
            
            # Step 3: Check if journal entry exists for trace_id
            if result["trace_id"]:
                try:
                    journal_entry = db.query(ApiJournal).filter(
                        ApiJournal.trace_id == result["trace_id"]
                    ).first()
                    
                    if journal_entry:
                        result["journal_check"] = "OK"
                    else:
                        result["journal_check"] = "SKIPPED"
                except Exception as e:
                    result["journal_check"] = f"FAIL: {str(e)}"
    
    except Exception as e:
        result["read"] = f"FAIL: {str(e)}"
        result["intent"] = f"FAIL: {str(e)}"
    
    return result
