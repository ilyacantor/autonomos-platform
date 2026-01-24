/**
 * Chaos Monitor Panel
 *
 * Displays chaos injection events and recovery status from FARM stress tests.
 * Shows breakdown by chaos type with recovery tracking.
 */

import React from 'react';
import {
  Zap,
  Clock,
  XCircle,
  CheckCircle,
  AlertTriangle,
  RotateCcw,
  Ban,
  Wifi,
  Server,
  Shield,
  AlertOctagon,
  Activity,
} from 'lucide-react';

interface ChaosData {
  events_triggered: number;
  events_recovered: number;
  events_failed: number;
  recovery_rate: number;
  by_type: Record<string, number>;
}

interface FarmEvent {
  type: string;
  timestamp: string;
  data: Record<string, any>;
}

interface ChaosMonitorPanelProps {
  chaos?: ChaosData;
  events: FarmEvent[];
  loading: boolean;
}

// Chaos type configurations
const CHAOS_TYPES = [
  { key: 'tool_timeout', label: 'Tool Timeout', icon: Clock, color: 'yellow' },
  { key: 'tool_failure', label: 'Tool Failure', icon: XCircle, color: 'red' },
  { key: 'agent_conflict', label: 'Agent Conflict', icon: AlertTriangle, color: 'orange' },
  { key: 'policy_violation', label: 'Policy Violation', icon: Shield, color: 'purple' },
  { key: 'checkpoint_crash', label: 'Checkpoint Crash', icon: Server, color: 'pink' },
  { key: 'memory_pressure', label: 'Memory Pressure', icon: Activity, color: 'cyan' },
  { key: 'rate_limit', label: 'Rate Limit', icon: Ban, color: 'blue' },
  { key: 'data_corruption', label: 'Data Corruption', icon: AlertOctagon, color: 'rose' },
  { key: 'network_partition', label: 'Network Partition', icon: Wifi, color: 'gray' },
];

