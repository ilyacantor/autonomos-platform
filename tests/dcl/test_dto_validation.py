"""
Test DCL Engine DTO Validation

Validates Phase 3 Priority 3 DTO implementations including:
- Field validation and constraints
- Enum value validation
- Backward compatibility
- Tenant isolation
- Idempotency support
"""

import pytest
from typing import Dict, Any, List
from uuid import uuid4
from datetime import datetime
from pydantic import ValidationError

from app.dcl_engine.schemas.dto import (
    # Base DTOs
    BaseDTO,
    # Enums
    FeatureFlag,
    ConnectorType,
    DevMode,
    ConnectionStatus,
    AgentType,
    # Phase 1 DTOs
    ConnectRequest,
    ConnectResponse,
    StateResponse,
    GraphState,
    GraphNode,
    GraphEdge,
    ResetRequest,
    ResetResponse,
    ToggleRequest,
    ToggleResponse,
    SourceSchema,
    SourceSchemasResponse,
    # Phase 2 DTOs
    ViewsRequest,
    ViewsResponse,
    EntityView,
    UnifyRequest,
    UnifyResponse,
    UnificationMatch,
)


class TestBaseDTO:
    """Tests for BaseDTO validation and behavior"""
    
    def test_base_dto_defaults(self):
        """Test BaseDTO creates with default values"""
        dto = BaseDTO()
        assert dto.tenant_id == "default"
        assert dto.idempotency_key is None
        assert dto.trace_id is None
    
    def test_base_dto_with_values(self):
        """Test BaseDTO accepts all optional fields"""
        dto = BaseDTO(
            tenant_id="tenant_123",
            idempotency_key="req_456",
            trace_id="trace_789"
        )
        assert dto.tenant_id == "tenant_123"
        assert dto.idempotency_key == "req_456"
        assert dto.trace_id == "trace_789"
    
    def test_tenant_id_validation(self):
        """Test tenant_id validation strips whitespace and handles empty strings"""
        # Empty string defaults to "default"
        dto1 = BaseDTO(tenant_id="")
        assert dto1.tenant_id == "default"
        
        # Whitespace is stripped
        dto2 = BaseDTO(tenant_id="  tenant_abc  ")
        assert dto2.tenant_id == "tenant_abc"
        
        # None defaults to "default"
        dto3 = BaseDTO(tenant_id=None)
        assert dto3.tenant_id == "default"
    
    def test_field_length_constraints(self):
        """Test field length validation"""
        # Valid lengths
        dto = BaseDTO(
            idempotency_key="a" * 255,  # Max length
            trace_id="b" * 255,  # Max length
            tenant_id="c" * 100  # Max length
        )
        assert len(dto.idempotency_key) == 255
        
        # Invalid lengths should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            BaseDTO(idempotency_key="a" * 256)  # Too long
        assert "String should have at most 255 characters" in str(exc_info.value)


class TestEnums:
    """Tests for enum validation"""
    
    def test_feature_flag_enum(self):
        """Test FeatureFlag enum values"""
        assert FeatureFlag.DEV_MODE == "dev_mode"
        assert FeatureFlag.AUTO_INGEST == "auto_ingest"
        assert FeatureFlag.AAM_MODE == "aam_mode"
        assert FeatureFlag.RAG_ENABLED == "rag_enabled"
        assert FeatureFlag.AGENT_EXECUTION == "agent_execution"
        assert FeatureFlag.DISTRIBUTED_LOCKING == "distributed_locking"
    
    def test_connector_type_enum(self):
        """Test ConnectorType enum values"""
        assert ConnectorType.SALESFORCE == "salesforce"
        assert ConnectorType.HUBSPOT == "hubspot"
        assert ConnectorType.MONGODB == "mongodb"
        assert ConnectorType.SUPABASE == "supabase"
    
    def test_dev_mode_enum(self):
        """Test DevMode enum values"""
        assert DevMode.ENABLED == "enabled"
        assert DevMode.DISABLED == "disabled"
        assert DevMode.AUTO == "auto"
    
    def test_connection_status_enum(self):
        """Test ConnectionStatus enum values"""
        assert ConnectionStatus.ACTIVE == "active"
        assert ConnectionStatus.PENDING == "pending"
        assert ConnectionStatus.FAILED == "failed"
        assert ConnectionStatus.HEALING == "healing"
        assert ConnectionStatus.DRIFTED == "drifted"


