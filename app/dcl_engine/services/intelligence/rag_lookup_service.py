"""
RAG Lookup Service - Phase 2

Vector similarity search for historical mapping knowledge base.
Uses pgvector for semantic search over past mapping decisions.

Provides fast-path RAG lookups before falling back to LLM generation.
"""

import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from ..resilience import (
    with_resilience,
    with_bulkhead,
    DependencyType,
    CircuitBreakerOpenError,
    TimeoutError as ResilienceTimeoutError,
    RetryExhaustedError
)
from ..fallbacks import rag_cache_fallback

logger = logging.getLogger(__name__)


@dataclass
class RAGResult:
    """RAG lookup result"""
    canonical_field: str
    canonical_entity: str
    similarity: float
    source_mapping_id: str
    usage_count: int
    confidence: float
    last_used: Optional[str] = None


class RAGLookupService:
    """
    RAG-based mapping lookup service using pgvector.
    Performs similarity search over historical mapping knowledge base.
    """
    
    DEFAULT_SIMILARITY_THRESHOLD = 0.85
    DEFAULT_TOP_K = 5
    
    def __init__(self, db_session: AsyncSession, embedding_service: Optional[Any] = None):
        """
        Initialize RAG lookup service.
        
        Args:
            db_session: Async SQLAlchemy session
            embedding_service: Optional embedding service (OpenAI, sentence-transformers)
        """
        self.db = db_session
        self.embedding_service = embedding_service
        logger.info("RAGLookupService initialized")
    
    @with_bulkhead("rag")
    @with_resilience(
        DependencyType.RAG,
        operation_name="rag_lookup_mapping",
        fallback_name="_cache_fallback"
    )
    async def lookup_mapping(
        self,
        connector: str,
        source_table: str,
        source_field: str,
        tenant_id: str,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        top_k: int = DEFAULT_TOP_K
    ) -> Optional[RAGResult]:
        """
        Lookup historical mapping via vector similarity search.
        
        Flow:
        1. Build query string: "{connector}.{source_table}.{source_field}"
        2. Generate embedding for query
        3. Perform pgvector <=> similarity search
        4. Filter by tenant_id and similarity_threshold
        5. Return best match (highest similarity)
        
        Args:
            connector: Source connector ID (e.g., 'salesforce')
            source_table: Source table name (e.g., 'Opportunity')
            source_field: Source field name (e.g., 'Amount')
            tenant_id: Tenant identifier for isolation
            similarity_threshold: Minimum cosine similarity (default: 0.85)
            top_k: Number of results to retrieve (default: 5)
            
        Returns:
            RAGResult if similar mapping found, None otherwise
        """
        query_string = f"{connector}.{source_table}.{source_field}"
        logger.info(
            f"RAG lookup for: {query_string} "
            f"(tenant={tenant_id}, threshold={similarity_threshold})"
        )
        
        if not self.embedding_service:
            logger.warning("No embedding service configured, falling back to exact match")
            return await self._exact_match_lookup(
                connector, source_table, source_field, tenant_id
            )
        
        query_embedding = await self._generate_embedding(query_string)
        
        results = await self._similarity_search(
            query_embedding,
            tenant_id,
            similarity_threshold,
            top_k
        )
        
        if not results:
            logger.info(f"No RAG matches found for {query_string}")
            return None
        
        best_match = results[0]
        logger.info(
            f"RAG match found: {best_match['canonical_field']} "
            f"(similarity={best_match['similarity']:.3f})"
        )
        
        return RAGResult(
            canonical_field=best_match['canonical_field'],
            canonical_entity=best_match.get('canonical_entity', 'unknown'),
            similarity=best_match['similarity'],
            source_mapping_id=best_match['id'],
            usage_count=best_match.get('usage_count', 0),
            confidence=best_match.get('confidence', 0.0),
            last_used=best_match.get('last_used')
        )
    
    async def _cache_fallback(
        self,
        connector: str,
        source_table: str,
        source_field: str,
        tenant_id: str,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        top_k: int = DEFAULT_TOP_K
    ) -> Optional[RAGResult]:
        """
        Cache fallback when RAG vector search is unavailable.
        
        Attempts to retrieve cached mapping from local storage or memory.
        Returns None if cache miss, triggering downstream LLM fallback.
        
        Signature matches lookup_mapping (excluding 'self') for decorator compatibility.
        """
        logger.info(
            f"Executing cache fallback for {connector}.{source_table}.{source_field}"
        )
        
        cache_result = await rag_cache_fallback(
            connector=connector,
            source_table=source_table,
            source_field=source_field,
            tenant_id=tenant_id
        )
        
        if cache_result:
            logger.info("Cache fallback successful")
            return RAGResult(
                canonical_field=cache_result['canonical_field'],
                canonical_entity=cache_result.get('canonical_entity', 'unknown'),
                similarity=cache_result.get('similarity', 0.8),
                source_mapping_id=cache_result.get('id', 'cached'),
                usage_count=cache_result.get('usage_count', 0),
                confidence=cache_result.get('confidence', 0.7)
            )
        
        logger.warning("No cache available, returning None to trigger LLM fallback")
        return None
    
    async def index_mapping(
        self,
        connector: str,
        source_table: str,
        source_field: str,
        canonical_field: str,
        canonical_entity: str,
        tenant_id: str,
        confidence: float = 1.0
    ):
        """
        Index a mapping in the vector store for future RAG lookups.
        
        Stores:
        - Query: "{connector}.{source_table}.{source_field}"
        - Embedding: Vector representation of query
        - Metadata: canonical_field, confidence, creation timestamp
        
        Args:
            connector: Source connector ID
            source_table: Source table name
            source_field: Source field name
            canonical_field: Mapped canonical field
            canonical_entity: Canonical entity type
            tenant_id: Tenant identifier
            confidence: Mapping confidence score
        """
        if not self.embedding_service:
            logger.warning("No embedding service configured, skipping indexing")
            return
        
        query_string = f"{connector}.{source_table}.{source_field}"
        embedding = await self._generate_embedding(query_string)
        
        await self._store_embedding(
            query_string=query_string,
            embedding=embedding,
            connector=connector,
            source_table=source_table,
            source_field=source_field,
            canonical_field=canonical_field,
            canonical_entity=canonical_entity,
            tenant_id=tenant_id,
            confidence=confidence
        )
        
        logger.info(f"Indexed mapping: {query_string} → {canonical_field}")
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for query string.
        
        Uses OpenAI embeddings or sentence-transformers.
        """
        if self.embedding_service:
            try:
                embedding = await self.embedding_service.embed(text)
                return embedding
            except Exception as e:
                logger.error(f"Embedding generation failed: {e}")
                raise
        
        raise ValueError("No embedding service configured")
    
    async def _similarity_search(
        self,
        query_embedding: List[float],
        tenant_id: str,
        similarity_threshold: float,
        top_k: int
    ) -> List[Dict[str, Any]]:
        """
        Perform pgvector similarity search.
        
        Uses cosine similarity (<->) operator for efficient vector search.
        """
        try:
            embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
            
            query = text("""
                SELECT 
                    id,
                    connector_name as connector,
                    entity_name as entity,
                    field_name as field,
                    canonical_field,
                    canonical_entity,
                    embedding <-> :query_embedding::vector AS similarity,
                    usage_count,
                    confidence_score as confidence,
                    last_used_at::text as last_used
                FROM repair_knowledge_base
                WHERE tenant_id = :tenant_id
                    AND (embedding <-> :query_embedding::vector) < (1 - :similarity_threshold)
                ORDER BY similarity
                LIMIT :top_k
            """)
            
            result = await self.db.execute(
                query,
                {
                    'query_embedding': embedding_str,
                    'tenant_id': tenant_id,
                    'similarity_threshold': similarity_threshold,
                    'top_k': top_k
                }
            )
            
            rows = result.fetchall()
            
            return [
                {
                    'id': str(row.id),
                    'connector': row.connector,
                    'entity': row.entity,
                    'field': row.field,
                    'canonical_field': row.canonical_field,
                    'canonical_entity': row.canonical_entity,
                    'similarity': 1 - row.similarity,
                    'usage_count': row.usage_count or 0,
                    'confidence': float(row.confidence) if row.confidence else 0.0,
                    'last_used': row.last_used
                }
                for row in rows
            ]
            
        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            return []
    
    async def _store_embedding(
        self,
        query_string: str,
        embedding: List[float],
        connector: str,
        source_table: str,
        source_field: str,
        canonical_field: str,
        canonical_entity: str,
        tenant_id: str,
        confidence: float
    ):
        """Store embedding in repair_knowledge_base table"""
        try:
            embedding_str = '[' + ','.join(map(str, embedding)) + ']'
            
            query = text("""
                INSERT INTO repair_knowledge_base (
                    tenant_id,
                    connector_name,
                    entity_name,
                    field_name,
                    canonical_field,
                    canonical_entity,
                    embedding,
                    confidence_score,
                    usage_count,
                    created_at,
                    last_used_at
                ) VALUES (
                    :tenant_id,
                    :connector,
                    :entity,
                    :field,
                    :canonical_field,
                    :canonical_entity,
                    :embedding::vector,
                    :confidence,
                    0,
                    NOW(),
                    NOW()
                )
                ON CONFLICT (tenant_id, connector_name, entity_name, field_name)
                DO UPDATE SET
                    usage_count = repair_knowledge_base.usage_count + 1,
                    last_used_at = NOW()
            """)
            
            await self.db.execute(
                query,
                {
                    'tenant_id': tenant_id,
                    'connector': connector,
                    'entity': source_table,
                    'field': source_field,
                    'canonical_field': canonical_field,
                    'canonical_entity': canonical_entity,
                    'embedding': embedding_str,
                    'confidence': confidence
                }
            )
            await self.db.commit()
            
        except Exception as e:
            logger.error(f"Failed to store embedding: {e}")
            await self.db.rollback()
            raise
    
    async def _exact_match_lookup(
        self,
        connector: str,
        source_table: str,
        source_field: str,
        tenant_id: str
    ) -> Optional[RAGResult]:
        """
        Fallback exact match lookup when embedding service unavailable.
        
        Checks field_mappings table for exact connector/table/field match.
        """
        try:
            query = text("""
                SELECT 
                    id,
                    canonical_field,
                    canonical_entity,
                    confidence_score as confidence,
                    1.0 as similarity,
                    0 as usage_count
                FROM field_mappings
                WHERE tenant_id = :tenant_id
                    AND connector_id = (
                        SELECT id FROM connector_definitions 
                        WHERE connector_name = :connector 
                        AND tenant_id = :tenant_id
                        LIMIT 1
                    )
                    AND source_table = :source_table
                    AND source_field = :source_field
                    AND status = 'active'
                ORDER BY confidence_score DESC
                LIMIT 1
            """)
            
            result = await self.db.execute(
                query,
                {
                    'tenant_id': tenant_id,
                    'connector': connector,
                    'source_table': source_table,
                    'source_field': source_field
                }
            )
            
            row = result.fetchone()
            if row:
                return RAGResult(
                    canonical_field=row.canonical_field,
                    canonical_entity=row.canonical_entity,
                    similarity=1.0,
                    source_mapping_id=str(row.id),
                    usage_count=0,
                    confidence=float(row.confidence) if row.confidence else 0.0
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Exact match lookup failed: {e}")
            return None
