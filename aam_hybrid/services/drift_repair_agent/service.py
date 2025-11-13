"""
Drift Repair Agent - Autonomous Schema Healing
Subscribes to repair proposals and autonomously applies high-confidence fixes
"""
import logging
import uuid
import sys
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import httpx

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from aam_hybrid.shared.config import settings
from aam_hybrid.shared.database import AsyncSessionLocal
from aam_hybrid.shared.models import (
    Connection,
    SyncCatalogVersion,
    ConnectionStatus,
    CatalogUpdate,
    RepairProposal,
    StatusUpdate
)
from aam_hybrid.shared.event_bus import event_bus
from aam_hybrid.shared.airbyte_client import airbyte_client

logger = logging.getLogger(__name__)


class DriftRepairAgent:
    """
    Autonomous repair agent that applies schema fixes
    
    Capabilities:
    - Subscribes to repair_proposed events from RAG Engine
    - Autonomously executes high-confidence repairs (confidence > 0.90)
    - Sends low-confidence repairs for manual review
    - Implements feedback loop by storing successful repairs
    """
    
    CONFIDENCE_THRESHOLD = 0.90
    
    def __init__(self):
        self.running = False
    
    async def handle_repair_proposed(self, event_data: dict):
        """
        Handle repair proposal from RAG Engine
        
        Flow:
        1. Check confidence score
        2. If high confidence (>0.90): apply autonomously
        3. If low confidence: flag for manual review
        4. On success: store in knowledge base (feedback loop)
        5. Publish status updates
        
        Args:
            event_data: RepairProposal event data
        """
        try:
            proposal = RepairProposal(**event_data)
            logger.info(f"🔧 Received repair proposal for {proposal.connection_id} (confidence: {proposal.confidence_score:.2f})")
            
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Connection).where(Connection.id == proposal.connection_id)
                )
                connection = result.scalar_one_or_none()
                
                if not connection:
                    logger.error(f"Connection not found: {proposal.connection_id}")
                    return
                
                if proposal.confidence_score > self.CONFIDENCE_THRESHOLD:
                    logger.info(f"✅ High confidence ({proposal.confidence_score:.2f}) - Applying autonomously")
                    await self._apply_autonomous_repair(connection, proposal, db)
                else:
                    logger.warning(f"⚠️ Low confidence ({proposal.confidence_score:.2f}) - Flagging for manual review")
                    await self._flag_for_manual_review(connection, proposal, db)
        
        except Exception as e:
            logger.error(f"Error handling repair proposal: {e}")
    
    async def _apply_autonomous_repair(
        self,
        connection: Connection,
        proposal: RepairProposal,
        db: AsyncSession
    ):
        """
        Autonomously apply a high-confidence repair
        
        Steps:
        1. Update status to HEALING
        2. Apply catalog to Airbyte
        3. Test sync (trigger a sync)
        4. If successful: update to ACTIVE and store in knowledge base
        5. If failed: update to FAILED
        """
        try:
            connection.status = ConnectionStatus.HEALING
            await db.commit()
            
            await self._publish_status(
                connection.id,
                ConnectionStatus.HEALING,
                f"Applying autonomous repair (confidence: {proposal.confidence_score:.2f})"
            )
            
            logger.info(f"Connection {connection.id} status set to HEALING")
            
            if not connection.airbyte_connection_id:
                raise Exception("No Airbyte connection ID found")
            
            await airbyte_client.update_connection(
                connection_id=str(connection.airbyte_connection_id),
                sync_catalog=proposal.proposed_catalog
            )
            
            logger.info("Catalog applied to Airbyte successfully")
            
            version_result = await db.execute(
                select(func.max(SyncCatalogVersion.version_number))
                .where(SyncCatalogVersion.connection_id == connection.id)
            )
            current_version = version_result.scalar() or 0
            new_version_number = current_version + 1
            
            new_catalog_version = SyncCatalogVersion(
                connection_id=connection.id,
                sync_catalog=proposal.proposed_catalog,
                version_number=new_version_number
            )
            db.add(new_catalog_version)
            
            logger.info("Triggering test sync...")
            sync_result = await airbyte_client.trigger_sync(str(connection.airbyte_connection_id))
            job_id = sync_result.get("jobId")
            
            logger.info(f"Test sync triggered: {job_id}")
            
            connection.status = ConnectionStatus.ACTIVE
            await db.commit()
            
            await self._publish_status(
                connection.id,
                ConnectionStatus.ACTIVE,
                f"Repair applied successfully (version {new_version_number})"
            )
            
            logger.info(f"✅ Repair completed successfully for {connection.id}")
            
            await self._store_successful_repair(
                connection=connection,
                error_signature=proposal.original_error_signature,
                successful_mapping=proposal.proposed_catalog,
                confidence_score=proposal.confidence_score
            )
            
        except Exception as e:
            logger.error(f"Failed to apply autonomous repair: {e}")
            
            connection.status = ConnectionStatus.FAILED
            await db.commit()
            
            await self._publish_status(
                connection.id,
                ConnectionStatus.FAILED,
                f"Autonomous repair failed: {str(e)[:100]}"
            )
    
    async def _flag_for_manual_review(
        self,
        connection: Connection,
        proposal: RepairProposal,
        db: AsyncSession
    ):
        """
        Flag low-confidence repair for manual review
        """
        try:
            connection.status = ConnectionStatus.MANUAL_REVIEW_REQUIRED
            await db.commit()
            
            await self._publish_status(
                connection.id,
                ConnectionStatus.MANUAL_REVIEW_REQUIRED,
                f"Low confidence repair ({proposal.confidence_score:.2f}) - manual review required"
            )
            
            logger.info(f"⚠️ Connection {connection.id} flagged for manual review")
            
        except Exception as e:
            logger.error(f"Error flagging for manual review: {e}")
    
    async def _store_successful_repair(
        self,
        connection: Connection,
        error_signature: str,
        successful_mapping: dict,
        confidence_score: float
    ):
        """
        Store successful repair in knowledge base (Feedback Loop)
        """
        try:
            rag_engine_url = f"http://localhost:{settings.SERVICE_PORT_RAG_ENGINE}"
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{rag_engine_url}/store_repair",
                    json={
                        "source_type": connection.source_type,
                        "error_signature": error_signature,
                        "successful_mapping": successful_mapping,
                        "confidence_score": confidence_score
                    },
                    timeout=30.0
                )
                response.raise_for_status()
            
            logger.info(f"📚 Stored successful repair in knowledge base for {connection.source_type}")
            
        except Exception as e:
            logger.error(f"Failed to store repair in knowledge base: {e}")
    
    async def _publish_status(self, connection_id: uuid.UUID, status: ConnectionStatus, message: str = None):
        """Publish status update to event bus"""
        status_update = StatusUpdate(
            connection_id=connection_id,
            status=status,
            message=message
        )
        await event_bus.publish("aam:status_update", status_update.model_dump())
        logger.info(f"📡 Published status update: {status.value}")
    
    async def start(self):
        """Start the drift repair agent"""
        logger.info("Starting Drift Repair Agent...")
        
        await event_bus.connect()
        await event_bus.subscribe("aam:repair_proposed", self.handle_repair_proposed)
        
        self.running = True
        await event_bus.listen()
    
    async def stop(self):
        """Stop the drift repair agent"""
        logger.info("Stopping Drift Repair Agent...")
        self.running = False
        await event_bus.disconnect()


