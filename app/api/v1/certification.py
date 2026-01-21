"""
Certification API Endpoints

REST API for agent certification:
- Run certification evaluations
- Query certification status
- Manage certification lifecycle
- Export certification records
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app import models
from app.database import get_db
from app.security import get_current_user
from app.agentic.certification import (
    CertificationRegistry,
    CertificationWorkflow,
    CertificationStatus,
    CertificationType,
    CertificationScope,
    get_certification_registry,
)
from app.agentic.certification.workflows import AgentConfig

router = APIRouter(prefix="/certifications", tags=["Certification"])


# =============================================================================
# Request/Response Schemas
# =============================================================================

class CertificationRequest(BaseModel):
    """Request to certify an agent."""
    agent_id: UUID
    certification_type: CertificationType = CertificationType.AUTOMATED
    scope: CertificationScope = CertificationScope.PRODUCTION
    validity_days: int = Field(default=90, ge=1, le=365)
    conditions: Optional[List[str]] = None


class ManualReviewRequest(BaseModel):
    """Request to submit manual review."""
    requirement_id: str
    passed: bool
    notes: Optional[str] = None


class CertificationResponse(BaseModel):
    """Certification record response."""
    id: str
    agent_id: str
    agent_name: str
    agent_version: int
    status: str
    certification_type: str
    scope: str
    overall_score: float
    requirements_met: int
    requirements_total: int
    issued_at: Optional[datetime]
    valid_from: Optional[datetime]
    valid_until: Optional[datetime]
    certifier_type: str
    certifier_name: Optional[str]
    conditions: List[str]
    limitations: List[str]
    is_valid: bool
    days_until_expiry: Optional[int]

    class Config:
        from_attributes = True


class CertificationResultResponse(BaseModel):
    """Certification evaluation result response."""
    id: str
    agent_id: str
    status: str
    certification_type: str
    scope: str
    overall_score: float
    passed_count: int
    failed_count: int
    skipped_count: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_ms: int
    requirement_results: List[dict]


class CertificationStatusResponse(BaseModel):
    """Quick certification status check response."""
    agent_id: str
    is_certified: bool
    certification_id: Optional[str]
    status: Optional[str]
    scope: Optional[str]
    valid_until: Optional[datetime]
    days_until_expiry: Optional[int]
    can_execute: bool
    reason: Optional[str]


class CertificationStatsResponse(BaseModel):
    """Certification statistics response."""
    total: int
    by_status: dict
    by_scope: dict
    average_score: float
    expiring_soon: int


class RevocationRequest(BaseModel):
    """Request to revoke a certification."""
    reason: str = Field(..., min_length=10, max_length=1000)


# =============================================================================
# API Endpoints
# =============================================================================

@router.post("/evaluate", response_model=CertificationResultResponse)
async def evaluate_agent(
    request: CertificationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Run certification evaluation for an agent.

    This evaluates the agent against certification requirements.
    For automated certification, the result is returned immediately.
    For hybrid certification, manual review may be required.
    """
    # Get agent
    agent = db.query(models.Agent).filter(
        and_(
            models.Agent.id == request.agent_id,
            models.Agent.tenant_id == current_user.tenant_id,
        )
    ).first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {request.agent_id} not found"
        )

    # Build agent config
    agent_config = AgentConfig(
        agent_id=agent.id,
        agent_name=agent.name,
        agent_version=agent.version or 1,
        tenant_id=agent.tenant_id,
        system_prompt=agent.system_prompt,
        model=agent.model or "claude-sonnet-4-20250514",
        max_steps=agent.max_steps or 20,
        max_cost_usd=agent.max_cost_usd or 1.0,
        temperature=agent.temperature or 0.7,
        require_approval_for=agent.require_approval_for or [],
        forbidden_actions=agent.forbidden_actions or [],
        mcp_servers=[s.get("name", "") for s in (agent.mcp_servers or [])],
        description=agent.description,
    )

    # Run certification
    workflow = CertificationWorkflow()
    result = await workflow.run_certification(
        agent_config=agent_config,
        certification_type=request.certification_type,
        scope=request.scope,
        certifier_id=current_user.id,
        certifier_name=current_user.email,
    )

    # If passed, issue certification
    if result.status in (CertificationStatus.CERTIFIED, CertificationStatus.CONDITIONAL):
        certification = await workflow.issue_from_result(
            result=result,
            agent_config=agent_config,
            validity_days=request.validity_days,
            conditions=request.conditions,
            certifier_name=current_user.email,
        )

    return CertificationResultResponse(
        id=result.id,
        agent_id=str(result.agent_id),
        status=result.status.value,
        certification_type=result.certification_type.value,
        scope=result.scope.value,
        overall_score=result.overall_score,
        passed_count=result.passed_count,
        failed_count=result.failed_count,
        skipped_count=result.skipped_count,
        started_at=result.started_at,
        completed_at=result.completed_at,
        duration_ms=result.duration_ms,
        requirement_results=[
            {
                "requirement_id": r.requirement_id,
                "passed": r.passed,
                "score": r.score,
                "findings": r.findings,
                "recommendations": r.recommendations,
                "skipped": r.skipped,
                "skip_reason": r.skip_reason,
                "error": r.error,
            }
            for r in result.requirement_results
        ],
    )


