"""
Confidence Scoring Service - Phase 2

Multi-factor confidence calculation for mapping proposals.
Implements 3-tier threshold system from AAM RepairAgent.

Confidence Tiers:
- Auto-apply: >=0.85 (high confidence)
- HITL-queued: 0.6-0.85 (medium confidence, human review required)
- Rejected: <0.6 (low confidence, too uncertain)
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ConfidenceScore:
    """Confidence score result with tier and recommendations"""
    score: float
    tier: str
    factors: Dict[str, float]
    recommendations: list[str]


class ConfidenceScoringService:
    """
    Confidence scoring service for mapping proposals.
    Uses multi-factor scoring with configurable weights.
    """
    
    AUTO_APPLY_THRESHOLD = 0.85
    HITL_LOWER_THRESHOLD = 0.6
    
    DEFAULT_WEIGHTS = {
        'source_quality': 0.20,
        'usage_frequency': 0.15,
        'validation_success': 0.30,
        'human_approval': 0.25,
        'rag_similarity': 0.10
    }
    
    def __init__(self, tenant_weights: Optional[Dict[str, Dict[str, float]]] = None):
        """
        Initialize confidence scoring service.
        
        Args:
            tenant_weights: Optional tenant-specific weight overrides
                          {tenant_id: {factor: weight}}
        """
        self.tenant_weights = tenant_weights or {}
        logger.info("ConfidenceScoringService initialized")
    
    def calculate_confidence(
        self,
        factors: Dict[str, Any],
        tenant_id: str = "default"
    ) -> ConfidenceScore:
        """
        Calculate confidence score using weighted multi-factor analysis.
        
        Factors:
        - source_quality: Source data completeness and consistency (0-1)
        - usage_frequency: How often this mapping has been used successfully (normalized)
        - validation_success: Historical validation success rate (0-1)
        - human_approval: Whether a human has reviewed/approved (0 or 1)
        - rag_similarity: RAG lookup similarity score (0-1, if available)
        
        Args:
            factors: Dictionary of factor values
            tenant_id: Tenant identifier for custom weights
            
        Returns:
            ConfidenceScore with score, tier, factors, and recommendations
        """
        weights = self._get_tenant_weights(tenant_id)
        
        normalized_factors = {
            'source_quality': self._normalize_source_quality(factors.get('source_quality', 0)),
            'usage_frequency': self._normalize_usage_frequency(factors.get('usage_frequency', 0)),
            'validation_success': float(factors.get('validation_success', 0)),
            'human_approval': 1.0 if factors.get('human_approval', False) else 0.0,
            'rag_similarity': float(factors.get('rag_similarity', 0))
        }
        
        score = sum(
            normalized_factors[factor] * weights[factor]
            for factor in normalized_factors
        )
        
        score = max(0.0, min(1.0, score))
        
        tier = self.determine_action(score)
        recommendations = self._generate_recommendations(normalized_factors, score)
        
        logger.info(
            f"Calculated confidence score: {score:.3f} (tier: {tier}) "
            f"for tenant {tenant_id}"
        )
        
        return ConfidenceScore(
            score=score,
            tier=tier,
            factors=normalized_factors,
            recommendations=recommendations
        )
    
    def determine_action(self, confidence_score: float) -> str:
        """
        Determine action based on confidence tier.
        
        Returns:
            - "auto_apply" if >= 0.85
            - "hitl_queued" if 0.6 <= score < 0.85
            - "rejected" if < 0.6
        """
        if confidence_score >= self.AUTO_APPLY_THRESHOLD:
            return "auto_apply"
        elif confidence_score >= self.HITL_LOWER_THRESHOLD:
            return "hitl_queued"
        else:
            return "rejected"
    
    def _get_tenant_weights(self, tenant_id: str) -> Dict[str, float]:
        """Get tenant-specific weights or default weights"""
        return self.tenant_weights.get(tenant_id, self.DEFAULT_WEIGHTS)
    
    def _normalize_source_quality(self, raw_value: Any) -> float:
        """
        Normalize source quality to 0-1 range.
        
        Source quality could be:
        - Completeness ratio (already 0-1)
        - Data freshness score
        - Schema consistency score
        """
        if isinstance(raw_value, (int, float)):
            return max(0.0, min(1.0, float(raw_value)))
        return 0.0
    
    def _normalize_usage_frequency(self, usage_count: int) -> float:
        """
        Normalize usage frequency to 0-1 range.
        
        Uses logarithmic scaling for diminishing returns:
        - 0 uses: 0.0
        - 10 uses: ~0.5
        - 100 uses: ~0.75
        - 1000+ uses: ~1.0
        """
        if usage_count <= 0:
            return 0.0
        import math
        return min(1.0, math.log10(usage_count + 1) / 3.0)
    
    def _generate_recommendations(
        self,
        factors: Dict[str, float],
        score: float
    ) -> list[str]:
        """
        Generate improvement recommendations based on low-scoring factors.
        
        Args:
            factors: Normalized factor scores
            score: Overall confidence score
            
        Returns:
            List of actionable recommendations
        """
        recommendations = []
        
        if score < self.AUTO_APPLY_THRESHOLD:
            if factors['human_approval'] == 0:
                recommendations.append(
                    "Consider human review for production deployment"
                )
        
        if factors['validation_success'] < 0.7:
            recommendations.append(
                "Monitor validation success rate over time"
            )
        
        if factors['usage_frequency'] < 0.3:
            recommendations.append(
                "Mapping has low usage history - monitor closely after deployment"
            )
        
        if factors['rag_similarity'] > 0 and factors['rag_similarity'] < 0.8:
            recommendations.append(
                "RAG similarity moderate - verify canonical field mapping manually"
            )
        
        if factors['source_quality'] < 0.6:
            recommendations.append(
                "Source data quality is low - consider data validation rules"
            )
        
        if not recommendations and score < self.HITL_LOWER_THRESHOLD:
            recommendations.append(
                "Overall confidence is low - manual review strongly recommended"
            )
        
        return recommendations
