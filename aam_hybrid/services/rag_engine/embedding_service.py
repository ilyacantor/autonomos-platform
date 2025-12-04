"""
PHASE 2 RACI COMPLIANT: Embedding Service - DEPRECATED

This service no longer performs local embedding generation.
All embedding operations are delegated to DCL Intelligence API.

AAM is responsible ONLY for drift detection and observation.
DCL Intelligence API handles all vector embeddings via RAGLookupService.
"""
import logging
from typing import List
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    PHASE 2 RACI COMPLIANT: Embedding generation delegated to DCL Intelligence API.
    
    This service is deprecated and returns empty vectors.
    All embedding operations handled by DCL Intelligence Layer.
    """
    
    def __init__(self):
        # PHASE 2: No local embedding client - delegate to DCL Intelligence API
        self.dimensions = 1536
        logger.info("EmbeddingService initialized (PHASE 2 - RACI COMPLIANT): Delegates to DCL Intelligence API")
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        PHASE 2 RACI COMPLIANT: Embedding generation delegated to DCL Intelligence API.
        
        This method returns empty vector - DCL handles all embedding operations.
        
        Args:
            text: Input text to embed
            
        Returns:
            Empty embedding vector (DCL handles actual embeddings)
        """
        logger.info(
            f"⚠️ PHASE 2: generate_embedding called for text '{text[:50]}...' but "
            "AAM no longer performs embedding operations. DCL Intelligence API handles this."
        )
        return [0.0] * self.dimensions


embedding_service = EmbeddingService()