export default function ChaosMonitorPanel({
  chaos,
  events,
  loading,
}: ChaosMonitorPanelProps) {
  if (loading) {
    return (
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-slate-700 rounded w-36" />
          <div className="h-40 bg-slate-700/50 rounded" />
        </div>
      </div>
    );
  }

  const triggered = chaos?.events_triggered ?? 0;
  const recovered = chaos?.events_recovered ?? 0;
  const failed = chaos?.events_failed ?? 0;
  const recoveryRate = chaos?.recovery_rate ?? 0;
  const byType = chaos?.by_type ?? {};
  const pending = triggered - recovered - failed;

  // Parse events to get recovery status by chaos type
  const chaosStats = getChaosStatsByType(events, byType);

  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          <Zap className="w-5 h-5 text-yellow-400" />
          Chaos Events
        </h3>
        <RecoveryBadge rate={recoveryRate} />
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-4 gap-3 mb-6">
        <SummaryStat
          label="Triggered"
          value={triggered}
          icon={Zap}
          color="yellow"
        />
        <SummaryStat
          label="Recovered"
          value={recovered}
          icon={CheckCircle}
          color="green"
        />
        <SummaryStat
          label="Failed"
          value={failed}
          icon={XCircle}
          color="red"
        />
        <SummaryStat
          label="Pending"
          value={pending}
          icon={RotateCcw}
          color="blue"
        />
      </div>

      {/* Chaos Type Table */}
      {triggered > 0 && (
        <div className="overflow-hidden rounded-lg border border-slate-700/50">
          <table className="w-full">
            <thead className="bg-slate-700/30">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-400">Type</th>
                <th className="px-4 py-2 text-center text-xs font-medium text-gray-400">Count</th>
                <th className="px-4 py-2 text-center text-xs font-medium text-gray-400">Recovered</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-400">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/30">
              {CHAOS_TYPES.filter((ct) => (chaosStats[ct.key]?.count ?? 0) > 0).map(
                ({ key, label, icon: Icon, color }) => {
                  const stats = chaosStats[key] || { count: 0, recovered: 0, pending: 0 };
                  return (
                    <ChaosTypeRow
                      key={key}
                      icon={Icon}
                      label={label}
                      count={stats.count}
                      recovered={stats.recovered}
                      pending={stats.pending}
                      color={color}
                    />
                  );
                }
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Recovery Progress Bar */}
      {triggered > 0 && (
        <div className="mt-6">
          <div className="flex items-center justify-between mb-2 text-sm">
            <span className="text-gray-400">Overall Recovery Progress</span>
            <span className="text-yellow-400 font-medium">
              {recovered}/{triggered}
            </span>
          </div>
          <div className="w-full h-3 bg-slate-700 rounded-full overflow-hidden flex">
            <div
              className="h-full bg-green-500 transition-all duration-500"
              style={{ width: `${(recovered / triggered) * 100}%` }}
            />
            <div
              className="h-full bg-blue-500 transition-all duration-500"
              style={{ width: `${(pending / triggered) * 100}%` }}
            />
            <div
              className="h-full bg-red-500 transition-all duration-500"
              style={{ width: `${(failed / triggered) * 100}%` }}
            />
          </div>
          <div className="flex items-center justify-between mt-1 text-xs text-gray-500">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 bg-green-500 rounded-full" /> Recovered
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 bg-blue-500 rounded-full" /> Pending
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 bg-red-500 rounded-full" /> Failed
            </span>
          </div>
        </div>
      )}

      {/* Recent Chaos Events */}
      {events.length > 0 && (
        <div className="mt-6 pt-4 border-t border-slate-700/50">
          <h4 className="text-sm font-medium text-gray-400 mb-3">Recent Chaos Events</h4>
          <div className="space-y-2 max-h-32 overflow-y-auto">
            {events.slice(0, 5).map((event, idx) => (
              <ChaosEventRow key={idx} event={event} />
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {triggered === 0 && (
        <div className="text-center py-8 text-gray-500">
          <Zap className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>No chaos events yet.</p>
          <p className="text-sm">Chaos injections will appear during stress testing.</p>
        </div>
      )}
    </div>
  );
}

// Recovery Badge Component
function RecoveryBadge({ rate }: { rate: number }) {
  const percentage = (rate * 100).toFixed(0);

  if (rate >= 0.8) {
    return (
      <span className="flex items-center gap-1 px-2 py-1 bg-green-500/20 text-green-400 text-sm font-medium rounded-lg">
        <CheckCircle className="w-4 h-4" />
        {percentage}% Recovery
      </span>
    );
  }

  if (rate >= 0.5) {
    return (
      <span className="flex items-center gap-1 px-2 py-1 bg-yellow-500/20 text-yellow-400 text-sm font-medium rounded-lg">
        <AlertTriangle className="w-4 h-4" />
        {percentage}% Recovery
      </span>
    );
  }

  return (
    <span className="flex items-center gap-1 px-2 py-1 bg-red-500/20 text-red-400 text-sm font-medium rounded-lg">
      <XCircle className="w-4 h-4" />
      {percentage}% Recovery
    </span>
  );
}

// Summary Stat Component
function SummaryStat({
  label,
  value,
  icon: Icon,
  color,
}: {
  label: string;
  value: number;
  icon: any;
  color: string;
}) {
  const colorClasses: Record<string, { bg: string; text: string }> = {
    yellow: { bg: 'bg-yellow-500/20', text: 'text-yellow-400' },
    green: { bg: 'bg-green-500/20', text: 'text-green-400' },
    red: { bg: 'bg-red-500/20', text: 'text-red-400' },
    blue: { bg: 'bg-blue-500/20', text: 'text-blue-400' },
  };

  const colors = colorClasses[color] || colorClasses.yellow;

  return (
    <div className={`${colors.bg} rounded-lg p-3 text-center`}>
      <Icon className={`w-4 h-4 ${colors.text} mx-auto mb-1`} />
      <div className={`text-lg font-bold ${colors.text}`}>{value}</div>
      <div className="text-xs text-gray-500">{label}</div>
    </div>
  );
}

// Chaos Type Row Component
function ChaosTypeRow({
  icon: Icon,
  label,
  count,
  recovered,
  pending,
  color,
}: {
  icon: any;
  label: string;
  count: number;
  recovered: number;
  pending: number;
  color: string;
}) {
  const colorClasses: Record<string, string> = {
    yellow: 'text-yellow-400',
    red: 'text-red-400',
    orange: 'text-orange-400',
    purple: 'text-purple-400',
    pink: 'text-pink-400',
    cyan: 'text-cyan-400',
    blue: 'text-blue-400',
    rose: 'text-rose-400',
    gray: 'text-gray-400',
  };

  const textColor = colorClasses[color] || colorClasses.gray;

  return (
    <tr className="hover:bg-slate-700/20 transition-colors">
      <td className="px-4 py-2">
        <div className="flex items-center gap-2">
          <Icon className={`w-4 h-4 ${textColor}`} />
          <span className="text-sm text-gray-300">{label}</span>
        </div>
      </td>
      <td className="px-4 py-2 text-center">
        <span className={`text-sm font-medium ${textColor}`}>{count}</span>
      </td>
      <td className="px-4 py-2 text-center">
        <span className="text-sm font-medium text-green-400">{recovered}</span>
      </td>
      <td className="px-4 py-2">
        {pending > 0 ? (
          <span className="flex items-center gap-1 text-xs text-blue-400">
            <RotateCcw className="w-3 h-3 animate-spin" />
            {pending} pending
          </span>
        ) : (
          <span className="text-xs text-gray-500">-</span>
        )}
      </td>
    </tr>
  );
}

// Chaos Event Row Component
function ChaosEventRow({ event }: { event: FarmEvent }) {
  const isRecovered = event.type.includes('recovered');
  const isFailed = event.type.includes('failed');
  const time = new Date(event.timestamp).toLocaleTimeString();
  const chaosType = event.data.chaos_type || 'unknown';

  return (
    <div
      className={`flex items-center gap-3 py-2 px-3 rounded-lg ${
        isRecovered
          ? 'bg-green-500/10'
          : isFailed
          ? 'bg-red-500/10'
          : 'bg-yellow-500/10'
      }`}
    >
      {isRecovered ? (
        <CheckCircle className="w-4 h-4 text-green-400" />
      ) : isFailed ? (
        <XCircle className="w-4 h-4 text-red-400" />
      ) : (
        <Zap className="w-4 h-4 text-yellow-400" />
      )}
      <span className="text-gray-500 text-xs w-16">{time}</span>
      <span className="text-gray-300 text-sm">{chaosType}</span>
      {event.data.task_id && (
        <span className="text-gray-500 text-xs ml-auto">
          Task: {event.data.task_id.slice(0, 8)}...
        </span>
      )}
    </div>
  );
}

// Helper to calculate stats by chaos type from events
function getChaosStatsByType(
  events: FarmEvent[],
  byType: Record<string, number>
): Record<string, { count: number; recovered: number; pending: number }> {
  const stats: Record<string, { count: number; recovered: number; pending: number }> = {};

  // Initialize from byType
  for (const [type, count] of Object.entries(byType)) {
    stats[type] = { count, recovered: 0, pending: count };
  }

  // Update from events
  for (const event of events) {
    const chaosType = event.data.chaos_type;
    if (!chaosType) continue;

    if (!stats[chaosType]) {
      stats[chaosType] = { count: 0, recovered: 0, pending: 0 };
    }

    if (event.type.includes('injected')) {
      stats[chaosType].count++;
      stats[chaosType].pending++;
    } else if (event.type.includes('recovered')) {
      stats[chaosType].recovered++;
      stats[chaosType].pending = Math.max(0, stats[chaosType].pending - 1);
    }
  }

  return stats;
}
