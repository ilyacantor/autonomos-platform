"""
Embedding Service - Vector generation for RAG
Provides text embeddings for semantic similarity search
"""
import logging
from typing import List
from openai import AsyncOpenAI
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from aam_hybrid.shared.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Generates embeddings for text using OpenAI's API
    Used by RAG Engine for semantic similarity search
    """
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
        self.model = "text-embedding-3-small"
        self.dimensions = 1536
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for input text
        
        Args:
            text: Input text to embed
            
        Returns:
            Embedding vector (list of floats)
        """
        if not self.client:
            logger.warning("OpenAI API not configured - returning zero vector")
            return [0.0] * self.dimensions
        
        try:
            response = await self.client.embeddings.create(
                input=text,
                model=self.model
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return [0.0] * self.dimensions


embedding_service = EmbeddingService()
