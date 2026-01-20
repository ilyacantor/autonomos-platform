"""
Memory Governance Module

Provides memory management for agent conversations:
- Vector store for semantic search
- Right-to-Forget API for GDPR compliance
- Memory retention policies
- Conversation history management
"""

from app.agentic.memory.vector_store import (
    VectorStore,
    MemoryDocument,
    SearchResult,
    get_vector_store,
)
from app.agentic.memory.governance import (
    MemoryGovernance,
    RetentionPolicy,
    ForgetRequest,
    ForgetResult,
    get_memory_governance,
)

__all__ = [
    'VectorStore',
    'MemoryDocument',
    'SearchResult',
    'get_vector_store',
    'MemoryGovernance',
    'RetentionPolicy',
    'ForgetRequest',
    'ForgetResult',
    'get_memory_governance',
]
