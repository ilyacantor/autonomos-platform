"""High-volume read workflow for stress-testing rate limits."""
import asyncio
import time
from typing import Dict, Any
from datetime import datetime


async def high_volume_read_workflow(
    connector,
    endpoint: str = "/accounts",
    duration_seconds: int = 30,
    requests_per_second: int = 10
) -> Dict[str, Any]:
    """
    Repeatedly GET from paginated endpoint, stress-testing rate limits.
    
    Args:
        connector: AAM connector instance
        endpoint: API endpoint to read from
        duration_seconds: How long to run the test
        requests_per_second: Target request rate
    
    Returns:
        Metrics from the workflow execution
    """
    start_time = time.time()
    end_time = start_time + duration_seconds
    
    metrics = {
        "total_requests": 0,
        "successful_requests": 0,
        "failed_requests": 0,
        "rate_limited": 0,
        "errors": [],
        "start_time": datetime.utcnow().isoformat(),
        "duration_seconds": duration_seconds
    }
    
    page = 1
    request_interval = 1.0 / requests_per_second
    
    while time.time() < end_time:
        request_start = time.time()
        
        try:
            # Make paginated request
            response = await connector.get(
                f"{endpoint}?page={page}&limit=50"
            )
            
            metrics["total_requests"] += 1
            metrics["successful_requests"] += 1
            
            # Check if there are more pages
            if response.get("has_more", False):
                page += 1
            else:
                page = 1  # Reset to first page
            
        except Exception as e:
            metrics["total_requests"] += 1
            metrics["failed_requests"] += 1
            
            error_msg = str(e)
            if "429" in error_msg or "rate" in error_msg.lower():
                metrics["rate_limited"] += 1
            
            # Track first 10 errors
            if len(metrics["errors"]) < 10:
                metrics["errors"].append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "error": error_msg
                })
        
        # Control request rate
        elapsed = time.time() - request_start
        if elapsed < request_interval:
            await asyncio.sleep(request_interval - elapsed)
    
    # Calculate final metrics
    actual_duration = time.time() - start_time
    metrics["actual_duration_seconds"] = actual_duration
    metrics["effective_rps"] = metrics["total_requests"] / actual_duration if actual_duration > 0 else 0
    metrics["success_rate"] = (
        metrics["successful_requests"] / metrics["total_requests"] * 100
        if metrics["total_requests"] > 0 else 0
    )
    
    return metrics