@router.get("/agent/{agent_id}/status", response_model=CertificationStatusResponse)
async def get_certification_status(
    agent_id: UUID,
    scope: CertificationScope = CertificationScope.PRODUCTION,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Get quick certification status for an agent.

    Returns whether the agent can execute in the given scope.
    """
    # Verify agent belongs to tenant
    agent = db.query(models.Agent).filter(
        and_(
            models.Agent.id == agent_id,
            models.Agent.tenant_id == current_user.tenant_id,
        )
    ).first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )

    registry = get_certification_registry()
    cert = registry.get_current_certification(agent_id)

    can_execute, reason = registry.can_agent_execute(agent_id, scope)

    return CertificationStatusResponse(
        agent_id=str(agent_id),
        is_certified=cert is not None and cert.is_valid(),
        certification_id=cert.id if cert else None,
        status=cert.status.value if cert else None,
        scope=cert.scope.value if cert else None,
        valid_until=cert.valid_until if cert else None,
        days_until_expiry=cert.days_until_expiry() if cert else None,
        can_execute=can_execute,
        reason=reason,
    )


@router.get("/agent/{agent_id}/current", response_model=Optional[CertificationResponse])
async def get_current_certification(
    agent_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get the current valid certification for an agent."""
    # Verify agent belongs to tenant
    agent = db.query(models.Agent).filter(
        and_(
            models.Agent.id == agent_id,
            models.Agent.tenant_id == current_user.tenant_id,
        )
    ).first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )

    registry = get_certification_registry()
    cert = registry.get_current_certification(agent_id)

    if not cert:
        return None

    return CertificationResponse(
        id=cert.id,
        agent_id=str(cert.agent_id),
        agent_name=cert.agent_name,
        agent_version=cert.agent_version,
        status=cert.status.value,
        certification_type=cert.certification_type.value,
        scope=cert.scope.value,
        overall_score=cert.overall_score,
        requirements_met=cert.requirements_met,
        requirements_total=cert.requirements_total,
        issued_at=cert.issued_at,
        valid_from=cert.valid_from,
        valid_until=cert.valid_until,
        certifier_type=cert.certifier_type,
        certifier_name=cert.certifier_name,
        conditions=cert.conditions,
        limitations=cert.limitations,
        is_valid=cert.is_valid(),
        days_until_expiry=cert.days_until_expiry(),
    )


