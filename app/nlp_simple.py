"""
Simple NLP Gateway endpoints integrated into main AutonomOS API.
Provides natural language interface without requiring a separate service.
"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime
import uuid
import os

router = APIRouter(prefix="/nlp/v1", tags=["NLP Gateway"])

PersonaSlug = Literal["cto", "cro", "coo", "cfo"]

# Demo mode flag - when True, fills empty values with deterministic mock data
DEMO_MODE = os.getenv("AOS_DEMO_MODE", "false").lower() == "true"


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


class PersonaClassifyRequest(BaseModel):
    query: str
    tenant_id: str = "demo-tenant"


class PersonaClassifyResponse(BaseModel):
    persona: PersonaSlug
    confidence: float
    matched_keywords: List[str]
    trace_id: str


class PersonaTile(BaseModel):
    key: str
    title: str
    value: Optional[str]
    delta: Optional[str]
    timeframe: str
    last_updated: Optional[str]
    href: str
    note: Optional[str] = None
    mock: Optional[bool] = None


class PersonaTable(BaseModel):
    title: str
    columns: List[str]
    rows: List[List[str]]
    href: str
    note: Optional[str] = None
    mock: Optional[bool] = None


class PersonaSummaryResponse(BaseModel):
    persona: PersonaSlug
    tiles: List[PersonaTile]
    table: PersonaTable
    trace_id: str


@router.post("/persona/classify", response_model=PersonaClassifyResponse)
async def classify_persona(request: PersonaClassifyRequest):
    """Classify a query into a persona (CTO, CRO, COO, CFO)."""
    trace_id = f"nlp_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{str(uuid.uuid4())[:8]}"
    
    query_lower = request.query.lower()
    
    coo_keywords = ["spend", "budget", "vendor", "renewal", "finops", "cost", "cloud"]
    cfo_keywords = ["revenue", "ebitda", "cash", "burn", "runway", "margin"]
    cro_keywords = ["pipeline", "win rate", "quota", "sales", "deal"]
    cto_keywords = ["connector", "drift", "schema", "api", "service", "incident"]
    
    scores = {
        "coo": sum(1 for kw in coo_keywords if kw in query_lower),
        "cfo": sum(1 for kw in cfo_keywords if kw in query_lower),
        "cro": sum(1 for kw in cro_keywords if kw in query_lower),
        "cto": sum(1 for kw in cto_keywords if kw in query_lower),
    }
    
    persona = max(scores, key=scores.get)  # type: ignore
    matched = [kw for kw in (coo_keywords + cfo_keywords + cro_keywords + cto_keywords) if kw in query_lower]
    confidence = min(0.95, 0.6 + (scores[persona] * 0.1))
    
    return PersonaClassifyResponse(
        persona=persona,  # type: ignore
        confidence=confidence,
        matched_keywords=matched[:5],
        trace_id=trace_id
    )


@router.get("/persona/summary", response_model=PersonaSummaryResponse)
async def get_persona_summary(persona: PersonaSlug = Query(..., description="Persona type")):
    """Get persona-specific dashboard summary."""
    trace_id = f"nlp_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{str(uuid.uuid4())[:8]}"
    now_iso = datetime.utcnow().isoformat() + "Z"
    
    # TODO: Try fetching real data from live endpoints
    # For now, we'll use DEMO_MODE to determine stub vs demo data
    
    if persona == "coo":
        if DEMO_MODE:
            return PersonaSummaryResponse(
                persona="coo",
                tiles=[
                    PersonaTile(key="cloud_spend", title="Cloud Spend (MTD)", value="$184k", delta=None, timeframe="MTD vs Budget", last_updated=now_iso, href="/finops", mock=True),
                    PersonaTile(key="variance_mtd", title="Variance", value="+6.2%", delta="+6.2%", timeframe="MTD", last_updated=now_iso, href="/finops", mock=True),
                    PersonaTile(key="vendors_over_threshold", title="Vendors > $50k", value="7", delta=None, timeframe="Rolling 30d", last_updated=now_iso, href="/finops/vendors", mock=True),
                    PersonaTile(key="renewals_30d", title="Renewals (30d)", value="4", delta=None, timeframe="Next 30d", last_updated=now_iso, href="/finops/renewals", mock=True),
                ],
                table=PersonaTable(
                    title="Top 10 Cost Centers (MTD)",
                    columns=["Cost Center", "MTD Spend", "Δ vs prior period"],
                    rows=[
                        ["Engineering", "$68k", "+8.2%"],
                        ["Data Platform", "$42k", "+3.1%"],
                        ["GTM", "$31k", "+12.5%"],
                        ["Support", "$18k", "-2.3%"],
                        ["Security", "$12k", "+5.7%"],
                        ["Finance", "$7k", "+1.2%"],
                        ["Legal", "$4k", "-0.8%"],
                        ["HR", "$2k", "+0.5%"],
                    ],
                    href="/finops/cost-centers",
                    mock=True
                ),
                trace_id=trace_id
            )
        else:
            return PersonaSummaryResponse(
                persona="coo",
                tiles=[
                    PersonaTile(key="cloud_spend", title="Cloud Spend (MTD)", value=None, delta=None, timeframe="MTD vs Budget", last_updated=None, href="/finops", note="stub"),
                    PersonaTile(key="variance_mtd", title="Variance", value=None, delta=None, timeframe="MTD", last_updated=None, href="/finops", note="stub"),
                    PersonaTile(key="vendors_over_threshold", title="Vendors > $50k", value=None, delta=None, timeframe="Rolling 30d", last_updated=None, href="/finops/vendors", note="stub"),
                    PersonaTile(key="renewals_30d", title="Renewals (30d)", value=None, delta=None, timeframe="Next 30d", last_updated=None, href="/finops/renewals", note="stub"),
                ],
                table=PersonaTable(title="Top 10 Cost Centers (MTD)", columns=["Cost Center", "MTD Spend", "Δ vs prior period"], rows=[], href="/finops/cost-centers", note="stub"),
                trace_id=trace_id
            )
    elif persona == "cfo":
        if DEMO_MODE:
            return PersonaSummaryResponse(
                persona="cfo",
                tiles=[
                    PersonaTile(key="revenue_mtd", title="Revenue (MTD)", value="$2.4M", delta=None, timeframe="MTD/QTD/YTD", last_updated=now_iso, href="#", mock=True),
                    PersonaTile(key="gross_margin_pct", title="Gross Margin %", value="62%", delta=None, timeframe="MTD", last_updated=now_iso, href="#", mock=True),
                    PersonaTile(key="cash_balance", title="Cash Balance", value="$18.3M", delta=None, timeframe="Today", last_updated=now_iso, href="#", mock=True),
                    PersonaTile(key="burn_rate", title="Burn Rate", value="-$0.9M/mo", delta=None, timeframe="Rolling 30d", last_updated=now_iso, href="#", mock=True),
                    PersonaTile(key="runway_months", title="Runway (mo)", value="20", delta=None, timeframe="Projected", last_updated=now_iso, href="#", mock=True),
                    PersonaTile(key="dso_dpo", title="DSO / DPO", value="44 / 36", delta=None, timeframe="Rolling 90d", last_updated=now_iso, href="#", mock=True),
                ],
                table=PersonaTable(
                    title="Finance KPIs by Month",
                    columns=["Month", "Revenue", "GM%", "Burn", "Cash End"],
                    rows=[
                        ["Nov 2025", "$2.4M", "62%", "-$0.9M", "$18.3M"],
                        ["Oct 2025", "$2.3M", "61%", "-$0.9M", "$19.2M"],
                        ["Sep 2025", "$2.2M", "60%", "-$0.8M", "$20.1M"],
                        ["Aug 2025", "$2.1M", "59%", "-$0.8M", "$20.9M"],
                        ["Jul 2025", "$2.0M", "58%", "-$0.7M", "$21.7M"],
                        ["Jun 2025", "$1.9M", "57%", "-$0.7M", "$22.4M"],
                    ],
                    href="#",
                    mock=True
                ),
                trace_id=trace_id
            )
        else:
            return PersonaSummaryResponse(
                persona="cfo",
                tiles=[
                    PersonaTile(key="revenue_mtd", title="Revenue (MTD)", value=None, delta=None, timeframe="MTD/QTD/YTD", last_updated=None, href="#", note="stub"),
                    PersonaTile(key="gross_margin_pct", title="Gross Margin %", value=None, delta=None, timeframe="MTD", last_updated=None, href="#", note="stub"),
                    PersonaTile(key="cash_balance", title="Cash Balance", value=None, delta=None, timeframe="Today", last_updated=None, href="#", note="stub"),
                    PersonaTile(key="burn_rate", title="Burn Rate", value=None, delta=None, timeframe="Rolling 30d", last_updated=None, href="#", note="stub"),
                    PersonaTile(key="runway_months", title="Runway (mo)", value=None, delta=None, timeframe="Projected", last_updated=None, href="#", note="stub"),
                    PersonaTile(key="dso_dpo", title="DSO / DPO", value=None, delta=None, timeframe="Rolling 90d", last_updated=None, href="#", note="stub"),
                ],
                table=PersonaTable(title="Finance KPIs by Month", columns=["Month", "Revenue", "GM%", "Burn", "Cash End"], rows=[], href="#", note="stub"),
                trace_id=trace_id
            )
    elif persona == "cro":
        if DEMO_MODE:
            return PersonaSummaryResponse(
                persona="cro",
                tiles=[
                    PersonaTile(key="pipeline_value", title="Pipeline Value", value="$12.4M", delta=None, timeframe="Current Quarter", last_updated=now_iso, href="#", mock=True),
                    PersonaTile(key="forecast_commit", title="Forecast (Commit)", value="$10.8M", delta=None, timeframe="Current Quarter", last_updated=now_iso, href="#", mock=True),
                    PersonaTile(key="win_rate", title="Win Rate", value="27%", delta=None, timeframe="Last 90 days", last_updated=now_iso, href="#", mock=True),
                    PersonaTile(key="new_opps_7d", title="New Opps (7d)", value="23", delta=None, timeframe="Last 7 days", last_updated=now_iso, href="#", mock=True),
                ],
                table=PersonaTable(
                    title="Top Opportunities",
                    columns=["Opportunity", "Value", "Stage", "Close Date"],
                    rows=[
                        ["Acme Corp - Enterprise", "$850k", "Negotiation", "2025-12-15"],
                        ["TechStart Inc", "$420k", "Proposal", "2025-12-01"],
                        ["Global Systems", "$380k", "Discovery", "2026-01-10"],
                        ["DataFlow Solutions", "$290k", "Negotiation", "2025-11-30"],
                        ["CloudNine Services", "$210k", "Qualification", "2026-01-15"],
                    ],
                    href="#",
                    mock=True
                ),
                trace_id=trace_id
            )
        else:
            return PersonaSummaryResponse(
                persona="cro",
                tiles=[
                    PersonaTile(key="pipeline_value", title="Pipeline Value", value=None, delta=None, timeframe="Current Quarter", last_updated=None, href="#", note="stub"),
                    PersonaTile(key="win_rate", title="Win Rate", value=None, delta=None, timeframe="Last 90 days", last_updated=None, href="#", note="stub"),
                    PersonaTile(key="quota_attainment", title="Quota Attainment", value=None, delta=None, timeframe="MTD", last_updated=None, href="#", note="stub"),
                ],
                table=PersonaTable(title="Top Opportunities", columns=["Opportunity", "Value", "Stage", "Close Date"], rows=[], href="#", note="stub"),
                trace_id=trace_id
            )
    else:  # cto
        if DEMO_MODE:
            return PersonaSummaryResponse(
                persona="cto",
                tiles=[
                    PersonaTile(key="connectors_healthy", title="Connectors Healthy", value="97", delta=None, timeframe="Last 24h", last_updated=now_iso, href="#", mock=True),
                    PersonaTile(key="drift_open", title="Drift Events (Open)", value="3", delta=None, timeframe="Current", last_updated=now_iso, href="#", mock=True),
                    PersonaTile(key="discovery_apps", title="Apps Discovered", value="312", delta=None, timeframe="Total", last_updated=now_iso, href="#", mock=True),
                    PersonaTile(key="agents_running", title="Agents Running", value="14", delta=None, timeframe="Current", last_updated=now_iso, href="#", mock=True),
                ],
                table=PersonaTable(
                    title="Connector Drift Events",
                    columns=["Connector", "Drift %", "Last Check"],
                    rows=[
                        ["Salesforce", "2.1%", "2025-11-10T18:22Z"],
                        ["NetSuite", "1.6%", "2025-11-10T17:45Z"],
                        ["Zendesk", "1.3%", "2025-11-10T16:12Z"],
                    ],
                    href="#",
                    mock=True
                ),
                trace_id=trace_id
            )
        else:
            return PersonaSummaryResponse(
                persona="cto",
                tiles=[
                    PersonaTile(key="services_healthy", title="Services Healthy", value=None, delta=None, timeframe="Last 24h", last_updated=None, href="#", note="stub"),
                    PersonaTile(key="connectors_drifted", title="Connectors Drifted", value=None, delta=None, timeframe="Current", last_updated=None, href="#", note="stub"),
                    PersonaTile(key="incidents_open", title="Open Incidents", value=None, delta=None, timeframe="Current", last_updated=None, href="#", note="stub"),
                ],
                table=PersonaTable(title="Service Health", columns=["Service", "Status", "Latency", "Error Rate"], rows=[], href="#", note="stub"),
                trace_id=trace_id
            )
