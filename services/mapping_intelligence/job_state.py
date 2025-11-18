"""
Job State Management with Redis
- Track job status (pending/running/completed/failed)
- Tenant-scoped isolation
- Atomic semaphore for concurrent job limits
"""

import json
import redis
from datetime import datetime
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

MAX_CONCURRENT_JOBS_PER_TENANT = 5


class BulkMappingJobState:
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        from shared.redis_client import get_redis_client
        self.redis_client: redis.Redis = redis_client or get_redis_client()
        
        if not self.redis_client:
            raise RuntimeError("Redis client is required for job state management")
    
    def _get_job_key(self, tenant_id: str, job_id: str) -> str:
        return f"job:state:tenant:{tenant_id}:job:{job_id}"
    
    def _get_semaphore_key(self, tenant_id: str) -> str:
        return f"job:semaphore:tenant:{tenant_id}"
    
    def try_reserve_job_slot(self, tenant_id: str) -> bool:
        """Atomic semaphore reservation using INCR"""
        key = self._get_semaphore_key(tenant_id)
        current = int(self.redis_client.incr(key))
        if current > MAX_CONCURRENT_JOBS_PER_TENANT:
            self.redis_client.decr(key)
            logger.warning(f"Tenant {tenant_id} exceeded job limit: {current}/{MAX_CONCURRENT_JOBS_PER_TENANT}")
            return False
        logger.info(f"Reserved job slot for tenant {tenant_id}: {current}/{MAX_CONCURRENT_JOBS_PER_TENANT}")
        return True
    
    def release_job_slot(self, tenant_id: str):
        """Release semaphore slot"""
        key = self._get_semaphore_key(tenant_id)
        current = int(self.redis_client.decr(key))
        if current < 0:
            self.redis_client.set(key, 0)
            logger.warning(f"Semaphore for tenant {tenant_id} went negative, reset to 0")
        else:
            logger.info(f"Released job slot for tenant {tenant_id}: {current}/{MAX_CONCURRENT_JOBS_PER_TENANT}")
    
    def get_active_job_count(self, tenant_id: str) -> int:
        """Get current active job count"""
        key = self._get_semaphore_key(tenant_id)
        count = self.redis_client.get(key)
        return int(count) if count else 0
    
    def save_job_state(self, tenant_id: str, job_id: str, state: Dict):
        """Save job state to Redis"""
        key = self._get_job_key(tenant_id, job_id)
        state['last_updated'] = datetime.utcnow().isoformat()
        self.redis_client.setex(key, 86400, json.dumps(state))
        logger.debug(f"Saved job state for {tenant_id}:{job_id}: {state.get('status')}")
    
    def get_job_state(self, tenant_id: str, job_id: str) -> Optional[Dict]:
        """Get job state from Redis"""
        key = self._get_job_key(tenant_id, job_id)
        data = self.redis_client.get(key)
        return json.loads(data) if data else None
    
    def update_status(self, tenant_id: str, job_id: str, status: str):
        """Update job status - ALWAYS release semaphore on completion/failure"""
        state = self.get_job_state(tenant_id, job_id)
        
        if state is None:
            logger.error(f"Job state missing for {job_id}, recreating minimal state")
            # ✅ FIX: Recreate state instead of returning early
            state = {
                'job_id': job_id,
                'tenant_id': tenant_id,
                'status': status,
                'error_message': 'State was lost, recreated',
                'total_fields': 0,
                'processed_fields': 0
            }
        else:
            state['status'] = status
        
        if status == 'running':
            state['started_at'] = datetime.utcnow().isoformat()
        elif status in ['completed', 'failed']:
            state['completed_at'] = datetime.utcnow().isoformat()
            # ✅ ALWAYS release semaphore on terminal states
            self.release_job_slot(tenant_id)
        
        self.save_job_state(tenant_id, job_id, state)
        logger.info(f"Job {job_id} status updated to {status}")
    
    def set_error(self, tenant_id: str, job_id: str, error: str):
        """Set job error - ALWAYS release semaphore even if state missing"""
        state = self.get_job_state(tenant_id, job_id)
        
        if state is None:
            logger.warning(f"Job state missing for {job_id}, creating error state")
            # ✅ FIX: Create error state instead of returning
            state = {
                'job_id': job_id,
                'tenant_id': tenant_id,
                'status': 'failed',
                'error_message': error,
                'completed_at': datetime.utcnow().isoformat(),
                'total_fields': 0,
                'processed_fields': 0
            }
        else:
            state['status'] = 'failed'
            state['error_message'] = error
            state['completed_at'] = datetime.utcnow().isoformat()
        
        self.save_job_state(tenant_id, job_id, state)
        # ✅ ALWAYS release semaphore, even if state was missing
        self.release_job_slot(tenant_id)
        logger.error(f"Job {job_id} failed: {error}")
    
    def update_progress(self, tenant_id: str, job_id: str, processed: int, total: int, successful: int = None):
        """Update job progress"""
        state = self.get_job_state(tenant_id, job_id)
        if state:
            state['processed_fields'] = processed
            state['total_fields'] = total
            if successful is not None:
                state['successful_mappings'] = successful
            
            if total > 0:
                state['progress_percentage'] = int((processed / total) * 100)
            
            self.save_job_state(tenant_id, job_id, state)
            logger.debug(f"Job {job_id} progress: {processed}/{total}")
    
    def delete_job_state(self, tenant_id: str, job_id: str):
        """Delete job state from Redis"""
        key = self._get_job_key(tenant_id, job_id)
        self.redis_client.delete(key)
        logger.info(f"Deleted job state for {tenant_id}:{job_id}")
    
    def get_all_jobs_for_tenant(self, tenant_id: str) -> list:
        """Get all job keys for a tenant"""
        pattern = f"job:state:tenant:{tenant_id}:job:*"
        keys = self.redis_client.keys(pattern)
        jobs = []
        for key in keys:
            data = self.redis_client.get(key)
            if data:
                jobs.append(json.loads(data))
        return jobs
