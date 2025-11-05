"""
Drift Detector for AutonomOS AAM

This module detects schema changes in connector data sources by comparing
historical fingerprints stored in Redis with current schema fingerprints.

Key Features:
- Schema fingerprint comparison for drift detection
- Redis-backed fingerprint persistence with TTL
- Severity-based drift classification
- Foundation for Phase 4 auto-repair workflows

Usage:
    drift_detector = DriftDetector(redis_client)
    drift_event = drift_detector.detect_drift(entity_event)
    if drift_event:
        logger.warning(f"Schema drift detected: {drift_event.severity}")
"""

import logging
import json
import os
import uuid
from typing import Optional
from datetime import datetime
from pathlib import Path
import sys

import redis

current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

from app.contracts.canonical_event import (
    EntityEvent,
    DriftEvent,
    SchemaFingerprint
)

logger = logging.getLogger(__name__)


class DriftDetector:
    """
    Detects schema drift by comparing current and historical schema fingerprints.
    
    The DriftDetector stores schema fingerprints in Redis and compares them
    on each ingestion to detect:
    - Added fields (medium severity)
    - Removed fields (critical severity - data loss risk)
    - Combined changes (high severity - breaking change)
    
    Redis Key Pattern:
        drift:fingerprint:{tenant_id}:{connector}:{entity_type}
    
    TTL:
        Configurable via DRIFT_FINGERPRINT_TTL env var (default: 30 days)
    """
    
    DEFAULT_TTL_SECONDS = 2592000
    
    def __init__(self, redis_client: redis.Redis):
        """
        Initialize the DriftDetector.
        
        Args:
            redis_client: Redis client for fingerprint storage
        """
        self.redis_client = redis_client
        self.ttl_seconds = int(os.getenv('DRIFT_FINGERPRINT_TTL', self.DEFAULT_TTL_SECONDS))
        logger.info(f"DriftDetector initialized with TTL={self.ttl_seconds}s")
    
    def detect_drift(self, event: EntityEvent) -> Optional[DriftEvent]:
        """
        Main drift detection method.
        
        Compares the current schema fingerprint with the historical fingerprint
        stored in Redis. If no historical fingerprint exists, stores the current
        one as the baseline.
        
        Args:
            event: EntityEvent with schema fingerprint
            
        Returns:
            DriftEvent if drift detected, None otherwise
        """
        if not event.schema_fingerprint:
            logger.warning(f"Event {event.event_id} missing schema fingerprint - skipping drift detection")
            return None
        
        redis_key = self._build_redis_key(
            event.tenant_id,
            event.connector_name,
            event.entity_type
        )
        
        logger.debug(f"Checking drift for key: {redis_key}")
        
        historical_fingerprint = self._get_historical_fingerprint(redis_key)
        
        if not historical_fingerprint:
            logger.info(
                f"No historical fingerprint for {event.connector_name}.{event.entity_type} "
                f"(tenant: {event.tenant_id}) - storing baseline"
            )
            self._store_fingerprint(redis_key, event.schema_fingerprint)
            return None
        
        drift_event = self._compare_fingerprints(
            current=event.schema_fingerprint,
            historical=historical_fingerprint,
            event=event
        )
        
        if drift_event:
            logger.warning(
                f"⚠️ Schema drift detected: {drift_event.severity} - "
                f"{drift_event.changes.get('summary', 'unknown changes')}"
            )
            
            self._store_fingerprint(redis_key, event.schema_fingerprint)
        
        return drift_event
    
    def _get_historical_fingerprint(self, key: str) -> Optional[SchemaFingerprint]:
        """
        Retrieve historical fingerprint from Redis.
        
        Args:
            key: Redis key for fingerprint
            
        Returns:
            SchemaFingerprint if found, None otherwise
        """
        try:
            fingerprint_json = self.redis_client.get(key)
            
            if not fingerprint_json:
                return None
            
            # Ensure proper string type for json.loads
            if isinstance(fingerprint_json, bytes):
                fingerprint_json = fingerprint_json.decode('utf-8')
            elif not isinstance(fingerprint_json, str):
                fingerprint_json = str(fingerprint_json)
            
            fingerprint_data = json.loads(fingerprint_json)
            
            if 'generated_at' in fingerprint_data and isinstance(fingerprint_data['generated_at'], str):
                fingerprint_data['generated_at'] = datetime.fromisoformat(
                    fingerprint_data['generated_at'].replace('Z', '+00:00')
                )
            
            return SchemaFingerprint(**fingerprint_data)
            
        except Exception as e:
            logger.error(f"Error retrieving fingerprint from Redis key {key}: {e}", exc_info=True)
            return None
    
    def _store_fingerprint(self, key: str, fingerprint: SchemaFingerprint) -> None:
        """
        Store fingerprint in Redis with TTL.
        
        Args:
            key: Redis key for fingerprint
            fingerprint: SchemaFingerprint to store
        """
        try:
            fingerprint_dict = fingerprint.model_dump()
            
            if 'generated_at' in fingerprint_dict and isinstance(fingerprint_dict['generated_at'], datetime):
                fingerprint_dict['generated_at'] = fingerprint_dict['generated_at'].isoformat()
            
            fingerprint_json = json.dumps(fingerprint_dict)
            
            self.redis_client.setex(key, self.ttl_seconds, fingerprint_json)
            
            logger.debug(f"Stored fingerprint in Redis: {key} (TTL={self.ttl_seconds}s)")
            
        except Exception as e:
            logger.error(f"Error storing fingerprint to Redis key {key}: {e}", exc_info=True)
    
    def _compare_fingerprints(
        self,
        current: SchemaFingerprint,
        historical: SchemaFingerprint,
        event: EntityEvent
    ) -> Optional[DriftEvent]:
        """
        Compare current and historical fingerprints to detect drift.
        
        Detects:
        - Field count changes
        - Added fields
        - Removed fields
        
        Args:
            current: Current schema fingerprint
            historical: Historical schema fingerprint
            event: EntityEvent for context
            
        Returns:
            DriftEvent if changes detected, None otherwise
        """
        current_fields = set(current.field_names)
        historical_fields = set(historical.field_names)
        
        if current_fields == historical_fields and current.field_count == historical.field_count:
            logger.debug("No schema drift detected - fingerprints match")
            return None
        
        added_fields = list(current_fields - historical_fields)
        removed_fields = list(historical_fields - current_fields)
        field_count_delta = current.field_count - historical.field_count
        
        changes = {
            "added_fields": added_fields,
            "removed_fields": removed_fields,
            "field_count_delta": field_count_delta,
            "summary": self._generate_change_summary(added_fields, removed_fields, field_count_delta)
        }
        
        drift_event = DriftEvent(
            event_id=f"drift-{uuid.uuid4()}",
            drift_type="schema_change",
            severity="pending",
            connector_name=event.connector_name,
            entity_type=event.entity_type,
            tenant_id=event.tenant_id,
            detected_at=datetime.utcnow(),
            changes=changes,
            previous_fingerprint=historical,
            current_fingerprint=current,
            requires_repair=len(removed_fields) > 0 or len(added_fields) > 0,
            metadata={
                "event_id": event.event_id,
                "connector_id": event.connector_id,
                "previous_hash": historical.fingerprint_hash,
                "current_hash": current.fingerprint_hash
            }
        )
        
        drift_event.severity = self._calculate_drift_severity(drift_event)
        
        return drift_event
    
    def _calculate_drift_severity(self, drift_event: DriftEvent) -> str:
        """
        Calculate drift severity based on change type.
        
        Severity Levels:
        - critical: Removed fields (data loss risk)
        - high: Added AND removed fields (breaking change)
        - medium: Added fields only (non-breaking change)
        - low: No field changes, just metadata updates
        
        Args:
            drift_event: DriftEvent with changes
            
        Returns:
            Severity level: "low", "medium", "high", or "critical"
        """
        changes = drift_event.changes
        added_fields = changes.get("added_fields", [])
        removed_fields = changes.get("removed_fields", [])
        
        if len(removed_fields) > 0:
            if len(added_fields) > 0:
                return "high"
            return "critical"
        
        if len(added_fields) > 0:
            return "medium"
        
        return "low"
    
    def _build_redis_key(self, tenant_id: str, connector: str, entity_type: str) -> str:
        """
        Build Redis key for fingerprint storage.
        
        Args:
            tenant_id: Tenant identifier
            connector: Connector name
            entity_type: Entity type
            
        Returns:
            Redis key string
        """
        return f"drift:fingerprint:{tenant_id}:{connector}:{entity_type}"
    
    def _generate_change_summary(
        self,
        added_fields: list,
        removed_fields: list,
        field_count_delta: int
    ) -> str:
        """
        Generate human-readable summary of changes.
        
        Args:
            added_fields: List of added field names
            removed_fields: List of removed field names
            field_count_delta: Change in field count
            
        Returns:
            Summary string
        """
        parts = []
        
        if added_fields:
            parts.append(f"{len(added_fields)} field(s) added: {', '.join(added_fields[:5])}")
            if len(added_fields) > 5:
                parts[-1] += f" (+{len(added_fields) - 5} more)"
        
        if removed_fields:
            parts.append(f"{len(removed_fields)} field(s) removed: {', '.join(removed_fields[:5])}")
            if len(removed_fields) > 5:
                parts[-1] += f" (+{len(removed_fields) - 5} more)"
        
        if not parts:
            parts.append(f"Field count changed by {field_count_delta}")
        
        return "; ".join(parts)


