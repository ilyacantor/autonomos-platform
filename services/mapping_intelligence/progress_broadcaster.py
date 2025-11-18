"""
Progress Broadcasting for Bulk Mapping Jobs

Features:
- WebSocket/SSE progress broadcasting
- Redis pub/sub for multi-worker coordination
- ETA calculation based on processing rate
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
import asyncio

logger = logging.getLogger(__name__)


class ProgressBroadcaster:
    """
    Broadcasts job progress updates via Redis pub/sub
    """
    
    def __init__(self, redis_client=None):
        from shared.redis_client import get_redis_client
        self.redis_client = redis_client or get_redis_client()
        self.pubsub = None
        
        if self.redis_client:
            self.pubsub = self.redis_client.pubsub()
    
    def _get_channel_name(self, tenant_id: str, job_id: str) -> str:
        """Get Redis pub/sub channel name for a job"""
        return f"job:progress:tenant:{tenant_id}:job:{job_id}"
    
    def publish_progress(
        self,
        tenant_id: str,
        job_id: str,
        processed: int,
        total: int,
        status: str,
        metadata: Optional[Dict] = None
    ):
        """
        Publish progress update to Redis channel
        
        Args:
            tenant_id: Tenant identifier
            job_id: Job identifier
            processed: Number of items processed
            total: Total number of items
            status: Current job status
            metadata: Optional additional metadata
        """
        if not self.redis_client:
            logger.warning("Redis not available, skipping progress broadcast")
            return
        
        channel = self._get_channel_name(tenant_id, job_id)
        
        progress_data = {
            'job_id': job_id,
            'tenant_id': tenant_id,
            'processed': processed,
            'total': total,
            'status': status,
            'progress_percentage': int((processed / total * 100)) if total > 0 else 0,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if metadata:
            progress_data.update(metadata)
        
        eta = self._calculate_eta(processed, total, metadata)
        if eta:
            progress_data['eta_seconds'] = eta
            progress_data['eta_human'] = self._format_eta(eta)
        
        try:
            self.redis_client.publish(channel, json.dumps(progress_data))
            logger.debug(f"Published progress for job {job_id}: {processed}/{total}")
        except Exception as e:
            logger.error(f"Failed to publish progress: {e}")
    
    def subscribe_to_job(self, tenant_id: str, job_id: str):
        """
        Subscribe to progress updates for a specific job
        
        Args:
            tenant_id: Tenant identifier
            job_id: Job identifier
        
        Returns:
            Redis pubsub subscription
        """
        if not self.pubsub:
            logger.warning("Redis pub/sub not available")
            return None
        
        channel = self._get_channel_name(tenant_id, job_id)
        self.pubsub.subscribe(channel)
        logger.info(f"Subscribed to job progress: {channel}")
        return self.pubsub
    
    def unsubscribe_from_job(self, tenant_id: str, job_id: str):
        """Unsubscribe from job progress updates"""
        if not self.pubsub:
            return
        
        channel = self._get_channel_name(tenant_id, job_id)
        self.pubsub.unsubscribe(channel)
        logger.info(f"Unsubscribed from job progress: {channel}")
    
    def _calculate_eta(
        self,
        processed: int,
        total: int,
        metadata: Optional[Dict]
    ) -> Optional[int]:
        """
        Calculate estimated time to completion in seconds
        
        Args:
            processed: Number of items processed
            total: Total number of items
            metadata: Metadata containing timing information
        
        Returns:
            ETA in seconds, or None if cannot be calculated
        """
        if not metadata or processed == 0:
            return None
        
        start_time_str = metadata.get('started_at')
        if not start_time_str:
            return None
        
        try:
            start_time = datetime.fromisoformat(start_time_str)
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            
            if elapsed <= 0:
                return None
            
            rate = processed / elapsed
            
            remaining = total - processed
            if remaining <= 0:
                return 0
            
            eta = remaining / rate
            return int(eta)
        
        except Exception as e:
            logger.warning(f"Failed to calculate ETA: {e}")
            return None
    
    def _format_eta(self, seconds: int) -> str:
        """
        Format ETA seconds into human-readable string
        
        Args:
            seconds: ETA in seconds
        
        Returns:
            Human-readable ETA string
        """
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes}m {seconds % 60}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"
    
    async def listen_for_updates(self, tenant_id: str, job_id: str, callback):
        """
        Async listener for job progress updates
        
        Args:
            tenant_id: Tenant identifier
            job_id: Job identifier
            callback: Async callback function to process updates
        """
        if not self.pubsub:
            logger.warning("Redis pub/sub not available for listening")
            return
        
        self.subscribe_to_job(tenant_id, job_id)
        
        try:
            for message in self.pubsub.listen():
                if message['type'] == 'message':
                    try:
                        data = json.loads(message['data'])
                        await callback(data)
                        
                        if data.get('status') in ['completed', 'failed']:
                            logger.info(f"Job {job_id} finished, stopping listener")
                            break
                    
                    except Exception as e:
                        logger.error(f"Error processing progress message: {e}")
        
        finally:
            self.unsubscribe_from_job(tenant_id, job_id)
