"""
Mock AOS Discover (AOD) Service Endpoint
This is a temporary mock for testing the E2E discovery flow until the actual AOD service is deployed.
"""

import logging
import uuid
from datetime import datetime
from fastapi import APIRouter, Body
from app.contracts.aod_contract import (
    DiscoveryRequest,
    DiscoveryResponse,
    DiscoveredEntity,
    AgentRecommendation,
    DiscoveryProvenance,
    ConfidenceLevel
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/discover", response_model=DiscoveryResponse)
async def mock_discover(request: DiscoveryRequest = Body(...)):
    """
    Mock AOS Discover service endpoint for testing E2E flow.
    
    This simulates the discovery logic until the actual AOD microservice is deployed.
    It generates realistic discovery results based on the NLP query.
    """
    logger.info(f"[MOCK AOD] Received discovery request: query='{request.nlp_query}' tenant={request.tenant_id}")
    
    # Simulate processing time
    processing_start = datetime.utcnow()
    
    # Generate mock discovered entities based on query keywords
    entities = []
    agent_recommendations = []
    
    # FinOps-related keywords
    if any(keyword in request.nlp_query.lower() for keyword in ['cost', 'spend', 'cloud', 'aws', 'finops', 'financial']):
        entities.append(DiscoveredEntity(
            entity_id="opp-finops-001",
            entity_type="opportunity",
            entity_name="Cloud Infrastructure Cost Optimization",
            source_system="salesforce",
            source_schema="Opportunity",
            confidence_score=0.94,
            confidence_level=ConfidenceLevel.HIGH,
            attributes={
                "amount": 250000.0,
                "stage": "Negotiation",
                "close_date": "2025-12-31",
                "category": "finops"
            },
            metadata={
                "discovery_reason": "Matched financial/cost keywords in query",
                "data_sources": ["salesforce", "filesource"]
            }
        ))
        
        agent_recommendations.append(AgentRecommendation(
            agent_name="finops_pilot",
            agent_type="finops",
            reason="Query contains financial/cost-related keywords indicating FinOps domain",
            confidence_score=0.92,
            suggested_actions=[
                "Analyze cloud spending trends",
                "Identify cost optimization opportunities",
                "Generate FinOps recommendations"
            ],
            priority="high"
        ))
    
    # RevOps-related keywords
    if any(keyword in request.nlp_query.lower() for keyword in ['revenue', 'sales', 'opportunity', 'account', 'revops', 'crm']):
        entities.append(DiscoveredEntity(
            entity_id="opp-revops-001",
            entity_type="opportunity",
            entity_name="Enterprise SaaS Deal",
            source_system="salesforce",
            source_schema="Opportunity",
            confidence_score=0.89,
            confidence_level=ConfidenceLevel.HIGH,
            attributes={
                "amount": 500000.0,
                "stage": "Proposal",
                "close_date": "2026-01-31",
                "category": "revops"
            },
            metadata={
                "discovery_reason": "Matched revenue/sales keywords in query",
                "data_sources": ["salesforce", "dynamics"]
            }
        ))
        
        agent_recommendations.append(AgentRecommendation(
            agent_name="revops_pilot",
            agent_type="revops",
            reason="Query contains revenue/sales-related keywords indicating RevOps domain",
            confidence_score=0.88,
            suggested_actions=[
                "Analyze opportunity pipeline",
                "Identify revenue trends",
                "Generate sales forecasts"
            ],
            priority="high"
        ))
    
    # If no specific keywords, provide generic results
    if not entities:
        entities.append(DiscoveredEntity(
            entity_id="gen-001",
            entity_type="generic",
            entity_name="General Entity Discovery",
            source_system="unknown",
            confidence_score=0.65,
            confidence_level=ConfidenceLevel.MEDIUM,
            attributes={"query": request.nlp_query},
            metadata={"discovery_reason": "Generic discovery - no specific domain matched"}
        ))
        
        agent_recommendations.append(AgentRecommendation(
            agent_name="general_agent",
            agent_type="general",
            reason="No specific domain identified from query",
            confidence_score=0.65,
            suggested_actions=["Review query and refine for better matching"],
            priority="medium"
        ))
    
    # Calculate processing time
    processing_end = datetime.utcnow()
    processing_time_ms = (processing_end - processing_start).total_seconds() * 1000
    
    # Build provenance
    provenance = DiscoveryProvenance(
        discovery_method="hybrid",
        llm_model="gemini-2.0-flash-exp",
        rag_sources=["domain_knowledge", "schema_catalog"],
        processing_time_ms=processing_time_ms,
        human_review_required=False
    )
    
    # Calculate overall confidence
    overall_confidence = sum(e.confidence_score for e in entities) / len(entities) if entities else 0.0
    
    # Build response
    response = DiscoveryResponse(
        success=True,
        request_id=str(uuid.uuid4()),
        entities=entities,
        agent_recommendations=agent_recommendations,
        provenance=provenance,
        total_entities_found=len(entities),
        filtered_count=len(entities),
        overall_confidence=overall_confidence,
        quality_issues=[],
        errors=[],
        warnings=[]
    )
    
    logger.info(
        f"[MOCK AOD] Returning discovery results: "
        f"entities={len(entities)} agents={len(agent_recommendations)} confidence={overall_confidence:.2f}"
    )
    
    return response
