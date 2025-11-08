from pydantic import BaseModel, Field
from enum import Enum
from .common import Environment, BaseResponse


class FeedbackRating(str, Enum):
    UP = "up"
    DOWN = "down"


class FeedbackLogRequest(BaseModel):
    tenant_id: str = Field(..., description="Tenant identifier")
    env: Environment = Field(Environment.PROD, description="Environment")
    turn_id: str = Field(..., description="Conversation turn identifier")
    rating: FeedbackRating = Field(..., description="User rating")
    notes: str = Field("", description="Optional feedback notes")


class FeedbackLogResponse(BaseResponse):
    ok: bool = Field(True, description="Success indicator")
