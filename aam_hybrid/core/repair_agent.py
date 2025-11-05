"""
Auto-Repair Agent for AutonomOS Schema Drift

This module provides intelligent, LLM-powered schema drift repair with
RAG-enhanced context and human-in-the-loop (HITL) workflow integration.

Key Features:
- LLM + RAG for intelligent field mapping suggestions
- 3-tier confidence scoring (auto-apply, HITL queue, reject)
- Redis-backed HITL queue for medium-confidence repairs
- Graceful degradation with comprehensive error handling
- Feature flag gating for safe rollout

Usage:
    repair_agent = RepairAgent(redis_client, llm_service, rag_engine)
    suggestions = repair_agent.suggest_repairs(drift_event, canonical_event)
"""

import logging
import json
import os
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path
import sys

import redis

current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(current_dir))

from app.contracts.canonical_event import DriftEvent, EntityEvent
from app.config.feature_flags import FeatureFlagConfig, FeatureFlag

try:
    from repair_types import RepairSuggestion, RepairAction, RepairBatch
except ImportError:
    from .repair_types import RepairSuggestion, RepairAction, RepairBatch

try:
    from app.dcl_engine.llm_service import get_llm_service, LLMService
except ImportError:
    LLMService = None
    get_llm_service = None

try:
    from app.dcl_engine.rag_engine import RAGEngine
except ImportError:
    RAGEngine = None

logger = logging.getLogger(__name__)


