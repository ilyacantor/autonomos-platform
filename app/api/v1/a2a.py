"""
A2A (Agent-to-Agent) API Endpoints

REST API for agent collaboration:
- Agent Card management (/.well-known/agent.json)
- Discovery endpoints
- Delegation API
- Inter-agent messaging
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app import models
from app.database import get_db
from app.security import get_current_user
from app.api.utils import get_or_404, handle_api_errors
from app.agentic.a2a import (
    AgentCard,
    AgentCapability,
    AgentEndpoint,
    AuthScheme,
    create_agent_card,
    AgentDiscovery,
    DiscoveryFilter,
    get_agent_discovery,
    DelegationManager,
    DelegationRequest,
    DelegationStatus,
    DelegationType,
    get_delegation_manager,
    A2AProtocol,
    A2AMessage,
    A2AMessageType,
    get_a2a_protocol,
)
from app.agentic.certification import get_certification_registry

router = APIRouter(prefix="/a2a", tags=["A2A Protocol"])


# =============================================================================
# Request/Response Schemas
# =============================================================================

class AgentCardResponse(BaseModel):
    """Agent Card response."""
    id: str
    name: str
    description: str
    version: str
    agent_type: str
    role: str
    endpoints: List[Dict[str, Any]]
    capabilities: List[Dict[str, Any]]
    protocol_version: str
    certification_id: Optional[str]
    certification_status: Optional[str]
    trust_level: int
    can_delegate: bool
    can_accept_delegation: bool
    tags: List[str]


class DiscoveryRequest(BaseModel):
    """Agent discovery request."""
    capability_ids: Optional[List[str]] = None
    capability_tags: Optional[List[str]] = None
    agent_types: Optional[List[str]] = None
    roles: Optional[List[str]] = None
    min_trust_level: int = 0
    require_certified: bool = False
    can_accept_delegation: Optional[bool] = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class DiscoveryResponse(BaseModel):
    """Agent discovery response."""
    agents: List[AgentCardResponse]
    total: int
    has_more: bool
    query_time_ms: int


class DelegationCreateRequest(BaseModel):
    """Request to delegate a task."""
    delegatee_id: Optional[str] = None  # Auto-select if not provided
    task_input: str = Field(..., min_length=1, max_length=50000)
    capability_id: Optional[str] = None
    delegation_type: DelegationType = DelegationType.FULL
    priority: int = Field(default=5, ge=1, le=10)
    timeout_seconds: int = Field(default=300, ge=30, le=3600)
    context: Optional[Dict[str, Any]] = None


class DelegationResponse(BaseModel):
    """Delegation response."""
    id: str
    delegator_id: str
    delegatee_id: str
    task_input: str
    capability_id: Optional[str]
    delegation_type: str
    priority: int
    status: str
    status_message: Optional[str]
    created_at: datetime
    accepted_at: Optional[datetime]
    completed_at: Optional[datetime]
    result: Optional[Any]
    error: Optional[str]


class MessageRequest(BaseModel):
    """A2A message request."""
    to_agent: str
    message_type: str
    payload: Dict[str, Any] = Field(default_factory=dict)


class MessageResponse(BaseModel):
    """A2A message response."""
    id: str
    type: str
    from_agent: str
    to_agent: str
    payload: Dict[str, Any]
    timestamp: datetime


# =============================================================================
# Agent Card Endpoints
# =============================================================================

@router.get("/agents/{agent_id}/.well-known/agent.json", response_model=AgentCardResponse)
async def get_agent_card(
    agent_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Get the Agent Card for an agent (public endpoint).

    This is the standard A2A discovery endpoint.
    """
    # Get agent from database
    agent = get_or_404(
        db.query(models.Agent).filter(
            models.Agent.id == agent_id
        ).first(),
        "Agent",
        agent_id
    )

    # Check if agent is registered for discovery
    discovery = get_agent_discovery()
    card = discovery.get(str(agent_id))

    if not card:
        # Create card on-the-fly for unregistered agents
        cert_registry = get_certification_registry()
        cert = cert_registry.get_current_certification(agent_id)

        card = create_agent_card(
            agent_id=agent_id,
            name=agent.name,
            description=agent.description or "",
            tenant_id=agent.tenant_id,
            base_url="",  # Would be configured per deployment
            agent_type=agent.agent_type,
            certification_id=cert.id if cert else None,
            trust_level=int(cert.overall_score * 100) if cert else 0,
        )

    return AgentCardResponse(
        id=card.id,
        name=card.name,
        description=card.description,
        version=card.version,
        agent_type=card.agent_type,
        role=card.role,
        endpoints=[ep.to_dict() for ep in card.endpoints],
        capabilities=[cap.to_dict() for cap in card.capabilities],
        protocol_version=card.protocol_version.value,
        certification_id=card.certification_id,
        certification_status=card.certification_status,
        trust_level=card.trust_level,
        can_delegate=card.can_delegate,
        can_accept_delegation=card.can_accept_delegation,
        tags=card.tags,
    )


