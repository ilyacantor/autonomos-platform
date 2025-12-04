import uuid
from fastapi import APIRouter, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas.kb import KBIngestRequest, KBIngestResponse, IngestedDocument
from ..kb.ingestion import get_ingestion_pipeline
from ..kb.repository import KBRepository
from ..main import get_db
from ..utils import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/kb", tags=["Knowledge Base"])


@router.post("/ingest", response_model=KBIngestResponse)
async def ingest_documents(
    request: Request,
    req: KBIngestRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Ingest documents into knowledge base.
    
    Processes items through:
    1. Chunking (adaptive or fixed-size)
    2. Embedding generation
    3. PII redaction (if enabled)
    4. Storage in database
    
    Note: For production, this should be a background job via RQ.
    For now, processing synchronously for simplicity.
    """
    trace_id = request.state.trace_id
    logger.info(f"KB ingest request: {len(req.items)} items, policy={req.policy}")
    
    pipeline = get_ingestion_pipeline()
    repository = KBRepository(db)
    
    ingested_docs = []
    
    for item in req.items:
        try:
            logger.info(f"Processing item: {item.type} - {item.location}")
            
            processed = pipeline.process_item(item, req.policy)
            
            if "error" in processed:
                logger.error(f"Failed to process item: {processed['error']}")
                continue
            
            document = await repository.create_document(
                tenant_id=req.tenant_id,
                env=req.env,
                doc_id=processed["doc_id"],
                title=processed["title"],
                source_type=processed["source_type"],
                source_location=processed["source_location"],
                tags=processed["tags"],
                metadata=processed["metadata"]
            )
            
            for chunk_data in processed["chunks"]:
                await repository.create_chunk(
                    document_id=document.id,
                    tenant_id=req.tenant_id,
                    env=req.env,
                    chunk_index=chunk_data["index"],
                    section=chunk_data["section"],
                    text=chunk_data["text"],
                    text_redacted=chunk_data.get("text_redacted"),
                    embedding=chunk_data["embedding"],
                    tokens=chunk_data["tokens"],
                    metadata=chunk_data["metadata"]
                )
            
            await repository.update_document_status(
                doc_id=processed["doc_id"],
                status="completed"
            )
            
            ingested_docs.append(IngestedDocument(
                doc_id=processed["doc_id"],
                chunks=len(processed["chunks"]),
                tags=processed["tags"]
            ))
            
            logger.info(f"Ingested document: {processed['doc_id']} with {len(processed['chunks'])} chunks")
            
        except Exception as e:
            logger.error(f"Failed to ingest item: {e}", exc_info=True)
            continue
    
    return KBIngestResponse(
        trace_id=trace_id,
        ingested=ingested_docs
    )
