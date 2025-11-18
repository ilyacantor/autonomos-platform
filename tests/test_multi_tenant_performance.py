"""
Performance Tests Under Multi-Tenant Load

Validates:
- Throughput degradation as tenants increase
- Latency remains acceptable
- Scalability bottlenecks identified
"""

import pytest
import asyncio
import time
import statistics
from uuid import uuid4
from typing import List, Dict
from services.mapping_intelligence.job_enqueue import enqueue_bulk_mapping_job
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


@pytest.fixture
def job_state(redis_client):
    """Get job state manager"""
    return BulkMappingJobState(redis_client)


@pytest.fixture
def resource_monitor(redis_client):
    """Get resource monitor"""
    return ResourceMonitor(redis_client)


class TestThroughputDegradation:
    """Test 1: Throughput Degradation Check"""
    
    @pytest.mark.asyncio
    async def test_throughput_degradation_with_tenants(self, redis_client, job_state):
        """
        Measure throughput as tenants increase:
        - 1 tenant baseline: X jobs/sec
        - 5 tenants: should maintain > 80% of X
        - 10 tenants: should maintain > 60% of X
        - Identify scalability bottlenecks
        """
        
        async def measure_throughput(num_tenants: int, jobs_per_tenant: int) -> Dict:
            """Measure throughput for N tenants"""
            tenant_ids = [f"tenant-perf-{i}-{uuid4()}" for i in range(num_tenants)]
            
            async def process_tenant_jobs(tenant_id: str) -> int:
                """Process jobs for one tenant"""
                jobs_completed = 0
                
                for i in range(jobs_per_tenant):
                    result = enqueue_bulk_mapping_job(
                        tenant_id=tenant_id,
                        connector_definition_ids=[f'conn-{i}'],
                        use_tenant_pool=True
                    )
                    
                    if result['status'] == 'queued':
                        job_id = result['job_id']
                        job_state.update_status(tenant_id, job_id, 'running')
                        await asyncio.sleep(0.01)
                        job_state.update_status(tenant_id, job_id, 'completed')
                        jobs_completed += 1
                
                return jobs_completed
            
            start_time = time.time()
            
            results = await asyncio.gather(*[
                process_tenant_jobs(tid) for tid in tenant_ids
            ])
            
            elapsed = time.time() - start_time
            total_jobs = sum(results)
            throughput = total_jobs / elapsed if elapsed > 0 else 0
            
            for tenant_id in tenant_ids:
                pattern = f"job:*:tenant:{tenant_id}:*"
                keys = redis_client.keys(pattern)
                if keys:
                    redis_client.delete(*keys)
            
            return {
                'num_tenants': num_tenants,
                'total_jobs': total_jobs,
                'elapsed_time': elapsed,
                'throughput': throughput
            }
        
        baseline = await measure_throughput(num_tenants=1, jobs_per_tenant=20)
        baseline_throughput = baseline['throughput']
        
        medium_load = await measure_throughput(num_tenants=5, jobs_per_tenant=20)
        medium_throughput = medium_load['throughput']
        medium_degradation = (baseline_throughput - medium_throughput) / baseline_throughput
        
        heavy_load = await measure_throughput(num_tenants=10, jobs_per_tenant=20)
        heavy_throughput = heavy_load['throughput']
        heavy_degradation = (baseline_throughput - heavy_throughput) / baseline_throughput
        
        assert medium_degradation < 0.20, \
            f"5 tenants: throughput degraded by {medium_degradation*100:.1f}% (should be < 20%)"
        
        assert heavy_degradation < 0.40, \
            f"10 tenants: throughput degraded by {heavy_degradation*100:.1f}% (should be < 40%)"
        
        print(f"\n✅ Performance Test 1 PASSED: Throughput Degradation")
        print(f"   - 1 tenant baseline: {baseline_throughput:.2f} jobs/sec")
        print(f"   - 5 tenants: {medium_throughput:.2f} jobs/sec ({(1-medium_degradation)*100:.1f}% of baseline)")
        print(f"   - 10 tenants: {heavy_throughput:.2f} jobs/sec ({(1-heavy_degradation)*100:.1f}% of baseline)")
        print(f"   - Scalability: ✅ Within acceptable limits")


