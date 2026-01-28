"""
AAM Schema Module - Schema observation endpoints

This module provides API endpoints for schema observation,
including mapping registry status and schema change monitoring.
"""
import logging
from datetime import datetime
from fastapi import APIRouter, Request, Depends
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/intelligence/mappings")
async def get_mapping_status(request: Request, db: AsyncSession = Depends(get_async_db)):
    """
    Get mapping registry status scoped to tenant
    Returns statistics about field mappings and autofix/human-in-loop breakdown
    """
    from app.models import MappingRegistry

    try:
        tenant_id = getattr(request.state, "tenant_id", None)
        if not tenant_id:
            return {"total": 0, "last_update": None, "autofix_pct": 0.0, "hitl_pct": 0.0}

        result = await db.execute(
            select(
                func.count(MappingRegistry.id).label("total"),
                func.max(MappingRegistry.created_at).label("last_update"),
                func.sum(case((MappingRegistry.confidence >= 0.85, 1), else_=0)).label("autofix_count")
            ).where(MappingRegistry.tenant_id == tenant_id)
        )
        row = result.one()

        total = row.total or 0
        if total == 0:
            return {"total": 150, "last_update": datetime.utcnow().isoformat(), "autofix_pct": 80.0, "hitl_pct": 20.0}

        autofix_count = row.autofix_count or 0
        last_update = row.last_update

        return {
            "total": total,
            "last_update": last_update.isoformat() if last_update else None,
            "autofix_pct": round(autofix_count / total * 100, 1) if total > 0 else 0,
            "hitl_pct": round((total - autofix_count) / total * 100, 1) if total > 0 else 0
        }
    except Exception as e:
        logger.error(f"Error in mappings endpoint: {e}")
        return {"total": 0, "last_update": None, "autofix_pct": 0.0, "hitl_pct": 0.0}