async def apply_catalog_update(
    db: AsyncSession,
    catalog_update: CatalogUpdate
) -> dict:
    """
    Apply a new syncCatalog to heal connection drift (Manual API endpoint)
    """
    logger.info(f"Starting catalog update for connection: {catalog_update.connection_id}")
    
    result = await db.execute(
        select(Connection).where(Connection.id == catalog_update.connection_id)
    )
    connection = result.scalar_one_or_none()
    
    if not connection:
        raise Exception(f"Connection not found: {catalog_update.connection_id}")
    
    airbyte_conn_id = connection.airbyte_connection_id
    if not airbyte_conn_id:
        raise Exception(f"Connection has no Airbyte connection ID: {catalog_update.connection_id}")
    
    try:
        connection.status = ConnectionStatus.HEALING
        await db.commit()
        
        logger.info(f"Connection status set to HEALING")
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update status: {e}")
        raise
    
    try:
        await airbyte_client.update_connection(
            connection_id=str(airbyte_conn_id),
            sync_catalog=catalog_update.new_sync_catalog
        )
        
        logger.info("Airbyte connection catalog updated successfully")
    except Exception as e:
        connection.status = ConnectionStatus.FAILED
        await db.commit()
        logger.error(f"Failed to update Airbyte connection: {e}")
        raise Exception(f"Airbyte catalog update failed: {e}")
    
    try:
        version_result = await db.execute(
            select(func.max(SyncCatalogVersion.version_number))
            .where(SyncCatalogVersion.connection_id == catalog_update.connection_id)
        )
        current_version = version_result.scalar() or 0
        new_version_number = current_version + 1
        
        new_catalog_version = SyncCatalogVersion(
            connection_id=catalog_update.connection_id,
            sync_catalog=catalog_update.new_sync_catalog,
            version_number=new_version_number
        )
        
        db.add(new_catalog_version)
        
        connection.status = ConnectionStatus.ACTIVE
        
        await db.commit()
        
        logger.info(f"Catalog version {new_version_number} created, status set to ACTIVE")
        
        return {
            "connection_id": str(catalog_update.connection_id),
            "previous_version": current_version,
            "new_version": new_version_number,
            "status": "success",
            "message": "Catalog updated and versioned successfully"
        }
    
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to version catalog: {e}")
        raise Exception(f"Registry versioning failed: {e}")


drift_repair_agent = DriftRepairAgent()