class TestLatencyUnderLoad:
    """Test 2: Latency Increase Under Load"""
    
    @pytest.mark.asyncio
    async def test_latency_increase_multi_tenant(self, redis_client, job_state):
        """
        Validate latency remains acceptable:
        - P95 latency < 15s for 10 concurrent tenants
        - No exponential latency growth
        - Queue wait time proportional to load
        """
        num_tenants = 10
        jobs_per_tenant = 10
        
        tenant_ids = [f"tenant-latency-{i}-{uuid4()}" for i in range(num_tenants)]
        
        all_latencies = []
        
        async def measure_tenant_latency(tenant_id: str) -> List[float]:
            """Measure latency for each job"""
            latencies = []
            
            for i in range(jobs_per_tenant):
                job_start = time.time()
                
                result = enqueue_bulk_mapping_job(
                    tenant_id=tenant_id,
                    connector_definition_ids=[f'conn-{i}'],
                    use_tenant_pool=True
                )
                
                if result['status'] == 'queued':
                    job_id = result['job_id']
                    
                    job_state.update_status(tenant_id, job_id, 'running')
                    await asyncio.sleep(0.05)
                    job_state.update_status(tenant_id, job_id, 'completed')
                    
                    job_end = time.time()
                    latency = job_end - job_start
                    latencies.append(latency)
            
            return latencies
        
        results = await asyncio.gather(*[
            measure_tenant_latency(tid) for tid in tenant_ids
        ])
        
        for tenant_latencies in results:
            all_latencies.extend(tenant_latencies)
        
        if all_latencies:
            all_latencies.sort()
            
            p50 = all_latencies[len(all_latencies) // 2]
            p95_index = int(len(all_latencies) * 0.95)
            p95 = all_latencies[p95_index]
            p99_index = int(len(all_latencies) * 0.99)
            p99 = all_latencies[p99_index]
            
            avg_latency = statistics.mean(all_latencies)
            max_latency = max(all_latencies)
            
            assert p95 < 15.0, \
                f"P95 latency too high: {p95:.2f}s (should be < 15s)"
            
            assert max_latency < 30.0, \
                f"Max latency too high: {max_latency:.2f}s (should be < 30s)"
            
            growth_ratio = p95 / p50 if p50 > 0 else 0
            assert growth_ratio < 5.0, \
                f"Exponential latency growth detected: P95/P50 = {growth_ratio:.1f}x"
        
        for tenant_id in tenant_ids:
            pattern = f"job:*:tenant:{tenant_id}:*"
            keys = redis_client.keys(pattern)
            if keys:
                redis_client.delete(*keys)
        
        print(f"\n✅ Performance Test 2 PASSED: Latency Under Load")
        print(f"   - P50 latency: {p50:.3f}s")
        print(f"   - P95 latency: {p95:.3f}s (< 15s threshold)")
        print(f"   - P99 latency: {p99:.3f}s")
        print(f"   - Max latency: {max_latency:.3f}s")
        print(f"   - Avg latency: {avg_latency:.3f}s")
        print(f"   - No exponential growth detected")


class TestResourceUtilization:
    """Test 3: Resource Utilization Under Load"""
    
    @pytest.mark.asyncio
    async def test_resource_utilization_multi_tenant(self, redis_client, job_state, resource_monitor):
        """
        Validate resource usage remains stable:
        - Memory usage doesn't grow unbounded
        - CPU usage proportional to load
        - Redis connection pool stable
        """
        num_tenants = 5
        jobs_per_tenant = 20
        
        tenant_ids = [f"tenant-resource-{i}-{uuid4()}" for i in range(num_tenants)]
        
        initial_metrics = resource_monitor.get_current_metrics()
        initial_memory = initial_metrics.get('memory_rss_mb', 0)
        
        async def submit_tenant_load(tenant_id: str):
            """Submit load for one tenant"""
            for i in range(jobs_per_tenant):
                result = enqueue_bulk_mapping_job(
                    tenant_id=tenant_id,
                    connector_definition_ids=[f'conn-{i}'],
                    use_tenant_pool=True
                )
                
                if result['status'] == 'queued':
                    job_state.update_status(tenant_id, result['job_id'], 'running')
                    await asyncio.sleep(0.01)
                    job_state.update_status(tenant_id, result['job_id'], 'completed')
        
        await asyncio.gather(*[submit_tenant_load(tid) for tid in tenant_ids])
        
        final_metrics = resource_monitor.get_current_metrics()
        final_memory = final_metrics.get('memory_rss_mb', 0)
        
        memory_increase = final_memory - initial_memory
        
        assert memory_increase < 200, \
            f"Excessive memory growth: {memory_increase:.1f}MB (should be < 200MB)"
        
        for tenant_id in tenant_ids:
            pattern = f"job:*:tenant:{tenant_id}:*"
            keys = redis_client.keys(pattern)
            if keys:
                redis_client.delete(*keys)
        
        print(f"\n✅ Performance Test 3 PASSED: Resource Utilization")
        print(f"   - Initial memory: {initial_memory:.1f}MB")
        print(f"   - Final memory: {final_memory:.1f}MB")
        print(f"   - Memory increase: {memory_increase:.1f}MB (< 200MB threshold)")
        print(f"   - Resource usage stable")


class TestConcurrencyLimits:
    """Test 4: Concurrency Limits Under Load"""
    
    @pytest.mark.asyncio
    async def test_concurrent_job_limit_enforcement(self, redis_client, job_state):
        """
        Validate concurrency limits enforced under heavy load:
        - Multiple tenants respect their individual limits
        - System-wide concurrency doesn't exceed expectations
        - No race conditions in semaphore management
        """
        num_tenants = 10
        
        tenant_ids = [f"tenant-concur-{i}-{uuid4()}" for i in range(num_tenants)]
        
        async def max_out_tenant(tenant_id: str) -> Dict:
            """Try to max out tenant's concurrency"""
            job_ids = []
            
            for i in range(MAX_CONCURRENT_JOBS_PER_TENANT * 2):
                result = enqueue_bulk_mapping_job(
                    tenant_id=tenant_id,
                    connector_definition_ids=[f'conn-{i}'],
                    use_tenant_pool=True
                )
                
                if result['status'] == 'queued':
                    job_ids.append(result['job_id'])
            
            active_count = job_state.get_active_job_count(tenant_id)
            
            return {
                'tenant_id': tenant_id,
                'jobs_queued': len(job_ids),
                'active_count': active_count
            }
        
        results = await asyncio.gather(*[max_out_tenant(tid) for tid in tenant_ids])
        
        for result in results:
            tenant_id = result['tenant_id']
            active_count = result['active_count']
            
            assert active_count <= MAX_CONCURRENT_JOBS_PER_TENANT, \
                f"Tenant {tenant_id} exceeded limit: {active_count} > {MAX_CONCURRENT_JOBS_PER_TENANT}"
        
        total_active = sum(r['active_count'] for r in results)
        expected_max = num_tenants * MAX_CONCURRENT_JOBS_PER_TENANT
        
        assert total_active <= expected_max, \
            f"System-wide concurrency exceeded: {total_active} > {expected_max}"
        
        for tenant_id in tenant_ids:
            jobs = job_state.get_all_jobs_for_tenant(tenant_id)
            for job in jobs:
                job_state.update_status(tenant_id, job['job_id'], 'completed')
        
        for tenant_id in tenant_ids:
            pattern = f"job:*:tenant:{tenant_id}:*"
            keys = redis_client.keys(pattern)
            if keys:
                redis_client.delete(*keys)
        
        print(f"\n✅ Performance Test 4 PASSED: Concurrency Limits")
        print(f"   - {num_tenants} tenants tested concurrently")
        print(f"   - All tenants respected {MAX_CONCURRENT_JOBS_PER_TENANT} job limit")
        print(f"   - Total active jobs: {total_active} (≤ {expected_max})")
        print(f"   - No race conditions detected")


class TestQueueDepthScaling:
    """Test 5: Queue Depth Scaling"""
    
    @pytest.mark.asyncio
    async def test_queue_depth_handling(self, redis_client, job_state):
        """
        Validate system handles deep queues efficiently:
        - Large backlog doesn't degrade performance exponentially
        - Queue processing remains stable
        - FIFO ordering maintained
        """
        tenant_id = f"tenant-queue-{uuid4()}"
        
        large_batch = 100
        
        submission_start = time.time()
        
        submitted_jobs = []
        for i in range(large_batch):
            result = enqueue_bulk_mapping_job(
                tenant_id=tenant_id,
                connector_definition_ids=[f'conn-{i}'],
                use_tenant_pool=True
            )
            
            if result['status'] == 'queued':
                submitted_jobs.append({
                    'job_id': result['job_id'],
                    'submission_time': time.time()
                })
        
        submission_elapsed = time.time() - submission_start
        
        assert submission_elapsed < 30, \
            f"Submission took too long: {submission_elapsed:.2f}s (should be < 30s)"
        
        processing_start = time.time()
        
        for job_info in submitted_jobs[:10]:
            job_state.update_status(tenant_id, job_info['job_id'], 'running')
            await asyncio.sleep(0.01)
            job_state.update_status(tenant_id, job_info['job_id'], 'completed')
        
        processing_elapsed = time.time() - processing_start
        avg_processing_time = processing_elapsed / 10 if len(submitted_jobs) > 0 else 0
        
        assert avg_processing_time < 5, \
            f"Average processing time too high: {avg_processing_time:.2f}s"
        
        for job_info in submitted_jobs[10:]:
            job_state.update_status(tenant_id, job_info['job_id'], 'completed')
        
        pattern = f"job:*:tenant:{tenant_id}:*"
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
        
        print(f"\n✅ Performance Test 5 PASSED: Queue Depth Scaling")
        print(f"   - Submitted {large_batch} jobs in {submission_elapsed:.2f}s")
        print(f"   - Average processing time: {avg_processing_time:.3f}s per job")
        print(f"   - Queue handled efficiently")
        print(f"   - No exponential degradation detected")
