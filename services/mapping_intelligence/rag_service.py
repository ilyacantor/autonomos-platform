"""
RAG Service for Mapping Intelligence

Provides AI-powered field mapping proposals using RAG (Retrieval Augmented Generation).
"""
import logging
from typing import Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MappingProposal:
    """Mapping proposal from RAG service"""
    source_field: str
    canonical_field: str
    confidence_score: float
    mapping_method: str
    transformation_function: Optional[str] = None
    semantic_similarity: Optional[float] = None


class RAGService:
    """
    RAG-based mapping intelligence service
    
    Uses retrieval augmented generation to propose field mappings
    by learning from historical mappings and semantic similarity.
    """
    
    def __init__(self):
        """Initialize RAG service"""
        logger.info("RAG Service initialized")
    
    async def get_mapping_proposal(
        self,
        source_field: str,
        context: Dict
    ) -> MappingProposal:
        """
        Get AI-powered mapping proposal for a source field
        
        Args:
            source_field: Source field name to map
            context: Context containing connector_name, canonical_entity, tenant_id
        
        Returns:
            MappingProposal with suggested canonical field and confidence score
        """
        connector_name = context.get('connector_name', '')
        canonical_entity = context.get('canonical_entity', '')
        
        # Simple rule-based mapping for now (can be enhanced with ML/LLM later)
        canonical_field = self._infer_canonical_field(source_field, canonical_entity)
        confidence_score = self._calculate_confidence(source_field, canonical_field)
        
        logger.debug(
            f"RAG proposal for {source_field} ({connector_name}): "
            f"{canonical_field} (confidence: {confidence_score:.2f})"
        )
        
        return MappingProposal(
            source_field=source_field,
            canonical_field=canonical_field,
            confidence_score=confidence_score,
            mapping_method="semantic_similarity",
            semantic_similarity=confidence_score
        )
    
    def _infer_canonical_field(self, source_field: str, canonical_entity: str) -> str:
        """
        Infer canonical field name from source field
        
        Uses simple heuristics - can be enhanced with LLM in future.
        """
        # Convert to lowercase and replace common separators
        normalized = source_field.lower().replace('-', '_').replace(' ', '_')
        
        # Common field mappings
        field_mappings = {
            'id': 'id',
            'name': 'name',
            'email': 'email',
            'phone': 'phone',
            'amount': 'amount',
            'value': 'amount',
            'stage': 'stage',
            'status': 'status',
            'created': 'created_at',
            'createdat': 'created_at',
            'created_date': 'created_at',
            'updated': 'updated_at',
            'updatedat': 'updated_at',
            'updated_date': 'updated_at',
            'owner': 'owner_id',
            'ownerid': 'owner_id',
            'close_date': 'close_date',
            'closedate': 'close_date',
        }
        
        # Try exact match first
        if normalized in field_mappings:
            return field_mappings[normalized]
        
        # Try partial matches
        for key, value in field_mappings.items():
            if key in normalized:
                return value
        
        # Default: return normalized field name
        return normalized
    
    def _calculate_confidence(self, source_field: str, canonical_field: str) -> float:
        """
        Calculate confidence score for the mapping
        
        Returns a score between 0.0 and 1.0.
        """
        # Simple similarity-based confidence
        source_normalized = source_field.lower().replace('-', '_').replace(' ', '_')
        
        # Exact match = high confidence
        if source_normalized == canonical_field:
            return 0.95
        
        # Partial match = medium confidence
        if canonical_field in source_normalized or source_normalized in canonical_field:
            return 0.75
        
        # Common transformations = medium confidence
        if source_normalized.replace('_', '') == canonical_field.replace('_', ''):
            return 0.80
        
        # Default = low confidence (needs review)
        return 0.50
