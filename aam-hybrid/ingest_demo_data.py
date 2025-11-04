#!/usr/bin/env python3
"""
AAM Demo Data Ingestion Script

This script ingests demo CSV data, generates canonical events,
and publishes them to Redis Streams for DCL consumption.

Usage:
    python ingest_demo_data.py

Environment Variables:
    REDIS_URL - Redis connection URL (default: from main app config)
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add parent paths to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

import redis

from core.data_ingestion import ingest_connector_data

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_redis_client() -> redis.Redis:
    """
    Get Redis client using the main app's configuration.
    
    Returns:
        Redis client instance
    """
    redis_url = os.getenv('REDIS_URL')
    
    if not redis_url:
        logger.error("REDIS_URL environment variable not set")
        raise ValueError("REDIS_URL not configured")
    
    # Convert redis:// to rediss:// for TLS (Upstash Redis)
    if redis_url.startswith('redis://') and 'upstash' in redis_url:
        redis_url = redis_url.replace('redis://', 'rediss://')
        logger.info("Converted to TLS connection for Upstash Redis")
    
    try:
        client = redis.Redis.from_url(
            redis_url,
            decode_responses=False,
            socket_connect_timeout=5,
            socket_keepalive=True
        )
        client.ping()
        logger.info(f"✓ Connected to Redis")
        return client
    except Exception as e:
        logger.error(f"✗ Failed to connect to Redis: {e}")
        raise


async def ingest_all_demo_connectors(tenant_id: str = "demo-tenant"):
    """
    Ingest data from all demo connectors.
    
    Args:
        tenant_id: Tenant ID for multi-tenancy (default: 'demo-tenant')
    """
    logger.info("=" * 70)
    logger.info("AAM Demo Data Ingestion")
    logger.info("=" * 70)
    logger.info(f"Tenant ID: {tenant_id}")
    logger.info("")
    
    redis_client = get_redis_client()
    
    connectors = [
        {'name': 'salesforce', 'id': 'salesforce-demo-001'},
        {'name': 'hubspot', 'id': 'hubspot-demo-001'},
        {'name': 'dynamics', 'id': 'dynamics-demo-001'},
        {'name': 'supabase', 'id': 'supabase-demo-001'},
        {'name': 'mongodb', 'id': 'mongodb-demo-001'},
    ]
    
    total_events = 0
    successful = 0
    failed = 0
    
    for connector in connectors:
        try:
            logger.info(f"\n{'=' * 70}")
            logger.info(f"Ingesting: {connector['name']}")
            logger.info(f"{'=' * 70}")
            
            result = await ingest_connector_data(
                connector_name=connector['name'],
                connector_id=connector['id'],
                tenant_id=tenant_id,
                redis_client=redis_client
            )
            
            if result['success']:
                successful += 1
                events_count = result['total_events']
                total_events += events_count
                
                logger.info(f"✓ {connector['name']}: {events_count} events published")
                
                if 'publish_result' in result:
                    stream_key = result['publish_result'].get('stream_key')
                    batches = result['publish_result'].get('batches_published', 0)
                    logger.info(f"  Stream: {stream_key}")
                    logger.info(f"  Batches: {batches}")
                
                for entity_type, entity_result in result.get('entity_results', {}).items():
                    logger.info(
                        f"  - {entity_type}: {entity_result['events_generated']} events"
                    )
            else:
                failed += 1
                logger.error(f"✗ {connector['name']}: Failed")
                for error in result.get('errors', []):
                    logger.error(f"  Error: {error}")
        
        except Exception as e:
            failed += 1
            logger.error(f"✗ {connector['name']}: Exception - {e}", exc_info=True)
    
    logger.info(f"\n{'=' * 70}")
    logger.info("Ingestion Summary")
    logger.info(f"{'=' * 70}")
    logger.info(f"Total Connectors: {len(connectors)}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Total Events Published: {total_events}")
    logger.info(f"{'=' * 70}\n")
    
    return {
        'total_connectors': len(connectors),
        'successful': successful,
        'failed': failed,
        'total_events': total_events
    }


async def inspect_redis_streams(tenant_id: str = "demo-tenant"):
    """
    Inspect Redis Streams to verify data was published.
    
    Args:
        tenant_id: Tenant ID for multi-tenancy
    """
    logger.info("\n" + "=" * 70)
    logger.info("Redis Streams Inspection")
    logger.info("=" * 70)
    
    redis_client = redis.Redis.from_url(
        os.getenv('REDIS_URL'),
        decode_responses=True
    )
    
    connectors = ['salesforce', 'hubspot', 'dynamics', 'supabase', 'mongodb']
    
    for connector in connectors:
        stream_key = f"aam:dcl:{tenant_id}:{connector}"
        
        try:
            stream_length = redis_client.xlen(stream_key)
            
            if stream_length > 0:
                logger.info(f"✓ {stream_key}: {stream_length} messages")
                
                messages = redis_client.xrevrange(stream_key, count=1)
                if messages:
                    msg_id, fields = messages[0]
                    logger.info(f"  Latest message ID: {msg_id}")
                    
                    import json
                    if 'payload' in fields:
                        payload = json.loads(fields['payload'])
                        logger.info(f"  Batch ID: {payload.get('batch_id')}")
                        logger.info(f"  Record Count: {payload.get('record_count')}")
                        logger.info(f"  Tables: {list(payload.get('tables', {}).keys())}")
            else:
                logger.warning(f"✗ {stream_key}: Empty (0 messages)")
        
        except Exception as e:
            logger.error(f"✗ {stream_key}: Error - {e}")
    
    logger.info("=" * 70 + "\n")


async def main():
    """Main entry point"""
    try:
        tenant_id = os.getenv('TENANT_ID', 'demo-tenant')
        
        result = await ingest_all_demo_connectors(tenant_id=tenant_id)
        
        if result['successful'] > 0:
            logger.info("\n✓ Data ingestion successful!")
            logger.info(f"✓ {result['total_events']} canonical events published to Redis Streams")
            logger.info("\nYou can now enable USE_AAM_AS_SOURCE=true to test the AAM → DCL flow")
            
            await inspect_redis_streams(tenant_id=tenant_id)
        else:
            logger.error("\n✗ Data ingestion failed - no connectors succeeded")
            sys.exit(1)
    
    except Exception as e:
        logger.error(f"✗ Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
