"""
Agent Inventory

Central inventory for tracking all registered agents.
Implements Agent Registry: Agent discovery & inventory from RACI.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import UUID

from .models import (
    AgentRecord,
    AgentMetadata,
    AgentOwnership,
    AgentStatus,
    AgentDomain,
    TrustTier,
)

logger = logging.getLogger(__name__)


@dataclass
class InventoryFilter:
    """Filter criteria for agent inventory queries."""
    # Identity filters
    agent_ids: Optional[List[UUID]] = None
    tenant_id: Optional[UUID] = None
    names: Optional[List[str]] = None
    name_pattern: Optional[str] = None

    # Type filters
    agent_types: Optional[List[str]] = None
    domains: Optional[List[AgentDomain]] = None

    # Trust filters
    trust_tiers: Optional[List[TrustTier]] = None
    min_trust_tier: Optional[TrustTier] = None

    # Status filters
    statuses: Optional[List[AgentStatus]] = None
    exclude_inactive: bool = True
    include_zombies: bool = False

    # Ownership filters
    owner_ids: Optional[List[UUID]] = None
    owner_types: Optional[List[str]] = None

    # Capability filters
    capabilities: Optional[List[str]] = None
    tags: Optional[List[str]] = None

    # Certification filters
    require_certified: bool = False
    exclude_expired_certs: bool = True

    # Health filters
    require_healthy: bool = False

    # Time filters
    active_since: Optional[datetime] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None

    # Pagination
    limit: int = 100
    offset: int = 0

    # Sorting
    sort_by: str = "name"
    sort_desc: bool = False


@dataclass
class InventoryStats:
    """Statistics about the agent inventory."""
    total_agents: int = 0
    active_agents: int = 0
    inactive_agents: int = 0
    zombie_agents: int = 0

    by_domain: Dict[str, int] = field(default_factory=dict)
    by_trust_tier: Dict[str, int] = field(default_factory=dict)
    by_status: Dict[str, int] = field(default_factory=dict)
    by_owner_type: Dict[str, int] = field(default_factory=dict)

    certified_agents: int = 0
    healthy_agents: int = 0

    total_runs_24h: int = 0
    total_cost_24h_usd: float = 0.0

    last_updated: datetime = field(default_factory=datetime.utcnow)


class AgentInventory:
    """
    Agent Inventory Service.

    Central registry for all agents in the platform:
    - Register and unregister agents
    - Query agents by various criteria
    - Track agent metadata and ownership
    - Detect zombie agents
    """

    # Trust tier ordering for comparisons
    TRUST_TIER_ORDER = {
        TrustTier.NATIVE: 4,
        TrustTier.VERIFIED: 3,
        TrustTier.CUSTOMER: 2,
        TrustTier.THIRD_PARTY: 1,
        TrustTier.SANDBOX: 0,
    }

    def __init__(self):
        """Initialize the inventory."""
        # Primary storage
        self._agents: Dict[UUID, AgentRecord] = {}

        # Indexes for fast lookup
        self._by_tenant: Dict[UUID, Set[UUID]] = {}
        self._by_owner: Dict[UUID, Set[UUID]] = {}
        self._by_domain: Dict[AgentDomain, Set[UUID]] = {}
        self._by_status: Dict[AgentStatus, Set[UUID]] = {}
        self._by_capability: Dict[str, Set[UUID]] = {}
        self._by_tag: Dict[str, Set[UUID]] = {}

        # Event callbacks
        self._on_register: List[Callable[[AgentRecord], None]] = []
        self._on_unregister: List[Callable[[AgentRecord], None]] = []
        self._on_status_change: List[Callable[[AgentRecord, AgentStatus, AgentStatus], None]] = []
        self._on_zombie_detected: List[Callable[[AgentRecord], None]] = []

        # Zombie detection config
        self._zombie_threshold = timedelta(days=7)

    def register(self, record: AgentRecord) -> AgentRecord:
        """
        Register an agent in the inventory.

        Args:
            record: Agent record to register

        Returns:
            Registered agent record
        """
        agent_id = record.id

        # Store agent
        self._agents[agent_id] = record

        # Update indexes
        self._index_agent(record)

        logger.info(f"Agent registered: {record.name} ({agent_id})")

        # Notify callbacks
        for callback in self._on_register:
            try:
                callback(record)
            except Exception as e:
                logger.error(f"Register callback error: {e}")

        return record

    def unregister(self, agent_id: UUID) -> Optional[AgentRecord]:
        """
        Unregister an agent from the inventory.

        Args:
            agent_id: ID of agent to unregister

        Returns:
            Removed agent record or None
        """
        record = self._agents.pop(agent_id, None)
        if not record:
            return None

        # Remove from indexes
        self._unindex_agent(record)

        logger.info(f"Agent unregistered: {record.name} ({agent_id})")

        # Notify callbacks
        for callback in self._on_unregister:
            try:
                callback(record)
            except Exception as e:
                logger.error(f"Unregister callback error: {e}")

        return record

    def update(self, record: AgentRecord) -> AgentRecord:
        """
        Update an agent's registration.

        Args:
            record: Updated agent record

        Returns:
            Updated agent record
        """
        old_record = self._agents.get(record.id)

        # Unindex old record if exists
        if old_record:
            self._unindex_agent(old_record)

        # Store and index new record
        record.metadata.updated_at = datetime.utcnow()
        self._agents[record.id] = record
        self._index_agent(record)

        # Check for status change
        if old_record and old_record.status != record.status:
            for callback in self._on_status_change:
                try:
                    callback(record, old_record.status, record.status)
                except Exception as e:
                    logger.error(f"Status change callback error: {e}")

        return record

    def get(self, agent_id: UUID) -> Optional[AgentRecord]:
        """Get an agent record by ID."""
        return self._agents.get(agent_id)

    def exists(self, agent_id: UUID) -> bool:
        """Check if an agent exists."""
        return agent_id in self._agents

    def query(self, filter: InventoryFilter) -> List[AgentRecord]:
        """
        Query agents matching filter criteria.

        Args:
            filter: Query filter

        Returns:
            List of matching agent records
        """
        # Start with candidates based on most selective filter
        candidates = self._get_initial_candidates(filter)

        # Apply filters
        results = []
        for agent_id in candidates:
            record = self._agents.get(agent_id)
            if record and self._matches_filter(record, filter):
                results.append(record)

        # Sort
        results = self._sort_results(results, filter.sort_by, filter.sort_desc)

        # Paginate
        return results[filter.offset:filter.offset + filter.limit]

    def count(self, filter: InventoryFilter) -> int:
        """Count agents matching filter criteria."""
        candidates = self._get_initial_candidates(filter)
        count = 0
        for agent_id in candidates:
            record = self._agents.get(agent_id)
            if record and self._matches_filter(record, filter):
                count += 1
        return count

    def get_stats(self, tenant_id: Optional[UUID] = None) -> InventoryStats:
        """
        Get inventory statistics.

        Args:
            tenant_id: Optional tenant filter

        Returns:
            Inventory statistics
        """
        if tenant_id:
            agent_ids = self._by_tenant.get(tenant_id, set())
            agents = [self._agents[aid] for aid in agent_ids if aid in self._agents]
        else:
            agents = list(self._agents.values())

        stats = InventoryStats(
            total_agents=len(agents),
            last_updated=datetime.utcnow(),
        )

        for agent in agents:
            # Status counts
            status = agent.status.value
            stats.by_status[status] = stats.by_status.get(status, 0) + 1

            if agent.status == AgentStatus.ACTIVE:
                stats.active_agents += 1
            elif agent.status == AgentStatus.ZOMBIE:
                stats.zombie_agents += 1
            elif agent.status in [AgentStatus.INACTIVE, AgentStatus.SUSPENDED]:
                stats.inactive_agents += 1

            # Domain counts
            domain = agent.metadata.domain.value
            stats.by_domain[domain] = stats.by_domain.get(domain, 0) + 1

            # Trust tier counts
            tier = agent.metadata.trust_tier.value
            stats.by_trust_tier[tier] = stats.by_trust_tier.get(tier, 0) + 1

            # Owner type counts
            owner_type = agent.ownership.owner_type
            stats.by_owner_type[owner_type] = stats.by_owner_type.get(owner_type, 0) + 1

            # Certification
            if agent.is_certified():
                stats.certified_agents += 1

            # Health
            if agent.health_status == "healthy":
                stats.healthy_agents += 1

        return stats

    def detect_zombies(self, threshold: Optional[timedelta] = None) -> List[AgentRecord]:
        """
        Detect zombie agents (inactive for too long).

        Args:
            threshold: Inactivity threshold (default 7 days)

        Returns:
            List of detected zombie agents
        """
        if threshold is None:
            threshold = self._zombie_threshold

        cutoff = datetime.utcnow() - threshold
        zombies = []

        for agent in self._agents.values():
            # Skip already marked zombies or inactive agents
            if agent.status in [AgentStatus.ZOMBIE, AgentStatus.INACTIVE, AgentStatus.DEPRECATED]:
                continue

            # Check last activity
            last_active = agent.last_active_at or agent.metadata.created_at
            if last_active < cutoff:
                # Mark as zombie
                old_status = agent.status
                agent.status = AgentStatus.ZOMBIE
                agent.status_reason = f"No activity since {last_active.isoformat()}"
                agent.status_updated_at = datetime.utcnow()

                zombies.append(agent)

                # Notify callbacks
                for callback in self._on_zombie_detected:
                    try:
                        callback(agent)
                    except Exception as e:
                        logger.error(f"Zombie detection callback error: {e}")

                for callback in self._on_status_change:
                    try:
                        callback(agent, old_status, AgentStatus.ZOMBIE)
                    except Exception as e:
                        logger.error(f"Status change callback error: {e}")

        return zombies

    def get_by_owner(self, owner_id: UUID) -> List[AgentRecord]:
        """Get all agents owned by a specific owner."""
        agent_ids = self._by_owner.get(owner_id, set())
        return [self._agents[aid] for aid in agent_ids if aid in self._agents]

    def get_by_tenant(self, tenant_id: UUID) -> List[AgentRecord]:
        """Get all agents for a specific tenant."""
        agent_ids = self._by_tenant.get(tenant_id, set())
        return [self._agents[aid] for aid in agent_ids if aid in self._agents]

    def get_by_capability(self, capability: str) -> List[AgentRecord]:
        """Get all agents with a specific capability."""
        agent_ids = self._by_capability.get(capability, set())
        return [self._agents[aid] for aid in agent_ids if aid in self._agents]

    def record_activity(self, agent_id: UUID, success: bool, cost_usd: float = 0.0) -> None:
        """
        Record agent activity (run completion).

        Args:
            agent_id: Agent ID
            success: Whether the run was successful
            cost_usd: Cost of the run
        """
        record = self._agents.get(agent_id)
        if not record:
            return

        record.last_active_at = datetime.utcnow()
        record.total_runs += 1
        record.total_cost_usd += cost_usd

        if success:
            record.successful_runs += 1
        else:
            record.failed_runs += 1

    # Event registration
    def on_register(self, callback: Callable[[AgentRecord], None]) -> None:
        """Register callback for agent registration events."""
        self._on_register.append(callback)

    def on_unregister(self, callback: Callable[[AgentRecord], None]) -> None:
        """Register callback for agent unregistration events."""
        self._on_unregister.append(callback)

    def on_status_change(self, callback: Callable[[AgentRecord, AgentStatus, AgentStatus], None]) -> None:
        """Register callback for agent status changes."""
        self._on_status_change.append(callback)

    def on_zombie_detected(self, callback: Callable[[AgentRecord], None]) -> None:
        """Register callback for zombie agent detection."""
        self._on_zombie_detected.append(callback)

    # Private methods

    def _index_agent(self, record: AgentRecord) -> None:
        """Add agent to indexes."""
        agent_id = record.id

        # Tenant index
        if record.tenant_id:
            if record.tenant_id not in self._by_tenant:
                self._by_tenant[record.tenant_id] = set()
            self._by_tenant[record.tenant_id].add(agent_id)

        # Owner index
        if record.ownership:
            if record.ownership.owner_id not in self._by_owner:
                self._by_owner[record.ownership.owner_id] = set()
            self._by_owner[record.ownership.owner_id].add(agent_id)

        # Domain index
        domain = record.metadata.domain
        if domain not in self._by_domain:
            self._by_domain[domain] = set()
        self._by_domain[domain].add(agent_id)

        # Status index
        status = record.status
        if status not in self._by_status:
            self._by_status[status] = set()
        self._by_status[status].add(agent_id)

        # Capability index
        for cap in record.metadata.declared_capabilities:
            if cap not in self._by_capability:
                self._by_capability[cap] = set()
            self._by_capability[cap].add(agent_id)

        # Tag index
        for tag in record.metadata.tags:
            if tag not in self._by_tag:
                self._by_tag[tag] = set()
            self._by_tag[tag].add(agent_id)

    def _unindex_agent(self, record: AgentRecord) -> None:
        """Remove agent from indexes."""
        agent_id = record.id

        if record.tenant_id and record.tenant_id in self._by_tenant:
            self._by_tenant[record.tenant_id].discard(agent_id)

        if record.ownership and record.ownership.owner_id in self._by_owner:
            self._by_owner[record.ownership.owner_id].discard(agent_id)

        if record.metadata.domain in self._by_domain:
            self._by_domain[record.metadata.domain].discard(agent_id)

        if record.status in self._by_status:
            self._by_status[record.status].discard(agent_id)

        for cap in record.metadata.declared_capabilities:
            if cap in self._by_capability:
                self._by_capability[cap].discard(agent_id)

        for tag in record.metadata.tags:
            if tag in self._by_tag:
                self._by_tag[tag].discard(agent_id)

    def _get_initial_candidates(self, filter: InventoryFilter) -> Set[UUID]:
        """Get initial candidate set based on most selective filter."""
        if filter.agent_ids:
            return set(filter.agent_ids) & set(self._agents.keys())

        if filter.tenant_id:
            return self._by_tenant.get(filter.tenant_id, set()).copy()

        if filter.owner_ids and len(filter.owner_ids) == 1:
            return self._by_owner.get(filter.owner_ids[0], set()).copy()

        if filter.capabilities:
            result = None
            for cap in filter.capabilities:
                cap_agents = self._by_capability.get(cap, set())
                if result is None:
                    result = cap_agents.copy()
                else:
                    result &= cap_agents
            return result or set()

        if filter.statuses and len(filter.statuses) == 1:
            return self._by_status.get(filter.statuses[0], set()).copy()

        return set(self._agents.keys())

    def _matches_filter(self, record: AgentRecord, filter: InventoryFilter) -> bool:
        """Check if an agent matches the filter criteria."""
        # Name filters
        if filter.names and record.name not in filter.names:
            return False

        if filter.name_pattern:
            import fnmatch
            if not fnmatch.fnmatch(record.name.lower(), filter.name_pattern.lower()):
                return False

        # Type filters
        if filter.agent_types and record.agent_type not in filter.agent_types:
            return False

        if filter.domains and record.metadata.domain not in filter.domains:
            return False

        # Trust filters
        if filter.trust_tiers and record.metadata.trust_tier not in filter.trust_tiers:
            return False

        if filter.min_trust_tier:
            min_order = self.TRUST_TIER_ORDER.get(filter.min_trust_tier, 0)
            record_order = self.TRUST_TIER_ORDER.get(record.metadata.trust_tier, 0)
            if record_order < min_order:
                return False

        # Status filters
        if filter.statuses and record.status not in filter.statuses:
            return False

        if filter.exclude_inactive and record.status in [
            AgentStatus.INACTIVE, AgentStatus.SUSPENDED, AgentStatus.DEPRECATED
        ]:
            return False

        if not filter.include_zombies and record.status == AgentStatus.ZOMBIE:
            return False

        # Ownership filters
        if filter.owner_ids and record.ownership.owner_id not in filter.owner_ids:
            return False

        if filter.owner_types and record.ownership.owner_type not in filter.owner_types:
            return False

        # Tags filter
        if filter.tags:
            if not any(tag in record.metadata.tags for tag in filter.tags):
                return False

        # Certification filter
        if filter.require_certified and not record.is_certified():
            return False

        if filter.exclude_expired_certs and record.certification_id:
            if not record.is_certified():
                return False

        # Health filter
        if filter.require_healthy and record.health_status != "healthy":
            return False

        # Time filters
        if filter.active_since and record.last_active_at:
            if record.last_active_at < filter.active_since:
                return False

        if filter.created_after and record.metadata.created_at < filter.created_after:
            return False

        if filter.created_before and record.metadata.created_at > filter.created_before:
            return False

        return True

    def _sort_results(
        self,
        results: List[AgentRecord],
        sort_by: str,
        desc: bool
    ) -> List[AgentRecord]:
        """Sort query results."""
        key_funcs = {
            "name": lambda r: r.name.lower(),
            "created_at": lambda r: r.metadata.created_at,
            "updated_at": lambda r: r.metadata.updated_at,
            "last_active_at": lambda r: r.last_active_at or datetime.min,
            "total_runs": lambda r: r.total_runs,
            "success_rate": lambda r: r.success_rate(),
            "total_cost": lambda r: r.total_cost_usd,
            "trust_tier": lambda r: self.TRUST_TIER_ORDER.get(r.metadata.trust_tier, 0),
        }

        key_func = key_funcs.get(sort_by, key_funcs["name"])
        return sorted(results, key=key_func, reverse=desc)


# Global inventory instance
_inventory: Optional[AgentInventory] = None


def get_agent_inventory() -> AgentInventory:
    """Get the global agent inventory instance."""
    global _inventory
    if _inventory is None:
        _inventory = AgentInventory()
    return _inventory