class TestConnectDTOs:
    """Tests for /dcl/connect endpoint DTOs"""
    
    def test_connect_request_valid(self):
        """Test valid ConnectRequest creation"""
        req = ConnectRequest(
            sources=["salesforce", "hubspot"],
            agents=["revops_pilot"],
            llm_model="gemini-2.0-flash-exp",
            force_refresh=False,
            tenant_id="tenant_123"
        )
        assert len(req.sources) == 2
        assert req.sources[0] == "salesforce"
        assert req.agents[0] == "revops_pilot"
        assert req.llm_model == "gemini-2.0-flash-exp"
        assert req.force_refresh is False
    
    def test_connect_request_defaults(self):
        """Test ConnectRequest with minimal required fields"""
        req = ConnectRequest(sources=["salesforce"])
        assert req.sources == ["salesforce"]
        assert req.agents == []  # Default empty list
        assert req.llm_model == "gemini-2.0-flash-exp"  # Default model
        assert req.force_refresh is False  # Default false
        assert req.tenant_id == "default"  # Default tenant
    
    def test_connect_request_validation(self):
        """Test ConnectRequest field validation"""
        # Empty sources list should fail
        with pytest.raises(ValidationError) as exc_info:
            ConnectRequest(sources=[])
        assert "at least 1 item" in str(exc_info.value).lower()
        
        # Too many sources should fail
        with pytest.raises(ValidationError) as exc_info:
            ConnectRequest(sources=["source"] * 101)
        assert "at most 100 items" in str(exc_info.value).lower()
        
        # Empty string in sources should fail
        with pytest.raises(ValidationError) as exc_info:
            ConnectRequest(sources=[""])
        assert "at least 1 character" in str(exc_info.value).lower()
    
    def test_connect_response_valid(self):
        """Test valid ConnectResponse creation"""
        resp = ConnectResponse(
            status="success",
            connected_sources=["salesforce", "hubspot"],
            graph_nodes=25,
            graph_edges=30,
            confidence=0.85,
            message="Successfully connected 2 sources",
            tenant_id="tenant_123"
        )
        assert resp.status == "success"
        assert len(resp.connected_sources) == 2
        assert resp.graph_nodes == 25
        assert resp.graph_edges == 30
        assert resp.confidence == 0.85
    
    def test_connect_response_validation(self):
        """Test ConnectResponse field validation"""
        # Invalid status value
        with pytest.raises(ValidationError):
            ConnectResponse(
                status="invalid",  # Must be success/partial/failed
                connected_sources=[],
                message="Test"
            )
        
        # Invalid confidence range
        with pytest.raises(ValidationError):
            ConnectResponse(
                status="success",
                connected_sources=["test"],
                confidence=1.5,  # Must be 0.0-1.0
                message="Test"
            )
        
        # Negative node count
        with pytest.raises(ValidationError):
            ConnectResponse(
                status="success",
                connected_sources=["test"],
                graph_nodes=-1,  # Must be >= 0
                message="Test"
            )


class TestStateDTOs:
    """Tests for /dcl/state endpoint DTOs"""
    
    def test_graph_node_creation(self):
        """Test GraphNode DTO creation"""
        node = GraphNode(
            id="node_1",
            label="Account",
            type="entity",
            metadata={"source": "salesforce"}
        )
        assert node.id == "node_1"
        assert node.label == "Account"
        assert node.type == "entity"
        assert node.metadata["source"] == "salesforce"
    
    def test_graph_edge_creation(self):
        """Test GraphEdge DTO creation"""
        edge = GraphEdge(
            source="node_1",
            target="node_2",
            label="has_many",
            weight=0.9
        )
        assert edge.source == "node_1"
        assert edge.target == "node_2"
        assert edge.label == "has_many"
        assert edge.weight == 0.9
    
    def test_graph_state_creation(self):
        """Test GraphState DTO creation"""
        nodes = [
            GraphNode(id="n1", label="Node 1", type="entity"),
            GraphNode(id="n2", label="Node 2", type="source")
        ]
        edges = [
            GraphEdge(source="n1", target="n2", label="connected")
        ]
        
        graph = GraphState(
            nodes=nodes,
            edges=edges,
            confidence=0.75,
            last_updated=datetime.now()
        )
        assert len(graph.nodes) == 2
        assert len(graph.edges) == 1
        assert graph.confidence == 0.75
        assert graph.last_updated is not None
    
    def test_state_response_creation(self):
        """Test StateResponse DTO creation"""
        graph = GraphState(
            nodes=[],
            edges=[],
            confidence=0.8
        )
        
        resp = StateResponse(
            tenant_id="tenant_123",
            graph=graph,
            sources_added=["salesforce", "hubspot"],
            entity_sources={"account": ["salesforce"], "contact": ["hubspot"]},
            selected_agents=["revops_pilot"],
            metadata={"llm_calls": 10}
        )
        assert resp.tenant_id == "tenant_123"
        assert len(resp.sources_added) == 2
        assert "account" in resp.entity_sources
        assert resp.metadata["llm_calls"] == 10


