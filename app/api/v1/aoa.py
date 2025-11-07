import logging
import httpx
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from redis import Redis
from rq import Queue

from app import crud, schemas, models
from app.database import get_db
from app.config import settings
from app.security import get_current_user
from app.contracts.aod_contract import (
    DiscoveryRequest,
    DiscoveryResponse,
    DiscoveryHandoff
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize Redis connection (optional)
redis_conn = None
task_queue = None
try:
    redis_conn = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB)
    task_queue = Queue(connection=redis_conn)
except Exception as e:
    logger.warning(f"Redis not available in AOA module: {e}")

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
    
    if task_queue is None:
        raise HTTPException(
            status_code=503, 
            detail="Task queue not available. Redis connection required for background tasks."
        )
    
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
    
    if task_queue is None:
        raise HTTPException(
            status_code=503, 
            detail="Task queue not available. Redis connection required for background tasks."
        )
    
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
    
    if task_queue is None:
        raise HTTPException(
            status_code=503, 
            detail="Task queue not available. Redis connection required for background tasks."
        )
    
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


@router.post("/discover")
async def discover(
    request: DiscoveryRequest = Body(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    API-based E2E Flow: NLP Discovery with AOS Discover (AOD) Service
    
    This endpoint implements the CTO directive for microservice integration:
    1. Accept NLP query from frontend
    2. Call external AOD service via network API
    3. Log all data flow for debugging
    4. Hand off discovery results to Agents & Humans
    
    Flow:
    - User NLP input → This endpoint → AOD service API
    - AOD returns JSON → Log response → Hand to Agents
    """
    request_id = str(uuid.uuid4())
    
    # Override tenant_id with authenticated user's tenant
    request.tenant_id = str(current_user.tenant_id)
    
    # ═══════════════════════════════════════════════════════════
    # STEP 1: LOG - Data being sent to AOD service
    # ═══════════════════════════════════════════════════════════
    logger.info(
        f"[DISCOVER E2E] Step 1/3: Sending discovery request to AOD service | "
        f"request_id={request_id} | tenant_id={current_user.tenant_id} | "
        f"nlp_query='{request.nlp_query}' | discovery_types={request.discovery_types} | "
        f"AOD_URL={settings.AOD_BASE_URL}"
    )
    logger.debug(f"[DISCOVER E2E] Full request payload: {request.dict()}")
    
    # ═══════════════════════════════════════════════════════════
    # STEP 2: Network API Call to AOS Discover (AOD) service
    # ═══════════════════════════════════════════════════════════
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            aod_url = f"{settings.AOD_BASE_URL}/discover"
            
            logger.info(f"[DISCOVER E2E] Making HTTP POST to AOD: {aod_url}")
            
            response = await client.post(
                aod_url,
                json=request.dict(),
                headers={"Content-Type": "application/json"}
            )
            
            response.raise_for_status()
            discovery_data = response.json()
            
            # Parse into DiscoveryResponse for type safety
            discovery_response = DiscoveryResponse(**discovery_data)
            
    except httpx.HTTPError as e:
        logger.error(
            f"[DISCOVER E2E] AOD service API call failed | "
            f"request_id={request_id} | error={str(e)} | "
            f"AOD_URL={settings.AOD_BASE_URL}"
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to reach AOS Discover service: {str(e)}. "
                   f"Ensure AOD_BASE_URL is configured correctly."
        )
    except Exception as e:
        logger.error(
            f"[DISCOVER E2E] Failed to parse AOD response | "
            f"request_id={request_id} | error={str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Invalid response from AOD service: {str(e)}"
        )
    
    # ═══════════════════════════════════════════════════════════
    # STEP 3: LOG - JSON response received from AOD
    # ═══════════════════════════════════════════════════════════
    logger.info(
        f"[DISCOVER E2E] Step 2/3: Received discovery response from AOD | "
        f"request_id={request_id} | success={discovery_response.success} | "
        f"entities_found={discovery_response.total_entities_found} | "
        f"filtered={discovery_response.filtered_count} | "
        f"confidence={discovery_response.overall_confidence:.2f} | "
        f"recommended_agents={len(discovery_response.agent_recommendations)}"
    )
    logger.debug(
        f"[DISCOVER E2E] Full AOD response: {discovery_response.dict()}"
    )
    
    # ═══════════════════════════════════════════════════════════
    # STEP 4: Transform to DiscoveryHandoff for Agent layer
    # ═══════════════════════════════════════════════════════════
    assigned_agents = [
        rec.agent_name 
        for rec in discovery_response.agent_recommendations
        if rec.priority in ["high", "medium"]
    ]
    
    handoff = DiscoveryHandoff(
        discovery_response=discovery_response,
        tenant_id=str(current_user.tenant_id),
        original_query=request.nlp_query,
        assigned_agents=assigned_agents,
        processing_priority="high" if discovery_response.overall_confidence >= 0.9 else "medium",
        handoff_status="assigned" if assigned_agents else "pending"
    )
    
    # ═══════════════════════════════════════════════════════════
    # STEP 5: LOG - Data handoff to Agents & Humans
    # ═══════════════════════════════════════════════════════════
    logger.info(
        f"[DISCOVER E2E] Step 3/3: Handing off to Agents & Humans | "
        f"request_id={request_id} | assigned_agents={assigned_agents} | "
        f"priority={handoff.processing_priority} | status={handoff.handoff_status}"
    )
    logger.debug(
        f"[DISCOVER E2E] Full handoff payload: {handoff.dict()}"
    )
    
    # TODO: Actual handoff to Agents & Humans components
    # This will be implemented in task 6 (agent handoff bridge)
    # For now, we return the handoff data to frontend
    
    logger.info(
        f"[DISCOVER E2E] ✓ Discovery flow completed successfully | "
        f"request_id={request_id}"
    )
    
    return {
        "success": True,
        "request_id": request_id,
        "discovery": discovery_response.dict(),
        "handoff": handoff.dict()
    }
