from typing import List, Dict, Tuple, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, text, func
from sqlalchemy.orm import selectinload
import random

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None

from ..models.kb import KBChunk, KBDocument
from ..schemas.common import Environment
from ..schemas.kb import DocumentMatch
from ..utils.logger import get_logger

logger = get_logger(__name__)

if not SENTENCE_TRANSFORMERS_AVAILABLE:
    logger.warning(
        "⚠️ sentence-transformers not installed. "
        "Vector search will use random embeddings (demo mode only). "
        "Install with: pip install sentence-transformers"
    )


class HybridRetriever:
    """
    Hybrid retrieval engine combining BM25 and vector search.
    
    Two-stage retrieval:
    1. BM25: Keyword-based search using PostgreSQL full-text search (tsvector) and trigrams (pg_trgm)
    2. Vector: Semantic search using pgvector cosine similarity
    3. Fusion: Weighted combination with reciprocal rank fusion
    
    Optional Dependencies:
    - sentence-transformers: Required for semantic vector search
      Without it, random embeddings are used (demo mode only)
    """
    
    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        bm25_weight: float = 0.3,
        vector_weight: float = 0.7
    ):
        """
        Initialize hybrid retriever.
        
        Args:
            model_name: SentenceTransformer model name (requires sentence-transformers package)
            bm25_weight: Weight for BM25 results (0-1)
            vector_weight: Weight for vector results (0-1)
        """
        self.model_name = model_name
        self.bm25_weight = bm25_weight
        self.vector_weight = vector_weight
        self._model = None
        logger.info(f"HybridRetriever initialized with model: {model_name}")
    
    @property
    def model(self):
        """Lazy load the sentence transformer model or use fallback."""
        if self._model is None:
            if not SENTENCE_TRANSFORMERS_AVAILABLE:
                logger.warning("Using random embedding fallback (sentence-transformers not available)")
                return None
            try:
                self._model = SentenceTransformer(self.model_name)
                logger.info(f"Loaded sentence transformer model: {self.model_name}")
            except Exception as e:
                logger.error(f"Failed to load model {self.model_name}: {e}")
                return None
        return self._model
    
    def _generate_random_embedding(self, dimension: int = 384) -> List[float]:
        """Generate random embedding for demo/fallback mode."""
        return [random.random() for _ in range(dimension)]
    
    async def search(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        env: Environment,
        query: str,
        top_k: int = 5
    ) -> List[DocumentMatch]:
        """
        Hybrid search combining BM25 and vector search.
        
        Args:
            session: Database session
            tenant_id: Tenant ID (can be string or UUID)
            env: Environment
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of DocumentMatch results
        """
        if isinstance(tenant_id, str):
            try:
                tenant_id = UUID(tenant_id)
            except ValueError as e:
                logger.error(f"Invalid tenant_id format: {tenant_id}")
                return []
        
        if self.model is not None:
            query_embedding = self.model.encode(query).tolist()
        else:
            query_embedding = self._generate_random_embedding()
        
        bm25_results = await self._bm25_search(
            session, tenant_id, env, query, top_k * 2
        )
        
        vector_results = await self._vector_search(
            session, tenant_id, env, query_embedding, top_k * 2
        )
        
        fused_results = self._fuse_results(
            bm25_results, vector_results, top_k
        )
        
        matches = []
        for chunk_id, score in fused_results[:top_k]:
            chunk = await self._get_chunk_with_document(session, chunk_id)
            if chunk:
                matches.append(self._build_document_match(chunk, score))
        
        return matches
    
    async def _bm25_search(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        env: Environment,
        query: str,
        limit: int
    ) -> List[Tuple[UUID, float]]:
        """
        BM25 search using PostgreSQL full-text search and trigrams.
        
        Uses:
        - ts_rank for full-text search ranking
        - similarity() from pg_trgm for fuzzy matching
        """
        sql = text("""
            SELECT 
                id,
                (
                    ts_rank(to_tsvector('english', text), plainto_tsquery('english', :query)) * 0.6 +
                    similarity(text, :query) * 0.4
                ) as score
            FROM kb_chunks
            WHERE tenant_id = :tenant_id
              AND env = :env
              AND (
                  to_tsvector('english', text) @@ plainto_tsquery('english', :query)
                  OR similarity(text, :query) > 0.1
              )
            ORDER BY score DESC
            LIMIT :limit
        """)
        
        result = await session.execute(
            sql,
            {
                "tenant_id": tenant_id,
                "env": env.value,
                "query": query,
                "limit": limit
            }
        )
        
        return [(row.id, row.score) for row in result]
    
    async def _vector_search(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        env: Environment,
        query_embedding: List[float],
        limit: int
    ) -> List[Tuple[UUID, float]]:
        """
        Vector search using pgvector cosine similarity.
        """
        sql = text("""
            SELECT 
                id,
                1 - (embedding <=> :embedding::vector) as score
            FROM kb_chunks
            WHERE tenant_id = :tenant_id
              AND env = :env
              AND embedding IS NOT NULL
            ORDER BY embedding <=> :embedding::vector
            LIMIT :limit
        """)
        
        result = await session.execute(
            sql,
            {
                "tenant_id": tenant_id,
                "env": env.value,
                "embedding": str(query_embedding),
                "limit": limit
            }
        )
        
        return [(row.id, row.score) for row in result]
    
    def _fuse_results(
        self,
        bm25_results: List[Tuple[UUID, float]],
        vector_results: List[Tuple[UUID, float]],
        top_k: int
    ) -> List[Tuple[UUID, float]]:
        """
        Reciprocal rank fusion of BM25 and vector results.
        
        RRF formula: score = sum(1 / (rank + k)) where k=60 (standard constant)
        """
        k = 60
        chunk_scores = {}
        
        for rank, (chunk_id, score) in enumerate(bm25_results, start=1):
            chunk_scores[chunk_id] = chunk_scores.get(chunk_id, 0) + self.bm25_weight / (rank + k)
        
        for rank, (chunk_id, score) in enumerate(vector_results, start=1):
            chunk_scores[chunk_id] = chunk_scores.get(chunk_id, 0) + self.vector_weight / (rank + k)
        
        sorted_chunks = sorted(
            chunk_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return sorted_chunks[:top_k]
    
    async def _get_chunk_with_document(
        self,
        session: AsyncSession,
        chunk_id: UUID
    ) -> Optional[KBChunk]:
        """Get chunk with its parent document loaded."""
        result = await session.execute(
            select(KBChunk)
            .where(KBChunk.id == chunk_id)
            .options(selectinload(KBChunk.document))
        )
        return result.scalar_one_or_none()
    
    def _build_document_match(
        self,
        chunk: KBChunk,
        score: float
    ) -> DocumentMatch:
        """Build DocumentMatch from chunk."""
        text = str(chunk.text_redacted) if chunk.text_redacted else str(chunk.text)
        snippet = text[:200] + "..." if len(text) > 200 else text
        
        citation = f"{str(chunk.document.title)}:{str(chunk.section)}"
        
        return DocumentMatch(
            doc_id=str(chunk.document.doc_id),
            title=str(chunk.document.title),
            section=str(chunk.section),
            score=round(score, 4),
            snippet=snippet,
            citation=citation
        )


_retriever_instance: Optional[HybridRetriever] = None


def get_retriever() -> HybridRetriever:
    """Get singleton retriever instance."""
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = HybridRetriever()
    return _retriever_instance
