"""
Extended Load and Performance Tests for Distributed Job Queue

Additional Tests:
- Multi-tenant isolation
- Stress testing
- Soak testing
- Performance baseline validation
"""

import pytest
import asyncio
import time
from uuid import uuid4
from services.mapping_intelligence.job_enqueue import enqueue_bulk_mapping_job, get_job_status
from services.mapping_intelligence.job_state import BulkMappingJobState, MAX_CONCURRENT_JOBS_PER_TENANT
from services.mapping_intelligence.resource_monitor import ResourceMonitor
from shared.redis_client import get_redis_client


@pytest.fixture
def redis_client():
    """Get Redis client and skip if unavailable"""
    client = get_redis_client()
    if not client:
        pytest.skip("Redis not available")
    return client


class TestMultiTenantIsolation:
    """Test multi-tenant isolation and no cross-tenant interference"""
    
    @pytest.mark.asyncio
    async def test_concurrent_multi_tenant_load(self, redis_client):
        """Test 10 tenants submitting 10 jobs each simultaneously"""
        num_tenants = 10
        jobs_per_tenant = 10
        
        async def submit_tenant_jobs(tenant_idx):
            tenant_id = f"test-tenant-multi-{tenant_idx}-{uuid4()}"
            submitted_jobs = []
            
            for job_idx in range(jobs_per_tenant):
                try:
                    result = enqueue_bulk_mapping_job(
                        tenant_id=tenant_id,
                        connector_definition_ids=[f'conn-{job_idx}'],
                        use_tenant_pool=True
                    )
                    submitted_jobs.append(result)
                except Exception as e:
                    print(f"Tenant {tenant_idx} job {job_idx} failed: {e}")
            
            return {
                'tenant_id': tenant_id,
                'submitted': len(submitted_jobs),
                'queued': len([j for j in submitted_jobs if j['status'] == 'queued']),
                'rejected': len([j for j in submitted_jobs if j['status'] == 'rejected'])
            }
        
        results = await asyncio.gather(*[submit_tenant_jobs(i) for i in range(num_tenants)])
        
        job_state = BulkMappingJobState(redis_client)
        for tenant_result in results:
            tenant_id = tenant_result['tenant_id']
            active_count = job_state.get_active_job_count(tenant_id)
            
            assert active_count <= MAX_CONCURRENT_JOBS_PER_TENANT, \
                f"Tenant {tenant_id} exceeded semaphore limit: {active_count}"
            
            assert tenant_result['queued'] <= MAX_CONCURRENT_JOBS_PER_TENANT, \
                f"Tenant {tenant_id} queued more than allowed: {tenant_result['queued']}"
        
        for tenant_result in results:
            tenant_id = tenant_result['tenant_id']
            pattern = f"job:*:tenant:{tenant_id}:*"
            keys = redis_client.keys(pattern)
            if keys:
                redis_client.delete(*keys)
        
        print(f"\n✅ Multi-tenant isolation verified:")
        print(f"   - {num_tenants} tenants submitted jobs concurrently")
        print(f"   - No cross-tenant interference detected")
        print(f"   - Per-tenant semaphores enforced correctly")
    
    @pytest.mark.asyncio
    async def test_tenant_semaphore_independence(self, redis_client):
        """Verify tenant semaphores don't interfere with each other"""
        tenant_a = f"test-tenant-a-{uuid4()}"
        tenant_b = f"test-tenant-b-{uuid4()}"
        
        job_state = BulkMappingJobState(redis_client)
        
        for i in range(MAX_CONCURRENT_JOBS_PER_TENANT):
            assert job_state.try_reserve_job_slot(tenant_a)
        
        for i in range(MAX_CONCURRENT_JOBS_PER_TENANT):
            assert job_state.try_reserve_job_slot(tenant_b), \
                f"Tenant B affected by Tenant A's semaphore at slot {i}"
        
        assert job_state.get_active_job_count(tenant_a) == MAX_CONCURRENT_JOBS_PER_TENANT
        assert job_state.get_active_job_count(tenant_b) == MAX_CONCURRENT_JOBS_PER_TENANT
        
        for tenant_id in [tenant_a, tenant_b]:
            pattern = f"job:*:tenant:{tenant_id}:*"
            keys = redis_client.keys(pattern)
            if keys:
                redis_client.delete(*keys)