class TestToggleDTOs:
    """Tests for /dcl/toggle endpoint DTOs"""
    
    def test_toggle_request_creation(self):
        """Test ToggleRequest DTO creation"""
        req = ToggleRequest(
            feature=FeatureFlag.DEV_MODE,
            value=True,
            tenant_id="tenant_123"
        )
        assert req.feature == FeatureFlag.DEV_MODE
        assert req.value is True
        assert req.tenant_id == "tenant_123"
    
    def test_toggle_request_enum_validation(self):
        """Test ToggleRequest validates feature enum"""
        # Valid enum value works
        req = ToggleRequest(feature=FeatureFlag.AAM_MODE)
        assert req.feature == FeatureFlag.AAM_MODE
        
        # Invalid enum value fails
        with pytest.raises(ValidationError):
            ToggleRequest(feature="invalid_feature")
    
    def test_toggle_response_creation(self):
        """Test ToggleResponse DTO creation"""
        resp = ToggleResponse(
            feature="dev_mode",
            previous_value=False,
            current_value=True,
            message="Dev mode enabled",
            tenant_id="tenant_123"
        )
        assert resp.feature == "dev_mode"
        assert resp.previous_value is False
        assert resp.current_value is True
        assert resp.message == "Dev mode enabled"


class TestSourceSchemaDTOs:
    """Tests for /dcl/source-schemas endpoint DTOs"""
    
    def test_source_schema_creation(self):
        """Test SourceSchema DTO creation"""
        schema = SourceSchema(
            source="salesforce",
            tables={
                "Account": ["Id", "Name", "Type"],
                "Opportunity": ["Id", "Amount", "Stage"]
            },
            row_counts={"Account": 1000, "Opportunity": 500},
            last_synced=datetime.now()
        )
        assert schema.source == "salesforce"
        assert "Account" in schema.tables
        assert len(schema.tables["Account"]) == 3
        assert schema.row_counts["Account"] == 1000
    
    def test_source_schemas_response_creation(self):
        """Test SourceSchemasResponse DTO creation"""
        schemas = [
            SourceSchema(
                source="salesforce",
                tables={"Account": ["Id", "Name"]}
            ),
            SourceSchema(
                source="hubspot",
                tables={"Contact": ["email", "name"]}
            )
        ]
        
        resp = SourceSchemasResponse(
            schemas=schemas,
            total_sources=2,
            total_tables=2,
            tenant_id="tenant_123"
        )
        assert len(resp.schemas) == 2
        assert resp.total_sources == 2
        assert resp.total_tables == 2


class TestViewsDTOs:
    """Tests for /api/v1/dcl/views endpoint DTOs"""
    
    def test_views_request_creation(self):
        """Test ViewsRequest DTO creation"""
        req = ViewsRequest(
            entity_types=["account", "opportunity"],
            include_metadata=True,
            limit=100,
            offset=0,
            tenant_id="tenant_123"
        )
        assert len(req.entity_types) == 2
        assert req.include_metadata is True
        assert req.limit == 100
        assert req.offset == 0
    
    def test_views_request_validation(self):
        """Test ViewsRequest field validation"""
        # Valid limit
        req1 = ViewsRequest(limit=5000)
        assert req1.limit == 5000
        
        # Invalid limit (too high)
        with pytest.raises(ValidationError):
            ViewsRequest(limit=10001)
        
        # Invalid limit (too low)
        with pytest.raises(ValidationError):
            ViewsRequest(limit=0)
        
        # Invalid offset (negative)
        with pytest.raises(ValidationError):
            ViewsRequest(offset=-1)
    
    def test_entity_view_creation(self):
        """Test EntityView DTO creation"""
        view = EntityView(
            entity_type="account",
            unified_id="acc_unified_123",
            source_ids={"salesforce": "001D000000AbcDe", "hubspot": "12345"},
            attributes={"name": "Acme Corp", "revenue": 1000000},
            confidence=0.95,
            last_updated=datetime.now()
        )
        assert view.entity_type == "account"
        assert view.unified_id == "acc_unified_123"
        assert view.source_ids["salesforce"] == "001D000000AbcDe"
        assert view.attributes["revenue"] == 1000000
        assert view.confidence == 0.95
    
    def test_views_response_creation(self):
        """Test ViewsResponse DTO creation"""
        views = [
            EntityView(
                entity_type="account",
                unified_id="acc_1",
                source_ids={"salesforce": "001"},
                attributes={"name": "Test"}
            )
        ]
        
        resp = ViewsResponse(
            views=views,
            total_entities=100,
            has_more=True,
            metadata={"processing_time_ms": 250},
            tenant_id="tenant_123"
        )
        assert len(resp.views) == 1
        assert resp.total_entities == 100
        assert resp.has_more is True
        assert resp.metadata["processing_time_ms"] == 250


