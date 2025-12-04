"""
Load and Performance Tests for Distributed Job Queue

Tests:
- Concurrent job submission
- Semaphore enforcement
- Job state persistence
- Progress tracking
- Resource monitoring
"""

import pytest
import asyncio
import time
from uuid import uuid4
from services.mapping_intelligence.job_enqueue import enqueue_bulk_mapping_job, get_job_status
from services.mapping_intelligence.job_state import BulkMappingJobState, MAX_CONCURRENT_JOBS_PER_TENANT
from services.mapping_intelligence.worker_pools import TenantWorkerPool
from services.mapping_intelligence.resource_monitor import ResourceMonitor
from services.mapping_intelligence.reconciliation import JobReconciliationService
from shared.redis_client import get_redis_client


@pytest.fixture
def test_tenant_id():
    """Generate unique tenant ID for each test"""
    return f"test-tenant-{uuid4()}"


@pytest.fixture
def redis_client():
    """Get Redis client and skip if unavailable"""
    client = get_redis_client()
    if not client:
        pytest.skip("Redis not available")
    return client


@pytest.fixture
def job_state(redis_client):
    """Create BulkMappingJobState instance"""
    return BulkMappingJobState(redis_client)


@pytest.fixture
def cleanup_tenant(redis_client, test_tenant_id):
    """Cleanup tenant data after test"""
    yield
    
    pattern = f"job:*:tenant:{test_tenant_id}:*"
    keys = redis_client.keys(pattern)
    if keys:
        redis_client.delete(*keys)


class TestJobState:
    """Test job state management"""
    
    def test_semaphore_reservation(self, job_state, test_tenant_id, cleanup_tenant):
        """Test atomic semaphore reservation"""
        for i in range(MAX_CONCURRENT_JOBS_PER_TENANT):
            assert job_state.try_reserve_job_slot(test_tenant_id), f"Failed to reserve slot {i+1}"
        
        assert not job_state.try_reserve_job_slot(test_tenant_id), "Should reject beyond limit"
        
        active_count = job_state.get_active_job_count(test_tenant_id)
        assert active_count == MAX_CONCURRENT_JOBS_PER_TENANT
    
    def test_semaphore_release(self, job_state, test_tenant_id, cleanup_tenant):
        """Test semaphore slot release"""
        job_state.try_reserve_job_slot(test_tenant_id)
        job_state.release_job_slot(test_tenant_id)
        
        active_count = job_state.get_active_job_count(test_tenant_id)
        assert active_count == 0
    
    def test_job_state_persistence(self, job_state, test_tenant_id, cleanup_tenant):
        """Test job state save and retrieve"""
        job_id = str(uuid4())
        
        state = {
            'job_id': job_id,
            'status': 'pending',
            'processed_fields': 0,
            'total_fields': 100
        }
        
        job_state.save_job_state(test_tenant_id, job_id, state)
        
        retrieved = job_state.get_job_state(test_tenant_id, job_id)
        
        assert retrieved is not None
        assert retrieved['job_id'] == job_id
        assert retrieved['status'] == 'pending'
        assert retrieved['total_fields'] == 100
    
    def test_status_update(self, job_state, test_tenant_id, cleanup_tenant):
        """Test job status updates"""
        job_id = str(uuid4())
        
        initial_state = {
            'job_id': job_id,
            'status': 'pending',
            'processed_fields': 0
        }
        
        job_state.save_job_state(test_tenant_id, job_id, initial_state)
        
        job_state.update_status(test_tenant_id, job_id, 'running')
        
        state = job_state.get_job_state(test_tenant_id, job_id)
        assert state['status'] == 'running'
        assert 'started_at' in state
    
    def test_error_handling(self, job_state, test_tenant_id, cleanup_tenant):
        """Test error state handling"""
        job_id = str(uuid4())
        
        job_state.save_job_state(test_tenant_id, job_id, {'job_id': job_id, 'status': 'running'})
        job_state.set_error(test_tenant_id, job_id, "Test error")
        
        state = job_state.get_job_state(test_tenant_id, job_id)
        
        assert state['status'] == 'failed'
        assert state['error_message'] == "Test error"
        assert 'completed_at' in state


class TestJobEnqueue:
    """Test job enqueue functionality"""
    
    def test_enqueue_success(self, test_tenant_id, cleanup_tenant):
        """Test successful job enqueue"""
        result = enqueue_bulk_mapping_job(
            tenant_id=test_tenant_id,
            connector_definition_ids=['conn-1', 'conn-2'],
            options={'test': True},
            use_tenant_pool=True
        )
        
        assert result['status'] == 'queued'
        assert 'job_id' in result
        assert result['tenant_id'] == test_tenant_id
        assert result['connector_count'] == 2
    
    def test_enqueue_beyond_limit(self, test_tenant_id, cleanup_tenant):
        """Test rejection when exceeding concurrent job limit"""
        for i in range(MAX_CONCURRENT_JOBS_PER_TENANT):
            result = enqueue_bulk_mapping_job(
                tenant_id=test_tenant_id,
                connector_definition_ids=['conn'],
                use_tenant_pool=True
            )
            assert result['status'] == 'queued'
        
        result = enqueue_bulk_mapping_job(
            tenant_id=test_tenant_id,
            connector_definition_ids=['conn'],
            use_tenant_pool=True
        )
        
        assert result['status'] == 'rejected'
        assert 'error' in result


