"""Drift-sensitive workflow for testing schema evolution handling."""
import asyncio
import time
from typing import Dict, Any, List, Optional
from datetime import datetime


async def drift_sensitive_workflow(
    connector,
    endpoint: str = "/accounts",
    record_id: str = "123",
    expected_fields: List[str] = None,
    drift_fields: Dict[str, str] = None
) -> Dict[str, Any]:
    """
    Test schema drift handling by accessing fields that may change.
    
    Args:
        connector: AAM connector instance
        endpoint: API endpoint to read from
        record_id: Specific record to fetch
        expected_fields: List of expected field names
        drift_fields: Mapping of old field names to new field names
    
    Returns:
        Metrics about drift detection and handling
    """
    if expected_fields is None:
        expected_fields = ["id", "account_name", "industry", "revenue"]
    
    if drift_fields is None:
        drift_fields = {
            "account_name": "name",
            "revenue": "annual_revenue",
            "industry": "industry_type"
        }
    
    metrics = {
        "drift_detected": False,
        "missing_fields": [],
        "renamed_fields": [],
        "new_fields": [],
        "field_mappings": {},
        "requests_made": 0,
        "errors": [],
        "start_time": datetime.utcnow().isoformat()
    }
    
    try:
        # Fetch the record
        response = await connector.get(f"{endpoint}/{record_id}")
        metrics["requests_made"] += 1
        
        # Check for expected fields
        for field in expected_fields:
            if field in response:
                # Field exists as expected
                metrics["field_mappings"][field] = field
            elif field in drift_fields and drift_fields[field] in response:
                # Field has been renamed
                metrics["drift_detected"] = True
                metrics["renamed_fields"].append({
                    "old": field,
                    "new": drift_fields[field]
                })
                metrics["field_mappings"][field] = drift_fields[field]
            else:
                # Field is missing
                metrics["drift_detected"] = True
                metrics["missing_fields"].append(field)
        
        # Check for new unexpected fields
        known_fields = set(expected_fields) | set(drift_fields.values())
        for field in response.keys():
            if field not in known_fields:
                metrics["new_fields"].append(field)
        
        # Try to access data using both old and new field names
        account_name = response.get("account_name") or response.get("name")
        revenue = response.get("revenue") or response.get("annual_revenue")
        
        metrics["data_retrieved"] = {
            "account_name": account_name,
            "revenue": revenue,
            "id": response.get("id")
        }
        
    except Exception as e:
        metrics["errors"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        })
    
    return metrics


async def continuous_drift_monitor(
    connector,
    endpoint: str = "/accounts",
    duration_seconds: int = 60,
    check_interval: int = 5
) -> Dict[str, Any]:
    """
    Continuously monitor for schema drift over time.
    
    Args:
        connector: AAM connector instance
        endpoint: API endpoint to monitor
        duration_seconds: How long to monitor
        check_interval: Seconds between checks
    
    Returns:
        Timeline of drift events
    """
    start_time = time.time()
    end_time = start_time + duration_seconds
    
    metrics = {
        "total_checks": 0,
        "drift_events": [],
        "schema_versions": [],
        "start_time": datetime.utcnow().isoformat()
    }
    
    # Track schema over time
    last_schema = None
    
    while time.time() < end_time:
        try:
            # Fetch sample records
            response = await connector.get(f"{endpoint}?limit=1")
            metrics["total_checks"] += 1
            
            if response and "data" in response and len(response["data"]) > 0:
                record = response["data"][0]
                current_schema = set(record.keys())
                
                if last_schema is None:
                    # First check
                    last_schema = current_schema
                    metrics["schema_versions"].append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "fields": list(current_schema)
                    })
                elif current_schema != last_schema:
                    # Schema has changed
                    added_fields = current_schema - last_schema
                    removed_fields = last_schema - current_schema
                    
                    drift_event = {
                        "timestamp": datetime.utcnow().isoformat(),
                        "check_number": metrics["total_checks"],
                        "added_fields": list(added_fields),
                        "removed_fields": list(removed_fields)
                    }
                    
                    metrics["drift_events"].append(drift_event)
                    metrics["schema_versions"].append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "fields": list(current_schema)
                    })
                    
                    last_schema = current_schema
            
        except Exception as e:
            # Log error but continue monitoring
            if "errors" not in metrics:
                metrics["errors"] = []
            metrics["errors"].append({
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            })
        
        # Wait before next check
        await asyncio.sleep(check_interval)
    
    # Calculate final metrics
    actual_duration = time.time() - start_time
    metrics["actual_duration_seconds"] = actual_duration
    metrics["drift_detected"] = len(metrics["drift_events"]) > 0
    metrics["num_schema_versions"] = len(metrics["schema_versions"])
    
    return metrics


async def field_compatibility_test(
    connector,
    endpoint: str = "/accounts",
    num_records: int = 10
) -> Dict[str, Any]:
    """
    Test field compatibility across multiple records.
    
    Args:
        connector: AAM connector instance
        endpoint: API endpoint to test
        num_records: Number of records to analyze
    
    Returns:
        Field compatibility analysis
    """
    metrics = {
        "records_analyzed": 0,
        "field_consistency": {},
        "type_variations": {},
        "null_counts": {},
        "start_time": datetime.utcnow().isoformat()
    }
    
    all_fields = set()
    field_types = {}
    
    try:
        # Fetch multiple records
        response = await connector.get(f"{endpoint}?limit={num_records}")
        
        if response and "data" in response:
            records = response["data"]
            metrics["records_analyzed"] = len(records)
            
            for record in records:
                # Track all fields seen
                for field, value in record.items():
                    all_fields.add(field)
                    
                    # Track field presence
                    if field not in metrics["field_consistency"]:
                        metrics["field_consistency"][field] = 0
                    metrics["field_consistency"][field] += 1
                    
                    # Track null values
                    if value is None:
                        if field not in metrics["null_counts"]:
                            metrics["null_counts"][field] = 0
                        metrics["null_counts"][field] += 1
                    
                    # Track type variations
                    value_type = type(value).__name__
                    if field not in field_types:
                        field_types[field] = set()
                    field_types[field].add(value_type)
            
            # Calculate consistency percentages
            for field in all_fields:
                presence_count = metrics["field_consistency"].get(field, 0)
                metrics["field_consistency"][field] = {
                    "count": presence_count,
                    "percentage": (presence_count / metrics["records_analyzed"] * 100)
                        if metrics["records_analyzed"] > 0 else 0
                }
            
            # Record type variations
            for field, types in field_types.items():
                if len(types) > 1:
                    metrics["type_variations"][field] = list(types)
    
    except Exception as e:
        metrics["error"] = str(e)
    
    return metrics