class TestUnifyDTOs:
    """Tests for /api/v1/dcl/unify endpoint DTOs"""
    
    def test_unify_request_creation(self):
        """Test UnifyRequest DTO creation"""
        req = UnifyRequest(
            entity_type="contact",
            matching_strategy="email",
            sources=["salesforce", "hubspot"],
            confidence_threshold=0.7,
            dry_run=False,
            tenant_id="tenant_123"
        )
        assert req.entity_type == "contact"
        assert req.matching_strategy == "email"
        assert len(req.sources) == 2
        assert req.confidence_threshold == 0.7
        assert req.dry_run is False
    
    def test_unify_request_validation(self):
        """Test UnifyRequest field validation"""
        # Valid matching strategy
        req1 = UnifyRequest(entity_type="contact", matching_strategy="fuzzy")
        assert req1.matching_strategy == "fuzzy"
        
        # Invalid matching strategy
        with pytest.raises(ValidationError):
            UnifyRequest(entity_type="contact", matching_strategy="invalid")
        
        # Invalid confidence threshold
        with pytest.raises(ValidationError):
            UnifyRequest(entity_type="contact", confidence_threshold=1.5)
        
        # Empty entity type
        with pytest.raises(ValidationError):
            UnifyRequest(entity_type="")
    
    def test_unification_match_creation(self):
        """Test UnificationMatch DTO creation"""
        match = UnificationMatch(
            unified_id="contact_unified_123",
            source_entities=[
                {"source": "salesforce", "id": "003XX000004TMM2"},
                {"source": "hubspot", "id": "contact-456"}
            ],
            match_confidence=0.95,
            match_reason="Email match: john@example.com"
        )
        assert match.unified_id == "contact_unified_123"
        assert len(match.source_entities) == 2
        assert match.match_confidence == 0.95
        assert "Email match" in match.match_reason
    
    def test_unify_response_creation(self):
        """Test UnifyResponse DTO creation"""
        matches = [
            UnificationMatch(
                unified_id="contact_1",
                source_entities=[{"source": "sf", "id": "001"}],
                match_confidence=0.9,
                match_reason="Email match"
            )
        ]
        
        resp = UnifyResponse(
            status="success",
            entity_type="contact",
            total_processed=500,
            total_unified=450,
            total_duplicates=50,
            matches=matches,
            execution_time_ms=1250.5,
            tenant_id="tenant_123"
        )
        assert resp.status == "success"
        assert resp.entity_type == "contact"
        assert resp.total_processed == 500
        assert resp.total_unified == 450
        assert resp.total_duplicates == 50
        assert len(resp.matches) == 1
        assert resp.execution_time_ms == 1250.5


class TestBackwardCompatibility:
    """Tests for backward compatibility with existing API contracts"""
    
    def test_state_response_backward_compatible(self):
        """Test StateResponse maintains backward compatibility with metadata field"""
        graph = GraphState(nodes=[], edges=[])
        
        # Old clients might expect these fields in metadata
        legacy_metadata = {
            "events": ["event1", "event2"],
            "llm": {"calls": 10, "tokens": 1000},
            "dev_mode": True,
            "auth_enabled": True
        }
        
        resp = StateResponse(
            graph=graph,
            sources_added=[],
            entity_sources={},
            metadata=legacy_metadata
        )
        
        # Verify legacy fields are preserved in metadata
        assert resp.metadata["events"] == ["event1", "event2"]
        assert resp.metadata["llm"]["calls"] == 10
        assert resp.metadata["dev_mode"] is True
    
    def test_optional_fields_allow_none(self):
        """Test that optional fields can be None for backward compatibility"""
        # ConnectRequest with minimal fields
        req1 = ConnectRequest(sources=["salesforce"])
        assert req1.agents == []  # Default, not None
        assert req1.llm_model == "gemini-2.0-flash-exp"  # Default
        
        # StateResponse with minimal fields
        resp1 = StateResponse(
            graph=GraphState(nodes=[], edges=[]),
            sources_added=[],
            entity_sources={}
        )
        assert resp1.selected_agents == []  # Default empty list
        assert resp1.metadata is None  # Optional, can be None
        
        # ViewsRequest with all defaults
        req2 = ViewsRequest()
        assert req2.entity_types is None  # Optional
        assert req2.include_metadata is True  # Default
        assert req2.limit == 100  # Default


