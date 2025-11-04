from fastapi import APIRouter, Request, status, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
import os
import logging
from services.aam.canonical.subscriber import (
    get_canonical_opportunities, 
    get_canonical_accounts,
    get_materialized_opportunities,
    get_materialized_accounts
)
from app.security import get_current_user
from app.models import User

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    return {
        "ok": True,
        "service": "AOS",
        "mode": "dev"
    }

@router.get("/dcl/views/opportunities")
def get_opportunities_view(
    page: int = 1,
    page_size: int = 10,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Fetch materialized opportunities with JWT authentication"""
    try:
        tenant_id = str(current_user.tenant_id)
        offset = (page - 1) * page_size
        
        opportunities = get_materialized_opportunities(
            tenant_id=tenant_id,
            limit=page_size,
            offset=offset
        )
        
        return {
            "items": opportunities,
            "page": page,
            "page_size": page_size,
            "total": len(opportunities)
        }
        
    except Exception as e:
        logger.error(f"Error in opportunities view: {e}", exc_info=True)
        return {"items": [], "page": page, "page_size": page_size, "total": 0}

@router.get("/dcl/views/accounts")
def get_accounts_view(
    page: int = 1,
    page_size: int = 10,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Fetch materialized accounts with JWT authentication"""
    try:
        tenant_id = str(current_user.tenant_id)
        offset = (page - 1) * page_size
        
        accounts = get_materialized_accounts(
            tenant_id=tenant_id,
            limit=page_size,
            offset=offset
        )
        
        return {
            "items": accounts,
            "page": page,
            "page_size": page_size,
            "total": len(accounts)
        }
        
    except Exception as e:
        logger.error(f"Error in accounts view: {e}", exc_info=True)
        return {"items": [], "page": page, "page_size": page_size, "total": 0}

@router.post("/intents/revops/execute", status_code=status.HTTP_202_ACCEPTED)
async def execute_revops_intent(request: Request) -> Dict[str, Any]:
    return {
        "task_id": "demo-task",
        "trace_id": "demo-trace"
    }

@router.post("/intents/finops/execute", status_code=status.HTTP_202_ACCEPTED)
async def execute_finops_intent(request: Request) -> Dict[str, Any]:
    return {
        "task_id": "demo-task",
        "trace_id": "demo-trace"
    }
