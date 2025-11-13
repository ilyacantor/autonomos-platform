from fastapi import APIRouter, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas.kb import KBSearchRequest, KBSearchResponse
from ..kb.retrieval import get_retriever
from ..main import get_db
from ..utils import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/kb", tags=["Knowledge Base"])


@router.post("/search", response_model=KBSearchResponse)
async def search_kb(
    request: Request,
    req: KBSearchRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Search knowledge base using hybrid retrieval (BM25 + vector search).
    
    Returns relevant documents with citations.
    """
    trace_id = request.state.trace_id
    logger.info(f"KB search request: query={req.query[:50]}... top_k={req.top_k}")
    
    retriever = get_retriever()
    
    try:
        matches = await retriever.search(
            session=db,
            tenant_id=req.tenant_id,
            env=req.env,
            query=req.query,
            top_k=req.top_k
        )
        
        logger.info(f"KB search completed: {len(matches)} matches found")
        
        return KBSearchResponse(
            trace_id=trace_id,
            matches=matches
        )
        
    except Exception as e:
        logger.error(f"KB search failed: {e}", exc_info=True)
        return KBSearchResponse(
            trace_id=trace_id,
            matches=[]
        )
