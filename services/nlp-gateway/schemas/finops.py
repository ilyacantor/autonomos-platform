from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date
from .common import Environment, BaseResponse


class FinOpsSummaryRequest(BaseModel):
    tenant_id: str = Field(..., description="Tenant identifier")
    env: Environment = Field(Environment.PROD, description="Environment")
    from_date: date = Field(..., alias="from", description="Start date (YYYY-MM-DD)")
    to_date: date = Field(..., alias="to", description="End date (YYYY-MM-DD)")

    class Config:
        populate_by_name = True


class FinOpsAction(BaseModel):
    id: str = Field(..., description="Action identifier")
    date: date = Field(..., description="Action date")
    action: str = Field(..., description="Action description")
    savings: float = Field(..., description="Savings amount")
    status: str = Field(..., description="Action status")


class FinOpsSummaryResponse(BaseResponse):
    window: dict = Field(..., description="Time window {from, to}")
    totals: dict = Field(..., description="Total savings {savings_identified, savings_executed}")
    actions: List[FinOpsAction] = Field(default_factory=list, description="List of FinOps actions")
