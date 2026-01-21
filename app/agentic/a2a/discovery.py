"""
Agent Discovery Service

Enables agents to discover and connect with other agents:
- Register agents for discovery
- Search agents by capabilities
- Health monitoring
- Trust verification
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import UUID

from .agent_card import AgentCard, AgentCapability

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health status of an agent."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class DiscoveryFilter:
    """Filter criteria for agent discovery."""
    # Identity filters
    agent_ids: Optional[List[str]] = None
    tenant_id: Optional[UUID] = None
    organization: Optional[str] = None

    # Type filters
    agent_types: Optional[List[str]] = None
    roles: Optional[List[str]] = None

    # Capability filters
    capability_ids: Optional[List[str]] = None
    capability_tags: Optional[List[str]] = None
    capability_types: Optional[List[str]] = None

    # Trust filters
    min_trust_level: int = 0
    require_certified: bool = False

    # Collaboration filters
    can_delegate: Optional[bool] = None
    can_accept_delegation: Optional[bool] = None

    # Health filters
    health_status: Optional[HealthStatus] = None
    exclude_unhealthy: bool = True

    # Pagination
    limit: int = 100
    offset: int = 0


@dataclass
class AgentHealth:
    """Health information for an agent."""
    agent_id: str
    status: HealthStatus
    last_check: datetime
    response_time_ms: Optional[int] = None
    error: Optional[str] = None
    consecutive_failures: int = 0


@dataclass
class DiscoveryResult:
    """Result of an agent discovery query."""
    agents: List[AgentCard]
    total: int
    has_more: bool
    query_time_ms: int


class AgentDiscovery:
    """
    Agent Discovery Service.

    Central registry for agent discovery:
    - Agents register their cards
    - Other agents query for capabilities
    - Health monitoring keeps registry current
    """

    def __init__(self):
        """Initialize the discovery service."""
        # Agent registry
        self._agents: Dict[str, AgentCard] = {}
        self._by_tenant: Dict[UUID, Set[str]] = {}
        self._by_capability: Dict[str, Set[str]] = {}
        self._by_tag: Dict[str, Set[str]] = {}

        # Health tracking
        self._health: Dict[str, AgentHealth] = {}
        self._health_check_interval = 60  # seconds

        # Callbacks
        self._on_register: List[Callable] = []
        self._on_unregister: List[Callable] = []
        self._on_health_change: List[Callable] = []

    def register(self, card: AgentCard) -> None:
        """
        Register an agent for discovery.

        Args:
            card: Agent card to register
        """
        agent_id = card.id
        self._agents[agent_id] = card

        # Index by tenant
        if card.tenant_id:
            if card.tenant_id not in self._by_tenant:
                self._by_tenant[card.tenant_id] = set()
            self._by_tenant[card.tenant_id].add(agent_id)

        # Index by capability
        for cap in card.capabilities:
            if cap.id not in self._by_capability:
                self._by_capability[cap.id] = set()
            self._by_capability[cap.id].add(agent_id)

            # Index by tags
            for tag in cap.tags:
                if tag not in self._by_tag:
                    self._by_tag[tag] = set()
                self._by_tag[tag].add(agent_id)

        # Initialize health
        self._health[agent_id] = AgentHealth(
            agent_id=agent_id,
            status=HealthStatus.UNKNOWN,
            last_check=datetime.utcnow(),
        )

        logger.info(f"Agent registered: {card.name} ({agent_id})")

        # Notify callbacks
        for callback in self._on_register:
            try:
                callback(card)
            except Exception as e:
                logger.error(f"Register callback error: {e}")

    def unregister(self, agent_id: str) -> Optional[AgentCard]:
        """
        Unregister an agent from discovery.

        Args:
            agent_id: Agent to unregister

        Returns:
            Removed AgentCard or None if not found
        """
        card = self._agents.pop(agent_id, None)
        if not card:
            return None

        # Remove from indexes
        if card.tenant_id and card.tenant_id in self._by_tenant:
            self._by_tenant[card.tenant_id].discard(agent_id)

        for cap in card.capabilities:
            if cap.id in self._by_capability:
                self._by_capability[cap.id].discard(agent_id)
            for tag in cap.tags:
                if tag in self._by_tag:
                    self._by_tag[tag].discard(agent_id)

        # Remove health
        self._health.pop(agent_id, None)

        logger.info(f"Agent unregistered: {card.name} ({agent_id})")

        # Notify callbacks
        for callback in self._on_unregister:
            try:
                callback(card)
            except Exception as e:
                logger.error(f"Unregister callback error: {e}")

        return card

    def update(self, card: AgentCard) -> None:
        """
        Update an agent's registration.

        Args:
            card: Updated agent card
        """
        # Unregister old card
        self.unregister(card.id)
        # Register new card
        self.register(card)

    def get(self, agent_id: str) -> Optional[AgentCard]:
        """Get an agent card by ID."""
        return self._agents.get(agent_id)

    def get_health(self, agent_id: str) -> Optional[AgentHealth]:
        """Get health status for an agent."""
        return self._health.get(agent_id)

    def discover(self, filter: DiscoveryFilter) -> DiscoveryResult:
        """
        Discover agents matching the filter criteria.

        Args:
            filter: Discovery filter

        Returns:
            DiscoveryResult with matching agents
        """
        start_time = datetime.utcnow()

        # Start with all agents or filtered set
        candidates: Set[str] = set()

        if filter.agent_ids:
            candidates = set(filter.agent_ids) & set(self._agents.keys())
        elif filter.tenant_id:
            candidates = self._by_tenant.get(filter.tenant_id, set()).copy()
        elif filter.capability_ids:
            for cap_id in filter.capability_ids:
                cap_agents = self._by_capability.get(cap_id, set())
                if not candidates:
                    candidates = cap_agents.copy()
                else:
                    candidates &= cap_agents
        elif filter.capability_tags:
            for tag in filter.capability_tags:
                tag_agents = self._by_tag.get(tag, set())
                if not candidates:
                    candidates = tag_agents.copy()
                else:
                    candidates &= tag_agents
        else:
            candidates = set(self._agents.keys())

        # Apply additional filters
        results: List[AgentCard] = []

        for agent_id in candidates:
            card = self._agents.get(agent_id)
            if not card:
                continue

            # Type filter
            if filter.agent_types and card.agent_type not in filter.agent_types:
                continue

            # Role filter
            if filter.roles and card.role not in filter.roles:
                continue

            # Capability type filter
            if filter.capability_types:
                has_type = any(
                    cap.capability_type in filter.capability_types
                    for cap in card.capabilities
                )
                if not has_type:
                    continue

            # Trust filter
            if card.trust_level < filter.min_trust_level:
                continue

            # Certification filter
            if filter.require_certified and not card.certification_id:
                continue

            # Delegation filters
            if filter.can_delegate is not None and card.can_delegate != filter.can_delegate:
                continue
            if filter.can_accept_delegation is not None and card.can_accept_delegation != filter.can_accept_delegation:
                continue

            # Health filter
            health = self._health.get(agent_id)
            if filter.exclude_unhealthy and health and health.status == HealthStatus.UNHEALTHY:
                continue
            if filter.health_status and health and health.status != filter.health_status:
                continue

            results.append(card)

        # Sort by trust level (descending)
        results.sort(key=lambda c: c.trust_level, reverse=True)

        # Pagination
        total = len(results)
        has_more = (filter.offset + filter.limit) < total
        results = results[filter.offset:filter.offset + filter.limit]

        query_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        return DiscoveryResult(
            agents=results,
            total=total,
            has_more=has_more,
            query_time_ms=query_time,
        )

    def find_by_capability(
        self,
        capability_id: str,
        tenant_id: Optional[UUID] = None,
        min_trust: int = 0,
    ) -> List[AgentCard]:
        """
        Find agents with a specific capability.

        Args:
            capability_id: Capability to find
            tenant_id: Optional tenant filter
            min_trust: Minimum trust level

        Returns:
            List of matching agent cards
        """
        result = self.discover(DiscoveryFilter(
            capability_ids=[capability_id],
            tenant_id=tenant_id,
            min_trust_level=min_trust,
        ))
        return result.agents

    def find_by_tag(
        self,
        tag: str,
        tenant_id: Optional[UUID] = None,
        min_trust: int = 0,
    ) -> List[AgentCard]:
        """
        Find agents with capabilities matching a tag.

        Args:
            tag: Tag to search for
            tenant_id: Optional tenant filter
            min_trust: Minimum trust level

        Returns:
            List of matching agent cards
        """
        result = self.discover(DiscoveryFilter(
            capability_tags=[tag],
            tenant_id=tenant_id,
            min_trust_level=min_trust,
        ))
        return result.agents

    def find_delegatees(
        self,
        capability_id: str,
        excluding: Optional[str] = None,
        tenant_id: Optional[UUID] = None,
    ) -> List[AgentCard]:
        """
        Find agents that can accept delegation for a capability.

        Args:
            capability_id: Capability to delegate
            excluding: Agent ID to exclude (usually the delegator)
            tenant_id: Optional tenant filter

        Returns:
            List of agents that can accept the delegation
        """
        result = self.discover(DiscoveryFilter(
            capability_ids=[capability_id],
            tenant_id=tenant_id,
            can_accept_delegation=True,
            exclude_unhealthy=True,
        ))

        agents = result.agents
        if excluding:
            agents = [a for a in agents if a.id != excluding]

        return agents

    async def update_health(
        self,
        agent_id: str,
        status: HealthStatus,
        response_time_ms: Optional[int] = None,
        error: Optional[str] = None,
    ) -> None:
        """
        Update health status for an agent.

        Args:
            agent_id: Agent to update
            status: New health status
            response_time_ms: Response time if healthy
            error: Error message if unhealthy
        """
        health = self._health.get(agent_id)
        if not health:
            return

        old_status = health.status
        health.status = status
        health.last_check = datetime.utcnow()
        health.response_time_ms = response_time_ms
        health.error = error

        if status == HealthStatus.UNHEALTHY:
            health.consecutive_failures += 1
        else:
            health.consecutive_failures = 0

        # Notify on status change
        if old_status != status:
            logger.info(f"Agent {agent_id} health changed: {old_status.value} -> {status.value}")
            for callback in self._on_health_change:
                try:
                    callback(agent_id, old_status, status)
                except Exception as e:
                    logger.error(f"Health change callback error: {e}")

    async def check_health(self, agent_id: str) -> HealthStatus:
        """
        Perform a health check on an agent.

        Args:
            agent_id: Agent to check

        Returns:
            Current health status
        """
        card = self._agents.get(agent_id)
        if not card:
            return HealthStatus.UNKNOWN

        endpoint = card.get_primary_endpoint()
        if not endpoint or not endpoint.health_check_path:
            return HealthStatus.UNKNOWN

        # Perform health check (simplified - in production would make HTTP call)
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                url = f"{endpoint.url.rstrip('/')}{endpoint.health_check_path}"
                start = datetime.utcnow()
                async with session.get(url, timeout=10) as response:
                    response_time = int((datetime.utcnow() - start).total_seconds() * 1000)

                    if response.status == 200:
                        status = HealthStatus.HEALTHY
                    elif response.status < 500:
                        status = HealthStatus.DEGRADED
                    else:
                        status = HealthStatus.UNHEALTHY

                    await self.update_health(agent_id, status, response_time)
                    return status

        except Exception as e:
            await self.update_health(agent_id, HealthStatus.UNHEALTHY, error=str(e))
            return HealthStatus.UNHEALTHY

    def on_register(self, callback: Callable[[AgentCard], None]) -> None:
        """Register a callback for agent registration events."""
        self._on_register.append(callback)

    def on_unregister(self, callback: Callable[[AgentCard], None]) -> None:
        """Register a callback for agent unregistration events."""
        self._on_unregister.append(callback)

    def on_health_change(self, callback: Callable[[str, HealthStatus, HealthStatus], None]) -> None:
        """Register a callback for health status changes."""
        self._on_health_change.append(callback)

    def get_statistics(self, tenant_id: Optional[UUID] = None) -> Dict[str, Any]:
        """Get discovery service statistics."""
        if tenant_id:
            agent_ids = self._by_tenant.get(tenant_id, set())
            agents = [self._agents[aid] for aid in agent_ids if aid in self._agents]
        else:
            agents = list(self._agents.values())

        health_counts = {s: 0 for s in HealthStatus}
        for h in self._health.values():
            health_counts[h.status] += 1

        return {
            "total_agents": len(agents),
            "by_type": {},
            "by_role": {},
            "health_status": {s.value: c for s, c in health_counts.items()},
            "total_capabilities": sum(len(a.capabilities) for a in agents),
            "certified_agents": sum(1 for a in agents if a.certification_id),
        }


# Global discovery instance
_discovery: Optional[AgentDiscovery] = None


def get_agent_discovery() -> AgentDiscovery:
    """Get the global agent discovery instance."""
    global _discovery
    if _discovery is None:
        _discovery = AgentDiscovery()
    return _discovery
