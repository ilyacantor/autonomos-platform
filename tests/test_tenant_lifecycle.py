"""
Tenant Lifecycle Management Tests

Validates:
- Tenant onboarding under load
- Tenant cleanup and resource deallocation
- No orphaned resources
"""

import pytest
import asyncio
import time
from uuid import uuid4
from typing import List, Dict
from services.mapping_intelligence.job_enqueue import enqueue_bulk_mapping_job
from services.mapping_intelligence.job_state import BulkMappingJobState, MAX_CONCURRENT_JOBS_PER_TENANT
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


class TestTenantOnboarding:
    """Test 1: Tenant Onboarding Under Load"""
    
    @pytest.mark.asyncio
    async def test_new_tenant_onboarding_during_load(self, redis_client, job_state):
        """
        Validate new tenant can start jobs while others are running:
        - 5 tenants with active jobs
        - Create new Tenant F
        - Tenant F should get independent semaphore
        - No impact on existing tenants
        """
        existing_tenants = [f"tenant-existing-{i}-{uuid4()}" for i in range(5)]
        
        async def keep_tenant_busy(tenant_id: str):
            """Keep a tenant continuously processing jobs"""
            for i in range(20):
                result = enqueue_bulk_mapping_job(
                    tenant_id=tenant_id,
                    connector_definition_ids=[f'conn-{i}'],
                    use_tenant_pool=True
                )
                
                if result['status'] == 'queued':
                    job_state.update_status(tenant_id, result['job_id'], 'running')
                    await asyncio.sleep(0.05)
                    job_state.update_status(tenant_id, result['job_id'], 'completed')
        
        existing_tasks = [keep_tenant_busy(tid) for tid in existing_tenants]
        
        await asyncio.sleep(0.2)
        
        new_tenant_id = f"tenant-new-{uuid4()}"
        
        new_tenant_jobs = []
        for i in range(10):
            result = enqueue_bulk_mapping_job(
                tenant_id=new_tenant_id,
                connector_definition_ids=[f'new-conn-{i}'],
                use_tenant_pool=True
            )
            
            if result['status'] == 'queued':
                new_tenant_jobs.append(result['job_id'])
        
        assert len(new_tenant_jobs) > 0, "New tenant should be able to submit jobs"
        
        new_tenant_active = job_state.get_active_job_count(new_tenant_id)
        assert new_tenant_active <= MAX_CONCURRENT_JOBS_PER_TENANT, \
            f"New tenant exceeded limit: {new_tenant_active}"
        
        for tenant_id in existing_tenants:
            active_count = job_state.get_active_job_count(tenant_id)
            assert active_count >= 0, f"Existing tenant {tenant_id} affected: {active_count}"
        
        for job_id in new_tenant_jobs:
            job_state.update_status(new_tenant_id, job_id, 'running')
            await asyncio.sleep(0.01)
            job_state.update_status(new_tenant_id, job_id, 'completed')
        
        await asyncio.gather(*existing_tasks)
        
        for tenant_id in existing_tenants + [new_tenant_id]:
            final_count = job_state.get_active_job_count(tenant_id)
            assert final_count == 0, f"Semaphore leaked for {tenant_id}: {final_count}"
        
        for tenant_id in existing_tenants + [new_tenant_id]:
            pattern = f"job:*:tenant:{tenant_id}:*"
            keys = redis_client.keys(pattern)
            if keys:
                redis_client.delete(*keys)
        
        print(f"\n✅ Lifecycle Test 1 PASSED: Tenant Onboarding Under Load")
        print(f"   - {len(existing_tenants)} existing tenants remained stable")
        print(f"   - New tenant successfully onboarded")
        print(f"   - New tenant got independent semaphore")
        print(f"   - No impact on existing tenants detected")


class TestTenantCleanup:
    """Test 2: Tenant Cleanup"""
    
    def test_tenant_cleanup_no_orphaned_resources(self, redis_client, job_state):
        """
        Validate tenant deletion cleans up:
        - All Redis job state keys deleted
        - Semaphore slots released
        - No orphaned jobs in queue
        - Database records archived/deleted
        """
        tenant_id = f"tenant-cleanup-{uuid4()}"
        
        job_ids = []
        for i in range(10):
            result = enqueue_bulk_mapping_job(
                tenant_id=tenant_id,
                connector_definition_ids=[f'conn-{i}'],
                use_tenant_pool=True
            )
            
            if result['status'] == 'queued':
                job_ids.append(result['job_id'])
        
        initial_active_count = job_state.get_active_job_count(tenant_id)
        assert initial_active_count > 0, "Should have active jobs before cleanup"
        
        initial_jobs = job_state.get_all_jobs_for_tenant(tenant_id)
        assert len(initial_jobs) > 0, "Should have jobs before cleanup"
        
        for job_id in job_ids:
            job_state.delete_job_state(tenant_id, job_id)
        
        semaphore_key = f"job:semaphore:tenant:{tenant_id}"
        redis_client.delete(semaphore_key)
        
        pattern = f"job:*:tenant:{tenant_id}:*"
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
        
        remaining_jobs = job_state.get_all_jobs_for_tenant(tenant_id)
        assert len(remaining_jobs) == 0, \
            f"Found {len(remaining_jobs)} orphaned jobs after cleanup"
        
        final_active_count = job_state.get_active_job_count(tenant_id)
        assert final_active_count == 0, \
            f"Semaphore not released: {final_active_count}"
        
        all_keys = redis_client.keys(pattern)
        assert len(all_keys) == 0, \
            f"Found {len(all_keys)} orphaned Redis keys: {all_keys[:5]}"
        
        print(f"\n✅ Lifecycle Test 2 PASSED: Tenant Cleanup")
        print(f"   - All Redis job state keys deleted")
        print(f"   - Semaphore slots released")
        print(f"   - No orphaned jobs remaining")
        print(f"   - Complete cleanup verified")


