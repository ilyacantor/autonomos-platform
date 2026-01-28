"""
Agent Orchestration API

CRUD endpoints for managing agents, runs, and approvals.
Part of the Agentic Orchestration Platform (Phase 1).
"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app import models, schemas
from app.database import get_db
from app.security import get_current_user
from app.api.utils import get_or_404
from app.api.pagination import PaginationParams, paginate_query

router = APIRouter()


# =============================================================================
# Agent CRUD Endpoints
# =============================================================================

@router.post("/", response_model=schemas.AgentResponse, status_code=status.HTTP_201_CREATED)
def create_agent(
    agent_data: schemas.AgentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Create a new agent configuration."""
    # Convert MCP servers to JSON-serializable format
    mcp_servers = [s.model_dump() for s in agent_data.mcp_servers] if agent_data.mcp_servers else []

    agent = models.Agent(
        tenant_id=current_user.tenant_id,
        name=agent_data.name,
        description=agent_data.description,
        agent_type=agent_data.agent_type.value,
        graph_definition=agent_data.graph_definition,
        system_prompt=agent_data.system_prompt,
        mcp_servers=mcp_servers,
        model=agent_data.model,
        temperature=agent_data.temperature,
        max_tokens=agent_data.max_tokens,
        max_steps=agent_data.max_steps,
        max_cost_usd=agent_data.max_cost_usd,
        require_approval_for=agent_data.require_approval_for,
        forbidden_actions=agent_data.forbidden_actions,
        created_by=current_user.id,
    )

    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


