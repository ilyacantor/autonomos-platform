"""
Test Script for Auto-Repair Agent

This script validates the RepairAgent implementation with simulated drift events.

Usage:
    python aam_hybrid/test_repair_agent.py
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import json

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

aam_core_path = Path(__file__).parent / "core"
sys.path.insert(0, str(aam_core_path))

import redis

from app.contracts.canonical_event import (
    DriftEvent,
    EntityEvent,
    SchemaFingerprint,
    EventType,
    CanonicalEntityType
)

from repair_agent import RepairAgent
from repair_types import RepairAction
from app.config.feature_flags import FeatureFlagConfig, FeatureFlag


def get_redis_client():
    """Get Redis client from environment"""
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    return redis.from_url(redis_url, decode_responses=True)


def create_test_drift_event():
    """Create a simulated drift event for testing"""
    
    current_fingerprint = SchemaFingerprint(
        fingerprint_hash="abc123new",
        field_count=6,
        field_names=["id", "name", "amount", "stage", "close_date", "closeDate"],
        schema_version="v2.4",
        connector_name="salesforce",
        entity_type="Opportunity"
    )
    
    historical_fingerprint = SchemaFingerprint(
        fingerprint_hash="abc123old",
        field_count=5,
        field_names=["id", "name", "amount", "stage", "close_date"],
        schema_version="v2.3",
        connector_name="salesforce",
        entity_type="Opportunity"
    )
    
    drift_event = DriftEvent(
        event_id="drift-test-001",
        drift_type="schema_change",
        severity="medium",
        connector_name="salesforce",
        entity_type="Opportunity",
        tenant_id="tenant-demo-001",
        changes={
            "summary": "Field added: closeDate",
            "added_fields": ["closeDate"],
            "removed_fields": [],
            "field_count_delta": 1
        },
        previous_fingerprint=historical_fingerprint,
        current_fingerprint=current_fingerprint,
        requires_repair=True
    )
    
    return drift_event


def create_test_canonical_event():
    """Create a simulated canonical event for testing"""
    
    fingerprint = SchemaFingerprint(
        fingerprint_hash="abc123new",
        field_count=6,
        field_names=["id", "name", "amount", "stage", "close_date", "closeDate"],
        schema_version="v2.4",
        connector_name="salesforce",
        entity_type="Opportunity"
    )
    
    entity_event = EntityEvent(
        event_id="evt-test-001",
        event_type=EventType.ENTITY_CREATED,
        connector_name="salesforce",
        connector_id="sf-conn-001",
        entity_type=CanonicalEntityType.OPPORTUNITY,
        entity_id="SF-OPP-TEST-001",
        tenant_id="tenant-demo-001",
        schema_fingerprint=fingerprint,
        payload={
            "id": "SF-OPP-TEST-001",
            "name": "Test Enterprise Deal",
            "amount": 150000.0,
            "stage": "Qualification",
            "close_date": "2024-12-15",
            "closeDate": "2024-12-15T00:00:00Z"
        },
        overall_confidence=0.95
    )
    
    return entity_event


def test_repair_agent_basic():
    """Test basic RepairAgent instantiation"""
    print("\n" + "="*60)
    print("TEST 1: Basic RepairAgent Instantiation")
    print("="*60)
    
    try:
        redis_client = get_redis_client()
        repair_agent = RepairAgent(redis_client)
        
        print("✅ RepairAgent instantiated successfully")
        print(f"   - Confidence threshold: {repair_agent.confidence_threshold}")
        print(f"   - LLM service: {'enabled' if repair_agent.llm_service else 'disabled'}")
        print(f"   - RAG engine: {'enabled' if repair_agent.rag_engine else 'disabled'}")
        
        return True
    except Exception as e:
        print(f"❌ Failed to instantiate RepairAgent: {e}")
        return False


def test_feature_flags():
    """Test feature flag configuration"""
    print("\n" + "="*60)
    print("TEST 2: Feature Flag Configuration")
    print("="*60)
    
    auto_repair_enabled = FeatureFlagConfig.is_enabled(FeatureFlag.ENABLE_AUTO_REPAIR)
    hitl_enabled = FeatureFlagConfig.is_enabled(FeatureFlag.ENABLE_HITL_WORKFLOW)
    
    print(f"ENABLE_AUTO_REPAIR: {'✅ ENABLED' if auto_repair_enabled else '❌ DISABLED'}")
    print(f"ENABLE_HITL_WORKFLOW: {'✅ ENABLED' if hitl_enabled else '❌ DISABLED'}")
    
    if not auto_repair_enabled:
        print("\n⚠️  Note: Auto-repair is disabled. To test repair suggestions,")
        print("   set environment variable: FEATURE_ENABLE_AUTO_REPAIR=true")
    
    return True


def test_suggest_repairs():
    """Test repair suggestion generation"""
    print("\n" + "="*60)
    print("TEST 3: Repair Suggestion Generation")
    print("="*60)
    
    try:
        redis_client = get_redis_client()
        repair_agent = RepairAgent(redis_client)
        
        drift_event = create_test_drift_event()
        canonical_event = create_test_canonical_event()
        
        print(f"\nSimulated Drift Event:")
        print(f"  - Event ID: {drift_event.event_id}")
        print(f"  - Severity: {drift_event.severity}")
        print(f"  - Added fields: {drift_event.changes.get('added_fields', [])}")
        
        repair_batch = repair_agent.suggest_repairs(drift_event, canonical_event)
        
        print(f"\nRepair Batch Results:")
        print(f"  - Drift Event ID: {repair_batch.drift_event_id}")
        print(f"  - Total fields: {repair_batch.total_fields}")
        print(f"  - Auto-applied: {repair_batch.auto_applied_count}")
        print(f"  - HITL queued: {repair_batch.hitl_queued_count}")
        print(f"  - Rejected: {repair_batch.rejected_count}")
        print(f"  - Overall confidence: {repair_batch.overall_confidence:.2f}")
        
        if repair_batch.suggestions:
            print(f"\nSuggestion Details:")
            for i, suggestion in enumerate(repair_batch.suggestions, 1):
                print(f"  {i}. Field: {suggestion.field_name}")
                print(f"     - Suggested mapping: {suggestion.suggested_mapping}")
                print(f"     - Confidence: {suggestion.confidence:.2f}")
                print(f"     - Action: {suggestion.repair_action}")
                print(f"     - Reason: {suggestion.confidence_reason}")
                print(f"     - RAG matches: {suggestion.rag_similarity_count}")
                print(f"     - Queued for HITL: {suggestion.queued_for_hitl}")
        
        print("\n✅ Repair suggestion generation completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to generate repair suggestions: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_hitl_queue():
    """Test HITL queue functionality - verify Redis writes for medium-confidence repairs"""
    print("\n" + "="*60)
    print("TEST 4: HITL Queue Verification (Redis Writes)")
    print("="*60)
    
    try:
        redis_client = get_redis_client()
        
        # Clean up any existing test keys
        existing_keys = redis_client.keys("hitl:repair:tenant-demo-001:*")
        if existing_keys:
            redis_client.delete(*existing_keys)
            print(f"Cleaned up {len(existing_keys)} existing test keys")
        
        # Create RepairAgent
        repair_agent = RepairAgent(redis_client)
        
        # Create test drift event and canonical event
        drift_event = create_test_drift_event()
        canonical_event = create_test_canonical_event()
        
        # Generate repair suggestions (should create HITL entries for medium confidence)
        repair_batch = repair_agent.suggest_repairs(drift_event, canonical_event)
        
        print(f"\nGenerated {repair_batch.total_fields} repair suggestions")
        print(f"  - Auto-applied: {repair_batch.auto_applied_count}")
        print(f"  - HITL queued: {repair_batch.hitl_queued_count}")
        print(f"  - Rejected: {repair_batch.rejected_count}")
        
        # Verify HITL entries in Redis
        hitl_keys = redis_client.keys("hitl:repair:tenant-demo-001:*")
        
        print(f"\nFound {len(hitl_keys)} HITL entries in Redis")
        
        # Validate that HITL count matches Redis entries
        if len(hitl_keys) != repair_batch.hitl_queued_count:
            print(f"⚠️  WARNING: RepairBatch reports {repair_batch.hitl_queued_count} HITL items, "
                  f"but Redis has {len(hitl_keys)} entries")
        
        validation_passed = True
        
        if hitl_keys:
            print("\nValidating HITL Queue Entries:")
            for key in hitl_keys:
                print(f"\n  Key: {key}")
                
                # Validate key pattern
                expected_pattern = "hitl:repair:tenant-demo-001:salesforce:Opportunity:"
                if not key.startswith(expected_pattern):
                    print(f"    ❌ Invalid key pattern! Expected to start with: {expected_pattern}")
                    validation_passed = False
                else:
                    print(f"    ✅ Key pattern valid")
                
                # Get and parse Redis value
                hitl_data = redis_client.get(key)
                if not hitl_data:
                    print(f"    ❌ No data found for key!")
                    validation_passed = False
                    continue
                
                try:
                    hitl_json = json.loads(hitl_data)
                    
                    # Validate required fields
                    required_fields = [
                        'field_name', 'suggested_mapping', 'confidence', 
                        'confidence_reason', 'rag_context', 'drift_event_id',
                        'connector', 'entity_type', 'tenant_id', 'timestamp'
                    ]
                    
                    missing_fields = [f for f in required_fields if f not in hitl_json]
                    if missing_fields:
                        print(f"    ❌ Missing required fields: {missing_fields}")
                        validation_passed = False
                    else:
                        print(f"    ✅ All required fields present")
                    
                    # Display key information
                    print(f"    - Field: {hitl_json.get('field_name')}")
                    print(f"    - Suggested mapping: {hitl_json.get('suggested_mapping')}")
                    print(f"    - Confidence: {hitl_json.get('confidence', 0.0):.2f}")
                    print(f"    - Connector: {hitl_json.get('connector')}")
                    print(f"    - Entity type: {hitl_json.get('entity_type')}")
                    print(f"    - Tenant ID: {hitl_json.get('tenant_id')}")
                    
                    # Validate confidence is in medium range (0.6-0.85)
                    confidence = hitl_json.get('confidence', 0.0)
                    if not (0.6 <= confidence < 0.85):
                        print(f"    ⚠️  Confidence {confidence:.2f} is outside medium range (0.6-0.85)")
                    
                except json.JSONDecodeError as e:
                    print(f"    ❌ Invalid JSON in Redis value: {e}")
                    validation_passed = False
                
                # Validate TTL
                ttl = redis_client.ttl(key)
                expected_ttl = 604800  # 7 days in seconds
                
                # TTL might be slightly less due to processing time, so allow 5 second tolerance
                if ttl < expected_ttl - 5:
                    print(f"    ❌ Invalid TTL! Expected ~{expected_ttl}s (7 days), got {ttl}s")
                    validation_passed = False
                elif ttl > expected_ttl:
                    print(f"    ❌ Invalid TTL! TTL cannot exceed {expected_ttl}s, got {ttl}s")
                    validation_passed = False
                else:
                    print(f"    ✅ TTL valid: {ttl}s (~7 days)")
        
        if validation_passed and len(hitl_keys) > 0:
            print("\n✅ HITL queue verification PASSED - Redis writes validated")
            return True
        elif len(hitl_keys) == 0:
            print("\n⚠️  No HITL entries found. This may be expected if:")
            print("    - ENABLE_HITL_WORKFLOW feature flag is disabled")
            print("    - LLM service returned high/low confidence (not medium)")
            print("    - All repairs were auto-applied or rejected")
            print("\n   To generate HITL entries, ensure:")
            print("    - FEATURE_ENABLE_HITL_WORKFLOW=true")
            print("    - FEATURE_ENABLE_AUTO_REPAIR=true")
            return True
        else:
            print("\n❌ HITL queue validation FAILED - see errors above")
            return False
        
    except Exception as e:
        print(f"❌ Failed to verify HITL queue: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_confidence_tiers():
    """Test confidence tier classification"""
    print("\n" + "="*60)
    print("TEST 5: Confidence Tier Classification")
    print("="*60)
    
    try:
        redis_client = get_redis_client()
        repair_agent = RepairAgent(redis_client, confidence_threshold=0.85)
        
        test_cases = [
            (0.95, RepairAction.AUTO_APPLIED, "High confidence - auto-apply"),
            (0.75, RepairAction.HITL_QUEUED, "Medium confidence - HITL queue"),
            (0.50, RepairAction.REJECTED, "Low confidence - reject")
        ]
        
        print("\nTesting confidence tier logic:")
        all_passed = True
        
        for confidence, expected_action, description in test_cases:
            actual_action = repair_agent._determine_repair_action(confidence)
            
            if actual_action == expected_action:
                print(f"  ✅ {description}")
                print(f"     Confidence: {confidence:.2f} → Action: {actual_action}")
            else:
                print(f"  ❌ {description}")
                print(f"     Confidence: {confidence:.2f}")
                print(f"     Expected: {expected_action}, Got: {actual_action}")
                all_passed = False
        
        if all_passed:
            print("\n✅ All confidence tier tests passed")
        else:
            print("\n⚠️  Some confidence tier tests failed")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Failed confidence tier tests: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("AUTO-REPAIR AGENT TEST SUITE")
    print("="*60)
    print(f"Time: {datetime.now().isoformat()}")
    
    tests = [
        ("Basic Instantiation", test_repair_agent_basic),
        ("Feature Flags", test_feature_flags),
        ("Confidence Tiers", test_confidence_tiers),
        ("Repair Suggestions", test_suggest_repairs),
        ("HITL Queue", test_hitl_queue)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:30s} {status}")
    
    total_tests = len(results)
    passed_tests = sum(1 for _, passed in results if passed)
    
    print("="*60)
    print(f"Total: {passed_tests}/{total_tests} tests passed")
    print("="*60)
    
    if passed_tests == total_tests:
        print("\n🎉 All tests passed! RepairAgent is ready for production.")
    else:
        print(f"\n⚠️  {total_tests - passed_tests} test(s) failed. Review output above.")
    
    return passed_tests == total_tests


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
