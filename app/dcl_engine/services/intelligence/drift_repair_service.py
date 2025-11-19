"""
Drift Repair Service - Phase 2

Orchestrates LLM + RAG + Confidence for schema drift repairs.
Coordinates the full intelligence pipeline for drift remediation.

Separation of Concerns (RACI):
- AAM: Detects drift (observes source system changes)
- DCL (this service): Proposes repairs (intelligence layer)
- AAM: Applies repairs (executes transformation)
"""

import logging
import uuid
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from .llm_proposal_service import LLMProposalService, MappingProposal
from .rag_lookup_service import RAGLookupService
from .confidence_service import ConfidenceScoringService
from ..resilience import (
    with_resilience,
    DependencyType,
    CircuitBreakerOpenError,
    TimeoutError as ResilienceTimeoutError,
    RetryExhaustedError
)

logger = logging.getLogger(__name__)


@dataclass
class FieldRepair:
    """Single field repair proposal"""
    field_name: str
    drift_type: str
    canonical_field: str
    canonical_entity: str
    confidence: float
    action: str
    reasoning: str


@dataclass
class RepairProposal:
    """Complete drift repair proposal with multiple field repairs"""
    repair_proposal_id: str
    drift_event_id: str
    field_repairs: List[FieldRepair]
    overall_confidence: float
    auto_applied_count: int
    hitl_queued_count: int
    rejected_count: int
    created_at: datetime