@router.post("/agents/{agent_id}/register")
async def register_agent_for_discovery(
    agent_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Register an agent for A2A discovery.

    This makes the agent discoverable by other agents.
    """
    # Verify agent belongs to tenant
    agent = get_or_404(
        db.query(models.Agent).filter(
            and_(
                models.Agent.id == agent_id,
                models.Agent.tenant_id == current_user.tenant_id,
            )
        ).first(),
        "Agent",
        agent_id
    )

    # Get certification info
    cert_registry = get_certification_registry()
    cert = cert_registry.get_current_certification(agent_id)

    # Create agent card
    card = create_agent_card(
        agent_id=agent_id,
        name=agent.name,
        description=agent.description or "",
        tenant_id=agent.tenant_id,
        base_url="",  # Configured per deployment
        agent_type=agent.agent_type,
        certification_id=cert.id if cert else None,
        trust_level=int(cert.overall_score * 100) if cert else 0,
    )

    # Register for discovery
    discovery = get_agent_discovery()
    discovery.register(card)

    return {"status": "registered", "agent_id": str(agent_id)}


@router.delete("/agents/{agent_id}/register")
async def unregister_agent_from_discovery(
    agent_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Unregister an agent from A2A discovery."""
    # Verify agent belongs to tenant
    get_or_404(
        db.query(models.Agent).filter(
            and_(
                models.Agent.id == agent_id,
                models.Agent.tenant_id == current_user.tenant_id,
            )
        ).first(),
        "Agent",
        agent_id
    )

    discovery = get_agent_discovery()
    discovery.unregister(str(agent_id))

    return {"status": "unregistered", "agent_id": str(agent_id)}


# =============================================================================
# Discovery Endpoints
# =============================================================================

@router.post("/discover", response_model=DiscoveryResponse)
async def discover_agents(
    request: DiscoveryRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Discover agents matching criteria.

    Search for agents by capabilities, tags, type, etc.
    """
    discovery = get_agent_discovery()

    filter = DiscoveryFilter(
        tenant_id=current_user.tenant_id,
        capability_ids=request.capability_ids,
        capability_tags=request.capability_tags,
        agent_types=request.agent_types,
        roles=request.roles,
        min_trust_level=request.min_trust_level,
        require_certified=request.require_certified,
        can_accept_delegation=request.can_accept_delegation,
        limit=request.limit,
        offset=request.offset,
    )

    result = discovery.discover(filter)

    return DiscoveryResponse(
        agents=[
            AgentCardResponse(
                id=card.id,
                name=card.name,
                description=card.description,
                version=card.version,
                agent_type=card.agent_type,
                role=card.role,
                endpoints=[ep.to_dict() for ep in card.endpoints],
                capabilities=[cap.to_dict() for cap in card.capabilities],
                protocol_version=card.protocol_version.value,
                certification_id=card.certification_id,
                certification_status=card.certification_status,
                trust_level=card.trust_level,
                can_delegate=card.can_delegate,
                can_accept_delegation=card.can_accept_delegation,
                tags=card.tags,
            )
            for card in result.agents
        ],
        total=result.total,
        has_more=result.has_more,
        query_time_ms=result.query_time_ms,
    )


@router.get("/discover/by-capability/{capability_id}", response_model=List[AgentCardResponse])
async def discover_by_capability(
    capability_id: str,
    min_trust: int = Query(0, ge=0, le=100),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Find agents with a specific capability."""
    discovery = get_agent_discovery()
    cards = discovery.find_by_capability(
        capability_id=capability_id,
        tenant_id=current_user.tenant_id,
        min_trust=min_trust,
    )

    return [
        AgentCardResponse(
            id=card.id,
            name=card.name,
            description=card.description,
            version=card.version,
            agent_type=card.agent_type,
            role=card.role,
            endpoints=[ep.to_dict() for ep in card.endpoints],
            capabilities=[cap.to_dict() for cap in card.capabilities],
            protocol_version=card.protocol_version.value,
            certification_id=card.certification_id,
            certification_status=card.certification_status,
            trust_level=card.trust_level,
            can_delegate=card.can_delegate,
            can_accept_delegation=card.can_accept_delegation,
            tags=card.tags,
        )
        for card in cards
    ]


@router.get("/discover/by-tag/{tag}", response_model=List[AgentCardResponse])
async def discover_by_tag(
    tag: str,
    min_trust: int = Query(0, ge=0, le=100),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Find agents with capabilities matching a tag."""
    discovery = get_agent_discovery()
    cards = discovery.find_by_tag(
        tag=tag,
        tenant_id=current_user.tenant_id,
        min_trust=min_trust,
    )

    return [
        AgentCardResponse(
            id=card.id,
            name=card.name,
            description=card.description,
            version=card.version,
            agent_type=card.agent_type,
            role=card.role,
            endpoints=[ep.to_dict() for ep in card.endpoints],
            capabilities=[cap.to_dict() for cap in card.capabilities],
            protocol_version=card.protocol_version.value,
            certification_id=card.certification_id,
            certification_status=card.certification_status,
            trust_level=card.trust_level,
            can_delegate=card.can_delegate,
            can_accept_delegation=card.can_accept_delegation,
            tags=card.tags,
        )
        for card in cards
    ]


# =============================================================================
# Delegation Endpoints
# =============================================================================

@router.post("/agents/{agent_id}/delegate", response_model=DelegationResponse)
async def create_delegation(
    agent_id: UUID,
    request: DelegationCreateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Delegate a task from one agent to another.

    The delegator agent must belong to the current user's tenant.
    """
    # Verify delegator agent belongs to tenant
    get_or_404(
        db.query(models.Agent).filter(
            and_(
                models.Agent.id == agent_id,
                models.Agent.tenant_id == current_user.tenant_id,
            )
        ).first(),
        "Agent",
        agent_id
    )

    # Create delegation
    delegation = get_delegation_manager()

    try:
        from app.agentic.a2a.delegation import DelegationContext

        context = None
        if request.context:
            context = DelegationContext(
                original_input=request.task_input,
                original_context=request.context,
            )

        delegation_request = await delegation.delegate(
            delegator_id=str(agent_id),
            task_input=request.task_input,
            capability_id=request.capability_id,
            delegatee_id=request.delegatee_id,
            context=context,
            delegation_type=request.delegation_type,
            priority=request.priority,
            timeout_seconds=request.timeout_seconds,
        )

        return DelegationResponse(
            id=delegation_request.id,
            delegator_id=delegation_request.delegator_id,
            delegatee_id=delegation_request.delegatee_id,
            task_input=delegation_request.task_input,
            capability_id=delegation_request.capability_id,
            delegation_type=delegation_request.delegation_type.value,
            priority=delegation_request.priority,
            status=delegation_request.status.value,
            status_message=delegation_request.status_message,
            created_at=delegation_request.created_at,
            accepted_at=delegation_request.accepted_at,
            completed_at=delegation_request.completed_at,
            result=delegation_request.result,
            error=delegation_request.error,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/delegations/{delegation_id}", response_model=DelegationResponse)
async def get_delegation(
    delegation_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get a delegation by ID."""
    delegation = get_delegation_manager()
    request = get_or_404(
        delegation.get_delegation(delegation_id),
        "Delegation",
        delegation_id
    )

    return DelegationResponse(
        id=request.id,
        delegator_id=request.delegator_id,
        delegatee_id=request.delegatee_id,
        task_input=request.task_input,
        capability_id=request.capability_id,
        delegation_type=request.delegation_type.value,
        priority=request.priority,
        status=request.status.value,
        status_message=request.status_message,
        created_at=request.created_at,
        accepted_at=request.accepted_at,
        completed_at=request.completed_at,
        result=request.result,
        error=request.error,
    )


@router.post("/delegations/{delegation_id}/cancel", response_model=DelegationResponse)
async def cancel_delegation(
    delegation_id: str,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Cancel a delegation."""
    delegation = get_delegation_manager()

    try:
        request = await delegation.cancel_delegation(delegation_id, reason)

        return DelegationResponse(
            id=request.id,
            delegator_id=request.delegator_id,
            delegatee_id=request.delegatee_id,
            task_input=request.task_input,
            capability_id=request.capability_id,
            delegation_type=request.delegation_type.value,
            priority=request.priority,
            status=request.status.value,
            status_message=request.status_message,
            created_at=request.created_at,
            accepted_at=request.accepted_at,
            completed_at=request.completed_at,
            result=request.result,
            error=request.error,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/agents/{agent_id}/delegations/sent", response_model=List[DelegationResponse])
async def get_sent_delegations(
    agent_id: UUID,
    status_filter: Optional[DelegationStatus] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get delegations sent by an agent."""
    delegation = get_delegation_manager()
    requests = delegation.get_delegator_requests(str(agent_id), status_filter)

    return [
        DelegationResponse(
            id=r.id,
            delegator_id=r.delegator_id,
            delegatee_id=r.delegatee_id,
            task_input=r.task_input,
            capability_id=r.capability_id,
            delegation_type=r.delegation_type.value,
            priority=r.priority,
            status=r.status.value,
            status_message=r.status_message,
            created_at=r.created_at,
            accepted_at=r.accepted_at,
            completed_at=r.completed_at,
            result=r.result,
            error=r.error,
        )
        for r in requests
    ]


@router.get("/agents/{agent_id}/delegations/received", response_model=List[DelegationResponse])
async def get_received_delegations(
    agent_id: UUID,
    status_filter: Optional[DelegationStatus] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get delegations received by an agent."""
    delegation = get_delegation_manager()
    requests = delegation.get_delegatee_requests(str(agent_id), status_filter)

    return [
        DelegationResponse(
            id=r.id,
            delegator_id=r.delegator_id,
            delegatee_id=r.delegatee_id,
            task_input=r.task_input,
            capability_id=r.capability_id,
            delegation_type=r.delegation_type.value,
            priority=r.priority,
            status=r.status.value,
            status_message=r.status_message,
            created_at=r.created_at,
            accepted_at=r.accepted_at,
            completed_at=r.completed_at,
            result=r.result,
            error=r.error,
        )
        for r in requests
    ]


# =============================================================================
# Statistics Endpoints
# =============================================================================

@router.get("/stats/discovery")
async def get_discovery_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get discovery service statistics."""
    discovery = get_agent_discovery()
    return discovery.get_statistics(tenant_id=current_user.tenant_id)


@router.get("/stats/delegations")
async def get_delegation_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get delegation statistics."""
    delegation = get_delegation_manager()
    return delegation.get_statistics()
