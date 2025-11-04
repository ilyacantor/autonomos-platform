"""
Example Usage: AAM DCL Output Adapter

This example demonstrates how to use the DCL Output Adapter to transform
AAM canonical events and publish them to Redis Streams for DCL consumption.
"""

import redis
import logging
from datetime import datetime
from typing import List

from dcl_output_adapter import publish_to_dcl_stream

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SampleCanonicalEvent:
    """Sample canonical event structure for demonstration"""
    
    def __init__(self, event_id, entity_type, payload, connector_name="salesforce"):
        self.event_id = event_id
        self.entity_type = entity_type
        self.payload = payload
        self.connector_name = connector_name
        self.timestamp = datetime.utcnow()
        
        self.schema_fingerprint = type('obj', (object,), {
            'fingerprint_hash': 'sample_fingerprint_hash_123'
        })()


def example_basic_usage():
    """
    Example 1: Basic usage with a small batch of events
    """
    print("\n" + "=" * 60)
    print("Example 1: Basic Usage")
    print("=" * 60)
    
    redis_client = redis.Redis.from_url("redis://localhost:6379", decode_responses=False)
    
    events = [
        SampleCanonicalEvent(
            event_id="sf-opp-001",
            entity_type="opportunity",
            payload={
                "id": "SF-OPP-001",
                "name": "Enterprise Deal",
                "amount": 100000.0,
                "stage": "Proposal",
                "close_date": "2025-12-31"
            }
        ),
        SampleCanonicalEvent(
            event_id="sf-opp-002",
            entity_type="opportunity",
            payload={
                "id": "SF-OPP-002",
                "name": "SMB Deal",
                "amount": 25000.0,
                "stage": "Negotiation",
                "close_date": "2025-11-30"
            }
        ),
    ]
    
    result = publish_to_dcl_stream(
        tenant_id="demo-tenant",
        connector_type="salesforce",
        canonical_events=events,
        redis_client=redis_client,
        connector_config_id="sf-prod-config-001"
    )
    
    print(f"Success: {result['success']}")
    print(f"Stream Key: {result['stream_key']}")
    print(f"Batches Published: {result['batches_published']}")
    print(f"Total Records: {result['total_records']}")
    print(f"Batch IDs: {result['batch_ids']}")
    
    if result['errors']:
        print(f"Errors: {result['errors']}")


def example_large_batch():
    """
    Example 2: Large batch with automatic chunking
    """
    print("\n" + "=" * 60)
    print("Example 2: Large Batch with Chunking")
    print("=" * 60)
    
    redis_client = redis.Redis.from_url("redis://localhost:6379", decode_responses=False)
    
    events = []
    for i in range(500):
        events.append(SampleCanonicalEvent(
            event_id=f"sf-opp-{i:04d}",
            entity_type="opportunity",
            payload={
                "id": f"SF-OPP-{i:04d}",
                "name": f"Deal #{i}",
                "amount": 10000.0 + (i * 1000),
                "stage": "Prospecting" if i % 3 == 0 else "Proposal",
                "close_date": "2025-12-31"
            }
        ))
    
    result = publish_to_dcl_stream(
        tenant_id="demo-tenant",
        connector_type="salesforce",
        canonical_events=events,
        redis_client=redis_client
    )
    
    print(f"Success: {result['success']}")
    print(f"Total Records: {result['total_records']}")
    print(f"Batches Created: {result['batches_published']}")
    print(f"Batch IDs: {result['batch_ids'][:3]}... (showing first 3)")


def example_multiple_entities():
    """
    Example 3: Multiple entity types (opportunities, accounts, contacts)
    """
    print("\n" + "=" * 60)
    print("Example 3: Multiple Entity Types")
    print("=" * 60)
    
    redis_client = redis.Redis.from_url("redis://localhost:6379", decode_responses=False)
    
    events = [
        SampleCanonicalEvent(
            event_id="sf-opp-001",
            entity_type="opportunity",
            payload={"name": "Enterprise Deal", "amount": 100000.0}
        ),
        SampleCanonicalEvent(
            event_id="sf-acc-001",
            entity_type="account",
            payload={"name": "Acme Corp", "industry": "Technology"}
        ),
        SampleCanonicalEvent(
            event_id="sf-con-001",
            entity_type="contact",
            payload={"name": "John Doe", "email": "john@acme.com"}
        ),
        SampleCanonicalEvent(
            event_id="sf-opp-002",
            entity_type="opportunity",
            payload={"name": "SMB Deal", "amount": 25000.0}
        ),
    ]
    
    result = publish_to_dcl_stream(
        tenant_id="demo-tenant",
        connector_type="salesforce",
        canonical_events=events,
        redis_client=redis_client
    )
    
    print(f"Success: {result['success']}")
    print(f"Total Records: {result['total_records']}")
    print(f"Stream: {result['stream_key']}")


def example_multi_tenant():
    """
    Example 4: Multi-tenant isolation
    """
    print("\n" + "=" * 60)
    print("Example 4: Multi-Tenant Isolation")
    print("=" * 60)
    
    redis_client = redis.Redis.from_url("redis://localhost:6379", decode_responses=False)
    
    tenants = ["tenant-A", "tenant-B", "tenant-C"]
    
    for tenant_id in tenants:
        events = [
            SampleCanonicalEvent(
                event_id=f"{tenant_id}-opp-001",
                entity_type="opportunity",
                payload={"name": f"Deal for {tenant_id}", "amount": 50000.0}
            ),
        ]
        
        result = publish_to_dcl_stream(
            tenant_id=tenant_id,
            connector_type="salesforce",
            canonical_events=events,
            redis_client=redis_client
        )
        
        print(f"Tenant: {tenant_id} -> Stream: {result['stream_key']}")


def example_reading_from_stream():
    """
    Example 5: Reading DCL batches from Redis Stream
    """
    print("\n" + "=" * 60)
    print("Example 5: Reading from Stream")
    print("=" * 60)
    
    redis_client = redis.Redis.from_url("redis://localhost:6379", decode_responses=True)
    
    stream_key = "aam:dcl:demo-tenant:salesforce"
    
    try:
        messages = redis_client.xread({stream_key: '0'}, count=5)
        
        if not messages:
            print(f"No messages found in stream: {stream_key}")
            return
        
        for stream, msgs in messages:
            print(f"\nStream: {stream}")
            for msg_id, fields in msgs:
                print(f"  Message ID: {msg_id}")
                
                import json
                payload = json.loads(fields['payload'])
                
                print(f"  Batch ID: {payload['batch_id']}")
                print(f"  Record Count: {payload['record_count']}")
                print(f"  Tables: {list(payload['tables'].keys())}")
                
                for table_name, table_data in payload['tables'].items():
                    print(f"    - {table_name}: {table_data['record_count']} records")
                    print(f"      Schema: {list(table_data['schema'].keys())}")
                
    except Exception as e:
        logger.error(f"Error reading from stream: {e}")


def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("AAM DCL Output Adapter - Usage Examples")
    print("=" * 60)
    
    try:
        redis_client = redis.Redis.from_url("redis://localhost:6379")
        redis_client.ping()
        print("✓ Redis connection successful")
    except Exception as e:
        print(f"✗ Redis connection failed: {e}")
        print("\nPlease ensure Redis is running on localhost:6379")
        return
    
    print("\nRunning examples...\n")
    
    try:
        example_basic_usage()
        example_large_batch()
        example_multiple_entities()
        example_multi_tenant()
        example_reading_from_stream()
        
        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        logger.error(f"Example failed: {e}", exc_info=True)


if __name__ == "__main__":
    main()
