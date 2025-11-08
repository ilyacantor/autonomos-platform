"""
Funnel Metrics Tracker for AAM Auto-Onboarding

Redis-backed counters tracking progression through the onboarding funnel:
eligible → reachable → active

SLO: coverage = active / eligible ≥ 0.90
"""

import logging
from typing import Optional
import redis

logger = logging.getLogger(__name__)


class FunnelMetricsTracker:
    """
    Tracks auto-onboarding funnel metrics in Redis with namespace isolation
    
    Metrics tracked:
    - eligible: Intents received (mappable + sanctioned + credentialed)
    - reachable: Passed health check
    - active: Tiny first sync succeeded
    - awaiting_credentials: Missing credentials
    - network_blocked: Health check failed
    - unsupported_type: Source type not in allowlist
    - healing: In HEALING state
    - error: Onboarding exception
    """
    
    def __init__(self, redis_client: redis.Redis):
        """
        Initialize funnel metrics tracker
        
        Args:
            redis_client: Redis client for storing counters
        """
        self.redis = redis_client
        logger.info("FunnelMetricsTracker initialized")
    
    def _key(self, namespace: str, metric: str) -> str:
        """Generate Redis key for metric"""
        return f"aam:funnel:{namespace}:{metric}"
    
    def increment(self, namespace: str, metric: str, amount: int = 1) -> int:
        """
        Increment a funnel metric counter
        
        Args:
            namespace: Connection namespace (autonomy or demo)
            metric: Metric name (eligible, reachable, active, etc.)
            amount: Amount to increment (default 1)
            
        Returns:
            New counter value
        """
        key = self._key(namespace, metric)
        new_value = self.redis.incr(key, amount)
        logger.debug(f"Incremented {metric} for {namespace}: {new_value}")
        return new_value
    
    def decrement(self, namespace: str, metric: str, amount: int = 1) -> int:
        """
        Decrement a funnel metric counter
        
        Args:
            namespace: Connection namespace
            metric: Metric name
            amount: Amount to decrement
            
        Returns:
            New counter value
        """
        key = self._key(namespace, metric)
        new_value = self.redis.decr(key, amount)
        logger.debug(f"Decremented {metric} for {namespace}: {new_value}")
        return new_value
    
    def get(self, namespace: str, metric: str) -> int:
        """
        Get current value of a funnel metric
        
        Args:
            namespace: Connection namespace
            metric: Metric name
            
        Returns:
            Counter value (0 if not set)
        """
        key = self._key(namespace, metric)
        value = self.redis.get(key)
        return int(value) if value else 0
    
    def get_all(self, namespace: str) -> dict:
        """
        Get all funnel metrics for a namespace
        
        Args:
            namespace: Connection namespace
            
        Returns:
            Dictionary of all funnel metrics with SLO calculation
        """
        metrics = {
            'eligible': self.get(namespace, 'eligible'),
            'reachable': self.get(namespace, 'reachable'),
            'active': self.get(namespace, 'active'),
            'awaiting_credentials': self.get(namespace, 'awaiting_credentials'),
            'network_blocked': self.get(namespace, 'network_blocked'),
            'unsupported_type': self.get(namespace, 'unsupported_type'),
            'healing': self.get(namespace, 'healing'),
            'error': self.get(namespace, 'error'),
        }
        
        # Calculate SLO coverage
        eligible = metrics['eligible']
        active = metrics['active']
        coverage = (active / eligible) if eligible > 0 else 0.0
        slo_met = coverage >= 0.90
        
        return {
            'namespace': namespace,
            **metrics,
            'coverage': round(coverage, 4),
            'slo_met': slo_met,
            'target': 0.90
        }
    
    def reset(self, namespace: str) -> None:
        """
        Reset all funnel metrics for a namespace
        
        Args:
            namespace: Connection namespace
        """
        metrics = ['eligible', 'reachable', 'active', 'awaiting_credentials',
                   'network_blocked', 'unsupported_type', 'healing', 'error']
        
        for metric in metrics:
            key = self._key(namespace, metric)
            self.redis.delete(key)
        
        logger.info(f"Reset all funnel metrics for namespace: {namespace}")
    
    def transition(self, namespace: str, from_metric: str, to_metric: str) -> None:
        """
        Move a connection from one funnel stage to another
        
        Args:
            namespace: Connection namespace
            from_metric: Source metric to decrement
            to_metric: Target metric to increment
        """
        if from_metric:
            self.decrement(namespace, from_metric)
        self.increment(namespace, to_metric)
        logger.info(f"Funnel transition {namespace}: {from_metric} → {to_metric}")
