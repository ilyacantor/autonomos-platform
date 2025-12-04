"""
Resource Monitoring for Distributed Jobs

Features:
- CPU/memory sampling
- Performance metrics collection
- Resource usage tracking per tenant
"""

import psutil
import logging
from datetime import datetime
from typing import Dict, Optional
import json

logger = logging.getLogger(__name__)


class ResourceMonitor:
    """
    Monitors system resources for job processing
    """
    
    def __init__(self, redis_client=None):
        from shared.redis_client import get_redis_client
        self.redis_client = redis_client or get_redis_client()
        self.process = psutil.Process()
    
    def get_current_metrics(self) -> Dict:
        """
        Get current system resource metrics
        
        Returns:
            Dictionary with CPU, memory, and system metrics
        """
        try:
            cpu_percent = self.process.cpu_percent(interval=0.1)
            memory_info = self.process.memory_info()
            
            metrics = {
                'timestamp': datetime.utcnow().isoformat(),
                'cpu_percent': cpu_percent,
                'memory_rss_mb': memory_info.rss / (1024 * 1024),
                'memory_vms_mb': memory_info.vms / (1024 * 1024),
                'memory_percent': self.process.memory_percent(),
                'num_threads': self.process.num_threads(),
                'system_cpu_percent': psutil.cpu_percent(interval=0.1),
                'system_memory_percent': psutil.virtual_memory().percent,
                'system_memory_available_mb': psutil.virtual_memory().available / (1024 * 1024)
            }
            
            return metrics
        
        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'error': str(e)
            }
    
    def record_job_metrics(
        self,
        tenant_id: str,
        job_id: str,
        metrics: Optional[Dict] = None
    ):
        """
        Record metrics for a specific job
        
        Args:
            tenant_id: Tenant identifier
            job_id: Job identifier
            metrics: Optional metrics dict, or current metrics if None
        """
        if not self.redis_client:
            logger.warning("Redis not available, skipping metrics recording")
            return
        
        if metrics is None:
            metrics = self.get_current_metrics()
        
        key = f"job:metrics:tenant:{tenant_id}:job:{job_id}"
        
        try:
            self.redis_client.setex(
                key,
                3600,
                json.dumps(metrics)
            )
            logger.debug(f"Recorded metrics for job {job_id}")
        
        except Exception as e:
            logger.error(f"Failed to record job metrics: {e}")
    
    def get_job_metrics(self, tenant_id: str, job_id: str) -> Optional[Dict]:
        """
        Get recorded metrics for a job
        
        Args:
            tenant_id: Tenant identifier
            job_id: Job identifier
        
        Returns:
            Metrics dictionary or None if not found
        """
        if not self.redis_client:
            return None
        
        key = f"job:metrics:tenant:{tenant_id}:job:{job_id}"
        
        try:
            data = self.redis_client.get(key)
            return json.loads(data) if data else None
        
        except Exception as e:
            logger.error(f"Failed to get job metrics: {e}")
            return None
    
    def get_tenant_metrics_summary(self, tenant_id: str) -> Dict:
        """
        Get aggregated metrics for all jobs of a tenant
        
        Args:
            tenant_id: Tenant identifier
        
        Returns:
            Aggregated metrics dictionary
        """
        if not self.redis_client:
            return {'error': 'Redis not available'}
        
        pattern = f"job:metrics:tenant:{tenant_id}:job:*"
        
        try:
            keys = self.redis_client.keys(pattern)
            
            if not keys:
                return {
                    'tenant_id': tenant_id,
                    'job_count': 0,
                    'metrics': []
                }
            
            metrics_list = []
            for key in keys:
                data = self.redis_client.get(key)
                if data:
                    metrics_list.append(json.loads(data))
            
            avg_cpu = sum(m.get('cpu_percent', 0) for m in metrics_list) / len(metrics_list) if metrics_list else 0
            avg_memory = sum(m.get('memory_rss_mb', 0) for m in metrics_list) / len(metrics_list) if metrics_list else 0
            
            return {
                'tenant_id': tenant_id,
                'job_count': len(metrics_list),
                'avg_cpu_percent': round(avg_cpu, 2),
                'avg_memory_mb': round(avg_memory, 2),
                'metrics': metrics_list
            }
        
        except Exception as e:
            logger.error(f"Failed to get tenant metrics summary: {e}")
            return {
                'tenant_id': tenant_id,
                'error': str(e)
            }
    
    def check_resource_availability(self) -> bool:
        """
        Check if system has sufficient resources for new jobs
        
        Returns:
            True if resources are available, False otherwise
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory_percent = psutil.virtual_memory().percent
            
            if cpu_percent > 90:
                logger.warning(f"CPU usage high: {cpu_percent}%")
                return False
            
            if memory_percent > 90:
                logger.warning(f"Memory usage high: {memory_percent}%")
                return False
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to check resource availability: {e}")
            return True
