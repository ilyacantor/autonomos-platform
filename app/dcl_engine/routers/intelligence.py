"""
DCL Intelligence Router - Phase 2

API endpoints for intelligence services:
- LLM mapping proposals
- RAG similarity lookup
- Confidence scoring
- Drift repair proposals
- Approval workflows

Achieves 100% RACI compliance by centralizing all decision-making in DCL.
"""

import logging
from typing import List, Any, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.session import get_async_db
from app.dcl_engine.llm_service import get_llm_service, LLMService
from app.dcl_engine.services.intelligence import (
    LLMProposalService,
    RAGLookupService,
    ConfidenceScoringService,
    DriftRepairService,
    MappingApprovalService
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dcl/intelligence", tags=["intelligence"])


class ProposeRequest(BaseModel):
    """Request schema for POST /dcl/intelligence/propose-mapping"""
    connector: str = Field(..., description="Source connector name (e.g., 'salesforce')")
    source_table: str = Field(..., description="Source table name (e.g., 'Opportunity')")
    source_field: str = Field(..., description="Source field name (e.g., 'Amount')")
    sample_values: List[Any] = Field(..., description="Sample values from the field")
    tenant_id: str = Field(..., description="Tenant identifier")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context metadata")


class MappingProposalResponse(BaseModel):
    """Response schema for mapping proposals"""
    proposal_id: str
    connector: str
    source_table: str
    source_field: str
    canonical_entity: str
    canonical_field: str
    confidence: float
    reasoning: str
    alternatives: List[Dict[str, Any]]
    action: str
    source: str
    created_at: datetime


class ConfidenceRequest(BaseModel):
    """Request schema for POST /dcl/intelligence/calculate-confidence"""
    mapping_id: Optional[str] = None
    proposal_id: Optional[str] = None
    factors: Dict[str, Any] = Field(..., description="Confidence factors to evaluate")
    tenant_id: str = Field(..., description="Tenant identifier")


class ConfidenceResponse(BaseModel):
    """Response schema for confidence calculations"""
    score: float
    tier: str
    factors: Dict[str, float]
    recommendations: List[str]


class DriftRepairRequest(BaseModel):
    """Request schema for POST /dcl/intelligence/repair-drift"""
    drift_event_id: str
    tenant_id: str


class FieldRepairResponse(BaseModel):
    """Field repair in drift repair proposal"""
    field_name: str
    drift_type: str
    canonical_field: str
    canonical_entity: str
    confidence: float
    action: str
    reasoning: str


class RepairProposalResponse(BaseModel):
    """Response schema for drift repair proposals"""
    repair_proposal_id: str
    drift_event_id: str
    field_repairs: List[FieldRepairResponse]
    overall_confidence: float
    auto_applied_count: int
    hitl_queued_count: int
    rejected_count: int
    created_at: datetime


class ApprovalSubmitRequest(BaseModel):
    """Request schema for approval submission"""
    proposal_id: str
    tenant_id: str
    priority: str = Field("normal", description="Priority level (normal, high, critical)")
    notes: Optional[str] = None


class ApprovalWorkflowResponse(BaseModel):
    """Response schema for approval workflows"""
    workflow_id: str
    proposal_id: str
    status: str
    assigned_to: str
    created_at: datetime
    expires_at: datetime
    priority: str
    approver_id: Optional[str] = None
    approval_notes: Optional[str] = None
    rejection_reason: Optional[str] = None


class ApprovalActionRequest(BaseModel):
    """Request schema for approve/reject actions"""
    approver_id: str
    notes: Optional[str] = None


async def get_services(
    db: AsyncSession = Depends(get_async_db)
) -> Dict[str, Any]:
    """Dependency injection for intelligence services"""
    llm_client = get_llm_service()
    
    confidence_service = ConfidenceScoringService()
    rag_service = RAGLookupService(db_session=db, embedding_service=None)
    
    llm_service = LLMProposalService(
        llm_client=llm_client,
        rag_service=rag_service,
        confidence_service=confidence_service,
        db_session=db
    )
    
    approval_service = MappingApprovalService(
        db_session=db,
        notification_service=None
    )
    
    drift_repair_service = DriftRepairService(
        llm_service=llm_service,
        rag_service=rag_service,
        confidence_service=confidence_service,
        db_session=db
    )
    
    return {
        'llm': llm_service,
        'rag': rag_service,
        'confidence': confidence_service,
        'drift_repair': drift_repair_service,
        'approval': approval_service
    }


@router.post("/propose-mapping", response_model=MappingProposalResponse)
async def propose_mapping(
    request: ProposeRequest,
    services: Dict[str, Any] = Depends(get_services)
):
    """
    Generate canonical mapping proposal for source field.
    
    Uses RAG-first strategy with LLM fallback.
    Automatically scores confidence and determines action tier.
    """
    try:
        llm_service: LLMProposalService = services['llm']
        
        proposal = await llm_service.propose_mapping(
            connector=request.connector,
            source_table=request.source_table,
            source_field=request.source_field,
            sample_values=request.sample_values,
            tenant_id=request.tenant_id,
            context=request.context
        )
        
        return MappingProposalResponse(
            proposal_id=proposal.proposal_id,
            connector=proposal.connector,
            source_table=proposal.source_table,
            source_field=proposal.source_field,
            canonical_entity=proposal.canonical_entity,
            canonical_field=proposal.canonical_field,
            confidence=proposal.confidence,
            reasoning=proposal.reasoning,
            alternatives=proposal.alternatives,
            action=proposal.action,
            source=proposal.source,
            created_at=proposal.created_at
        )
        
    except Exception as e:
        logger.error(f"Failed to propose mapping: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rag-lookup/{connector}/{source_table}/{source_field}")
async def rag_lookup(
    connector: str,
    source_table: str,
    source_field: str,
    tenant_id: str = "default",
    similarity_threshold: float = 0.85,
    services: Dict[str, Any] = Depends(get_services)
):
    """
    RAG similarity search for existing mappings.
    
    Returns best match if similarity exceeds threshold.
    """
    try:
        rag_service: RAGLookupService = services['rag']
        
        result = await rag_service.lookup_mapping(
            connector=connector,
            source_table=source_table,
            source_field=source_field,
            tenant_id=tenant_id,
            similarity_threshold=similarity_threshold
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="No RAG match found")
        
        return {
            "canonical_field": result.canonical_field,
            "canonical_entity": result.canonical_entity,
            "similarity": result.similarity,
            "source_mapping_id": result.source_mapping_id,
            "usage_count": result.usage_count,
            "confidence": result.confidence,
            "last_used": result.last_used
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"RAG lookup failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calculate-confidence", response_model=ConfidenceResponse)
async def calculate_confidence(
    request: ConfidenceRequest,
    services: Dict[str, Any] = Depends(get_services)
):
    """
    Calculate multi-factor confidence score for mapping.
    
    Factors: source_quality, usage_frequency, validation_success,
             human_approval, rag_similarity
    """
    try:
        confidence_service: ConfidenceScoringService = services['confidence']
        
        result = confidence_service.calculate_confidence(
            factors=request.factors,
            tenant_id=request.tenant_id
        )
        
        return ConfidenceResponse(
            score=result.score,
            tier=result.tier,
            factors=result.factors,
            recommendations=result.recommendations
        )
        
    except Exception as e:
        logger.error(f"Confidence calculation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/repair-drift", response_model=RepairProposalResponse)
async def repair_drift(
    request: DriftRepairRequest,
    services: Dict[str, Any] = Depends(get_services)
):
    """
    Generate repair proposals for schema drift.
    
    Analyzes drifted fields and proposes canonical mappings.
    Routes proposals to auto-apply, HITL queue, or rejection.
    """
    try:
        drift_repair_service: DriftRepairService = services['drift_repair']
        
        proposal = await drift_repair_service.propose_repair(
            drift_event_id=request.drift_event_id,
            tenant_id=request.tenant_id
        )
        
        field_repairs = [
            FieldRepairResponse(
                field_name=repair.field_name,
                drift_type=repair.drift_type,
                canonical_field=repair.canonical_field,
                canonical_entity=repair.canonical_entity,
                confidence=repair.confidence,
                action=repair.action,
                reasoning=repair.reasoning
            )
            for repair in proposal.field_repairs
        ]
        
        return RepairProposalResponse(
            repair_proposal_id=proposal.repair_proposal_id,
            drift_event_id=proposal.drift_event_id,
            field_repairs=field_repairs,
            overall_confidence=proposal.overall_confidence,
            auto_applied_count=proposal.auto_applied_count,
            hitl_queued_count=proposal.hitl_queued_count,
            rejected_count=proposal.rejected_count,
            created_at=proposal.created_at
        )
        
    except Exception as e:
        logger.error(f"Drift repair failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/submit-for-approval", response_model=ApprovalWorkflowResponse)
async def submit_for_approval(
    request: ApprovalSubmitRequest,
    services: Dict[str, Any] = Depends(get_services)
):
    """
    Submit mapping proposal for human review.
    
    Creates approval workflow with 7-day TTL.
    Sends notification to assigned approver.
    """
    try:
        approval_service: MappingApprovalService = services['approval']
        
        workflow = await approval_service.submit_for_approval(
            proposal_id=request.proposal_id,
            tenant_id=request.tenant_id,
            priority=request.priority,
            notes=request.notes
        )
        
        return ApprovalWorkflowResponse(
            workflow_id=workflow.workflow_id,
            proposal_id=workflow.proposal_id,
            status=workflow.status,
            assigned_to=workflow.assigned_to,
            created_at=workflow.created_at,
            expires_at=workflow.expires_at,
            priority=workflow.priority
        )
        
    except Exception as e:
        logger.error(f"Approval submission failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/approve/{workflow_id}")
async def approve_proposal(
    workflow_id: str,
    request: ApprovalActionRequest,
    services: Dict[str, Any] = Depends(get_services)
):
    """
    Approve a pending mapping proposal.
    
    Creates active field mapping from approved proposal.
    """
    try:
        approval_service: MappingApprovalService = services['approval']
        
        await approval_service.approve_proposal(
            workflow_id=workflow_id,
            approver_id=request.approver_id,
            notes=request.notes
        )
        
        return {"status": "approved", "workflow_id": workflow_id}
        
    except Exception as e:
        logger.error(f"Approval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reject/{workflow_id}")
async def reject_proposal(
    workflow_id: str,
    approver_id: str,
    reason: str,
    services: Dict[str, Any] = Depends(get_services)
):
    """
    Reject a pending mapping proposal.
    
    Stores rejection reason for audit trail.
    """
    try:
        approval_service: MappingApprovalService = services['approval']
        
        await approval_service.reject_proposal(
            workflow_id=workflow_id,
            approver_id=approver_id,
            reason=reason
        )
        
        return {"status": "rejected", "workflow_id": workflow_id}
        
    except Exception as e:
        logger.error(f"Rejection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/approval-status/{proposal_id}", response_model=ApprovalWorkflowResponse)
async def get_approval_status(
    proposal_id: str,
    services: Dict[str, Any] = Depends(get_services)
):
    """
    Check approval workflow status for a proposal.
    
    Returns latest workflow state.
    """
    try:
        approval_service: MappingApprovalService = services['approval']
        
        workflow = await approval_service.get_approval_status(proposal_id)
        
        if not workflow:
            raise HTTPException(status_code=404, detail="No approval workflow found")
        
        return ApprovalWorkflowResponse(
            workflow_id=workflow.workflow_id,
            proposal_id=workflow.proposal_id,
            status=workflow.status,
            assigned_to=workflow.assigned_to,
            created_at=workflow.created_at,
            expires_at=workflow.expires_at,
            priority=workflow.priority,
            approver_id=workflow.approver_id,
            approval_notes=workflow.approval_notes,
            rejection_reason=workflow.rejection_reason
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get approval status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
