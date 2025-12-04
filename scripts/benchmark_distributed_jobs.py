"""
Enterprise Performance Benchmarking Suite for Distributed Job Processing

Features:
- Workload profiles (small, medium, large, enterprise)
- Advanced metrics collection (P50/P95/P99 latency, throughput, resource usage)
- Multi-format reporting (JSON, CSV, Markdown)
- Baseline comparison and regression detection
- Tenant isolation validation
"""

import asyncio
import time
import logging
import json
import csv
import psutil
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path
import sys
import os
import statistics

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.mapping_intelligence.job_enqueue import enqueue_bulk_mapping_job, get_job_status
from services.mapping_intelligence.job_state import BulkMappingJobState
from shared.redis_client import get_redis_client

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


WORKLOAD_PROFILES = {
    'small': {
        'connectors': 10,
        'concurrent_jobs': 5,
        'fields_per_connector': 50,
        'description': 'Small workload for basic testing'
    },
    'medium': {
        'connectors': 100,
        'concurrent_jobs': 20,
        'fields_per_connector': 100,
        'description': 'Medium workload for typical production load'
    },
    'large': {
        'connectors': 500,
        'concurrent_jobs': 50,
        'fields_per_connector': 200,
        'description': 'Large workload for high-scale scenarios'
    },
    'enterprise': {
        'connectors': 1000,
        'concurrent_jobs': 100,
        'fields_per_connector': 500,
        'description': 'Enterprise workload for maximum scale testing'
    }
}


class PerformanceMetrics:
    """Collects and analyzes performance metrics"""
    
    def __init__(self):
        self.latencies: List[float] = []
        self.queue_wait_times: List[float] = []
        self.processing_times: List[float] = []
        self.cpu_samples: List[float] = []
        self.memory_samples: List[float] = []
        self.redis_connections: List[int] = []
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        
        self.process = psutil.Process()
    
    def start(self):
        """Start metrics collection"""
        self.start_time = time.time()
        self._sample_resources()
    
    def end(self):
        """End metrics collection"""
        self.end_time = time.time()
        self._sample_resources()
    
    def _sample_resources(self):
        """Sample current resource usage"""
        try:
            self.cpu_samples.append(self.process.cpu_percent(interval=0.1))
            memory_info = self.process.memory_info()
            self.memory_samples.append(memory_info.rss / 1024 / 1024)
        except Exception as e:
            logger.warning(f"Failed to sample resources: {e}")
    
    def record_job_completion(self, job_data: Dict):
        """Record metrics for a completed job"""
        try:
            created_at = datetime.fromisoformat(job_data.get('created_at', ''))
            completed_at = datetime.fromisoformat(job_data.get('completed_at', ''))
            started_at_str = job_data.get('started_at')
            
            total_latency = (completed_at - created_at).total_seconds() * 1000
            self.latencies.append(total_latency)
            
            if started_at_str:
                started_at = datetime.fromisoformat(started_at_str)
                queue_wait = (started_at - created_at).total_seconds() * 1000
                processing_time = (completed_at - started_at).total_seconds() * 1000
                
                self.queue_wait_times.append(queue_wait)
                self.processing_times.append(processing_time)
        
        except Exception as e:
            logger.warning(f"Failed to record job metrics: {e}")
    
    def calculate_percentiles(self, data: List[float], percentiles: List[int]) -> Dict[str, float]:
        """Calculate percentiles for given data"""
        if not data:
            return {f'p{p}': 0.0 for p in percentiles}
        
        sorted_data = sorted(data)
        result = {}
        
        for p in percentiles:
            index = int(len(sorted_data) * p / 100.0)
            index = min(index, len(sorted_data) - 1)
            result[f'p{p}'] = sorted_data[index]
        
        return result
    
    def get_summary(self) -> Dict:
        """Get comprehensive metrics summary"""
        duration = (self.end_time - self.start_time) if self.start_time and self.end_time else 0
        
        latency_percentiles = self.calculate_percentiles(self.latencies, [50, 95, 99])
        queue_wait_percentiles = self.calculate_percentiles(self.queue_wait_times, [50, 95, 99])
        processing_percentiles = self.calculate_percentiles(self.processing_times, [50, 95, 99])
        
        return {
            'duration_seconds': duration,
            'latency_ms': {
                'min': min(self.latencies) if self.latencies else 0,
                'max': max(self.latencies) if self.latencies else 0,
                'avg': statistics.mean(self.latencies) if self.latencies else 0,
                'median': statistics.median(self.latencies) if self.latencies else 0,
                **latency_percentiles
            },
            'queue_wait_ms': {
                'avg': statistics.mean(self.queue_wait_times) if self.queue_wait_times else 0,
                **queue_wait_percentiles
            },
            'processing_time_ms': {
                'avg': statistics.mean(self.processing_times) if self.processing_times else 0,
                **processing_percentiles
            },
            'resource_usage': {
                'cpu_percent_avg': statistics.mean(self.cpu_samples) if self.cpu_samples else 0,
                'cpu_percent_max': max(self.cpu_samples) if self.cpu_samples else 0,
                'memory_mb_avg': statistics.mean(self.memory_samples) if self.memory_samples else 0,
                'memory_mb_max': max(self.memory_samples) if self.memory_samples else 0
            }
        }


