"""
Simple NLP Gateway endpoints integrated into main AutonomOS API.
Provides natural language interface without requiring a separate service.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid

router = APIRouter(prefix="/nlp/v1", tags=["NLP Gateway"])


class KBSearchRequest(BaseModel):
    tenant_id: str = "demo-tenant"
    env: str = "prod"
    query: str
    top_k: int = 5


class KBMatch(BaseModel):
    title: str
    content: str
    score: float
    section: str


class KBSearchResponse(BaseModel):
    matches: List[KBMatch]
    trace_id: str
    timestamp: str


class FinOpsRequest(BaseModel):
    tenant_id: str = "demo-tenant"
    env: str = "prod"
    from_: str = Field(alias="from", default="2025-11-01")
    to: str = "2025-11-10"


class RevOpsRequest(BaseModel):
    tenant_id: str = "demo-tenant"
    env: str = "prod"
    incident_id: str


class AODRequest(BaseModel):
    tenant_id: str = "demo-tenant"
    env: str = "prod"
    service: str


class AAMRequest(BaseModel):
    tenant_id: str = "demo-tenant"
    env: str = "prod"
    status: str = "All"


@router.post("/kb/search", response_model=KBSearchResponse)
async def kb_search(request: KBSearchRequest):
    """Search knowledge base using hybrid RAG."""
    trace_id = f"nlp_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{str(uuid.uuid4())[:8]}"
    
    # Demo responses based on query keywords
    demo_matches = []
    
    if "aam" in request.query.lower() or "connector" in request.query.lower():
        demo_matches = [
            KBMatch(
                title="AAM Hybrid Retrieval Guide",
                content="The Adaptive API Mesh (AAM) uses hybrid search combining BM25 keyword matching and vector embeddings. This enables both exact phrase matching and semantic similarity.",
                score=0.947,
                section="Technical Details"
            ),
            KBMatch(
                title="Connector Configuration Guide",
                content="AAM connectors support Salesforce, MongoDB, Supabase, and FileSource. Each connector implements schema fingerprinting for drift detection.",
                score=0.823,
                section="Setup"
            )
        ]
    elif "cost" in request.query.lower() or "finops" in request.query.lower():
        demo_matches = [
            KBMatch(
                title="FinOps Best Practices",
                content="Cost optimization starts with visibility. Tag all resources, set budgets, and review spend weekly. Focus on rightsizing before scaling.",
                score=0.912,
                section="Optimization"
            )
        ]
    else:
        demo_matches = [
            KBMatch(
                title="Platform Architecture Overview",
                content="AutonomOS provides AI-driven data orchestration with multi-tenant isolation, JWT authentication, and real-time event streaming.",
                score=0.785,
                section="Introduction"
            )
        ]
    
    return KBSearchResponse(
        matches=demo_matches[:request.top_k],
        trace_id=trace_id,
        timestamp=datetime.utcnow().isoformat()
    )


@router.post("/finops/summary")
async def finops_summary(request: FinOpsRequest):
    """Get FinOps cost summary."""
    trace_id = f"nlp_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{str(uuid.uuid4())[:8]}"
    
    return {
        "summary": {
            "total_cost": "$45,230",
            "vs_last_month": "+12%",
            "top_services": [
                {"name": "EC2", "cost": "$18,500"},
                {"name": "RDS", "cost": "$12,300"},
                {"name": "S3", "cost": "$8,200"}
            ],
            "savings_opportunities": "$5,400/month"
        },
        "trace_id": trace_id,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/revops/incident")
async def revops_incident(request: RevOpsRequest):
    """Get RevOps incident details."""
    trace_id = f"nlp_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{str(uuid.uuid4())[:8]}"
    
    return {
        "incident": {
            "incident_id": request.incident_id,
            "title": "Salesforce sync failure",
            "status": "Resolved",
            "root_cause": "API rate limit exceeded",
            "resolution": "Implemented exponential backoff retry logic",
            "impact": "15 minutes data sync delay"
        },
        "trace_id": trace_id,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/aod/dependencies")
async def aod_dependencies(request: AODRequest):
    """Get service dependency mapping."""
    trace_id = f"nlp_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{str(uuid.uuid4())[:8]}"
    
    return {
        "service": request.service,
        "dependencies": {
            "upstream": ["payment-gateway", "inventory-service"],
            "downstream": ["order-processor", "shipping-service"]
        },
        "health": "healthy",
        "trace_id": trace_id,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/aam/connectors")
async def aam_connectors(request: AAMRequest):
    """List AAM connectors with health status."""
    trace_id = f"nlp_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{str(uuid.uuid4())[:8]}"
    
    all_connectors = [
        {"name": "Salesforce", "status": "Healthy", "last_sync": "5 min ago"},
        {"name": "MongoDB", "status": "Healthy", "last_sync": "3 min ago"},
        {"name": "Supabase", "status": "Drifted", "last_sync": "12 min ago"},
        {"name": "FileSource", "status": "Healthy", "last_sync": "1 min ago"}
    ]
    
    if request.status != "All":
        all_connectors = [c for c in all_connectors if c["status"] == request.status]
    
    return {
        "connectors": all_connectors,
        "total": len(all_connectors),
        "trace_id": trace_id,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/health")
async def nlp_health():
    """NLP Gateway health check."""
    return {
        "status": "healthy",
        "service": "nlp-gateway",
        "version": "1.0.0"
    }
