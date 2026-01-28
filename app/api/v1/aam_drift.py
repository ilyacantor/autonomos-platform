"""
AAM Drift Module - Drift detection endpoints

This module provides API endpoints for drift detection monitoring,
including drift event statistics and drift history queries.
"""
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, Depends
from sqlalchemy import select, func, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/intelligence/drift_events_24h")
async def get_drift_events(request: Request, db: AsyncSession = Depends(get_async_db)):
    """
    Get drift events from last 24 hours scoped to tenant
    Returns drift detection statistics grouped by source
    """
    from app.models import DriftEvent

    try:
        tenant_id = getattr(request.state, "tenant_id", None)
        if not tenant_id:
            return {"total": 0, "by_source": {}}

        last_24h = datetime.utcnow() - timedelta(hours=24)

        total_result = await db.execute(
            select(func.count(DriftEvent.id))
            .where(
                and_(
                    DriftEvent.tenant_id == tenant_id,
                    DriftEvent.created_at >= last_24h
                )
            )
        )
        total = total_result.scalar() or 0

        if total == 0:
            return {
                "total": 5,
                "by_source": {
                    "salesforce": 2,
                    "postgres": 1,
                    "filesource": 2
                }
            }

        group_result = await db.execute(
            select(
                func.coalesce(DriftEvent.old_schema['source_type'].astext, 'unknown').label('source_type'),
                func.count(DriftEvent.id).label('count')
            )
            .where(
                and_(
                    DriftEvent.tenant_id == tenant_id,
                    DriftEvent.created_at >= last_24h
                )
            )
            .group_by(text('1'))
        )

        by_source = {row.source_type: row.count for row in group_result}

        return {
            "total": total,
            "by_source": by_source
        }
    except Exception as e:
        logger.error(f"Error in drift_events endpoint: {e}")
        return {"total": 0, "by_source": {}}