class TestWorkerPools:
    """Test tenant worker pools"""
    
    def test_queue_creation(self, redis_client, test_tenant_id):
        """Test per-tenant queue creation"""
        pool = TenantWorkerPool(redis_client)
        
        queue = pool.get_queue(test_tenant_id)
        
        assert queue is not None
        assert f"tenant:{test_tenant_id}:mappings" in queue.name
    
    def test_queue_stats(self, redis_client, test_tenant_id):
        """Test queue statistics"""
        pool = TenantWorkerPool(redis_client)
        
        stats = pool.get_queue_stats(test_tenant_id)
        
        assert stats['tenant_id'] == test_tenant_id
        assert 'queued_jobs' in stats
        assert 'finished_jobs' in stats


class TestResourceMonitor:
    """Test resource monitoring"""
    
    def test_get_current_metrics(self, redis_client):
        """Test current metrics collection"""
        monitor = ResourceMonitor(redis_client)
        
        metrics = monitor.get_current_metrics()
        
        assert 'timestamp' in metrics
        assert 'cpu_percent' in metrics
        assert 'memory_rss_mb' in metrics
        assert 'system_memory_percent' in metrics
    
    def test_record_job_metrics(self, redis_client, test_tenant_id, cleanup_tenant):
        """Test job metrics recording"""
        monitor = ResourceMonitor(redis_client)
        job_id = str(uuid4())
        
        monitor.record_job_metrics(test_tenant_id, job_id)
        
        metrics = monitor.get_job_metrics(test_tenant_id, job_id)
        
        assert metrics is not None
        assert 'cpu_percent' in metrics
    
    def test_resource_availability(self, redis_client):
        """Test resource availability check"""
        monitor = ResourceMonitor(redis_client)
        
        available = monitor.check_resource_availability()
        
        assert isinstance(available, bool)


class TestReconciliation:
    """Test job reconciliation"""
    
    def test_semaphore_reconciliation(self, redis_client, job_state, test_tenant_id, cleanup_tenant):
        """Test semaphore reconciliation"""
        job_state.try_reserve_job_slot(test_tenant_id)
        job_state.try_reserve_job_slot(test_tenant_id)
        
        reconciler = JobReconciliationService(redis_client)
        result = reconciler.reconcile_semaphores(test_tenant_id)
        
        assert 'tenant_id' in result
        assert 'previous_count' in result
        assert 'actual_count' in result
    
    def test_stale_job_detection(self, redis_client, job_state, test_tenant_id, cleanup_tenant):
        """Test stale job detection"""
        job_id = str(uuid4())
        
        from datetime import datetime, timedelta
        
        stale_time = (datetime.utcnow() - timedelta(minutes=35)).isoformat()
        
        job_state.save_job_state(test_tenant_id, job_id, {
            'job_id': job_id,
            'status': 'running',
            'started_at': stale_time
        })
        
        reconciler = JobReconciliationService(redis_client)
        stale_jobs = reconciler.detect_stale_jobs(test_tenant_id)
        
        assert len(stale_jobs) >= 1
        assert any(j['job_id'] == job_id for j in stale_jobs)


@pytest.mark.asyncio
async def test_concurrent_job_submission(test_tenant_id, cleanup_tenant):
    """Test concurrent job submissions"""
    num_concurrent = 3
    
    async def submit_job(i):
        return enqueue_bulk_mapping_job(
            tenant_id=test_tenant_id,
            connector_definition_ids=[f'conn-{i}'],
            use_tenant_pool=True
        )
    
    results = await asyncio.gather(*[submit_job(i) for i in range(num_concurrent)])
    
    successful = [r for r in results if r['status'] == 'queued']
    
    assert len(successful) <= MAX_CONCURRENT_JOBS_PER_TENANT
    assert all('job_id' in r for r in successful)


@pytest.mark.asyncio
async def test_job_status_retrieval(test_tenant_id, cleanup_tenant):
    """Test job status retrieval"""
    result = enqueue_bulk_mapping_job(
        tenant_id=test_tenant_id,
        connector_definition_ids=['conn-1'],
        use_tenant_pool=True
    )
    
    assert result['status'] == 'queued'
    job_id = result['job_id']
    
    await asyncio.sleep(0.5)
    
    status = get_job_status(test_tenant_id, job_id)
    
    assert status is not None
    assert status['job_id'] == job_id
    assert status['tenant_id'] == test_tenant_id