class DriftRepairService:
    """
    Drift repair proposal service.
    Coordinates LLM + RAG + Confidence for drift repairs.
    """
    
    def __init__(
        self,
        llm_service: LLMProposalService,
        rag_service: RAGLookupService,
        confidence_service: ConfidenceScoringService,
        db_session: AsyncSession
    ):
        """
        Initialize drift repair service.
        
        Args:
            llm_service: LLM proposal service
            rag_service: RAG lookup service
            confidence_service: Confidence scoring service
            db_session: Async SQLAlchemy session
        """
        self.llm = llm_service
        self.rag = rag_service
        self.confidence = confidence_service
        self.db = db_session
        logger.info("DriftRepairService initialized")
    
    @with_resilience(
        DependencyType.HTTP,
        operation_name="drift_repair_orchestration"
    )
    async def propose_repair(
        self,
        drift_event_id: str,
        tenant_id: str
    ) -> RepairProposal:
        """
        Generate repair proposal for schema drift.
        
        Flow:
        1. Extract drifted fields from drift_event.changes
        2. For each drifted field:
           a. Query RAG for similar drift repairs
           b. Fallback to LLM if RAG miss
           c. Score confidence
        3. Aggregate proposals into RepairProposal
        4. Store in drift_events + mapping_proposals tables
        
        Args:
            drift_event_id: DriftEvent ID from AAM schema observer
            tenant_id: Tenant identifier
            
        Returns:
            RepairProposal with field mappings, confidence, action tier
        """
        logger.info(f"Proposing repair for drift event: {drift_event_id} (tenant={tenant_id})")
        
        drift_event = await self._load_drift_event(drift_event_id, tenant_id)
        
        if not drift_event:
            raise ValueError(f"Drift event {drift_event_id} not found")
        
        drifted_fields = self._extract_drifted_fields(drift_event)
        
        logger.info(f"Analyzing {len(drifted_fields)} drifted fields")
        
        field_repairs: List[FieldRepair] = []
        
        for field_info in drifted_fields:
            try:
                repair = await self._propose_field_repair(
                    connector=drift_event['connector'],
                    source_table=drift_event['source_table'],
                    field_name=field_info['field_name'],
                    drift_type=field_info['drift_type'],
                    sample_values=field_info.get('sample_values', []),
                    tenant_id=tenant_id
                )
                
                field_repairs.append(repair)
                
            except Exception as e:
                logger.error(f"Failed to propose repair for field {field_info['field_name']}: {e}")
                field_repairs.append(
                    FieldRepair(
                        field_name=field_info['field_name'],
                        drift_type=field_info['drift_type'],
                        canonical_field='unknown_field',
                        canonical_entity='unknown',
                        confidence=0.0,
                        action='rejected',
                        reasoning=f"Error: {str(e)}"
                    )
                )
        
        proposal = self._aggregate_proposals(
            drift_event_id=drift_event_id,
            field_repairs=field_repairs
        )
        
        await self._store_repair_proposal(proposal, tenant_id)
        
        logger.info(
            f"Generated repair proposal: {proposal.repair_proposal_id} "
            f"({proposal.auto_applied_count} auto-apply, "
            f"{proposal.hitl_queued_count} HITL, "
            f"{proposal.rejected_count} rejected)"
        )
        
        return proposal
    
    async def _propose_field_repair(
        self,
        connector: str,
        source_table: str,
        field_name: str,
        drift_type: str,
        sample_values: List[Any],
        tenant_id: str
    ) -> FieldRepair:
        """
        Propose repair for a single drifted field.
        
        Uses LLMProposalService which handles RAG-first strategy internally.
        """
        mapping_proposal = await self.llm.propose_mapping(
            connector=connector,
            source_table=source_table,
            source_field=field_name,
            sample_values=sample_values,
            tenant_id=tenant_id,
            context={'drift_type': drift_type}
        )
        
        return FieldRepair(
            field_name=field_name,
            drift_type=drift_type,
            canonical_field=mapping_proposal.canonical_field,
            canonical_entity=mapping_proposal.canonical_entity,
            confidence=mapping_proposal.confidence,
            action=mapping_proposal.action,
            reasoning=mapping_proposal.reasoning
        )
    
    def _extract_drifted_fields(self, drift_event: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract drifted fields from drift_event.changes.
        
        Parses schema diff to identify added/removed/modified fields.
        """
        drifted_fields = []
        
        new_schema = drift_event.get('new_schema', {})
        old_schema = drift_event.get('old_schema', {})
        
        new_fields = set(new_schema.get('fields', {}).keys())
        old_fields = set(old_schema.get('fields', {}).keys())
        
        added_fields = new_fields - old_fields
        removed_fields = old_fields - new_fields
        
        for field in added_fields:
            drifted_fields.append({
                'field_name': field,
                'drift_type': 'added',
                'sample_values': new_schema['fields'][field].get('sample_values', [])
            })
        
        for field in removed_fields:
            drifted_fields.append({
                'field_name': field,
                'drift_type': 'removed',
                'sample_values': []
            })
        
        common_fields = new_fields & old_fields
        for field in common_fields:
            old_type = old_schema['fields'][field].get('type')
            new_type = new_schema['fields'][field].get('type')
            
            if old_type != new_type:
                drifted_fields.append({
                    'field_name': field,
                    'drift_type': 'type_changed',
                    'sample_values': new_schema['fields'][field].get('sample_values', [])
                })
        
        return drifted_fields
    
    def _aggregate_proposals(
        self,
        drift_event_id: str,
        field_repairs: List[FieldRepair]
    ) -> RepairProposal:
        """
        Aggregate field repairs into complete RepairProposal.
        
        Calculates overall confidence and counts by action tier.
        """
        auto_applied = sum(1 for r in field_repairs if r.action == 'auto_apply')
        hitl_queued = sum(1 for r in field_repairs if r.action == 'hitl_queued')
        rejected = sum(1 for r in field_repairs if r.action == 'rejected')
        
        confidences = [r.confidence for r in field_repairs if r.confidence > 0]
        overall_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return RepairProposal(
            repair_proposal_id=str(uuid.uuid4()),
            drift_event_id=drift_event_id,
            field_repairs=field_repairs,
            overall_confidence=overall_confidence,
            auto_applied_count=auto_applied,
            hitl_queued_count=hitl_queued,
            rejected_count=rejected,
            created_at=datetime.utcnow()
        )
    
    async def _load_drift_event(
        self,
        drift_event_id: str,
        tenant_id: str
    ) -> Optional[Dict[str, Any]]:
        """Load drift event from database"""
        try:
            from sqlalchemy import text
            import json
            
            query = text("""
                SELECT 
                    id,
                    connection_id,
                    event_type,
                    old_schema,
                    new_schema,
                    status
                FROM drift_events
                WHERE id = :drift_event_id
                    AND tenant_id = :tenant_id
            """)
            
            result = await self.db.execute(
                query,
                {
                    'drift_event_id': drift_event_id,
                    'tenant_id': tenant_id
                }
            )
            
            row = result.fetchone()
            
            if not row:
                return None
            
            old_schema = row.old_schema or {}
            new_schema = row.new_schema or {}
            
            if isinstance(old_schema, str):
                old_schema = json.loads(old_schema)
            if isinstance(new_schema, str):
                new_schema = json.loads(new_schema)
            
            return {
                'id': str(row.id),
                'connection_id': str(row.connection_id) if row.connection_id else None,
                'event_type': row.event_type,
                'old_schema': old_schema,
                'new_schema': new_schema,
                'connector': old_schema.get('connector', 'unknown'),
                'source_table': old_schema.get('table', 'unknown'),
                'status': row.status
            }
            
        except Exception as e:
            logger.error(f"Failed to load drift event: {e}")
            return None
    
    async def _store_repair_proposal(
        self,
        proposal: RepairProposal,
        tenant_id: str
    ):
        """
        Store repair proposal and update drift event.
        
        Links drift event to repair proposal via repair_proposal_id.
        """
        try:
            from sqlalchemy import text
            
            query = text("""
                UPDATE drift_events
                SET 
                    repair_proposal_id = :proposal_id,
                    repair_status = :repair_status
                WHERE id = :drift_event_id
                    AND tenant_id = :tenant_id
            """)
            
            repair_status = 'proposed'
            if proposal.auto_applied_count > 0:
                repair_status = 'auto_applied'
            elif proposal.hitl_queued_count > 0:
                repair_status = 'hitl_queued'
            else:
                repair_status = 'rejected'
            
            await self.db.execute(
                query,
                {
                    'proposal_id': proposal.repair_proposal_id,
                    'repair_status': repair_status,
                    'drift_event_id': proposal.drift_event_id,
                    'tenant_id': tenant_id
                }
            )
            await self.db.commit()
            
            logger.info(
                f"Stored repair proposal: {proposal.repair_proposal_id} "
                f"(status={repair_status})"
            )
            
        except Exception as e:
            logger.error(f"Failed to store repair proposal: {e}")
            await self.db.rollback()
            raise
