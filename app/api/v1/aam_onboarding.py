"""
AAM Auto-Onboarding API Endpoints

REST API for auto-onboarding connections from AOD discovery with 90% day-one SLO.

Endpoints:
- POST /connections/onboard - Auto-onboard single connection intent
- POST /connections/onboard/batch - Auto-onboard multiple connection intents
- GET /metrics/funnel - Get funnel metrics for SLO tracking
- GET /connections?namespace=autonomy - List connections by namespace
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from uuid import UUID

from app.schemas.connection_intent import (
    ConnectionIntent,
    OnboardingResult,
    FunnelMetrics,
    OnboardBatchRequest,
    OnboardBatchResult
)
from app.security import get_current_user
from app.models import User

logger = logging.getLogger(__name__)

router = APIRouter()

# Global service instances (initialized by main.py startup)
onboarding_service = None
funnel_tracker = None


@router.post(
    "/connections/onboard",
    response_model=OnboardingResult,
    status_code=status.HTTP_201_CREATED,
    summary="Auto-onboard connection from AOD discovery",
    description="Accept connection intent from AOD and auto-onboard in Safe Mode. "
                "Validates allowlist, resolves credentials, runs tiny first sync (≤20 items), "
                "and persists to Connection Registry with namespace isolation."
)
async def onboard_connection(
    intent: ConnectionIntent,
    current_user: User = Depends(get_current_user)
):
    """
    Auto-onboard a single connection from AOD discovery
    
    **Authentication Required**: Bearer token in Authorization header
    
    **Flow**:
    1. Validate source_type against 30+ allowlist
    2. Resolve credentials (vault/env/consent/SP)
    3. Create/upsert connector (Airbyte or native)
    4. Discover schema (metadata-only for Safe Mode)
    5. Health check → ACTIVE
    6. Run tiny first sync (≤20 items)
    7. Update funnel metrics
    
    **Safe Mode**:
    - Read-only/metadata scopes
    - Tiny first sync (≤20 items)
    - No destructive operations
    - Idempotent upserts
    """
    global onboarding_service
    
    if not onboarding_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Onboarding service not initialized. Check server logs."
        )
    
    try:
        logger.info(
            f"User {current_user.email} initiated onboarding: {intent.source_type} "
            f"(namespace={intent.namespace}, risk={intent.risk_level})"
        )
        
        result = await onboarding_service.onboard_connection(intent)
        
        logger.info(
            f"Onboarding result: {result.status} (stage={result.funnel_stage}, "
            f"connection_id={result.connection_id})"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Onboarding error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Onboarding failed: {str(e)}"
        )


@router.post(
    "/connections/onboard/batch",
    response_model=OnboardBatchResult,
    status_code=status.HTTP_201_CREATED,
    summary="Auto-onboard multiple connections (batch)",
    description="Accept multiple connection intents and auto-onboard in parallel. "
                "Returns aggregated results and updated funnel metrics."
)
async def onboard_batch(
    request: OnboardBatchRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Auto-onboard multiple connections in batch
    
    **Authentication Required**: Bearer token in Authorization header
    
    Processes all intents sequentially and returns:
    - Individual onboarding results
    - Aggregated success/failure counts
    - Updated funnel metrics
    """
    global onboarding_service, funnel_tracker
    
    if not onboarding_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Onboarding service not initialized"
        )
    
    logger.info(f"User {current_user.email} initiated batch onboarding: {len(request.intents)} intents")
    
    results = []
    succeeded = 0
    failed = 0
    
    for intent in request.intents:
        try:
            result = await onboarding_service.onboard_connection(intent)
            results.append(result)
            
            if result.status == "ACTIVE":
                succeeded += 1
            else:
                failed += 1
                
        except Exception as e:
            logger.error(f"Batch item error: {e}")
            results.append(OnboardingResult(
                connection_id=None,
                status="FAILED",
                namespace=intent.namespace,
                funnel_stage="error",
                message="Batch processing error",
                error=str(e)
            ))
            failed += 1
    
    # Get updated funnel metrics (use first intent's namespace or default to 'autonomy')
    namespace = request.intents[0].namespace if request.intents else 'autonomy'
    funnel_metrics = funnel_tracker.get_all(namespace)
    
    return OnboardBatchResult(
        total=len(results),
        succeeded=succeeded,
        failed=failed,
        results=results,
        funnel=FunnelMetrics(**funnel_metrics)
    )