class TestDTOSerialization:
    """Tests for DTO JSON serialization/deserialization"""
    
    def test_connect_request_json_roundtrip(self):
        """Test ConnectRequest can be serialized and deserialized"""
        req = ConnectRequest(
            sources=["salesforce", "hubspot"],
            agents=["revops_pilot"],
            tenant_id="tenant_123"
        )
        
        # Serialize to JSON
        json_str = req.model_dump_json()
        assert "salesforce" in json_str
        assert "tenant_123" in json_str
        
        # Deserialize from JSON
        req2 = ConnectRequest.model_validate_json(json_str)
        assert req2.sources == req.sources
        assert req2.tenant_id == req.tenant_id
    
    def test_state_response_json_serialization(self):
        """Test StateResponse with complex nested structures serializes correctly"""
        graph = GraphState(
            nodes=[
                GraphNode(id="n1", label="Node 1", type="entity"),
                GraphNode(id="n2", label="Node 2", type="source")
            ],
            edges=[
                GraphEdge(source="n1", target="n2")
            ],
            confidence=0.85,
            last_updated=datetime.now()
        )
        
        resp = StateResponse(
            tenant_id="tenant_123",
            graph=graph,
            sources_added=["salesforce"],
            entity_sources={"account": ["salesforce"]},
            metadata={"complex": {"nested": {"data": [1, 2, 3]}}}
        )
        
        # Should serialize without errors
        json_dict = resp.model_dump()
        assert json_dict["tenant_id"] == "tenant_123"
        assert len(json_dict["graph"]["nodes"]) == 2
        assert json_dict["metadata"]["complex"]["nested"]["data"] == [1, 2, 3]
        
        # Should handle datetime serialization
        json_str = resp.model_dump_json()
        assert "last_updated" in json_str


class TestFieldConstraints:
    """Tests for field constraint validation"""
    
    def test_array_size_limits(self):
        """Test array size constraints are enforced"""
        # Valid: up to 100 sources
        req1 = ConnectRequest(sources=["source"] * 100)
        assert len(req1.sources) == 100
        
        # Invalid: more than 100 sources
        with pytest.raises(ValidationError) as exc_info:
            ConnectRequest(sources=["source"] * 101)
        assert "at most 100 items" in str(exc_info.value).lower()
        
        # Valid: up to 50 agents
        req2 = ConnectRequest(sources=["sf"], agents=["agent"] * 50)
        assert len(req2.agents) == 50
        
        # Invalid: more than 50 agents
        with pytest.raises(ValidationError):
            ConnectRequest(sources=["sf"], agents=["agent"] * 51)
        
        # Valid: up to 20 entity types
        req3 = ViewsRequest(entity_types=["entity"] * 20)
        assert len(req3.entity_types) == 20
        
        # Invalid: more than 20 entity types
        with pytest.raises(ValidationError):
            ViewsRequest(entity_types=["entity"] * 21)
    
    def test_string_length_constraints(self):
        """Test string length constraints are enforced"""
        # Valid string lengths
        req = UnifyRequest(
            entity_type="a" * 100,  # Max length
            matching_strategy="email"
        )
        assert len(req.entity_type) == 100
        
        # Invalid: too long
        with pytest.raises(ValidationError):
            UnifyRequest(
                entity_type="a" * 101,  # Too long
                matching_strategy="email"
            )
        
        # Invalid: too short
        with pytest.raises(ValidationError):
            UnifyRequest(
                entity_type="",  # Too short (min 1)
                matching_strategy="email"
            )
    
    def test_numeric_constraints(self):
        """Test numeric field constraints"""
        # Valid confidence values (0.0 - 1.0)
        resp1 = ConnectResponse(
            status="success",
            connected_sources=["sf"],
            confidence=0.0,  # Min value
            message="Test"
        )
        assert resp1.confidence == 0.0
        
        resp2 = ConnectResponse(
            status="success",
            connected_sources=["sf"],
            confidence=1.0,  # Max value
            message="Test"
        )
        assert resp2.confidence == 1.0
        
        # Invalid confidence values
        with pytest.raises(ValidationError):
            ConnectResponse(
                status="success",
                connected_sources=["sf"],
                confidence=-0.1,  # Too low
                message="Test"
            )
        
        with pytest.raises(ValidationError):
            ConnectResponse(
                status="success",
                connected_sources=["sf"],
                confidence=1.1,  # Too high
                message="Test"
            )