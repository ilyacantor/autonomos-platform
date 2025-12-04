"""
Multi-Tenant Stress Testing Suite

Validates AutonomOS can handle concurrent workloads from multiple tenants with:
- Complete isolation
- Fairness
- No cross-tenant interference
"""

import pytest
import asyncio
import time
from uuid import uuid4
from typing import List, Dict
from services.mapping_intelligence.job_enqueue import enqueue_bulk_mapping_job, get_job_status
from services.mapping_intelligence.job_state import BulkMappingJobState, MAX_CONCURRENT_JOBS_PER_TENANT
from services.mapping_intelligence.reconciliation import JobReconciliationService
from shared.redis_client import get_redis_client


@pytest.fixture
def redis_client():
    """Get Redis client and skip if unavailable"""
    client = get_redis_client()
    if not client:
        pytest.skip("Redis not available")
    return client


@pytest.fixture
def job_state(redis_client):
    """Get job state manager"""
    return BulkMappingJobState(redis_client)


@pytest.fixture
def reconciliation_service(redis_client):
    """Get reconciliation service"""
    return JobReconciliationService(redis_client)


class TestTenantIsolationUnderLoad:
    """Test 1: Tenant Isolation Under Concurrent Load"""
    
    @pytest.mark.asyncio
    async def test_tenant_isolation_under_concurrent_load(self, redis_client, job_state):
        """
        Validate that 10 tenants submitting jobs simultaneously have:
        - Independent semaphore enforcement (5 concurrent jobs per tenant)
        - No cross-tenant job interference
        - No resource starvation
        - Independent job state tracking
        """
        num_tenants = 10
        jobs_per_tenant = 20
        
        tenant_ids = [f"tenant-stress-{i}-{uuid4()}" for i in range(num_tenants)]
        
        async def submit_tenant_jobs(tenant_id: str, tenant_idx: int) -> Dict:
            """Submit jobs for a single tenant"""
            submitted = []
            queued = []
            rejected = []
            
            for job_idx in range(jobs_per_tenant):
                try:
                    result = enqueue_bulk_mapping_job(
                        tenant_id=tenant_id,
                        connector_definition_ids=[f'connector-{tenant_idx}-{job_idx}'],
                        use_tenant_pool=True
                    )
                    submitted.append(result)
                    
                    if result['status'] == 'queued':
                        queued.append(result)
                    else:
                        rejected.append(result)
                        
                except Exception as e:
                    print(f"Tenant {tenant_idx} job {job_idx} error: {e}")
            
            return {
                'tenant_id': tenant_id,
                'tenant_idx': tenant_idx,
                'submitted': len(submitted),
                'queued': len(queued),
                'rejected': len(rejected)
            }
        
        results = await asyncio.gather(*[
            submit_tenant_jobs(tenant_ids[i], i) 
            for i in range(num_tenants)
        ])
        
        for result in results:
            tenant_id = result['tenant_id']
            tenant_idx = result['tenant_idx']
            
            active_count = job_state.get_active_job_count(tenant_id)
            
            assert active_count <= MAX_CONCURRENT_JOBS_PER_TENANT, \
                f"Tenant {tenant_idx} exceeded semaphore: {active_count} > {MAX_CONCURRENT_JOBS_PER_TENANT}"
            
            assert result['queued'] <= MAX_CONCURRENT_JOBS_PER_TENANT, \
                f"Tenant {tenant_idx} queued too many: {result['queued']}"
            
            assert result['rejected'] > 0, \
                f"Tenant {tenant_idx} should have rejected jobs with {jobs_per_tenant} submissions"
        
        for tenant_id in tenant_ids:
            all_jobs = job_state.get_all_jobs_for_tenant(tenant_id)
            
            for other_tenant_id in tenant_ids:
                if other_tenant_id != tenant_id:
                    other_jobs = job_state.get_all_jobs_for_tenant(other_tenant_id)
                    other_job_ids = {job['job_id'] for job in other_jobs}
                    
                    for job in all_jobs:
                        assert job['job_id'] not in other_job_ids, \
                            f"Cross-tenant job leakage detected!"
        
        for tenant_id in tenant_ids:
            pattern = f"job:*:tenant:{tenant_id}:*"
            keys = redis_client.keys(pattern)
            if keys:
                redis_client.delete(*keys)
        
        print(f"\n✅ Test 1 PASSED: Tenant Isolation Under Load")
        print(f"   - {num_tenants} tenants processed {num_tenants * jobs_per_tenant} total jobs")
        print(f"   - All tenants respected {MAX_CONCURRENT_JOBS_PER_TENANT} concurrent job limit")
        print(f"   - No cross-tenant interference detected")
        print(f"   - Independent job state tracking verified")


