"""
Persona API endpoints for role-based dashboards and query routing.
"""
from fastapi import APIRouter, Request, Query
from typing import Literal

from ..schemas.persona import (
    PersonaClassifyRequest,
    PersonaClassifyResponse,
    PersonaSummaryResponse,
    PersonaTile,
    PersonaTable,
    PersonaType
)
from ..utils.persona_classifier import classify_persona
from ..utils.trace_id import get_trace_id

router = APIRouter(prefix="/v1/persona", tags=["persona"])


@router.post("/classify", response_model=PersonaClassifyResponse)
async def classify_query(request: Request, payload: PersonaClassifyRequest):
    """
    Classify a natural language query into a persona (CTO, CRO, COO, CFO).
    
    Uses keyword matching with tie-breaking rules:
    - COO: FinOps keywords (spend, budget, vendor, etc.)
    - CFO: Finance keywords (revenue, EBITDA, cash, etc.)
    - CRO: RevOps keywords (pipeline, win rate, etc.)
    - CTO: Technical keywords (connector, drift, API, etc.)
    """
    persona_str, confidence, matched_keywords = classify_persona(payload.query)
    
    return PersonaClassifyResponse(
        persona=persona_str,  # type: ignore
        confidence=confidence,
        matched_keywords=matched_keywords,
        trace_id=get_trace_id()
    )


@router.get("/summary", response_model=PersonaSummaryResponse)
async def get_persona_summary(
    request: Request,
    persona: PersonaType = Query(..., description="Persona type (cto, cro, coo, cfo)")
):
    """
    Get role-specific dashboard summary with KPIs and data tables.
    
    - COO: FinOps dashboard (cloud spend, vendors, renewals, cost centers)
    - CFO: Finance scoreboard (revenue, margins, cash, burn - currently stubbed)
    - CRO: RevOps dashboard (pipeline, deals, win rate - currently stubbed)
    - CTO: Technical dashboard (connectors, services, incidents - currently stubbed)
    """
    trace_id = get_trace_id()
    
    if persona == "coo":
        return _build_coo_summary(trace_id)
    elif persona == "cfo":
        return _build_cfo_summary(trace_id)
    elif persona == "cro":
        return _build_cro_summary(trace_id)
    else:  # cto
        return _build_cto_summary(trace_id)


def _build_coo_summary(trace_id: str) -> PersonaSummaryResponse:
    """Build COO FinOps dashboard (stubbed - will connect to FinOps endpoints)."""
    return PersonaSummaryResponse(
        persona="coo",
        tiles=[
            PersonaTile(
                key="cloud_spend",
                title="Cloud Spend (MTD)",
                value=None,
                delta=None,
                timeframe="MTD vs Budget",
                last_updated=None,
                href="/finops",
                note="stub"
            ),
            PersonaTile(
                key="variance_mtd",
                title="Variance",
                value=None,
                delta=None,
                timeframe="MTD",
                last_updated=None,
                href="/finops",
                note="stub"
            ),
            PersonaTile(
                key="vendors_over_threshold",
                title="Vendors > $50k",
                value=None,
                delta=None,
                timeframe="Rolling 30d",
                last_updated=None,
                href="/finops/vendors",
                note="stub"
            ),
            PersonaTile(
                key="renewals_30d",
                title="Renewals (30d)",
                value=None,
                delta=None,
                timeframe="Next 30d",
                last_updated=None,
                href="/finops/renewals",
                note="stub"
            ),
            PersonaTile(
                key="top_cost_centers",
                title="Top Cost Centers",
                value=None,
                delta=None,
                timeframe="MTD",
                last_updated=None,
                href="/finops/cost-centers",
                note="stub"
            )
        ],
        table=PersonaTable(
            title="Top 10 Cost Centers (MTD)",
            columns=["Cost Center", "MTD Spend", "Δ vs prior period"],
            rows=[],
            href="/finops/cost-centers",
            note="stub"
        ),
        trace_id=trace_id
    )