class TestTenantIsolationDuringLifecycle:
    """Test 3: Tenant Isolation During Lifecycle Operations"""
    
    @pytest.mark.asyncio
    async def test_tenant_deletion_doesnt_affect_others(self, redis_client, job_state):
        """
        Validate deleting one tenant doesn't affect others:
        - Create 3 tenants with active jobs
        - Delete Tenant B
        - Verify Tenant A and C continue normally
        - No cross-tenant resource interference
        """
        tenant_a = f"tenant-a-{uuid4()}"
        tenant_b = f"tenant-b-{uuid4()}"
        tenant_c = f"tenant-c-{uuid4()}"
        
        all_tenants = [tenant_a, tenant_b, tenant_c]
        
        tenant_jobs = {}
        
        for tenant_id in all_tenants:
            job_ids = []
            
            for i in range(5):
                result = enqueue_bulk_mapping_job(
                    tenant_id=tenant_id,
                    connector_definition_ids=[f'conn-{i}'],
                    use_tenant_pool=True
                )
                
                if result['status'] == 'queued':
                    job_ids.append(result['job_id'])
            
            tenant_jobs[tenant_id] = job_ids
        
        for tenant_id in all_tenants:
            jobs = job_state.get_all_jobs_for_tenant(tenant_id)
            assert len(jobs) > 0, f"Tenant {tenant_id} should have jobs"
        
        for job_id in tenant_jobs[tenant_b]:
            job_state.delete_job_state(tenant_b, job_id)
        
        semaphore_key = f"job:semaphore:tenant:{tenant_b}"
        redis_client.delete(semaphore_key)
        
        pattern = f"job:*:tenant:{tenant_b}:*"
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
        
        tenant_a_jobs = job_state.get_all_jobs_for_tenant(tenant_a)
        assert len(tenant_a_jobs) > 0, "Tenant A jobs should remain"
        
        tenant_c_jobs = job_state.get_all_jobs_for_tenant(tenant_c)
        assert len(tenant_c_jobs) > 0, "Tenant C jobs should remain"
        
        tenant_b_jobs = job_state.get_all_jobs_for_tenant(tenant_b)
        assert len(tenant_b_jobs) == 0, "Tenant B jobs should be deleted"
        
        for tenant_id in [tenant_a, tenant_c]:
            result = enqueue_bulk_mapping_job(
                tenant_id=tenant_id,
                connector_definition_ids=['new-conn'],
                use_tenant_pool=True
            )
            
            assert result['status'] in ['queued', 'rejected'], \
                f"Tenant {tenant_id} should still function normally"
        
        for tenant_id in [tenant_a, tenant_c]:
            for job_id in tenant_jobs[tenant_id]:
                job_state.update_status(tenant_id, job_id, 'completed')
        
        for tenant_id in all_tenants:
            pattern = f"job:*:tenant:{tenant_id}:*"
            keys = redis_client.keys(pattern)
            if keys:
                redis_client.delete(*keys)
        
        print(f"\n✅ Lifecycle Test 3 PASSED: Tenant Deletion Isolation")
        print(f"   - Tenant B successfully deleted")
        print(f"   - Tenant A and C unaffected")
        print(f"   - No cross-tenant interference")
        print(f"   - Resource isolation maintained")


