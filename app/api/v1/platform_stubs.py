from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from typing import Dict, Any
import os
import logging
from services.aam.canonical.subscriber import get_canonical_opportunities, get_canonical_accounts

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
    request: Request = None
) -> Dict[str, Any]:
    """Real implementation - fetch from canonical_streams if FEATURE_USE_FILESOURCE enabled"""
    try:
        if os.getenv("FEATURE_USE_FILESOURCE", "false").lower() == "true":
            tenant_id = getattr(request.state, "tenant_id", None) if request else None
            
            if tenant_id:
                opportunities = get_canonical_opportunities(tenant_id, limit=100)
                
                start = (page - 1) * page_size
                end = start + page_size
                paginated = opportunities[start:end]
                
                return {
                    "items": paginated,
                    "page": page,
                    "page_size": page_size,
                    "total": len(opportunities)
                }
        
        return {"items": [], "page": page, "page_size": page_size, "total": 0}
        
    except Exception as e:
        logger.error(f"Error in opportunities view: {e}")
        return {"items": [], "page": page, "page_size": page_size, "total": 0}

@router.get("/dcl/views/accounts")
def get_accounts_view(
    page: int = 1,
    page_size: int = 10,
    request: Request = None
) -> Dict[str, Any]:
    """Real implementation - fetch from canonical_streams if FEATURE_USE_FILESOURCE enabled"""
    try:
        if os.getenv("FEATURE_USE_FILESOURCE", "false").lower() == "true":
            tenant_id = getattr(request.state, "tenant_id", None) if request else None
            
            if tenant_id:
                accounts = get_canonical_accounts(tenant_id, limit=100)
                
                start = (page - 1) * page_size
                end = start + page_size
                paginated = accounts[start:end]
                
                return {
                    "items": paginated,
                    "page": page,
                    "page_size": page_size,
                    "total": len(accounts)
                }
        
        return {"items": [], "page": page, "page_size": page_size, "total": 0}
        
    except Exception as e:
        logger.error(f"Error in accounts view: {e}")
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