def _build_cfo_summary(trace_id: str) -> PersonaSummaryResponse:
    """Build CFO Finance scoreboard (stubbed)."""
    return PersonaSummaryResponse(
        persona="cfo",
        tiles=[
            PersonaTile(
                key="revenue_mtd",
                title="Revenue (MTD)",
                value=None,
                delta=None,
                timeframe="MTD/QTD/YTD",
                last_updated=None,
                href="#",
                note="stub"
            ),
            PersonaTile(
                key="gross_margin_pct",
                title="Gross Margin %",
                value=None,
                delta=None,
                timeframe="MTD",
                last_updated=None,
                href="#",
                note="stub"
            ),
            PersonaTile(
                key="cash_balance",
                title="Cash Balance",
                value=None,
                delta=None,
                timeframe="Today",
                last_updated=None,
                href="#",
                note="stub"
            ),
            PersonaTile(
                key="burn_rate",
                title="Burn Rate",
                value=None,
                delta=None,
                timeframe="Rolling 30d",
                last_updated=None,
                href="#",
                note="stub"
            ),
            PersonaTile(
                key="runway_months",
                title="Runway (mo)",
                value=None,
                delta=None,
                timeframe="Projected",
                last_updated=None,
                href="#",
                note="stub"
            ),
            PersonaTile(
                key="dso_dpo",
                title="DSO / DPO",
                value=None,
                delta=None,
                timeframe="Rolling 90d",
                last_updated=None,
                href="#",
                note="stub"
            )
        ],
        table=PersonaTable(
            title="Finance KPIs by Month",
            columns=["Month", "Revenue", "GM%", "Burn", "Cash End"],
            rows=[],
            href="#",
            note="stub"
        ),
        trace_id=trace_id
    )


def _build_cro_summary(trace_id: str) -> PersonaSummaryResponse:
    """Build CRO RevOps dashboard (stubbed)."""
    return PersonaSummaryResponse(
        persona="cro",
        tiles=[
            PersonaTile(
                key="pipeline_value",
                title="Pipeline Value",
                value=None,
                delta=None,
                timeframe="Current Quarter",
                last_updated=None,
                href="#",
                note="stub"
            ),
            PersonaTile(
                key="win_rate",
                title="Win Rate",
                value=None,
                delta=None,
                timeframe="Last 90 days",
                last_updated=None,
                href="#",
                note="stub"
            ),
            PersonaTile(
                key="quota_attainment",
                title="Quota Attainment",
                value=None,
                delta=None,
                timeframe="MTD",
                last_updated=None,
                href="#",
                note="stub"
            )
        ],
        table=PersonaTable(
            title="Top Opportunities",
            columns=["Opportunity", "Value", "Stage", "Close Date"],
            rows=[],
            href="#",
            note="stub"
        ),
        trace_id=trace_id
    )


def _build_cto_summary(trace_id: str) -> PersonaSummaryResponse:
    """Build CTO Technical dashboard (stubbed)."""
    return PersonaSummaryResponse(
        persona="cto",
        tiles=[
            PersonaTile(
                key="services_healthy",
                title="Services Healthy",
                value=None,
                delta=None,
                timeframe="Last 24h",
                last_updated=None,
                href="#",
                note="stub"
            ),
            PersonaTile(
                key="connectors_drifted",
                title="Connectors Drifted",
                value=None,
                delta=None,
                timeframe="Current",
                last_updated=None,
                href="#",
                note="stub"
            ),
            PersonaTile(
                key="incidents_open",
                title="Open Incidents",
                value=None,
                delta=None,
                timeframe="Current",
                last_updated=None,
                href="#",
                note="stub"
            )
        ],
        table=PersonaTable(
            title="Service Health",
            columns=["Service", "Status", "Latency", "Error Rate"],
            rows=[],
            href="#",
            note="stub"
        ),
        trace_id=trace_id
    )
