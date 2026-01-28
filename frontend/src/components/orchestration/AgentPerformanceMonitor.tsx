/**
 * Agent Performance Monitor Component
 *
 * Displays real-time performance metrics for each agent from the API.
 * Shows: execution rates, success rates, duration, cost, and status.
 *
 * Uses the following reusable hooks:
 * - usePolledData: For automatic data fetching with polling
 * - useStatusColors: For consistent status color mapping
 */

import { useState } from 'react';
import { RefreshCw, AlertTriangle, ExternalLink, TrendingUp, Clock, DollarSign, Zap, Plus } from 'lucide-react';
import type { AgentPerformance, AgentPerformanceResponse, AgentStatus } from './types';
import { fetchAgentPerformance, seedDemoAgents } from './api';
import { usePolledData } from '../../hooks/usePolledData';
import { useStatusColors } from '../../hooks/useStatusColors';

// Polling interval in milliseconds
const POLL_INTERVAL = 15000;

// External URLs for specific agents
const AGENT_URLS: Record<string, string> = {
  'finops': 'https://autonomos.technology/',
  'revops': 'https://autonomos.cloud/',
};

/**
 * Get external URL for an agent if available.
 */
function getAgentUrl(agentName: string): string | null {
  const nameLower = agentName.toLowerCase();
  for (const [key, url] of Object.entries(AGENT_URLS)) {
    if (nameLower.includes(key)) {
      return url;
    }
  }
  return null;
}

