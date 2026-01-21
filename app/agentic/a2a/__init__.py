"""
A2A (Agent-to-Agent) Protocol

Enterprise agent collaboration system based on Google's A2A specification:
- Agent Card for discoverability
- Discovery service for finding agents
- Delegation protocol for task handoff
- Context sharing between agents
"""

from .agent_card import (
    AgentCard,
    AgentCapability,
    AgentEndpoint,
    AuthScheme,
    create_agent_card,
)
from .discovery import (
    AgentDiscovery,
    DiscoveryFilter,
    get_agent_discovery,
)
from .delegation import (
    DelegationRequest,
    DelegationResponse,
    DelegationStatus,
    DelegationManager,
    get_delegation_manager,
)
from .protocol import (
    A2AMessage,
    A2AMessageType,
    A2AProtocol,
    get_a2a_protocol,
)

__all__ = [
    # Agent Card
    "AgentCard",
    "AgentCapability",
    "AgentEndpoint",
    "AuthScheme",
    "create_agent_card",
    # Discovery
    "AgentDiscovery",
    "DiscoveryFilter",
    "get_agent_discovery",
    # Delegation
    "DelegationRequest",
    "DelegationResponse",
    "DelegationStatus",
    "DelegationManager",
    "get_delegation_manager",
    # Protocol
    "A2AMessage",
    "A2AMessageType",
    "A2AProtocol",
    "get_a2a_protocol",
]