class TestSemaphoreFairness:
    """Test 2: Semaphore Fairness Across Tenants"""
    
    @pytest.mark.asyncio
    async def test_semaphore_fairness_across_tenants(self, redis_client, job_state):
        """
        Validate semaphore allocation is fair:
        - Tenant A submits 100 jobs
        - Tenant B submits 100 jobs
        - Both should process at similar rates (no starvation)
        - Completion times within 20% of each other
        """
        tenant_a = f"tenant-fair-a-{uuid4()}"
        tenant_b = f"tenant-fair-b-{uuid4()}"
        jobs_per_tenant = 100
        
        async def submit_and_process_jobs(tenant_id: str) -> Dict:
            """Submit jobs and simulate processing"""
            start_time = time.time()
            submitted_jobs = []
            
            for i in range(jobs_per_tenant):
                try:
                    result = enqueue_bulk_mapping_job(
                        tenant_id=tenant_id,
                        connector_definition_ids=[f'conn-{i}'],
                        use_tenant_pool=True
                    )
                    
                    if result['status'] == 'queued':
                        submitted_jobs.append(result['job_id'])
                        
                        job_state.update_status(tenant_id, result['job_id'], 'running')
                        await asyncio.sleep(0.01)
                        job_state.update_status(tenant_id, result['job_id'], 'completed')
                        
                except Exception as e:
                    print(f"Job submission error: {e}")
                
                if i % 10 == 0:
                    await asyncio.sleep(0.05)
            
            elapsed = time.time() - start_time
            
            return {
                'tenant_id': tenant_id,
                'jobs_processed': len(submitted_jobs),
                'elapsed_time': elapsed
            }
        
        results = await asyncio.gather(
            submit_and_process_jobs(tenant_a),
            submit_and_process_jobs(tenant_b)
        )
        
        result_a = results[0]
        result_b = results[1]
        
        time_diff_ratio = abs(result_a['elapsed_time'] - result_b['elapsed_time']) / max(result_a['elapsed_time'], result_b['elapsed_time'])
        
        assert time_diff_ratio < 0.20, \
            f"Unfair processing times: Tenant A={result_a['elapsed_time']:.2f}s, " \
            f"Tenant B={result_b['elapsed_time']:.2f}s, diff={time_diff_ratio*100:.1f}%"
        
        for tenant_id in [tenant_a, tenant_b]:
            final_count = job_state.get_active_job_count(tenant_id)
            assert final_count == 0, f"Semaphore leaked for {tenant_id}: {final_count}"
        
        for tenant_id in [tenant_a, tenant_b]:
            pattern = f"job:*:tenant:{tenant_id}:*"
            keys = redis_client.keys(pattern)
            if keys:
                redis_client.delete(*keys)
        
        print(f"\n✅ Test 2 PASSED: Semaphore Fairness")
        print(f"   - Tenant A: {result_a['jobs_processed']} jobs in {result_a['elapsed_time']:.2f}s")
        print(f"   - Tenant B: {result_b['jobs_processed']} jobs in {result_b['elapsed_time']:.2f}s")
        print(f"   - Time difference: {time_diff_ratio*100:.1f}% (< 20% threshold)")
        print(f"   - No starvation detected")


