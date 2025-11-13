"""
Data Contract: AOA → AOD (AOS Discover) Interface

This module defines the canonical data structure for the API communication between
the Main AOS Demo (AOA) and the AOS Discover service (AOD).

The contract ensures:
- Type safety between microservices
- Clear request/response schema
- Structured discovery results with confidence scoring
- Agent recommendations and provenance tracking
"""

from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class DiscoveryType(str, Enum):
    """Types of discovery operations supported"""
    ENTITY_MAPPING = "entity_mapping"
    DATA_SOURCE_DISCOVERY = "data_source_discovery"
    SCHEMA_ANALYSIS = "schema_analysis"
    RELATIONSHIP_DISCOVERY = "relationship_discovery"


class ConfidenceLevel(str, Enum):
    """Confidence levels for discovery results"""
    HIGH = "high"       # >= 0.9
    MEDIUM = "medium"   # >= 0.7
    LOW = "low"         # >= 0.5
    VERY_LOW = "very_low"  # < 0.5


class DiscoveredEntity(BaseModel):
    """A single discovered entity with metadata"""
    entity_id: str = Field(..., description="Unique identifier for this entity")
    entity_type: str = Field(..., description="Entity type (e.g., 'opportunity', 'account')")
    entity_name: str = Field(..., description="Human-readable entity name")
    
    source_system: str = Field(..., description="Source system name")
    source_schema: Optional[str] = Field(None, description="Source schema/table name")
    
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Discovery confidence (0-1)")
    confidence_level: ConfidenceLevel = Field(..., description="Categorized confidence level")
    
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Entity attributes")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class AgentRecommendation(BaseModel):
    """Recommended agent for processing discovered entities"""
    agent_name: str = Field(..., description="Agent identifier (e.g., 'finops_pilot')")
    agent_type: str = Field(..., description="Agent category (e.g., 'finops', 'revops')")
    
    reason: str = Field(..., description="Why this agent was recommended")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Recommendation confidence")
    
    suggested_actions: List[str] = Field(default_factory=list, description="Actions this agent can take")
    priority: Literal["high", "medium", "low"] = Field("medium", description="Processing priority")


class DiscoveryProvenance(BaseModel):
    """Tracks how the discovery was performed"""
    discovery_method: Literal["llm", "rag", "heuristic", "hybrid"] = Field(
        ..., description="Method used for discovery"
    )
    llm_model: Optional[str] = Field(None, description="LLM model if used")
    rag_sources: List[str] = Field(default_factory=list, description="RAG knowledge sources used")
    
    processing_time_ms: float = Field(..., description="Time taken for discovery")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    human_review_required: bool = Field(False, description="Whether human review is needed")
    review_reason: Optional[str] = Field(None, description="Reason for human review")


class DiscoveryRequest(BaseModel):
    """
    Request format for AOD discovery service.
    
    This is sent from AOA to AOD for entity discovery.
    """
    nlp_query: str = Field(..., description="Natural language query from user")
    tenant_id: str = Field(..., description="Tenant identifier for isolation")
    
    discovery_types: List[DiscoveryType] = Field(
        default=[DiscoveryType.ENTITY_MAPPING],
        description="Types of discovery to perform"
    )
    
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context (e.g., filters, constraints)"
    )
    
    max_results: int = Field(10, ge=1, le=100, description="Maximum entities to return")
    min_confidence: float = Field(0.7, ge=0.0, le=1.0, description="Minimum confidence threshold")


class DiscoveryResponse(BaseModel):
    """
    Response format from AOD discovery service.
    
    This is returned from AOD to AOA with discovery results.
    """
    success: bool = Field(..., description="Whether discovery succeeded")
    request_id: str = Field(..., description="Unique request identifier for tracking")
    
    # Discovery results
    entities: List[DiscoveredEntity] = Field(default_factory=list, description="Discovered entities")
    agent_recommendations: List[AgentRecommendation] = Field(
        default_factory=list,
        description="Recommended agents for processing"
    )
    
    # Metadata
    provenance: DiscoveryProvenance = Field(..., description="Discovery methodology tracking")
    total_entities_found: int = Field(..., ge=0, description="Total entities discovered")
    filtered_count: int = Field(..., ge=0, description="Entities after filtering")
    
    # Quality indicators
    overall_confidence: float = Field(..., ge=0.0, le=1.0, description="Average confidence score")
    quality_issues: List[str] = Field(default_factory=list, description="Potential quality concerns")
    
    # Errors and warnings
    errors: List[str] = Field(default_factory=list, description="Error messages if any")
    warnings: List[str] = Field(default_factory=list, description="Warning messages")
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DiscoveryHandoff(BaseModel):
    """
    Internal format for handing off discovery results to Agents & Humans.
    
    Used within AOA to pass AOD results to downstream components.
    """
    discovery_response: DiscoveryResponse = Field(..., description="Original AOD response")
    
    # AOA enrichment
    tenant_id: str = Field(..., description="Tenant identifier")
    original_query: str = Field(..., description="Original NLP query")
    
    # Agent assignment
    assigned_agents: List[str] = Field(default_factory=list, description="Agents to process this")
    processing_priority: Literal["high", "medium", "low"] = Field("medium")
    
    # Tracking
    received_at: datetime = Field(default_factory=datetime.utcnow)
    handoff_status: Literal["pending", "assigned", "processing", "completed", "failed"] = Field(
        "pending", description="Current handoff status"
    )
    
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional handoff metadata")


# Example usage for documentation
if __name__ == "__main__":
    # Example discovery request
    example_request = DiscoveryRequest(
        nlp_query="Find all opportunities related to cloud infrastructure spending",
        tenant_id="tenant-123",
        discovery_types=[DiscoveryType.ENTITY_MAPPING, DiscoveryType.DATA_SOURCE_DISCOVERY],
        max_results=10,
        min_confidence=0.8
    )
    
    # Example discovery response
    example_entity = DiscoveredEntity(
        entity_id="opp-001",
        entity_type="opportunity",
        entity_name="Enterprise Cloud Deal",
        source_system="salesforce",
        source_schema="Opportunity",
        confidence_score=0.95,
        confidence_level=ConfidenceLevel.HIGH,
        attributes={
            "amount": 100000.0,
            "stage": "Proposal",
            "close_date": "2025-12-31"
        }
    )
    
    example_agent_rec = AgentRecommendation(
        agent_name="finops_pilot",
        agent_type="finops",
        reason="Query mentions 'cloud infrastructure spending' which matches FinOps domain",
        confidence_score=0.92,
        suggested_actions=["Analyze cost trends", "Optimize cloud spend"],
        priority="high"
    )
    
    example_provenance = DiscoveryProvenance(
        discovery_method="hybrid",
        llm_model="gemini-2.0-flash",
        rag_sources=["domain_knowledge", "schema_catalog"],
        processing_time_ms=250.5,
        human_review_required=False
    )
    
    example_response = DiscoveryResponse(
        success=True,
        request_id="req-abc-123",
        entities=[example_entity],
        agent_recommendations=[example_agent_rec],
        provenance=example_provenance,
        total_entities_found=1,
        filtered_count=1,
        overall_confidence=0.95,
        quality_issues=[]
    )
    
    print("AOA → AOD Discovery Contract Example:")
    print("=" * 60)
    print("\nRequest:")
    print(example_request.json(indent=2))
    print("\nResponse:")
    print(example_response.json(indent=2))
