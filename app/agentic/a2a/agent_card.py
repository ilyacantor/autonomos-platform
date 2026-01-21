"""
Agent Card Schema

Implementation of the Agent Card specification for agent discoverability.
Based on Google's A2A (Agent-to-Agent) protocol specification.

Agent Cards provide:
- Machine-readable agent identity and capabilities
- Service endpoints for interaction
- Authentication requirements
- Supported protocols and message types
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


class AuthScheme(str, Enum):
    """Authentication schemes supported by agents."""
    NONE = "none"
    API_KEY = "api_key"
    BEARER = "bearer"
    OAUTH2 = "oauth2"
    MTLS = "mtls"
    CUSTOM = "custom"


class ProtocolVersion(str, Enum):
    """A2A protocol versions."""
    V1 = "1.0"
    V1_1 = "1.1"


@dataclass
class AgentEndpoint:
    """
    An endpoint where the agent can be reached.

    Endpoints define how to interact with the agent:
    - HTTP REST endpoints
    - WebSocket connections
    - Message queue addresses
    """
    url: str
    protocol: str = "https"  # https, wss, grpc, amqp
    version: str = "v1"

    # Authentication
    auth_scheme: AuthScheme = AuthScheme.BEARER
    auth_config: Dict[str, Any] = field(default_factory=dict)

    # Capabilities at this endpoint
    supported_operations: List[str] = field(default_factory=lambda: [
        "execute", "query", "delegate", "status"
    ])

    # Rate limits
    rate_limit_rpm: Optional[int] = None  # Requests per minute

    # Health check
    health_check_path: Optional[str] = "/health"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "protocol": self.protocol,
            "version": self.version,
            "auth_scheme": self.auth_scheme.value,
            "auth_config": self.auth_config,
            "supported_operations": self.supported_operations,
            "rate_limit_rpm": self.rate_limit_rpm,
            "health_check_path": self.health_check_path,
        }


@dataclass
class AgentCapability:
    """
    A capability that an agent can perform.

    Capabilities define what the agent can do:
    - Tools it can use
    - Types of queries it can answer
    - Actions it can perform
    """
    id: str
    name: str
    description: str

    # Capability type
    capability_type: str = "tool"  # tool, query, action, workflow

    # Input/output schemas (JSON Schema format)
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)

    # Requirements
    requires_approval: bool = False
    requires_context: bool = False

    # Limitations
    max_tokens: Optional[int] = None
    timeout_seconds: Optional[int] = None

    # Tags for discovery
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "capability_type": self.capability_type,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "requires_approval": self.requires_approval,
            "requires_context": self.requires_context,
            "max_tokens": self.max_tokens,
            "timeout_seconds": self.timeout_seconds,
            "tags": self.tags,
        }


@dataclass
class AgentCard:
    """
    Agent Card - The complete identity and capability description of an agent.

    This is the machine-readable document that allows:
    - Other agents to discover this agent
    - Clients to understand what the agent can do
    - Systems to route requests appropriately

    Follows the A2A specification for interoperability.
    """
    # Identity
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    version: str = "1.0.0"

    # Organization
    tenant_id: Optional[UUID] = None
    organization: Optional[str] = None
    owner: Optional[str] = None

    # Agent type and role
    agent_type: str = "general"  # general, specialist, orchestrator, worker
    role: str = "assistant"  # assistant, executor, analyst, coordinator

    # Endpoints
    endpoints: List[AgentEndpoint] = field(default_factory=list)
    primary_endpoint: Optional[str] = None

    # Capabilities
    capabilities: List[AgentCapability] = field(default_factory=list)

    # Supported protocols
    protocol_version: ProtocolVersion = ProtocolVersion.V1_1
    supported_message_types: List[str] = field(default_factory=lambda: [
        "execute", "query", "delegate", "cancel", "status"
    ])

    # Trust and certification
    certification_id: Optional[str] = None
    certification_status: Optional[str] = None
    trust_level: int = 0  # 0-100

    # Limitations
    max_concurrent_tasks: int = 10
    max_context_tokens: int = 100000
    supported_languages: List[str] = field(default_factory=lambda: ["en"])

    # Collaboration
    can_delegate: bool = True
    can_accept_delegation: bool = True
    preferred_collaborators: List[str] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Well-known URL path
    well_known_path: str = "/.well-known/agent.json"

    def get_primary_endpoint(self) -> Optional[AgentEndpoint]:
        """Get the primary endpoint for this agent."""
        if self.primary_endpoint:
            for ep in self.endpoints:
                if ep.url == self.primary_endpoint:
                    return ep
        return self.endpoints[0] if self.endpoints else None

    def get_capability(self, capability_id: str) -> Optional[AgentCapability]:
        """Get a specific capability by ID."""
        for cap in self.capabilities:
            if cap.id == capability_id:
                return cap
        return None

    def supports_operation(self, operation: str) -> bool:
        """Check if any endpoint supports an operation."""
        for ep in self.endpoints:
            if operation in ep.supported_operations:
                return True
        return False

    def has_capability_tag(self, tag: str) -> bool:
        """Check if any capability has a specific tag."""
        for cap in self.capabilities:
            if tag in cap.tags:
                return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            # Identity
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,

            # Organization
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "organization": self.organization,
            "owner": self.owner,

            # Type and role
            "agent_type": self.agent_type,
            "role": self.role,

            # Endpoints
            "endpoints": [ep.to_dict() for ep in self.endpoints],
            "primary_endpoint": self.primary_endpoint,

            # Capabilities
            "capabilities": [cap.to_dict() for cap in self.capabilities],

            # Protocol
            "protocol_version": self.protocol_version.value,
            "supported_message_types": self.supported_message_types,

            # Trust
            "certification_id": self.certification_id,
            "certification_status": self.certification_status,
            "trust_level": self.trust_level,

            # Limitations
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "max_context_tokens": self.max_context_tokens,
            "supported_languages": self.supported_languages,

            # Collaboration
            "can_delegate": self.can_delegate,
            "can_accept_delegation": self.can_accept_delegation,
            "preferred_collaborators": self.preferred_collaborators,

            # Metadata
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "tags": self.tags,
            "metadata": self.metadata,

            # Well-known
            "well_known_path": self.well_known_path,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentCard":
        """Create an AgentCard from a dictionary."""
        # Parse endpoints
        endpoints = [
            AgentEndpoint(
                url=ep["url"],
                protocol=ep.get("protocol", "https"),
                version=ep.get("version", "v1"),
                auth_scheme=AuthScheme(ep.get("auth_scheme", "bearer")),
                auth_config=ep.get("auth_config", {}),
                supported_operations=ep.get("supported_operations", []),
                rate_limit_rpm=ep.get("rate_limit_rpm"),
                health_check_path=ep.get("health_check_path"),
            )
            for ep in data.get("endpoints", [])
        ]

        # Parse capabilities
        capabilities = [
            AgentCapability(
                id=cap["id"],
                name=cap["name"],
                description=cap["description"],
                capability_type=cap.get("capability_type", "tool"),
                input_schema=cap.get("input_schema", {}),
                output_schema=cap.get("output_schema", {}),
                requires_approval=cap.get("requires_approval", False),
                requires_context=cap.get("requires_context", False),
                max_tokens=cap.get("max_tokens"),
                timeout_seconds=cap.get("timeout_seconds"),
                tags=cap.get("tags", []),
            )
            for cap in data.get("capabilities", [])
        ]

        return cls(
            id=data.get("id", str(uuid4())),
            name=data.get("name", ""),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            tenant_id=UUID(data["tenant_id"]) if data.get("tenant_id") else None,
            organization=data.get("organization"),
            owner=data.get("owner"),
            agent_type=data.get("agent_type", "general"),
            role=data.get("role", "assistant"),
            endpoints=endpoints,
            primary_endpoint=data.get("primary_endpoint"),
            capabilities=capabilities,
            protocol_version=ProtocolVersion(data.get("protocol_version", "1.1")),
            supported_message_types=data.get("supported_message_types", []),
            certification_id=data.get("certification_id"),
            certification_status=data.get("certification_status"),
            trust_level=data.get("trust_level", 0),
            max_concurrent_tasks=data.get("max_concurrent_tasks", 10),
            max_context_tokens=data.get("max_context_tokens", 100000),
            supported_languages=data.get("supported_languages", ["en"]),
            can_delegate=data.get("can_delegate", True),
            can_accept_delegation=data.get("can_accept_delegation", True),
            preferred_collaborators=data.get("preferred_collaborators", []),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )


def create_agent_card(
    agent_id: UUID,
    name: str,
    description: str,
    tenant_id: UUID,
    base_url: str,
    capabilities: Optional[List[AgentCapability]] = None,
    agent_type: str = "general",
    certification_id: Optional[str] = None,
    trust_level: int = 50,
) -> AgentCard:
    """
    Factory function to create an Agent Card for an agent.

    Args:
        agent_id: Unique agent identifier
        name: Human-readable agent name
        description: What the agent does
        tenant_id: Owning tenant
        base_url: Base URL for agent endpoints
        capabilities: List of capabilities (auto-generated if not provided)
        agent_type: Type of agent
        certification_id: Certification ID if certified
        trust_level: Trust level (0-100)

    Returns:
        Configured AgentCard
    """
    # Create default endpoint
    endpoint = AgentEndpoint(
        url=f"{base_url}/api/v1/agents/{agent_id}",
        protocol="https",
        version="v1",
        auth_scheme=AuthScheme.BEARER,
        supported_operations=["execute", "query", "delegate", "status", "cancel"],
        health_check_path=f"/api/v1/agents/{agent_id}/health",
    )

    # Create default capabilities if not provided
    if capabilities is None:
        capabilities = [
            AgentCapability(
                id="execute",
                name="Execute Task",
                description="Execute a task with natural language input",
                capability_type="action",
                input_schema={
                    "type": "object",
                    "properties": {
                        "input": {"type": "string"},
                        "context": {"type": "object"},
                    },
                    "required": ["input"],
                },
                tags=["execute", "task"],
            ),
            AgentCapability(
                id="query",
                name="Query",
                description="Answer questions using available tools",
                capability_type="query",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                    },
                    "required": ["query"],
                },
                tags=["query", "qa"],
            ),
        ]

    return AgentCard(
        id=str(agent_id),
        name=name,
        description=description,
        tenant_id=tenant_id,
        agent_type=agent_type,
        endpoints=[endpoint],
        primary_endpoint=endpoint.url,
        capabilities=capabilities,
        certification_id=certification_id,
        certification_status="certified" if certification_id else None,
        trust_level=trust_level,
        can_delegate=True,
        can_accept_delegation=True,
    )
