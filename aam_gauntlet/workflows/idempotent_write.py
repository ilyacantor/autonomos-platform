"""Idempotent write workflow for testing write resilience."""
import asyncio
import time
import random
from typing import Dict, Any, List
from datetime import datetime


async def idempotent_write_workflow(
    connector,
    endpoint: str = "/invoices",
    num_writes: int = 50,
    failure_injection_rate: float = 0.1
) -> Dict[str, Any]:
    """
    POST invoices with idempotency, handling failures gracefully.
    
    Args:
        connector: AAM connector instance
        endpoint: API endpoint to write to
        num_writes: Number of write operations to perform
        failure_injection_rate: Probability of simulated failures
    
    Returns:
        Metrics from the workflow execution
    """
    start_time = time.time()
    
    metrics = {
        "total_writes": 0,
        "successful_writes": 0,
        "failed_writes": 0,
        "retried_writes": 0,
        "dlq_entries": 0,
        "idempotency_hits": 0,
        "errors": [],
        "start_time": datetime.utcnow().isoformat()
    }
    
    # Track idempotency keys for verification
    idempotency_keys = []
    
    for i in range(num_writes):
        # Generate invoice data
        invoice = {
            "invoice_number": f"INV-{i:05d}",
            "amount": 100 + (i * 10),
            "customer": f"CUST-{i % 10:03d}",
            "items": [
                {
                    "product": f"PROD-{j:03d}",
                    "quantity": random.randint(1, 5),
                    "price": random.uniform(10, 100)
                }
                for j in range(random.randint(1, 3))
            ],
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Simulate occasional duplicate submissions (idempotency test)
        duplicate_submission = random.random() < 0.2  # 20% chance
        
        try:
            # First attempt
            response = await connector.post(
                endpoint,
                invoice,
                generate_idempotency=True
            )
            
            metrics["total_writes"] += 1
            metrics["successful_writes"] += 1
            
            # If duplicate submission, try again with same data
            if duplicate_submission:
                await asyncio.sleep(0.1)
                response2 = await connector.post(
                    endpoint,
                    invoice,
                    generate_idempotency=True
                )
                
                # Check if idempotency worked (should get same response)
                if response == response2:
                    metrics["idempotency_hits"] += 1
                
        except Exception as e:
            metrics["total_writes"] += 1
            metrics["failed_writes"] += 1
            
            error_msg = str(e)
            
            # Track if this went to DLQ
            if "dlq" in error_msg.lower() or "dead letter" in error_msg.lower():
                metrics["dlq_entries"] += 1
            
            # Track first 10 errors
            if len(metrics["errors"]) < 10:
                metrics["errors"].append({
                    "invoice_number": invoice["invoice_number"],
                    "timestamp": datetime.utcnow().isoformat(),
                    "error": error_msg
                })
        
        # Small delay between writes
        await asyncio.sleep(0.05)
    
    # Calculate final metrics
    duration = time.time() - start_time
    metrics["duration_seconds"] = duration
    metrics["writes_per_second"] = metrics["total_writes"] / duration if duration > 0 else 0
    metrics["success_rate"] = (
        metrics["successful_writes"] / metrics["total_writes"] * 100
        if metrics["total_writes"] > 0 else 0
    )
    
    return metrics


async def bulk_write_workflow(
    connector,
    endpoint: str = "/bulk/invoices",
    batch_size: int = 100,
    num_batches: int = 10
) -> Dict[str, Any]:
    """
    Test bulk write operations with larger payloads.
    
    Args:
        connector: AAM connector instance
        endpoint: Bulk API endpoint
        batch_size: Number of records per batch
        num_batches: Number of batches to send
    
    Returns:
        Metrics from the bulk operation
    """
    start_time = time.time()
    
    metrics = {
        "total_batches": 0,
        "successful_batches": 0,
        "failed_batches": 0,
        "total_records": 0,
        "successful_records": 0,
        "start_time": datetime.utcnow().isoformat()
    }
    
    for batch_num in range(num_batches):
        # Generate batch of records
        batch = {
            "batch_id": f"BATCH-{batch_num:04d}",
            "records": [
                {
                    "invoice_number": f"INV-{batch_num:04d}-{i:05d}",
                    "amount": random.uniform(100, 10000),
                    "customer": f"CUST-{random.randint(1, 100):03d}"
                }
                for i in range(batch_size)
            ]
        }
        
        try:
            response = await connector.post(
                endpoint,
                batch,
                generate_idempotency=True
            )
            
            metrics["total_batches"] += 1
            metrics["successful_batches"] += 1
            metrics["total_records"] += batch_size
            metrics["successful_records"] += response.get("processed", batch_size)
            
        except Exception as e:
            metrics["total_batches"] += 1
            metrics["failed_batches"] += 1
            metrics["total_records"] += batch_size
        
        # Delay between batches
        await asyncio.sleep(1)
    
    # Calculate final metrics
    duration = time.time() - start_time
    metrics["duration_seconds"] = duration
    metrics["records_per_second"] = metrics["successful_records"] / duration if duration > 0 else 0
    
    return metrics