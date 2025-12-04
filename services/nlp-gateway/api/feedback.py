from fastapi import APIRouter, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas.feedback import FeedbackLogRequest, FeedbackLogResponse
from ..kb.repository import KBRepository
from ..main import get_db
from ..utils import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/feedback", tags=["Feedback"])


@router.post("/log", response_model=FeedbackLogResponse)
async def log_feedback(
    request: Request,
    req: FeedbackLogRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Log user feedback on responses.
    
    Captures thumbs up/down ratings and optional notes.
    Used for continuous improvement of retrieval quality.
    """
    trace_id = request.state.trace_id
    logger.info(f"Feedback logged: turn_id={req.turn_id} rating={req.rating}")
    
    repository = KBRepository(db)
    
    try:
        await repository.create_feedback(
            tenant_id=req.tenant_id,
            env=req.env,
            turn_id=req.turn_id,
            trace_id=trace_id,
            rating=req.rating.value,
            notes=req.notes,
            metadata={}
        )
        
        logger.info(f"Feedback saved successfully")
        
        return FeedbackLogResponse(
            trace_id=trace_id,
            ok=True
        )
        
    except Exception as e:
        logger.error(f"Failed to log feedback: {e}", exc_info=True)
        return FeedbackLogResponse(
            trace_id=trace_id,
            ok=False
        )
