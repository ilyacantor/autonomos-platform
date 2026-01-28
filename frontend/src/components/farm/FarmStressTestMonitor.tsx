/**
 * FARM Stress Test Monitor
 *
 * Real-time monitoring dashboard for FARM stress test execution.
 * Displays:
 * - Active stress test status
 * - Fleet ingestion metrics
 * - Workflow execution progress
 * - Chaos injection/recovery tracking
 * - FARM expectations validation
 *
 * Uses the following reusable hooks:
 * - useStatusColors: For consistent status color mapping
 *
 * Note: This component uses custom polling logic with dynamic intervals
 * based on activity level, so it doesn't use usePolledData directly.
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Activity,
  CheckCircle,
  AlertCircle,
  Clock,
  Zap,
  Users,
  GitBranch,
  Shield,
  DollarSign,
  RefreshCw,
  Wifi,
  WifiOff,
  TrendingUp,
  AlertTriangle,
  Target,
  Play,
  Pause,
} from 'lucide-react';

import FleetStatusPanel from './FleetStatusPanel';
import WorkflowExecutionGrid from './WorkflowExecutionGrid';
import ChaosMonitorPanel from './ChaosMonitorPanel';
import FarmExpectationsPanel from './FarmExpectationsPanel';
import { useStatusColors } from '../../hooks/useStatusColors';

// Types
interface DashboardData {
  timestamp: string;
  tenant_id: string;
  agents: {
    total_registered: number;
    active: number;
    inactive: number;
    by_status: Record<string, number>;
    by_type: Record<string, number>;
    by_trust_tier: Record<string, number>;
  };
  workflows: {
    active_workflows: number;
    completed_24h: number;
    failed_24h: number;
    completion_rate: number;
    avg_duration_ms: number;
    throughput_per_min: number;
  };
  chaos: {
    events_triggered: number;
    events_recovered: number;
    events_failed: number;
    recovery_rate: number;
    by_type: Record<string, number>;
  };
  costs: {
    today_usd: number;
    week_usd: number;
    month_usd: number;
    tokens_today: number;
    budget_remaining_usd: number | null;
    budget_utilization: number;
  };
  governance: {
    policies_active: number;
    policy_violations_24h: number;
    pending_approvals: number;
    approvals_auto_approved: number;
    approvals_escalated: number;
  };
  vitals: {
    cpu_usage: number | null;
    memory_usage: number | null;
    workflows_active: number;
    throughput_tps: number;
    chaos_recovery_rate: number;
    status: 'healthy' | 'warning' | 'critical';
  };
  simulation_active: boolean;
  simulation_scenario_id: string | null;
}

interface ScenarioResult {
  scenario_id: string;
  status: string;
  verdict: 'PASS' | 'DEGRADED' | 'FAIL' | 'PENDING';
  completion_rate: number;
  chaos_recovery_rate: number;
  workflows_completed: number;
  workflows_failed: number;
  total_tasks: number;
  tasks_completed: number;
  tasks_failed: number;
  chaos_events_total: number;
  chaos_events_recovered: number;
  validation: Record<string, any>;
  analysis: Record<string, any>;
  total_cost_usd: number;
}

interface FarmEvent {
  type: string;
  timestamp: string;
  data: Record<string, any>;
}

const POLL_INTERVAL_ACTIVE = 2000;
const POLL_INTERVAL_IDLE = 10000;

export default function FarmStressTestMonitor() {
  // State
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [scenarioResult, setScenarioResult] = useState<ScenarioResult | null>(null);
  const [events, setEvents] = useState<FarmEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pollInterval, setPollInterval] = useState(POLL_INTERVAL_IDLE);

  const eventSourceRef = useRef<EventSource | null>(null);

  // Use the reusable hook for consistent status colors
  const { getHealthStatusColor } = useStatusColors();

  // Fetch dashboard data
  const fetchDashboard = useCallback(async () => {
    try {
      const response = await fetch('/api/v1/aoa/dashboard', {
        headers: { 'X-Tenant-ID': 'default' },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data: DashboardData = await response.json();
      setDashboard(data);
      setError(null);

      // Adjust poll interval based on activity
      if (data.simulation_active || data.workflows.active_workflows > 0) {
        setPollInterval(POLL_INTERVAL_ACTIVE);
      } else {
        setPollInterval(POLL_INTERVAL_IDLE);
      }

      // Fetch scenario result if active
      if (data.simulation_scenario_id) {
        fetchScenarioResult(data.simulation_scenario_id);
      }
    } catch (err) {
      console.error('Dashboard fetch error:', err);
      setError('Failed to connect to AOA dashboard');
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch scenario result
  const fetchScenarioResult = async (scenarioId: string) => {
    try {
      const response = await fetch(`/api/v1/stress-test/scenario/${scenarioId}`);
      if (response.ok) {
        const data: ScenarioResult = await response.json();
        setScenarioResult(data);
      }
    } catch (err) {
      console.error('Scenario fetch error:', err);
    }
  };

  // Polling effect
  useEffect(() => {
    fetchDashboard();
    const interval = setInterval(fetchDashboard, pollInterval);
    return () => clearInterval(interval);
  }, [fetchDashboard, pollInterval]);

  // SSE connection for events
  useEffect(() => {
    const connectSSE = () => {
      const eventSource = new EventSource('/api/v1/aoa/events');

      eventSource.onopen = () => {
        setConnected(true);
        console.log('SSE connected to AOA events');
      };

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setEvents((prev) => [
            { type: data.type, timestamp: new Date().toISOString(), data },
            ...prev.slice(0, 99),
          ]);

          // Trigger immediate refresh on important events
          if (['scenario.completed', 'workflow.completed', 'workflow.failed'].includes(data.type)) {
            fetchDashboard();
          }
        } catch (err) {
          console.error('SSE parse error:', err);
        }
      };

      eventSource.onerror = () => {
        setConnected(false);
        eventSource.close();
        // Reconnect after delay
        setTimeout(connectSSE, 5000);
      };

      eventSourceRef.current = eventSource;
    };

    connectSSE();

    return () => {
      eventSourceRef.current?.close();
    };
  }, [fetchDashboard]);

  // Render loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <RefreshCw className="w-8 h-8 text-cyan-500 animate-spin" />
        <span className="ml-3 text-gray-400">Connecting to AOA...</span>
      </div>
    );
  }

  // Calculate verdict color (specific to stress test verdicts)
  const getVerdictColor = (verdict: string) => {
    switch (verdict) {
      case 'PASS':
        return 'bg-green-500';
      case 'DEGRADED':
        return 'bg-yellow-500';
      case 'FAIL':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  // Note: getHealthStatusColor from useStatusColors is used instead of a local getStatusColor
  // This provides consistent status color mapping across the application

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 bg-gradient-to-br from-orange-500 to-red-600 rounded-xl flex items-center justify-center shadow-lg shadow-orange-500/20">
            <Target className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">FARM Stress Test Monitor</h1>
            <p className="text-gray-400 text-sm">
              Real-time monitoring of stress test execution and chaos recovery
            </p>
          </div>
        </div>

        {/* Connection Status */}
        <div className="flex items-center gap-4">
          <div
            className={`flex items-center gap-2 px-3 py-1.5 rounded-full ${
              connected ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
            }`}
          >
            {connected ? <Wifi className="w-4 h-4" /> : <WifiOff className="w-4 h-4" />}
            <span className="text-sm">{connected ? 'Connected' : 'Disconnected'}</span>
          </div>

          {dashboard?.simulation_active && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-purple-500/20 text-purple-400">
              <Play className="w-4 h-4" />
              <span className="text-sm">Simulation Active</span>
            </div>
          )}
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-4 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-red-400" />
          <span className="text-red-400">{error}</span>
          <button
            onClick={fetchDashboard}
            className="ml-auto text-sm text-red-400 hover:text-red-300"
          >
            Retry
          </button>
        </div>
      )}

      {/* Verdict Banner (if scenario active) */}
      {scenarioResult && scenarioResult.verdict !== 'PENDING' && (
        <div
          className={`rounded-lg p-4 ${
            scenarioResult.verdict === 'PASS'
              ? 'bg-green-500/20 border border-green-500/50'
              : scenarioResult.verdict === 'DEGRADED'
              ? 'bg-yellow-500/20 border border-yellow-500/50'
              : 'bg-red-500/20 border border-red-500/50'
          }`}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 rounded-full ${getVerdictColor(scenarioResult.verdict)} flex items-center justify-center`}>
                {scenarioResult.verdict === 'PASS' ? (
                  <CheckCircle className="w-6 h-6 text-white" />
                ) : scenarioResult.verdict === 'DEGRADED' ? (
                  <AlertTriangle className="w-6 h-6 text-white" />
                ) : (
                  <AlertCircle className="w-6 h-6 text-white" />
                )}
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white">
                  Stress Test {scenarioResult.verdict}
                </h3>
                <p className="text-gray-400 text-sm">
                  {scenarioResult.analysis?.summary || `Scenario ${scenarioResult.scenario_id}`}
                </p>
              </div>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold text-white">
                {(scenarioResult.completion_rate * 100).toFixed(1)}%
              </div>
              <div className="text-gray-400 text-sm">Completion Rate</div>
            </div>
          </div>
        </div>
      )}

      {/* KPI Cards Row */}
      <div className="grid grid-cols-6 gap-4">
        <KPICard
          icon={Users}
          label="Active Agents"
          value={dashboard?.agents.active ?? 0}
          total={dashboard?.agents.total_registered ?? 0}
          color="cyan"
        />
        <KPICard
          icon={GitBranch}
          label="Active Workflows"
          value={dashboard?.workflows.active_workflows ?? 0}
          color="purple"
        />
        <KPICard
          icon={CheckCircle}
          label="Completion Rate"
          value={`${((dashboard?.workflows.completion_rate ?? 0) * 100).toFixed(1)}%`}
          color={dashboard?.workflows.completion_rate >= 0.95 ? 'green' : dashboard?.workflows.completion_rate >= 0.8 ? 'yellow' : 'red'}
        />
        <KPICard
          icon={Zap}
          label="Chaos Recovery"
          value={`${((dashboard?.chaos.recovery_rate ?? 0) * 100).toFixed(1)}%`}
          color={dashboard?.chaos.recovery_rate >= 0.8 ? 'green' : dashboard?.chaos.recovery_rate >= 0.5 ? 'yellow' : 'red'}
        />
        <KPICard
          icon={DollarSign}
          label="Cost Today"
          value={`$${(dashboard?.costs.today_usd ?? 0).toFixed(2)}`}
          color="blue"
        />
        <KPICard
          icon={Shield}
          label="Pending Approvals"
          value={dashboard?.governance.pending_approvals ?? 0}
          color={dashboard?.governance.pending_approvals > 0 ? 'orange' : 'gray'}
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-2 gap-6">
        {/* Fleet Status */}
        <FleetStatusPanel
          agents={dashboard?.agents}
          loading={loading}
        />

        {/* Workflow Execution */}
        <WorkflowExecutionGrid
          workflows={dashboard?.workflows}
          scenarioResult={scenarioResult}
          loading={loading}
        />
      </div>

      {/* Chaos & Expectations Row */}
      <div className="grid grid-cols-2 gap-6">
        {/* Chaos Monitor */}
        <ChaosMonitorPanel
          chaos={dashboard?.chaos}
          events={events.filter((e) => e.type.startsWith('chaos.'))}
          loading={loading}
        />

        {/* FARM Expectations */}
        <FarmExpectationsPanel
          scenarioResult={scenarioResult}
          loading={loading}
        />
      </div>

      {/* Event Log */}
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            <Activity className="w-5 h-5 text-cyan-400" />
            Recent Events
          </h3>
          <span className="text-sm text-gray-500">{events.length} events</span>
        </div>

        <div className="space-y-2 max-h-60 overflow-y-auto">
          {events.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              No events yet. Events will appear when stress test starts.
            </div>
          ) : (
            events.slice(0, 20).map((event, idx) => (
              <EventRow key={idx} event={event} />
            ))
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="text-center py-4 text-xs text-slate-500">
        Dashboard refreshes every {pollInterval / 1000}s • Connected to AOA Simulation Harness
      </div>
    </div>
  );
}

// KPI Card Component
function KPICard({
  icon: Icon,
  label,
  value,
  total,
  color,
}: {
  icon: any;
  label: string;
  value: string | number;
  total?: number;
  color: string;
}) {
  const colorClasses: Record<string, string> = {
    cyan: 'from-cyan-500 to-blue-600 shadow-cyan-500/20',
    purple: 'from-purple-500 to-pink-600 shadow-purple-500/20',
    green: 'from-green-500 to-emerald-600 shadow-green-500/20',
    yellow: 'from-yellow-500 to-orange-600 shadow-yellow-500/20',
    red: 'from-red-500 to-rose-600 shadow-red-500/20',
    blue: 'from-blue-500 to-indigo-600 shadow-blue-500/20',
    orange: 'from-orange-500 to-red-600 shadow-orange-500/20',
    gray: 'from-gray-500 to-slate-600 shadow-gray-500/20',
  };

  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4">
      <div className="flex items-center gap-3">
        <div
          className={`w-10 h-10 bg-gradient-to-br ${colorClasses[color]} rounded-lg flex items-center justify-center shadow-lg`}
        >
          <Icon className="w-5 h-5 text-white" />
        </div>
        <div>
          <div className="text-xl font-bold text-white">
            {value}
            {total !== undefined && (
              <span className="text-gray-500 text-sm font-normal">/{total}</span>
            )}
          </div>
          <div className="text-xs text-gray-400">{label}</div>
        </div>
      </div>
    </div>
  );
}

// Event Row Component
function EventRow({ event }: { event: FarmEvent }) {
  const getEventIcon = (type: string) => {
    if (type.startsWith('workflow.')) return GitBranch;
    if (type.startsWith('chaos.')) return Zap;
    if (type.startsWith('agent.')) return Users;
    if (type.startsWith('approval.')) return Shield;
    return Activity;
  };

  const getEventColor = (type: string) => {
    if (type.includes('completed') || type.includes('recovered') || type.includes('granted')) {
      return 'text-green-400';
    }
    if (type.includes('failed') || type.includes('rejected')) {
      return 'text-red-400';
    }
    if (type.includes('started') || type.includes('injected') || type.includes('requested')) {
      return 'text-yellow-400';
    }
    return 'text-gray-400';
  };

  const Icon = getEventIcon(event.type);
  const time = new Date(event.timestamp).toLocaleTimeString();

  return (
    <div className="flex items-center gap-3 py-2 px-3 bg-slate-700/30 rounded-lg">
      <Icon className={`w-4 h-4 ${getEventColor(event.type)}`} />
      <span className="text-gray-500 text-xs w-20">{time}</span>
      <span className="text-gray-300 text-sm flex-1">{event.type}</span>
      {event.data.task_id && (
        <span className="text-gray-500 text-xs">Task: {event.data.task_id.slice(0, 8)}...</span>
      )}
      {event.data.workflow_id && (
        <span className="text-gray-500 text-xs">WF: {event.data.workflow_id.slice(0, 8)}...</span>
      )}
    </div>
  );
}