@router.get("/", response_model=schemas.AgentListResponse)
def list_agents(
    pagination: PaginationParams = Depends(),
    status: Optional[schemas.AgentStatus] = None,
    agent_type: Optional[schemas.AgentType] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List all agents for the current tenant."""
    query = db.query(models.Agent).filter(
        models.Agent.tenant_id == current_user.tenant_id
    )

    if status:
        query = query.filter(models.Agent.status == status.value)
    if agent_type:
        query = query.filter(models.Agent.agent_type == agent_type.value)

    result = paginate_query(
        query,
        pagination,
        order_by=models.Agent.created_at.desc()
    )

    return result.build_response(schemas.AgentListResponse)


@router.get("/{agent_id}", response_model=schemas.AgentResponse)
def get_agent(
    agent_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get a specific agent by ID."""
    agent = get_or_404(
        db.query(models.Agent).filter(
            and_(
                models.Agent.id == agent_id,
                models.Agent.tenant_id == current_user.tenant_id
            )
        ).first(),
        "Agent",
        agent_id
    )
    return agent


@router.patch("/{agent_id}", response_model=schemas.AgentResponse)
def update_agent(
    agent_id: UUID,
    agent_data: schemas.AgentUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Update an existing agent configuration."""
    agent = get_or_404(
        db.query(models.Agent).filter(
            and_(
                models.Agent.id == agent_id,
                models.Agent.tenant_id == current_user.tenant_id
            )
        ).first(),
        "Agent",
        agent_id
    )

    # Update only provided fields
    update_data = agent_data.model_dump(exclude_unset=True)

    # Handle enum conversion
    if 'agent_type' in update_data and update_data['agent_type']:
        update_data['agent_type'] = update_data['agent_type'].value
    if 'status' in update_data and update_data['status']:
        update_data['status'] = update_data['status'].value

    # Handle MCP servers
    if 'mcp_servers' in update_data and update_data['mcp_servers']:
        update_data['mcp_servers'] = [s.model_dump() for s in update_data['mcp_servers']]

    for field, value in update_data.items():
        setattr(agent, field, value)

    # Increment version on update
    agent.version = (agent.version or 1) + 1

    db.commit()
    db.refresh(agent)
    return agent


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(
    agent_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Delete an agent (soft delete by setting status to archived)."""
    agent = get_or_404(
        db.query(models.Agent).filter(
            and_(
                models.Agent.id == agent_id,
                models.Agent.tenant_id == current_user.tenant_id
            )
        ).first(),
        "Agent",
        agent_id
    )

    # Soft delete
    agent.status = 'archived'
    db.commit()

    return None


# =============================================================================
# Agent Run Endpoints
# =============================================================================

@router.post("/{agent_id}/runs", response_model=schemas.AgentRunResponse, status_code=status.HTTP_201_CREATED)
def create_run(
    agent_id: UUID,
    run_data: schemas.AgentRunCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Start a new agent run.

    This creates the run record and returns immediately.
    The actual execution happens asynchronously via LangGraph.
    """
    # Verify agent exists and is active
    agent = get_or_404(
        db.query(models.Agent).filter(
            and_(
                models.Agent.id == agent_id,
                models.Agent.tenant_id == current_user.tenant_id,
                models.Agent.status == 'active'
            )
        ).first(),
        "Agent",
        agent_id,
        detail=f"Agent {agent_id} not found or not active"
    )

    # Create run record
    run = models.AgentRun(
        agent_id=agent_id,
        tenant_id=current_user.tenant_id,
        status='pending',
        input_data={
            'input': run_data.input,
            'context': run_data.context,
            'stream': run_data.stream
        },
        triggered_by=current_user.id,
        trigger_type=run_data.trigger_type.value,
    )

    db.add(run)
    db.commit()
    db.refresh(run)

    # TODO: Phase 2 - Dispatch to LangGraph executor via Redis queue
    # For now, just return the pending run

    return run


@router.get("/{agent_id}/runs", response_model=schemas.AgentRunListResponse)
def list_runs(
    agent_id: UUID,
    pagination: PaginationParams = Depends(),
    status: Optional[schemas.RunStatus] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List runs for a specific agent."""
    # Verify agent belongs to tenant
    get_or_404(
        db.query(models.Agent).filter(
            and_(
                models.Agent.id == agent_id,
                models.Agent.tenant_id == current_user.tenant_id
            )
        ).first(),
        "Agent",
        agent_id
    )

    query = db.query(models.AgentRun).filter(
        models.AgentRun.agent_id == agent_id
    )

    if status:
        query = query.filter(models.AgentRun.status == status.value)

    result = paginate_query(
        query,
        pagination,
        order_by=models.AgentRun.created_at.desc()
    )

    return result.build_response(schemas.AgentRunListResponse)


@router.get("/{agent_id}/runs/{run_id}", response_model=schemas.AgentRunResponse)
def get_run(
    agent_id: UUID,
    run_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get details of a specific run."""
    run = get_or_404(
        db.query(models.AgentRun).filter(
            and_(
                models.AgentRun.id == run_id,
                models.AgentRun.agent_id == agent_id,
                models.AgentRun.tenant_id == current_user.tenant_id
            )
        ).first(),
        "Run",
        run_id
    )
    return run


@router.post("/{agent_id}/runs/{run_id}/cancel", response_model=schemas.AgentRunResponse)
def cancel_run(
    agent_id: UUID,
    run_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Cancel a running or pending agent run."""
    run = get_or_404(
        db.query(models.AgentRun).filter(
            and_(
                models.AgentRun.id == run_id,
                models.AgentRun.agent_id == agent_id,
                models.AgentRun.tenant_id == current_user.tenant_id
            )
        ).first(),
        "Run",
        run_id
    )

    if run.status not in ('pending', 'running', 'awaiting_approval'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel run in status: {run.status}"
        )

    run.status = 'cancelled'
    run.completed_at = datetime.utcnow()

    # Also cancel any pending approvals
    db.query(models.AgentApproval).filter(
        and_(
            models.AgentApproval.run_id == run_id,
            models.AgentApproval.status == 'pending'
        )
    ).update({'status': 'expired'})

    db.commit()
    db.refresh(run)
    return run


# =============================================================================
# Approval Endpoints
# =============================================================================

@router.get("/approvals/pending", response_model=schemas.PendingApprovalsResponse)
def list_pending_approvals(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List all pending approvals for the current tenant."""
    approvals = db.query(models.AgentApproval).filter(
        and_(
            models.AgentApproval.tenant_id == current_user.tenant_id,
            models.AgentApproval.status == 'pending',
            models.AgentApproval.expires_at > datetime.utcnow()
        )
    ).order_by(models.AgentApproval.requested_at.desc()).all()

    return schemas.PendingApprovalsResponse(
        items=approvals,
        total=len(approvals)
    )


@router.get("/{agent_id}/runs/{run_id}/approvals", response_model=list[schemas.AgentApprovalResponse])
def list_run_approvals(
    agent_id: UUID,
    run_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List all approvals for a specific run."""
    # Verify run belongs to tenant
    get_or_404(
        db.query(models.AgentRun).filter(
            and_(
                models.AgentRun.id == run_id,
                models.AgentRun.agent_id == agent_id,
                models.AgentRun.tenant_id == current_user.tenant_id
            )
        ).first(),
        "Run",
        run_id
    )

    approvals = db.query(models.AgentApproval).filter(
        models.AgentApproval.run_id == run_id
    ).order_by(models.AgentApproval.step_number).all()

    return approvals


@router.post("/{agent_id}/runs/{run_id}/approvals/{approval_id}/respond", response_model=schemas.AgentApprovalResponse)
def respond_to_approval(
    agent_id: UUID,
    run_id: UUID,
    approval_id: UUID,
    action: schemas.ApprovalAction,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Approve or reject a pending approval.

    Implements ARB Condition 1: Token refresh happens on approval resume.
    """
    approval = get_or_404(
        db.query(models.AgentApproval).filter(
            and_(
                models.AgentApproval.id == approval_id,
                models.AgentApproval.run_id == run_id,
                models.AgentApproval.tenant_id == current_user.tenant_id
            )
        ).first(),
        "Approval",
        approval_id
    )

    if approval.status != 'pending':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Approval already resolved: {approval.status}"
        )

    if approval.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Approval has expired"
        )

    # Update approval
    approval.status = 'approved' if action.approved else 'rejected'
    approval.responded_at = datetime.utcnow()
    approval.responded_by = current_user.id
    approval.approval_notes = action.notes
    approval.rejection_reason = action.rejection_reason

    # Get the run
    run = db.query(models.AgentRun).filter(
        models.AgentRun.id == run_id
    ).first()

    if action.approved:
        # ARB Condition 1: Refresh OBO token on approval
        # Issue new token with 15-minute validity
        run.obo_token_issued_at = datetime.utcnow()
        run.obo_token_expires_at = datetime.utcnow() + timedelta(minutes=15)
        run.status = 'running'

        # TODO: Phase 2 - Signal LangGraph executor to resume
    else:
        run.status = 'cancelled'
        run.completed_at = datetime.utcnow()
        run.error = f"Approval rejected: {action.rejection_reason or 'No reason provided'}"

    db.commit()
    db.refresh(approval)
    return approval


# =============================================================================
# Evaluation Endpoints
# =============================================================================

@router.get("/{agent_id}/evals", response_model=list[schemas.EvalRunResponse])
def list_eval_runs(
    agent_id: UUID,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List recent evaluation runs for an agent."""
    # Verify agent belongs to tenant
    agent = db.query(models.Agent).filter(
        and_(
            models.Agent.id == agent_id,
            models.Agent.tenant_id == current_user.tenant_id
        )
    ).first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )

    evals = db.query(models.AgentEvalRun).filter(
        models.AgentEvalRun.agent_id == agent_id
    ).order_by(models.AgentEvalRun.started_at.desc()).limit(limit).all()

    return evals


@router.post("/{agent_id}/evals/run", response_model=schemas.EvalRunResponse, status_code=status.HTTP_201_CREATED)
def trigger_eval_run(
    agent_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Trigger a new evaluation run against the golden dataset.

    This is a long-running operation. The endpoint returns immediately
    with a pending eval run. Poll the status or use WebSocket for updates.
    """
    # Verify agent exists and is active
    agent = db.query(models.Agent).filter(
        and_(
            models.Agent.id == agent_id,
            models.Agent.tenant_id == current_user.tenant_id,
            models.Agent.status == 'active'
        )
    ).first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found or not active"
        )

    # Create eval run record
    eval_run = models.AgentEvalRun(
        agent_id=agent_id,
        tenant_id=current_user.tenant_id,
        triggered_by=current_user.id,
        total_cases=50,  # Golden dataset size
    )

    db.add(eval_run)
    db.commit()
    db.refresh(eval_run)

    # TODO: Phase 1 completion - Dispatch to eval worker

    return eval_run


@router.get("/{agent_id}/evals/{eval_id}", response_model=schemas.EvalRunResponse)
def get_eval_run(
    agent_id: UUID,
    eval_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get details of a specific evaluation run."""
    eval_run = db.query(models.AgentEvalRun).filter(
        and_(
            models.AgentEvalRun.id == eval_id,
            models.AgentEvalRun.agent_id == agent_id,
            models.AgentEvalRun.tenant_id == current_user.tenant_id
        )
    ).first()

    if not eval_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Eval run {eval_id} not found"
        )

    return eval_run