@router.get(
    "/metrics/funnel",
    response_model=FunnelMetrics,
    summary="Get auto-onboarding funnel metrics",
    description="Retrieve funnel metrics for SLO tracking. "
                "Returns 503 if coverage < 90% (SLO violation)."
)
async def get_funnel_metrics(
    namespace: str = Query("autonomy", description="Namespace filter (autonomy or demo)"),
    current_user: User = Depends(get_current_user)
):
    """
    Get funnel metrics for SLO tracking
    
    **Authentication Required**: Bearer token in Authorization header
    
    **Funnel Stages**:
    - eligible: Intents received (mappable + sanctioned + credentialed)
    - reachable: Passed health check
    - active: Tiny first sync succeeded
    - awaiting_credentials: Missing credentials
    - network_blocked: Health check failed
    - unsupported_type: Source type not in allowlist
    - healing: In HEALING state
    - error: Onboarding exception
    
    **SLO**: coverage = active / eligible ≥ 0.90
    
    **HTTP 503** if SLO not met (coverage < 90%)
    """
    global funnel_tracker
    
    if not funnel_tracker:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Funnel metrics tracker not initialized"
        )
    
    metrics = funnel_tracker.get_all(namespace)
    
    logger.info(
        f"User {current_user.email} requested funnel metrics for {namespace}: "
        f"coverage={metrics['coverage']:.2%}"
    )
    
    # SLO enforcement: Return 503 if coverage < 90%
    if not metrics['slo_met'] and metrics['eligible'] > 0:
        # Generate English failure summary with top blockers
        blockers = []
        if metrics['awaiting_credentials'] > 0:
            blockers.append(f"{metrics['awaiting_credentials']} awaiting credentials")
        if metrics['network_blocked'] > 0:
            blockers.append(f"{metrics['network_blocked']} network blocked")
        if metrics['unsupported_type'] > 0:
            blockers.append(f"{metrics['unsupported_type']} unsupported types")
        if metrics['error'] > 0:
            blockers.append(f"{metrics['error']} errors")
        
        blockers_str = ", ".join(blockers[:3]) if blockers else "unknown issues"
        
        summary = (
            f"SLO VIOLATION: Coverage {metrics['coverage']:.1%} < 90% target. "
            f"Eligible: {metrics['eligible']}, Active: {metrics['active']}. "
            f"Top blockers: {blockers_str}"
        )
        
        logger.error(summary)
        
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=summary,
            headers={"X-SLO-Coverage": str(metrics['coverage'])}
        )
    
    return FunnelMetrics(**metrics)


@router.get(
    "/connections/health/{connection_id}",
    summary="Get connection health status",
    description="Check health status of a specific connection including first sync stats."
)
async def get_connection_health(
    connection_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed health status of a connection
    
    **Authentication Required**: Bearer token in Authorization header
    
    Returns:
    - Connection status
    - First sync stats (rows, latency_ms)
    - Last health check timestamp
    - Namespace
    """
    from aam_hybrid.core.connection_manager import connection_manager
    
    connection = await connection_manager.get_connection(connection_id)
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connection not found: {connection_id}"
        )
    
    return {
        'connection_id': str(connection.id),
        'name': connection.name,
        'source_type': connection.source_type,
        'status': connection.status.value,
        'namespace': connection.namespace,
        'first_sync_rows': connection.first_sync_rows,
        'latency_ms': connection.latency_ms,
        'last_health_check': connection.last_health_check,
        'risk_level': connection.risk_level,
        'created_at': connection.created_at,
        'updated_at': connection.updated_at
    }
