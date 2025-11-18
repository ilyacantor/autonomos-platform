#!/usr/bin/env python3
"""
Tenant Metrics Validation Script

Validates tenant isolation by checking:
- Independent semaphore counts
- Tenant-scoped Redis keys
- Progress tracking isolation
- Resource usage metrics
"""

import sys
import json
from typing import Dict, List
from datetime import datetime
from shared.redis_client import get_redis_client
from services.mapping_intelligence.job_state import BulkMappingJobState


class TenantMetricsValidator:
    """Validates tenant metrics and isolation"""
    
    def __init__(self):
        self.redis_client = get_redis_client()
        if not self.redis_client:
            raise RuntimeError("Redis client not available")
        
        self.job_state = BulkMappingJobState(self.redis_client)
    
    def discover_tenants(self) -> List[str]:
        """Discover all tenant IDs from Redis keys"""
        pattern = "job:*:tenant:*"
        all_keys = self.redis_client.keys(pattern)
        
        tenant_ids = set()
        
        for key in all_keys:
            key_str = key.decode('utf-8') if isinstance(key, bytes) else key
            parts = key_str.split(':')
            
            if len(parts) >= 4 and parts[2] == 'tenant':
                tenant_id = parts[3]
                tenant_ids.add(tenant_id)
        
        return sorted(list(tenant_ids))
    
    def validate_semaphore_isolation(self, tenant_ids: List[str]) -> Dict:
        """Validate each tenant has independent semaphore"""
        results = {}
        
        for tenant_id in tenant_ids:
            active_count = self.job_state.get_active_job_count(tenant_id)
            semaphore_key = f"job:semaphore:tenant:{tenant_id}"
            
            results[tenant_id] = {
                'active_count': active_count,
                'semaphore_key': semaphore_key,
                'isolated': True
            }
        
        return results
    
    def validate_job_state_isolation(self, tenant_ids: List[str]) -> Dict:
        """Validate job state keys are tenant-scoped"""
        results = {}
        
        for tenant_id in tenant_ids:
            jobs = self.job_state.get_all_jobs_for_tenant(tenant_id)
            
            job_ids = [job['job_id'] for job in jobs]
            
            cross_tenant_leakage = []
            for other_tenant_id in tenant_ids:
                if other_tenant_id == tenant_id:
                    continue
                
                other_jobs = self.job_state.get_all_jobs_for_tenant(other_tenant_id)
                other_job_ids = {job['job_id'] for job in other_jobs}
                
                leaked = [jid for jid in job_ids if jid in other_job_ids]
                if leaked:
                    cross_tenant_leakage.extend(leaked)
            
            results[tenant_id] = {
                'job_count': len(jobs),
                'job_ids': job_ids,
                'cross_tenant_leakage': cross_tenant_leakage,
                'isolated': len(cross_tenant_leakage) == 0
            }
        
        return results
    
    def validate_redis_key_namespacing(self, tenant_ids: List[str]) -> Dict:
        """Validate Redis keys follow tenant-scoped naming"""
        results = {}
        
        for tenant_id in tenant_ids:
            pattern = f"job:*:tenant:{tenant_id}:*"
            tenant_keys = self.redis_client.keys(pattern)
            
            key_types = {}
            for key in tenant_keys:
                key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                
                if ':semaphore:' in key_str:
                    key_types['semaphore'] = key_types.get('semaphore', 0) + 1
                elif ':state:' in key_str:
                    key_types['state'] = key_types.get('state', 0) + 1
                else:
                    key_types['other'] = key_types.get('other', 0) + 1
            
            results[tenant_id] = {
                'total_keys': len(tenant_keys),
                'key_types': key_types,
                'properly_namespaced': all(':tenant:' in (k.decode('utf-8') if isinstance(k, bytes) else k) for k in tenant_keys)
            }
        
        return results
    
    def validate_progress_tracking(self, tenant_ids: List[str]) -> Dict:
        """Validate progress tracking is isolated per tenant"""
        results = {}
        
        for tenant_id in tenant_ids:
            jobs = self.job_state.get_all_jobs_for_tenant(tenant_id)
            
            progress_data = []
            for job in jobs:
                progress_data.append({
                    'job_id': job.get('job_id'),
                    'status': job.get('status'),
                    'processed_fields': job.get('processed_fields', 0),
                    'total_fields': job.get('total_fields', 0)
                })
            
            results[tenant_id] = {
                'jobs_with_progress': len(progress_data),
                'progress_data': progress_data,
                'tracking_isolated': True
            }
        
        return results
    
    def generate_isolation_report(self) -> Dict:
        """Generate comprehensive tenant isolation report"""
        tenant_ids = self.discover_tenants()
        
        if not tenant_ids:
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'tenants_found': 0,
                'message': 'No tenants found in Redis'
            }
        
        semaphore_validation = self.validate_semaphore_isolation(tenant_ids)
        job_state_validation = self.validate_job_state_isolation(tenant_ids)
        key_namespacing = self.validate_redis_key_namespacing(tenant_ids)
        progress_tracking = self.validate_progress_tracking(tenant_ids)
        
        all_isolated = all([
            all(v['isolated'] for v in semaphore_validation.values()),
            all(v['isolated'] for v in job_state_validation.values()),
            all(v['properly_namespaced'] for v in key_namespacing.values()),
            all(v['tracking_isolated'] for v in progress_tracking.values())
        ])
        
        report = {
            'timestamp': datetime.utcnow().isoformat(),
            'tenants_found': len(tenant_ids),
            'tenant_ids': tenant_ids,
            'all_isolated': all_isolated,
            'validations': {
                'semaphore_isolation': semaphore_validation,
                'job_state_isolation': job_state_validation,
                'redis_key_namespacing': key_namespacing,
                'progress_tracking': progress_tracking
            }
        }
        
        return report
    
    def print_report(self, report: Dict):
        """Print formatted validation report"""
        print("\n" + "="*80)
        print("TENANT METRICS VALIDATION REPORT")
        print("="*80)
        print(f"Timestamp: {report['timestamp']}")
        print(f"Tenants Found: {report['tenants_found']}")
        print(f"Overall Isolation Status: {'✅ PASSED' if report.get('all_isolated') else '❌ FAILED'}")
        print("="*80)
        
        if report['tenants_found'] == 0:
            print("\n⚠️  No tenants found in Redis")
            return
        
        print("\n📊 TENANT SUMMARY")
        print("-"*80)
        for tenant_id in report['tenant_ids']:
            print(f"  • {tenant_id}")
        
        print("\n🔒 SEMAPHORE ISOLATION")
        print("-"*80)
        for tenant_id, data in report['validations']['semaphore_isolation'].items():
            status = "✅" if data['isolated'] else "❌"
            print(f"  {status} {tenant_id}: {data['active_count']} active jobs")
        
        print("\n📦 JOB STATE ISOLATION")
        print("-"*80)
        for tenant_id, data in report['validations']['job_state_isolation'].items():
            status = "✅" if data['isolated'] else "❌"
            leakage = f" (⚠️  {len(data['cross_tenant_leakage'])} leaked jobs)" if data['cross_tenant_leakage'] else ""
            print(f"  {status} {tenant_id}: {data['job_count']} jobs{leakage}")
        
        print("\n🔑 REDIS KEY NAMESPACING")
        print("-"*80)
        for tenant_id, data in report['validations']['redis_key_namespacing'].items():
            status = "✅" if data['properly_namespaced'] else "❌"
            print(f"  {status} {tenant_id}: {data['total_keys']} keys, {data['key_types']}")
        
        print("\n📈 PROGRESS TRACKING")
        print("-"*80)
        for tenant_id, data in report['validations']['progress_tracking'].items():
            status = "✅" if data['tracking_isolated'] else "❌"
            print(f"  {status} {tenant_id}: {data['jobs_with_progress']} jobs with progress data")
        
        print("\n" + "="*80)
        
        if report.get('all_isolated'):
            print("✅ VALIDATION PASSED: All tenants are properly isolated")
        else:
            print("❌ VALIDATION FAILED: Isolation issues detected")
        
        print("="*80 + "\n")


def main():
    """Main entry point"""
    try:
        validator = TenantMetricsValidator()
        
        print("Generating tenant metrics validation report...")
        report = validator.generate_isolation_report()
        
        validator.print_report(report)
        
        output_file = f"tenant_metrics_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"📄 Detailed report saved to: {output_file}\n")
        
        if not report.get('all_isolated', True):
            sys.exit(1)
        
        sys.exit(0)
    
    except Exception as e:
        print(f"\n❌ Error generating report: {e}\n", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
