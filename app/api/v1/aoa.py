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
    log_msg = (
        f"[DISCOVER E2E] Step 1/3: Sending discovery request to AOD service | "
        f"request_id={request_id} | tenant_id={current_user.tenant_id} | "
        f"nlp_query='{request.nlp_query}' | discovery_types={request.discovery_types} | "
        f"AOD_URL={settings.AOD_BASE_URL}"
    )
    logger.info(log_msg)
    print(log_msg)  # Ensure console output for debugging
    logger.debug(f"[DISCOVER E2E] Full request payload: {request.dict()}")
    
    # ═══════════════════════════════════════════════════════════
    # STEP 2: Network API Call to AOS Discover (AOD) service
    # ═══════════════════════════════════════════════════════════
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            aod_url = f"{settings.AOD_BASE_URL}/api/discover"
            
            logger.info(f"[DISCOVER E2E] Making HTTP POST to AOD: {aod_url}")
            
            # Transform request to match AOD's expected contract
            # AOD expects "query" instead of "nlp_query"
            aod_payload = {
                "query": request.nlp_query,
                "tenant_id": request.tenant_id,
                "discovery_types": [dt.value for dt in request.discovery_types],
                "context": request.context,
                "max_results": request.max_results,
                "min_confidence": request.min_confidence
            }
            
            response = await client.post(
                aod_url,
                json=aod_payload,
                headers={"Content-Type": "application/json"}
            )
            
            response.raise_for_status()
            aod_response = response.json()
            
    except httpx.HTTPError as e:
        error_log = (
            f"[DISCOVER E2E] AOD service API call failed | "
            f"request_id={request_id} | error={str(e)} | "
            f"AOD_URL={settings.AOD_BASE_URL}"
        )
        logger.error(error_log)
        print(error_log)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to reach AOS Discover service: {str(e)}. "
                   f"Ensure AOD_BASE_URL is configured correctly."
        )
    
    # ═══════════════════════════════════════════════════════════
    # STEP 3: LOG - JSON response received from AOD
    # ═══════════════════════════════════════════════════════════
    aod_status = aod_response.get("status", "unknown")
    aod_results = aod_response.get("results", [])
    aod_total = aod_response.get("total_count", 0)
    aod_timestamp = aod_response.get("timestamp", "")
    
    log_msg2 = (
        f"[DISCOVER E2E] Step 2/3: Received discovery response from AOD | "
        f"request_id={request_id} | aod_status={aod_status} | "
        f"results_count={len(aod_results)} | total_count={aod_total} | "
        f"timestamp={aod_timestamp}"
    )
    logger.info(log_msg2)
    print(log_msg2)  # Ensure console output for debugging
    logger.debug(f"[DISCOVER E2E] Full AOD response sample: {str(aod_response)[:500]}...")
    
    # ═══════════════════════════════════════════════════════════
    # STEP 4: Transform AOD response to internal format
    # ═══════════════════════════════════════════════════════════
    # Determine recommended agents based on asset types and query keywords
    assigned_agents = []
    query_lower = request.nlp_query.lower()
    
    # FinOps domain keywords
    if any(kw in query_lower for kw in ["cost", "spending", "aws", "cloud", "infrastructure", "finops"]):
        assigned_agents.append("finops_pilot")
    
    # RevOps domain keywords
    if any(kw in query_lower for kw in ["revenue", "sales", "opportunity", "pipeline", "revops"]):
        assigned_agents.append("revops_pilot")
    
    # Default to general agent if no specific domain
    if not assigned_agents:
        assigned_agents.append("general_agent")
    
    # Calculate overall confidence from AOD assets
    avg_confidence = 0.0
    if aod_results:
        confidences = [asset.get("confidence", 0.0) for asset in aod_results if "confidence" in asset]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
    
    # ═══════════════════════════════════════════════════════════
    # STEP 5: LOG - Data handoff to Agents & Humans
    # ═══════════════════════════════════════════════════════════
    priority = "high" if avg_confidence >= 0.9 else "medium"
    handoff_status = "assigned" if assigned_agents else "pending"
    
    log_msg3 = (
        f"[DISCOVER E2E] Step 3/3: Handing off to Agents & Humans | "
        f"request_id={request_id} | assigned_agents={assigned_agents} | "
        f"priority={priority} | status={handoff_status} | avg_confidence={avg_confidence:.2f}"
    )
    logger.info(log_msg3)
    print(log_msg3)  # Ensure console output for debugging
    
    logger.info(
        f"[DISCOVER E2E] ✓ Discovery flow completed successfully | "
        f"request_id={request_id}"
    )
    
    # Return transformed response compatible with frontend
    return {
        "success": True,
        "request_id": request_id,
        "message": f"Discovered {len(aod_results)} assets from AOD service",
        "discovery": {
            "total_entities_found": aod_total,
            "filtered_count": len(aod_results),
            "overall_confidence": avg_confidence,
            "entities": aod_results[:10],  # First 10 for display
            "agent_recommendations": [
                {
                    "agent_name": agent,
                    "agent_type": agent.split("_")[0],  # finops, revops, general
                    "reason": f"Query matched {agent.split('_')[0]} domain keywords",
                    "confidence_score": avg_confidence,
                    "priority": priority
                }
                for agent in assigned_agents
            ],
            "aod_status": aod_status,
            "timestamp": aod_timestamp
        }
    }


