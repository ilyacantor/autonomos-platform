#!/usr/bin/env python3
"""
Quick AAM Test Data Seed
Populates Redis Streams with minimal canonical events for DCL graph testing
"""
import json
import uuid
import redis
import os
from datetime import datetime

def seed_aam_streams():
    """Populate AAM Redis Streams with test canonical events"""
    
    # Connect to Redis
    redis_url = os.getenv('REDIS_URL')
    if not redis_url:
        print("❌ REDIS_URL not set")
        return
    
    r = redis.from_url(redis_url, decode_responses=True)
    tenant_id = 'default'
    
    # Define minimal test data for each connector
    connectors_data = {
        'salesforce': {
            'Account': {
                'schema': {'Id': 'string', 'Name': 'string', 'Industry': 'string'},
                'samples': [
                    {'Id': 'ACC001', 'Name': 'Acme Corp', 'Industry': 'Technology'},
                    {'Id': 'ACC002', 'Name': 'Global Solutions', 'Industry': 'Finance'}
                ]
            },
            'Opportunity': {
                'schema': {'Id': 'string', 'AccountId': 'string', 'Amount': 'number', 'Stage': 'string'},
                'samples': [
                    {'Id': 'OPP001', 'AccountId': 'ACC001', 'Amount': 50000, 'Stage': 'Closed Won'},
                    {'Id': 'OPP002', 'AccountId': 'ACC002', 'Amount': 75000, 'Stage': 'Negotiation'}
                ]
            }
        },
        'supabase': {
            'users': {
                'schema': {'id': 'string', 'email': 'string', 'created_at': 'timestamp'},
                'samples': [
                    {'id': 'user_001', 'email': 'alice@example.com', 'created_at': '2025-01-01T00:00:00Z'},
                    {'id': 'user_002', 'email': 'bob@example.com', 'created_at': '2025-01-02T00:00:00Z'}
                ]
            }
        },
        'mongodb': {
            'orders': {
                'schema': {'_id': 'string', 'user_id': 'string', 'total': 'number', 'status': 'string'},
                'samples': [
                    {'_id': 'order_001', 'user_id': 'user_001', 'total': 299, 'status': 'completed'},
                    {'_id': 'order_002', 'user_id': 'user_002', 'total': 450, 'status': 'pending'}
                ]
            }
        },
        'filesource': {
            'invoices': {
                'schema': {'invoice_id': 'string', 'customer_id': 'string', 'amount': 'number'},
                'samples': [
                    {'invoice_id': 'INV001', 'customer_id': 'CUST001', 'amount': 1200},
                    {'invoice_id': 'INV002', 'customer_id': 'CUST002', 'amount': 850}
                ]
            }
        }
    }
    
    total_events = 0
    
    for connector_type, tables in connectors_data.items():
        stream_key = f'aam:dcl:{tenant_id}:{connector_type}'
        
        # Create canonical event payload
        payload = {
            'batch_id': str(uuid.uuid4()),
            'timestamp': datetime.utcnow().isoformat(),
            'source_system': connector_type,
            'tenant_id': tenant_id,
            'tables': tables
        }
        
        # Publish to Redis Stream
        message_id = r.xadd(stream_key, {'payload': json.dumps(payload)})
        total_events += 1
        
        print(f"✅ {connector_type}: Published {len(tables)} tables to {stream_key}")
        print(f"   Message ID: {message_id}")
    
    print(f"\n🎉 Successfully seeded {total_events} canonical events across {len(connectors_data)} AAM connectors")
    print(f"\n📊 Stream summary:")
    
    for connector_type in connectors_data.keys():
        stream_key = f'aam:dcl:{tenant_id}:{connector_type}'
        info = r.xinfo_stream(stream_key)
        print(f"  {stream_key}: {info.get('length', 0)} messages")

if __name__ == '__main__':
    seed_aam_streams()