@router.get("/agent/{agent_id}/history", response_model=List[CertificationResponse])
async def get_certification_history(
    agent_id: UUID,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get certification history for an agent."""
    # Verify agent belongs to tenant
    agent = db.query(models.Agent).filter(
        and_(
            models.Agent.id == agent_id,
            models.Agent.tenant_id == current_user.tenant_id,
        )
    ).first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )

    registry = get_certification_registry()
    certs = registry.get_certification_history(agent_id, limit=limit)

    return [
        CertificationResponse(
            id=cert.id,
            agent_id=str(cert.agent_id),
            agent_name=cert.agent_name,
            agent_version=cert.agent_version,
            status=cert.status.value,
            certification_type=cert.certification_type.value,
            scope=cert.scope.value,
            overall_score=cert.overall_score,
            requirements_met=cert.requirements_met,
            requirements_total=cert.requirements_total,
            issued_at=cert.issued_at,
            valid_from=cert.valid_from,
            valid_until=cert.valid_until,
            certifier_type=cert.certifier_type,
            certifier_name=cert.certifier_name,
            conditions=cert.conditions,
            limitations=cert.limitations,
            is_valid=cert.is_valid(),
            days_until_expiry=cert.days_until_expiry(),
        )
        for cert in certs
    ]


@router.get("/{cert_id}", response_model=CertificationResponse)
async def get_certification(
    cert_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get a specific certification by ID."""
    registry = get_certification_registry()
    cert = registry.get_certification(cert_id)

    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certification {cert_id} not found"
        )

    # Verify tenant access
    if cert.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this certification"
        )

    return CertificationResponse(
        id=cert.id,
        agent_id=str(cert.agent_id),
        agent_name=cert.agent_name,
        agent_version=cert.agent_version,
        status=cert.status.value,
        certification_type=cert.certification_type.value,
        scope=cert.scope.value,
        overall_score=cert.overall_score,
        requirements_met=cert.requirements_met,
        requirements_total=cert.requirements_total,
        issued_at=cert.issued_at,
        valid_from=cert.valid_from,
        valid_until=cert.valid_until,
        certifier_type=cert.certifier_type,
        certifier_name=cert.certifier_name,
        conditions=cert.conditions,
        limitations=cert.limitations,
        is_valid=cert.is_valid(),
        days_until_expiry=cert.days_until_expiry(),
    )


@router.get("/{cert_id}/export")
async def export_certification(
    cert_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Export a certification record for publishing.

    Returns an immutable, shareable record of the certification.
    """
    registry = get_certification_registry()
    cert = registry.get_certification(cert_id)

    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certification {cert_id} not found"
        )

    # Verify tenant access
    if cert.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this certification"
        )

    export = registry.export_certification(cert_id)
    return export


@router.post("/{cert_id}/revoke", response_model=CertificationResponse)
async def revoke_certification(
    cert_id: str,
    request: RevocationRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Revoke a certification.

    This permanently invalidates the certification.
    """
    registry = get_certification_registry()
    cert = registry.get_certification(cert_id)

    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certification {cert_id} not found"
        )

    # Verify tenant access
    if cert.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this certification"
        )

    # Revoke
    cert = registry.revoke_certification(cert_id, current_user.id, request.reason)

    return CertificationResponse(
        id=cert.id,
        agent_id=str(cert.agent_id),
        agent_name=cert.agent_name,
        agent_version=cert.agent_version,
        status=cert.status.value,
        certification_type=cert.certification_type.value,
        scope=cert.scope.value,
        overall_score=cert.overall_score,
        requirements_met=cert.requirements_met,
        requirements_total=cert.requirements_total,
        issued_at=cert.issued_at,
        valid_from=cert.valid_from,
        valid_until=cert.valid_until,
        certifier_type=cert.certifier_type,
        certifier_name=cert.certifier_name,
        conditions=cert.conditions,
        limitations=cert.limitations,
        is_valid=cert.is_valid(),
        days_until_expiry=cert.days_until_expiry(),
    )


