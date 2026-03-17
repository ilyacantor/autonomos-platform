/**
 * Maestra Monitoring Surface
 *
 * Dev/debugging monitoring page for Maestra orchestration.
 * Four panels: Engagement Status, Run Ledger, Human Review Queue, Constitution & Tools.
 */

import { useState, useEffect, useCallback, useRef, Fragment } from 'react';
import {
  Activity,
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  RefreshCw,
  Plus,
  Eye,
} from 'lucide-react';

// ============================================================================
// Types
// ============================================================================

interface Engagement {
  engagement_id: string;
  entity_a: string;
  entity_b: string;
  entity_a_name: string;
  entity_b_name: string;
  state: string;
  created_by: string;
  created_at: string;
  updated_at: string;
}

interface MaestraStatus {
  status: string;
  active_engagement: Engagement | null;
  pending_reviews_count: number;
  available_tools: number;
  constitution_rules: number;
}

interface LedgerStep {
  step_id: string;
  engagement_id: string;
  step_name: string;
  status: string;
  idempotency_key: string;
  inputs_hash: string;
  upstream_deps: string[] | null;
  outputs_ref: string | null;
  error: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

interface Review {
  review_id: string;
  engagement_id: string;
  action: string;
  context: Record<string, unknown>;
  tier: number;
  status: string;
  requested_by: string;
  approved_by: string | null;
  rejected_by: string | null;
  reason: string | null;
  created_at: string;
}

interface Constitution {
  rules: string[];
  count: number;
}

interface ToolDefinition {
  name: string;
  description: string;
  parameters: Record<string, string>;
}

// ============================================================================
// API helpers
// ============================================================================

const BASE = '/api/maestra';

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
    throw new Error(body.detail || `HTTP ${response.status}`);
  }
  return response.json();
}

