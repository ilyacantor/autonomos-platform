"""
AOA Simulation Harness

Provides synthetic agent activity generation for:
- UI dashboard KPI visualization
- FARM stress test integration
- Platform load testing

This module bridges FARM-generated test data with AOA's
observability, governance, and coordination modules.
"""

from app.agentic.simulation.executor import (
    SimulationExecutor,
    ExecutionConfig,
    ExecutionResult,
    get_simulation_executor,
)
from app.agentic.simulation.metrics_bridge import (
    MetricsBridge,
    get_metrics_bridge,
)
from app.agentic.simulation.event_emitter import (
    EventEmitter,
    get_event_emitter,
)

__all__ = [
    # Executor
    'SimulationExecutor',
    'ExecutionConfig',
    'ExecutionResult',
    'get_simulation_executor',
    # Metrics Bridge
    'MetricsBridge',
    'get_metrics_bridge',
    # Event Emitter
    'EventEmitter',
    'get_event_emitter',
]
