/**
 * Orchestration Dashboard Page
 *
 * Unified dashboard for Agentic Orchestration featuring tabbed interface:
 * - Overview: Real-time vitals and KPI summary
 * - Agents: Fleet management and agent performance
 * - Workflows: Execution tracking and progress
 * - Resilience: Chaos testing and recovery metrics
 * - Governance: Approvals, policies, and budget
 * - Stress Test: Full FARM stress test monitoring
 *
 * Integrates AOA functions with FARM stress testing capabilities.
 */

import { useState, useEffect, useCallback } from 'react';
import {
  Activity,
  Users,
  GitBranch,
  Zap,
  Shield,
  Target,
} from 'lucide-react';
import AOAStatusCard from './AOAStatusCard';
import AOAFunctionsPanel from './AOAFunctionsPanel';
import AgentPerformanceMonitor from './AgentPerformanceMonitor';
import AutonomyModeToggle from './AutonomyModeToggle';

// Import FARM components
import FleetStatusPanel from '../farm/FleetStatusPanel';
import WorkflowExecutionGrid from '../farm/WorkflowExecutionGrid';
import ChaosMonitorPanel from '../farm/ChaosMonitorPanel';
import FarmExpectationsPanel from '../farm/FarmExpectationsPanel';

// Tab types
type TabId = 'overview' | 'agents' | 'workflows' | 'resilience' | 'governance' | 'stress-test';

interface Tab {
  id: TabId;
  label: string;
  icon: any;
  description: string;
}

const TABS: Tab[] = [
  { id: 'overview', label: 'Overview', icon: Activity, description: 'Real-time vitals and KPIs' },
  { id: 'agents', label: 'Agents', icon: Users, description: 'Fleet management and performance' },
  { id: 'workflows', label: 'Workflows', icon: GitBranch, description: 'Execution tracking' },
  { id: 'resilience', label: 'Resilience', icon: Zap, description: 'Chaos testing and recovery' },
  { id: 'governance', label: 'Governance', icon: Shield, description: 'Approvals and policies' },
  { id: 'stress-test', label: 'Stress Test', icon: Target, description: 'FARM stress testing' },
];

// Dashboard data types
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

