"""
Tenant-isolated Worker Pools

Features:
- Per-tenant RQ queues
- Resource isolation
- Queue statistics
"""

import logging
from typing import Dict, Optional
from rq import Queue
from redis import Redis

logger = logging.getLogger(__name__)


class TenantWorkerPool:
    """
    Manages per-tenant worker queues for resource isolation
    """
    
    def __init__(self, redis_client: Optional[Redis] = None):
        from shared.redis_client import get_redis_client
        self.redis_client = redis_client or get_redis_client()
        
        if not self.redis_client:
            raise RuntimeError("Redis is required for worker pools")
        
        self._queues: Dict[str, Queue] = {}
        logger.info("TenantWorkerPool initialized")
    
    def get_queue(self, tenant_id: str) -> Queue:
        """
        Get or create a queue for a specific tenant
        
        Args:
            tenant_id: Tenant identifier
        
        Returns:
            RQ Queue instance for the tenant
        """
        if tenant_id not in self._queues:
            queue_name = f"tenant:{tenant_id}:mappings"
            self._queues[tenant_id] = Queue(
                name=queue_name,
                connection=self.redis_client
            )
            logger.info(f"Created queue for tenant {tenant_id}: {queue_name}")
        
        return self._queues[tenant_id]
    
    def get_queue_stats(self, tenant_id: str) -> Dict:
        """
        Get statistics for a tenant's queue
        
        Args:
            tenant_id: Tenant identifier
        
        Returns:
            Dictionary with queue statistics
        """
        queue = self.get_queue(tenant_id)
        
        try:
            stats = {
                'tenant_id': tenant_id,
                'queue_name': queue.name,
                'queued_jobs': len(queue),
                'started_jobs': queue.started_job_registry.count,
                'finished_jobs': queue.finished_job_registry.count,
                'failed_jobs': queue.failed_job_registry.count,
                'deferred_jobs': queue.deferred_job_registry.count,
                'scheduled_jobs': queue.scheduled_job_registry.count
            }
            
            return stats
        
        except Exception as e:
            logger.error(f"Failed to get queue stats for tenant {tenant_id}: {e}")
            return {
                'tenant_id': tenant_id,
                'error': str(e)
            }
    
    def clear_queue(self, tenant_id: str):
        """
        Clear all jobs from a tenant's queue
        
        Args:
            tenant_id: Tenant identifier
        """
        queue = self.get_queue(tenant_id)
        
        try:
            queue.empty()
            logger.info(f"Cleared queue for tenant {tenant_id}")
        except Exception as e:
            logger.error(f"Failed to clear queue for tenant {tenant_id}: {e}")
            raise
    
    def get_all_tenant_stats(self) -> list:
        """
        Get statistics for all tenant queues
        
        Returns:
            List of queue statistics dictionaries
        """
        return [
            self.get_queue_stats(tenant_id)
            for tenant_id in self._queues.keys()
        ]