class RepairAgent:
    """
    Auto-Repair Agent for Schema Drift Detection.
    
    Uses LLM + RAG to intelligently suggest field mappings for drifted fields,
    with confidence-based decision making and HITL workflow integration.
    
    Confidence Tiers:
    - >= 0.85: Auto-applied (high confidence)
    - 0.6 - 0.85: Queued for HITL review (medium confidence)
    - < 0.6: Rejected (low confidence, too uncertain)
    """
    
    HITL_TTL_SECONDS = 604800
    DEFAULT_CONFIDENCE_THRESHOLD = 0.85
    HITL_LOWER_THRESHOLD = 0.6
    
    def __init__(
        self,
        redis_client: redis.Redis,
        llm_service: Optional[Any] = None,
        rag_engine: Optional[Any] = None,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
        db_session: Optional[Any] = None
    ):
        """
        Initialize the Auto-Repair Agent.
        
        Args:
            redis_client: Redis client for HITL queue storage
            llm_service: LLM service for generating repair suggestions (optional)
            rag_engine: RAG engine for retrieving similar mappings (optional)
            confidence_threshold: Minimum confidence for auto-apply (default: 0.85)
            db_session: SQLAlchemy database session for PostgreSQL audit persistence (optional)
        """
        self.redis_client = redis_client
        self.confidence_threshold = confidence_threshold
        self.db_session = db_session
        
        self.llm_service = llm_service
        if llm_service is None and get_llm_service is not None:
            try:
                self.llm_service = get_llm_service()
                logger.info("✅ RepairAgent initialized with default LLM service")
            except Exception as e:
                logger.warning(f"Failed to initialize default LLM service: {e}")
                self.llm_service = None
        
        self.rag_engine = rag_engine
        if rag_engine is None and RAGEngine is not None:
            try:
                self.rag_engine = RAGEngine()
                logger.info("✅ RepairAgent initialized with RAG engine")
            except Exception as e:
                logger.warning(f"Failed to initialize RAG engine: {e}")
                self.rag_engine = None
        
        logger.info(
            f"RepairAgent initialized: confidence_threshold={confidence_threshold}, "
            f"LLM={'enabled' if self.llm_service else 'disabled'}, "
            f"RAG={'enabled' if self.rag_engine else 'disabled'}, "
            f"DB={'enabled' if self.db_session else 'disabled (Redis-only)'}"
        )
    
    def suggest_repairs(
        self,
        drift_event: DriftEvent,
        canonical_event: EntityEvent
    ) -> RepairBatch:
        """
        Generate repair suggestions for drifted fields in a drift event.
        
        Pipeline:
        1. Check feature flags (ENABLE_AUTO_REPAIR)
        2. Extract drifted fields from drift event
        3. For each drifted field:
           a. Query RAG for similar historical mappings
           b. Build LLM prompt with RAG context
           c. Call LLM to generate field mapping with confidence
           d. Apply confidence-based decision (auto/HITL/reject)
           e. Queue for HITL if needed
        4. Return RepairBatch with all suggestions
        
        Args:
            drift_event: DriftEvent containing schema changes
            canonical_event: EntityEvent that triggered drift detection
            
        Returns:
            RepairBatch containing all repair suggestions
        """
        if not FeatureFlagConfig.is_enabled(FeatureFlag.ENABLE_AUTO_REPAIR):
            logger.info("Auto-repair disabled by feature flag - skipping repair suggestions")
            return RepairBatch(
                drift_event_id=drift_event.event_id,
                suggestions=[],
                total_fields=0
            )
        
        logger.info(
            f"🔧 Generating repair suggestions for drift event {drift_event.event_id} "
            f"(severity: {drift_event.severity})"
        )
        
        repair_batch = RepairBatch(drift_event_id=drift_event.event_id)
        
        drifted_fields = self._extract_drifted_fields(drift_event)
        
        if not drifted_fields:
            logger.warning(f"No drifted fields found in drift event {drift_event.event_id}")
            return repair_batch
        
        logger.info(f"Processing {len(drifted_fields)} drifted fields...")
        
        for field_info in drifted_fields:
            try:
                suggestion = self._process_drifted_field(
                    field_info=field_info,
                    drift_event=drift_event,
                    canonical_event=canonical_event
                )
                
                repair_batch.add_suggestion(suggestion)
                
                logger.info(
                    f"  ✓ {field_info['field_name']}: {suggestion.repair_action} "
                    f"(confidence: {suggestion.confidence:.2f})"
                )
                
            except Exception as e:
                logger.error(
                    f"Error processing drifted field {field_info.get('field_name', 'unknown')}: {e}",
                    exc_info=True
                )
                
                fallback_suggestion = self._create_rejected_suggestion(
                    field_name=field_info.get('field_name', 'unknown'),
                    reason=f"Processing error: {str(e)}"
                )
                repair_batch.add_suggestion(fallback_suggestion)
        
        logger.info(
            f"✅ Repair suggestions complete: {repair_batch.auto_applied_count} auto-applied, "
            f"{repair_batch.hitl_queued_count} HITL queued, {repair_batch.rejected_count} rejected"
        )
        
        return repair_batch
    
    def _extract_drifted_fields(self, drift_event: DriftEvent) -> List[Dict[str, Any]]:
        """
        Extract drifted fields from drift event changes.
        
        Args:
            drift_event: DriftEvent containing schema changes
            
        Returns:
            List of drifted field info dictionaries
        """
        drifted_fields = []
        
        changes = drift_event.changes
        
        added_fields = changes.get('added_fields', [])
        for field_name in added_fields:
            drifted_fields.append({
                'field_name': field_name,
                'drift_type': 'added',
                'field_type': 'unknown'
            })
        
        removed_fields = changes.get('removed_fields', [])
        for field_name in removed_fields:
            drifted_fields.append({
                'field_name': field_name,
                'drift_type': 'removed',
                'field_type': 'unknown'
            })
        
        return drifted_fields
    
    def _process_drifted_field(
        self,
        field_info: Dict[str, Any],
        drift_event: DriftEvent,
        canonical_event: EntityEvent
    ) -> RepairSuggestion:
        """
        Process a single drifted field and generate repair suggestion.
        
        Args:
            field_info: Dictionary with field_name, drift_type, field_type
            drift_event: Parent drift event
            canonical_event: Canonical event that triggered drift
            
        Returns:
            RepairSuggestion with confidence scoring and action
        """
        field_name = field_info['field_name']
        field_type = field_info.get('field_type', 'unknown')
        
        sample_value = None
        if canonical_event.payload and field_name in canonical_event.payload:
            sample_value = canonical_event.payload[field_name]
        
        rag_context, rag_similarity_count = self._retrieve_rag_context(
            field_name=field_name,
            field_type=field_type,
            connector=drift_event.connector_name,
            entity_type=drift_event.entity_type
        )
        
        llm_result = self._call_llm_for_mapping(
            field_name=field_name,
            field_type=field_type,
            connector=drift_event.connector_name,
            entity_type=drift_event.entity_type,
            rag_context=rag_context
        )
        
        if not llm_result:
            return self._create_rejected_suggestion(
                field_name=field_name,
                reason="LLM call failed - insufficient confidence to auto-repair"
            )
        
        confidence = llm_result.get('confidence', 0.0)
        suggested_mapping = llm_result.get('suggested_mapping', '')
        confidence_reason = llm_result.get('confidence_reason', 'No reason provided')
        transformation = llm_result.get('transformation', 'direct')
        
        repair_action = self._determine_repair_action(confidence)
        
        suggestion = RepairSuggestion(
            field_name=field_name,
            original_value=sample_value,
            suggested_mapping=suggested_mapping,
            confidence=confidence,
            confidence_reason=confidence_reason,
            rag_similarity_count=rag_similarity_count,
            repair_action=repair_action,
            queued_for_hitl=(repair_action == RepairAction.HITL_QUEUED),
            transformation=transformation,
            metadata={
                'llm_model': self.llm_service.get_model_name() if self.llm_service else 'none',
                'drift_event_id': drift_event.event_id,
                'connector': drift_event.connector_name,
                'entity_type': drift_event.entity_type,
                'tenant_id': drift_event.tenant_id
            }
        )
        
        if repair_action == RepairAction.HITL_QUEUED:
            logger.info(f"🔄 Queueing {field_name} for HITL review (confidence: {confidence:.2f})")
            self._queue_for_hitl(suggestion, drift_event, rag_context)
        
        return suggestion
    
    def _retrieve_rag_context(
        self,
        field_name: str,
        field_type: str,
        connector: str,
        entity_type: str
    ) -> tuple[str, int]:
        """
        Retrieve similar historical mappings from RAG engine.
        
        Args:
            field_name: Name of drifted field
            field_type: Data type of field
            connector: Source connector name
            entity_type: Entity type in source system
            
        Returns:
            Tuple of (RAG context string, similarity count)
        """
        if not self.rag_engine:
            return "No RAG context available (RAG engine not initialized)", 0
        
        try:
            similar_mappings = self.rag_engine.retrieve_similar_mappings(
                field_name=field_name,
                field_type=field_type,
                source_system=connector,
                top_k=5,
                min_confidence=0.7
            )
            
            if not similar_mappings:
                return "No similar historical mappings found", 0
            
            rag_context = "HISTORICAL MAPPINGS (RAG context):\n"
            for i, mapping in enumerate(similar_mappings, 1):
                rag_context += (
                    f"  {i}. {mapping.get('source_field', 'unknown')} → "
                    f"{mapping.get('ontology_entity', 'unknown')} "
                    f"(confidence: {mapping.get('confidence', 0.0):.2f}, "
                    f"similarity: {mapping.get('similarity_score', 0.0):.2f})\n"
                )
            
            return rag_context, len(similar_mappings)
            
        except Exception as e:
            logger.warning(f"RAG retrieval failed for {field_name}: {e}")
            return f"RAG retrieval error: {str(e)}", 0
    
    def _call_llm_for_mapping(
        self,
        field_name: str,
        field_type: str,
        connector: str,
        entity_type: str,
        rag_context: str
    ) -> Optional[Dict[str, Any]]:
        """
        Call LLM to generate field mapping suggestion with confidence scoring.
        
        Args:
            field_name: Name of drifted field
            field_type: Data type of field
            connector: Source connector name
            entity_type: Entity type in source system
            rag_context: RAG context string with similar mappings
            
        Returns:
            Dictionary with suggested_mapping, confidence, confidence_reason, transformation
            or None if LLM call fails
        """
        if not self.llm_service:
            logger.warning("LLM service not available - cannot generate mapping")
            return None
        
        prompt = self._build_repair_prompt(
            field_name=field_name,
            field_type=field_type,
            connector=connector,
            entity_type=entity_type,
            rag_context=rag_context
        )
        
        try:
            llm_result = self.llm_service.generate(
                prompt=prompt,
                source_key=f"repair_{connector}_{entity_type}_{field_name}"
            )
            
            if not llm_result:
                logger.warning(f"LLM returned no result for {field_name}")
                return None
            
            required_fields = ['suggested_mapping', 'confidence', 'confidence_reason']
            if not all(field in llm_result for field in required_fields):
                logger.warning(f"LLM result missing required fields: {llm_result}")
                return None
            
            return llm_result
            
        except Exception as e:
            logger.error(f"LLM call failed for {field_name}: {e}", exc_info=True)
            return None
    
    def _build_repair_prompt(
        self,
        field_name: str,
        field_type: str,
        connector: str,
        entity_type: str,
        rag_context: str
    ) -> str:
        """
        Build LLM prompt for repair suggestion with RAG context.
        
        Args:
            field_name: Name of drifted field
            field_type: Data type of field
            connector: Source connector name
            entity_type: Entity type in source system
            rag_context: RAG context string
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""You are a data integration repair agent. Analyze the drifted field and suggest the best mapping.

DRIFTED FIELD:
- Name: {field_name}
- Type: {field_type}
- Source: {connector}
- Entity: {entity_type}

{rag_context}

TASK: Suggest the best ontology mapping for this field.

OUTPUT FORMAT (JSON only):
{{
  "suggested_mapping": "canonical_field_name",
  "confidence": 0.0-1.0,
  "confidence_reason": "explanation",
  "transformation": "direct|lowercase|timestamp_conversion|etc"
}}

CONFIDENCE SCORING RULES:
- 0.9-1.0: Perfect RAG match or exact field name match
- 0.75-0.9: Strong RAG similarity or semantic match
- 0.6-0.75: Moderate confidence, requires human review
- <0.6: Uncertain, reject

IMPORTANT: Always return a valid JSON object with all required fields.
"""
        return prompt
    
    def _determine_repair_action(self, confidence: float) -> RepairAction:
        """
        Determine repair action based on confidence score.
        
        3-Tier System:
        - >= 0.85: Auto-apply (high confidence)
        - 0.6 - 0.85: Queue for HITL review (medium confidence)
        - < 0.6: Reject (low confidence)
        
        Args:
            confidence: Confidence score from LLM (0.0-1.0)
            
        Returns:
            RepairAction enum value
        """
        if confidence >= self.confidence_threshold:
            return RepairAction.AUTO_APPLIED
        elif confidence >= self.HITL_LOWER_THRESHOLD:
            if FeatureFlagConfig.is_enabled(FeatureFlag.ENABLE_HITL_WORKFLOW):
                return RepairAction.HITL_QUEUED
            else:
                return RepairAction.REJECTED
        else:
            return RepairAction.REJECTED
    
    def _queue_for_hitl(
        self,
        suggestion: RepairSuggestion,
        drift_event: DriftEvent,
        rag_context: str
    ) -> None:
        """
        Queue repair suggestion for human-in-the-loop review.
        
        Persists to:
        1. Redis (operational queue, 7-day TTL)
        2. PostgreSQL (permanent audit trail, if db_session provided)
        
        Redis Key Pattern:
            hitl:repair:{tenant_id}:{connector}:{entity_type}:{field_name}
        
        Args:
            suggestion: RepairSuggestion to queue
            drift_event: Parent drift event
            rag_context: RAG context for human reviewer
        """
        redis_key = (
            f"hitl:repair:{drift_event.tenant_id}:{drift_event.connector_name}:"
            f"{drift_event.entity_type}:{suggestion.field_name}"
        )
        
        hitl_payload = {
            'field_name': suggestion.field_name,
            'suggested_mapping': suggestion.suggested_mapping,
            'confidence': suggestion.confidence,
            'confidence_reason': suggestion.confidence_reason,
            'rag_context': rag_context,
            'rag_similarity_count': suggestion.rag_similarity_count,
            'transformation': suggestion.transformation,
            'drift_event_id': drift_event.event_id,
            'connector': drift_event.connector_name,
            'entity_type': drift_event.entity_type,
            'tenant_id': drift_event.tenant_id,
            'timestamp': suggestion.timestamp,
            'original_value': str(suggestion.original_value) if suggestion.original_value else None
        }
        
        try:
            self.redis_client.setex(
                redis_key,
                self.HITL_TTL_SECONDS,
                json.dumps(hitl_payload)
            )
            
            logger.info(
                f"📋 Queued for HITL review (Redis): {suggestion.field_name} → {suggestion.suggested_mapping} "
                f"(confidence: {suggestion.confidence:.2f}, TTL: 7 days)"
            )
            
        except Exception as e:
            logger.error(f"Failed to queue HITL item in Redis: {e}", exc_info=True)
        
        if self.db_session:
            try:
                import uuid as uuid_lib
                
                audit_data = {
                    'tenant_id': uuid_lib.UUID(drift_event.tenant_id) if isinstance(drift_event.tenant_id, str) else drift_event.tenant_id,
                    'drift_event_id': drift_event.event_id,
                    'field_name': suggestion.field_name,
                    'connector_name': drift_event.connector_name,
                    'entity_type': drift_event.entity_type,
                    'suggested_mapping': suggestion.suggested_mapping,
                    'confidence': suggestion.confidence,
                    'confidence_reason': suggestion.confidence_reason,
                    'transformation': suggestion.transformation,
                    'rag_similarity_count': suggestion.rag_similarity_count,
                    'review_status': 'pending',
                    'audit_metadata': suggestion.metadata
                }
                
                try:
                    from app.crud import create_hitl_audit_record
                    create_hitl_audit_record(self.db_session, audit_data)
                    logger.info(f"✅ Persisted HITL audit record to PostgreSQL: {suggestion.field_name}")
                except ImportError:
                    logger.warning("app.crud not available - skipping PostgreSQL persistence")
                
            except Exception as e:
                logger.error(f"Failed to persist HITL audit record to PostgreSQL: {e}", exc_info=True)
    
    def _create_rejected_suggestion(
        self,
        field_name: str,
        reason: str
    ) -> RepairSuggestion:
        """
        Create a rejected repair suggestion (fallback for errors).
        
        Args:
            field_name: Name of field that failed
            reason: Reason for rejection
            
        Returns:
            RepairSuggestion with REJECTED action
        """
        return RepairSuggestion(
            field_name=field_name,
            original_value=None,
            suggested_mapping="",
            confidence=0.0,
            confidence_reason=reason,
            rag_similarity_count=0,
            repair_action=RepairAction.REJECTED,
            queued_for_hitl=False,
            transformation=None,
            metadata={'error': True, 'reason': reason}
        )


if __name__ == "__main__":
    print("RepairAgent Module - Auto-Repair Agent for Schema Drift")
    print("=" * 60)
    print("Features:")
    print("  - LLM + RAG powered intelligent repair suggestions")
    print("  - 3-tier confidence scoring (auto/HITL/reject)")
    print("  - Redis-backed HITL queue (7 day TTL)")
    print("  - Feature flag gating for safe rollout")
    print("  - Graceful degradation with error handling")
