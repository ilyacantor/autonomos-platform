/**
 * Fleet Status Panel
 *
 * Displays agent fleet distribution and status from FARM stress tests.
 * Shows breakdown by agent type and reliability tier.
 */

import React from 'react';
import { Users, Cpu, Eye, UserCheck, Shield, Activity } from 'lucide-react';

interface AgentData {
  total_registered: number;
  active: number;
  inactive: number;
  by_status: Record<string, number>;
  by_type: Record<string, number>;
  by_trust_tier: Record<string, number>;
}

interface FleetStatusPanelProps {
  agents?: AgentData;
  loading: boolean;
}

// Agent type configurations
const AGENT_TYPES = [
  { key: 'planner', label: 'Planner', icon: Cpu, color: 'cyan' },
  { key: 'worker', label: 'Worker', icon: Users, color: 'blue' },
  { key: 'specialist', label: 'Specialist', icon: Activity, color: 'purple' },
  { key: 'reviewer', label: 'Reviewer', icon: Eye, color: 'orange' },
  { key: 'approver', label: 'Approver', icon: Shield, color: 'green' },
];

// Reliability tier configurations
const RELIABILITY_TIERS = [
  { key: 'rock_solid', label: 'Rock Solid', color: 'emerald' },
  { key: 'reliable', label: 'Reliable', color: 'blue' },
  { key: 'flaky', label: 'Flaky', color: 'yellow' },
  { key: 'unreliable', label: 'Unreliable', color: 'red' },
];

export default function FleetStatusPanel({ agents, loading }: FleetStatusPanelProps) {
  if (loading) {
    return (
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-slate-700 rounded w-32" />
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-8 bg-slate-700/50 rounded" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  const totalAgents = agents?.total_registered ?? 0;
  const activeAgents = agents?.active ?? 0;
  const byType = agents?.by_type ?? {};
  const byTrustTier = agents?.by_trust_tier ?? {};

  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          <Users className="w-5 h-5 text-cyan-400" />
          Fleet Status
        </h3>
        <div className="flex items-center gap-2 text-sm">
          <span className="text-gray-400">Active:</span>
          <span className="text-cyan-400 font-medium">{activeAgents}/{totalAgents}</span>
        </div>
      </div>

      {/* Agent Type Distribution */}
      <div className="mb-6">
        <h4 className="text-sm font-medium text-gray-400 mb-3">Distribution by Type</h4>
        <div className="space-y-3">
          {AGENT_TYPES.map(({ key, label, icon: Icon, color }) => {
            const count = byType[key] ?? 0;
            const percentage = totalAgents > 0 ? (count / totalAgents) * 100 : 0;

            return (
              <AgentTypeRow
                key={key}
                icon={Icon}
                label={label}
                count={count}
                total={totalAgents}
                percentage={percentage}
                color={color}
              />
            );
          })}
        </div>
      </div>

      {/* Reliability Tiers */}
      <div>
        <h4 className="text-sm font-medium text-gray-400 mb-3">Reliability Tiers</h4>
        <div className="grid grid-cols-4 gap-2">
          {RELIABILITY_TIERS.map(({ key, label, color }) => {
            const count = byTrustTier[key] ?? 0;
            return (
              <ReliabilityTierBadge
                key={key}
                label={label}
                count={count}
                color={color}
              />
            );
          })}
        </div>
      </div>

      {/* Status Summary */}
      {totalAgents > 0 && (
        <div className="mt-6 pt-4 border-t border-slate-700/50">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-500">Fleet Utilization</span>
            <div className="flex items-center gap-2">
              <div className="w-32 h-2 bg-slate-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 transition-all duration-500"
                  style={{ width: `${(activeAgents / totalAgents) * 100}%` }}
                />
              </div>
              <span className="text-cyan-400 font-medium">
                {((activeAgents / totalAgents) * 100).toFixed(0)}%
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Empty State */}
      {totalAgents === 0 && (
        <div className="text-center py-8 text-gray-500">
          <Users className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>No agents registered yet.</p>
          <p className="text-sm">Agents will appear when FARM sends a fleet.</p>
        </div>
      )}
    </div>
  );
}

// Agent Type Row Component
function AgentTypeRow({
  icon: Icon,
  label,
  count,
  total,
  percentage,
  color,
}: {
  icon: any;
  label: string;
  count: number;
  total: number;
  percentage: number;
  color: string;
}) {
  const colorClasses: Record<string, { bg: string; text: string; bar: string }> = {
    cyan: { bg: 'bg-cyan-500/20', text: 'text-cyan-400', bar: 'bg-cyan-500' },
    blue: { bg: 'bg-blue-500/20', text: 'text-blue-400', bar: 'bg-blue-500' },
    purple: { bg: 'bg-purple-500/20', text: 'text-purple-400', bar: 'bg-purple-500' },
    orange: { bg: 'bg-orange-500/20', text: 'text-orange-400', bar: 'bg-orange-500' },
    green: { bg: 'bg-green-500/20', text: 'text-green-400', bar: 'bg-green-500' },
  };

  const colors = colorClasses[color] || colorClasses.blue;

  return (
    <div className="flex items-center gap-3">
      <div className={`w-8 h-8 ${colors.bg} rounded-lg flex items-center justify-center`}>
        <Icon className={`w-4 h-4 ${colors.text}`} />
      </div>
      <div className="flex-1">
        <div className="flex items-center justify-between mb-1">
          <span className="text-sm text-gray-300">{label}</span>
          <span className={`text-sm font-medium ${colors.text}`}>{count}</span>
        </div>
        <div className="w-full h-1.5 bg-slate-700 rounded-full overflow-hidden">
          <div
            className={`h-full ${colors.bar} transition-all duration-500`}
            style={{ width: `${percentage}%` }}
          />
        </div>
      </div>
    </div>
  );
}

// Reliability Tier Badge Component
function ReliabilityTierBadge({
  label,
  count,
  color,
}: {
  label: string;
  count: number;
  color: string;
}) {
  const colorClasses: Record<string, string> = {
    emerald: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    blue: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    yellow: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    red: 'bg-red-500/20 text-red-400 border-red-500/30',
  };

  const classes = colorClasses[color] || colorClasses.blue;

  return (
    <div className={`px-2 py-2 rounded-lg border ${classes} text-center`}>
      <div className="text-lg font-bold">{count}</div>
      <div className="text-xs opacity-80">{label}</div>
    </div>
  );
}
