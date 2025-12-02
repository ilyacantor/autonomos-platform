"""
DCL v2 Bridge Module

Clean API boundary for integrating with the external DCL v2 service.
Provides demo endpoints with stub fallback when DCL v2 is not configured.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import httpx

from app.security import get_current_user
from app.models import User

logger = logging.getLogger(__name__)

router = APIRouter()

DCL_V2_BASE_URL = os.getenv("DCL_V2_BASE_URL")


class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    metadata: Optional[Dict[str, Any]] = None


class GraphEdge(BaseModel):
    source: str
    target: str
    relationship: str


class GraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    summary: Dict[str, Any]
    source: str


class QueryRequest(BaseModel):
    question: str
    persona: Optional[str] = "general"


class QueryResponse(BaseModel):
    question: str
    persona: str
    intent: str
    answer: str
    confidence: float
    entities_referenced: List[str]
    source: str


def get_stub_graph() -> GraphResponse:
    """Return a realistic stub graph for demo purposes"""
    nodes = [
        GraphNode(id="salesforce", label="Salesforce CRM", type="source", metadata={"category": "CRM", "records": 45000}),
        GraphNode(id="stripe", label="Stripe Payments", type="source", metadata={"category": "Payments", "records": 12000}),
        GraphNode(id="netsuite", label="NetSuite ERP", type="source", metadata={"category": "ERP", "records": 8500}),
        GraphNode(id="snowflake", label="Snowflake DW", type="source", metadata={"category": "Warehouse", "records": 2500000}),
        GraphNode(id="account", label="Account", type="ontology", metadata={"entity_type": "canonical", "unified_count": 3200}),
        GraphNode(id="opportunity", label="Opportunity", type="ontology", metadata={"entity_type": "canonical", "unified_count": 8500}),
        GraphNode(id="revenue", label="Revenue", type="ontology", metadata={"entity_type": "canonical", "unified_count": 15000}),
        GraphNode(id="cost", label="Cost", type="ontology", metadata={"entity_type": "canonical", "unified_count": 22000}),
        GraphNode(id="usage", label="Usage", type="ontology", metadata={"entity_type": "canonical", "unified_count": 180000}),
        GraphNode(id="finops_agent", label="FinOps Agent", type="agent", metadata={"persona": "CFO", "active": True}),
        GraphNode(id="revops_agent", label="RevOps Agent", type="agent", metadata={"persona": "CRO", "active": True}),
    ]
    
    edges = [
        GraphEdge(source="salesforce", target="account", relationship="provides"),
        GraphEdge(source="salesforce", target="opportunity", relationship="provides"),
        GraphEdge(source="stripe", target="revenue", relationship="provides"),
        GraphEdge(source="netsuite", target="cost", relationship="provides"),
        GraphEdge(source="netsuite", target="revenue", relationship="provides"),
        GraphEdge(source="snowflake", target="usage", relationship="provides"),
        GraphEdge(source="account", target="finops_agent", relationship="feeds"),
        GraphEdge(source="revenue", target="finops_agent", relationship="feeds"),
        GraphEdge(source="cost", target="finops_agent", relationship="feeds"),
        GraphEdge(source="account", target="revops_agent", relationship="feeds"),
        GraphEdge(source="opportunity", target="revops_agent", relationship="feeds"),
        GraphEdge(source="revenue", target="revops_agent", relationship="feeds"),
    ]
    
    summary = {
        "total_sources": 4,
        "total_entities": 5,
        "total_agents": 2,
        "records_unified": 228700,
        "confidence_score": 0.94,
        "last_sync": "2025-12-02T10:30:00Z"
    }
    
    return GraphResponse(nodes=nodes, edges=edges, summary=summary, source="stub")


def get_stub_query_response(question: str, persona: str) -> QueryResponse:
    """Return a realistic stub query response for demo purposes"""
    persona_responses = {
        "CFO": {
            "intent": "financial_analysis",
            "answer": "Based on current data, your MRR is $2.4M with a 15% month-over-month growth. Cost efficiency has improved by 8% due to infrastructure optimization. 3 accounts representing $180K ARR show elevated churn risk based on declining usage patterns.",
            "entities_referenced": ["revenue", "cost", "account", "usage"],
            "confidence": 0.92
        },
        "CRO": {
            "intent": "pipeline_analysis",
            "answer": "Your pipeline shows 47 opportunities worth $3.2M in total value. Win rate has improved to 28% this quarter. Top 10 accounts by expansion potential have been identified with $850K in upsell opportunity.",
            "entities_referenced": ["opportunity", "account", "revenue"],
            "confidence": 0.89
        },
        "general": {
            "intent": "general_query",
            "answer": "AutonomOS has unified 228,700 records across 4 data sources into 5 canonical entities. The system maintains a 94% confidence score on entity mappings. 2 AI agents are actively processing this data to generate insights.",
            "entities_referenced": ["account", "opportunity", "revenue", "cost", "usage"],
            "confidence": 0.95
        }
    }
    
    response_data = persona_responses.get(persona, persona_responses["general"])
    
    return QueryResponse(
        question=question,
        persona=persona,
        intent=response_data["intent"],
        answer=response_data["answer"],
        confidence=response_data["confidence"],
        entities_referenced=response_data["entities_referenced"],
        source="stub"
    )


@router.get(
    "/demo/dcl/graph",
    response_model=GraphResponse,
    summary="Get DCL canonical graph",
    description="Returns the current DCL graph showing sources, canonical entities, and agent connections"
)
async def get_dcl_graph(
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Get the DCL canonical graph for visualization.
    
    If DCL_V2_BASE_URL is configured, proxies to the external DCL v2 service.
    Otherwise, returns a realistic stub graph for demo purposes.
    """
    if DCL_V2_BASE_URL:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{DCL_V2_BASE_URL}/demo/graph")
                response.raise_for_status()
                data = response.json()
                return GraphResponse(
                    nodes=[GraphNode(**n) for n in data.get("nodes", [])],
                    edges=[GraphEdge(**e) for e in data.get("edges", [])],
                    summary=data.get("summary", {}),
                    source="dcl_v2"
                )
        except httpx.TimeoutException:
            logger.warning("DCL v2 request timed out, falling back to stub")
        except httpx.HTTPError as e:
            logger.warning(f"DCL v2 request failed: {e}, falling back to stub")
        except Exception as e:
            logger.error(f"Unexpected error calling DCL v2: {e}")
    
    return get_stub_graph()