@router.post("/{cert_id}/suspend", response_model=CertificationResponse)
async def suspend_certification(
    cert_id: str,
    request: RevocationRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Temporarily suspend a certification.

    The certification can be reinstated later.
    """
    registry = get_certification_registry()
    cert = registry.get_certification(cert_id)

    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certification {cert_id} not found"
        )

    # Verify tenant access
    if cert.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this certification"
        )

    # Suspend
    cert = registry.suspend_certification(cert_id, request.reason)

    return CertificationResponse(
        id=cert.id,
        agent_id=str(cert.agent_id),
        agent_name=cert.agent_name,
        agent_version=cert.agent_version,
        status=cert.status.value,
        certification_type=cert.certification_type.value,
        scope=cert.scope.value,
        overall_score=cert.overall_score,
        requirements_met=cert.requirements_met,
        requirements_total=cert.requirements_total,
        issued_at=cert.issued_at,
        valid_from=cert.valid_from,
        valid_until=cert.valid_until,
        certifier_type=cert.certifier_type,
        certifier_name=cert.certifier_name,
        conditions=cert.conditions,
        limitations=cert.limitations,
        is_valid=cert.is_valid(),
        days_until_expiry=cert.days_until_expiry(),
    )


@router.post("/{cert_id}/reinstate", response_model=CertificationResponse)
async def reinstate_certification(
    cert_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Reinstate a suspended certification.
    """
    registry = get_certification_registry()
    cert = registry.get_certification(cert_id)

    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certification {cert_id} not found"
        )

    # Verify tenant access
    if cert.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this certification"
        )

    if cert.status != CertificationStatus.SUSPENDED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reinstate - certification status is {cert.status.value}"
        )

    # Reinstate
    cert = registry.reinstate_certification(cert_id)

    return CertificationResponse(
        id=cert.id,
        agent_id=str(cert.agent_id),
        agent_name=cert.agent_name,
        agent_version=cert.agent_version,
        status=cert.status.value,
        certification_type=cert.certification_type.value,
        scope=cert.scope.value,
        overall_score=cert.overall_score,
        requirements_met=cert.requirements_met,
        requirements_total=cert.requirements_total,
        issued_at=cert.issued_at,
        valid_from=cert.valid_from,
        valid_until=cert.valid_until,
        certifier_type=cert.certifier_type,
        certifier_name=cert.certifier_name,
        conditions=cert.conditions,
        limitations=cert.limitations,
        is_valid=cert.is_valid(),
        days_until_expiry=cert.days_until_expiry(),
    )


@router.get("/", response_model=List[CertificationResponse])
async def list_certifications(
    status_filter: Optional[CertificationStatus] = None,
    include_expired: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """List all certifications for the current tenant."""
    registry = get_certification_registry()
    certs = registry.get_tenant_certifications(
        tenant_id=current_user.tenant_id,
        status=status_filter,
        include_expired=include_expired,
    )

    return [
        CertificationResponse(
            id=cert.id,
            agent_id=str(cert.agent_id),
            agent_name=cert.agent_name,
            agent_version=cert.agent_version,
            status=cert.status.value,
            certification_type=cert.certification_type.value,
            scope=cert.scope.value,
            overall_score=cert.overall_score,
            requirements_met=cert.requirements_met,
            requirements_total=cert.requirements_total,
            issued_at=cert.issued_at,
            valid_from=cert.valid_from,
            valid_until=cert.valid_until,
            certifier_type=cert.certifier_type,
            certifier_name=cert.certifier_name,
            conditions=cert.conditions,
            limitations=cert.limitations,
            is_valid=cert.is_valid(),
            days_until_expiry=cert.days_until_expiry(),
        )
        for cert in certs
    ]


@router.get("/stats", response_model=CertificationStatsResponse)
async def get_certification_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get certification statistics for the current tenant."""
    registry = get_certification_registry()
    stats = registry.get_statistics(tenant_id=current_user.tenant_id)

    return CertificationStatsResponse(**stats)
