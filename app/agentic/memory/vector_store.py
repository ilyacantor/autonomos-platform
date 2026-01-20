"""
Vector Store for Agent Memory

Provides semantic search over conversation history and context:
- Document storage with embeddings
- Similarity search
- Metadata filtering
- Namespace isolation for multi-tenancy
"""

import hashlib
import logging
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4
import numpy as np

logger = logging.getLogger(__name__)


class DocumentType(str, Enum):
    """Types of stored documents."""
    CONVERSATION = "conversation"  # User-agent conversation turns
    TOOL_OUTPUT = "tool_output"    # Results from tool executions
    KNOWLEDGE = "knowledge"        # General knowledge/context
    SUMMARY = "summary"            # Conversation summaries
    PREFERENCE = "preference"      # User preferences/settings


@dataclass
class MemoryDocument:
    """A document stored in the vector store."""

    doc_id: str
    tenant_id: str
    content: str
    doc_type: DocumentType

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Context
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None
    agent_id: Optional[str] = None

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None

    # Embedding (computed)
    embedding: Optional[List[float]] = None

    def to_dict(self) -> dict:
        return {
            "doc_id": self.doc_id,
            "tenant_id": self.tenant_id,
            "content": self.content,
            "doc_type": self.doc_type.value,
            "metadata": self.metadata,
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "agent_id": self.agent_id,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MemoryDocument":
        return cls(
            doc_id=data["doc_id"],
            tenant_id=data["tenant_id"],
            content=data["content"],
            doc_type=DocumentType(data["doc_type"]),
            metadata=data.get("metadata", {}),
            conversation_id=data.get("conversation_id"),
            user_id=data.get("user_id"),
            agent_id=data.get("agent_id"),
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
        )


@dataclass
class SearchResult:
    """Result from a vector search."""

    document: MemoryDocument
    score: float  # Similarity score (0-1)
    rank: int

    def to_dict(self) -> dict:
        return {
            "document": self.document.to_dict(),
            "score": self.score,
            "rank": self.rank,
        }


class VectorStore:
    """
    Vector store for agent memory.

    In production, integrate with:
    - Pinecone
    - Weaviate
    - Qdrant
    - Chroma
    - pgvector

    This implementation uses a simple in-memory store with
    cosine similarity for demonstration.
    """

    def __init__(
        self,
        embedding_dim: int = 384,
        similarity_threshold: float = 0.7,
    ):
        """
        Initialize the vector store.

        Args:
            embedding_dim: Dimension of embeddings
            similarity_threshold: Minimum similarity for search results
        """
        self.embedding_dim = embedding_dim
        self.similarity_threshold = similarity_threshold

        # In-memory storage (keyed by tenant_id -> doc_id -> document)
        self._documents: Dict[str, Dict[str, MemoryDocument]] = {}

        # Index by various fields for fast lookup
        self._by_conversation: Dict[str, List[str]] = {}  # conversation_id -> doc_ids
        self._by_user: Dict[str, List[str]] = {}  # user_id -> doc_ids
        self._by_agent: Dict[str, List[str]] = {}  # agent_id -> doc_ids

    async def add_document(
        self,
        content: str,
        tenant_id: str,
        doc_type: DocumentType,
        metadata: Optional[Dict[str, Any]] = None,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> MemoryDocument:
        """
        Add a document to the vector store.

        Args:
            content: Document content
            tenant_id: Tenant ID for isolation
            doc_type: Type of document
            metadata: Additional metadata
            conversation_id: Associated conversation
            user_id: Associated user
            agent_id: Associated agent
            expires_at: Expiration time

        Returns:
            Created document
        """
        doc_id = str(uuid4())

        # Generate embedding
        embedding = self._generate_embedding(content)

        doc = MemoryDocument(
            doc_id=doc_id,
            tenant_id=tenant_id,
            content=content,
            doc_type=doc_type,
            metadata=metadata or {},
            conversation_id=conversation_id,
            user_id=user_id,
            agent_id=agent_id,
            expires_at=expires_at,
            embedding=embedding,
        )

        # Store document
        if tenant_id not in self._documents:
            self._documents[tenant_id] = {}
        self._documents[tenant_id][doc_id] = doc

        # Update indices
        if conversation_id:
            if conversation_id not in self._by_conversation:
                self._by_conversation[conversation_id] = []
            self._by_conversation[conversation_id].append(doc_id)

        if user_id:
            if user_id not in self._by_user:
                self._by_user[user_id] = []
            self._by_user[user_id].append(doc_id)

        if agent_id:
            if agent_id not in self._by_agent:
                self._by_agent[agent_id] = []
            self._by_agent[agent_id].append(doc_id)

        logger.debug(f"Added document {doc_id} to vector store")
        return doc

    async def search(
        self,
        query: str,
        tenant_id: str,
        limit: int = 10,
        doc_types: Optional[List[DocumentType]] = None,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        min_score: Optional[float] = None,
    ) -> List[SearchResult]:
        """
        Search for similar documents.

        Args:
            query: Search query
            tenant_id: Tenant ID for isolation
            limit: Maximum results
            doc_types: Filter by document types
            conversation_id: Filter by conversation
            user_id: Filter by user
            agent_id: Filter by agent
            min_score: Minimum similarity score

        Returns:
            List of search results
        """
        min_score = min_score or self.similarity_threshold

        # Get tenant documents
        tenant_docs = self._documents.get(tenant_id, {})
        if not tenant_docs:
            return []

        # Generate query embedding
        query_embedding = self._generate_embedding(query)

        # Calculate similarities
        results = []
        for doc_id, doc in tenant_docs.items():
            # Apply filters
            if doc_types and doc.doc_type not in doc_types:
                continue
            if conversation_id and doc.conversation_id != conversation_id:
                continue
            if user_id and doc.user_id != user_id:
                continue
            if agent_id and doc.agent_id != agent_id:
                continue

            # Check expiration
            if doc.expires_at and doc.expires_at < datetime.utcnow():
                continue

            # Calculate similarity
            if doc.embedding:
                score = self._cosine_similarity(query_embedding, doc.embedding)
                if score >= min_score:
                    results.append((doc, score))

        # Sort by score (descending)
        results.sort(key=lambda x: x[1], reverse=True)

        # Limit and format results
        search_results = []
        for rank, (doc, score) in enumerate(results[:limit], 1):
            search_results.append(SearchResult(
                document=doc,
                score=score,
                rank=rank,
            ))

        return search_results

    async def get_document(
        self,
        doc_id: str,
        tenant_id: str,
    ) -> Optional[MemoryDocument]:
        """Get a specific document."""
        tenant_docs = self._documents.get(tenant_id, {})
        return tenant_docs.get(doc_id)

    async def delete_document(
        self,
        doc_id: str,
        tenant_id: str,
    ) -> bool:
        """Delete a document."""
        tenant_docs = self._documents.get(tenant_id, {})
        if doc_id not in tenant_docs:
            return False

        doc = tenant_docs[doc_id]

        # Remove from indices
        if doc.conversation_id and doc.conversation_id in self._by_conversation:
            if doc_id in self._by_conversation[doc.conversation_id]:
                self._by_conversation[doc.conversation_id].remove(doc_id)

        if doc.user_id and doc.user_id in self._by_user:
            if doc_id in self._by_user[doc.user_id]:
                self._by_user[doc.user_id].remove(doc_id)

        if doc.agent_id and doc.agent_id in self._by_agent:
            if doc_id in self._by_agent[doc.agent_id]:
                self._by_agent[doc.agent_id].remove(doc_id)

        # Delete document
        del tenant_docs[doc_id]

        logger.debug(f"Deleted document {doc_id} from vector store")
        return True

    async def delete_by_conversation(
        self,
        conversation_id: str,
        tenant_id: str,
    ) -> int:
        """Delete all documents for a conversation."""
        doc_ids = self._by_conversation.get(conversation_id, [])
        deleted = 0

        for doc_id in list(doc_ids):  # Copy list to avoid modification during iteration
            if await self.delete_document(doc_id, tenant_id):
                deleted += 1

        return deleted

    async def delete_by_user(
        self,
        user_id: str,
        tenant_id: str,
    ) -> int:
        """Delete all documents for a user (GDPR Right to Forget)."""
        doc_ids = self._by_user.get(user_id, [])
        deleted = 0

        for doc_id in list(doc_ids):
            if await self.delete_document(doc_id, tenant_id):
                deleted += 1

        return deleted

    async def get_conversation_history(
        self,
        conversation_id: str,
        tenant_id: str,
        limit: int = 100,
    ) -> List[MemoryDocument]:
        """Get conversation history in chronological order."""
        doc_ids = self._by_conversation.get(conversation_id, [])
        tenant_docs = self._documents.get(tenant_id, {})

        docs = []
        for doc_id in doc_ids:
            if doc_id in tenant_docs:
                doc = tenant_docs[doc_id]
                # Check expiration
                if not doc.expires_at or doc.expires_at > datetime.utcnow():
                    docs.append(doc)

        # Sort by creation time
        docs.sort(key=lambda x: x.created_at)

        return docs[:limit]

    async def cleanup_expired(
        self,
        tenant_id: Optional[str] = None,
    ) -> int:
        """Remove expired documents."""
        deleted = 0
        now = datetime.utcnow()

        tenants = [tenant_id] if tenant_id else list(self._documents.keys())

        for tid in tenants:
            tenant_docs = self._documents.get(tid, {})
            for doc_id in list(tenant_docs.keys()):
                doc = tenant_docs[doc_id]
                if doc.expires_at and doc.expires_at < now:
                    if await self.delete_document(doc_id, tid):
                        deleted += 1

        return deleted

    async def get_stats(
        self,
        tenant_id: str,
    ) -> Dict[str, Any]:
        """Get vector store statistics for a tenant."""
        tenant_docs = self._documents.get(tenant_id, {})

        # Count by type
        type_counts = {}
        for doc in tenant_docs.values():
            doc_type = doc.doc_type.value
            type_counts[doc_type] = type_counts.get(doc_type, 0) + 1

        return {
            "total_documents": len(tenant_docs),
            "by_type": type_counts,
            "total_conversations": len(set(
                doc.conversation_id for doc in tenant_docs.values()
                if doc.conversation_id
            )),
            "total_users": len(set(
                doc.user_id for doc in tenant_docs.values()
                if doc.user_id
            )),
        }

    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text.

        In production, use:
        - OpenAI embeddings
        - Sentence Transformers
        - Cohere embeddings
        """
        # Simple hash-based pseudo-embedding for demo
        # In production, use actual embedding models
        hash_bytes = hashlib.sha384(text.encode()).digest()

        # Convert bytes to floats in range [-1, 1]
        embedding = []
        for i in range(self.embedding_dim):
            byte_idx = i % len(hash_bytes)
            value = (hash_bytes[byte_idx] / 127.5) - 1.0
            embedding.append(value)

        # Normalize
        norm = sum(x ** 2 for x in embedding) ** 0.5
        if norm > 0:
            embedding = [x / norm for x in embedding]

        return embedding

    def _cosine_similarity(
        self,
        vec1: List[float],
        vec2: List[float],
    ) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(x ** 2 for x in vec1) ** 0.5
        norm2 = sum(x ** 2 for x in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return (dot_product / (norm1 * norm2) + 1) / 2  # Normalize to [0, 1]


# Global instance
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Get the global vector store instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
