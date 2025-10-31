from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from typing import Dict, Any

router = APIRouter()

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    try:
        return {
            "ok": True,
            "service": "AOS",
            "mode": "dev"
        }
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "ok": True,
                "service": "AOS",
                "mode": "dev"
            }
        )

@router.get("/dcl/views/opportunities")
async def get_opportunities_view() -> Dict[str, Any]:
    try:
        return {
            "items": [],
            "page": 1,
            "page_size": 10,
            "total": 0
        }
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "items": [],
                "page": 1,
                "page_size": 10,
                "total": 0
            }
        )

@router.get("/dcl/views/accounts")
async def get_accounts_view() -> Dict[str, Any]:
    try:
        return {
            "items": [],
            "page": 1,
            "page_size": 10,
            "total": 0
        }
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "items": [],
                "page": 1,
                "page_size": 10,
                "total": 0
            }
        )

@router.post("/intents/revops/execute", status_code=status.HTTP_202_ACCEPTED)
async def execute_revops_intent(request: Request) -> Dict[str, Any]:
    try:
        return {
            "task_id": "demo-task",
            "trace_id": "demo-trace"
        }
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "task_id": "demo-task",
                "trace_id": "demo-trace"
            }
        )

@router.post("/intents/finops/execute", status_code=status.HTTP_202_ACCEPTED)
async def execute_finops_intent(request: Request) -> Dict[str, Any]:
    try:
        return {
            "task_id": "demo-task",
            "trace_id": "demo-trace"
        }
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "task_id": "demo-task",
                "trace_id": "demo-trace"
            }
        )