// ============================================================================
// Utility
// ============================================================================

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function formatTime(iso: string | null): string {
  if (!iso) return '\u2014';
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function durationBetween(start: string | null, end: string | null): string {
  if (!start) return '\u2014';
  const s = new Date(start).getTime();
  const e = end ? new Date(end).getTime() : Date.now();
  const ms = e - s;
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

// ============================================================================
// Status badge
// ============================================================================

const STATUS_COLORS: Record<string, string> = {
  active: 'bg-green-500/20 text-green-400 border-green-500/30',
  running: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  complete: 'bg-green-500/20 text-green-400 border-green-500/30',
  completed: 'bg-green-500/20 text-green-400 border-green-500/30',
  failed: 'bg-red-500/20 text-red-400 border-red-500/30',
  pending: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
  paused: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  stale: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  draft: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
  archived: 'bg-gray-600/20 text-gray-500 border-gray-600/30',
  approved: 'bg-green-500/20 text-green-400 border-green-500/30',
  rejected: 'bg-red-500/20 text-red-400 border-red-500/30',
  operational: 'bg-green-500/20 text-green-400 border-green-500/30',
};

function StatusBadge({ status, pulse }: { status: string; pulse?: boolean }) {
  const cls = STATUS_COLORS[status] || 'bg-gray-500/20 text-gray-400 border-gray-500/30';
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full border ${cls}`}>
      {pulse && <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />}
      {status}
    </span>
  );
}

// Tier colors for review cards
const TIER_COLORS: Record<number, string> = {
  1: 'bg-green-500/20 text-green-400',
  2: 'bg-blue-500/20 text-blue-400',
  3: 'bg-amber-500/20 text-amber-400',
  4: 'bg-red-500/20 text-red-400',
};

// ============================================================================
// Panel 1: Engagement Status
// ============================================================================

function EngagementStatusPanel({
  engagements,
  maestraStatus,
  onCreateEngagement,
  creating,
  selectedEngagementId,
  onSelectEngagement,
}: {
  engagements: Engagement[];
  maestraStatus: MaestraStatus | null;
  onCreateEngagement: () => void;
  creating: boolean;
  selectedEngagementId: string | null;
  onSelectEngagement: (id: string) => void;
}) {
  // Find the active engagement, or the first one, or the selected one
  const activeEngagement = engagements.find(e => e.state === 'active') || null;
  const displayEngagement = activeEngagement || engagements.find(e => e.engagement_id === selectedEngagementId) || engagements[0] || null;

  if (engagements.length === 0) {
    return (
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Activity className="w-5 h-5 text-cyan-400" />
          Engagement Status
        </h2>
        <div className="text-center py-8">
          <p className="text-gray-500 mb-4">No active engagement</p>
          <button
            onClick={onCreateEngagement}
            disabled={creating}
            className="inline-flex items-center gap-2 px-4 py-2 bg-cyan-600 hover:bg-cyan-500 disabled:bg-gray-600 text-white text-sm font-medium rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" />
            {creating ? 'Creating...' : 'Create Engagement'}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
          <Activity className="w-5 h-5 text-cyan-400" />
          Engagement Status
        </h2>
        <div className="flex items-center gap-3">
          {engagements.length > 1 && (
            <select
              value={selectedEngagementId || displayEngagement?.engagement_id || ''}
              onChange={(e) => onSelectEngagement(e.target.value)}
              className="bg-slate-700 text-gray-300 text-sm rounded-lg px-3 py-1.5 border border-slate-600"
            >
              {engagements.map((e) => (
                <option key={e.engagement_id} value={e.engagement_id}>
                  {e.engagement_id} ({e.state})
                </option>
              ))}
            </select>
          )}
          <button
            onClick={onCreateEngagement}
            disabled={creating}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-cyan-600 hover:bg-cyan-500 disabled:bg-gray-600 text-white text-xs font-medium rounded-lg transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            {creating ? 'Creating...' : 'New Engagement'}
          </button>
        </div>
      </div>

      {displayEngagement && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <StatusCard label="Engagement ID" value={displayEngagement.engagement_id} mono />
          <StatusCard label="Status">
            <StatusBadge status={displayEngagement.state} pulse={displayEngagement.state === 'active'} />
          </StatusCard>
          <StatusCard label="Entity A" value={displayEngagement.entity_a_name || displayEngagement.entity_a} />
          <StatusCard label="Entity B" value={displayEngagement.entity_b_name || displayEngagement.entity_b} />
          <StatusCard label="Created" value={relativeTime(displayEngagement.created_at)} />
          <StatusCard label="Maestra Status">
            {maestraStatus ? (
              <StatusBadge status={maestraStatus.status} />
            ) : (
              <span className="text-gray-500 text-sm">\u2014</span>
            )}
          </StatusCard>
        </div>
      )}
    </div>
  );
}

function StatusCard({ label, value, mono, children }: { label: string; value?: string; mono?: boolean; children?: React.ReactNode }) {
  return (
    <div className="bg-slate-700/30 rounded-lg p-3">
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      {children || (
        <div className={`text-sm text-white truncate ${mono ? 'font-mono' : ''}`} title={value}>
          {value || '\u2014'}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Panel 2: Run Ledger
// ============================================================================

function RunLedgerPanel({
  steps,
  loading,
  error,
  autoRefresh,
  onToggleAutoRefresh,
  onRefresh,
}: {
  steps: LedgerStep[];
  loading: boolean;
  error: string | null;
  autoRefresh: boolean;
  onToggleAutoRefresh: () => void;
  onRefresh: () => void;
}) {
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set());

  const toggleStep = (stepId: string) => {
    setExpandedSteps((prev) => {
      const next = new Set(prev);
      if (next.has(stepId)) next.delete(stepId);
      else next.add(stepId);
      return next;
    });
  };

  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
          <Clock className="w-5 h-5 text-purple-400" />
          Run Ledger
        </h2>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={onToggleAutoRefresh}
              className="rounded border-slate-600 bg-slate-700 text-cyan-500 focus:ring-cyan-500"
            />
            Auto-refresh
          </label>
          <button
            onClick={onRefresh}
            className="p-1.5 text-gray-400 hover:text-white hover:bg-slate-700 rounded-lg transition-colors"
            title="Refresh now"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 mb-4 text-red-400 text-sm">
          {error}
        </div>
      )}

      {steps.length === 0 && !error ? (
        <div className="text-center py-8 text-gray-500">No steps recorded</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-500 text-xs uppercase tracking-wider border-b border-slate-700/50">
                <th className="text-left py-2 px-3">Step Name</th>
                <th className="text-left py-2 px-3">Status</th>
                <th className="text-left py-2 px-3">Source Run Tag</th>
                <th className="text-left py-2 px-3">Started</th>
                <th className="text-left py-2 px-3">Completed</th>
                <th className="text-left py-2 px-3">Duration</th>
                <th className="text-left py-2 px-3">Error</th>
              </tr>
            </thead>
            <tbody>
              {steps.map((step) => {
                const isExpanded = expandedSteps.has(step.step_id);
                // All rows are expandable for drill-through
                const hasError = step.status === 'failed' && step.error;
                const hasDeps = step.upstream_deps && step.upstream_deps.length > 0;

                return (
                  <Fragment key={step.step_id}>
                    <tr
                      className="border-b border-slate-700/30 hover:bg-slate-700/20 transition-colors cursor-pointer"
                      onClick={() => toggleStep(step.step_id)}
                    >
                      <td className="py-2.5 px-3">
                        <div className="flex items-center gap-2">
                          {isExpanded
                            ? <ChevronDown className="w-3.5 h-3.5 text-gray-500 flex-shrink-0" />
                            : <ChevronRight className="w-3.5 h-3.5 text-gray-500 flex-shrink-0" />
                          }
                          <span className="text-white font-medium">{step.step_name}</span>
                        </div>
                      </td>
                      <td className="py-2.5 px-3">
                        <StatusBadge status={step.status} pulse={step.status === 'running'} />
                      </td>
                      <td className="py-2.5 px-3">
                        {step.outputs_ref ? (
                          <span className="text-amber-400 font-mono text-xs bg-amber-500/10 border border-amber-500/20 px-1.5 py-0.5 rounded">
                            {step.outputs_ref}
                          </span>
                        ) : (
                          <span className="text-gray-600">{'\u2014'}</span>
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-gray-400 font-mono text-xs">{formatTime(step.started_at)}</td>
                      <td className="py-2.5 px-3 text-gray-400 font-mono text-xs">{formatTime(step.completed_at)}</td>
                      <td className="py-2.5 px-3 text-gray-400">{durationBetween(step.started_at, step.completed_at)}</td>
                      <td className="py-2.5 px-3">
                        {step.error ? (
                          <span className="text-red-400 text-xs truncate block max-w-[150px]" title={step.error}>
                            {step.error}
                          </span>
                        ) : (
                          <span className="text-gray-600">{'\u2014'}</span>
                        )}
                      </td>
                    </tr>
                    {isExpanded && (
                      <tr key={`${step.step_id}-detail`} className="bg-slate-700/10">
                        <td colSpan={7} className="px-6 py-3">
                          <div className="space-y-3">
                            {/* Step details */}
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                              <div className="bg-slate-700/30 rounded p-2">
                                <div className="text-gray-500 mb-0.5">Step ID</div>
                                <div className="text-white font-mono">{step.step_id}</div>
                              </div>
                              <div className="bg-slate-700/30 rounded p-2">
                                <div className="text-gray-500 mb-0.5">Idempotency Key</div>
                                <div className="text-white font-mono truncate" title={step.idempotency_key}>{step.idempotency_key}</div>
                              </div>
                              <div className="bg-slate-700/30 rounded p-2">
                                <div className="text-gray-500 mb-0.5">Inputs Hash</div>
                                <div className="text-white font-mono truncate" title={step.inputs_hash}>{step.inputs_hash || '\u2014'}</div>
                              </div>
                              <div className="bg-slate-700/30 rounded p-2">
                                <div className="text-gray-500 mb-0.5">Outputs Ref</div>
                                <div className="text-amber-400 font-mono truncate" title={step.outputs_ref || ''}>{step.outputs_ref || '\u2014'}</div>
                              </div>
                            </div>
                            {/* Upstream dependencies */}
                            {hasDeps && (
                              <div className="bg-slate-700/30 rounded p-2">
                                <div className="text-xs text-gray-500 mb-1">Upstream Dependencies</div>
                                <div className="flex flex-wrap gap-1">
                                  {step.upstream_deps!.map((dep) => (
                                    <span key={dep} className="bg-slate-600 px-2 py-0.5 rounded text-xs text-gray-300 font-mono">
                                      {dep}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}
                            {/* Error details */}
                            {hasError && (
                              <div className="bg-red-500/10 border border-red-500/20 rounded p-3">
                                <div className="text-xs text-red-400 font-mono whitespace-pre-wrap">
                                  {step.error}
                                </div>
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Panel 3: Human Review Queue
// ============================================================================

function ReviewQueuePanel({
  reviews,
  loading,
  error,
  onApprove,
  onReject,
}: {
  reviews: Review[];
  loading: boolean;
  error: string | null;
  onApprove: (reviewId: string) => void;
  onReject: (reviewId: string) => void;
}) {
  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
      <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
        <AlertTriangle className="w-5 h-5 text-amber-400" />
        Human Review Queue
      </h2>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 mb-4 text-red-400 text-sm">
          {error}
        </div>
      )}

      {reviews.length === 0 && !error ? (
        <div className="text-center py-8 text-gray-500">No pending reviews</div>
      ) : (
        <div className="space-y-3">
          {reviews.map((review) => (
            <ReviewCard
              key={review.review_id}
              review={review}
              onApprove={() => onApprove(review.review_id)}
              onReject={() => onReject(review.review_id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function ReviewCard({
  review,
  onApprove,
  onReject,
}: {
  review: Review;
  onApprove: () => void;
  onReject: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const isPending = review.status === 'pending';
  const tierColor = TIER_COLORS[review.tier] || TIER_COLORS[3];

  return (
    <div className="bg-slate-700/30 rounded-lg border border-slate-600/30 p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <StatusBadge status={review.status} />
            <span className="text-white font-medium text-sm">{review.action}</span>
          </div>
          <div className="flex items-center gap-3 text-xs text-gray-500 mb-2">
            <span className={`px-2 py-0.5 rounded ${tierColor} text-xs font-medium`}>
              Tier {review.tier}
            </span>
            <span>Requested by: {review.requested_by}</span>
            <span>{relativeTime(review.created_at)}</span>
          </div>

          {/* Context (expandable) */}
          {review.context && Object.keys(review.context).length > 0 && (
            <>
              <button
                onClick={() => setExpanded(!expanded)}
                className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-300 transition-colors"
              >
                <Eye className="w-3 h-3" />
                {expanded ? 'Hide' : 'View'} context
              </button>
              {expanded && (
                <pre className="mt-2 bg-slate-800 rounded p-3 text-xs text-gray-300 font-mono overflow-x-auto max-h-48">
                  {JSON.stringify(review.context, null, 2)}
                </pre>
              )}
            </>
          )}

          {review.reason && (
            <div className="mt-2 text-xs text-gray-400">
              Reason: {review.reason}
            </div>
          )}
        </div>

        {isPending && (
          <div className="flex items-center gap-2 flex-shrink-0">
            <button
              onClick={onApprove}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-green-600/20 hover:bg-green-600/30 text-green-400 text-xs font-medium rounded-lg border border-green-500/30 transition-colors"
            >
              <CheckCircle className="w-3.5 h-3.5" />
              Approve
            </button>
            <button
              onClick={onReject}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-red-600/20 hover:bg-red-600/30 text-red-400 text-xs font-medium rounded-lg border border-red-500/30 transition-colors"
            >
              <XCircle className="w-3.5 h-3.5" />
              Reject
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// Panel 4: Constitution & Tools
// ============================================================================

const TOOL_DEFINITIONS: ToolDefinition[] = [
  { name: 'check_module_status', description: 'Check health and readiness of an AOS module', parameters: { module: 'aod|aam|dcl|nlq|farm' } },
  { name: 'trigger_pipeline_run', description: 'Trigger a pipeline run for specified entities', parameters: { entities: 'list[str]', run_type: 'full|incremental' } },
  { name: 'get_engagement_state', description: 'Get current engagement state and progress', parameters: { engagement_id: 'str' } },
  { name: 'request_human_review', description: 'Escalate a decision for human review', parameters: { decision_type: 'str', context: 'dict', urgency: 'low|medium|high|critical' } },
  { name: 'update_run_ledger', description: 'Record a step completion or failure in the run ledger', parameters: { step_name: 'str', status: 'str', outputs_ref: 'str|None' } },
];

function ConstitutionToolsPanel({
  constitution,
  constitutionError,
  onExecuteTool,
  toolResults,
}: {
  constitution: Constitution | null;
  constitutionError: string | null;
  onExecuteTool: (toolName: string) => void;
  toolResults: Record<string, { status: string; result?: unknown; error?: string }>;
}) {
  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
      <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
        <Activity className="w-5 h-5 text-green-400" />
        Constitution & Tools
      </h2>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Constitution (left) */}
        <div>
          <h3 className="text-sm font-medium text-gray-400 mb-3">Constitution Rules</h3>
          {constitutionError ? (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-red-400 text-sm">
              {constitutionError}
            </div>
          ) : constitution ? (
            <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
              {constitution.rules.map((rule, i) => (
                <div key={i} className="bg-slate-700/30 rounded-lg p-3">
                  <div className="text-xs text-gray-500 mb-1">Rule {i + 1}</div>
                  <div className="text-sm text-gray-200">{rule}</div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-gray-500 text-sm">Loading...</div>
          )}
        </div>

        {/* Tools (right) */}
        <div>
          <h3 className="text-sm font-medium text-gray-400 mb-3">Available Tools</h3>
          <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
            {TOOL_DEFINITIONS.map((tool) => {
              const result = toolResults[tool.name];
              const isRunning = result?.status === 'running';
              return (
                <button
                  key={tool.name}
                  onClick={() => onExecuteTool(tool.name)}
                  disabled={isRunning}
                  className="w-full text-left bg-slate-700/30 rounded-lg p-3 hover:bg-slate-700/50 transition-colors border border-transparent hover:border-cyan-500/30 disabled:opacity-50 disabled:cursor-wait"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm text-white font-mono">{tool.name}</span>
                    {isRunning && (
                      <div className="w-3 h-3 border border-cyan-400 border-t-transparent rounded-full animate-spin" />
                    )}
                    {result?.status === 'done' && (
                      <CheckCircle className="w-3.5 h-3.5 text-green-400" />
                    )}
                    {result?.status === 'error' && (
                      <XCircle className="w-3.5 h-3.5 text-red-400" />
                    )}
                  </div>
                  <div className="text-xs text-gray-400">{tool.description}</div>
                  <div className="mt-1.5 flex flex-wrap gap-1">
                    {Object.entries(tool.parameters).map(([k, v]) => (
                      <span key={k} className="text-xs bg-slate-600/50 text-gray-400 px-1.5 py-0.5 rounded font-mono">
                        {k}: {v}
                      </span>
                    ))}
                  </div>
                  {result?.status === 'done' && result.result && (
                    <pre className="mt-2 bg-slate-800 rounded p-2 text-xs text-gray-300 font-mono overflow-x-auto max-h-24">
                      {typeof result.result === 'string' ? result.result : JSON.stringify(result.result, null, 2)}
                    </pre>
                  )}
                  {result?.status === 'error' && result.error && (
                    <div className="mt-2 text-xs text-red-400">{result.error}</div>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export default function MaestraMonitor() {
  // Engagement state
  const [engagements, setEngagements] = useState<Engagement[]>([]);
  const [selectedEngagementId, setSelectedEngagementId] = useState<string | null>(null);
  const [maestraStatus, setMaestraStatus] = useState<MaestraStatus | null>(null);
  const [creating, setCreating] = useState(false);

  // Run ledger state
  const [steps, setSteps] = useState<LedgerStep[]>([]);
  const [stepsLoading, setStepsLoading] = useState(false);
  const [stepsError, setStepsError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  // Reviews state
  const [reviews, setReviews] = useState<Review[]>([]);
  const [reviewsError, setReviewsError] = useState<string | null>(null);

  // Constitution state
  const [constitution, setConstitution] = useState<Constitution | null>(null);
  const [constitutionError, setConstitutionError] = useState<string | null>(null);

  // Tool execution state
  const [toolResults, setToolResults] = useState<Record<string, { status: string; result?: unknown; error?: string }>>({});

  // Loading state
  const [initialLoading, setInitialLoading] = useState(true);

  // Polling ref
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Determine the engagement to display in the ledger
  const activeEngagement = engagements.find(e => e.state === 'active');
  const currentEngagementId = selectedEngagementId || activeEngagement?.engagement_id || engagements[0]?.engagement_id || null;

  // Fetch engagements
  const fetchEngagements = useCallback(async () => {
    try {
      const data = await apiFetch<Engagement[]>('/engagements');
      setEngagements(data);
    } catch {
      // Engagements endpoint failing is not fatal — might just be empty
      setEngagements([]);
    }
  }, []);

  // Fetch status
  const fetchStatus = useCallback(async () => {
    try {
      const data = await apiFetch<MaestraStatus>('/status');
      setMaestraStatus(data);
    } catch {
      setMaestraStatus(null);
    }
  }, []);

  // Fetch run ledger for current engagement
  const fetchLedger = useCallback(async () => {
    if (!currentEngagementId) {
      setSteps([]);
      return;
    }
    setStepsLoading(true);
    try {
      const data = await apiFetch<LedgerStep[]>(`/run-ledger/${currentEngagementId}`);
      // Sort by created_at descending
      data.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
      setSteps(data);
      setStepsError(null);
    } catch (err: any) {
      setStepsError(err.message);
    } finally {
      setStepsLoading(false);
    }
  }, [currentEngagementId]);

  // Fetch reviews
  const fetchReviews = useCallback(async () => {
    try {
      const data = await apiFetch<Review[]>('/reviews');
      setReviews(data);
      setReviewsError(null);
    } catch (err: any) {
      setReviewsError(err.message);
    }
  }, []);

  // Fetch constitution (once)
  const fetchConstitution = useCallback(async () => {
    try {
      const data = await apiFetch<Constitution>('/constitution');
      setConstitution(data);
      setConstitutionError(null);
    } catch (err: any) {
      setConstitutionError(err.message);
    }
  }, []);

  // Initial load
  useEffect(() => {
    Promise.all([fetchEngagements(), fetchStatus(), fetchReviews(), fetchConstitution()]).finally(() => {
      setInitialLoading(false);
    });
  }, [fetchEngagements, fetchStatus, fetchReviews, fetchConstitution]);

  // Fetch ledger when currentEngagementId changes
  useEffect(() => {
    fetchLedger();
  }, [fetchLedger]);

  // Auto-refresh polling
  useEffect(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }

    if (!autoRefresh) return;

    // Check if we should poll: any step running or pending
    const shouldPoll = steps.some(s => s.status === 'running' || s.status === 'pending') || autoRefresh;

    if (shouldPoll) {
      pollTimerRef.current = setInterval(() => {
        fetchEngagements();
        fetchStatus();
        fetchLedger();
        fetchReviews();
      }, 5000);
    }

    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    };
  }, [autoRefresh, steps, fetchEngagements, fetchStatus, fetchLedger, fetchReviews]);

  // Create engagement
  const handleCreateEngagement = async () => {
    setCreating(true);
    try {
      const id = `eng-${Date.now().toString(36)}`;
      await apiFetch<Engagement>('/engagements', {
        method: 'POST',
        body: JSON.stringify({
          engagement_id: id,
          entity_a: 'meridian',
          entity_b: 'cascadia',
          entity_a_name: 'Meridian Partners',
          entity_b_name: 'Cascadia Process Solutions',
          created_by: 'monitoring-ui',
        }),
      });
      await fetchEngagements();
      setSelectedEngagementId(id);
    } catch (err: any) {
      console.error('Failed to create engagement:', err.message);
    } finally {
      setCreating(false);
    }
  };

  // Approve review
  const handleApprove = async (reviewId: string) => {
    try {
      await apiFetch(`/reviews/${reviewId}/approve`, {
        method: 'PATCH',
        body: JSON.stringify({ approved_by: 'monitoring-ui' }),
      });
      await fetchReviews();
    } catch (err: any) {
      console.error('Failed to approve review:', err.message);
    }
  };

  // Reject review
  const handleReject = async (reviewId: string) => {
    const reason = window.prompt('Reason for rejection:');
    if (!reason) return;
    try {
      await apiFetch(`/reviews/${reviewId}/reject`, {
        method: 'PATCH',
        body: JSON.stringify({ rejected_by: 'monitoring-ui', reason }),
      });
      await fetchReviews();
    } catch (err: any) {
      console.error('Failed to reject review:', err.message);
    }
  };

  // Execute a tool — maps tool name to its API action with default params
  const handleExecuteTool = async (toolName: string) => {
    setToolResults((prev) => ({ ...prev, [toolName]: { status: 'running' } }));
    try {
      let result: unknown;
      switch (toolName) {
        case 'check_module_status': {
          // Check all modules in sequence
          const modules = ['dcl', 'farm', 'nlq', 'aod', 'aam'];
          const statuses: Record<string, string> = {};
          for (const mod of modules) {
            try {
              const res = await fetch(`/api/${mod === 'farm' ? 'business-data' : mod}/health`);
              statuses[mod] = res.ok ? 'healthy' : `HTTP ${res.status}`;
            } catch {
              statuses[mod] = 'unreachable';
            }
          }
          result = statuses;
          break;
        }
        case 'get_engagement_state': {
          if (currentEngagementId) {
            result = await apiFetch(`/engagements/${currentEngagementId}`);
          } else {
            result = { message: 'No engagement selected' };
          }
          break;
        }
        case 'trigger_pipeline_run': {
          result = { message: 'Pipeline trigger requires Farm service. Use Farm UI to generate triples.' };
          break;
        }
        case 'request_human_review': {
          result = { message: 'Human review requests are created by Maestra during COFA unification.' };
          break;
        }
        case 'update_run_ledger': {
          if (currentEngagementId) {
            result = await apiFetch<LedgerStep[]>(`/run-ledger/${currentEngagementId}`);
          } else {
            result = { message: 'No engagement selected' };
          }
          break;
        }
        default:
          result = { message: `Unknown tool: ${toolName}` };
      }
      setToolResults((prev) => ({ ...prev, [toolName]: { status: 'done', result } }));
    } catch (err: any) {
      setToolResults((prev) => ({ ...prev, [toolName]: { status: 'error', error: err.message } }));
    }
  };

  if (initialLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="flex flex-col items-center gap-4">
          <div className="w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-gray-400 text-sm">Loading Maestra monitoring...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-pink-600 rounded-xl flex items-center justify-center shadow-lg shadow-purple-500/20">
          <span className="text-white font-bold text-lg">M</span>
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white">Maestra Monitor</h1>
          <p className="text-gray-400 text-sm">
            Engagement orchestration, run ledger, human reviews, and constitution
          </p>
        </div>
      </div>

      {/* Panel 1: Engagement Status */}
      <EngagementStatusPanel
        engagements={engagements}
        maestraStatus={maestraStatus}
        onCreateEngagement={handleCreateEngagement}
        creating={creating}
        selectedEngagementId={selectedEngagementId}
        onSelectEngagement={setSelectedEngagementId}
      />

      {/* Panel 2: Run Ledger */}
      <RunLedgerPanel
        steps={steps}
        loading={stepsLoading}
        error={stepsError}
        autoRefresh={autoRefresh}
        onToggleAutoRefresh={() => setAutoRefresh(!autoRefresh)}
        onRefresh={() => {
          fetchLedger();
          fetchEngagements();
          fetchStatus();
          fetchReviews();
        }}
      />

      {/* Panel 3: Human Review Queue */}
      <ReviewQueuePanel
        reviews={reviews}
        loading={false}
        error={reviewsError}
        onApprove={handleApprove}
        onReject={handleReject}
      />

      {/* Panel 4: Constitution & Tools */}
      <ConstitutionToolsPanel
        constitution={constitution}
        constitutionError={constitutionError}
        onExecuteTool={handleExecuteTool}
        toolResults={toolResults}
      />

      {/* Footer */}
      <div className="text-center py-4 text-xs text-slate-500">
        {autoRefresh ? 'Auto-refreshing every 5 seconds.' : 'Auto-refresh paused.'}{' '}
        All data from live Maestra endpoints.
      </div>
    </div>
  );
}
