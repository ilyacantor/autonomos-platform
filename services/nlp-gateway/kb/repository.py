from typing import List, Optional, Dict, Union
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, delete
from sqlalchemy.orm import selectinload

from ..models.kb import KBDocument, KBChunk, KBMetadata, KBIngestJob, KBFeedback
from ..schemas.common import Environment
from ..utils.logger import get_logger

logger = get_logger(__name__)


def _to_uuid(value: Union[str, UUID]) -> UUID:
    """
    Convert string or UUID to UUID.
    
    Args:
        value: String tenant ID (e.g., "demo-tenant") or UUID
        
    Returns:
        UUID object
        
    Raises:
        ValueError: If string is not a valid UUID format
    """
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        try:
            return UUID(value)
        except ValueError as e:
            logger.error(f"Invalid UUID format: {value}")
            raise ValueError(f"Invalid UUID format: {value}") from e
    raise TypeError(f"Expected str or UUID, got {type(value)}")


class KBRepository:
    """
    Repository layer for KB operations.
    
    Provides CRUD operations for:
    - Documents
    - Chunks
    - Metadata
    - Ingest Jobs
    - Feedback
    
    Note: All methods accept tenant_id as either string or UUID.
    String tenant IDs are automatically converted to UUIDs.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_document(
        self,
        tenant_id: Union[str, UUID],
        env: Environment,
        doc_id: str,
        title: str,
        source_type: str,
        source_location: str,
        tags: List[str] = None,
        metadata: Dict = None
    ) -> KBDocument:
        """
        Create a new KB document.
        
        Args:
            tenant_id: Tenant ID (string or UUID)
            env: Environment
            doc_id: Document ID
            title: Document title
            source_type: Source type (file, url, text)
            source_location: Source location
            tags: Document tags
            metadata: Additional metadata
            
        Returns:
            Created KBDocument
        """
        tenant_id = _to_uuid(tenant_id)
        document = KBDocument(
            tenant_id=tenant_id,
            env=env.value,
            doc_id=doc_id,
            title=title,
            source_type=source_type,
            source_location=source_location,
            tags=tags or [],
            metadata=metadata or {},
            status="pending"
        )
        self.session.add(document)
        await self.session.commit()
        await self.session.refresh(document)
        return document
    
    async def get_document(self, doc_id: str) -> Optional[KBDocument]:
        """Get document by doc_id."""
        result = await self.session.execute(
            select(KBDocument).where(KBDocument.doc_id == doc_id)
        )
        return result.scalar_one_or_none()
    
    async def list_documents(
        self,
        tenant_id: Union[str, UUID],
        env: Environment,
        limit: int = 100,
        offset: int = 0
    ) -> List[KBDocument]:
        """
        List documents for a tenant.
        
        Args:
            tenant_id: Tenant ID (string or UUID)
            env: Environment
            limit: Maximum number of documents to return
            offset: Number of documents to skip
            
        Returns:
            List of KBDocument objects
        """
        tenant_id = _to_uuid(tenant_id)
        result = await self.session.execute(
            select(KBDocument)
            .where(
                and_(
                    KBDocument.tenant_id == tenant_id,
                    KBDocument.env == env.value
                )
            )
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()
    
    async def update_document_status(
        self,
        doc_id: str,
        status: str
    ) -> Optional[KBDocument]:
        """Update document status."""
        document = await self.get_document(doc_id)
        if document:
            document.status = status
            await self.session.commit()
            await self.session.refresh(document)
        return document
    
    async def delete_document(self, doc_id: str) -> bool:
        """Delete document and all its chunks (cascades)."""
        document = await self.get_document(doc_id)
        if document:
            await self.session.delete(document)
            await self.session.commit()
            return True
        return False
    
    async def create_chunk(
        self,
        document_id: UUID,
        tenant_id: Union[str, UUID],
        env: Environment,
        chunk_index: int,
        section: str,
        text: str,
        text_redacted: Optional[str] = None,
        embedding: Optional[List[float]] = None,
        tokens: int = 0,
        metadata: Dict = None
    ) -> KBChunk:
        """
        Create a new KB chunk.
        
        Args:
            document_id: Parent document ID
            tenant_id: Tenant ID (string or UUID)
            env: Environment
            chunk_index: Index of this chunk in the document
            section: Section name
            text: Chunk text
            text_redacted: PII-redacted text (optional)
            embedding: Vector embedding (optional)
            tokens: Token count
            metadata: Additional metadata
            
        Returns:
            Created KBChunk
        """
        tenant_id = _to_uuid(tenant_id)
        chunk = KBChunk(
            document_id=document_id,
            tenant_id=tenant_id,
            env=env.value,
            chunk_index=chunk_index,
            section=section,
            text=text,
            text_redacted=text_redacted,
            embedding=embedding,
            tokens=tokens,
            metadata=metadata or {}
        )
        self.session.add(chunk)
        await self.session.commit()
        await self.session.refresh(chunk)
        return chunk
    
    async def list_chunks_by_document(
        self,
        document_id: UUID
    ) -> List[KBChunk]:
        """List all chunks for a document."""
        result = await self.session.execute(
            select(KBChunk)
            .where(KBChunk.document_id == document_id)
            .order_by(KBChunk.chunk_index)
        )
        return result.scalars().all()
    
    async def create_ingest_job(
        self,
        tenant_id: Union[str, UUID],
        env: Environment,
        job_id: str,
        items_count: int,
        policy: Dict
    ) -> KBIngestJob:
        """
        Create a new ingest job.
        
        Args:
            tenant_id: Tenant ID (string or UUID)
            env: Environment
            job_id: Job ID
            items_count: Number of items to process
            policy: Ingestion policy
            
        Returns:
            Created KBIngestJob
        """
        tenant_id = _to_uuid(tenant_id)
        job = KBIngestJob(
            tenant_id=tenant_id,
            env=env.value,
            job_id=job_id,
            items_count=items_count,
            policy=policy,
            status="queued"
        )
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)
        return job
    
    async def get_ingest_job(self, job_id: str) -> Optional[KBIngestJob]:
        """Get ingest job by job_id."""
        result = await self.session.execute(
            select(KBIngestJob).where(KBIngestJob.job_id == job_id)
        )
        return result.scalar_one_or_none()
    
    async def update_ingest_job(
        self,
        job_id: str,
        status: Optional[str] = None,
        items_processed: Optional[int] = None,
        result: Optional[Dict] = None,
        error: Optional[str] = None
    ) -> Optional[KBIngestJob]:
        """Update ingest job status and progress."""
        job = await self.get_ingest_job(job_id)
        if job:
            if status:
                job.status = status
            if items_processed is not None:
                job.items_processed = items_processed
            if result:
                job.result = result
            if error:
                job.error = error
            await self.session.commit()
            await self.session.refresh(job)
        return job
    
    async def create_feedback(
        self,
        tenant_id: Union[str, UUID],
        env: Environment,
        turn_id: str,
        trace_id: str,
        rating: str,
        notes: str = "",
        metadata: Dict = None
    ) -> KBFeedback:
        """
        Create feedback record.
        
        Args:
            tenant_id: Tenant ID (string or UUID)
            env: Environment
            turn_id: Turn ID
            trace_id: Trace ID
            rating: Rating (thumbs_up, thumbs_down)
            notes: Optional notes
            metadata: Additional metadata
            
        Returns:
            Created KBFeedback
        """
        tenant_id = _to_uuid(tenant_id)
        feedback = KBFeedback(
            tenant_id=tenant_id,
            env=env.value,
            turn_id=turn_id,
            trace_id=trace_id,
            rating=rating,
            notes=notes,
            metadata=metadata or {}
        )
        self.session.add(feedback)
        await self.session.commit()
        await self.session.refresh(feedback)
        return feedback
    
    async def get_metadata(
        self,
        tenant_id: Union[str, UUID],
        env: Environment,
        key: str
    ) -> Optional[KBMetadata]:
        """
        Get metadata value by key.
        
        Args:
            tenant_id: Tenant ID (string or UUID)
            env: Environment
            key: Metadata key
            
        Returns:
            KBMetadata object or None
        """
        tenant_id = _to_uuid(tenant_id)
        result = await self.session.execute(
            select(KBMetadata).where(
                and_(
                    KBMetadata.tenant_id == tenant_id,
                    KBMetadata.env == env.value,
                    KBMetadata.key == key
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def set_metadata(
        self,
        tenant_id: Union[str, UUID],
        env: Environment,
        key: str,
        value: Dict
    ) -> KBMetadata:
        """
        Set metadata value (upsert).
        
        Args:
            tenant_id: Tenant ID (string or UUID)
            env: Environment
            key: Metadata key
            value: Metadata value
            
        Returns:
            KBMetadata object
        """
        tenant_id = _to_uuid(tenant_id)
        metadata = await self.get_metadata(tenant_id, env, key)
        if metadata:
            metadata.value = value
        else:
            metadata = KBMetadata(
                tenant_id=tenant_id,
                env=env.value,
                key=key,
                value=value
            )
            self.session.add(metadata)
        await self.session.commit()
        await self.session.refresh(metadata)
        return metadata
