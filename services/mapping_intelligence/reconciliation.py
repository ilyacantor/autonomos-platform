"""
Autonomous Job Reconciliation

Features:
- Semaphore reconciliation
- Stale job detection (30min timeout)
- Automatic cleanup and recovery
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict
import json

logger = logging.getLogger(__name__)

STALE_JOB_TIMEOUT_MINUTES = 30


class JobReconciliationService:
    """
    Autonomous service for reconciling job state and cleaning up stale jobs
    """
    
    def __init__(self, redis_client=None):
        from shared.redis_client import get_redis_client
        self.redis_client = redis_client or get_redis_client()
        
        if not self.redis_client:
            raise RuntimeError("Redis is required for job reconciliation")
    
    def reconcile_semaphores(self, tenant_id: str) -> Dict:
        """
        Reconcile semaphore counts with actual running jobs
        
        Args:
            tenant_id: Tenant identifier
        
        Returns:
            Dictionary with reconciliation results
        """
        logger.info(f"Starting semaphore reconciliation for tenant {tenant_id}")
        
        from services.mapping_intelligence.job_state import BulkMappingJobState
        job_state = BulkMappingJobState(self.redis_client)
        
        current_count = job_state.get_active_job_count(tenant_id)
        
        all_jobs = job_state.get_all_jobs_for_tenant(tenant_id)
        
        running_jobs = [
            job for job in all_jobs
            if job.get('status') in ['running', 'pending']
        ]
        
        actual_count = len(running_jobs)
        
        if current_count != actual_count:
            logger.warning(
                f"Semaphore mismatch for tenant {tenant_id}: "
                f"semaphore={current_count}, actual={actual_count}"
            )
            
            semaphore_key = f"job:semaphore:tenant:{tenant_id}"
            self.redis_client.set(semaphore_key, actual_count)
            
            logger.info(f"Reset semaphore for tenant {tenant_id} to {actual_count}")
        
        return {
            'tenant_id': tenant_id,
            'previous_count': current_count,
            'actual_count': actual_count,
            'reconciled': current_count != actual_count,
            'running_jobs': [job.get('job_id') for job in running_jobs]
        }
    
    def detect_stale_jobs(self, tenant_id: str) -> List[Dict]:
        """
        Detect jobs that have been running longer than timeout
        
        Args:
            tenant_id: Tenant identifier
        
        Returns:
            List of stale job information
        """
        logger.info(f"Detecting stale jobs for tenant {tenant_id}")
        
        from services.mapping_intelligence.job_state import BulkMappingJobState
        job_state = BulkMappingJobState(self.redis_client)
        
        all_jobs = job_state.get_all_jobs_for_tenant(tenant_id)
        
        stale_jobs = []
        cutoff_time = datetime.utcnow() - timedelta(minutes=STALE_JOB_TIMEOUT_MINUTES)
        
        for job in all_jobs:
            if job.get('status') != 'running':
                continue
            
            started_at_str = job.get('started_at')
            if not started_at_str:
                continue
            
            try:
                started_at = datetime.fromisoformat(started_at_str)
                
                if started_at < cutoff_time:
                    elapsed_minutes = (datetime.utcnow() - started_at).total_seconds() / 60
                    
                    stale_jobs.append({
                        'job_id': job.get('job_id'),
                        'tenant_id': tenant_id,
                        'started_at': started_at_str,
                        'elapsed_minutes': round(elapsed_minutes, 2),
                        'status': job.get('status')
                    })
                    
                    logger.warning(
                        f"Detected stale job {job.get('job_id')} "
                        f"running for {elapsed_minutes:.1f} minutes"
                    )
            
            except Exception as e:
                logger.error(f"Error checking job staleness: {e}")
        
        return stale_jobs
    
    def cleanup_stale_jobs(self, tenant_id: str, auto_fail: bool = True) -> Dict:
        """
        Clean up stale jobs by marking them as failed
        
        Args:
            tenant_id: Tenant identifier
            auto_fail: If True, automatically mark stale jobs as failed
        
        Returns:
            Dictionary with cleanup results
        """
        logger.info(f"Cleaning up stale jobs for tenant {tenant_id}")
        
        stale_jobs = self.detect_stale_jobs(tenant_id)
        
        if not stale_jobs:
            logger.info(f"No stale jobs found for tenant {tenant_id}")
            return {
                'tenant_id': tenant_id,
                'stale_jobs_found': 0,
                'jobs_failed': 0
            }
        
        jobs_failed = 0
        
        if auto_fail:
            from services.mapping_intelligence.job_state import BulkMappingJobState
            job_state = BulkMappingJobState(self.redis_client)
            
            for job in stale_jobs:
                job_id = job['job_id']
                
                try:
                    job_state.set_error(
                        tenant_id,
                        job_id,
                        f"Job timed out after {STALE_JOB_TIMEOUT_MINUTES} minutes"
                    )
                    jobs_failed += 1
                    
                    logger.info(f"Marked stale job {job_id} as failed")
                
                except Exception as e:
                    logger.error(f"Failed to mark job {job_id} as failed: {e}")
        
        return {
            'tenant_id': tenant_id,
            'stale_jobs_found': len(stale_jobs),
            'jobs_failed': jobs_failed,
            'stale_jobs': stale_jobs
        }
    
    def full_reconciliation(self, tenant_id: str) -> Dict:
        """
        Perform full reconciliation: semaphores + stale job cleanup
        
        Args:
            tenant_id: Tenant identifier
        
        Returns:
            Dictionary with full reconciliation results
        """
        logger.info(f"Starting full reconciliation for tenant {tenant_id}")
        
        semaphore_result = self.reconcile_semaphores(tenant_id)
        cleanup_result = self.cleanup_stale_jobs(tenant_id, auto_fail=True)
        
        result = {
            'tenant_id': tenant_id,
            'timestamp': datetime.utcnow().isoformat(),
            'semaphore_reconciliation': semaphore_result,
            'stale_job_cleanup': cleanup_result
        }
        
        logger.info(f"Completed full reconciliation for tenant {tenant_id}")
        
        return result
    
    def reconcile_all_tenants(self, tenant_ids: List[str]) -> List[Dict]:
        """
        Perform reconciliation for multiple tenants
        
        Args:
            tenant_ids: List of tenant identifiers
        
        Returns:
            List of reconciliation results
        """
        results = []
        
        for tenant_id in tenant_ids:
            try:
                result = self.full_reconciliation(tenant_id)
                results.append(result)
            
            except Exception as e:
                logger.error(f"Reconciliation failed for tenant {tenant_id}: {e}")
                results.append({
                    'tenant_id': tenant_id,
                    'error': str(e)
                })
        
        return results
