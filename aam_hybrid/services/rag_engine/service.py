"""
RAG Engine Service - PHASE 2 RACI COMPLIANT

DEPRECATED: This service no longer performs local LLM/RAG operations.
All intelligence is delegated to DCL Intelligence API (100% RACI compliance).

This service now acts as a thin proxy that delegates to DCL.
"""
import json
import logging
from typing import List, Optional
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from aam_hybrid.shared.models import AAMDriftEventPayload, RepairProposal, ConnectionStatus, StatusUpdate
from aam_hybrid.shared.event_bus import event_bus
from aam_hybrid.shared.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


class RAGEngine:
    """
    PHASE 2 RACI COMPLIANT: Proxy to DCL Intelligence API
    
    This service no longer performs local LLM/RAG operations.
    All intelligence is delegated to DCL Intelligence Layer.
    """
    
    def __init__(self):
        # PHASE 2: No local LLM client - delegate to DCL Intelligence API
        logger.info("RAGEngine initialized (PHASE 2 - RACI COMPLIANT): Delegates to DCL Intelligence API")
    
    async def handle_drift_detected(self, event_data: dict):
        """
        Handle drift detection event from Schema Observer
        
        Flow:
        1. Retrieve similar historical repairs (RAG)
        2. Generate new syncCatalog using LLM
        3. Publish repair proposal
        """
        try:
            drift_event = AAMDriftEventPayload(**event_data)
            logger.info(f"🔍 Processing drift for connection: {drift_event.connection_id}")
            
            # Step 1: Retrieval - Find similar historical repairs
            similar_repairs = await self.retrieve_similar_repairs(
                error_signature=drift_event.error_signature,
                top_k=5
            )
            
            logger.info(f"📚 Retrieved {len(similar_repairs)} similar repairs from knowledge base")
            
            # Step 2: Generation - Use LLM to propose new catalog
            proposed_catalog, confidence = await self.generate_repair_proposal(
                last_good_catalog=drift_event.last_good_catalog,
                error_signature=drift_event.error_signature,
                similar_repairs=similar_repairs
            )
            
            if not proposed_catalog:
                logger.warning(f"❌ Failed to generate repair for {drift_event.connection_id}")
                await self._publish_status(drift_event.connection_id, ConnectionStatus.MANUAL_REVIEW_REQUIRED,
                                          "LLM failed to generate valid repair proposal")
                return
            
            # Step 3: Publish repair proposal
            repair_proposal = RepairProposal(
                connection_id=drift_event.connection_id,
                proposed_catalog=proposed_catalog,
                confidence_score=confidence,
                original_error_signature=drift_event.error_signature
            )
            
            await event_bus.publish("aam:repair_proposed", repair_proposal.model_dump())
            logger.info(f"✅ Published repair proposal (confidence: {confidence:.2f})")
            
        except Exception as e:
            logger.error(f"RAG Engine error: {e}")
    
    async def retrieve_similar_repairs(self, error_signature: str, top_k: int = 5) -> List[dict]:
        """
        PHASE 2 RACI COMPLIANT: Delegated to DCL Intelligence API
        
        AAM no longer performs local RAG operations.
        This method returns empty results - DCL handles similarity search.
        """
        logger.info(
            "⚠️ PHASE 2: retrieve_similar_repairs called but AAM no longer performs RAG. "
            "DCL Intelligence API handles all similarity search via RAGLookupService."
        )
        return []
    
    async def generate_repair_proposal(
        self,
        last_good_catalog: dict,
        error_signature: str,
        similar_repairs: List[dict]
    ) -> tuple[Optional[dict], float]:
        """
        PHASE 2 RACI COMPLIANT: Delegated to DCL Intelligence API
        
        AAM no longer performs local LLM operations.
        This method returns None - DCL handles proposal generation.
        """
        logger.info(
            "⚠️ PHASE 2: generate_repair_proposal called but AAM no longer performs LLM operations. "
            "DCL Intelligence API handles all proposal generation via LLMProposalService."
        )
        return None, 0.0
    
    async def store_successful_repair(
        self,
        source_type: str,
        error_signature: str,
        successful_mapping: dict,
        confidence_score: float
    ):
        """
        PHASE 2 RACI COMPLIANT: Delegated to DCL Intelligence API
        
        AAM no longer stores repair knowledge locally.
        DCL handles all knowledge base operations.
        """
        logger.info(
            "⚠️ PHASE 2: store_successful_repair called but AAM no longer maintains RAG knowledge base. "
            "DCL Intelligence API handles all knowledge base storage."
        )
        return
    
    async def _publish_status(self, connection_id, status: ConnectionStatus, message: str = None):
        """Publish status update to event bus"""
        status_update = StatusUpdate(
            connection_id=connection_id,
            status=status,
            message=message
        )
        await event_bus.publish("aam:status_update", status_update.model_dump())


# Singleton instance
rag_engine = RAGEngine()
