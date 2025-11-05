"""
Canonical Event Processor for AutonomOS AAM

This module normalizes and validates canonical events before they're published
to Redis Streams. It provides the foundation for Phase 4 drift detection and repair.

Processing Pipeline:
1. Normalize: Standardize field names and infer data types
2. Validate: Check schema compliance and data quality
3. Enrich: Add metadata for observability and lineage tracking
4. Filter: Remove invalid events with warning logs
"""

import logging
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import sys

import redis

current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

from app.contracts.canonical_event import EntityEvent, FieldMapping
from app.config.feature_flags import FeatureFlagConfig, FeatureFlag

logger = logging.getLogger(__name__)


class CanonicalProcessor:
    """
    Processes canonical events with normalization, validation, and enrichment.
    
    This processor ensures all events flowing through AAM meet quality standards
    before being published to DCL streams.
    """
    
    PROCESSOR_VERSION = "1.0"
    
    def __init__(self, redis_client: redis.Redis, db_session=None):
        """
        Initialize the canonical processor.
        
        Args:
            redis_client: Redis client for metadata persistence
            db_session: Optional SQLAlchemy session for PostgreSQL persistence
        """
        self.redis_client = redis_client
        self.db_session = db_session
        logger.info(f"CanonicalProcessor initialized (version {self.PROCESSOR_VERSION})")
    
    def process_events(self, events: List[EntityEvent]) -> List[EntityEvent]:
        """
        Main processing pipeline for canonical events.
        
        Pipeline stages:
        1. Normalize each event (field names, data types)
        2. Detect drift (schema changes via fingerprint comparison)
        3. Validate events (schema compliance, required fields)
        4. Enrich with metadata (timestamps, confidence, lineage)
        5. Filter out invalid events
        
        Args:
            events: List of canonical events to process
            
        Returns:
            List of validated and enriched events
        """
        if not events:
            logger.warning("No events to process")
            return []
        
        logger.info(f"Processing {len(events)} canonical events...")
        
        drift_detector = None
        if FeatureFlagConfig.is_enabled(FeatureFlag.ENABLE_DRIFT_DETECTION):
            from .drift_detector import DriftDetector
            drift_detector = DriftDetector(self.redis_client)
            logger.info("Drift detection enabled")
        
        processed_events = []
        invalid_count = 0
        
        for event in events:
            try:
                # Stage 1: Normalize
                normalized_event = self.normalize_event(event)
                
                # Stage 2: Detect drift (after normalization, before validation)
                if drift_detector:
                    drift_event = drift_detector.detect_drift(normalized_event)
                    if drift_event:
                        logger.warning(
                            f"⚠️ Schema drift detected: {drift_event.severity} - "
                            f"{drift_event.changes.get('summary', 'unknown changes')}"
                        )
                        
                        # Use structured DriftStatus
                        from app.contracts.canonical_event import DriftStatus
                        
                        drift_status = DriftStatus(
                            drift_detected=True,
                            drift_event_id=drift_event.event_id,
                            drift_severity=drift_event.severity,
                            drift_type=drift_event.drift_type,
                            detected_at=datetime.utcnow()
                        )
                        normalized_event.drift_status = drift_status
                        
                        # Keep backward compatibility: also add to metadata
                        if normalized_event.metadata is None:
                            normalized_event.metadata = {}
                        normalized_event.metadata["drift_detected"] = True
                        normalized_event.metadata["drift_severity"] = drift_event.severity
                        normalized_event.metadata["drift_event_id"] = drift_event.event_id
                        
                        # NEW: Process drift with RepairAgent
                        if FeatureFlagConfig.is_enabled(FeatureFlag.ENABLE_AUTO_REPAIR):
                            from .repair_agent import RepairAgent
                            from app.contracts.canonical_event import RepairSummary, RepairHistory
                            
                            repair_agent = RepairAgent(
                                redis_client=self.redis_client,
                                db_session=self.db_session
                            )
                            
                            try:
                                repair_batch = repair_agent.suggest_repairs(drift_event, normalized_event)
                                
                                # Build RepairHistory objects with EXPLICIT values
                                repair_history_list = []
                                for suggestion in repair_batch.suggestions:
                                    repair_history_list.append(RepairHistory(
                                        repair_event_id=drift_event.event_id,
                                        repair_action=suggestion.repair_action,
                                        field_name=suggestion.field_name,
                                        suggested_mapping=suggestion.suggested_mapping,
                                        confidence=suggestion.confidence,
                                        confidence_reason=suggestion.confidence_reason if hasattr(suggestion, 'confidence_reason') else None,
                                        transformation=suggestion.transformation if hasattr(suggestion, 'transformation') else None,
                                        rag_similarity_count=suggestion.rag_similarity_count if hasattr(suggestion, 'rag_similarity_count') else 0,
                                        applied_at=datetime.utcnow(),  # EXPLICIT timestamp
                                        applied_by="llm",  # EXPLICIT attribution
                                        human_reviewed=False,  # EXPLICIT pending state
                                        reviewed_by=None,
                                        reviewed_at=None
                                    ))
                                
                                # Create RepairSummary
                                repair_summary = RepairSummary(
                                    repair_processed=True,
                                    auto_applied_count=repair_batch.auto_applied_count,
                                    hitl_queued_count=repair_batch.hitl_queued_count,
                                    rejected_count=repair_batch.rejected_count,
                                    overall_confidence=repair_batch.overall_confidence,
                                    repair_history=repair_history_list
                                )
                                normalized_event.repair_summary = repair_summary
                                
                                # Update drift_status
                                drift_status.repair_attempted = True
                                drift_status.repair_successful = repair_batch.auto_applied_count > 0
                                drift_status.requires_human_review = repair_batch.hitl_queued_count > 0
                                
                                # Log each suggestion with appropriate emoji
                                for suggestion in repair_batch.suggestions:
                                    if suggestion.repair_action == "auto_applied":
                                        logger.info(
                                            f"✅ Auto-applied repair: {suggestion.field_name} → "
                                            f"{suggestion.suggested_mapping} (confidence: {suggestion.confidence:.2f})"
                                        )
                                    elif suggestion.repair_action == "hitl_queued":
                                        logger.info(
                                            f"📋 Queued for HITL review: {suggestion.field_name} → "
                                            f"{suggestion.suggested_mapping} (confidence: {suggestion.confidence:.2f})"
                                        )
                                    elif suggestion.repair_action == "rejected":
                                        logger.warning(
                                            f"❌ Repair rejected (low confidence): {suggestion.field_name} "
                                            f"(confidence: {suggestion.confidence:.2f})"
                                        )
                                
                                # Keep backward compatibility: also add to metadata
                                normalized_event.metadata["repair_processed"] = True
                                normalized_event.metadata["repair_auto_applied"] = repair_batch.auto_applied_count
                                normalized_event.metadata["repair_hitl_queued"] = repair_batch.hitl_queued_count
                                normalized_event.metadata["repair_rejected"] = repair_batch.rejected_count
                                normalized_event.metadata["repair_overall_confidence"] = repair_batch.overall_confidence
                                normalized_event.metadata["repair_suggestions"] = [
                                    {
                                        "field_name": s.field_name,
                                        "suggested_mapping": s.suggested_mapping,
                                        "confidence": s.confidence,
                                        "action": s.repair_action
                                    }
                                    for s in repair_batch.suggestions
                                ]
                                        
                            except Exception as e:
                                logger.error(f"RepairAgent processing failed: {e}", exc_info=True)
                                normalized_event.metadata["repair_error"] = str(e)
                
                # Stage 3: Validate
                if not self.validate_event(normalized_event):
                    invalid_count += 1
                    logger.warning(
                        f"Event {event.event_id} failed validation - skipping. "
                        f"Entity: {event.entity_type}, Connector: {event.connector_name}"
                    )
                    continue
                
                # Stage 4: Enrich metadata
                enriched_event = self.enrich_metadata(normalized_event)
                
                processed_events.append(enriched_event)
                
            except Exception as e:
                invalid_count += 1
                logger.error(
                    f"Error processing event {event.event_id}: {e}",
                    exc_info=True
                )
        
        logger.info(
            f"✅ Processing complete: {len(processed_events)} valid events, "
            f"{invalid_count} invalid events filtered"
        )
        
        return processed_events
    
    def normalize_event(self, event: EntityEvent) -> EntityEvent:
        """
        Normalize event data for consistency.
        
        Normalization includes:
        - Standardize field names to lowercase snake_case
        - Infer and convert data types (string → int/float/bool)
        - Handle null values consistently
        - Preserve original payload in metadata
        
        Args:
            event: Event to normalize
            
        Returns:
            Normalized event
        """
        # Store original payload in metadata
        if event.metadata is None:
            event.metadata = {}
        
        event.metadata['original_payload'] = event.payload.copy()
        
        # Normalize payload field names and values
        normalized_payload = {}
        
        for field_name, value in event.payload.items():
            # Standardize field name to snake_case
            normalized_name = self._to_snake_case(field_name)
            
            # Infer and convert data types
            normalized_value = self._infer_and_convert_type(value)
            
            normalized_payload[normalized_name] = normalized_value
        
        event.payload = normalized_payload
        
        # Update field mappings to reflect normalized names
        if event.field_mappings:
            for mapping in event.field_mappings:
                mapping.canonical_field = self._to_snake_case(mapping.canonical_field)
        
        logger.debug(f"Normalized event {event.event_id}: {len(normalized_payload)} fields")
        
        return event
    
    def validate_event(self, event: EntityEvent) -> bool:
        """
        Validate event schema and data quality.
        
        Validation checks:
        - Required fields: event_id, entity_type, payload
        - Schema fingerprint exists
        - Payload is not empty
        - Field mappings exist and have confidence scores
        
        Args:
            event: Event to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Check required fields
        if not event.event_id:
            logger.warning("Validation failed: missing event_id")
            return False
        
        if not event.entity_type:
            logger.warning(f"Validation failed for {event.event_id}: missing entity_type")
            return False
        
        if not event.payload:
            logger.warning(f"Validation failed for {event.event_id}: empty payload")
            return False
        
        # Validate schema fingerprint
        if not event.schema_fingerprint:
            logger.warning(f"Validation failed for {event.event_id}: missing schema_fingerprint")
            return False
        
        if not event.schema_fingerprint.fingerprint_hash:
            logger.warning(f"Validation failed for {event.event_id}: invalid schema fingerprint")
            return False
        
        # Validate field mappings
        if not event.field_mappings:
            logger.warning(f"Validation failed for {event.event_id}: no field_mappings")
            return False
        
        # Check that all field mappings have confidence scores
        for mapping in event.field_mappings:
            if mapping.confidence_score is None or not (0.0 <= mapping.confidence_score <= 1.0):
                logger.warning(
                    f"Validation failed for {event.event_id}: "
                    f"invalid confidence_score for field {mapping.source_field}"
                )
                return False
        
        # Payload data quality checks
        if len(event.payload) == 0:
            logger.warning(f"Validation failed for {event.event_id}: payload has no fields")
            return False
        
        logger.debug(f"Event {event.event_id} passed validation")
        return True
    
    def enrich_metadata(self, event: EntityEvent) -> EntityEvent:
        """
        Enrich event with processing metadata.
        
        Metadata enrichment:
        - Add processed_at timestamp
        - Calculate overall confidence score from field mappings
        - Add lineage info (ingested_at, processor_version)
        - Prepare for future drift detection metadata
        - Add DataLineage tracking
        
        Args:
            event: Event to enrich
            
        Returns:
            Enriched event
        """
        if event.metadata is None:
            event.metadata = {}
        
        # Add processing timestamp
        event.metadata['processed_at'] = datetime.utcnow().isoformat()
        event.metadata['processor_version'] = self.PROCESSOR_VERSION
        
        # Calculate overall confidence from field mappings if not set or low
        if event.field_mappings:
            avg_confidence = sum(m.confidence_score for m in event.field_mappings) / len(event.field_mappings)
            
            # Update overall confidence if needed
            if not hasattr(event, 'overall_confidence') or event.overall_confidence < avg_confidence:
                event.overall_confidence = round(avg_confidence, 3)
            
            event.metadata['field_confidence_avg'] = round(avg_confidence, 3)
            event.metadata['field_confidence_min'] = round(min(m.confidence_score for m in event.field_mappings), 3)
            event.metadata['field_confidence_max'] = round(max(m.confidence_score for m in event.field_mappings), 3)
        
        # Add lineage information (keep for backward compatibility)
        event.metadata['lineage'] = {
            'ingested_at': event.timestamp.isoformat() if hasattr(event.timestamp, 'isoformat') else str(event.timestamp),
            'processor_version': self.PROCESSOR_VERSION,
            'connector_name': event.connector_name,
            'connector_id': event.connector_id,
            'tenant_id': event.tenant_id
        }
        
        # Prepare for future drift detection (keep for backward compatibility)
        event.metadata['drift_detection'] = {
            'schema_fingerprint': event.schema_fingerprint.fingerprint_hash,
            'field_count': event.schema_fingerprint.field_count,
            'schema_version': event.schema_fingerprint.schema_version
        }
        
        # NEW: Add DataLineage tracking
        from app.contracts.canonical_event import DataLineage
        
        processing_stages = ["ingestion", "normalization"]
        transformations = ["snake_case", "type_inference"]
        
        if event.drift_status and event.drift_status.drift_detected:
            processing_stages.append("drift_detection")
        
        if event.repair_summary and event.repair_summary.repair_processed:
            processing_stages.append("repair")
            transformations.append("auto_repair")
        
        processing_stages.extend(["validation", "enrichment"])
        
        data_lineage = DataLineage(
            source_system=event.connector_name,
            source_connector_id=event.connector_id,
            processing_stages=processing_stages,
            transformations_applied=transformations,
            processor_version=self.PROCESSOR_VERSION,
            data_quality_score=event.overall_confidence
        )
        event.data_lineage = data_lineage
        
        logger.debug(
            f"Enriched event {event.event_id}: "
            f"confidence={event.overall_confidence:.2f}, "
            f"fields={len(event.field_mappings)}"
        )
        
        return event
    
    def _to_snake_case(self, name: str) -> str:
        """
        Convert field name to snake_case.
        
        Examples:
            "firstName" -> "first_name"
            "First Name" -> "first_name"
            "FIRST_NAME" -> "first_name"
            "first-name" -> "first_name"
        
        Args:
            name: Field name to convert
            
        Returns:
            snake_case field name
        """
        # Handle acronyms and camelCase
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1)
        
        # Replace spaces and hyphens with underscores
        s3 = s2.replace(' ', '_').replace('-', '_')
        
        # Convert to lowercase and remove multiple underscores
        s4 = re.sub('_+', '_', s3.lower())
        
        # Remove leading/trailing underscores
        return s4.strip('_')
    
    def _infer_and_convert_type(self, value: Any) -> Any:
        """
        Infer and convert data types for better consistency.
        
        Conversions (in order):
        - "123" -> int (FIRST to prevent "0"/"1" being converted to bool)
        - "123.45" -> float
        - "true"/"false"/"yes"/"no" -> bool (excludes numeric "0"/"1")
        - "null"/"None" -> None
        - Empty strings -> None
        
        Args:
            value: Value to convert
            
        Returns:
            Converted value with inferred type
        """
        # Handle None and null values
        if value is None or value == '':
            return None
        
        # If already not a string, return as-is
        if not isinstance(value, str):
            return value
        
        # Handle null strings
        if value.lower() in ('null', 'none', 'n/a', 'na'):
            return None
        
        # Try integer conversion FIRST (before boolean check)
        # This ensures "0", "1", "123" etc. become integers, not booleans
        try:
            if '.' not in value and 'e' not in value.lower():
                return int(value)
        except (ValueError, AttributeError):
            pass
        
        # Try float conversion
        try:
            return float(value)
        except (ValueError, AttributeError):
            pass
        
        # Handle boolean strings (AFTER numeric conversion)
        # Only explicit boolean keywords, NOT numeric "0"/"1"
        if value.lower() in ('true', 'yes', 'y'):
            return True
        if value.lower() in ('false', 'no', 'n'):
            return False
        
        # Return as string if no conversion applies
        return value


if __name__ == "__main__":
    # Example usage
    from app.contracts.canonical_event import (
        EventType,
        CanonicalEntityType,
        SchemaFingerprint
    )
    
    # Create a sample event
    fingerprint = SchemaFingerprint(
        fingerprint_hash="test123",
        field_count=3,
        field_names=["id", "name", "amount"],
        schema_version="v1.0",
        connector_name="test",
        entity_type="opportunity"
    )
    
    field_mapping = FieldMapping(
        source_field="Amount",
        canonical_field="amount",
        source_type="string",
        canonical_type="float",
        mapping_method="heuristic",
        confidence_score=0.85
    )
    
    event = EntityEvent(
        event_id="test-001",
        event_type=EventType.ENTITY_CREATED,
        connector_name="test",
        connector_id="test-conn-001",
        entity_type=CanonicalEntityType.OPPORTUNITY,
        entity_id="TEST-001",
        tenant_id="tenant-test",
        schema_fingerprint=fingerprint,
        payload={
            "Amount": "100000",
            "OpportunityName": "Test Deal",
            "IsActive": "true"
        },
        field_mappings=[field_mapping],
        overall_confidence=0.85
    )
    
    # Test the processor
    import redis
    redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
    
    processor = CanonicalProcessor(redis_client)
    processed = processor.process_events([event])
    
    if processed:
        print("✅ Event processed successfully!")
        print(f"Normalized payload: {processed[0].payload}")
        print(f"Metadata: {processed[0].metadata}")