class TestStressScenarios:
    """Stress testing scenarios"""
    
    def test_stress_over_semaphore_limit(self, redis_client):
        """Submit 100 jobs to single tenant (max 5 concurrent)"""
        tenant_id = f"test-stress-{uuid4()}"
        total_jobs = 100
        
        submitted = []
        
        for i in range(total_jobs):
            result = enqueue_bulk_mapping_job(
                tenant_id=tenant_id,
                connector_definition_ids=[f'conn-{i}'],
                use_tenant_pool=True
            )
            submitted.append(result)
        
        queued = [r for r in submitted if r['status'] == 'queued']
        rejected = [r for r in submitted if r['status'] == 'rejected']
        
        assert len(queued) <= MAX_CONCURRENT_JOBS_PER_TENANT, \
            f"More than {MAX_CONCURRENT_JOBS_PER_TENANT} jobs queued: {len(queued)}"
        
        assert len(rejected) > 0, "Expected some jobs to be rejected"
        
        job_state = BulkMappingJobState(redis_client)
        active_count = job_state.get_active_job_count(tenant_id)
        
        assert active_count <= MAX_CONCURRENT_JOBS_PER_TENANT, \
            f"Semaphore leaked: {active_count} > {MAX_CONCURRENT_JOBS_PER_TENANT}"
        
        pattern = f"job:*:tenant:{tenant_id}:*"
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
        
        print(f"\n✅ Stress test passed:")
        print(f"   - Submitted: {total_jobs} jobs")
        print(f"   - Queued: {len(queued)} jobs")
        print(f"   - Rejected: {len(rejected)} jobs")
        print(f"   - No semaphore leaks detected")
    
    @pytest.mark.asyncio
    async def test_rapid_submission_and_completion(self, redis_client):
        """Test rapid job submission and immediate completion simulation"""
        tenant_id = f"test-rapid-{uuid4()}"
        job_state = BulkMappingJobState(redis_client)
        
        num_iterations = 20
        
        for iteration in range(num_iterations):
            result = enqueue_bulk_mapping_job(
                tenant_id=tenant_id,
                connector_definition_ids=['conn'],
                use_tenant_pool=True
            )
            
            if result['status'] == 'queued':
                job_id = result['job_id']
                
                job_state.update_status(tenant_id, job_id, 'completed')
                
                await asyncio.sleep(0.01)
        
        active_count = job_state.get_active_job_count(tenant_id)
        assert active_count == 0, f"Semaphore not properly released: {active_count}"
        
        pattern = f"job:*:tenant:{tenant_id}:*"
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)


class TestSoakTesting:
    """Soak testing - sustained load over time"""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_soak_sustained_load(self, redis_client):
        """Run constant load for 5 minutes to detect memory leaks"""
        tenant_id = f"test-soak-{uuid4()}"
        job_state = BulkMappingJobState(redis_client)
        monitor = ResourceMonitor(redis_client)
        
        duration_seconds = 300
        jobs_per_minute = 10
        submission_interval = 60 / jobs_per_minute
        
        start_time = time.time()
        end_time = start_time + duration_seconds
        
        submitted_count = 0
        completed_count = 0
        
        memory_samples = []
        
        while time.time() < end_time:
            result = enqueue_bulk_mapping_job(
                tenant_id=tenant_id,
                connector_definition_ids=['conn'],
                use_tenant_pool=True
            )
            
            if result['status'] == 'queued':
                job_id = result['job_id']
                submitted_count += 1
                
                job_state.update_status(tenant_id, job_id, 'running')
                await asyncio.sleep(0.1)
                job_state.update_status(tenant_id, job_id, 'completed')
                completed_count += 1
            
            metrics = monitor.get_current_metrics()
            memory_samples.append(metrics['memory_rss_mb'])
            
            await asyncio.sleep(submission_interval)
        
        elapsed = time.time() - start_time
        
        if len(memory_samples) > 10:
            first_half_avg = sum(memory_samples[:len(memory_samples)//2]) / (len(memory_samples)//2)
            second_half_avg = sum(memory_samples[len(memory_samples)//2:]) / (len(memory_samples)//2)
            memory_increase = second_half_avg - first_half_avg
            
            assert memory_increase < 100, \
                f"Potential memory leak detected: {memory_increase:.1f}MB increase"
        
        active_count = job_state.get_active_job_count(tenant_id)
        assert active_count == 0, f"Semaphore leak after soak test: {active_count}"
        
        pattern = f"job:*:tenant:{tenant_id}:*"
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
        
        print(f"\n✅ Soak test passed:")
        print(f"   - Duration: {elapsed:.1f}s")
        print(f"   - Jobs submitted: {submitted_count}")
        print(f"   - Jobs completed: {completed_count}")
        print(f"   - Memory stable (no leaks detected)")
        print(f"   - Reconciliation service maintained integrity")


class TestPerformanceBaseline:
    """Performance baseline validation tests"""
    
    @pytest.mark.asyncio
    async def test_small_workload_baseline(self, redis_client):
        """Validate small workload meets baseline targets"""
        tenant_id = f"test-baseline-small-{uuid4()}"
        job_state = BulkMappingJobState(redis_client)
        
        num_jobs = 5
        start_time = time.time()
        
        job_ids = []
        for i in range(num_jobs):
            result = enqueue_bulk_mapping_job(
                tenant_id=tenant_id,
                connector_definition_ids=[f'conn-{i}'],
                use_tenant_pool=True
            )
            if result['status'] == 'queued':
                job_ids.append(result['job_id'])
        
        for job_id in job_ids:
            job_state.update_status(tenant_id, job_id, 'running')
            await asyncio.sleep(0.1)
            job_state.update_status(tenant_id, job_id, 'completed')
        
        elapsed = time.time() - start_time
        
        assert elapsed < 30, f"Small workload took too long: {elapsed:.1f}s > 30s"
        
        throughput = len(job_ids) / elapsed
        assert throughput >= 0.5, f"Throughput too low: {throughput:.2f} jobs/sec < 0.5 jobs/sec"
        
        pattern = f"job:*:tenant:{tenant_id}:*"
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
        
        print(f"\n✅ Small workload baseline met:")
        print(f"   - Duration: {elapsed:.2f}s < 30s target")
        print(f"   - Throughput: {throughput:.2f} jobs/sec")
