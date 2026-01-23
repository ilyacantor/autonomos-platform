"""
Vitals Monitor

Aggregates and monitors vital signs for agents and the platform.
Implements Observability: Vitals aggregation from RACI.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID

from .models import Vital, VitalStatus

logger = logging.getLogger(__name__)


@dataclass
class VitalsSnapshot:
    """A snapshot of all vitals at a point in time."""
    id: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Overall status
    overall_status: VitalStatus = VitalStatus.UNKNOWN
    healthy_count: int = 0
    warning_count: int = 0
    critical_count: int = 0
    unknown_count: int = 0

    # Vitals by component
    vitals: List[Vital] = field(default_factory=list)
    by_component: Dict[str, List[Vital]] = field(default_factory=dict)
    by_agent: Dict[str, List[Vital]] = field(default_factory=dict)

    def get_component_status(self, component: str) -> VitalStatus:
        """Get overall status for a component."""
        component_vitals = self.by_component.get(component, [])
        return self._aggregate_status(component_vitals)

    def get_agent_status(self, agent_id: str) -> VitalStatus:
        """Get overall status for an agent."""
        agent_vitals = self.by_agent.get(agent_id, [])
        return self._aggregate_status(agent_vitals)

    def _aggregate_status(self, vitals: List[Vital]) -> VitalStatus:
        """Aggregate status from multiple vitals."""
        if not vitals:
            return VitalStatus.UNKNOWN

        if any(v.status == VitalStatus.CRITICAL for v in vitals):
            return VitalStatus.CRITICAL
        if any(v.status == VitalStatus.WARNING for v in vitals):
            return VitalStatus.WARNING
        if all(v.status == VitalStatus.HEALTHY for v in vitals):
            return VitalStatus.HEALTHY
        return VitalStatus.UNKNOWN

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "overall_status": self.overall_status.value,
            "summary": {
                "healthy": self.healthy_count,
                "warning": self.warning_count,
                "critical": self.critical_count,
                "unknown": self.unknown_count,
                "total": len(self.vitals),
            },
            "vitals": [v.to_dict() for v in self.vitals],
        }


class VitalsMonitor:
    """
    Vitals Monitor.

    Monitors and aggregates vital signs:
    - CPU, memory, latency vitals
    - Agent-specific vitals
    - System-level vitals
    - Historical tracking
    """

    # Default vital definitions
    DEFAULT_VITALS = [
        {
            "name": "agent_active_runs",
            "component": "agents",
            "warning_threshold": 80,
            "critical_threshold": 95,
            "unit": "percent",
        },
        {
            "name": "agent_error_rate",
            "component": "agents",
            "warning_threshold": 5,
            "critical_threshold": 10,
            "unit": "percent",
        },
        {
            "name": "agent_latency_p99",
            "component": "agents",
            "warning_threshold": 5000,
            "critical_threshold": 10000,
            "unit": "ms",
        },
        {
            "name": "task_queue_depth",
            "component": "system",
            "warning_threshold": 1000,
            "critical_threshold": 5000,
            "unit": "tasks",
        },
        {
            "name": "worker_utilization",
            "component": "system",
            "warning_threshold": 80,
            "critical_threshold": 95,
            "unit": "percent",
        },
        {
            "name": "cost_burn_rate",
            "component": "economics",
            "warning_threshold": 150,
            "critical_threshold": 200,
            "unit": "percent_of_budget",
        },
    ]

    def __init__(self):
        """Initialize the vitals monitor."""
        # Vital definitions
        self._vital_definitions: Dict[str, Dict[str, Any]] = {}

        # Current vitals
        self._current_vitals: Dict[str, Vital] = {}

        # History
        self._snapshots: List[VitalsSnapshot] = []
        self._max_snapshots = 1000

        # Vital providers (functions that return vital values)
        self._providers: Dict[str, Callable[[], Optional[float]]] = {}

        # Callbacks
        self._on_status_change: List[Callable[[Vital, VitalStatus, VitalStatus], None]] = []
        self._on_critical: List[Callable[[Vital], None]] = []

        # Initialize default vitals
        for vital_def in self.DEFAULT_VITALS:
            self.register_vital(**vital_def)

    def register_vital(
        self,
        name: str,
        component: str,
        warning_threshold: Optional[float] = None,
        critical_threshold: Optional[float] = None,
        unit: Optional[str] = None,
    ) -> None:
        """
        Register a vital to monitor.

        Args:
            name: Vital name
            component: Component this vital belongs to
            warning_threshold: Warning threshold
            critical_threshold: Critical threshold
            unit: Unit of measurement
        """
        self._vital_definitions[name] = {
            "name": name,
            "component": component,
            "warning_threshold": warning_threshold,
            "critical_threshold": critical_threshold,
            "unit": unit,
        }

    def register_provider(
        self,
        vital_name: str,
        provider: Callable[[], Optional[float]],
    ) -> None:
        """Register a provider function for a vital."""
        self._providers[vital_name] = provider

    def record(
        self,
        name: str,
        value: float,
        agent_id: Optional[UUID] = None,
        tenant_id: Optional[UUID] = None,
        message: Optional[str] = None,
    ) -> Vital:
        """
        Record a vital value.

        Args:
            name: Vital name
            value: Current value
            agent_id: Agent ID
            tenant_id: Tenant ID
            message: Status message

        Returns:
            Recorded vital
        """
        definition = self._vital_definitions.get(name, {})

        vital = Vital(
            name=name,
            component=definition.get("component", "unknown"),
            value=value,
            unit=definition.get("unit"),
            warning_threshold=definition.get("warning_threshold"),
            critical_threshold=definition.get("critical_threshold"),
            agent_id=agent_id,
            tenant_id=tenant_id,
            message=message,
        )

        # Evaluate status
        vital.status = vital.evaluate()

        # Check for status change
        key = self._make_key(name, agent_id)
        old_vital = self._current_vitals.get(key)

        if old_vital:
            vital.previous_value = old_vital.value
            if old_vital.value is not None and vital.value is not None:
                if vital.value > old_vital.value:
                    vital.trend = "up"
                elif vital.value < old_vital.value:
                    vital.trend = "down"
                else:
                    vital.trend = "stable"

            if old_vital.status != vital.status:
                for callback in self._on_status_change:
                    try:
                        callback(vital, old_vital.status, vital.status)
                    except Exception as e:
                        logger.error(f"Vital status change callback error: {e}")

        # Store current vital
        self._current_vitals[key] = vital

        # Notify on critical
        if vital.status == VitalStatus.CRITICAL:
            for callback in self._on_critical:
                try:
                    callback(vital)
                except Exception as e:
                    logger.error(f"Vital critical callback error: {e}")

        return vital

    def collect_all(self) -> VitalsSnapshot:
        """
        Collect all vitals and create a snapshot.

        Returns:
            Current vitals snapshot
        """
        # Collect from providers
        for name, provider in self._providers.items():
            try:
                value = provider()
                if value is not None:
                    self.record(name, value)
            except Exception as e:
                logger.error(f"Vital provider error for {name}: {e}")

        # Create snapshot
        snapshot = VitalsSnapshot(
            id=f"snapshot_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            timestamp=datetime.utcnow(),
        )

        for vital in self._current_vitals.values():
            snapshot.vitals.append(vital)

            # Count by status
            if vital.status == VitalStatus.HEALTHY:
                snapshot.healthy_count += 1
            elif vital.status == VitalStatus.WARNING:
                snapshot.warning_count += 1
            elif vital.status == VitalStatus.CRITICAL:
                snapshot.critical_count += 1
            else:
                snapshot.unknown_count += 1

            # Group by component
            if vital.component not in snapshot.by_component:
                snapshot.by_component[vital.component] = []
            snapshot.by_component[vital.component].append(vital)

            # Group by agent
            if vital.agent_id:
                agent_key = str(vital.agent_id)
                if agent_key not in snapshot.by_agent:
                    snapshot.by_agent[agent_key] = []
                snapshot.by_agent[agent_key].append(vital)

        # Calculate overall status
        if snapshot.critical_count > 0:
            snapshot.overall_status = VitalStatus.CRITICAL
        elif snapshot.warning_count > 0:
            snapshot.overall_status = VitalStatus.WARNING
        elif snapshot.healthy_count > 0:
            snapshot.overall_status = VitalStatus.HEALTHY
        else:
            snapshot.overall_status = VitalStatus.UNKNOWN

        # Store snapshot
        self._snapshots.append(snapshot)
        if len(self._snapshots) > self._max_snapshots:
            self._snapshots = self._snapshots[-self._max_snapshots:]

        return snapshot

    def get_current(self, name: str, agent_id: Optional[UUID] = None) -> Optional[Vital]:
        """Get current value for a vital."""
        key = self._make_key(name, agent_id)
        return self._current_vitals.get(key)

    def get_all_current(
        self,
        component: Optional[str] = None,
        agent_id: Optional[UUID] = None,
    ) -> List[Vital]:
        """Get all current vitals with optional filters."""
        vitals = list(self._current_vitals.values())

        if component:
            vitals = [v for v in vitals if v.component == component]
        if agent_id:
            vitals = [v for v in vitals if v.agent_id == agent_id]

        return vitals

    def get_snapshot(self, snapshot_id: str) -> Optional[VitalsSnapshot]:
        """Get a specific snapshot."""
        for snapshot in self._snapshots:
            if snapshot.id == snapshot_id:
                return snapshot
        return None

    def get_latest_snapshot(self) -> Optional[VitalsSnapshot]:
        """Get the most recent snapshot."""
        return self._snapshots[-1] if self._snapshots else None

    def get_history(
        self,
        name: str,
        agent_id: Optional[UUID] = None,
        limit: int = 100,
    ) -> List[Vital]:
        """Get historical values for a vital."""
        key_pattern = self._make_key(name, agent_id) if agent_id else name

        vitals = []
        for snapshot in reversed(self._snapshots):
            for vital in snapshot.vitals:
                if vital.name == name:
                    if agent_id is None or vital.agent_id == agent_id:
                        vitals.append(vital)
                        if len(vitals) >= limit:
                            break
            if len(vitals) >= limit:
                break

        return vitals

    def get_stats(self) -> Dict[str, Any]:
        """Get vitals monitoring statistics."""
        current = list(self._current_vitals.values())

        by_status = {}
        for status in VitalStatus:
            by_status[status.value] = sum(1 for v in current if v.status == status)

        by_component = {}
        for v in current:
            by_component[v.component] = by_component.get(v.component, 0) + 1

        return {
            "total_vitals": len(current),
            "by_status": by_status,
            "by_component": by_component,
            "total_snapshots": len(self._snapshots),
            "registered_providers": len(self._providers),
        }

    # Event registration
    def on_status_change(
        self,
        callback: Callable[[Vital, VitalStatus, VitalStatus], None],
    ) -> None:
        """Register callback for vital status changes."""
        self._on_status_change.append(callback)

    def on_critical(self, callback: Callable[[Vital], None]) -> None:
        """Register callback for critical vitals."""
        self._on_critical.append(callback)

    def _make_key(self, name: str, agent_id: Optional[UUID]) -> str:
        """Create a unique key for a vital."""
        if agent_id:
            return f"{name}:{agent_id}"
        return name


# Global vitals monitor
_vitals_monitor: Optional[VitalsMonitor] = None


def get_vitals_monitor() -> VitalsMonitor:
    """Get the global vitals monitor instance."""
    global _vitals_monitor
    if _vitals_monitor is None:
        _vitals_monitor = VitalsMonitor()
    return _vitals_monitor
