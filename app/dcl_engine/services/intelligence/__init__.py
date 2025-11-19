"""
DCL Intelligence Layer - Phase 2

Centralized intelligence services for LLM proposals, RAG lookup,
confidence scoring, drift repair, and approval workflows.

Achieves 100% RACI compliance by moving ALL decision-making from AAM to DCL.
"""

import logging

from .llm_proposal_service import LLMProposalService
from .rag_lookup_service import RAGLookupService
from .confidence_service import ConfidenceScoringService
from .drift_repair_service import DriftRepairService
from .approval_service import MappingApprovalService

logger = logging.getLogger(__name__)

# Phase 4: Flow Event Publisher for DCL telemetry
_flow_publisher = None

def set_flow_publisher(publisher):
    """Inject FlowEventPublisher from main app into DCL intelligence services"""
    global _flow_publisher
    _flow_publisher = publisher
    logger.info("FlowEventPublisher injected into DCL intelligence services")

def get_flow_publisher():
    """Get the injected FlowEventPublisher"""
    return _flow_publisher

__all__ = [
    "LLMProposalService",
    "RAGLookupService",
    "ConfidenceScoringService",
    "DriftRepairService",
    "MappingApprovalService",
    "set_flow_publisher",
    "get_flow_publisher",
]