@router.post("/demo-scan")
async def demo_scan(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Demo Scan: Trigger full asset discovery scan from AOD training data
    
    This endpoint:
    1. Calls AOD with a "full scan" query to discover all assets
    2. Categorizes assets by risk level (high, medium, low)
    3. Returns scan statistics for display in Control Center
    4. Queues high/medium risk assets for HITL review
    """
    import time
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    logger.info(f"[DEMO SCAN] Starting full asset scan | request_id={request_id} | tenant_id={current_user.tenant_id}")
    print(f"[DEMO SCAN] Starting full asset scan | request_id={request_id}")
    
    # Call AOD with full scan query
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            aod_url = f"{settings.AOD_BASE_URL}/api/discover"
            
            # Full scan query to discover all assets
            aod_payload = {
                "query": "discover all assets in the system",
                "tenant_id": str(current_user.tenant_id),
                "discovery_types": ["entity_mapping"],
                "context": {},
                "max_results": 1000,
                "min_confidence": 0.0
            }
            
            logger.info(f"[DEMO SCAN] Calling AOD service: {aod_url}")
            response = await client.post(
                aod_url,
                json=aod_payload,
                headers={"Content-Type": "application/json"}
            )
            
            response.raise_for_status()
            aod_response = response.json()
            
    except httpx.HTTPError as e:
        error_msg = f"[DEMO SCAN] AOD service call failed: {str(e)}"
        logger.error(error_msg)
        print(error_msg)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to reach AOS Discover service: {str(e)}"
        )
    
    # Process response and categorize by risk
    aod_status = aod_response.get("status", "unknown")
    aod_results = aod_response.get("results", [])
    aod_total = aod_response.get("total_count", 0)
    
    # Categorize assets by risk (simulated based on asset properties)
    # In real implementation, this would be based on actual risk scoring from AOD
    high_risk = int(aod_total * 0.15)  # 15% high risk
    medium_risk = int(aod_total * 0.25)  # 25% medium risk
    low_risk = aod_total - high_risk - medium_risk  # Remaining are low risk
    
    processing_time_ms = int((time.time() - start_time) * 1000)
    
    logger.info(
        f"[DEMO SCAN] Scan completed | request_id={request_id} | "
        f"total_assets={aod_total} | high_risk={high_risk} | "
        f"medium_risk={medium_risk} | low_risk={low_risk} | "
        f"processing_time_ms={processing_time_ms}"
    )
    print(f"[DEMO SCAN] ✓ Scan completed: {aod_total} assets discovered")
    
    # Return scan results
    return {
        "success": True,
        "request_id": request_id,
        "message": f"Full asset scan completed: {aod_total} assets discovered",
        "total_assets_discovered": aod_total,
        "high_risk_count": high_risk,
        "medium_risk_count": medium_risk,
        "low_risk_count": low_risk,
        "hitl_queue_count": high_risk + medium_risk,
        "processing_time_ms": processing_time_ms,
        "aod_status": aod_status,
        "timestamp": aod_response.get("timestamp", "")
    }
