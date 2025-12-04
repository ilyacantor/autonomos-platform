"""
DCL Output Adapter Stub

This is a stub module after DCL v1 removal. 
DCL v2 is now an external service - this stub maintains backward compatibility.
"""

import logging
from typing import List, Dict, Any, Optional
from redis import Redis

logger = logging.getLogger(__name__)


def publish_to_dcl_stream(
    tenant_id: str,
    connector_type: str,
    canonical_events: List[Any],
    redis_client: Optional[Redis] = None
) -> Dict[str, Any]:
    """
    Stub for DCL stream publishing after DCL v1 removal.
    
    DCL v2 is now an external service. This stub maintains API compatibility
    for any callers that haven't been updated yet.
    
    Returns:
        Dict with stub response indicating DCL v1 is removed
    """
    logger.info(f"[DCL Stub] publish_to_dcl_stream called with {len(canonical_events)} events for tenant {tenant_id}")
    logger.info(f"[DCL Stub] DCL v1 removed - use DCL v2 external service for data orchestration")
    
    return {
        'success': True,
        'batches_published': 0,
        'total_records': len(canonical_events),
        'stream_key': f'aam:canonical:{tenant_id}',
        'note': 'DCL v1 removed. Events not published to legacy DCL stream.'
    }
