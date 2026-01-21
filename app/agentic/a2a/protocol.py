"""
A2A Protocol Implementation

Inter-agent communication protocol:
- Message types and formats
- Request/response handling
- Context sharing
- Error handling
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID, uuid4

from .agent_card import AgentCard
from .discovery import AgentDiscovery, get_agent_discovery
from .delegation import DelegationManager, DelegationRequest, DelegationResponse, get_delegation_manager

logger = logging.getLogger(__name__)


class A2AMessageType(str, Enum):
    """Types of A2A protocol messages."""
    # Discovery
    DISCOVER = "discover"
    DISCOVER_RESPONSE = "discover_response"

    # Capability queries
    CAPABILITY_QUERY = "capability_query"
    CAPABILITY_RESPONSE = "capability_response"

    # Task execution
    EXECUTE = "execute"
    EXECUTE_RESPONSE = "execute_response"

    # Delegation
    DELEGATE = "delegate"
    DELEGATE_ACCEPT = "delegate_accept"
    DELEGATE_REJECT = "delegate_reject"
    DELEGATE_RESULT = "delegate_result"

    # Status
    STATUS_QUERY = "status_query"
    STATUS_RESPONSE = "status_response"

    # Control
    CANCEL = "cancel"
    CANCEL_ACK = "cancel_ack"

    # Context
    CONTEXT_SHARE = "context_share"
    CONTEXT_UPDATE = "context_update"

    # Health
    PING = "ping"
    PONG = "pong"

    # Error
    ERROR = "error"


@dataclass
class A2AMessage:
    """
    A2A Protocol Message.

    The standard message format for agent-to-agent communication.
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    type: A2AMessageType = A2AMessageType.EXECUTE

    # Routing
    from_agent: str = ""
    to_agent: str = ""

    # Correlation
    correlation_id: Optional[str] = None  # Links request/response pairs
    in_reply_to: Optional[str] = None  # ID of message being replied to

    # Payload
    payload: Dict[str, Any] = field(default_factory=dict)

    # Timing
    timestamp: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None

    # Metadata
    protocol_version: str = "1.1"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "correlation_id": self.correlation_id,
            "in_reply_to": self.in_reply_to,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "protocol_version": self.protocol_version,
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "A2AMessage":
        return cls(
            id=data.get("id", str(uuid4())),
            type=A2AMessageType(data.get("type", "execute")),
            from_agent=data.get("from_agent", ""),
            to_agent=data.get("to_agent", ""),
            correlation_id=data.get("correlation_id"),
            in_reply_to=data.get("in_reply_to"),
            payload=data.get("payload", {}),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.utcnow(),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            protocol_version=data.get("protocol_version", "1.1"),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "A2AMessage":
        return cls.from_dict(json.loads(json_str))

    def create_reply(
        self,
        message_type: A2AMessageType,
        payload: Dict[str, Any],
    ) -> "A2AMessage":
        """Create a reply message."""
        return A2AMessage(
            type=message_type,
            from_agent=self.to_agent,
            to_agent=self.from_agent,
            correlation_id=self.correlation_id or self.id,
            in_reply_to=self.id,
            payload=payload,
        )

    def create_error_reply(self, error: str, code: str = "ERROR") -> "A2AMessage":
        """Create an error reply message."""
        return self.create_reply(
            A2AMessageType.ERROR,
            {"error": error, "code": code},
        )


class A2AProtocol:
    """
    A2A Protocol Handler.

    Manages inter-agent communication:
    - Message routing
    - Request/response correlation
    - Protocol enforcement
    """

    def __init__(
        self,
        discovery: Optional[AgentDiscovery] = None,
        delegation: Optional[DelegationManager] = None,
    ):
        """Initialize the protocol handler."""
        self.discovery = discovery or get_agent_discovery()
        self.delegation = delegation or get_delegation_manager()

        # Message handlers by type
        self._handlers: Dict[A2AMessageType, List[Callable]] = {
            t: [] for t in A2AMessageType
        }

        # Pending requests (correlation_id -> callback)
        self._pending_requests: Dict[str, asyncio.Future] = {}

        # Message queue per agent
        self._message_queues: Dict[str, asyncio.Queue] = {}

        # Register default handlers
        self._register_default_handlers()

    def _register_default_handlers(self):
        """Register built-in message handlers."""
        self.on_message(A2AMessageType.PING, self._handle_ping)
        self.on_message(A2AMessageType.DISCOVER, self._handle_discover)
        self.on_message(A2AMessageType.CAPABILITY_QUERY, self._handle_capability_query)
        self.on_message(A2AMessageType.DELEGATE, self._handle_delegate)
        self.on_message(A2AMessageType.STATUS_QUERY, self._handle_status_query)

    def on_message(
        self,
        message_type: A2AMessageType,
        handler: Callable[[A2AMessage], Optional[A2AMessage]],
    ) -> None:
        """Register a handler for a message type."""
        self._handlers[message_type].append(handler)

    async def send(self, message: A2AMessage) -> Optional[A2AMessage]:
        """
        Send a message to another agent.

        Args:
            message: Message to send

        Returns:
            Response message if synchronous, None for async
        """
        # Validate message
        if not message.to_agent:
            raise ValueError("Message must have a to_agent")

        # Check if target agent exists
        target = self.discovery.get(message.to_agent)
        if not target:
            raise ValueError(f"Target agent {message.to_agent} not found")

        logger.debug(
            f"Sending {message.type.value} from {message.from_agent} to {message.to_agent}"
        )

        # For request types, set up response handling
        is_request = message.type in (
            A2AMessageType.EXECUTE,
            A2AMessageType.DELEGATE,
            A2AMessageType.DISCOVER,
            A2AMessageType.CAPABILITY_QUERY,
            A2AMessageType.STATUS_QUERY,
        )

        if is_request and not message.correlation_id:
            message.correlation_id = message.id

        # Queue message for target agent
        await self._queue_message(message.to_agent, message)

        # If synchronous request, wait for response
        if is_request:
            return await self._wait_for_response(message.correlation_id)

        return None

    async def _queue_message(self, agent_id: str, message: A2AMessage) -> None:
        """Queue a message for an agent."""
        if agent_id not in self._message_queues:
            self._message_queues[agent_id] = asyncio.Queue()

        await self._message_queues[agent_id].put(message)

    async def _wait_for_response(
        self,
        correlation_id: str,
        timeout: float = 30.0,
    ) -> Optional[A2AMessage]:
        """Wait for a response to a request."""
        future = asyncio.Future()
        self._pending_requests[correlation_id] = future

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"Request {correlation_id} timed out")
            return None
        finally:
            self._pending_requests.pop(correlation_id, None)

    async def receive(self, agent_id: str, timeout: float = 1.0) -> Optional[A2AMessage]:
        """
        Receive the next message for an agent.

        Args:
            agent_id: Agent receiving messages
            timeout: How long to wait for a message

        Returns:
            Next message or None if timeout
        """
        if agent_id not in self._message_queues:
            self._message_queues[agent_id] = asyncio.Queue()

        try:
            message = await asyncio.wait_for(
                self._message_queues[agent_id].get(),
                timeout=timeout,
            )
            return message
        except asyncio.TimeoutError:
            return None

    async def process(self, message: A2AMessage) -> Optional[A2AMessage]:
        """
        Process a received message.

        Calls registered handlers and returns any response.
        """
        logger.debug(f"Processing {message.type.value} message {message.id}")

        # Check if this is a response to a pending request
        if message.correlation_id and message.correlation_id in self._pending_requests:
            future = self._pending_requests[message.correlation_id]
            if not future.done():
                future.set_result(message)
            return None

        # Call registered handlers
        handlers = self._handlers.get(message.type, [])
        response = None

        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(message)
                else:
                    result = handler(message)

                if result is not None:
                    response = result
            except Exception as e:
                logger.error(f"Handler error for {message.type.value}: {e}")
                response = message.create_error_reply(str(e))

        return response

    async def _handle_ping(self, message: A2AMessage) -> A2AMessage:
        """Handle ping message."""
        return message.create_reply(
            A2AMessageType.PONG,
            {"timestamp": datetime.utcnow().isoformat()},
        )

    async def _handle_discover(self, message: A2AMessage) -> A2AMessage:
        """Handle discovery message."""
        from .discovery import DiscoveryFilter

        filter_data = message.payload.get("filter", {})
        filter = DiscoveryFilter(
            capability_ids=filter_data.get("capability_ids"),
            capability_tags=filter_data.get("capability_tags"),
            agent_types=filter_data.get("agent_types"),
            min_trust_level=filter_data.get("min_trust_level", 0),
            limit=filter_data.get("limit", 10),
        )

        result = self.discovery.discover(filter)

        return message.create_reply(
            A2AMessageType.DISCOVER_RESPONSE,
            {
                "agents": [a.to_dict() for a in result.agents],
                "total": result.total,
                "has_more": result.has_more,
            },
        )

    async def _handle_capability_query(self, message: A2AMessage) -> A2AMessage:
        """Handle capability query message."""
        agent_id = message.payload.get("agent_id", message.to_agent)
        capability_id = message.payload.get("capability_id")

        agent = self.discovery.get(agent_id)
        if not agent:
            return message.create_error_reply(f"Agent {agent_id} not found", "NOT_FOUND")

        if capability_id:
            capability = agent.get_capability(capability_id)
            if not capability:
                return message.create_error_reply(
                    f"Capability {capability_id} not found",
                    "NOT_FOUND",
                )
            capabilities = [capability.to_dict()]
        else:
            capabilities = [c.to_dict() for c in agent.capabilities]

        return message.create_reply(
            A2AMessageType.CAPABILITY_RESPONSE,
            {"capabilities": capabilities},
        )

    async def _handle_delegate(self, message: A2AMessage) -> A2AMessage:
        """Handle delegation request message."""
        from .delegation import DelegationContext

        payload = message.payload
        context_data = payload.get("context", {})

        context = DelegationContext(
            original_input=context_data.get("original_input", payload.get("input", "")),
            original_context=context_data.get("original_context", {}),
            delegation_reason=context_data.get("delegation_reason"),
            delegated_capability=context_data.get("delegated_capability"),
            max_steps=context_data.get("max_steps"),
            max_cost_usd=context_data.get("max_cost_usd"),
            timeout_seconds=context_data.get("timeout_seconds", 300),
            delegation_chain=context_data.get("delegation_chain", []),
            shared_state=context_data.get("shared_state", {}),
        )

        try:
            request = await self.delegation.delegate(
                delegator_id=message.from_agent,
                task_input=payload.get("input", ""),
                capability_id=payload.get("capability_id"),
                delegatee_id=message.to_agent,
                context=context,
            )

            return message.create_reply(
                A2AMessageType.DELEGATE_ACCEPT,
                {"delegation_id": request.id, "status": request.status.value},
            )

        except Exception as e:
            return message.create_reply(
                A2AMessageType.DELEGATE_REJECT,
                {"error": str(e)},
            )

    async def _handle_status_query(self, message: A2AMessage) -> A2AMessage:
        """Handle status query message."""
        delegation_id = message.payload.get("delegation_id")

        if delegation_id:
            request = self.delegation.get_delegation(delegation_id)
            if not request:
                return message.create_error_reply(
                    f"Delegation {delegation_id} not found",
                    "NOT_FOUND",
                )

            return message.create_reply(
                A2AMessageType.STATUS_RESPONSE,
                {
                    "delegation_id": request.id,
                    "status": request.status.value,
                    "result": request.result,
                    "error": request.error,
                },
            )

        # General status query
        agent_id = message.to_agent
        agent = self.discovery.get(agent_id)

        if not agent:
            return message.create_error_reply(f"Agent {agent_id} not found", "NOT_FOUND")

        health = self.discovery.get_health(agent_id)

        return message.create_reply(
            A2AMessageType.STATUS_RESPONSE,
            {
                "agent_id": agent_id,
                "agent_name": agent.name,
                "health_status": health.status.value if health else "unknown",
                "active_delegations": len(self.delegation.get_delegatee_requests(agent_id)),
            },
        )

    # Convenience methods for common operations

    async def ping(self, from_agent: str, to_agent: str) -> bool:
        """Ping another agent to check availability."""
        message = A2AMessage(
            type=A2AMessageType.PING,
            from_agent=from_agent,
            to_agent=to_agent,
        )

        response = await self.send(message)
        return response is not None and response.type == A2AMessageType.PONG

    async def discover_agents(
        self,
        from_agent: str,
        to_agent: str,
        capability_tags: Optional[List[str]] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Discover agents through another agent."""
        message = A2AMessage(
            type=A2AMessageType.DISCOVER,
            from_agent=from_agent,
            to_agent=to_agent,
            payload={
                "filter": {
                    "capability_tags": capability_tags,
                    "limit": limit,
                }
            },
        )

        response = await self.send(message)
        if response and response.type == A2AMessageType.DISCOVER_RESPONSE:
            return response.payload.get("agents", [])
        return []

    async def query_capabilities(
        self,
        from_agent: str,
        to_agent: str,
        capability_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Query an agent's capabilities."""
        message = A2AMessage(
            type=A2AMessageType.CAPABILITY_QUERY,
            from_agent=from_agent,
            to_agent=to_agent,
            payload={"capability_id": capability_id},
        )

        response = await self.send(message)
        if response and response.type == A2AMessageType.CAPABILITY_RESPONSE:
            return response.payload.get("capabilities", [])
        return []

    async def delegate_task(
        self,
        from_agent: str,
        to_agent: str,
        task_input: str,
        capability_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Delegate a task to another agent."""
        message = A2AMessage(
            type=A2AMessageType.DELEGATE,
            from_agent=from_agent,
            to_agent=to_agent,
            payload={
                "input": task_input,
                "capability_id": capability_id,
                "context": context or {},
            },
        )

        response = await self.send(message)
        if response and response.type == A2AMessageType.DELEGATE_ACCEPT:
            return response.payload.get("delegation_id")
        return None

    async def query_status(
        self,
        from_agent: str,
        to_agent: str,
        delegation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Query status of an agent or delegation."""
        message = A2AMessage(
            type=A2AMessageType.STATUS_QUERY,
            from_agent=from_agent,
            to_agent=to_agent,
            payload={"delegation_id": delegation_id},
        )

        response = await self.send(message)
        if response and response.type == A2AMessageType.STATUS_RESPONSE:
            return response.payload
        return {}


# Global protocol instance
_protocol: Optional[A2AProtocol] = None


def get_a2a_protocol() -> A2AProtocol:
    """Get the global A2A protocol instance."""
    global _protocol
    if _protocol is None:
        _protocol = A2AProtocol()
    return _protocol
