#!/usr/bin/env python3
"""
Continuous Multi-Tenant Load Test (Soak Test)

Features:
- Run indefinitely or for specified duration
- Simulate 5-10 tenants with varying workloads
- Collect metrics every 60s
- Detect anomalies (semaphore leaks, memory growth, error spikes)
- Generate real-time dashboard data
"""

import sys
import time
import json
import asyncio
import argparse
import signal
from datetime import datetime
from typing import Dict, List
from uuid import uuid4
from statistics import mean, median
from services.mapping_intelligence.job_enqueue import enqueue_bulk_mapping_job
from services.mapping_intelligence.job_state import BulkMappingJobState, MAX_CONCURRENT_JOBS_PER_TENANT
from services.mapping_intelligence.resource_monitor import ResourceMonitor
from services.mapping_intelligence.reconciliation import JobReconciliationService
from shared.redis_client import get_redis_client


class ContinuousLoadTester:
    """Continuous multi-tenant load tester"""
    
    def __init__(self, num_tenants: int = 5, duration_minutes: int = None):
        self.num_tenants = num_tenants
        self.duration_minutes = duration_minutes
        self.running = True
        
        self.redis_client = get_redis_client()
        if not self.redis_client:
            raise RuntimeError("Redis client not available")
        
        self.job_state = BulkMappingJobState(self.redis_client)
        self.resource_monitor = ResourceMonitor(self.redis_client)
        self.reconciliation_service = JobReconciliationService(self.redis_client)
        
        self.tenant_ids = [f"load-test-{i}-{uuid4()}" for i in range(num_tenants)]
        
        self.metrics_history = []
        self.anomalies = []
        
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signal"""
        print("\n\n🛑 Shutdown signal received, stopping load test...")
        self.running = False
    
    async def simulate_tenant_workload(self, tenant_id: str, iteration: int) -> Dict:
        """Simulate workload for a single tenant"""
        workload_type = iteration % 3
        
        jobs_submitted = 0
        jobs_completed = 0
        jobs_rejected = 0
        errors = []
        
        if workload_type == 0:
            num_jobs = 5
            job_duration = 0.05
        elif workload_type == 1:
            num_jobs = 10
            job_duration = 0.02
        else:
            num_jobs = 3
            job_duration = 0.1
        
        for i in range(num_jobs):
            try:
                result = enqueue_bulk_mapping_job(
                    tenant_id=tenant_id,
                    connector_definition_ids=[f'conn-{iteration}-{i}'],
                    use_tenant_pool=True
                )
                
                jobs_submitted += 1
                
                if result['status'] == 'queued':
                    job_id = result['job_id']
                    
                    self.job_state.update_status(tenant_id, job_id, 'running')
                    await asyncio.sleep(job_duration)
                    self.job_state.update_status(tenant_id, job_id, 'completed')
                    
                    jobs_completed += 1
                else:
                    jobs_rejected += 1
            
            except Exception as e:
                errors.append(str(e))
        
        return {
            'tenant_id': tenant_id,
            'workload_type': workload_type,
            'jobs_submitted': jobs_submitted,
            'jobs_completed': jobs_completed,
            'jobs_rejected': jobs_rejected,
            'error_count': len(errors),
            'errors': errors
        }
    
    async def run_iteration(self, iteration: int) -> Dict:
        """Run a single iteration of the load test"""
        iteration_start = time.time()
        
        workload_results = await asyncio.gather(*[
            self.simulate_tenant_workload(tid, iteration) 
            for tid in self.tenant_ids
        ])
        
        iteration_elapsed = time.time() - iteration_start
        
        total_submitted = sum(r['jobs_submitted'] for r in workload_results)
        total_completed = sum(r['jobs_completed'] for r in workload_results)
        total_rejected = sum(r['jobs_rejected'] for r in workload_results)
        total_errors = sum(r['error_count'] for r in workload_results)
        
        return {
            'iteration': iteration,
            'elapsed_time': iteration_elapsed,
            'total_submitted': total_submitted,
            'total_completed': total_completed,
            'total_rejected': total_rejected,
            'total_errors': total_errors,
            'per_tenant_results': workload_results
        }
    
    def collect_metrics(self, iteration_result: Dict) -> Dict:
        """Collect system and tenant metrics"""
        resource_metrics = self.resource_monitor.get_current_metrics()
        
        tenant_metrics = {}
        for tenant_id in self.tenant_ids:
            active_count = self.job_state.get_active_job_count(tenant_id)
            jobs = self.job_state.get_all_jobs_for_tenant(tenant_id)
            
            tenant_metrics[tenant_id] = {
                'active_jobs': active_count,
                'total_jobs_in_state': len(jobs)
            }
        
        metrics = {
            'timestamp': datetime.utcnow().isoformat(),
            'iteration': iteration_result['iteration'],
            'workload': {
                'jobs_submitted': iteration_result['total_submitted'],
                'jobs_completed': iteration_result['total_completed'],
                'jobs_rejected': iteration_result['total_rejected'],
                'error_count': iteration_result['total_errors'],
                'elapsed_time': iteration_result['elapsed_time']
            },
            'resources': resource_metrics,
            'tenants': tenant_metrics
        }
        
        return metrics
    
    def detect_anomalies(self, current_metrics: Dict) -> List[Dict]:
        """Detect anomalies in current metrics"""
        anomalies = []
        
        for tenant_id, tenant_data in current_metrics['tenants'].items():
            if tenant_data['active_jobs'] > MAX_CONCURRENT_JOBS_PER_TENANT:
                anomalies.append({
                    'type': 'semaphore_leak',
                    'tenant_id': tenant_id,
                    'active_jobs': tenant_data['active_jobs'],
                    'limit': MAX_CONCURRENT_JOBS_PER_TENANT,
                    'severity': 'critical'
                })
        
        if len(self.metrics_history) >= 5:
            recent_memory = [m['resources'].get('memory_rss_mb', 0) for m in self.metrics_history[-5:]]
            current_memory = current_metrics['resources'].get('memory_rss_mb', 0)
            
            if recent_memory and current_memory > max(recent_memory) * 1.5:
                anomalies.append({
                    'type': 'memory_spike',
                    'current_memory_mb': current_memory,
                    'recent_max_mb': max(recent_memory),
                    'severity': 'warning'
                })
        
        error_rate = current_metrics['workload']['error_count']
        if error_rate > 5:
            anomalies.append({
                'type': 'error_rate_spike',
                'error_count': error_rate,
                'severity': 'critical'
            })
        
        return anomalies
    
    def run_reconciliation(self):
        """Run reconciliation for all tenants"""
        for tenant_id in self.tenant_ids:
            try:
                self.reconciliation_service.full_reconciliation(tenant_id)
            except Exception as e:
                print(f"  ⚠️  Reconciliation failed for {tenant_id}: {e}")
    
    def print_status(self, metrics: Dict, anomalies: List[Dict]):
        """Print current status"""
        print(f"\n{'='*80}")
        print(f"ITERATION {metrics['iteration']} - {metrics['timestamp']}")
        print(f"{'='*80}")
        
        print(f"\n📊 WORKLOAD METRICS")
        print(f"  Jobs Submitted:  {metrics['workload']['jobs_submitted']}")
        print(f"  Jobs Completed:  {metrics['workload']['jobs_completed']}")
        print(f"  Jobs Rejected:   {metrics['workload']['jobs_rejected']}")
        print(f"  Errors:          {metrics['workload']['error_count']}")
        print(f"  Iteration Time:  {metrics['workload']['elapsed_time']:.2f}s")
        
        print(f"\n💻 RESOURCE METRICS")
        print(f"  Memory (RSS):    {metrics['resources'].get('memory_rss_mb', 0):.1f} MB")
        print(f"  CPU %:           {metrics['resources'].get('cpu_percent', 0):.1f}%")
        
        print(f"\n👥 TENANT METRICS")
        for tenant_id, tenant_data in metrics['tenants'].items():
            status = "✅" if tenant_data['active_jobs'] <= MAX_CONCURRENT_JOBS_PER_TENANT else "❌"
            print(f"  {status} {tenant_id[:20]}: {tenant_data['active_jobs']} active, {tenant_data['total_jobs_in_state']} total")
        
        if anomalies:
            print(f"\n⚠️  ANOMALIES DETECTED: {len(anomalies)}")
            for anomaly in anomalies:
                severity = anomaly['severity'].upper()
                print(f"  [{severity}] {anomaly['type']}: {anomaly}")
        else:
            print(f"\n✅ NO ANOMALIES DETECTED")
    
    def save_metrics(self, output_file: str = "continuous_load_metrics.json"):
        """Save metrics to file"""
        data = {
            'test_config': {
                'num_tenants': self.num_tenants,
                'duration_minutes': self.duration_minutes,
                'tenant_ids': self.tenant_ids
            },
            'metrics_history': self.metrics_history,
            'anomalies': self.anomalies,
            'summary': self.generate_summary()
        }
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"\n📄 Metrics saved to: {output_file}")
    
    def generate_summary(self) -> Dict:
        """Generate test summary"""
        if not self.metrics_history:
            return {}
        
        total_jobs_submitted = sum(m['workload']['jobs_submitted'] for m in self.metrics_history)
        total_jobs_completed = sum(m['workload']['jobs_completed'] for m in self.metrics_history)
        total_errors = sum(m['workload']['error_count'] for m in self.metrics_history)
        
        memory_values = [m['resources'].get('memory_rss_mb', 0) for m in self.metrics_history]
        
        return {
            'total_iterations': len(self.metrics_history),
            'total_jobs_submitted': total_jobs_submitted,
            'total_jobs_completed': total_jobs_completed,
            'total_errors': total_errors,
            'success_rate': (total_jobs_completed / total_jobs_submitted * 100) if total_jobs_submitted > 0 else 0,
            'memory_stats': {
                'min_mb': min(memory_values) if memory_values else 0,
                'max_mb': max(memory_values) if memory_values else 0,
                'avg_mb': mean(memory_values) if memory_values else 0,
                'median_mb': median(memory_values) if memory_values else 0
            },
            'anomaly_count': len(self.anomalies)
        }
    
    def cleanup(self):
        """Cleanup test resources"""
        print("\n🧹 Cleaning up test resources...")
        
        for tenant_id in self.tenant_ids:
            try:
                pattern = f"job:*:tenant:{tenant_id}:*"
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
                    print(f"  ✅ Cleaned up {len(keys)} keys for {tenant_id}")
            except Exception as e:
                print(f"  ⚠️  Cleanup failed for {tenant_id}: {e}")
    
    async def run(self):
        """Run continuous load test"""
        print("\n" + "="*80)
        print("CONTINUOUS MULTI-TENANT LOAD TEST")
        print("="*80)
        print(f"Tenants: {self.num_tenants}")
        print(f"Duration: {'Indefinite' if self.duration_minutes is None else f'{self.duration_minutes} minutes'}")
        print(f"Metric Collection: Every 60 seconds")
        print("="*80)
        
        start_time = time.time()
        iteration = 0
        
        try:
            while self.running:
                if self.duration_minutes:
                    elapsed_minutes = (time.time() - start_time) / 60
                    if elapsed_minutes >= self.duration_minutes:
                        print(f"\n⏱️  Duration limit reached ({self.duration_minutes} minutes)")
                        break
                
                iteration += 1
                
                iteration_result = await self.run_iteration(iteration)
                
                metrics = self.collect_metrics(iteration_result)
                self.metrics_history.append(metrics)
                
                anomalies = self.detect_anomalies(metrics)
                if anomalies:
                    self.anomalies.extend(anomalies)
                
                self.print_status(metrics, anomalies)
                
                if iteration % 5 == 0:
                    print(f"\n🔄 Running reconciliation (iteration {iteration})...")
                    self.run_reconciliation()
                
                await asyncio.sleep(60)
        
        except Exception as e:
            print(f"\n❌ Error during load test: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            elapsed_time = time.time() - start_time
            
            print("\n" + "="*80)
            print("LOAD TEST SUMMARY")
            print("="*80)
            
            summary = self.generate_summary()
            
            print(f"Total Runtime:        {elapsed_time / 60:.1f} minutes")
            print(f"Total Iterations:     {summary.get('total_iterations', 0)}")
            print(f"Jobs Submitted:       {summary.get('total_jobs_submitted', 0)}")
            print(f"Jobs Completed:       {summary.get('total_jobs_completed', 0)}")
            print(f"Success Rate:         {summary.get('success_rate', 0):.1f}%")
            print(f"Total Errors:         {summary.get('total_errors', 0)}")
            print(f"Anomalies Detected:   {summary.get('anomaly_count', 0)}")
            
            memory_stats = summary.get('memory_stats', {})
            print(f"\nMemory Usage:")
            print(f"  Min:     {memory_stats.get('min_mb', 0):.1f} MB")
            print(f"  Max:     {memory_stats.get('max_mb', 0):.1f} MB")
            print(f"  Average: {memory_stats.get('avg_mb', 0):.1f} MB")
            print(f"  Median:  {memory_stats.get('median_mb', 0):.1f} MB")
            
            print("="*80)
            
            self.save_metrics()
            
            self.cleanup()
            
            if summary.get('anomaly_count', 0) > 0:
                print("\n⚠️  LOAD TEST COMPLETED WITH ANOMALIES")
                return 1
            else:
                print("\n✅ LOAD TEST COMPLETED SUCCESSFULLY")
                return 0


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Continuous Multi-Tenant Load Test')
    parser.add_argument('--tenants', type=int, default=5, help='Number of tenants (default: 5)')
    parser.add_argument('--duration', type=int, default=None, help='Duration in minutes (default: indefinite)')
    parser.add_argument('--output', type=str, default='continuous_load_metrics.json', help='Output file for metrics')
    
    args = parser.parse_args()
    
    try:
        tester = ContinuousLoadTester(
            num_tenants=args.tenants,
            duration_minutes=args.duration
        )
        
        exit_code = await tester.run()
        sys.exit(exit_code)
    
    except KeyboardInterrupt:
        print("\n\n🛑 Load test interrupted by user")
        sys.exit(0)
    
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
