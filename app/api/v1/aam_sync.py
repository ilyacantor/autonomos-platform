"""
AAM Sync Module - Airbyte sync integration helpers

This module provides functions to fetch and cache Airbyte sync activity
for AAM connectors. Used by aam_connectors.py for connector status display.
"""
import logging
import time
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Import SchemaObserver singleton at module level
SCHEMA_OBSERVER_AVAILABLE = False
try:
    from aam_hybrid.services.schema_observer.service import schema_observer
    SCHEMA_OBSERVER_AVAILABLE = True
    logger.info("aam_sync: SchemaObserver imported successfully")
except Exception as e:
    logger.warning(f"aam_sync: Could not import SchemaObserver: {e}")
    schema_observer = None  # type: ignore

# Cache storage for Airbyte sync activity with TTL
_airbyte_cache: Dict[str, Dict[str, Any]] = {}
_cache_ttl = 60  # seconds


def get_airbyte_sync_activity(airbyte_connection_id: Optional[str]) -> Dict[str, Any]:
    """
    Get latest Airbyte sync activity for a connection with 60s caching (sync version).

    Calls SchemaObserver's get_connection_jobs() method and caches results for 60 seconds.

    Args:
        airbyte_connection_id: Airbyte connection UUID (can be None)

    Returns:
        Dict with keys: status, records, bytes, timestamp (all None if unavailable)
    """
    # Default response
    default = {
        "status": None,
        "records": None,
        "bytes": None,
        "timestamp": None
    }

    # Handle missing connection ID
    if not airbyte_connection_id:
        return default

    # Check if SchemaObserver is available
    if not SCHEMA_OBSERVER_AVAILABLE or not schema_observer:
        return default

    # Convert to string for cache key
    cache_key = str(airbyte_connection_id)

    # Check cache with TTL
    current_time = time.time()
    if cache_key in _airbyte_cache:
        cached_entry = _airbyte_cache[cache_key]
        if current_time - cached_entry.get("_cached_at", 0) < _cache_ttl:
            # Return cached data (excluding _cached_at)
            return {k: v for k, v in cached_entry.items() if k != "_cached_at"}

    # Fetch from Airbyte API
    try:
        # Run async SchemaObserver call in thread pool to avoid event loop conflicts
        import concurrent.futures

        def _fetch_jobs():
            """Helper to run async code in a new event loop"""
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                return new_loop.run_until_complete(
                    schema_observer.get_connection_jobs(str(airbyte_connection_id), limit=10)
                )
            finally:
                new_loop.close()

        # Execute in thread pool to avoid "event loop already running" error
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_fetch_jobs)
            jobs = future.result(timeout=10)  # 10 second timeout

        if not jobs or len(jobs) == 0:
            # Cache empty result
            result_with_cache = default.copy()
            result_with_cache["_cached_at"] = current_time  # type: ignore
            _airbyte_cache[cache_key] = result_with_cache
            return default

        # Get latest job - Airbyte returns jobs in ASCENDING order, so we need the LAST one
        # Sort by startTime to ensure we get the most recent
        sorted_jobs = sorted(
            jobs,
            key=lambda j: j.get('startTime') or j.get('createdAt') or '',
            reverse=True
        )

        # Prefer the most recent job WITH data, fall back to absolute most recent
        latest_job_with_data = None
        for job in sorted_jobs:
            records = job.get('recordsCommitted') or job.get('recordsEmitted') or job.get('rowsSynced') or 0
            bytes_val = job.get('bytesCommitted') or job.get('bytesEmitted') or job.get('bytesSynced') or 0
            if records > 0 or bytes_val > 0:
                latest_job_with_data = job
                break

        # Use job with data if available, otherwise use most recent (even if empty)
        latest_job = latest_job_with_data if latest_job_with_data else sorted_jobs[0]

        # Extract status
        status = latest_job.get("status", "").lower()

        # Parse records and bytes from job - try multiple field names
        records = (
            latest_job.get("recordsCommitted") or
            latest_job.get("recordsEmitted") or
            latest_job.get("rowsSynced") or
            0
        )
        bytes_transferred = (
            latest_job.get("bytesCommitted") or
            latest_job.get("bytesEmitted") or
            latest_job.get("bytesSynced") or
            0
        )

        # Parse timestamp - Airbyte uses "createdAt" field
        created_at_str = latest_job.get("createdAt") or latest_job.get("startTime")
        timestamp = None
        if created_at_str:
            try:
                # Parse ISO format timestamp, handle both with and without Z
                if isinstance(created_at_str, str):
                    timestamp = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                elif isinstance(created_at_str, datetime):
                    timestamp = created_at_str
            except Exception as e:
                logger.debug(f"Failed to parse timestamp {created_at_str}: {e}")

        result = {
            "status": status,
            "records": int(records) if records else None,
            "bytes": int(bytes_transferred) if bytes_transferred else None,
            "timestamp": timestamp,
            "_cached_at": current_time
        }

        # Store in cache
        _airbyte_cache[cache_key] = result

        # Return without _cached_at
        return {k: v for k, v in result.items() if k != "_cached_at"}

    except Exception as e:
        logger.error(f"Failed to get Airbyte sync activity for {airbyte_connection_id}: {e}")
        # Cache the error to avoid hammering the API
        result_with_cache = default.copy()
        result_with_cache["_cached_at"] = current_time  # type: ignore
        _airbyte_cache[cache_key] = result_with_cache
        return default


