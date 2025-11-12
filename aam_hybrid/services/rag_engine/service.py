"""
RAG Engine Service - The Intelligence Core
Performs retrieval-augmented generation for schema repair
"""
import json
import logging
from typing import List, Optional
from openai import AsyncOpenAI
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from aam_hybrid.shared.config import settings
from aam_hybrid.shared.models import RepairKnowledgeBase, DriftEvent, RepairProposal, ConnectionStatus, StatusUpdate
from aam_hybrid.shared.event_bus import event_bus
from aam_hybrid.shared.database import AsyncSessionLocal
from aam_hybrid.services.rag_engine.embedding_service import embedding_service

logger = logging.getLogger(__name__)


class RAGEngine:
    """
    RAG-powered self-healing engine
    Retrieves similar past repairs and uses LLM to generate new syncCatalog
    """
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
        self.model = settings.LLM_MODEL_NAME
    
    async def handle_drift_detected(self, event_data: dict):
        """
        Handle drift detection event from Schema Observer
        
        Flow:
        1. Retrieve similar historical repairs (RAG)
        2. Generate new syncCatalog using LLM
        3. Publish repair proposal
        """
        try:
            drift_event = DriftEvent(**event_data)
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
        Perform similarity search using pgvector
        
        Args:
            error_signature: Error description to search for
            top_k: Number of similar repairs to retrieve
            
        Returns:
            List of similar repair records
        """
        try:
            # Generate embedding for the error signature
            query_embedding = await embedding_service.generate_embedding(error_signature)
            
            async with AsyncSessionLocal() as session:
                # Perform vector similarity search using pgvector's <=> operator
                query = text("""
                    SELECT id, source_type, error_signature, successful_mapping, confidence_score
                    FROM repair_knowledge_base
                    ORDER BY error_signature_embedding <=> :query_embedding
                    LIMIT :top_k
                """)
                
                result = await session.execute(
                    query,
                    {"query_embedding": str(query_embedding), "top_k": top_k}
                )
                
                repairs = []
                for row in result:
                    repairs.append({
                        "id": str(row.id),
                        "source_type": row.source_type,
                        "error_signature": row.error_signature,
                        "successful_mapping": row.successful_mapping,
                        "confidence_score": row.confidence_score
                    })
                
                return repairs
                
        except Exception as e:
            logger.error(f"Retrieval error: {e}")
            return []
    
    async def generate_repair_proposal(
        self,
        last_good_catalog: dict,
        error_signature: str,
        similar_repairs: List[dict]
    ) -> tuple[Optional[dict], float]:
        """
        Use LLM to generate a new syncCatalog based on context
        
        Returns:
            (proposed_catalog, confidence_score)
        """
        if not self.client:
            logger.warning("OpenAI API not configured - cannot generate repairs")
            return None, 0.0
        
        try:
            # Construct the prompt
            system_prompt = """You are an expert Airbyte Schema Architect specializing in API schema repair.
Your task is to analyze schema drift failures and propose corrected syncCatalog configurations.

CRITICAL: Respond ONLY with valid JSON for the syncCatalog. No explanations, no markdown, just the JSON object."""

            historical_context = "\n\n".join([
                f"Historical Repair {i+1}:\nError: {r['error_signature']}\nSolution: {json.dumps(r['successful_mapping'], indent=2)}"
                for i, r in enumerate(similar_repairs[:3])
            ]) if similar_repairs else "No historical repairs available."
            
            user_prompt = f"""Analyze this schema drift failure and propose a corrected syncCatalog.

ERROR SIGNATURE:
{error_signature}

LAST KNOWN GOOD CATALOG:
{json.dumps(last_good_catalog, indent=2)}

SIMILAR HISTORICAL REPAIRS:
{historical_context}

Generate a corrected syncCatalog that addresses the error. Respond with ONLY the JSON syncCatalog object."""

            # Call LLM
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            # Parse response
            proposed_catalog_str = response.choices[0].message.content
            proposed_catalog = json.loads(proposed_catalog_str)
            
            # MVP: High confidence if valid JSON was returned
            confidence_score = 0.95 if proposed_catalog else 0.0
            
            logger.info(f"🤖 LLM generated repair proposal (confidence: {confidence_score})")
            return proposed_catalog, confidence_score
            
        except json.JSONDecodeError as e:
            logger.error(f"LLM returned invalid JSON: {e}")
            return None, 0.0
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            return None, 0.0
    
    async def store_successful_repair(
        self,
        source_type: str,
        error_signature: str,
        successful_mapping: dict,
        confidence_score: float
    ):
        """
        Store successful repair in knowledge base (Feedback Loop)
        
        Args:
            source_type: Source type (e.g., 'Salesforce')
            error_signature: The error that was resolved
            successful_mapping: The syncCatalog that worked
            confidence_score: Confidence of this repair
        """
        try:
            # Generate embedding
            embedding = await embedding_service.generate_embedding(error_signature)
            
            async with AsyncSessionLocal() as session:
                repair_record = RepairKnowledgeBase(
                    source_type=source_type,
                    error_signature=error_signature,
                    error_signature_embedding=embedding,
                    successful_mapping=successful_mapping,
                    confidence_score=confidence_score
                )
                session.add(repair_record)
                await session.commit()
                
            logger.info(f"📚 Stored successful repair in knowledge base (source: {source_type})")
            
        except Exception as e:
            logger.error(f"Failed to store repair: {e}")
    
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
