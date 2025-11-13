"""
Schema Observer Service - Drift Detection Engine
Monitors Airbyte sync jobs and detects schema drift failures
"""
import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional, List
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from aam_hybrid.shared.config import settings
from aam_hybrid.shared.database import AsyncSessionLocal
from aam_hybrid.shared.models import (
    Connection,
    SyncCatalogVersion,
    JobHistory,
    ConnectionStatus,
    JobStatus,
    DriftEvent,
    StatusUpdate
)
from aam_hybrid.shared.event_bus import event_bus
import httpx

logger = logging.getLogger(__name__)


class SchemaObserver:
    """
    Monitors Airbyte jobs for schema drift failures
    Detects schema-related errors and triggers the healing pipeline
    """
    
    POLLING_INTERVAL = 30  # seconds
    
    DRIFT_KEYWORDS = [
        "type mismatch",
        "missing column",
        "column not found",
        "schema changed",
        "unexpected field",
        "invalid type",
        "field type changed",
        "schema validation failed",
        "incompatible schema",
        "stream not found",
        "table structure changed",
        "data type mismatch"
    ]
    
    def __init__(self):
        self.running = False
        self.airbyte_base_url = settings.AIRBYTE_API_URL
        self.client_id = settings.AIRBYTE_CLIENT_ID
        self.client_secret = settings.AIRBYTE_CLIENT_SECRET
        self.access_token: Optional[str] = None
        self.use_oss = settings.AIRBYTE_USE_OSS
    
    async def _get_access_token(self, force_refresh: bool = False) -> str:
        """Get Airbyte API access token (Airbyte Cloud only)"""
        if self.access_token and not force_refresh:
            return self.access_token
        
        try:
            # Airbyte Cloud OAuth endpoint
            # API URL is like: https://api.airbyte.com/v1
            # OAuth endpoint is: https://api.airbyte.com/v1/applications/token
            base_url = self.airbyte_base_url.rstrip('/')
            oauth_url = f"{base_url}/applications/token"
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    oauth_url,
                    json={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret
                    }
                )
                response.raise_for_status()
                data = response.json()
                self.access_token = data["access_token"]
                logger.info("✅ Airbyte Cloud OAuth token refreshed successfully")
                return self.access_token
        except Exception as e:
            logger.error(f"Failed to get Airbyte access token: {e}")
            raise
    
    async def _airbyte_request(self, method: str, endpoint: str, **kwargs):
        """Make authenticated request to Airbyte API with auto-retry on 401"""
        headers = kwargs.pop("headers", {})
        headers["Content-Type"] = "application/json"
        
        # Only use OAuth for Airbyte Cloud
        if not self.use_oss:
            token = await self._get_access_token()
            headers["Authorization"] = f"Bearer {token}"
        
        url = f"{self.airbyte_base_url}/{endpoint.lstrip('/')}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(method, url, headers=headers, **kwargs)
            
            # If 401, refresh token and retry once
            if response.status_code == 401 and not self.use_oss:
                logger.warning("Access token expired, refreshing...")
                token = await self._get_access_token(force_refresh=True)
                headers["Authorization"] = f"Bearer {token}"
                response = await client.request(method, url, headers=headers, **kwargs)
            
            response.raise_for_status()
            return response.json()
    
    async def get_connection_jobs(self, airbyte_connection_id: str, limit: int = 10) -> List[dict]:
        """
        Get recent jobs for a connection
        
        Args:
            airbyte_connection_id: Airbyte connection UUID
            limit: Number of jobs to retrieve
            
        Returns:
            List of job records
        """
        try:
            result = await self._airbyte_request(
                "GET",
                f"/jobs?connectionId={airbyte_connection_id}&limit={limit}"
            )
            return result.get("data", [])
        except Exception as e:
            logger.error(f"Failed to get jobs for connection {airbyte_connection_id}: {e}")
            return []
    
    async def get_job_logs(self, job_id: str) -> Optional[str]:
        """
        Get logs for a specific job
        
        Args:
            job_id: Airbyte job ID
            
        Returns:
            Job logs as string or None
        """
        try:
            result = await self._airbyte_request("GET", f"/jobs/{job_id}")
            
            # Extract logs from job response
            logs = result.get("logs", "")
            if not logs:
                # Try to get from attempts
                attempts = result.get("attempts", [])
                if attempts:
                    logs = attempts[-1].get("logs", {}).get("logLines", [])
                    if isinstance(logs, list):
                        logs = "\n".join(logs)
            
            return logs or ""
        except Exception as e:
            logger.error(f"Failed to get logs for job {job_id}: {e}")
            return None
    
    def is_schema_drift_error(self, error_message: str) -> bool:
        """
        Analyze error message to determine if it's schema drift
        
        Args:
            error_message: Error message from failed job
            
        Returns:
            True if error indicates schema drift
        """
        if not error_message:
            return False
        
        error_lower = error_message.lower()
        
        for keyword in self.DRIFT_KEYWORDS:
            if keyword.lower() in error_lower:
                logger.info(f"Detected drift keyword: '{keyword}' in error message")
                return True
        
        return False
    
    async def process_connection(self, connection: Connection, db: AsyncSession):
        """
        Check a single connection for drift
        
        Args:
            connection: Connection record from database
            db: Database session
        """
        if not connection.airbyte_connection_id:
            return
        
        try:
            # Get recent jobs from Airbyte
            jobs = await self.get_connection_jobs(str(connection.airbyte_connection_id), limit=5)
            
            if not jobs:
                return
            
            # Check for failed jobs
            for job in jobs:
                job_id = str(job.get("jobId"))  # Convert to string for database
                job_status = job.get("status", "").lower()
                
                # Skip if not failed
                if job_status != "failed":
                    continue
                
                # Check if we've already processed this job
                existing_job = await db.execute(
                    select(JobHistory).where(JobHistory.airbyte_job_id == job_id)
                )
                if existing_job.scalar_one_or_none():
                    continue  # Already processed
                
                # Get job logs
                logs = await self.get_job_logs(job_id)
                
                if not logs:
                    logger.warning(f"No logs available for failed job {job_id}")
                    continue
                
                # Check if error is schema drift
                if self.is_schema_drift_error(logs):
                    logger.warning(f"🚨 Schema drift detected for connection {connection.id}")
                    
                    await self._handle_drift_detection(
                        connection=connection,
                        error_logs=logs,
                        job_id=job_id,
                        db=db
                    )
                    
                    # Only process one drift per polling cycle
                    break
        
        except Exception as e:
            logger.error(f"Error processing connection {connection.id}: {e}")
    
    async def _handle_drift_detection(
        self,
        connection: Connection,
        error_logs: str,
        job_id: str,
        db: AsyncSession
    ):
        """
        Handle detected drift: update status, retrieve catalog, publish event
        
        Args:
            connection: Connection with drift
            error_logs: Error logs from failed job
            job_id: Airbyte job ID
            db: Database session
        """
        try:
            # Step 1: Update connection status to DRIFTED
            connection.status = ConnectionStatus.DRIFTED
            
            # Step 2: Record failed job in history
            job_record = JobHistory(
                connection_id=connection.id,
                airbyte_job_id=job_id,
                status=JobStatus.FAILED,
                error_message=error_logs[:500]  # Truncate for storage
            )
            db.add(job_record)
            
            await db.commit()
            
            logger.info(f"Updated connection {connection.id} status to DRIFTED")
            
            # Step 3: Retrieve last known good catalog
            catalog_result = await db.execute(
                select(SyncCatalogVersion)
                .where(SyncCatalogVersion.connection_id == connection.id)
                .order_by(desc(SyncCatalogVersion.version_number))
                .limit(1)
            )
            last_catalog = catalog_result.scalar_one_or_none()
            
            if not last_catalog:
                logger.error(f"No catalog history found for connection {connection.id}")
                return
            
            # Step 4: Extract error signature (first 300 chars of error)
            error_signature = error_logs[:300] if error_logs else "Unknown schema drift error"
            
            # Step 5: Publish DriftDetected event
            drift_event = DriftEvent(
                connection_id=connection.id,
                last_good_catalog=last_catalog.sync_catalog,
                error_signature=error_signature,
                error_logs=error_logs
            )
            
            await event_bus.publish("aam:drift_detected", drift_event.model_dump())
            logger.info(f"📡 Published drift_detected event for connection {connection.id}")
            
            # Step 6: Publish status update
            status_update = StatusUpdate(
                connection_id=connection.id,
                status=ConnectionStatus.DRIFTED,
                message=f"Schema drift detected: {error_signature[:100]}"
            )
            
            await event_bus.publish("aam:status_update", status_update.model_dump())
            logger.info(f"📡 Published status_update event (DRIFTED)")
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error handling drift detection: {e}")
    
    async def polling_loop(self):
        """
        Main polling loop - runs continuously in the background
        Checks all active connections every 30 seconds
        """
        logger.info(f"🔄 Schema Observer polling loop started (interval: {self.POLLING_INTERVAL}s)")
        self.running = True
        
        while self.running:
            try:
                async with AsyncSessionLocal() as db:
                    # Get all active connections
                    result = await db.execute(
                        select(Connection).where(
                            Connection.status.in_([
                                ConnectionStatus.ACTIVE,
                                ConnectionStatus.DRIFTED,
                                ConnectionStatus.HEALING
                            ])
                        )
                    )
                    connections = result.scalars().all()
                    
                    logger.debug(f"Checking {len(connections)} connections for drift...")
                    
                    # Process each connection
                    for connection in connections:
                        await self.process_connection(connection, db)
                
                # Wait before next poll
                await asyncio.sleep(self.POLLING_INTERVAL)
                
            except asyncio.CancelledError:
                logger.info("Polling loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                await asyncio.sleep(self.POLLING_INTERVAL)
    
    async def start(self):
        """Start the schema observer"""
        mode = "OSS" if self.use_oss else "Cloud"
        logger.info(f"Starting Schema Observer in {mode} mode...")
        logger.info(f"API URL: {self.airbyte_base_url}")
        
        # Connect to event bus
        await event_bus.connect()
        
        # Start polling loop
        await self.polling_loop()
    
    async def stop(self):
        """Stop the schema observer"""
        logger.info("Stopping Schema Observer...")
        self.running = False
        await event_bus.disconnect()


# Singleton instance
schema_observer = SchemaObserver()