if __name__ == "__main__":
    from app.contracts.canonical_event import (
        EventType,
        CanonicalEntityType,
        FieldMapping
    )
    
    redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
    
    fingerprint_v1 = SchemaFingerprint(
        fingerprint_hash="hash-v1",
        field_count=3,
        field_names=["id", "name", "amount"],
        schema_version="v1.0",
        connector_name="test",
        entity_type="opportunity"
    )
    
    fingerprint_v2 = SchemaFingerprint(
        fingerprint_hash="hash-v2",
        field_count=4,
        field_names=["id", "name", "amount", "stage"],
        schema_version="v2.0",
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
    
    event_v1 = EntityEvent(
        event_id="test-001",
        event_type=EventType.ENTITY_CREATED,
        connector_name="test",
        connector_id="test-conn-001",
        entity_type=CanonicalEntityType.OPPORTUNITY,
        entity_id="TEST-001",
        tenant_id="tenant-test",
        schema_fingerprint=fingerprint_v1,
        payload={"id": "1", "name": "Test", "amount": 100},
        field_mappings=[field_mapping],
        overall_confidence=0.85
    )
    
    event_v2 = EntityEvent(
        event_id="test-002",
        event_type=EventType.ENTITY_CREATED,
        connector_name="test",
        connector_id="test-conn-001",
        entity_type=CanonicalEntityType.OPPORTUNITY,
        entity_id="TEST-002",
        tenant_id="tenant-test",
        schema_fingerprint=fingerprint_v2,
        payload={"id": "2", "name": "Test 2", "amount": 200, "stage": "Open"},
        field_mappings=[field_mapping],
        overall_confidence=0.85
    )
    
    detector = DriftDetector(redis_client)
    
    print("Testing Drift Detection:")
    print("=" * 60)
    
    print("\n1. First ingestion (baseline):")
    drift1 = detector.detect_drift(event_v1)
    print(f"   Drift detected: {drift1 is not None}")
    
    print("\n2. Second ingestion (with schema change):")
    drift2 = detector.detect_drift(event_v2)
    if drift2:
        print(f"   ✅ Drift detected!")
        print(f"   Severity: {drift2.severity}")
        print(f"   Changes: {drift2.changes['summary']}")
    else:
        print("   ❌ No drift detected")