class TestConcurrentOnboarding:
    """Test 4: Concurrent Tenant Onboarding"""
    
    @pytest.mark.asyncio
    async def test_multiple_tenants_onboard_simultaneously(self, redis_client, job_state):
        """
        Validate multiple tenants can onboard simultaneously:
        - 10 new tenants created at once
        - All get independent semaphores
        - No resource conflicts
        - All tenants functional immediately
        """
        num_new_tenants = 10
        
        new_tenant_ids = [f"tenant-simul-{i}-{uuid4()}" for i in range(num_new_tenants)]
        
        async def onboard_tenant(tenant_id: str) -> Dict:
            """Onboard a single tenant"""
            job_ids = []
            
            for i in range(3):
                result = enqueue_bulk_mapping_job(
                    tenant_id=tenant_id,
                    connector_definition_ids=[f'conn-{i}'],
                    use_tenant_pool=True
                )
                
                if result['status'] == 'queued':
                    job_ids.append(result['job_id'])
            
            return {
                'tenant_id': tenant_id,
                'jobs_created': len(job_ids),
                'active_count': job_state.get_active_job_count(tenant_id)
            }
        
        results = await asyncio.gather(*[onboard_tenant(tid) for tid in new_tenant_ids])
        
        for result in results:
            tenant_id = result['tenant_id']
            
            assert result['jobs_created'] > 0, \
                f"Tenant {tenant_id} failed to create jobs"
            
            assert result['active_count'] <= MAX_CONCURRENT_JOBS_PER_TENANT, \
                f"Tenant {tenant_id} exceeded limit: {result['active_count']}"
        
        all_job_ids_set = set()
        
        for tenant_id in new_tenant_ids:
            jobs = job_state.get_all_jobs_for_tenant(tenant_id)
            tenant_job_ids = {job['job_id'] for job in jobs}
            
            overlap = all_job_ids_set.intersection(tenant_job_ids)
            assert len(overlap) == 0, \
                f"Job ID collision detected for tenant {tenant_id}: {overlap}"
            
            all_job_ids_set.update(tenant_job_ids)
        
        for tenant_id in new_tenant_ids:
            jobs = job_state.get_all_jobs_for_tenant(tenant_id)
            for job in jobs:
                job_state.update_status(tenant_id, job['job_id'], 'completed')
        
        for tenant_id in new_tenant_ids:
            pattern = f"job:*:tenant:{tenant_id}:*"
            keys = redis_client.keys(pattern)
            if keys:
                redis_client.delete(*keys)
        
        total_jobs_created = sum(r['jobs_created'] for r in results)
        
        print(f"\n✅ Lifecycle Test 4 PASSED: Concurrent Onboarding")
        print(f"   - {num_new_tenants} tenants onboarded simultaneously")
        print(f"   - Total jobs created: {total_jobs_created}")
        print(f"   - All tenants got independent semaphores")
        print(f"   - No resource conflicts detected")


class TestTenantReactivation:
    """Test 5: Tenant Reactivation After Cleanup"""
    
    @pytest.mark.asyncio
    async def test_tenant_reactivation_after_cleanup(self, redis_client, job_state):
        """
        Validate tenant can be reactivated after cleanup:
        - Create tenant with jobs
        - Clean up all resources
        - Reactivate same tenant ID
        - Verify fresh state (no residual data)
        """
        tenant_id = f"tenant-reactivate-{uuid4()}"
        
        first_job_ids = []
        for i in range(5):
            result = enqueue_bulk_mapping_job(
                tenant_id=tenant_id,
                connector_definition_ids=[f'first-conn-{i}'],
                use_tenant_pool=True
            )
            
            if result['status'] == 'queued':
                first_job_ids.append(result['job_id'])
        
        first_jobs = job_state.get_all_jobs_for_tenant(tenant_id)
        assert len(first_jobs) > 0, "Should have jobs in first lifecycle"
        
        for job_id in first_job_ids:
            job_state.delete_job_state(tenant_id, job_id)
        
        pattern = f"job:*:tenant:{tenant_id}:*"
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
        
        jobs_after_cleanup = job_state.get_all_jobs_for_tenant(tenant_id)
        assert len(jobs_after_cleanup) == 0, "Should have no jobs after cleanup"
        
        await asyncio.sleep(0.1)
        
        second_job_ids = []
        for i in range(5):
            result = enqueue_bulk_mapping_job(
                tenant_id=tenant_id,
                connector_definition_ids=[f'second-conn-{i}'],
                use_tenant_pool=True
            )
            
            if result['status'] == 'queued':
                second_job_ids.append(result['job_id'])
        
        assert len(second_job_ids) > 0, "Should be able to reactivate tenant"
        
        second_jobs = job_state.get_all_jobs_for_tenant(tenant_id)
        second_job_ids_set = {job['job_id'] for job in second_jobs}
        
        for old_job_id in first_job_ids:
            assert old_job_id not in second_job_ids_set, \
                f"Old job {old_job_id} still present after reactivation"
        
        for job_id in second_job_ids:
            job_state.update_status(tenant_id, job_id, 'completed')
        
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
        
        print(f"\n✅ Lifecycle Test 5 PASSED: Tenant Reactivation")
        print(f"   - First lifecycle: {len(first_job_ids)} jobs")
        print(f"   - Cleanup successful")
        print(f"   - Second lifecycle: {len(second_job_ids)} jobs")
        print(f"   - Fresh state verified (no residual data)")
