"""
Bulk Mapping Generation API

RESTful endpoints for asynchronous bulk mapping generation jobs.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from uuid import UUID
from app.database import get_db
from sqlalchemy.orm import Session
from app.security import get_current_user
from app import models
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bulk-mappings", tags=["bulk-mappings"])


class BulkMappingRequest(BaseModel):
    """Request to generate bulk mappings"""
    connector_definition_ids: List[str] = Field(
        ...,
        description="List of connector definition IDs to process"
    )
    options: Optional[Dict] = Field(
        default=None,
        description="Optional job configuration"
    )


class BulkMappingResponse(BaseModel):
    """Response from bulk mapping job submission"""
    status: str
    job_id: Optional[str] = None
    tenant_id: str
    connector_count: Optional[int] = None
    queue_name: Optional[str] = None
    error: Optional[str] = None


class JobStatusResponse(BaseModel):
    """Response with job status details"""
    job_id: str
    tenant_id: str
    status: str
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    processed_fields: int = 0
    total_fields: int = 0
    successful_mappings: int = 0
    progress_percentage: Optional[int] = None
    error_message: Optional[str] = None


@router.post("", response_model=BulkMappingResponse)
async def create_bulk_mapping_job(
    request: BulkMappingRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new bulk mapping generation job
    
    Enqueues a background job to generate mappings for the specified connectors.
    Returns immediately with job ID for status tracking.
    """
    try:
        from services.mapping_intelligence.job_enqueue import enqueue_bulk_mapping_job
        
        tenant_id = str(current_user.tenant_id)
        
        result = enqueue_bulk_mapping_job(
            tenant_id=tenant_id,
            connector_definition_ids=request.connector_definition_ids,
            options=request.options,
            use_tenant_pool=True
        )
        
        logger.info(
            f"Created bulk mapping job for tenant {tenant_id}: "
            f"{result.get('job_id')} with status {result.get('status')}"
        )
        
        return BulkMappingResponse(**result)
    
    except RuntimeError as e:
        logger.error(f"Runtime error creating job: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    
    except Exception as e:
        logger.error(f"Error creating bulk mapping job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_bulk_mapping_job_status(
    job_id: str,
    current_user: models.User = Depends(get_current_user)
):
    """
    Get status of a bulk mapping job
    
    Returns current status, progress, and results of the job.
    """
    try:
        from services.mapping_intelligence.job_enqueue import get_job_status
        
        tenant_id = str(current_user.tenant_id)
        status = get_job_status(tenant_id, job_id)
        
        if not status:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found for tenant {tenant_id}"
            )
        
        return JobStatusResponse(**status)
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Error getting job status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=List[JobStatusResponse])
async def list_bulk_mapping_jobs(
    current_user: models.User = Depends(get_current_user),
    limit: int = 100
):
    """
    List all bulk mapping jobs for a tenant
    
    Returns list of jobs with their current status.
    """
    try:
        from shared.redis_client import get_redis_client
        from services.mapping_intelligence.job_state import BulkMappingJobState
        
        tenant_id = str(current_user.tenant_id)
        redis_client = get_redis_client()
        if not redis_client:
            raise HTTPException(
                status_code=503,
                detail="Redis is not available"
            )
        
        job_state = BulkMappingJobState(redis_client)
        jobs = job_state.get_all_jobs_for_tenant(tenant_id)
        
        jobs = jobs[:limit]
        
        return [JobStatusResponse(**job) for job in jobs]
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Error listing jobs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{job_id}")
async def cancel_bulk_mapping_job(
    job_id: str,
    current_user: models.User = Depends(get_current_user)
):
    """
    Cancel a bulk mapping job
    
    Attempts to cancel a running or pending job.
    """
    try:
        from shared.redis_client import get_redis_client
        from services.mapping_intelligence.job_state import BulkMappingJobState
        
        tenant_id = str(current_user.tenant_id)
        redis_client = get_redis_client()
        if not redis_client:
            raise HTTPException(
                status_code=503,
                detail="Redis is not available"
            )
        
        job_state = BulkMappingJobState(redis_client)
        current_state = job_state.get_job_state(tenant_id, job_id)
        
        if not current_state:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found"
            )
        
        if current_state['status'] in ['completed', 'failed']:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel job with status {current_state['status']}"
            )
        
        job_state.set_error(tenant_id, job_id, "Job cancelled by user")
        
        logger.info(f"Cancelled job {job_id} for tenant {tenant_id}")
        
        return {
            "status": "cancelled",
            "job_id": job_id,
            "tenant_id": tenant_id
        }
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Error cancelling job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
