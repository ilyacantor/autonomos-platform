"""
Persona-related schemas for role-based data access.
"""
from typing import Literal, Optional, List
from pydantic import BaseModel, Field


PersonaType = Literal["cto", "cro", "coo", "cfo"]


class PersonaClassifyRequest(BaseModel):
    """Request to classify a query into a persona."""
    query: str = Field(..., description="Natural language query to classify")
    tenant_id: str = Field(..., description="Tenant ID for scoping")


class PersonaClassifyResponse(BaseModel):
    """Response with persona classification."""
    persona: PersonaType = Field(..., description="Detected persona (cto, cro, coo, cfo)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    matched_keywords: List[str] = Field(default_factory=list, description="Keywords that matched")
    trace_id: str = Field(..., description="Trace ID for debugging")


class PersonaTile(BaseModel):
    """A single KPI tile in the persona dashboard."""
    key: str = Field(..., description="Unique identifier for the tile")
    title: str = Field(..., description="Display title")
    value: Optional[str] = Field(None, description="Current value (null if unavailable)")
    delta: Optional[str] = Field(None, description="Change indicator")
    timeframe: str = Field(..., description="Time context (MTD, QTD, etc)")
    last_updated: Optional[str] = Field(None, description="ISO timestamp of last update")
    href: str = Field(..., description="Link to detailed view")
    note: Optional[str] = Field(None, description="Status note (e.g., 'stub')")


class PersonaTable(BaseModel):
    """Table data for persona dashboard."""
    title: str = Field(..., description="Table title")
    columns: List[str] = Field(..., description="Column headers")
    rows: List[List[str]] = Field(default_factory=list, description="Table rows")
    href: str = Field(..., description="Link to full table view")
    note: Optional[str] = Field(None, description="Status note (e.g., 'stub')")


class PersonaSummaryResponse(BaseModel):
    """Summary dashboard for a persona."""
    persona: PersonaType = Field(..., description="Persona type")
    tiles: List[PersonaTile] = Field(..., description="KPI tiles for dashboard")
    table: PersonaTable = Field(..., description="Primary data table")
    trace_id: str = Field(..., description="Trace ID for debugging")
