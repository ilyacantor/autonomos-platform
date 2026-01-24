/**
 * Workflow Execution Grid
 *
 * Real-time display of workflow execution progress from FARM stress tests.
 * Shows individual workflow cards with progress bars and status.
 */

import React from 'react';
import {
  GitBranch,
  CheckCircle,
  XCircle,
  Clock,
  Zap,
  AlertTriangle,
  Play,
} from 'lucide-react';

interface WorkflowData {
  active_workflows: number;
  completed_24h: number;
  failed_24h: number;
  completion_rate: number;
  avg_duration_ms: number;
  throughput_per_min: number;
}

interface WorkflowResult {
  workflow_id: string;
  status: string;
  tasks_completed: number;
  chaos_handled: number;
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

interface WorkflowExecutionGridProps {
  workflows?: WorkflowData;
  scenarioResult?: ScenarioResult | null;
  loading: boolean;
}

export default function WorkflowExecutionGrid({
  workflows,
  scenarioResult,
  loading,
}: WorkflowExecutionGridProps) {
  if (loading) {
    return (
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-slate-700 rounded w-40" />
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-20 bg-slate-700/50 rounded" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  const activeWorkflows = workflows?.active_workflows ?? 0;
  const completedWorkflows = workflows?.completed_24h ?? 0;
  const failedWorkflows = workflows?.failed_24h ?? 0;
  const completionRate = workflows?.completion_rate ?? 0;
  const avgDurationMs = workflows?.avg_duration_ms ?? 0;
  const throughput = workflows?.throughput_per_min ?? 0;

  const totalWorkflows = activeWorkflows + completedWorkflows + failedWorkflows;
  const tasksCompleted = scenarioResult?.tasks_completed ?? 0;
  const totalTasks = scenarioResult?.total_tasks ?? 0;
  const taskProgress = totalTasks > 0 ? (tasksCompleted / totalTasks) * 100 : 0;

  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          <GitBranch className="w-5 h-5 text-purple-400" />
          Workflow Execution
        </h3>
        <div className="flex items-center gap-3 text-sm">
          <span className="text-gray-400">Throughput:</span>
          <span className="text-purple-400 font-medium">{throughput.toFixed(1)}/min</span>
        </div>
      </div>

      {/* Summary Stats Row */}
      <div className="grid grid-cols-4 gap-3 mb-6">
        <StatBadge
          icon={Play}
          label="Running"
          value={activeWorkflows}
          color="blue"
        />
        <StatBadge
          icon={CheckCircle}
          label="Completed"
          value={completedWorkflows}
          color="green"
        />
        <StatBadge
          icon={XCircle}
          label="Failed"
          value={failedWorkflows}
          color="red"
        />
        <StatBadge
          icon={Clock}
          label="Avg Time"
          value={`${(avgDurationMs / 1000).toFixed(1)}s`}
          color="gray"
        />
      </div>

      {/* Overall Progress */}
      {totalTasks > 0 && (
        <div className="mb-6 p-4 bg-slate-700/30 rounded-lg">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-400">Overall Task Progress</span>
            <span className="text-sm font-medium text-white">
              {tasksCompleted}/{totalTasks} tasks
            </span>
          </div>
          <div className="w-full h-3 bg-slate-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-purple-500 to-pink-500 transition-all duration-500"
              style={{ width: `${taskProgress}%` }}
            />
          </div>
          <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
            <span>0%</span>
            <span className="text-purple-400 font-medium">{taskProgress.toFixed(1)}%</span>
            <span>100%</span>
          </div>
        </div>
      )}

      {/* Completion Rate Indicator */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-gray-400">Completion Rate</span>
          <CompletionBadge rate={completionRate} />
        </div>
        <div className="w-full h-2 bg-slate-700 rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-500 ${getCompletionBarColor(completionRate)}`}
            style={{ width: `${completionRate * 100}%` }}
          />
        </div>
      </div>

      {/* Workflow Results from Scenario (if available) */}
      {scenarioResult?.analysis?.sections && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-gray-400 mb-3">Execution Analysis</h4>

          {Object.entries(scenarioResult.analysis.sections).map(([key, section]: [string, any]) => (
            <AnalysisSection
              key={key}
              title={key.charAt(0).toUpperCase() + key.slice(1)}
              verdict={section.verdict}
              findings={section.findings || []}
            />
          ))}
        </div>
      )}

      {/* Empty State */}
      {totalWorkflows === 0 && !scenarioResult && (
        <div className="text-center py-8 text-gray-500">
          <GitBranch className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>No workflows executed yet.</p>
          <p className="text-sm">Workflows will appear when stress test starts.</p>
        </div>
      )}

      {/* Chaos Events Summary */}
      {scenarioResult && (scenarioResult.chaos_events_total ?? 0) > 0 && (
        <div className="mt-4 pt-4 border-t border-slate-700/50">
          <div className="flex items-center gap-2 text-sm">
            <Zap className="w-4 h-4 text-yellow-400" />
            <span className="text-gray-400">Chaos events handled:</span>
            <span className="text-yellow-400 font-medium">
              {scenarioResult.chaos_events_recovered}/{scenarioResult.chaos_events_total}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

// Stat Badge Component
function StatBadge({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: any;
  label: string;
  value: string | number;
  color: string;
}) {
  const colorClasses: Record<string, { bg: string; text: string }> = {
    blue: { bg: 'bg-blue-500/20', text: 'text-blue-400' },
    green: { bg: 'bg-green-500/20', text: 'text-green-400' },
    red: { bg: 'bg-red-500/20', text: 'text-red-400' },
    gray: { bg: 'bg-gray-500/20', text: 'text-gray-400' },
  };

  const colors = colorClasses[color] || colorClasses.gray;

  return (
    <div className={`${colors.bg} rounded-lg p-3 text-center`}>
      <Icon className={`w-4 h-4 ${colors.text} mx-auto mb-1`} />
      <div className={`text-lg font-bold ${colors.text}`}>{value}</div>
      <div className="text-xs text-gray-500">{label}</div>
    </div>
  );
}

// Completion Badge Component
function CompletionBadge({ rate }: { rate: number }) {
  const percentage = (rate * 100).toFixed(1);

  if (rate >= 0.95) {
    return (
      <span className="flex items-center gap-1 text-green-400 text-sm font-medium">
        <CheckCircle className="w-4 h-4" />
        {percentage}%
      </span>
    );
  }

  if (rate >= 0.8) {
    return (
      <span className="flex items-center gap-1 text-yellow-400 text-sm font-medium">
        <AlertTriangle className="w-4 h-4" />
        {percentage}%
      </span>
    );
  }

  return (
    <span className="flex items-center gap-1 text-red-400 text-sm font-medium">
      <XCircle className="w-4 h-4" />
      {percentage}%
    </span>
  );
}

// Analysis Section Component
function AnalysisSection({
  title,
  verdict,
  findings,
}: {
  title: string;
  verdict: string;
  findings: string[];
}) {
  const verdictColors: Record<string, { bg: string; text: string; icon: any }> = {
    PASS: { bg: 'bg-green-500/20', text: 'text-green-400', icon: CheckCircle },
    DEGRADED: { bg: 'bg-yellow-500/20', text: 'text-yellow-400', icon: AlertTriangle },
    FAIL: { bg: 'bg-red-500/20', text: 'text-red-400', icon: XCircle },
  };

  const colors = verdictColors[verdict] || verdictColors.PASS;
  const Icon = colors.icon;

  return (
    <div className={`${colors.bg} rounded-lg p-3`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-white">{title}</span>
        <span className={`flex items-center gap-1 text-xs ${colors.text}`}>
          <Icon className="w-3 h-3" />
          {verdict}
        </span>
      </div>
      {findings.length > 0 && (
        <ul className="text-xs text-gray-400 space-y-1">
          {findings.slice(0, 3).map((finding, idx) => (
            <li key={idx} className="flex items-start gap-2">
              <span className="text-gray-600">•</span>
              {finding}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// Helper function for progress bar color
function getCompletionBarColor(rate: number): string {
  if (rate >= 0.95) return 'bg-gradient-to-r from-green-500 to-emerald-500';
  if (rate >= 0.8) return 'bg-gradient-to-r from-yellow-500 to-orange-500';
  return 'bg-gradient-to-r from-red-500 to-rose-500';
}
