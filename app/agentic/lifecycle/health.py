"""
Agent Health Monitor

Monitors agent health and manages health checks.
Implements Agent Lifecycle: Agent health monitoring from RACI.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID

from .models import HealthCheck, HealthStatus

logger = logging.getLogger(__name__)


@dataclass
class HealthCheckResult:
    """Result of a health check execution."""
    check_id: UUID
    agent_id: UUID
    status: HealthStatus
    response_time_ms: Optional[int] = None
    status_code: Optional[int] = None
    error: Optional[str] = None
    checked_at: datetime = field(default_factory=datetime.utcnow)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "check_id": str(self.check_id),
            "agent_id": str(self.agent_id),
            "status": self.status.value,
            "response_time_ms": self.response_time_ms,
            "status_code": self.status_code,
            "error": self.error,
            "checked_at": self.checked_at.isoformat(),
            "details": self.details,
        }


class HealthMonitor:
    """
    Agent Health Monitor.

    Manages health checks and monitors agent health:
    - Register health checks for agents
    - Execute health checks periodically
    - Track health history
    - Alert on health changes
    """

    def __init__(self):
        """Initialize the health monitor."""
        # Health check registry
        self._checks: Dict[UUID, HealthCheck] = {}
        self._by_agent: Dict[UUID, List[UUID]] = {}

        # Health history
        self._history: Dict[UUID, List[HealthCheckResult]] = {}
        self._max_history_per_agent = 100

        # Current status
        self._current_status: Dict[UUID, HealthStatus] = {}

        # Callbacks
        self._on_health_change: List[Callable[[UUID, HealthStatus, HealthStatus], None]] = []
        self._on_unhealthy: List[Callable[[UUID, HealthCheckResult], None]] = []

        # Background task
        self._running = False
        self._check_task: Optional[asyncio.Task] = None

    def register_check(self, check: HealthCheck) -> HealthCheck:
        """
        Register a health check for an agent.

        Args:
            check: Health check configuration

        Returns:
            Registered health check
        """
        self._checks[check.id] = check

        if check.agent_id not in self._by_agent:
            self._by_agent[check.agent_id] = []
        self._by_agent[check.agent_id].append(check.id)

        logger.info(f"Health check registered: {check.id} for agent {check.agent_id}")
        return check

    def unregister_check(self, check_id: UUID) -> Optional[HealthCheck]:
        """
        Unregister a health check.

        Args:
            check_id: Check to unregister

        Returns:
            Removed check or None
        """
        check = self._checks.pop(check_id, None)
        if not check:
            return None

        if check.agent_id in self._by_agent:
            self._by_agent[check.agent_id] = [
                cid for cid in self._by_agent[check.agent_id]
                if cid != check_id
            ]

        logger.info(f"Health check unregistered: {check_id}")
        return check

    def get_check(self, check_id: UUID) -> Optional[HealthCheck]:
        """Get a health check by ID."""
        return self._checks.get(check_id)

    def get_agent_checks(self, agent_id: UUID) -> List[HealthCheck]:
        """Get all health checks for an agent."""
        check_ids = self._by_agent.get(agent_id, [])
        return [self._checks[cid] for cid in check_ids if cid in self._checks]

    def get_agent_status(self, agent_id: UUID) -> HealthStatus:
        """Get current health status for an agent."""
        return self._current_status.get(agent_id, HealthStatus.UNKNOWN)

    def get_agent_history(
        self,
        agent_id: UUID,
        limit: int = 50,
        since: Optional[datetime] = None,
    ) -> List[HealthCheckResult]:
        """
        Get health check history for an agent.

        Args:
            agent_id: Agent ID
            limit: Maximum results
            since: Only results after this time

        Returns:
            List of health check results
        """
        history = self._history.get(agent_id, [])

        if since:
            history = [r for r in history if r.checked_at >= since]

        # Most recent first
        history.sort(key=lambda r: r.checked_at, reverse=True)
        return history[:limit]

    async def check_agent(self, agent_id: UUID) -> HealthStatus:
        """
        Run all health checks for an agent.

        Args:
            agent_id: Agent to check

        Returns:
            Aggregated health status
        """
        checks = self.get_agent_checks(agent_id)
        if not checks:
            return HealthStatus.UNKNOWN

        results = []
        for check in checks:
            if not check.enabled:
                continue
            result = await self._execute_check(check)
            results.append(result)

        if not results:
            return HealthStatus.UNKNOWN

        # Aggregate status - worst status wins
        status = self._aggregate_status(results)
        self._update_agent_status(agent_id, status)

        return status

    async def check_all(self) -> Dict[UUID, HealthStatus]:
        """
        Run health checks for all registered agents.

        Returns:
            Map of agent ID to health status
        """
        results = {}

        for agent_id in self._by_agent:
            try:
                status = await self.check_agent(agent_id)
                results[agent_id] = status
            except Exception as e:
                logger.error(f"Health check failed for agent {agent_id}: {e}")
                results[agent_id] = HealthStatus.UNKNOWN

        return results

    async def start(self) -> None:
        """Start the background health check loop."""
        if self._running:
            return

        self._running = True
        self._check_task = asyncio.create_task(self._check_loop())
        logger.info("Health monitor started")

    async def stop(self) -> None:
        """Stop the background health check loop."""
        self._running = False

        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass
            self._check_task = None

        logger.info("Health monitor stopped")

    def on_health_change(
        self,
        callback: Callable[[UUID, HealthStatus, HealthStatus], None]
    ) -> None:
        """Register callback for health status changes."""
        self._on_health_change.append(callback)

    def on_unhealthy(
        self,
        callback: Callable[[UUID, HealthCheckResult], None]
    ) -> None:
        """Register callback for unhealthy status."""
        self._on_unhealthy.append(callback)

    def get_stats(self) -> Dict[str, Any]:
        """Get health monitor statistics."""
        status_counts = {}
        for status in self._current_status.values():
            status_counts[status.value] = status_counts.get(status.value, 0) + 1

        return {
            "total_checks": len(self._checks),
            "total_agents": len(self._by_agent),
            "status_distribution": status_counts,
            "running": self._running,
        }

    async def _check_loop(self) -> None:
        """Background health check loop."""
        while self._running:
            try:
                # Find checks due to run
                now = datetime.utcnow()

                for check in self._checks.values():
                    if not check.enabled:
                        continue

                    # Check if due
                    if check.last_check_at:
                        next_check = check.last_check_at + timedelta(seconds=check.interval_seconds)
                        if now < next_check:
                            continue

                    # Execute check
                    await self._execute_check(check)

                # Sleep before next iteration
                await asyncio.sleep(1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(5)

    async def _execute_check(self, check: HealthCheck) -> HealthCheckResult:
        """Execute a single health check."""
        start_time = datetime.utcnow()

        try:
            if check.check_type == "http":
                result = await self._http_check(check)
            elif check.check_type == "tcp":
                result = await self._tcp_check(check)
            elif check.check_type == "heartbeat":
                result = await self._heartbeat_check(check)
            else:
                result = HealthCheckResult(
                    check_id=check.id,
                    agent_id=check.agent_id,
                    status=HealthStatus.UNKNOWN,
                    error=f"Unknown check type: {check.check_type}",
                )

        except Exception as e:
            result = HealthCheckResult(
                check_id=check.id,
                agent_id=check.agent_id,
                status=HealthStatus.UNHEALTHY,
                error=str(e),
            )

        # Calculate response time
        result.response_time_ms = int(
            (datetime.utcnow() - start_time).total_seconds() * 1000
        )

        # Update check state
        check.last_check_at = datetime.utcnow()
        check.last_status = result.status

        if result.status == HealthStatus.HEALTHY:
            check.consecutive_successes += 1
            check.consecutive_failures = 0
        else:
            check.consecutive_failures += 1
            check.consecutive_successes = 0

        # Store in history
        self._add_to_history(check.agent_id, result)

        # Handle unhealthy
        if result.status == HealthStatus.UNHEALTHY:
            for callback in self._on_unhealthy:
                try:
                    callback(check.agent_id, result)
                except Exception as e:
                    logger.error(f"Unhealthy callback error: {e}")

        return result

    async def _http_check(self, check: HealthCheck) -> HealthCheckResult:
        """Perform HTTP health check."""
        if not check.endpoint:
            return HealthCheckResult(
                check_id=check.id,
                agent_id=check.agent_id,
                status=HealthStatus.UNKNOWN,
                error="No endpoint configured",
            )

        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    check.endpoint,
                    timeout=aiohttp.ClientTimeout(total=check.timeout_seconds),
                ) as response:
                    status_code = response.status
                    body = await response.text()

                    # Check status code
                    if status_code not in check.expected_status_codes:
                        return HealthCheckResult(
                            check_id=check.id,
                            agent_id=check.agent_id,
                            status=HealthStatus.UNHEALTHY,
                            status_code=status_code,
                            error=f"Unexpected status code: {status_code}",
                        )

                    # Check body content
                    if check.expected_body_contains:
                        if check.expected_body_contains not in body:
                            return HealthCheckResult(
                                check_id=check.id,
                                agent_id=check.agent_id,
                                status=HealthStatus.UNHEALTHY,
                                status_code=status_code,
                                error="Expected body content not found",
                            )

                    return HealthCheckResult(
                        check_id=check.id,
                        agent_id=check.agent_id,
                        status=HealthStatus.HEALTHY,
                        status_code=status_code,
                    )

        except asyncio.TimeoutError:
            return HealthCheckResult(
                check_id=check.id,
                agent_id=check.agent_id,
                status=HealthStatus.UNHEALTHY,
                error="Timeout",
            )
        except Exception as e:
            return HealthCheckResult(
                check_id=check.id,
                agent_id=check.agent_id,
                status=HealthStatus.UNHEALTHY,
                error=str(e),
            )

    async def _tcp_check(self, check: HealthCheck) -> HealthCheckResult:
        """Perform TCP health check."""
        if not check.endpoint or not check.port:
            return HealthCheckResult(
                check_id=check.id,
                agent_id=check.agent_id,
                status=HealthStatus.UNKNOWN,
                error="No endpoint or port configured",
            )

        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(check.endpoint, check.port),
                timeout=check.timeout_seconds,
            )
            writer.close()
            await writer.wait_closed()

            return HealthCheckResult(
                check_id=check.id,
                agent_id=check.agent_id,
                status=HealthStatus.HEALTHY,
            )

        except asyncio.TimeoutError:
            return HealthCheckResult(
                check_id=check.id,
                agent_id=check.agent_id,
                status=HealthStatus.UNHEALTHY,
                error="Timeout",
            )
        except Exception as e:
            return HealthCheckResult(
                check_id=check.id,
                agent_id=check.agent_id,
                status=HealthStatus.UNHEALTHY,
                error=str(e),
            )

    async def _heartbeat_check(self, check: HealthCheck) -> HealthCheckResult:
        """Check heartbeat (passive health check)."""
        # Heartbeat checks rely on agents reporting in
        # If last check was recent, agent is healthy
        if check.last_check_at:
            age = datetime.utcnow() - check.last_check_at
            if age.total_seconds() < check.interval_seconds * 2:
                return HealthCheckResult(
                    check_id=check.id,
                    agent_id=check.agent_id,
                    status=HealthStatus.HEALTHY,
                )

        return HealthCheckResult(
            check_id=check.id,
            agent_id=check.agent_id,
            status=HealthStatus.UNKNOWN,
            error="No recent heartbeat",
        )

    def record_heartbeat(self, agent_id: UUID) -> None:
        """Record a heartbeat from an agent."""
        checks = self.get_agent_checks(agent_id)
        for check in checks:
            if check.check_type == "heartbeat":
                check.last_check_at = datetime.utcnow()
                check.last_status = HealthStatus.HEALTHY
                check.consecutive_successes += 1
                check.consecutive_failures = 0

    def _aggregate_status(self, results: List[HealthCheckResult]) -> HealthStatus:
        """Aggregate multiple check results into a single status."""
        if not results:
            return HealthStatus.UNKNOWN

        # Priority: UNHEALTHY > DEGRADED > UNKNOWN > HEALTHY
        has_unhealthy = any(r.status == HealthStatus.UNHEALTHY for r in results)
        has_degraded = any(r.status == HealthStatus.DEGRADED for r in results)
        has_unknown = any(r.status == HealthStatus.UNKNOWN for r in results)

        if has_unhealthy:
            return HealthStatus.UNHEALTHY
        if has_degraded:
            return HealthStatus.DEGRADED
        if has_unknown:
            return HealthStatus.UNKNOWN
        return HealthStatus.HEALTHY

    def _update_agent_status(self, agent_id: UUID, new_status: HealthStatus) -> None:
        """Update agent status and notify on change."""
        old_status = self._current_status.get(agent_id, HealthStatus.UNKNOWN)
        self._current_status[agent_id] = new_status

        if old_status != new_status:
            logger.info(f"Agent {agent_id} health changed: {old_status.value} -> {new_status.value}")
            for callback in self._on_health_change:
                try:
                    callback(agent_id, old_status, new_status)
                except Exception as e:
                    logger.error(f"Health change callback error: {e}")

    def _add_to_history(self, agent_id: UUID, result: HealthCheckResult) -> None:
        """Add result to history."""
        if agent_id not in self._history:
            self._history[agent_id] = []

        self._history[agent_id].append(result)

        # Trim history
        if len(self._history[agent_id]) > self._max_history_per_agent:
            self._history[agent_id] = self._history[agent_id][-self._max_history_per_agent:]


# Global instance
_health_monitor: Optional[HealthMonitor] = None


def get_health_monitor() -> HealthMonitor:
    """Get the global health monitor instance."""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = HealthMonitor()
    return _health_monitor