async def get_airbyte_sync_activity_async(airbyte_connection_id: Optional[str]) -> Dict[str, Any]:
    """
    Get latest Airbyte sync activity for a connection with 60s caching (async version).

    Calls SchemaObserver's get_connection_jobs() method and caches results for 60 seconds.
    Shares the same cache dictionary as the sync version for consistency.

    Args:
        airbyte_connection_id: Airbyte connection UUID (can be None)

    Returns:
        Dict with keys: status, records, bytes, timestamp (all None if unavailable)
    """
    # Default response
    default = {
        "status": None,
        "records": None,
        "bytes": None,
        "timestamp": None
    }

    # Handle missing connection ID
    if not airbyte_connection_id:
        return default

    # Check if SchemaObserver is available
    if not SCHEMA_OBSERVER_AVAILABLE or not schema_observer:
        return default

    # Convert to string for cache key
    cache_key = str(airbyte_connection_id)

    # Check cache with TTL
    current_time = time.time()
    if cache_key in _airbyte_cache:
        cached_entry = _airbyte_cache[cache_key]
        if current_time - cached_entry.get("_cached_at", 0) < _cache_ttl:
            # Return cached data (excluding _cached_at)
            return {k: v for k, v in cached_entry.items() if k != "_cached_at"}

    # Fetch from Airbyte API
    try:
        # Call async method directly (no event loop needed in async context)
        jobs = await schema_observer.get_connection_jobs(str(airbyte_connection_id), limit=10)

        if not jobs or len(jobs) == 0:
            # Cache empty result
            result_with_cache = default.copy()
            result_with_cache["_cached_at"] = current_time  # type: ignore
            _airbyte_cache[cache_key] = result_with_cache
            return default

        # Get latest job - Airbyte returns jobs in ASCENDING order, so we need the LAST one
        # Sort by startTime to ensure we get the most recent
        sorted_jobs = sorted(
            jobs,
            key=lambda j: j.get('startTime') or j.get('createdAt') or '',
            reverse=True
        )

        # Prefer the most recent job WITH data, fall back to absolute most recent
        latest_job_with_data = None
        for job in sorted_jobs:
            records = job.get('recordsCommitted') or job.get('recordsEmitted') or job.get('rowsSynced') or 0
            bytes_val = job.get('bytesCommitted') or job.get('bytesEmitted') or job.get('bytesSynced') or 0
            if records > 0 or bytes_val > 0:
                latest_job_with_data = job
                break

        # Use job with data if available, otherwise use most recent (even if empty)
        latest_job = latest_job_with_data if latest_job_with_data else sorted_jobs[0]

        # Extract status
        status = latest_job.get("status", "").lower()

        # Parse records and bytes from job - try multiple field names
        records = (
            latest_job.get("recordsCommitted") or
            latest_job.get("recordsEmitted") or
            latest_job.get("rowsSynced") or
            0
        )
        bytes_transferred = (
            latest_job.get("bytesCommitted") or
            latest_job.get("bytesEmitted") or
            latest_job.get("bytesSynced") or
            0
        )

        # Parse timestamp - Airbyte uses "createdAt" field
        created_at_str = latest_job.get("createdAt") or latest_job.get("startTime")
        timestamp = None
        if created_at_str:
            try:
                # Parse ISO format timestamp, handle both with and without Z
                if isinstance(created_at_str, str):
                    timestamp = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                elif isinstance(created_at_str, datetime):
                    timestamp = created_at_str
            except Exception as e:
                logger.debug(f"Failed to parse timestamp {created_at_str}: {e}")

        result = {
            "status": status,
            "records": int(records) if records else None,
            "bytes": int(bytes_transferred) if bytes_transferred else None,
            "timestamp": timestamp,
            "_cached_at": current_time
        }

        # Store in cache
        _airbyte_cache[cache_key] = result

        # Return without _cached_at
        return {k: v for k, v in result.items() if k != "_cached_at"}

    except Exception as e:
        logger.error(f"Failed to get Airbyte sync activity for {airbyte_connection_id}: {e}")
        # Cache the error to avoid hammering the API
        result_with_cache = default.copy()
        result_with_cache["_cached_at"] = current_time  # type: ignore
        _airbyte_cache[cache_key] = result_with_cache
        return default
