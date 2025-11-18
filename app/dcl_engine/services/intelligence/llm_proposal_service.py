"""
LLM Proposal Service - Phase 2

Generate mapping proposals using Gemini LLM with RAG-first strategy.
Coordinates RAG lookup → LLM generation → Confidence scoring → Storage.

Implements the core intelligence flow for schema drift repair.
"""

import logging
import uuid
from typing import List, Any, Optional, Dict
from dataclasses import dataclass
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.dcl_engine.llm_service import LLMService
from .rag_lookup_service import RAGLookupService
from .confidence_service import ConfidenceScoringService

logger = logging.getLogger(__name__)


@dataclass
class MappingProposal:
    """Mapping proposal result from LLM/RAG"""
    proposal_id: str
    connector: str
    source_table: str
    source_field: str
    canonical_entity: str
    canonical_field: str
    confidence: float
    reasoning: str
    alternatives: List[Dict[str, Any]]
    action: str
    source: str
    created_at: datetime


class LLMProposalService:
    """
    LLM-powered mapping proposal service.
    Uses RAG-first strategy with LLM fallback.
    """
    
    def __init__(
        self,
        llm_client: LLMService,
        rag_service: RAGLookupService,
        confidence_service: ConfidenceScoringService,
        db_session: AsyncSession
    ):
        """
        Initialize LLM proposal service.
        
        Args:
            llm_client: Gemini LLM service
            rag_service: RAG lookup service
            confidence_service: Confidence scoring service
            db_session: Async SQLAlchemy session
        """
        self.llm = llm_client
        self.rag = rag_service
        self.confidence = confidence_service
        self.db = db_session
        logger.info("LLMProposalService initialized")
    
    async def propose_mapping(
        self,
        connector: str,
        source_table: str,
        source_field: str,
        sample_values: List[Any],
        tenant_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> MappingProposal:
        """
        Propose canonical mapping for a source field.
        
        Strategy:
        1. RAG lookup (fast path, high confidence)
        2. LLM generation (slow path, medium confidence)
        3. Confidence scoring
        4. Store proposal
        
        Args:
            connector: Source connector ID (e.g., 'salesforce')
            source_table: Source table name (e.g., 'Opportunity')
            source_field: Source field name (e.g., 'Amount')
            sample_values: Sample values from source field for type inference
            tenant_id: Tenant identifier
            context: Optional metadata (drift event ID, etc.)
            
        Returns:
            MappingProposal with canonical_field, confidence, reasoning
        """
        logger.info(
            f"Proposing mapping for {connector}.{source_table}.{source_field} "
            f"(tenant={tenant_id})"
        )
        
        rag_result = await self.rag.lookup_mapping(
            connector=connector,
            source_table=source_table,
            source_field=source_field,
            tenant_id=tenant_id,
            similarity_threshold=0.90
        )
        
        if rag_result and rag_result.similarity >= 0.90:
            logger.info(
                f"RAG hit: {rag_result.canonical_field} "
                f"(similarity={rag_result.similarity:.3f})"
            )
            
            confidence_result = self.confidence.calculate_confidence(
                factors={
                    'rag_similarity': rag_result.similarity,
                    'usage_frequency': rag_result.usage_count,
                    'validation_success': rag_result.confidence,
                    'source_quality': 0.9,
                    'human_approval': False
                },
                tenant_id=tenant_id
            )
            
            proposal = await self._create_proposal(
                connector=connector,
                source_table=source_table,
                source_field=source_field,
                canonical_entity=rag_result.canonical_entity,
                canonical_field=rag_result.canonical_field,
                confidence=confidence_result.score,
                reasoning=f"RAG lookup: similar mapping found with {rag_result.similarity:.1%} similarity (used {rag_result.usage_count} times)",
                alternatives=[],
                action=confidence_result.tier,
                source="rag",
                tenant_id=tenant_id
            )
            
            return proposal
        
        logger.info("RAG miss - falling back to LLM generation")
        
        canonical_entity = self._infer_canonical_entity(source_table)
        
        prompt = self._build_llm_prompt(
            connector=connector,
            source_table=source_table,
            source_field=source_field,
            sample_values=sample_values,
            canonical_entity=canonical_entity
        )
        
        llm_response = self.llm.generate(prompt, source_key=f"{connector}.{source_table}")
        
        if not llm_response:
            raise ValueError("LLM failed to generate mapping proposal")
        
        canonical_field, alternatives, reasoning = self._parse_llm_response(llm_response)
        
        confidence_result = self.confidence.calculate_confidence(
            factors={
                'rag_similarity': 0.0,
                'usage_frequency': 0,
                'validation_success': 0.7,
                'source_quality': 0.8,
                'human_approval': False
            },
            tenant_id=tenant_id
        )
        
        proposal = await self._create_proposal(
            connector=connector,
            source_table=source_table,
            source_field=source_field,
            canonical_entity=canonical_entity,
            canonical_field=canonical_field,
            confidence=confidence_result.score,
            reasoning=reasoning,
            alternatives=alternatives,
            action=confidence_result.tier,
            source="llm",
            tenant_id=tenant_id
        )
        
        await self.rag.index_mapping(
            connector=connector,
            source_table=source_table,
            source_field=source_field,
            canonical_field=canonical_field,
            canonical_entity=canonical_entity,
            tenant_id=tenant_id,
            confidence=confidence_result.score
        )
        
        return proposal
    
    def _build_llm_prompt(
        self,
        connector: str,
        source_table: str,
        source_field: str,
        sample_values: List[Any],
        canonical_entity: str
    ) -> str:
        """
        Build LLM prompt for mapping proposal.
        
        Includes:
        - Connector context
        - Source field information
        - Sample values for type inference
        - Canonical entity hint
        - Expected output format
        """
        sample_values_str = ', '.join(str(v) for v in sample_values[:5])
        
        return f"""You are a data mapping expert. Map the following source field to a canonical field.

**Source System**: {connector}
**Source Table**: {source_table}
**Source Field**: {source_field}
**Sample Values**: {sample_values_str}

**Target Canonical Entity**: {canonical_entity}

**Instructions**:
1. Analyze the source field name and sample values
2. Determine the most appropriate canonical field name
3. Use standard naming conventions (lowercase, snake_case)
4. Provide 1-2 alternative mappings if applicable
5. Explain your reasoning

**Response Format** (JSON):
{{
    "canonical_field": "primary_mapping_name",
    "alternatives": [
        {{"field": "alternative_1", "confidence": 0.7}},
        {{"field": "alternative_2", "confidence": 0.5}}
    ],
    "reasoning": "Brief explanation of the mapping choice"
}}

**Common Canonical Fields for {canonical_entity}**:
- name, description, status, type, owner_id
- created_at, updated_at, deleted_at
- amount, currency, probability (for opportunities)
- email, phone, title (for contacts)
"""
    
    def _parse_llm_response(self, llm_response: Dict[str, Any]) -> tuple[str, List[Dict], str]:
        """
        Parse LLM JSON response.
        
        Returns:
            (canonical_field, alternatives, reasoning)
        """
        canonical_field = llm_response.get('canonical_field', 'unknown_field')
        alternatives = llm_response.get('alternatives', [])
        reasoning = llm_response.get('reasoning', 'LLM-generated mapping')
        
        canonical_field = canonical_field.lower().replace(' ', '_')
        
        return canonical_field, alternatives, reasoning
    
    def _infer_canonical_entity(self, source_table: str) -> str:
        """
        Infer canonical entity type from source table name.
        
        Simple heuristics:
        - Opportunity/Deal → opportunity
        - Account/Company → account
        - Contact/Person → contact
        - Default → lowercase table name
        """
        table_lower = source_table.lower()
        
        if any(x in table_lower for x in ['opportunity', 'deal', 'opp']):
            return 'opportunity'
        elif any(x in table_lower for x in ['account', 'company', 'organization']):
            return 'account'
        elif any(x in table_lower for x in ['contact', 'person', 'lead']):
            return 'contact'
        
        return table_lower
    
    async def _create_proposal(
        self,
        connector: str,
        source_table: str,
        source_field: str,
        canonical_entity: str,
        canonical_field: str,
        confidence: float,
        reasoning: str,
        alternatives: List[Dict],
        action: str,
        source: str,
        tenant_id: str
    ) -> MappingProposal:
        """
        Store mapping proposal in database.
        
        Creates record in mapping_proposals table.
        """
        proposal_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        
        try:
            query = text("""
                INSERT INTO mapping_proposals (
                    id, tenant_id, connector, source_table, source_field,
                    canonical_entity, canonical_field, confidence, reasoning,
                    alternatives, action, source, created_at
                ) VALUES (
                    :id, :tenant_id, :connector, :source_table, :source_field,
                    :canonical_entity, :canonical_field, :confidence, :reasoning,
                    :alternatives::jsonb, :action, :source, :created_at
                )
            """)
            
            await self.db.execute(
                query,
                {
                    'id': proposal_id,
                    'tenant_id': tenant_id,
                    'connector': connector,
                    'source_table': source_table,
                    'source_field': source_field,
                    'canonical_entity': canonical_entity,
                    'canonical_field': canonical_field,
                    'confidence': confidence,
                    'reasoning': reasoning,
                    'alternatives': str(alternatives) if alternatives else '[]',
                    'action': action,
                    'source': source,
                    'created_at': created_at
                }
            )
            await self.db.commit()
            
            logger.info(
                f"Stored proposal: {proposal_id} "
                f"({canonical_field}, confidence={confidence:.3f}, action={action})"
            )
            
        except Exception as e:
            logger.error(f"Failed to store proposal: {e}")
            await self.db.rollback()
            raise
        
        return MappingProposal(
            proposal_id=proposal_id,
            connector=connector,
            source_table=source_table,
            source_field=source_field,
            canonical_entity=canonical_entity,
            canonical_field=canonical_field,
            confidence=confidence,
            reasoning=reasoning,
            alternatives=alternatives,
            action=action,
            source=source,
            created_at=created_at
        )
