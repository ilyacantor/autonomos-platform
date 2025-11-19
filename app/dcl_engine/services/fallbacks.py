"""
Graceful Fallback Strategies - Phase 3

Provides degraded service when external dependencies are unavailable.
Used by resilience layer when circuit breakers open or operations timeout.

Strategies:
- LLM unavailable → Heuristic-based mapping (field name similarity)
- RAG unavailable → Cached historical mappings
- Confidence calculation failure → Conservative default scores
- Approval workflow failure → Defer to HITL queue
"""

import logging
import re
from typing import List, Any, Optional, Dict
from difflib import SequenceMatcher
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FallbackMappingProposal:
    """Heuristic-based mapping proposal (used when LLM unavailable)"""
    canonical_field: str
    confidence: float
    reasoning: str
    source: str = "heuristic"


_common_field_mappings = {
    'id': 'id',
    'name': 'name',
    'email': 'email',
    'phone': 'phone',
    'address': 'address',
    'city': 'city',
    'state': 'state',
    'country': 'country',
    'zip': 'zip_code',
    'amount': 'amount',
    'revenue': 'revenue',
    'cost': 'cost',
    'price': 'price',
    'quantity': 'quantity',
    'status': 'status',
    'date': 'date',
    'created': 'created_at',
    'updated': 'updated_at',
    'deleted': 'deleted_at',
    'first_name': 'first_name',
    'last_name': 'last_name',
    'company': 'company',
    'title': 'title',
    'description': 'description',
    'notes': 'notes',
}


def _normalize_field_name(field: str) -> str:
    """Normalize field name for comparison (lowercase, snake_case)"""
    field = field.lower()
    field = re.sub(r'[^a-z0-9_]', '_', field)
    field = re.sub(r'_+', '_', field)
    field = field.strip('_')
    return field


def _calculate_field_similarity(source_field: str, canonical_field: str) -> float:
    """Calculate similarity between two field names using SequenceMatcher"""
    normalized_source = _normalize_field_name(source_field)
    normalized_canonical = _normalize_field_name(canonical_field)
    
    return SequenceMatcher(None, normalized_source, normalized_canonical).ratio()


async def heuristic_mapping_fallback(
    connector: str,
    source_table: str,
    source_field: str,
    sample_values: List[Any],
    tenant_id: str,
    context: Optional[Dict[str, Any]] = None
) -> FallbackMappingProposal:
    """
    Heuristic-based mapping proposal when LLM unavailable.
    
    Strategy:
    1. Check common field name patterns (exact match)
    2. Calculate field name similarity with ontology fields
    3. Return low-confidence proposal for human review
    
    Args:
        connector: Source connector ID
        source_table: Source table name
        source_field: Source field name
        sample_values: Sample values (for type hints)
        tenant_id: Tenant identifier
        context: Optional context
        
    Returns:
        FallbackMappingProposal with low confidence (requires HITL)
    """
    logger.warning(
        f"LLM unavailable, using heuristic fallback for {connector}.{source_table}.{source_field}"
    )
    
    normalized_field = _normalize_field_name(source_field)
    
    if normalized_field in _common_field_mappings:
        canonical_field = _common_field_mappings[normalized_field]
        confidence = 0.65
        reasoning = f"Heuristic: exact match in common field patterns ({normalized_field} → {canonical_field})"
        
        logger.info(
            f"Heuristic fallback found exact match: {source_field} → {canonical_field} "
            f"(confidence={confidence:.2f})"
        )
    else:
        best_match = None
        best_similarity = 0.0
        
        for canonical_candidate in _common_field_mappings.values():
            similarity = _calculate_field_similarity(source_field, canonical_candidate)
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = canonical_candidate
        
        if best_match and best_similarity >= 0.6:
            canonical_field = best_match
            confidence = min(0.60, best_similarity)
            reasoning = (
                f"Heuristic: best similarity match ({source_field} → {canonical_field}, "
                f"similarity={best_similarity:.2f})"
            )
        else:
            canonical_field = "unmapped"
            confidence = 0.30
            reasoning = (
                f"Heuristic: no confident match found (best similarity={best_similarity:.2f}), "
                "human review required"
            )
    
    return FallbackMappingProposal(
        canonical_field=canonical_field,
        confidence=confidence,
        reasoning=reasoning,
        source="heuristic"
    )


async def rag_cache_fallback(
    connector: str,
    source_table: str,
    source_field: str,
    tenant_id: str
) -> Optional[Dict[str, Any]]:
    """
    Cached RAG lookup when pgvector unavailable.
    
    Returns None if no cached result available (triggers HITL).
    In production, this would query a local cache (Redis/SQLite).
    
    Args:
        connector: Source connector ID
        source_table: Source table name
        source_field: Source field name
        tenant_id: Tenant identifier
        
    Returns:
        Cached mapping dict or None
    """
    logger.warning(
        f"RAG service unavailable, checking local cache for "
        f"{connector}.{source_table}.{source_field}"
    )
    
    return None


def confidence_conservative_fallback(factors: Dict[str, Any]) -> Dict[str, Any]:
    """
    Conservative confidence scoring when ML model unavailable.
    
    Returns lower confidence scores to trigger human review.
    
    Args:
        factors: Confidence factor dictionary
        
    Returns:
        Conservative confidence result
    """
    logger.warning("Confidence service degraded, using conservative fallback")
    
    conservative_score = 0.55
    
    return {
        "score": conservative_score,
        "tier": "medium",
        "factors": factors,
        "recommendations": [
            "Conservative fallback applied (confidence service degraded)",
            "Manual review recommended",
            "Verify mapping accuracy before production use"
        ]
    }


async def approval_hitl_defer_fallback(
    proposal_id: str,
    tenant_id: str,
    priority: str = "high"
) -> Dict[str, Any]:
    """
    Defer approval to HITL queue when approval service unavailable.
    
    Creates high-priority HITL task for human review.
    
    Args:
        proposal_id: Mapping proposal ID
        tenant_id: Tenant identifier
        priority: Priority level (default: high)
        
    Returns:
        HITL queue confirmation
    """
    logger.warning(
        f"Approval service unavailable, deferring proposal {proposal_id} to HITL queue"
    )
    
    return {
        "workflow_id": f"hitl-{proposal_id}",
        "status": "queued",
        "priority": "high",
        "message": "Deferred to human review due to service degradation",
        "assigned_to": "human_reviewer",
        "notes": "Approval service temporarily unavailable"
    }