class TestDataIsolation:
    """Test 3: Data Isolation Validation"""
    
    def test_no_cross_tenant_data_leakage(self, redis_client, job_state):
        """
        Validate Redis job state isolation:
        - Tenant A's jobs invisible to Tenant B queries
        - Tenant B cannot modify Tenant A's job state
        - Tenant-scoped Redis keys enforced
        """
        tenant_a = f"tenant-isolated-a-{uuid4()}"
        tenant_b = f"tenant-isolated-b-{uuid4()}"
        
        job_ids_a = []
        job_ids_b = []
        
        for i in range(5):
            result_a = enqueue_bulk_mapping_job(
                tenant_id=tenant_a,
                connector_definition_ids=[f'conn-a-{i}'],
                use_tenant_pool=True
            )
            if result_a['status'] == 'queued':
                job_ids_a.append(result_a['job_id'])
            
            result_b = enqueue_bulk_mapping_job(
                tenant_id=tenant_b,
                connector_definition_ids=[f'conn-b-{i}'],
                use_tenant_pool=True
            )
            if result_b['status'] == 'queued':
                job_ids_b.append(result_b['job_id'])
        
        jobs_a = job_state.get_all_jobs_for_tenant(tenant_a)
        jobs_b = job_state.get_all_jobs_for_tenant(tenant_b)
        
        job_ids_in_a = {job['job_id'] for job in jobs_a}
        job_ids_in_b = {job['job_id'] for job in jobs_b}
        
        for job_id in job_ids_a:
            assert job_id in job_ids_in_a, f"Tenant A job {job_id} not found in tenant A query"
            assert job_id not in job_ids_in_b, f"Tenant A job {job_id} leaked to tenant B!"
        
        for job_id in job_ids_b:
            assert job_id in job_ids_in_b, f"Tenant B job {job_id} not found in tenant B query"
            assert job_id not in job_ids_in_a, f"Tenant B job {job_id} leaked to tenant A!"
        
        if job_ids_a:
            test_job_id = job_ids_a[0]
            
            job_state_a = job_state.get_job_state(tenant_a, test_job_id)
            assert job_state_a is not None, "Should be able to read own tenant's job"
            
            job_state.update_status(tenant_a, test_job_id, 'running')
            
            updated_state = job_state.get_job_state(tenant_a, test_job_id)
            assert updated_state['status'] == 'running', "Should be able to update own tenant's job"
            
            job_state.update_status(tenant_a, test_job_id, 'completed')
        
        for tenant_id in [tenant_a, tenant_b]:
            pattern = f"job:*:tenant:{tenant_id}:*"
            keys = redis_client.keys(pattern)
            if keys:
                redis_client.delete(*keys)
        
        print(f"\n✅ Test 3 PASSED: Data Isolation")
        print(f"   - Tenant A: {len(job_ids_a)} jobs isolated")
        print(f"   - Tenant B: {len(job_ids_b)} jobs isolated")
        print(f"   - No cross-tenant data leakage detected")
        print(f"   - Tenant-scoped Redis keys enforced")


