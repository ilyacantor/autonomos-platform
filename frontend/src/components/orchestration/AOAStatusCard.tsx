/**
 * AOA Status Card Component
 *
 * Displays real-time orchestration vitals from the API.
 * Shows: AOA state, agent uptime, active agents, failed steps,
 * anomalies, human overrides, triggers/min, compute load.
 */

import {
  Activity,
  Zap,
  Users,
  XCircle,
  AlertTriangle,
  UserCheck,
  Cpu,
  RefreshCw,
  Clock,
  Bell,
} from 'lucide-react';
import type { OrchestrationVitals } from './types';
import { fetchVitals } from './api';
import { usePolledData } from '../../hooks/usePolledData';
import { getAOAStateColor, getVitalColor } from '../../utils/statusColors';

// Polling interval in milliseconds
const POLL_INTERVAL = 10000;

export default function AOAStatusCard() {
  const {
    data: vitals,
    loading,
    error,
    lastUpdated,
    refresh: loadVitals,
  } = usePolledData<OrchestrationVitals>(fetchVitals, POLL_INTERVAL);

  if (loading && !vitals) {
    return (
      <div className="rounded-2xl shadow-md p-6 bg-slate-800/60 border border-slate-700 h-full flex items-center justify-center">
        <RefreshCw className="w-6 h-6 text-cyan-400 animate-spin" />
        <span className="ml-3 text-slate-400">Loading vitals...</span>
      </div>
    );
  }

  if (error && !vitals) {
    return (
      <div className="rounded-2xl shadow-md p-6 bg-slate-800/60 border border-red-500/30 h-full">
        <div className="flex items-center gap-3 text-red-400">
          <AlertTriangle className="w-6 h-6" />
          <span>Failed to load vitals: {error}</span>
        </div>
        <button
          onClick={loadVitals}
          className="mt-4 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-slate-200 text-sm"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!vitals) return null;

  return (
    <div className="rounded-2xl shadow-md p-6 bg-slate-800/60 border border-slate-700 relative overflow-hidden h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-xl flex items-center justify-center">
            <Activity className="w-6 h-6 text-white" />
          </div>
          <div
            className="cursor-help"
            title="AutonomOS Agentic Orchestration Agent (AOA): A persistent, meta-level agent that observes, coordinates, and optimizes the behavior of all other domain agents."
          >
            <h2 className="text-xl font-medium text-cyan-400">AutonomOS Orchestration Layer</h2>
            <p className="text-sm text-slate-500">Mode: {vitals.autonomy_mode}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {vitals.pending_approvals > 0 && (
            <div className="flex items-center gap-2 px-3 py-1.5 bg-yellow-500/20 rounded-lg border border-yellow-500/30">
              <Bell className="w-4 h-4 text-yellow-400" />
              <span className="text-sm text-yellow-400">{vitals.pending_approvals} pending</span>
            </div>
          )}
          <div className={`px-4 py-2 rounded-lg border ${getAOAStateColor(vitals.state)}`}>
            <span className="text-sm">{vitals.state}</span>
          </div>
        </div>
      </div>

      {/* Vitals Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3 mb-4">
        <div className="flex items-center gap-2 bg-slate-900/50 rounded-lg px-4 py-3 border border-slate-700">
          <Activity className="w-4 h-4 text-cyan-400 flex-shrink-0" />
          <div className="min-w-0">
            <div className="text-xs text-slate-500 truncate">Agent Uptime</div>
            <div className={`text-lg transition-colors ${getVitalColor('uptime', vitals.agent_uptime_pct)}`}>
              {vitals.agent_uptime_pct.toFixed(1)}%
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 bg-slate-900/50 rounded-lg px-4 py-3 border border-slate-700">
          <Users className="w-4 h-4 text-cyan-400 flex-shrink-0" />
          <div className="min-w-0">
            <div className="text-xs text-slate-500 truncate">Active Agents</div>
            <div className="text-lg text-cyan-400">
              {vitals.active_agents.current} / {vitals.active_agents.total}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 bg-slate-900/50 rounded-lg px-4 py-3 border border-slate-700">
          <XCircle className="w-4 h-4 text-cyan-400 flex-shrink-0" />
          <div className="min-w-0">
            <div className="text-xs text-slate-500 truncate">Failed Steps (24h)</div>
            <div className={`text-lg transition-colors ${getVitalColor('failed', vitals.failed_steps_24h)}`}>
              {vitals.failed_steps_24h}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 bg-slate-900/50 rounded-lg px-4 py-3 border border-slate-700">
          <AlertTriangle className="w-4 h-4 text-cyan-400 flex-shrink-0" />
          <div className="min-w-0">
            <div className="text-xs text-slate-500 truncate">Anomalies (24h)</div>
            <div className={`text-lg transition-colors ${getVitalColor('anomalies', vitals.anomaly_detections_24h)}`}>
              {vitals.anomaly_detections_24h}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 bg-slate-900/50 rounded-lg px-4 py-3 border border-slate-700">
          <UserCheck className="w-4 h-4 text-cyan-400 flex-shrink-0" />
          <div className="min-w-0">
            <div className="text-xs text-slate-500 truncate">Human Overrides</div>
            <div className={`text-lg transition-colors ${getVitalColor('overrides', vitals.human_overrides_24h)}`}>
              {vitals.human_overrides_24h}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 bg-slate-900/50 rounded-lg px-4 py-3 border border-slate-700">
          <Zap className="w-4 h-4 text-cyan-400 flex-shrink-0" />
          <div className="min-w-0">
            <div className="text-xs text-slate-500 truncate">Triggers/min</div>
            <div className="text-lg text-cyan-400">
              {vitals.triggers_per_min.toFixed(1)}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 bg-slate-900/50 rounded-lg px-4 py-3 border border-slate-700">
          <Cpu className="w-4 h-4 text-cyan-400 flex-shrink-0" />
          <div className="min-w-0">
            <div className="text-xs text-slate-500 truncate">Compute Load</div>
            <div className={`text-lg transition-colors ${getVitalColor('load', vitals.compute_load_pct)}`}>
              {vitals.compute_load_pct.toFixed(0)}%
            </div>
          </div>
        </div>
      </div>

      {/* Footer Stats */}
      <div className="flex items-center justify-between text-xs text-slate-500 pt-2 border-t border-slate-700/50">
        <div className="flex items-center gap-4">
          <span>Total Runs (24h): {vitals.total_runs_24h}</span>
          <span>Avg Duration: {vitals.avg_run_duration_ms.toFixed(0)}ms</span>
        </div>
        {lastUpdated && (
          <div className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            <span>Updated {lastUpdated.toLocaleTimeString()}</span>
          </div>
        )}
      </div>

      {/* Executing indicator */}
      {vitals.state === 'Executing' && (
        <div className="absolute bottom-0 left-0 w-full h-1 bg-slate-700 overflow-hidden">
          <div className="h-full bg-gradient-to-r from-cyan-500 via-blue-500 to-cyan-500 animate-pulse" />
        </div>
      )}
    </div>
  );
}
