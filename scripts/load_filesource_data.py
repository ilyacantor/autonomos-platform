#!/usr/bin/env python3
"""
Load FileSource CSV data into canonical_streams table AND Redis streams

This script invokes FileSourceConnector.replay_entity() to load AWS resources 
and cost reports CSVs for FinOps Pilot. Events are published to both database 
and Redis streams for AAM/DCL consumption.
"""
import sys
import logging
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from services.aam.connectors.filesource.connector import FileSourceConnector
from redis import Redis
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_redis_client() -> Redis:
    """Get Redis client from environment configuration"""
    redis_url = os.getenv("REDIS_URL")
    
    if redis_url:
        # Fix for Upstash Redis: Change redis:// to rediss:// to enable TLS/SSL
        # Upstash requires TLS connections, and rediss:// protocol enables this
        if redis_url.startswith("redis://") and "upstash" in redis_url:
            redis_url = "rediss://" + redis_url[8:]
            logger.info("🔒 Using TLS/SSL for Redis connection (rediss:// protocol)")
        else:
            logger.info(f"Using external Redis from REDIS_URL")
        
        # Don't use decode_responses for stream operations - it causes connection issues
        return Redis.from_url(redis_url, decode_responses=False)
    else:
        # Fallback to local Redis
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        redis_db = int(os.getenv("REDIS_DB", 0))
        logger.info(f"Using local Redis at {redis_host}:{redis_port}/{redis_db}")
        return Redis(host=redis_host, port=redis_port, db=redis_db, decode_responses=False)


def main():
    """Load FileSource AWS cost data for FinOps Pilot"""
    logger.info("Starting FileSource AWS cost data load (database + Redis streams)...")
    
    db = SessionLocal()
    redis_client = None
    
    try:
        # Get Redis client for stream publishing
        redis_client = get_redis_client()
        logger.info("✅ Connected to Redis")
        
        # Use existing default-tenant UUID from tenants table for database writes
        # FileSourceConnector will handle tenant ID mapping for Redis streams
        connector = FileSourceConnector(
            db=db, 
            tenant_id="167e5129-295e-4433-b65e-b8b4d41ffc76",  # UUID for database
            redis_client=redis_client
        )
        
        # Load only AWS entities for FinOps
        logger.info("=" * 80)
        logger.info("Loading aws_resources data...")
        stats_resources = connector.replay_entity(entity="aws_resources", system="filesource")
        
        logger.info("=" * 80)
        logger.info("Loading cost_reports data...")
        stats_costs = connector.replay_entity(entity="cost_reports", system="filesource")
        
        total_records = stats_resources['total_records'] + stats_costs['total_records']
        total_files = stats_resources['files_processed'] + stats_costs['files_processed']
        
        logger.info("=" * 80)
        logger.info(f"✅ FileSource AWS cost data loaded successfully!")
        logger.info(f"   Files processed: {total_files}")
        logger.info(f"   Total records: {total_records}")
        logger.info(f"   AWS Resources: {stats_resources['total_records']}")
        logger.info(f"   Cost Reports: {stats_costs['total_records']}")
        
        # Display Redis publishing results
        logger.info("")
        logger.info("📡 Redis Publishing Results:")
        logger.info("-" * 80)
        
        for entity_name, stats in [("aws_resources", stats_resources), ("cost_reports", stats_costs)]:
            redis_publish = stats.get('redis_publish')
            if redis_publish:
                if redis_publish.get('success'):
                    logger.info(f"✅ {entity_name}:")
                    logger.info(f"   Stream Key: {redis_publish.get('stream_key')}")
                    logger.info(f"   Batches Published: {redis_publish.get('batches_published')}")
                    logger.info(f"   Records Published: {redis_publish.get('total_records')}")
                    logger.info(f"   Batch IDs: {redis_publish.get('batch_ids')}")
                else:
                    logger.error(f"❌ {entity_name}: Publishing failed")
                    logger.error(f"   Errors: {redis_publish.get('errors', redis_publish.get('error'))}")
            else:
                logger.warning(f"⚠️  {entity_name}: No Redis publishing (client not configured)")
        
        logger.info("=" * 80)
        
        return 0
    
    except Exception as e:
        logger.error(f"❌ Failed to load FileSource data: {e}", exc_info=True)
        return 1
    
    finally:
        db.close()
        if redis_client:
            redis_client.close()
            logger.info("Redis connection closed")


if __name__ == "__main__":
    sys.exit(main())