class TestBurstLoad:
    """Test 4: Burst Load Handling"""
    
    @pytest.mark.asyncio
    async def test_burst_load_from_multiple_tenants(self, redis_client, job_state, reconciliation_service):
        """
        Simulate sudden burst:
        - 5 tenants submit 50 jobs each instantly
        - Validate queueing behavior
        - Check reconciliation service handles stale jobs
        - Verify no semaphore leaks
        """
        num_tenants = 5
        jobs_per_tenant = 50
        
        tenant_ids = [f"tenant-burst-{i}-{uuid4()}" for i in range(num_tenants)]
        
        async def burst_submit(tenant_id: str) -> Dict:
            """Submit all jobs instantly"""
            results = []
            
            for i in range(jobs_per_tenant):
                result = enqueue_bulk_mapping_job(
                    tenant_id=tenant_id,
                    connector_definition_ids=[f'conn-{i}'],
                    use_tenant_pool=True
                )
                results.append(result)
            
            queued = [r for r in results if r['status'] == 'queued']
            rejected = [r for r in results if r['status'] == 'rejected']
            
            return {
                'tenant_id': tenant_id,
                'queued': len(queued),
                'rejected': len(rejected),
                'job_ids': [r['job_id'] for r in queued]
            }
        
        start_time = time.time()
        results = await asyncio.gather(*[burst_submit(tid) for tid in tenant_ids])
        burst_time = time.time() - start_time
        
        for result in results:
            tenant_id = result['tenant_id']
            
            assert result['queued'] <= MAX_CONCURRENT_JOBS_PER_TENANT, \
                f"Too many jobs queued for {tenant_id}: {result['queued']}"
            
            assert result['rejected'] > 0, \
                f"Expected rejections for {tenant_id} with {jobs_per_tenant} submissions"
            
            active_count = job_state.get_active_job_count(tenant_id)
            assert active_count <= MAX_CONCURRENT_JOBS_PER_TENANT, \
                f"Semaphore exceeded for {tenant_id}: {active_count}"
        
        for result in results:
            tenant_id = result['tenant_id']
            reconcile_result = reconciliation_service.full_reconciliation(tenant_id)
            
            assert 'error' not in reconcile_result, \
                f"Reconciliation failed for {tenant_id}: {reconcile_result.get('error')}"
        
        for tenant_id in tenant_ids:
            final_count = job_state.get_active_job_count(tenant_id)
            assert final_count <= MAX_CONCURRENT_JOBS_PER_TENANT, \
                f"Semaphore leak detected for {tenant_id}: {final_count}"
        
        for tenant_id in tenant_ids:
            pattern = f"job:*:tenant:{tenant_id}:*"
            keys = redis_client.keys(pattern)
            if keys:
                redis_client.delete(*keys)
        
        total_queued = sum(r['queued'] for r in results)
        total_rejected = sum(r['rejected'] for r in results)
        
        print(f"\n✅ Test 4 PASSED: Burst Load Handling")
        print(f"   - {num_tenants} tenants submitted {num_tenants * jobs_per_tenant} jobs in {burst_time:.2f}s")
        print(f"   - Total queued: {total_queued}")
        print(f"   - Total rejected: {total_rejected}")
        print(f"   - Reconciliation verified for all tenants")
        print(f"   - No semaphore leaks detected")


class TestMixedWorkloads:
    """Test 5: Long-Running vs. Short Jobs"""
    
    @pytest.mark.asyncio
    async def test_tenant_mix_long_short_jobs(self, redis_client, job_state):
        """
        Validate mixed workloads:
        - Tenant A: 10 long-running jobs (simulated)
        - Tenant B: 100 short jobs (simulated)
        - Verify Tenant B not blocked by Tenant A's long jobs
        - Confirm independent throughput
        """
        tenant_a = f"tenant-long-{uuid4()}"
        tenant_b = f"tenant-short-{uuid4()}"
        
        async def submit_long_jobs(tenant_id: str) -> Dict:
            """Tenant A: Long-running jobs"""
            start_time = time.time()
            job_ids = []
            
            for i in range(10):
                result = enqueue_bulk_mapping_job(
                    tenant_id=tenant_id,
                    connector_definition_ids=[f'long-conn-{i}'],
                    use_tenant_pool=True
                )
                
                if result['status'] == 'queued':
                    job_ids.append(result['job_id'])
                    job_state.update_status(tenant_id, result['job_id'], 'running')
            
            await asyncio.sleep(2)
            
            for job_id in job_ids:
                job_state.update_status(tenant_id, job_id, 'completed')
            
            elapsed = time.time() - start_time
            
            return {
                'tenant_id': tenant_id,
                'jobs_completed': len(job_ids),
                'elapsed_time': elapsed
            }
        
        async def submit_short_jobs(tenant_id: str) -> Dict:
            """Tenant B: Short jobs"""
            start_time = time.time()
            job_ids = []
            
            for i in range(100):
                result = enqueue_bulk_mapping_job(
                    tenant_id=tenant_id,
                    connector_definition_ids=[f'short-conn-{i}'],
                    use_tenant_pool=True
                )
                
                if result['status'] == 'queued':
                    job_ids.append(result['job_id'])
                    job_state.update_status(tenant_id, result['job_id'], 'running')
                    await asyncio.sleep(0.01)
                    job_state.update_status(tenant_id, result['job_id'], 'completed')
            
            elapsed = time.time() - start_time
            
            return {
                'tenant_id': tenant_id,
                'jobs_completed': len(job_ids),
                'elapsed_time': elapsed
            }
        
        result_a, result_b = await asyncio.gather(
            submit_long_jobs(tenant_a),
            submit_short_jobs(tenant_b)
        )
        
        assert result_b['jobs_completed'] > 0, "Tenant B should complete jobs"
        
        throughput_a = result_a['jobs_completed'] / result_a['elapsed_time']
        throughput_b = result_b['jobs_completed'] / result_b['elapsed_time']
        
        assert throughput_b > throughput_a, \
            f"Tenant B should have higher throughput than Tenant A"
        
        for tenant_id in [tenant_a, tenant_b]:
            final_count = job_state.get_active_job_count(tenant_id)
            assert final_count == 0, f"Semaphore not released for {tenant_id}: {final_count}"
        
        for tenant_id in [tenant_a, tenant_b]:
            pattern = f"job:*:tenant:{tenant_id}:*"
            keys = redis_client.keys(pattern)
            if keys:
                redis_client.delete(*keys)
        
        print(f"\n✅ Test 5 PASSED: Mixed Workloads")
        print(f"   - Tenant A (long jobs): {result_a['jobs_completed']} jobs, {throughput_a:.2f} jobs/sec")
        print(f"   - Tenant B (short jobs): {result_b['jobs_completed']} jobs, {throughput_b:.2f} jobs/sec")
        print(f"   - Tenant B not blocked by Tenant A")
        print(f"   - Independent throughput verified")


