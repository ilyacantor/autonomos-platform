import logging
import httpx
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from redis import Redis
from rq import Queue

from app import crud, schemas, models
from app.database import get_db
from app.config import settings
from app.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

redis_conn = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB)
task_queue = Queue(connection=redis_conn)

@router.get("/state")
async def get_aoa_state(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Proxy to internal DCL engine /state
    Returns the current state of the AOA system.
    """
    logger.info(f"AOA state request from tenant {current_user.tenant_id}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://localhost:5000/dcl/state",
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch AOA state for tenant {current_user.tenant_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to fetch AOA state: {str(e)}"
        )

@router.post("/run", response_model=schemas.Task)
def run_aoa_connect(
    sources: str = Query(default=""),
    agents: str = Query(default=""),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Enqueue a job to connect AOA.
    Creates a task that will call internal DCL engine /connect
    Enforces 1 active AOA job per tenant.
    """
    logger.info(f"AOA run/connect request from tenant {current_user.tenant_id} with sources={sources}, agents={agents}")
    
    # Enforce 1 active job per tenant
    if crud.has_active_aoa_job(db, current_user.tenant_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An AOA job is already in progress for this tenant. Please wait for it to complete."
        )
    
    task_payload = {
        "action": "aoa_connect",
        "tenant_id": str(current_user.tenant_id),
        "sources": sources,
        "agents": agents
    }
    
    task_data = schemas.TaskCreate(payload=task_payload)
    db_task = crud.create_task(db, task_data, current_user.tenant_id)
    
    try:
        from app.worker import execute_task
        task_queue.enqueue(execute_task, str(db_task.id), job_timeout=300)
    except Exception as e:
        logger.error(f"Failed to enqueue AOA connect task {db_task.id}: {str(e)}")
        raise HTTPException(
            status_code=503, 
            detail="Task created but failed to enqueue for processing. Please check Redis connection."
        )
    
    return db_task

@router.post("/reset", response_model=schemas.Task)
def reset_aoa(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Enqueue a job to reset AOA.
    Creates a task that will call internal DCL engine /reset
    Enforces 1 active AOA job per tenant.
    """
    logger.info(f"AOA reset request from tenant {current_user.tenant_id}")
    
    # Enforce 1 active job per tenant
    if crud.has_active_aoa_job(db, current_user.tenant_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An AOA job is already in progress for this tenant. Please wait for it to complete."
        )
    
    task_payload = {
        "action": "aoa_reset",
        "tenant_id": str(current_user.tenant_id)
    }
    
    task_data = schemas.TaskCreate(payload=task_payload)
    db_task = crud.create_task(db, task_data, current_user.tenant_id)
    
    try:
        from app.worker import execute_task
        task_queue.enqueue(execute_task, str(db_task.id), job_timeout=300)
    except Exception as e:
        logger.error(f"Failed to enqueue AOA reset task {db_task.id}: {str(e)}")
        raise HTTPException(
            status_code=503, 
            detail="Task created but failed to enqueue for processing. Please check Redis connection."
        )
    
    return db_task

@router.post("/prod-mode", response_model=schemas.Task)
def toggle_prod_mode(
    prod_mode_data: schemas.ProdModeRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Enqueue a job to toggle production mode (dev mode).
    Creates a task that will call internal DCL engine /toggle_dev_mode
    Enforces 1 active AOA job per tenant.
    """
    logger.info(f"AOA prod-mode toggle request from tenant {current_user.tenant_id}, enabled={prod_mode_data.enabled}")
    
    # Enforce 1 active job per tenant
    if crud.has_active_aoa_job(db, current_user.tenant_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An AOA job is already in progress for this tenant. Please wait for it to complete."
        )
    
    task_payload = {
        "action": "aoa_toggle_dev_mode",
        "tenant_id": str(current_user.tenant_id),
        "enabled": prod_mode_data.enabled
    }
    
    task_data = schemas.TaskCreate(payload=task_payload)
    db_task = crud.create_task(db, task_data, current_user.tenant_id)
    
    try:
        from app.worker import execute_task
        task_queue.enqueue(execute_task, str(db_task.id), job_timeout=300)
    except Exception as e:
        logger.error(f"Failed to enqueue AOA toggle dev mode task {db_task.id}: {str(e)}")
        raise HTTPException(
            status_code=503, 
            detail="Task created but failed to enqueue for processing. Please check Redis connection."
        )
    
    return db_task
