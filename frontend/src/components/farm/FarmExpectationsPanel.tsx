/**
 * FARM Expectations Panel
 *
 * Displays FARM test oracle comparison - expected vs actual results.
 * Shows validation checks against the __expected__ block from FARM scenarios.
 */

import React from 'react';
import {
  Target,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Percent,
  Hash,
  ToggleLeft,
  Clock,
  Zap,
  TrendingUp,
} from 'lucide-react';

interface ValidationCheck {
  expected: any;
  actual: any;
  passed: boolean;
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
  validation: Record<string, ValidationCheck>;
  analysis: Record<string, any>;
  total_cost_usd: number;
}

interface FarmExpectationsPanelProps {
  scenarioResult?: ScenarioResult | null;
  loading: boolean;
}

// Expectation check configurations
const EXPECTATION_CHECKS = [
  {
    key: 'completion_rate',
    label: 'Completion Rate',
    icon: Percent,
    format: (v: any) => `≥${(v * 100).toFixed(0)}%`,
    formatActual: (v: any) => `${(v * 100).toFixed(1)}%`,
  },
  {
    key: 'chaos_recovery',
    label: 'Chaos Recovery',
    icon: Zap,
    format: (v: any) => `≥${(v * 100).toFixed(0)}%`,
    formatActual: (v: any) => `${(v * 100).toFixed(1)}%`,
  },
  {
    key: 'task_completion',
    label: 'Task Completion',
    icon: Hash,
    format: (v: any) => `${v} tasks`,
    formatActual: (v: any) => `${v} tasks`,
  },
  {
    key: 'all_assigned',
    label: 'All Tasks Assigned',
    icon: ToggleLeft,
    format: (v: any) => v ? 'Yes' : 'No',
    formatActual: (v: any) => v ? 'Yes' : 'No',
  },
  {
    key: 'can_execute_all',
    label: 'Can Execute All',
    icon: ToggleLeft,
    format: (v: any) => v ? 'Yes' : 'No',
    formatActual: (v: any) => v ? 'Yes' : 'No',
  },
  {
    key: 'throughput',
    label: 'Throughput',
    icon: TrendingUp,
    format: (v: any) => `≥${v} tasks/sec`,
    formatActual: (v: any) => `${v.toFixed(2)} tasks/sec`,
  },
  {
    key: 'avg_latency',
    label: 'Avg Latency',
    icon: Clock,
    format: (v: any) => `≤${v}ms`,
    formatActual: (v: any) => `${v.toFixed(0)}ms`,
  },
];