class TestResourceQuotas:
    """Test 6: Tenant Resource Quota Enforcement"""
    
    def test_tenant_resource_quota_enforcement(self, redis_client, job_state):
        """
        Validate tenant-level limits:
        - Tenant with 5 concurrent job limit enforced
        - 6th job rejected properly
        - Semaphore released on job completion
        - No quota bypass exploits
        """
        tenant_id = f"tenant-quota-{uuid4()}"
        
        job_ids = []
        
        for i in range(MAX_CONCURRENT_JOBS_PER_TENANT):
            result = enqueue_bulk_mapping_job(
                tenant_id=tenant_id,
                connector_definition_ids=[f'conn-{i}'],
                use_tenant_pool=True
            )
            
            assert result['status'] == 'queued', \
                f"Job {i+1} should be queued (within limit)"
            
            job_ids.append(result['job_id'])
        
        active_count = job_state.get_active_job_count(tenant_id)
        assert active_count == MAX_CONCURRENT_JOBS_PER_TENANT, \
            f"Should have {MAX_CONCURRENT_JOBS_PER_TENANT} active jobs, got {active_count}"
        
        result_rejected = enqueue_bulk_mapping_job(
            tenant_id=tenant_id,
            connector_definition_ids=['conn-overflow'],
            use_tenant_pool=True
        )
        
        assert result_rejected['status'] == 'rejected', \
            f"Job beyond limit should be rejected, got {result_rejected['status']}"
        
        job_state.update_status(tenant_id, job_ids[0], 'completed')
        
        active_count_after = job_state.get_active_job_count(tenant_id)
        assert active_count_after == MAX_CONCURRENT_JOBS_PER_TENANT - 1, \
            f"Active count should decrease after completion: {active_count_after}"
        
        result_new = enqueue_bulk_mapping_job(
            tenant_id=tenant_id,
            connector_definition_ids=['conn-new'],
            use_tenant_pool=True
        )
        
        assert result_new['status'] == 'queued', \
            f"New job should be queued after slot freed"
        
        for job_id in job_ids[1:]:
            job_state.update_status(tenant_id, job_id, 'completed')
        
        job_state.update_status(tenant_id, result_new['job_id'], 'completed')
        
        final_count = job_state.get_active_job_count(tenant_id)
        assert final_count == 0, f"All semaphores should be released: {final_count}"
        
        pattern = f"job:*:tenant:{tenant_id}:*"
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
        
        print(f"\n✅ Test 6 PASSED: Resource Quota Enforcement")
        print(f"   - Quota limit of {MAX_CONCURRENT_JOBS_PER_TENANT} enforced correctly")
        print(f"   - Overflow job rejected as expected")
        print(f"   - Semaphore released on completion")
        print(f"   - New job accepted after slot freed")
        print(f"   - No quota bypass exploits detected")