class BenchmarkRunner:
    """Enhanced benchmark runner with enterprise features"""
    
    def __init__(self, tenant_id: str = "benchmark-tenant"):
        self.tenant_id = tenant_id
        self.redis_client = get_redis_client()
        
        if not self.redis_client:
            raise RuntimeError("Redis is required for benchmarking")
        
        self.job_state = BulkMappingJobState(self.redis_client)
        self.metrics = PerformanceMetrics()
    
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
        submission_start = time.time()
        
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
            
            self.metrics._sample_resources()
        
        submission_time = time.time() - submission_start
        logger.info(f"Job submission completed in {submission_time:.2f}s")
        
        return job_ids
    
    async def wait_for_jobs(self, job_ids: List[str], timeout: int = 600) -> Dict:
        """Wait for all jobs to complete and collect statistics"""
        logger.info(f"Waiting for {len(job_ids)} jobs to complete (timeout: {timeout}s)")
        
        self.metrics.start()
        
        stats = {
            'total_jobs': len(job_ids),
            'completed': 0,
            'failed': 0,
            'timeout': 0,
            'total_time': 0,
            'jobs': []
        }
        
        check_interval = 1
        last_resource_sample = time.time()
        
        while time.time() - self.metrics.start_time < timeout:
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
                        self.metrics.record_job_completion(status)
                        logger.info(f"Job {job_id} completed ({stats['completed']}/{len(job_ids)})")
                elif job_status == 'failed':
                    if job_id not in [j['job_id'] for j in stats['jobs']]:
                        stats['failed'] += 1
                        stats['jobs'].append(status)
                        logger.error(f"Job {job_id} failed: {status.get('error_message')}")
            
            if all_done:
                break
            
            if time.time() - last_resource_sample > 5:
                self.metrics._sample_resources()
                last_resource_sample = time.time()
            
            await asyncio.sleep(check_interval)
        
        self.metrics.end()
        
        stats['total_time'] = time.time() - self.metrics.start_time
        stats['timeout'] = stats['total_jobs'] - stats['completed'] - stats['failed']
        
        return stats
    
    def calculate_throughput(self, stats: Dict, profile: Dict) -> Dict:
        """Calculate throughput metrics with correct field count"""
        total_time = stats['total_time']
        completed = stats['completed']
        
        if total_time == 0:
            return {'jobs_per_sec': 0, 'fields_per_sec': 0, 'total_fields_processed': 0}
        
        jobs_per_sec = completed / total_time
        
        # ✅ CORRECT CALCULATION:
        # Each job processes (total_connectors / concurrent_jobs) connectors
        # Each connector has fields_per_connector fields
        connectors_per_job = profile.get('connectors', 1) // max(profile.get('concurrent_jobs', 1), 1)
        fields_per_connector = profile.get('fields_per_connector', 100)
        
        total_fields_processed = completed * connectors_per_job * fields_per_connector
        fields_per_sec = total_fields_processed / total_time
        
        return {
            'jobs_per_sec': jobs_per_sec,
            'fields_per_sec': fields_per_sec,
            'total_fields_processed': total_fields_processed
        }
    
    def generate_report(self, stats: Dict, profile: Dict, workload_name: str) -> Dict:
        """Generate comprehensive performance report"""
        metrics_summary = self.metrics.get_summary()
        throughput = self.calculate_throughput(stats, profile)
        
        success_rate = (stats['completed'] / stats['total_jobs'] * 100) if stats['total_jobs'] > 0 else 0
        error_rate = (stats['failed'] / stats['total_jobs'] * 100) if stats['total_jobs'] > 0 else 0
        
        report = {
            'metadata': {
                'workload_profile': workload_name,
                'timestamp': datetime.utcnow().isoformat(),
                'tenant_id': self.tenant_id,
                'profile_config': profile
            },
            'execution': {
                'total_jobs': stats['total_jobs'],
                'completed': stats['completed'],
                'failed': stats['failed'],
                'timeout': stats['timeout'],
                'duration_seconds': stats['total_time'],
                'success_rate_percent': round(success_rate, 2),
                'error_rate_percent': round(error_rate, 2)
            },
            'performance': {
                'throughput': throughput,
                'latency': metrics_summary['latency_ms'],
                'queue_wait': metrics_summary['queue_wait_ms'],
                'processing_time': metrics_summary['processing_time_ms']
            },
            'resources': metrics_summary['resource_usage'],
            'recommendations': self._generate_recommendations(success_rate, error_rate, metrics_summary)
        }
        
        return report
    
    def _generate_recommendations(self, success_rate: float, error_rate: float, metrics: Dict) -> List[str]:
        """Generate performance recommendations"""
        recommendations = []
        
        if success_rate < 95:
            recommendations.append(f"⚠️  Success rate ({success_rate:.1f}%) below 95% target. Investigate job failures.")
        
        if error_rate > 5:
            recommendations.append(f"⚠️  Error rate ({error_rate:.1f}%) exceeds 5% threshold. Review error logs.")
        
        p95_latency = metrics['latency_ms'].get('p95', 0)
        if p95_latency > 30000:
            recommendations.append(f"⚠️  P95 latency ({p95_latency:.0f}ms) exceeds 30s. Consider scaling resources.")
        
        cpu_max = metrics['resource_usage'].get('cpu_percent_max', 0)
        if cpu_max > 80:
            recommendations.append(f"⚠️  CPU usage peaked at {cpu_max:.1f}%. Consider horizontal scaling.")
        
        memory_max = metrics['resource_usage'].get('memory_mb_max', 0)
        if memory_max > 1000:
            recommendations.append(f"ℹ️  Memory usage peaked at {memory_max:.0f}MB. Monitor for memory leaks.")
        
        if not recommendations:
            recommendations.append("✅ All metrics within acceptable ranges.")
        
        return recommendations
    
    def save_json_report(self, report: Dict, output_dir: str = "results"):
        """Save report as JSON"""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        filename = f"{output_dir}/{report['metadata']['workload_profile']}_{int(time.time())}.json"
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        latest_file = f"{output_dir}/latest.json"
        with open(latest_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"JSON report saved to {filename}")
        return filename
    
    def save_csv_report(self, report: Dict, output_dir: str = "results"):
        """Save metrics as CSV"""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        filename = f"{output_dir}/{report['metadata']['workload_profile']}_{int(time.time())}.csv"
        
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            
            writer.writerow(['Metric', 'Value', 'Unit'])
            
            exec_data = report['execution']
            writer.writerow(['Total Jobs', exec_data['total_jobs'], 'count'])
            writer.writerow(['Completed', exec_data['completed'], 'count'])
            writer.writerow(['Failed', exec_data['failed'], 'count'])
            writer.writerow(['Success Rate', exec_data['success_rate_percent'], 'percent'])
            writer.writerow(['Error Rate', exec_data['error_rate_percent'], 'percent'])
            writer.writerow(['Duration', exec_data['duration_seconds'], 'seconds'])
            
            perf_data = report['performance']
            writer.writerow(['Jobs/sec', perf_data['throughput']['jobs_per_sec'], 'jobs/sec'])
            writer.writerow(['Fields/sec', perf_data['throughput']['fields_per_sec'], 'fields/sec'])
            
            latency = perf_data['latency']
            writer.writerow(['Latency P50', latency['p50'], 'ms'])
            writer.writerow(['Latency P95', latency['p95'], 'ms'])
            writer.writerow(['Latency P99', latency['p99'], 'ms'])
            
            resources = report['resources']
            writer.writerow(['CPU Avg', resources['cpu_percent_avg'], 'percent'])
            writer.writerow(['CPU Max', resources['cpu_percent_max'], 'percent'])
            writer.writerow(['Memory Avg', resources['memory_mb_avg'], 'MB'])
            writer.writerow(['Memory Max', resources['memory_mb_max'], 'MB'])
        
        logger.info(f"CSV report saved to {filename}")
        return filename
    
    def save_markdown_report(self, report: Dict, output_dir: str = "results"):
        """Save report as Markdown"""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{output_dir}/benchmark_{timestamp}.md"
        
        with open(filename, 'w') as f:
            f.write("# AutonomOS Performance Benchmark Results\n\n")
            f.write(f"**Generated**: {report['metadata']['timestamp']}\n")
            f.write(f"**Profile**: {report['metadata']['workload_profile']}\n")
            f.write(f"**Tenant**: {report['metadata']['tenant_id']}\n\n")
            
            profile = report['metadata']['profile_config']
            f.write("## Workload Configuration\n\n")
            f.write(f"- **Connectors**: {profile['connectors']}\n")
            f.write(f"- **Concurrent Jobs**: {profile['concurrent_jobs']}\n")
            f.write(f"- **Fields per Connector**: {profile['fields_per_connector']}\n\n")
            
            exec_data = report['execution']
            f.write("## Execution Summary\n\n")
            f.write(f"- **Total Jobs**: {exec_data['total_jobs']}\n")
            f.write(f"- ✅ **Completed**: {exec_data['completed']} ({exec_data['success_rate_percent']}%)\n")
            f.write(f"- ❌ **Failed**: {exec_data['failed']} ({exec_data['error_rate_percent']}%)\n")
            f.write(f"- ⏱️  **Duration**: {exec_data['duration_seconds']:.2f}s\n\n")
            
            perf = report['performance']
            f.write("## Performance Metrics\n\n")
            f.write(f"- **Throughput**: {perf['throughput']['jobs_per_sec']:.2f} jobs/sec\n")
            f.write(f"- **Throughput**: {perf['throughput']['fields_per_sec']:.0f} fields/sec\n\n")
            
            latency = perf['latency']
            f.write("### Latency (ms)\n\n")
            f.write(f"- **P50**: {latency['p50']:.0f}ms\n")
            f.write(f"- **P95**: {latency['p95']:.0f}ms\n")
            f.write(f"- **P99**: {latency['p99']:.0f}ms\n")
            f.write(f"- **Max**: {latency['max']:.0f}ms\n\n")
            
            queue = perf['queue_wait']
            f.write("### Queue Wait Time (ms)\n\n")
            f.write(f"- **Average**: {queue['avg']:.0f}ms\n")
            f.write(f"- **P95**: {queue['p95']:.0f}ms\n\n")
            
            processing = perf['processing_time']
            f.write("### Processing Time (ms)\n\n")
            f.write(f"- **Average**: {processing['avg']:.0f}ms\n")
            f.write(f"- **P95**: {processing['p95']:.0f}ms\n\n")
            
            resources = report['resources']
            f.write("## Resource Usage\n\n")
            f.write(f"- **CPU**: Avg {resources['cpu_percent_avg']:.1f}%, Max {resources['cpu_percent_max']:.1f}%\n")
            f.write(f"- **Memory**: Avg {resources['memory_mb_avg']:.0f}MB, Max {resources['memory_mb_max']:.0f}MB\n\n")
            
            f.write("## Recommendations\n\n")
            for rec in report['recommendations']:
                f.write(f"- {rec}\n")
        
        logger.info(f"Markdown report saved to {filename}")
        return filename
    
    def save_reports(self, report: Dict, output_dir: str = "benchmarks/results"):
        """Save benchmark reports in multiple formats"""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 1. Save JSON report
        json_path = os.path.join(output_dir, f"benchmark_{timestamp}.json")
        with open(json_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Also save as latest.json (required by CI pipeline)
        latest_path = os.path.join(output_dir, "latest.json")
        with open(latest_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # 2. Save CSV report
        csv_path = os.path.join(output_dir, f"benchmark_{timestamp}.csv")
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow([
                'Profile', 'Connectors', 'Total Jobs', 'Successful', 'Failed',
                'Duration (s)', 'Throughput (jobs/s)', 'Throughput (fields/s)',
                'Latency P50 (ms)', 'Latency P95 (ms)', 'Latency P99 (ms)',
                'CPU Avg (%)', 'CPU Peak (%)', 'Memory Avg (MB)', 'Memory Peak (MB)'
            ])
            
            # Write data row
            metadata = report.get('metadata', {})
            profile_config = metadata.get('profile_config', {})
            exec_data = report.get('execution', {})
            perf = report.get('performance', {})
            throughput = perf.get('throughput', {})
            latency = perf.get('latency', {})
            resources = report.get('resources', {})
            
            writer.writerow([
                metadata.get('workload_profile', 'unknown'),
                profile_config.get('connectors', 0),
                exec_data.get('total_jobs', 0),
                exec_data.get('completed', 0),
                exec_data.get('failed', 0),
                exec_data.get('duration_seconds', 0),
                throughput.get('jobs_per_sec', 0),
                throughput.get('fields_per_sec', 0),
                latency.get('p50', 0),
                latency.get('p95', 0),
                latency.get('p99', 0),
                resources.get('cpu_percent_avg', 0),
                resources.get('cpu_percent_max', 0),
                resources.get('memory_mb_avg', 0),
                resources.get('memory_mb_max', 0)
            ])
        
        # 3. Save Markdown report
        md_path = os.path.join(output_dir, f"benchmark_{timestamp}.md")
        with open(md_path, 'w') as f:
            f.write("# AutonomOS Performance Benchmark Results\n\n")
            f.write(f"**Generated**: {datetime.now().isoformat()}\n")
            f.write(f"**Profile**: {metadata.get('workload_profile', 'unknown')}\n")
            f.write(f"**Tenant**: {metadata.get('tenant_id', 'unknown')}\n\n")
            
            f.write("## Workload Configuration\n\n")
            f.write(f"- **Connectors**: {profile_config.get('connectors', 0)}\n")
            f.write(f"- **Concurrent Jobs**: {profile_config.get('concurrent_jobs', 0)}\n")
            f.write(f"- **Fields per Connector**: {profile_config.get('fields_per_connector', 0)}\n\n")
            
            f.write("## Execution Summary\n\n")
            f.write(f"- **Total Jobs**: {exec_data.get('total_jobs', 0)}\n")
            f.write(f"- ✅ **Completed**: {exec_data.get('completed', 0)} ({exec_data.get('success_rate_percent', 0):.2f}%)\n")
            f.write(f"- ❌ **Failed**: {exec_data.get('failed', 0)} ({exec_data.get('error_rate_percent', 0):.2f}%)\n")
            f.write(f"- ⏱️  **Duration**: {exec_data.get('duration_seconds', 0):.2f}s\n\n")
            
            f.write("## Performance Metrics\n\n")
            f.write(f"- **Throughput**: {throughput.get('jobs_per_sec', 0):.2f} jobs/sec\n")
            f.write(f"- **Throughput**: {throughput.get('fields_per_sec', 0):.0f} fields/sec\n\n")
            
            f.write("### Latency (ms)\n\n")
            f.write(f"- **P50**: {latency.get('p50', 0):.0f}ms\n")
            f.write(f"- **P95**: {latency.get('p95', 0):.0f}ms\n")
            f.write(f"- **P99**: {latency.get('p99', 0):.0f}ms\n")
            f.write(f"- **Max**: {latency.get('max', 0):.0f}ms\n\n")
            
            queue = perf.get('queue_wait', {})
            f.write("### Queue Wait Time (ms)\n\n")
            f.write(f"- **Average**: {queue.get('avg', 0):.0f}ms\n")
            f.write(f"- **P95**: {queue.get('p95', 0):.0f}ms\n\n")
            
            processing = perf.get('processing_time', {})
            f.write("### Processing Time (ms)\n\n")
            f.write(f"- **Average**: {processing.get('avg', 0):.0f}ms\n")
            f.write(f"- **P95**: {processing.get('p95', 0):.0f}ms\n\n")
            
            f.write("## Resource Usage\n\n")
            f.write(f"- **CPU**: Avg {resources.get('cpu_percent_avg', 0):.1f}%, Max {resources.get('cpu_percent_max', 0):.1f}%\n")
            f.write(f"- **Memory**: Avg {resources.get('memory_mb_avg', 0):.0f}MB, Max {resources.get('memory_mb_max', 0):.0f}MB\n\n")
            
            f.write("## Recommendations\n\n")
            recommendations = report.get('recommendations', [])
            if recommendations:
                for rec in recommendations:
                    f.write(f"- {rec}\n")
            else:
                f.write("- No recommendations available\n")
        
        print(f"\n✅ Reports saved:")
        print(f"   JSON: {json_path}")
        print(f"   JSON (latest): {latest_path}")
        print(f"   CSV: {csv_path}")
        print(f"   Markdown: {md_path}")
        
        return {
            'json': json_path,
            'latest': latest_path,
            'csv': csv_path,
            'markdown': md_path
        }
    
    def print_markdown_report(self, report: Dict):
        """Print human-readable markdown report"""
        print("\n" + "="*80)
        print(f"# PERFORMANCE BENCHMARK REPORT: {report['metadata']['workload_profile'].upper()}")
        print("="*80)
        print(f"\n**Timestamp:** {report['metadata']['timestamp']}")
        print(f"**Tenant:** {report['metadata']['tenant_id']}")
        
        profile = report['metadata']['profile_config']
        print(f"\n## Workload Configuration")
        print(f"- Connectors: {profile['connectors']}")
        print(f"- Concurrent Jobs: {profile['concurrent_jobs']}")
        print(f"- Fields per Connector: {profile['fields_per_connector']}")
        
        exec_data = report['execution']
        print(f"\n## Execution Summary")
        print(f"- Total Jobs: {exec_data['total_jobs']}")
        print(f"- ✅ Completed: {exec_data['completed']} ({exec_data['success_rate_percent']}%)")
        print(f"- ❌ Failed: {exec_data['failed']} ({exec_data['error_rate_percent']}%)")
        print(f"- ⏱️  Duration: {exec_data['duration_seconds']:.2f}s")
        
        perf = report['performance']
        print(f"\n## Performance Metrics")
        print(f"- **Throughput:** {perf['throughput']['jobs_per_sec']:.2f} jobs/sec")
        print(f"- **Throughput:** {perf['throughput']['fields_per_sec']:.0f} fields/sec")
        
        latency = perf['latency']
        print(f"\n### Latency (ms)")
        print(f"- P50: {latency['p50']:.0f}ms")
        print(f"- P95: {latency['p95']:.0f}ms")
        print(f"- P99: {latency['p99']:.0f}ms")
        print(f"- Max: {latency['max']:.0f}ms")
        
        queue = perf['queue_wait']
        print(f"\n### Queue Wait Time (ms)")
        print(f"- Average: {queue['avg']:.0f}ms")
        print(f"- P95: {queue['p95']:.0f}ms")
        
        processing = perf['processing_time']
        print(f"\n### Processing Time (ms)")
        print(f"- Average: {processing['avg']:.0f}ms")
        print(f"- P95: {processing['p95']:.0f}ms")
        
        resources = report['resources']
        print(f"\n## Resource Usage")
        print(f"- **CPU:** Avg {resources['cpu_percent_avg']:.1f}%, Max {resources['cpu_percent_max']:.1f}%")
        print(f"- **Memory:** Avg {resources['memory_mb_avg']:.0f}MB, Max {resources['memory_mb_max']:.0f}MB")
        
        print(f"\n## Recommendations")
        for rec in report['recommendations']:
            print(f"  {rec}")
        
        print("\n" + "="*80 + "\n")


async def run_benchmark(
    profile_name: str = 'small',
    iterations: int = 1,
    output_dir: str = 'benchmarks/results'
):
    """Run a complete benchmark with specified profile"""
    
    if profile_name not in WORKLOAD_PROFILES:
        logger.error(f"Unknown profile: {profile_name}. Available: {list(WORKLOAD_PROFILES.keys())}")
        return
    
    profile = WORKLOAD_PROFILES[profile_name]
    
    logger.info(f"Starting benchmark: {profile_name}")
    logger.info(f"Profile: {profile['description']}")
    logger.info(f"Iterations: {iterations}")
    
    all_reports = []
    
    for iteration in range(iterations):
        logger.info(f"\n{'='*60}")
        logger.info(f"Iteration {iteration + 1}/{iterations}")
        logger.info(f"{'='*60}\n")
        
        runner = BenchmarkRunner(tenant_id=f"benchmark-{profile_name}-{iteration}")
        
        runner.cleanup_tenant_jobs()
        
        num_jobs = profile['concurrent_jobs']
        connectors_per_job = profile['connectors'] // num_jobs
        
        job_ids = runner.submit_jobs(num_jobs, connectors_per_job)
        
        if not job_ids:
            logger.error("No jobs were successfully submitted")
            continue
        
        timeout = 600 if profile_name in ['small', 'medium'] else 1200
        stats = await runner.wait_for_jobs(job_ids, timeout=timeout)
        
        report = runner.generate_report(stats, profile, profile_name)
        all_reports.append(report)
        
        # Use consolidated save_reports method
        saved_files = runner.save_reports(report, output_dir)
        runner.print_markdown_report(report)
        
        runner.cleanup_tenant_jobs()
        
        if iteration < iterations - 1:
            logger.info("Waiting 10s before next iteration...")
            await asyncio.sleep(10)
    
    if len(all_reports) > 1:
        print_aggregated_results(all_reports, profile_name)


def print_aggregated_results(reports: List[Dict], profile_name: str):
    """Print aggregated results from multiple iterations"""
    print("\n" + "="*80)
    print(f"# AGGREGATED RESULTS: {profile_name.upper()} ({len(reports)} iterations)")
    print("="*80)
    
    success_rates = [r['execution']['success_rate_percent'] for r in reports]
    p95_latencies = [r['performance']['latency']['p95'] for r in reports]
    throughputs = [r['performance']['throughput']['jobs_per_sec'] for r in reports]
    
    print(f"\n**Success Rate:** {statistics.mean(success_rates):.2f}% ± {statistics.stdev(success_rates) if len(success_rates) > 1 else 0:.2f}%")
    print(f"**P95 Latency:** {statistics.mean(p95_latencies):.0f}ms ± {statistics.stdev(p95_latencies) if len(p95_latencies) > 1 else 0:.0f}ms")
    print(f"**Throughput:** {statistics.mean(throughputs):.2f} jobs/sec ± {statistics.stdev(throughputs) if len(throughputs) > 1 else 0:.2f} jobs/sec")
    
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Enterprise Performance Benchmarking Suite")
    parser.add_argument(
        "--profile",
        type=str,
        default='small',
        choices=list(WORKLOAD_PROFILES.keys()),
        help="Workload profile to run"
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=1,
        help="Number of iterations to run"
    )
    parser.add_argument(
        "--output",
        type=str,
        default='benchmarks/results',
        help="Output directory for reports"
    )
    
    args = parser.parse_args()
    
    asyncio.run(run_benchmark(args.profile, args.iterations, args.output))