export default function FarmExpectationsPanel({
  scenarioResult,
  loading,
}: FarmExpectationsPanelProps) {
  if (loading) {
    return (
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-slate-700 rounded w-48" />
          <div className="h-40 bg-slate-700/50 rounded" />
        </div>
      </div>
    );
  }

  const validation = scenarioResult?.validation ?? {};
  const validationEntries = Object.entries(validation);
  const passedCount = validationEntries.filter(([_, v]) => v.passed).length;
  const totalCount = validationEntries.length;
  const alignmentRate = totalCount > 0 ? passedCount / totalCount : 0;

  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          <Target className="w-5 h-5 text-orange-400" />
          FARM Test Oracle
        </h3>
        {totalCount > 0 && <AlignmentBadge rate={alignmentRate} />}
      </div>

      {/* Validation Table */}
      {totalCount > 0 ? (
        <>
          <div className="overflow-hidden rounded-lg border border-slate-700/50">
            <table className="w-full">
              <thead className="bg-slate-700/30">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-400">
                    Check
                  </th>
                  <th className="px-4 py-2 text-center text-xs font-medium text-gray-400">
                    Expected
                  </th>
                  <th className="px-4 py-2 text-center text-xs font-medium text-gray-400">
                    Actual
                  </th>
                  <th className="px-4 py-2 text-center text-xs font-medium text-gray-400">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/30">
                {validationEntries.map(([key, check]) => {
                  const config = EXPECTATION_CHECKS.find((c) => c.key === key);
                  return (
                    <ValidationRow
                      key={key}
                      label={config?.label ?? formatLabel(key)}
                      icon={config?.icon ?? Target}
                      expected={config?.format ? config.format(check.expected) : String(check.expected)}
                      actual={config?.formatActual ? config.formatActual(check.actual) : String(check.actual)}
                      passed={check.passed}
                    />
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Summary */}
          <div className="mt-4 flex items-center justify-between text-sm">
            <span className="text-gray-500">
              {passedCount} of {totalCount} checks passed
            </span>
            <VerdictBadge verdict={scenarioResult?.verdict ?? 'PENDING'} />
          </div>

          {/* Discrepancies */}
          {passedCount < totalCount && (
            <div className="mt-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
              <h4 className="text-sm font-medium text-red-400 mb-2 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4" />
                Discrepancies
              </h4>
              <ul className="text-sm text-gray-400 space-y-1">
                {validationEntries
                  .filter(([_, v]) => !v.passed)
                  .map(([key, check]) => (
                    <li key={key} className="flex items-start gap-2">
                      <XCircle className="w-4 h-4 text-red-400 mt-0.5" />
                      <span>
                        <strong className="text-gray-300">{formatLabel(key)}</strong>: Expected{' '}
                        {formatValue(check.expected)}, got {formatValue(check.actual)}
                      </span>
                    </li>
                  ))}
              </ul>
            </div>
          )}

          {/* All Passed */}
          {passedCount === totalCount && totalCount > 0 && (
            <div className="mt-4 p-3 bg-green-500/10 border border-green-500/30 rounded-lg">
              <div className="flex items-center gap-2 text-green-400">
                <CheckCircle className="w-5 h-5" />
                <span className="text-sm font-medium">
                  All validation checks passed
                </span>
              </div>
            </div>
          )}
        </>
      ) : (
        /* Empty State */
        <div className="text-center py-8 text-gray-500">
          <Target className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>No expectations defined yet.</p>
          <p className="text-sm">FARM expectations will appear when a scenario is submitted.</p>
        </div>
      )}

      {/* Analysis Recommendations */}
      {scenarioResult?.analysis?.recommendations && scenarioResult.analysis.recommendations.length > 0 && (
        <div className="mt-6 pt-4 border-t border-slate-700/50">
          <h4 className="text-sm font-medium text-gray-400 mb-3">Recommendations</h4>
          <ul className="text-sm text-gray-400 space-y-2">
            {scenarioResult.analysis.recommendations.map((rec: string, idx: number) => (
              <li key={idx} className="flex items-start gap-2">
                <span className="text-orange-400">→</span>
                {rec}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Metrics Summary */}
      {scenarioResult?.analysis?.metrics && (
        <div className="mt-6 pt-4 border-t border-slate-700/50">
          <h4 className="text-sm font-medium text-gray-400 mb-3">Performance Metrics</h4>
          <div className="grid grid-cols-2 gap-3">
            {Object.entries(scenarioResult.analysis.metrics).slice(0, 4).map(([key, value]) => (
              <MetricCard key={key} label={formatLabel(key)} value={value} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// Alignment Badge Component
function AlignmentBadge({ rate }: { rate: number }) {
  const percentage = (rate * 100).toFixed(0);

  if (rate >= 1) {
    return (
      <span className="flex items-center gap-1 px-2 py-1 bg-green-500/20 text-green-400 text-sm font-medium rounded-lg">
        <CheckCircle className="w-4 h-4" />
        {percentage}% Aligned
      </span>
    );
  }

  if (rate >= 0.8) {
    return (
      <span className="flex items-center gap-1 px-2 py-1 bg-yellow-500/20 text-yellow-400 text-sm font-medium rounded-lg">
        <AlertTriangle className="w-4 h-4" />
        {percentage}% Aligned
      </span>
    );
  }

  return (
    <span className="flex items-center gap-1 px-2 py-1 bg-red-500/20 text-red-400 text-sm font-medium rounded-lg">
      <XCircle className="w-4 h-4" />
      {percentage}% Aligned
    </span>
  );
}

// Verdict Badge Component
function VerdictBadge({ verdict }: { verdict: string }) {
  const configs: Record<string, { bg: string; text: string; icon: any }> = {
    PASS: { bg: 'bg-green-500/20', text: 'text-green-400', icon: CheckCircle },
    DEGRADED: { bg: 'bg-yellow-500/20', text: 'text-yellow-400', icon: AlertTriangle },
    FAIL: { bg: 'bg-red-500/20', text: 'text-red-400', icon: XCircle },
    PENDING: { bg: 'bg-gray-500/20', text: 'text-gray-400', icon: Clock },
  };

  const config = configs[verdict] || configs.PENDING;
  const Icon = config.icon;

  return (
    <span className={`flex items-center gap-1 px-2 py-1 ${config.bg} ${config.text} text-sm font-medium rounded-lg`}>
      <Icon className="w-4 h-4" />
      {verdict}
    </span>
  );
}

// Validation Row Component
function ValidationRow({
  label,
  icon: Icon,
  expected,
  actual,
  passed,
}: {
  label: string;
  icon: any;
  expected: string;
  actual: string;
  passed: boolean;
}) {
  return (
    <tr className="hover:bg-slate-700/20 transition-colors">
      <td className="px-4 py-2">
        <div className="flex items-center gap-2">
          <Icon className="w-4 h-4 text-gray-500" />
          <span className="text-sm text-gray-300">{label}</span>
        </div>
      </td>
      <td className="px-4 py-2 text-center">
        <span className="text-sm text-gray-400">{expected}</span>
      </td>
      <td className="px-4 py-2 text-center">
        <span className={`text-sm font-medium ${passed ? 'text-green-400' : 'text-red-400'}`}>
          {actual}
        </span>
      </td>
      <td className="px-4 py-2 text-center">
        {passed ? (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-green-500/20 text-green-400 text-xs rounded-full">
            <CheckCircle className="w-3 h-3" />
            PASS
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-red-500/20 text-red-400 text-xs rounded-full">
            <XCircle className="w-3 h-3" />
            FAIL
          </span>
        )}
      </td>
    </tr>
  );
}

// Metric Card Component
function MetricCard({ label, value }: { label: string; value: any }) {
  const formattedValue = typeof value === 'number'
    ? value < 1 ? `${(value * 100).toFixed(1)}%` : value.toFixed(2)
    : String(value);

  return (
    <div className="bg-slate-700/30 rounded-lg p-3">
      <div className="text-lg font-bold text-white">{formattedValue}</div>
      <div className="text-xs text-gray-500">{label}</div>
    </div>
  );
}

// Helper to format label from key
function formatLabel(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

// Helper to format value for display
function formatValue(value: any): string {
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  if (typeof value === 'number') {
    if (value < 1 && value > 0) return `${(value * 100).toFixed(1)}%`;
    return value.toFixed(2);
  }
  return String(value);
}
