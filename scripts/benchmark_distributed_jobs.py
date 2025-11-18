"""
Benchmark Distributed Job Processing

Tests performance and reliability of the distributed job queue infrastructure.
"""

import asyncio
import time
import logging
from typing import List, Dict
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.mapping_intelligence.job_enqueue import enqueue_bulk_mapping_job, get_job_status
from services.mapping_intelligence.job_state import BulkMappingJobState
from shared.redis_client import get_redis_client

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BenchmarkRunner:
    """Runs performance benchmarks for distributed job processing"""
    
    def __init__(self, tenant_id: str = "benchmark-tenant"):
        self.tenant_id = tenant_id
        self.redis_client = get_redis_client()
        
        if not self.redis_client:
            raise RuntimeError("Redis is required for benchmarking")
        
        self.job_state = BulkMappingJobState(self.redis_client)
    
    def cleanup_tenant_jobs(self):
        """Clean up all jobs for the benchmark tenant"""
        logger.info(f"Cleaning up jobs for tenant {self.tenant_id}")
        
        jobs = self.job_state.get_all_jobs_for_tenant(self.tenant_id)
        
        for job in jobs:
            job_id = job.get('job_id')
            if job_id:
                self.job_state.delete_job_state(self.tenant_id, job_id)
        
        semaphore_key = f"job:semaphore:tenant:{self.tenant_id}"
        self.redis_client.set(semaphore_key, 0)
        
        logger.info(f"Cleaned up {len(jobs)} jobs")
    
    def submit_jobs(self, num_jobs: int, connectors_per_job: int = 5) -> List[str]:
        """Submit multiple jobs and return job IDs"""
        logger.info(f"Submitting {num_jobs} jobs with {connectors_per_job} connectors each")
        
        job_ids = []
        
        for i in range(num_jobs):
            connector_ids = [f"connector-{i}-{j}" for j in range(connectors_per_job)]
            
            try:
                result = enqueue_bulk_mapping_job(
                    tenant_id=self.tenant_id,
                    connector_definition_ids=connector_ids,
                    options={'benchmark': True},
                    use_tenant_pool=True
                )
                
                if result['status'] == 'queued':
                    job_ids.append(result['job_id'])
                    logger.info(f"Submitted job {i+1}/{num_jobs}: {result['job_id']}")
                else:
                    logger.warning(f"Job {i+1} rejected: {result.get('error')}")
            
            except Exception as e:
                logger.error(f"Failed to submit job {i+1}: {e}")
        
        return job_ids
    
    async def wait_for_jobs(self, job_ids: List[str], timeout: int = 300) -> Dict:
        """Wait for all jobs to complete and collect statistics"""
        logger.info(f"Waiting for {len(job_ids)} jobs to complete (timeout: {timeout}s)")
        
        start_time = time.time()
        stats = {
            'total_jobs': len(job_ids),
            'completed': 0,
            'failed': 0,
            'timeout': 0,
            'total_time': 0,
            'jobs': []
        }
        
        while time.time() - start_time < timeout:
            all_done = True
            
            for job_id in job_ids:
                status = get_job_status(self.tenant_id, job_id)
                
                if not status:
                    continue
                
                job_status = status.get('status')
                
                if job_status in ['pending', 'running']:
                    all_done = False
                elif job_status == 'completed':
                    if job_id not in [j['job_id'] for j in stats['jobs']]:
                        stats['completed'] += 1
                        stats['jobs'].append(status)
                        logger.info(f"Job {job_id} completed")
                elif job_status == 'failed':
                    if job_id not in [j['job_id'] for j in stats['jobs']]:
                        stats['failed'] += 1
                        stats['jobs'].append(status)
                        logger.error(f"Job {job_id} failed: {status.get('error_message')}")
            
            if all_done:
                break
            
            await asyncio.sleep(1)
        
        stats['total_time'] = time.time() - start_time
        stats['timeout'] = stats['total_jobs'] - stats['completed'] - stats['failed']
        
        return stats
    
    def print_results(self, stats: Dict):
        """Print benchmark results"""
        print("\n" + "="*60)
        print("BENCHMARK RESULTS")
        print("="*60)
        print(f"Total Jobs: {stats['total_jobs']}")
        print(f"Completed: {stats['completed']}")
        print(f"Failed: {stats['failed']}")
        print(f"Timeout: {stats['timeout']}")
        print(f"Total Time: {stats['total_time']:.2f}s")
        
        if stats['completed'] > 0:
            avg_time = stats['total_time'] / stats['completed']
            print(f"Avg Time per Job: {avg_time:.2f}s")
        
        print("="*60 + "\n")


async def run_benchmark(num_jobs: int = 10, connectors_per_job: int = 5):
    """Run a complete benchmark"""
    runner = BenchmarkRunner()
    
    runner.cleanup_tenant_jobs()
    
    job_ids = runner.submit_jobs(num_jobs, connectors_per_job)
    
    if not job_ids:
        logger.error("No jobs were successfully submitted")
        return
    
    stats = await runner.wait_for_jobs(job_ids)
    
    runner.print_results(stats)
    
    runner.cleanup_tenant_jobs()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Benchmark distributed job processing")
    parser.add_argument("--jobs", type=int, default=10, help="Number of jobs to submit")
    parser.add_argument("--connectors", type=int, default=5, help="Connectors per job")
    
    args = parser.parse_args()
    
    asyncio.run(run_benchmark(args.jobs, args.connectors))