export default function OrchestrationDashboard() {
  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [scenarioResult, setScenarioResult] = useState<ScenarioResult | null>(null);
  const [events, setEvents] = useState<FarmEvent[]>([]);
  const [loading, setLoading] = useState(true);

  // Fetch dashboard data
  const fetchDashboard = useCallback(async () => {
    try {
      const response = await fetch('/api/v1/aoa/dashboard', {
        headers: { 'X-Tenant-ID': 'default' },
      });

      if (response.ok) {
        const data: DashboardData = await response.json();
        setDashboard(data);

        // Fetch scenario result if active
        if (data.simulation_scenario_id) {
          const scenarioResponse = await fetch(`/api/v1/stress-test/scenario/${data.simulation_scenario_id}`);
          if (scenarioResponse.ok) {
            const scenarioData: ScenarioResult = await scenarioResponse.json();
            setScenarioResult(scenarioData);
          }
        }
      }
    } catch (err) {
      console.error('Dashboard fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Polling effect
  useEffect(() => {
    fetchDashboard();
    const interval = setInterval(fetchDashboard, 5000);
    return () => clearInterval(interval);
  }, [fetchDashboard]);

  // SSE connection for events
  useEffect(() => {
    let eventSource: EventSource | null = null;

    const connectSSE = () => {
      eventSource = new EventSource('/api/v1/aoa/events');

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setEvents((prev) => [
            { type: data.type, timestamp: new Date().toISOString(), data },
            ...prev.slice(0, 99),
          ]);
        } catch (err) {
          console.error('SSE parse error:', err);
        }
      };

      eventSource.onerror = () => {
        eventSource?.close();
        setTimeout(connectSSE, 5000);
      };
    };

    connectSSE();

    return () => {
      eventSource?.close();
    };
  }, []);

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-xl flex items-center justify-center shadow-lg shadow-cyan-500/20">
            <Activity className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Agentic Orchestration</h1>
            <p className="text-gray-400 text-sm">
              Real-time monitoring and control of autonomous agent operations
            </p>
          </div>
        </div>

        <AutonomyModeToggle />
      </div>

      {/* Tab Navigation */}
      <div className="flex items-center gap-1 bg-slate-800/50 rounded-xl p-1.5 border border-slate-700/50">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;

          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-lg transition-all ${
                isActive
                  ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-slate-700/50'
              }`}
              title={tab.description}
            >
              <Icon className="w-4 h-4" />
              <span className="font-medium text-sm">{tab.label}</span>
              {tab.id === 'stress-test' && dashboard?.simulation_active && (
                <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              )}
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      <div className="min-h-[600px]">
        {activeTab === 'overview' && (
          <OverviewTab dashboard={dashboard} loading={loading} />
        )}

        {activeTab === 'agents' && (
          <AgentsTab dashboard={dashboard} loading={loading} />
        )}

        {activeTab === 'workflows' && (
          <WorkflowsTab
            dashboard={dashboard}
            scenarioResult={scenarioResult}
            loading={loading}
          />
        )}

        {activeTab === 'resilience' && (
          <ResilienceTab
            dashboard={dashboard}
            events={events}
            loading={loading}
          />
        )}

        {activeTab === 'governance' && (
          <GovernanceTab dashboard={dashboard} loading={loading} />
        )}

        {activeTab === 'stress-test' && (
          <StressTestTab
            dashboard={dashboard}
            scenarioResult={scenarioResult}
            events={events}
            loading={loading}
          />
        )}
      </div>

      {/* Footer */}
      <div className="text-center py-4 text-xs text-slate-500">
        Dashboard data refreshes automatically. All metrics are derived from real agent execution data.
      </div>
    </div>
  );
}

// ============================================================================
// Tab Components
// ============================================================================

function OverviewTab({ dashboard, loading }: { dashboard: DashboardData | null; loading: boolean }) {
  return (
    <div className="space-y-6">
      {/* AOA Status Card */}
      <AOAStatusCard />

      {/* Quick Stats Grid */}
      <div className="grid grid-cols-4 gap-4">
        <QuickStatCard
          label="Active Agents"
          value={dashboard?.agents.active ?? 0}
          total={dashboard?.agents.total_registered}
          icon={Users}
          color="cyan"
        />
        <QuickStatCard
          label="Active Workflows"
          value={dashboard?.workflows.active_workflows ?? 0}
          icon={GitBranch}
          color="purple"
        />
        <QuickStatCard
          label="Chaos Recovery"
          value={`${((dashboard?.chaos.recovery_rate ?? 0) * 100).toFixed(0)}%`}
          icon={Zap}
          color={(dashboard?.chaos.recovery_rate ?? 0) >= 0.8 ? 'green' : 'yellow'}
        />
        <QuickStatCard
          label="Pending Approvals"
          value={dashboard?.governance.pending_approvals ?? 0}
          icon={Shield}
          color={(dashboard?.governance.pending_approvals ?? 0) > 0 ? 'orange' : 'gray'}
        />
      </div>

      {/* AOA Functions Panel */}
      <AOAFunctionsPanel />
    </div>
  );
}

function AgentsTab({ dashboard, loading }: { dashboard: DashboardData | null; loading: boolean }) {
  return (
    <div className="space-y-6">
      {/* Fleet Status Panel */}
      <FleetStatusPanel agents={dashboard?.agents} loading={loading} />

      {/* Agent Performance Monitor */}
      <AgentPerformanceMonitor />
    </div>
  );
}

function WorkflowsTab({
  dashboard,
  scenarioResult,
  loading,
}: {
  dashboard: DashboardData | null;
  scenarioResult: ScenarioResult | null;
  loading: boolean;
}) {
  return (
    <div className="space-y-6">
      {/* Workflow Execution Grid */}
      <WorkflowExecutionGrid
        workflows={dashboard?.workflows}
        scenarioResult={scenarioResult}
        loading={loading}
      />

      {/* Workflow Stats */}
      <div className="grid grid-cols-3 gap-4">
        <StatCard
          label="Completed (24h)"
          value={dashboard?.workflows.completed_24h ?? 0}
          color="green"
        />
        <StatCard
          label="Failed (24h)"
          value={dashboard?.workflows.failed_24h ?? 0}
          color="red"
        />
        <StatCard
          label="Avg Duration"
          value={`${((dashboard?.workflows.avg_duration_ms ?? 0) / 1000).toFixed(1)}s`}
          color="blue"
        />
      </div>
    </div>
  );
}

function ResilienceTab({
  dashboard,
  events,
  loading,
}: {
  dashboard: DashboardData | null;
  events: FarmEvent[];
  loading: boolean;
}) {
  const chaosEvents = events.filter((e) => e.type.startsWith('chaos.'));

  return (
    <div className="space-y-6">
      {/* Chaos Monitor Panel */}
      <ChaosMonitorPanel
        chaos={dashboard?.chaos}
        events={chaosEvents}
        loading={loading}
      />

      {/* Resilience Summary */}
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Resilience Summary</h3>
        <div className="grid grid-cols-3 gap-6">
          <div>
            <div className="text-3xl font-bold text-cyan-400">
              {dashboard?.chaos.events_triggered ?? 0}
            </div>
            <div className="text-sm text-gray-500">Total Events Triggered</div>
          </div>
          <div>
            <div className="text-3xl font-bold text-green-400">
              {dashboard?.chaos.events_recovered ?? 0}
            </div>
            <div className="text-sm text-gray-500">Successfully Recovered</div>
          </div>
          <div>
            <div className="text-3xl font-bold text-red-400">
              {dashboard?.chaos.events_failed ?? 0}
            </div>
            <div className="text-sm text-gray-500">Failed to Recover</div>
          </div>
        </div>
      </div>
    </div>
  );
}

function GovernanceTab({ dashboard, loading }: { dashboard: DashboardData | null; loading: boolean }) {
  return (
    <div className="space-y-6">
      {/* Governance Overview */}
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
        <h3 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
          <Shield className="w-5 h-5 text-purple-400" />
          Governance Overview
        </h3>

        <div className="grid grid-cols-2 gap-6">
          {/* Approvals Section */}
          <div className="space-y-4">
            <h4 className="text-sm font-medium text-gray-400">Approvals</h4>
            <div className="space-y-3">
              <GovernanceMetric
                label="Pending Approvals"
                value={dashboard?.governance.pending_approvals ?? 0}
                color={(dashboard?.governance.pending_approvals ?? 0) > 0 ? 'orange' : 'green'}
              />
              <GovernanceMetric
                label="Auto-Approved"
                value={dashboard?.governance.approvals_auto_approved ?? 0}
                color="green"
              />
              <GovernanceMetric
                label="Escalated"
                value={dashboard?.governance.approvals_escalated ?? 0}
                color="yellow"
              />
            </div>
          </div>

          {/* Policies Section */}
          <div className="space-y-4">
            <h4 className="text-sm font-medium text-gray-400">Policies</h4>
            <div className="space-y-3">
              <GovernanceMetric
                label="Active Policies"
                value={dashboard?.governance.policies_active ?? 0}
                color="cyan"
              />
              <GovernanceMetric
                label="Violations (24h)"
                value={dashboard?.governance.policy_violations_24h ?? 0}
                color={(dashboard?.governance.policy_violations_24h ?? 0) > 0 ? 'red' : 'green'}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Budget Section */}
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
        <h3 className="text-lg font-semibold text-white mb-6">Budget & Costs</h3>

        <div className="grid grid-cols-4 gap-4">
          <CostCard
            label="Today"
            value={dashboard?.costs.today_usd ?? 0}
          />
          <CostCard
            label="This Week"
            value={dashboard?.costs.week_usd ?? 0}
          />
          <CostCard
            label="This Month"
            value={dashboard?.costs.month_usd ?? 0}
          />
          <CostCard
            label="Budget Remaining"
            value={dashboard?.costs.budget_remaining_usd}
            highlight
          />
        </div>

        {/* Budget Utilization Bar */}
        {(dashboard?.costs.budget_utilization ?? 0) > 0 && (
          <div className="mt-6">
            <div className="flex items-center justify-between mb-2 text-sm">
              <span className="text-gray-400">Budget Utilization</span>
              <span className="text-cyan-400 font-medium">
                {((dashboard?.costs.budget_utilization ?? 0) * 100).toFixed(1)}%
              </span>
            </div>
            <div className="w-full h-3 bg-slate-700 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all duration-500 ${
                  (dashboard?.costs.budget_utilization ?? 0) > 0.9
                    ? 'bg-red-500'
                    : (dashboard?.costs.budget_utilization ?? 0) > 0.7
                    ? 'bg-yellow-500'
                    : 'bg-green-500'
                }`}
                style={{ width: `${(dashboard?.costs.budget_utilization ?? 0) * 100}%` }}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function StressTestTab({
  dashboard,
  scenarioResult,
  events,
  loading,
}: {
  dashboard: DashboardData | null;
  scenarioResult: ScenarioResult | null;
  events: FarmEvent[];
  loading: boolean;
}) {
  const chaosEvents = events.filter((e) => e.type.startsWith('chaos.'));

  return (
    <div className="space-y-6">
      {/* Stress Test Status Banner */}
      {dashboard?.simulation_active ? (
        <div className="bg-purple-500/20 border border-purple-500/50 rounded-lg p-4 flex items-center gap-3">
          <div className="w-3 h-3 bg-purple-500 rounded-full animate-pulse" />
          <span className="text-purple-400 font-medium">Stress Test Running</span>
          {dashboard.simulation_scenario_id && (
            <span className="text-gray-500 text-sm ml-auto">
              Scenario: {dashboard.simulation_scenario_id}
            </span>
          )}
        </div>
      ) : (
        <div className="bg-slate-700/30 border border-slate-600/50 rounded-lg p-4 flex items-center gap-3">
          <div className="w-3 h-3 bg-gray-500 rounded-full" />
          <span className="text-gray-400">No active stress test</span>
        </div>
      )}

      {/* Main Grid */}
      <div className="grid grid-cols-2 gap-6">
        {/* Fleet Status */}
        <FleetStatusPanel agents={dashboard?.agents} loading={loading} />

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
          events={chaosEvents}
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

        <div className="space-y-2 max-h-48 overflow-y-auto">
          {events.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              No events yet. Events will appear when stress test starts.
            </div>
          ) : (
            events.slice(0, 15).map((event, idx) => (
              <EventRow key={idx} event={event} />
            ))
          )}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Helper Components
// ============================================================================

function QuickStatCard({
  label,
  value,
  total,
  icon: Icon,
  color,
}: {
  label: string;
  value: string | number;
  total?: number;
  icon: any;
  color: string;
}) {
  const colorClasses: Record<string, string> = {
    cyan: 'from-cyan-500 to-blue-600 shadow-cyan-500/20',
    purple: 'from-purple-500 to-pink-600 shadow-purple-500/20',
    green: 'from-green-500 to-emerald-600 shadow-green-500/20',
    yellow: 'from-yellow-500 to-orange-600 shadow-yellow-500/20',
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

function StatCard({
  label,
  value,
  color,
}: {
  label: string;
  value: string | number;
  color: string;
}) {
  const colorClasses: Record<string, string> = {
    green: 'text-green-400',
    red: 'text-red-400',
    blue: 'text-blue-400',
  };

  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4 text-center">
      <div className={`text-2xl font-bold ${colorClasses[color]}`}>{value}</div>
      <div className="text-sm text-gray-500">{label}</div>
    </div>
  );
}

function GovernanceMetric({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: string;
}) {
  const colorClasses: Record<string, string> = {
    green: 'bg-green-500/20 text-green-400',
    orange: 'bg-orange-500/20 text-orange-400',
    yellow: 'bg-yellow-500/20 text-yellow-400',
    red: 'bg-red-500/20 text-red-400',
    cyan: 'bg-cyan-500/20 text-cyan-400',
  };

  return (
    <div className="flex items-center justify-between p-3 bg-slate-700/30 rounded-lg">
      <span className="text-sm text-gray-300">{label}</span>
      <span className={`px-2 py-1 rounded text-sm font-medium ${colorClasses[color]}`}>
        {value}
      </span>
    </div>
  );
}

function CostCard({
  label,
  value,
  highlight,
}: {
  label: string;
  value: number | null;
  highlight?: boolean;
}) {
  const displayValue = value !== null ? `$${value.toFixed(2)}` : 'N/A';

  return (
    <div
      className={`p-4 rounded-lg text-center ${
        highlight ? 'bg-cyan-500/10 border border-cyan-500/30' : 'bg-slate-700/30'
      }`}
    >
      <div className={`text-xl font-bold ${highlight ? 'text-cyan-400' : 'text-white'}`}>
        {displayValue}
      </div>
      <div className="text-xs text-gray-500">{label}</div>
    </div>
  );
}

function EventRow({ event }: { event: FarmEvent }) {
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

  const time = new Date(event.timestamp).toLocaleTimeString();

  return (
    <div className="flex items-center gap-3 py-2 px-3 bg-slate-700/30 rounded-lg">
      <span className="text-gray-500 text-xs w-20">{time}</span>
      <span className={`text-sm flex-1 ${getEventColor(event.type)}`}>{event.type}</span>
      {event.data.task_id && (
        <span className="text-gray-500 text-xs">
          Task: {event.data.task_id.slice(0, 8)}...
        </span>
      )}
    </div>
  );
}
