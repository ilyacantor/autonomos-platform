"""Dead Letter Queue management for failed requests."""
import asyncio
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from db import MetricsDB
from error_classifier import ErrorClass, ErrorClassifier


class DeadLetterQueue:
    """Manages failed requests that couldn't be processed."""
    
    def __init__(self, db: MetricsDB):
        self.db = db
        self.processing = False
        self.retry_tasks = []
    
    async def add_failed_request(
        self,
        connector_id: str,
        tenant_id: Optional[str],
        endpoint: str,
        method: str,
        payload: Dict[str, Any],
        error_class: ErrorClass,
        error_message: str,
        idempotency_key: Optional[str] = None
    ) -> bool:
        """Add a failed request to the DLQ."""
        # Determine if this error is worth retrying
        if not ErrorClassifier.is_retryable(error_class):
            max_retries = 0  # Don't retry non-retryable errors
        else:
            max_retries = 3
        
        return self.db.add_to_dlq(
            connector_id=connector_id,
            tenant_id=tenant_id,
            endpoint=endpoint,
            method=method,
            payload=payload,
            error_type=error_class.value,
            error_message=error_message,
            idempotency_key=idempotency_key,
            max_retries=max_retries
        )
    
    async def process_dlq(self, connector_manager):
        """Process pending DLQ entries."""
        if self.processing:
            return
        
        self.processing = True
        try:
            # Get pending entries
            entries = self.db.get_dlq_entries(status="pending", limit=10)
            
            for entry in entries:
                # Check if we've exceeded max retries
                if entry['retry_count'] >= entry['max_retries']:
                    self.db.update_dlq_entry(
                        entry['id'],
                        status="failed",
                        error_message="Max retries exceeded"
                    )
                    continue
                
                # Try to process the entry
                try:
                    connector = connector_manager.get_connector(
                        entry['connector_id']
                    )
                    
                    if entry['method'] == 'POST':
                        response = await connector.post(
                            entry['endpoint'],
                            entry['payload'],
                            idempotency_key=entry['idempotency_key']
                        )
                    elif entry['method'] == 'PUT':
                        response = await connector.put(
                            entry['endpoint'],
                            entry['payload'],
                            idempotency_key=entry['idempotency_key']
                        )
                    else:
                        # GET, DELETE etc don't have payloads
                        response = await connector.request(
                            entry['method'],
                            entry['endpoint']
                        )
                    
                    # Success! Mark as processed
                    self.db.update_dlq_entry(
                        entry['id'],
                        status="processed"
                    )
                    
                except Exception as e:
                    # Failed again, increment retry count
                    self.db.update_dlq_entry(
                        entry['id'],
                        status="pending",
                        retry_count=entry['retry_count'] + 1,
                        error_message=str(e)
                    )
        
        finally:
            self.processing = False
    
    def start_background_processor(self, connector_manager, interval_seconds: int = 30):
        """Start a background task to process DLQ entries."""
        async def processor():
            while True:
                await asyncio.sleep(interval_seconds)
                await self.process_dlq(connector_manager)
        
        task = asyncio.create_task(processor())
        self.retry_tasks.append(task)
        return task
    
    def get_stats(self) -> Dict[str, int]:
        """Get DLQ statistics."""
        entries = self.db.get_dlq_entries(status="pending", limit=1000)
        failed = self.db.get_dlq_entries(status="failed", limit=1000)
        processed = self.db.get_dlq_entries(status="processed", limit=1000)
        
        return {
            "pending": len(entries),
            "failed": len(failed),
            "processed": len(processed),
            "total": len(entries) + len(failed) + len(processed)
        }