export default function AgentPerformanceMonitor() {
  // Use the reusable hooks for data fetching and status colors
  const { data, loading, error, refresh } = usePolledData<AgentPerformanceResponse>(
    () => fetchAgentPerformance(20),
    POLL_INTERVAL
  );
  const { getAgentStatusColor } = useStatusColors();

  const [seeding, setSeeding] = useState(false);
  const [seedError, setSeedError] = useState<string | null>(null);

  const handleSeedAgents = async () => {
    setSeeding(true);
    setSeedError(null);
    try {
      await seedDemoAgents();
      refresh(); // Trigger a refresh after seeding
    } catch (err: any) {
      setSeedError(err.message);
    } finally {
      setSeeding(false);
    }
  };

  const getSuccessRateColor = (rate: number) => {
    if (rate >= 95) return 'text-green-400';
    if (rate >= 80) return 'text-yellow-400';
    return 'text-red-400';
  };

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms.toFixed(0)}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${(ms / 60000).toFixed(1)}m`;
  };

  const formatCost = (usd: number) => {
    if (usd === 0) return '$0';
    if (usd < 0.01) return '<$0.01';
    if (usd < 1) return `$${usd.toFixed(2)}`;
    return `$${usd.toFixed(2)}`;
  };

  const formatLastRun = (dateStr: string | null) => {
    if (!dateStr) return 'Never';
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${Math.floor(diffHours / 24)}d ago`;
  };

  if (loading && !data) {
    return (
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 h-full">
        <div className="flex items-center justify-center py-8">
          <RefreshCw className="w-6 h-6 text-cyan-400 animate-spin" />
          <span className="ml-3 text-gray-400">Loading agent performance...</span>
        </div>
      </div>
    );
  }

  // Display error for data fetching or seeding
  const displayError = error || seedError;
  if (displayError && !data) {
    return (
      <div className="bg-gray-900 rounded-xl border border-red-500/30 p-6 h-full">
        <div className="flex items-center gap-3 text-red-400">
          <AlertTriangle className="w-6 h-6" />
          <span>Failed to load performance: {displayError}</span>
        </div>
        <button
          onClick={refresh}
          className="mt-4 px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-gray-200 text-sm"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <h2
          className="text-lg font-semibold text-white cursor-help"
          title="Displays real-time operational metrics for each domain agent. Each row represents execution throughput, success rate, and resource usage per active agent."
        >
          Active Agent Performance
        </h2>
        <div className="text-sm text-gray-500">
          {data.total_agents} agents
        </div>
      </div>

      {data.agents.length === 0 ? (
        <div className="flex-1 flex items-center justify-center text-gray-500">
          <div className="text-center">
            <Zap className="w-12 h-12 mx-auto mb-3 text-gray-600" />
            <p className="text-white font-medium">No agents configured</p>
            <p className="text-sm mt-1 mb-4">Create demo agents to see the dashboard in action</p>
            <button
              onClick={handleSeedAgents}
              disabled={seeding}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600 disabled:from-gray-600 disabled:to-gray-600 text-white rounded-xl font-medium shadow-lg shadow-cyan-500/20 disabled:shadow-none transition-all"
            >
              {seeding ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Creating Agents...
                </>
              ) : (
                <>
                  <Plus className="w-4 h-4" />
                  Seed Demo Agents
                </>
              )}
            </button>
          </div>
        </div>
      ) : (
        <div className="flex-1 overflow-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-800">
                <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider pb-3">
                  Agent
                </th>
                <th className="text-center text-xs font-semibold text-gray-500 uppercase tracking-wider pb-3">
                  Status
                </th>
                <th className="text-right text-xs font-semibold text-gray-500 uppercase tracking-wider pb-3">
                  Exec/hr
                </th>
                <th className="text-right text-xs font-semibold text-gray-500 uppercase tracking-wider pb-3">
                  Success
                </th>
                <th className="text-right text-xs font-semibold text-gray-500 uppercase tracking-wider pb-3">
                  Avg Time
                </th>
                <th className="text-right text-xs font-semibold text-gray-500 uppercase tracking-wider pb-3">
                  Cost (24h)
                </th>
                <th className="text-right text-xs font-semibold text-gray-500 uppercase tracking-wider pb-3">
                  Last Run
                </th>
              </tr>
            </thead>
            <tbody>
              {data.agents.map((agent) => {
                const agentUrl = getAgentUrl(agent.name);
                return (
                <tr
                  key={agent.id}
                  className={`border-b border-gray-800 hover:bg-gray-800/50 transition-colors ${agentUrl ? 'cursor-pointer' : ''}`}
                  onClick={agentUrl ? () => window.open(agentUrl, '_blank') : undefined}
                >
                  <td className="py-3">
                    <div className="flex items-center gap-2">
                      <div className={`text-sm font-medium ${agentUrl ? 'text-cyan-400 hover:text-cyan-300' : 'text-white'}`}>
                        {agent.name}
                      </div>
                      {agentUrl && (
                        <ExternalLink className="w-3.5 h-3.5 text-cyan-400" />
                      )}
                      <span className="text-xs text-gray-500 bg-gray-800 px-2 py-0.5 rounded">
                        {agent.agent_type}
                      </span>
                      {agent.pending_approvals > 0 && (
                        <span className="text-xs text-yellow-400 bg-yellow-500/20 px-2 py-0.5 rounded">
                          {agent.pending_approvals} pending
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="py-3">
                    <div className="flex justify-center">
                      <div
                        className={`w-2.5 h-2.5 rounded-full ${getAgentStatusColor(agent.status)} ${
                          agent.status === 'running' ? 'animate-pulse' : ''
                        }`}
                        title={agent.status}
                      />
                    </div>
                  </td>
                  <td className="py-3 text-right">
                    <span className="text-sm text-gray-300">{agent.executions_per_hour}</span>
                  </td>
                  <td className="py-3 text-right">
                    <span className={`text-sm font-medium ${getSuccessRateColor(agent.success_rate_pct)}`}>
                      {agent.success_rate_pct.toFixed(1)}%
                    </span>
                  </td>
                  <td className="py-3 text-right">
                    <span className="text-sm text-gray-300">
                      {formatDuration(agent.avg_duration_ms)}
                    </span>
                  </td>
                  <td className="py-3 text-right">
                    <span className="text-sm text-gray-300">
                      {formatCost(agent.cost_24h_usd)}
                    </span>
                  </td>
                  <td className="py-3 text-right">
                    <span className="text-sm text-gray-500">
                      {formatLastRun(agent.last_run_at)}
                    </span>
                  </td>
                </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Summary Stats */}
      {data.agents.length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-800 grid grid-cols-4 gap-4 text-center">
          <div>
            <div className="text-xs text-gray-500">Total Runs (24h)</div>
            <div className="text-lg text-cyan-400">
              {data.agents.reduce((sum, a) => sum + a.total_runs_24h, 0)}
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-500">Failed (24h)</div>
            <div className="text-lg text-red-400">
              {data.agents.reduce((sum, a) => sum + a.failed_runs_24h, 0)}
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-500">Total Cost</div>
            <div className="text-lg text-green-400">
              {formatCost(data.agents.reduce((sum, a) => sum + a.cost_24h_usd, 0))}
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-500">Total Tokens</div>
            <div className="text-lg text-purple-400">
              {(data.agents.reduce((sum, a) => sum + a.tokens_24h, 0) / 1000).toFixed(1)}k
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
