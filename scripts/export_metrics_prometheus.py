"""
Export Job Queue Metrics to Prometheus Format

Exports metrics from Redis job queue for monitoring dashboards (Grafana, Prometheus).

Metrics exported:
- job_queue_depth: Current number of jobs in queue per tenant
- job_processing_time_seconds: Processing time histogram
- job_error_rate: Error rate per tenant
- job_semaphore_utilization: Semaphore slot utilization per tenant
- job_throughput_total: Total jobs processed
"""

import sys
import os
import argparse
from datetime import datetime
from typing import Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.redis_client import get_redis_client
from services.mapping_intelligence.job_state import BulkMappingJobState, MAX_CONCURRENT_JOBS_PER_TENANT


class PrometheusExporter:
    """Export job queue metrics in Prometheus format"""
    
    def __init__(self):
        self.redis_client = get_redis_client()
        if not self.redis_client:
            raise RuntimeError("Redis client is required")
        
        self.job_state = BulkMappingJobState(self.redis_client)
    
    def get_tenant_list(self) -> List[str]:
        """Get list of all tenants with jobs"""
        pattern = "job:semaphore:tenant:*"
        keys = self.redis_client.keys(pattern)
        
        tenants = []
        for key in keys:
            key_str = key.decode('utf-8') if isinstance(key, bytes) else key
            tenant_id = key_str.split(':')[-1]
            tenants.append(tenant_id)
        
        return tenants
    
    def get_queue_depth(self, tenant_id: str) -> Dict:
        """Get queue depth metrics for tenant"""
        jobs = self.job_state.get_all_jobs_for_tenant(tenant_id)
        
        pending = len([j for j in jobs if j.get('status') == 'pending'])
        running = len([j for j in jobs if j.get('status') == 'running'])
        
        return {
            'pending': pending,
            'running': running,
            'total': len(jobs)
        }
    
    def get_semaphore_utilization(self, tenant_id: str) -> float:
        """Get semaphore utilization percentage"""
        active = self.job_state.get_active_job_count(tenant_id)
        utilization = (active / MAX_CONCURRENT_JOBS_PER_TENANT) * 100
        return utilization
    
    def get_job_metrics(self, tenant_id: str) -> Dict:
        """Get job completion and error metrics"""
        jobs = self.job_state.get_all_jobs_for_tenant(tenant_id)
        
        completed = [j for j in jobs if j.get('status') == 'completed']
        failed = [j for j in jobs if j.get('status') == 'failed']
        
        processing_times = []
        for job in completed:
            if 'started_at' in job and 'completed_at' in job:
                try:
                    started = datetime.fromisoformat(job['started_at'])
                    ended = datetime.fromisoformat(job['completed_at'])
                    duration = (ended - started).total_seconds()
                    processing_times.append(duration)
                except Exception:
                    pass
        
        total = len(jobs)
        error_rate = (len(failed) / total * 100) if total > 0 else 0
        
        return {
            'completed': len(completed),
            'failed': len(failed),
            'error_rate': error_rate,
            'processing_times': processing_times
        }
    
    def export_prometheus_metrics(self) -> str:
        """Export all metrics in Prometheus format"""
        lines = []
        
        lines.append("# HELP job_queue_depth Number of jobs in queue by status")
        lines.append("# TYPE job_queue_depth gauge")
        
        lines.append("# HELP job_semaphore_utilization Percentage of semaphore slots in use")
        lines.append("# TYPE job_semaphore_utilization gauge")
        
        lines.append("# HELP job_error_rate Percentage of failed jobs")
        lines.append("# TYPE job_error_rate gauge")
        
        lines.append("# HELP job_processing_time_seconds Job processing time in seconds")
        lines.append("# TYPE job_processing_time_seconds histogram")
        
        lines.append("# HELP job_throughput_total Total jobs processed")
        lines.append("# TYPE job_throughput_total counter")
        
        tenants = self.get_tenant_list()
        
        for tenant_id in tenants:
            queue_depth = self.get_queue_depth(tenant_id)
            
            lines.append(
                f'job_queue_depth{{tenant="{tenant_id}",status="pending"}} {queue_depth["pending"]}'
            )
            lines.append(
                f'job_queue_depth{{tenant="{tenant_id}",status="running"}} {queue_depth["running"]}'
            )
            lines.append(
                f'job_queue_depth{{tenant="{tenant_id}",status="total"}} {queue_depth["total"]}'
            )
            
            utilization = self.get_semaphore_utilization(tenant_id)
            lines.append(
                f'job_semaphore_utilization{{tenant="{tenant_id}"}} {utilization:.2f}'
            )
            
            metrics = self.get_job_metrics(tenant_id)
            
            lines.append(
                f'job_error_rate{{tenant="{tenant_id}"}} {metrics["error_rate"]:.2f}'
            )
            
            lines.append(
                f'job_throughput_total{{tenant="{tenant_id}",status="completed"}} {metrics["completed"]}'
            )
            lines.append(
                f'job_throughput_total{{tenant="{tenant_id}",status="failed"}} {metrics["failed"]}'
            )
            
            if metrics['processing_times']:
                sorted_times = sorted(metrics['processing_times'])
                count = len(sorted_times)
                
                buckets = [1, 5, 10, 30, 60, 120, 300]
                cumulative = 0
                
                for bucket in buckets:
                    cumulative += sum(1 for t in sorted_times if t <= bucket)
                    lines.append(
                        f'job_processing_time_seconds_bucket{{tenant="{tenant_id}",le="{bucket}"}} {cumulative}'
                    )
                
                lines.append(
                    f'job_processing_time_seconds_bucket{{tenant="{tenant_id}",le="+Inf"}} {count}'
                )
                lines.append(
                    f'job_processing_time_seconds_sum{{tenant="{tenant_id}"}} {sum(sorted_times):.2f}'
                )
                lines.append(
                    f'job_processing_time_seconds_count{{tenant="{tenant_id}"}} {count}'
                )
        
        timestamp = int(datetime.utcnow().timestamp() * 1000)
        lines.append(f"\n# Export timestamp: {timestamp}")
        
        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Export job queue metrics to Prometheus format"
    )
    parser.add_argument(
        "--output",
        help="Output file path (default: stdout)"
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Continuously export metrics (every 10 seconds)"
    )
    
    args = parser.parse_args()
    
    exporter = PrometheusExporter()
    
    if args.watch:
        import time
        print("Watching metrics (Ctrl+C to stop)...")
        
        try:
            while True:
                metrics = exporter.export_prometheus_metrics()
                
                if args.output:
                    with open(args.output, 'w') as f:
                        f.write(metrics)
                    print(f"[{datetime.utcnow().isoformat()}] Metrics exported to {args.output}")
                else:
                    print("\n" + "="*60)
                    print(metrics)
                    print("="*60)
                
                time.sleep(10)
        
        except KeyboardInterrupt:
            print("\nStopped.")
    else:
        metrics = exporter.export_prometheus_metrics()
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(metrics)
            print(f"Metrics exported to {args.output}")
        else:
            print(metrics)


if __name__ == "__main__":
    main()