@router.post(
    "/demo/dcl/query",
    response_model=QueryResponse,
    summary="Query DCL with natural language",
    description="Ask questions about your unified data using natural language"
)
async def query_dcl(
    request: QueryRequest,
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Query DCL with natural language.
    
    If DCL_V2_BASE_URL is configured, proxies to the external DCL v2 service.
    Otherwise, returns a realistic stub response for demo purposes.
    """
    if DCL_V2_BASE_URL:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{DCL_V2_BASE_URL}/demo/query",
                    json={"question": request.question, "persona": request.persona}
                )
                response.raise_for_status()
                data = response.json()
                return QueryResponse(
                    question=request.question,
                    persona=request.persona or "general",
                    intent=data.get("intent", "unknown"),
                    answer=data.get("answer", ""),
                    confidence=data.get("confidence", 0.0),
                    entities_referenced=data.get("entities_referenced", []),
                    source="dcl_v2"
                )
        except httpx.TimeoutException:
            logger.warning("DCL v2 query timed out, falling back to stub")
        except httpx.HTTPError as e:
            logger.warning(f"DCL v2 query failed: {e}, falling back to stub")
        except Exception as e:
            logger.error(f"Unexpected error querying DCL v2: {e}")
    
    return get_stub_query_response(request.question, request.persona or "general")


@router.get(
    "/demo/dcl/status",
    summary="Check DCL v2 connection status",
    description="Returns whether DCL v2 is configured and reachable"
)
async def get_dcl_status():
    """Check if DCL v2 is configured and reachable"""
    status = {
        "dcl_v2_configured": bool(DCL_V2_BASE_URL),
        "dcl_v2_url": DCL_V2_BASE_URL[:30] + "..." if DCL_V2_BASE_URL and len(DCL_V2_BASE_URL) > 30 else DCL_V2_BASE_URL,
        "using_stubs": not bool(DCL_V2_BASE_URL),
        "available_endpoints": [
            "GET /api/v1/demo/dcl/graph",
            "POST /api/v1/demo/dcl/query",
            "GET /api/v1/demo/dcl/status"
        ]
    }
    
    if DCL_V2_BASE_URL:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{DCL_V2_BASE_URL}/health")
                status["dcl_v2_reachable"] = response.status_code == 200
        except Exception:
            status["dcl_v2_reachable"] = False
    else:
        status["dcl_v2_reachable"] = None
    
    return status
