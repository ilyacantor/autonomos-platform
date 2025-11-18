"""
Shared Job Enqueue Logic

Single source of truth for enqueuing bulk mapping jobs.
Used by production API and benchmark scripts.
"""

import logging
import os
import ssl as ssl_module
from typing import Dict, Optional, List
from uuid import uuid4
from redis import Redis
from rq import Queue, Retry
from services.mapping_intelligence.job_state import BulkMappingJobState
from services.mapping_intelligence.worker_pools import TenantWorkerPool

logger = logging.getLogger(__name__)


def get_rq_redis_connection() -> Optional[Redis]:
    """
    Get Redis connection for RQ workers
    
    Returns:
        Redis connection instance configured for RQ, or None if unavailable
    """
    REDIS_URL = os.getenv("REDIS_URL")
    
    if REDIS_URL:
        if REDIS_URL.startswith("rediss://"):
            CA_CERT_PATH = os.path.join(
                os.path.dirname(__file__), 
                "..", 
                "..", 
                "certs", 
                "redis_ca.pem"
            )
            
            if os.path.exists(CA_CERT_PATH):
                redis_conn = Redis.from_url(
                    REDIS_URL,
                    decode_responses=False,
                    ssl_cert_reqs=ssl_module.CERT_REQUIRED,
                    ssl_ca_certs=CA_CERT_PATH
                )
                logger.info("Using external Redis with TLS/SSL")
            else:
                logger.warning(f"CA cert not found at {CA_CERT_PATH}, using default SSL")
                redis_conn = Redis.from_url(REDIS_URL, decode_responses=False)
        else:
            redis_conn = Redis.from_url(REDIS_URL, decode_responses=False)
            logger.info("Using Redis without TLS")
    else:
        from app.config import settings
        redis_conn = Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=False
        )
        logger.info(f"Using local Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}")
    
    return redis_conn


def enqueue_bulk_mapping_job(
    tenant_id: str,
    connector_definition_ids: List[str],
    options: Optional[Dict] = None,
    use_tenant_pool: bool = True
) -> Dict:
    """
    Enqueue a bulk mapping generation job
    
    Args:
        tenant_id: Tenant identifier
        connector_definition_ids: List of connector definition IDs to process
        options: Optional job configuration
        use_tenant_pool: If True, use tenant-specific worker pool
    
    Returns:
        Dictionary with job information (job_id, status, etc.)
    """
    from shared.redis_client import get_redis_client
    
    redis_client = get_redis_client()
    if not redis_client:
        raise RuntimeError("Redis is not available")
    
    job_state = BulkMappingJobState(redis_client)
    
    if not job_state.try_reserve_job_slot(tenant_id):
        from services.mapping_intelligence.job_state import MAX_CONCURRENT_JOBS_PER_TENANT
        return {
            'status': 'rejected',
            'error': f'Maximum concurrent jobs ({MAX_CONCURRENT_JOBS_PER_TENANT}) reached for tenant',
            'tenant_id': tenant_id
        }
    
    job_id = str(uuid4())
    
    initial_state = {
        'job_id': job_id,
        'tenant_id': tenant_id,
        'status': 'pending',
        'connector_definition_ids': connector_definition_ids,
        'options': options or {},
        'created_at': None,
        'started_at': None,
        'completed_at': None,
        'processed_fields': 0,
        'total_fields': 0,
        'successful_mappings': 0
    }
    
    from datetime import datetime
    initial_state['created_at'] = datetime.utcnow().isoformat()
    
    job_state.save_job_state(tenant_id, job_id, initial_state)
    
    try:
        rq_redis = get_rq_redis_connection()
        if not rq_redis:
            raise RuntimeError("RQ Redis connection is not available")
        
        if use_tenant_pool:
            worker_pool = TenantWorkerPool(rq_redis)
            queue = worker_pool.get_queue(tenant_id)
        else:
            queue = Queue('default', connection=rq_redis)
        
        from services.mapping_intelligence.job_workers import sync_generate_bulk_mappings_job
        
        retry_config = Retry(max=3, interval=[10, 30, 60])
        
        rq_job = queue.enqueue(
            sync_generate_bulk_mappings_job,
            job_id,
            tenant_id,
            connector_definition_ids,
            options,
            job_timeout='10m',
            retry=retry_config,
            job_id=job_id
        )
        
        logger.info(
            f"Enqueued bulk mapping job {job_id} for tenant {tenant_id} "
            f"with {len(connector_definition_ids)} connectors"
        )
        
        return {
            'status': 'queued',
            'job_id': job_id,
            'tenant_id': tenant_id,
            'rq_job_id': rq_job.id,
            'connector_count': len(connector_definition_ids),
            'queue_name': queue.name
        }
    
    except Exception as e:
        logger.error(f"Failed to enqueue job: {e}", exc_info=True)
        
        job_state.set_error(tenant_id, job_id, f"Failed to enqueue: {str(e)}")
        
        raise


def get_job_status(tenant_id: str, job_id: str) -> Optional[Dict]:
    """
    Get status of a bulk mapping job
    
    Args:
        tenant_id: Tenant identifier
        job_id: Job identifier
    
    Returns:
        Job status dictionary or None if not found
    """
    from shared.redis_client import get_redis_client
    
    redis_client = get_redis_client()
    if not redis_client:
        return None
    
    job_state = BulkMappingJobState(redis_client)
    return job_state.get_job_state(tenant_id, job_id)
