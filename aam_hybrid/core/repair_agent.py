"""
Auto-Repair Agent for AutonomOS Schema Drift

PHASE 2 RACI COMPLIANT: This module delegates ALL intelligence operations
to DCL Intelligence API (LLM, RAG, confidence scoring, repairs, approvals).

Key Features:
- HTTP delegation to DCL Intelligence API for all intelligence operations
- Redis-backed HITL queue for medium-confidence repairs
- Graceful degradation with comprehensive error handling
- Feature flag gating for safe rollout

Usage:
    repair_agent = RepairAgent(redis_client)
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

logger = logging.getLogger(__name__)


class RepairAgent:
    """
    PHASE 2 RACI COMPLIANT: Auto-Repair Agent for Schema Drift Detection.
    
    Delegates ALL intelligence operations to DCL Intelligence API via HTTP.
    AAM is responsible ONLY for drift detection and observation.
    
    DCL Intelligence API handles:
    - LLM-powered field mapping suggestions
    - RAG-enhanced context retrieval
    - Confidence scoring and decision making
    - HITL workflow integration
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
        PHASE 2 RACI COMPLIANT: Initialize Auto-Repair Agent.
        
        AAM delegates ALL intelligence to DCL Intelligence API.
        
        Args:
            redis_client: Redis client for HITL queue storage
            llm_service: DEPRECATED - kept for backward compatibility (always None)
            rag_engine: DEPRECATED - kept for backward compatibility (always None)
            confidence_threshold: DEPRECATED - DCL handles confidence scoring
            db_session: SQLAlchemy database session for PostgreSQL audit persistence (optional)
        """
        self.redis_client = redis_client
        self.confidence_threshold = confidence_threshold
        self.db_session = db_session
        
        # PHASE 2 RACI COMPLIANCE: AAM no longer owns LLM/RAG services
        # All intelligence delegated to DCL Intelligence API via HTTP
        # Parameters kept for backward compatibility but always None
        self.llm_service = None
        self.rag_engine = None
        
        logger.info(
            f"RepairAgent initialized (PHASE 2 - RACI COMPLIANT): "
            f"confidence_threshold={confidence_threshold}, "
            f"DB={'enabled' if self.db_session else 'disabled (Redis-only)'}, "
            f"Delegation=DCL Intelligence API"
        )
    
    def suggest_repairs(
        self,
        drift_event: DriftEvent,
        canonical_event: EntityEvent
    ) -> RepairBatch:
        """
        Generate repair suggestions for drifted fields in a drift event.
        
        Pipeline (PHASE 2 - RACI COMPLIANT):
        1. Check feature flags (ENABLE_AUTO_REPAIR, USE_DCL_INTELLIGENCE_API)
        2. If USE_DCL_INTELLIGENCE_API enabled:
           → Delegate to DCL Intelligence API (100% RACI compliance)
        3. Otherwise (fallback):
           → Use local RepairAgent logic (backward compatibility)
        
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
        
        if FeatureFlagConfig.is_enabled(FeatureFlag.USE_DCL_INTELLIGENCE_API):
            logger.info("🚀 Phase 2: Delegating to DCL Intelligence API (RACI compliant)")
            return self._delegate_to_dcl_intelligence(drift_event, canonical_event)
        
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
        
        # PHASE 2 RACI: Confidence scoring delegated to DCL Intelligence API
        # Local fallback uses fixed score to avoid contract test violations
        score = llm_result.get('confidence', 0.0)
        suggested_mapping = llm_result.get('suggested_mapping', '')
        confidence_reason = llm_result.get('confidence_reason', 'No reason provided')
        transformation = llm_result.get('transformation', 'direct')
        
        repair_action = self._determine_repair_action(score)
        
        suggestion = RepairSuggestion(
            field_name=field_name,
            original_value=sample_value,
            suggested_mapping=suggested_mapping,
            confidence=score,
            confidence_reason=confidence_reason,
            rag_similarity_count=rag_similarity_count,
            repair_action=repair_action,
            queued_for_hitl=(repair_action == RepairAction.HITL_QUEUED),
            transformation=transformation,
            metadata={
                'model': 'dcl_intelligence_api',
                'drift_event_id': drift_event.event_id,
                'connector': drift_event.connector_name,
                'entity_type': drift_event.entity_type,
                'tenant_id': drift_event.tenant_id
            }
        )
        
        if repair_action == RepairAction.HITL_QUEUED:
            logger.info(f"🔄 Queueing {field_name} for HITL review (score: {score:.2f})")
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
        PHASE 2 RACI COMPLIANT: LLM calls delegated to DCL Intelligence API.
        
        This local fallback is deprecated. All LLM operations handled by DCL.
        
        Args:
            field_name: Name of drifted field
            field_type: Data type of field
            connector: Source connector name
            entity_type: Entity type in source system
            rag_context: RAG context string with similar mappings
            
        Returns:
            None - DCL Intelligence API handles all LLM operations
        """
        logger.warning(
            f"⚠️ PHASE 2: _call_llm_for_mapping called for {field_name} but "
            "AAM no longer performs LLM operations. DCL Intelligence API handles this."
        )
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
    
    def _delegate_to_dcl_intelligence(
        self,
        drift_event: DriftEvent,
        canonical_event: EntityEvent
    ) -> RepairBatch:
        """
        Delegate repair proposal to DCL Intelligence API (Phase 2 - RACI compliant).
        
        This achieves 100% RACI compliance by removing ALL intelligence from AAM
        and delegating to DCL's centralized intelligence layer.
        
        Flow:
        1. Create DriftEvent in database (if not exists)
        2. Call POST /api/v1/dcl/intelligence/repair-drift
        3. Convert DCL RepairProposal → AAM RepairBatch
        4. Return RepairBatch to AAM for execution
        
        Args:
            drift_event: DriftEvent containing schema changes
            canonical_event: EntityEvent that triggered drift
            
        Returns:
            RepairBatch containing repair suggestions from DCL
        """
        try:
            import httpx
            import os
            
            dcl_api_url = os.getenv("DCL_API_URL", "http://localhost:5000")
            endpoint = f"{dcl_api_url}/api/v1/dcl/intelligence/repair-drift"
            
            request_payload = {
                "drift_event_id": drift_event.event_id,
                "tenant_id": drift_event.tenant_id or "default"
            }
            
            logger.info(f"🌐 Calling DCL Intelligence API: {endpoint}")
            logger.debug(f"Request payload: {request_payload}")
            
            with httpx.Client(timeout=30.0) as client:
                response = client.post(endpoint, json=request_payload)
                response.raise_for_status()
                dcl_proposal = response.json()
            
            logger.info(
                f"✅ DCL Intelligence API responded: "
                f"{dcl_proposal.get('auto_applied_count', 0)} auto-apply, "
                f"{dcl_proposal.get('hitl_queued_count', 0)} HITL, "
                f"{dcl_proposal.get('rejected_count', 0)} rejected"
            )
            
            repair_batch = RepairBatch(drift_event_id=drift_event.event_id)
            
            for field_repair in dcl_proposal.get('field_repairs', []):
                action_map = {
                    'auto_apply': RepairAction.AUTO_APPLIED,
                    'hitl_queued': RepairAction.HITL_QUEUED,
                    'rejected': RepairAction.REJECTED
                }
                
                suggestion = RepairSuggestion(
                    field_name=field_repair['field_name'],
                    original_value=None,
                    suggested_mapping=field_repair['canonical_field'],
                    confidence=field_repair['confidence'],
                    confidence_reason=field_repair['reasoning'],
                    rag_similarity_count=0,
                    repair_action=action_map.get(field_repair['action'], RepairAction.REJECTED),
                    queued_for_hitl=(field_repair['action'] == 'hitl_queued'),
                    transformation='direct',
                    metadata={
                        'source': 'dcl_intelligence',
                        'drift_type': field_repair['drift_type'],
                        'canonical_entity': field_repair['canonical_entity'],
                        'tenant_id': drift_event.tenant_id
                    }
                )
                
                repair_batch.add_suggestion(suggestion)
            
            logger.info(
                f"✅ Converted DCL proposal to RepairBatch: "
                f"{repair_batch.auto_applied_count} auto-apply, "
                f"{repair_batch.hitl_queued_count} HITL, "
                f"{repair_batch.rejected_count} rejected"
            )
            
            return repair_batch
            
        except Exception as e:
            logger.error(
                f"❌ DCL Intelligence API call failed: {e}",
                exc_info=True
            )
            logger.warning("Falling back to local RepairAgent logic (degraded mode)")
            
            return self._fallback_to_local_repair(drift_event, canonical_event)
    
    def _fallback_to_local_repair(
        self,
        drift_event: DriftEvent,
        canonical_event: EntityEvent
    ) -> RepairBatch:
        """
        Fallback to local RepairAgent logic if DCL API fails.
        
        This ensures graceful degradation when DCL Intelligence API is unavailable.
        """
        logger.info("🔄 Using local RepairAgent logic (fallback mode)")
        
        repair_batch = RepairBatch(drift_event_id=drift_event.event_id)
        
        drifted_fields = self._extract_drifted_fields(drift_event)
        
        if not drifted_fields:
            logger.warning(f"No drifted fields found in drift event {drift_event.event_id}")
            return repair_batch
        
        logger.info(f"Processing {len(drifted_fields)} drifted fields (fallback mode)...")
        
        for field_info in drifted_fields:
            try:
                suggestion = self._process_drifted_field(
                    field_info=field_info,
                    drift_event=drift_event,
                    canonical_event=canonical_event
                )
                
                repair_batch.add_suggestion(suggestion)
                
            except Exception as e:
                logger.error(f"Error processing field {field_info.get('field_name')}: {e}")
                fallback_suggestion = self._create_rejected_suggestion(
                    field_name=field_info.get('field_name', 'unknown'),
                    reason=f"Processing error: {str(e)}"
                )
                repair_batch.add_suggestion(fallback_suggestion)
        
        return repair_batch
    
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
