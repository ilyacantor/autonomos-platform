/**
 * Scheduler Manager Component
 *
 * Manages scheduled agent jobs:
 * - Create/edit/delete scheduled jobs
 * - View job execution history
 * - Manual job triggers
 * - Cron expression validation
 */

import { useState, useEffect, useCallback } from 'react';
import {
  Clock,
  Play,
  Pause,
  Trash2,
  Plus,
  RefreshCw,
  Calendar,
  CheckCircle,
  XCircle,
  AlertCircle,
  Zap,
  ChevronDown,
  ChevronUp,
  Settings,
  History,
} from 'lucide-react';

// Types
interface JobTrigger {
  trigger_type: 'cron' | 'interval' | 'once' | 'webhook' | 'event';
  cron_expression?: string;
  timezone?: string;
  interval_seconds?: number;
  run_at?: string;
  event_type?: string;
  webhook_secret?: string;
}

interface ScheduledJob {
  job_id: string;
  tenant_id: string;
  name: string;
  description?: string;
  agent_id: string;
  input_template?: string;
  trigger: JobTrigger;
  status: 'active' | 'paused' | 'disabled' | 'expired';
  timeout_seconds: number;
  max_retries: number;
  allow_concurrent: boolean;
  run_count: number;
  last_run_at?: string;
  next_run_at?: string;
  created_at: string;
  updated_at: string;
}

interface JobExecution {
  execution_id: string;
  job_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'timeout' | 'cancelled';
  started_at?: string;
  completed_at?: string;
  error_message?: string;
  retry_count: number;
}

interface CronValidation {
  valid: boolean;
  error?: string;
  description?: string;
  next_runs?: string[];
}

// API helpers
const API_BASE = '/api/v1/scheduler';

async function fetchJobs(): Promise<ScheduledJob[]> {
  const response = await fetch(`${API_BASE}/jobs`);
  if (!response.ok) throw new Error('Failed to fetch jobs');
  const data = await response.json();
  return data.jobs;
}

async function fetchExecutions(jobId: string): Promise<JobExecution[]> {
  const response = await fetch(`${API_BASE}/jobs/${jobId}/executions`);
  if (!response.ok) throw new Error('Failed to fetch executions');
  const data = await response.json();
  return data.executions;
}

async function validateCron(expression: string): Promise<CronValidation> {
  const response = await fetch(`${API_BASE}/cron/validate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ expression }),
  });
  return response.json();
}

async function createJob(jobData: any): Promise<ScheduledJob> {
  const response = await fetch(`${API_BASE}/jobs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(jobData),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to create job');
  }
  return response.json();
}

async function pauseJob(jobId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/jobs/${jobId}/pause`, { method: 'POST' });
  if (!response.ok) throw new Error('Failed to pause job');
}

async function resumeJob(jobId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/jobs/${jobId}/resume`, { method: 'POST' });
  if (!response.ok) throw new Error('Failed to resume job');
}

async function deleteJob(jobId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/jobs/${jobId}`, { method: 'DELETE' });
  if (!response.ok) throw new Error('Failed to delete job');
}

async function triggerJob(jobId: string): Promise<string> {
  const response = await fetch(`${API_BASE}/jobs/${jobId}/trigger`, { method: 'POST' });
  if (!response.ok) throw new Error('Failed to trigger job');
  const data = await response.json();
  return data.execution_id;
}

// Status badge component
function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    active: 'bg-green-500/20 text-green-400',
    paused: 'bg-yellow-500/20 text-yellow-400',
    disabled: 'bg-gray-500/20 text-gray-400',
    expired: 'bg-red-500/20 text-red-400',
    pending: 'bg-blue-500/20 text-blue-400',
    running: 'bg-purple-500/20 text-purple-400',
    completed: 'bg-green-500/20 text-green-400',
    failed: 'bg-red-500/20 text-red-400',
    timeout: 'bg-orange-500/20 text-orange-400',
    cancelled: 'bg-gray-500/20 text-gray-400',
  };

  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${colors[status] || 'bg-gray-500/20 text-gray-400'}`}>
      {status}
    </span>
  );
}

// Trigger type badge
function TriggerBadge({ type }: { type: string }) {
  const icons: Record<string, React.ReactNode> = {
    cron: <Calendar className="w-3 h-3" />,
    interval: <RefreshCw className="w-3 h-3" />,
    once: <Clock className="w-3 h-3" />,
    webhook: <Zap className="w-3 h-3" />,
    event: <AlertCircle className="w-3 h-3" />,
  };

  return (
    <span className="flex items-center gap-1 px-2 py-0.5 bg-purple-500/20 text-purple-400 rounded text-xs font-medium">
      {icons[type]}
      {type}
    </span>
  );
}

// Job row component
function JobRow({
  job,
  expanded,
  onToggle,
  onPause,
  onResume,
  onDelete,
  onTrigger,
}: {
  job: ScheduledJob;
  expanded: boolean;
  onToggle: () => void;
  onPause: () => void;
  onResume: () => void;
  onDelete: () => void;
  onTrigger: () => void;
}) {
  const [executions, setExecutions] = useState<JobExecution[]>([]);
  const [loadingExecs, setLoadingExecs] = useState(false);

  useEffect(() => {
    if (expanded) {
      setLoadingExecs(true);
      fetchExecutions(job.job_id)
        .then(setExecutions)
        .catch(console.error)
        .finally(() => setLoadingExecs(false));
    }
  }, [expanded, job.job_id]);

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleString();
  };

  return (
    <div className="border border-gray-700 rounded-lg overflow-hidden">
      {/* Job Header */}
      <div
        className="flex items-center gap-4 p-4 bg-gray-800/50 cursor-pointer hover:bg-gray-800"
        onClick={onToggle}
      >
        <button className="text-gray-400">
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="font-medium text-white truncate">{job.name}</h3>
            <StatusBadge status={job.status} />
            <TriggerBadge type={job.trigger.trigger_type} />
          </div>
          <p className="text-sm text-gray-400 truncate mt-0.5">
            {job.description || `Agent: ${job.agent_id}`}
          </p>
        </div>

        <div className="hidden md:flex items-center gap-6 text-sm">
          <div className="text-center">
            <div className="text-gray-400 text-xs">Runs</div>
            <div className="text-white font-medium">{job.run_count}</div>
          </div>
          <div className="text-center">
            <div className="text-gray-400 text-xs">Last Run</div>
            <div className="text-white text-xs">{formatDate(job.last_run_at)}</div>
          </div>
          <div className="text-center">
            <div className="text-gray-400 text-xs">Next Run</div>
            <div className="text-cyan-400 text-xs">{formatDate(job.next_run_at)}</div>
          </div>
        </div>

        <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
          <button
            onClick={onTrigger}
            className="p-2 text-cyan-400 hover:bg-cyan-500/20 rounded-lg transition-colors"
            title="Run Now"
          >
            <Play className="w-4 h-4" />
          </button>
          {job.status === 'active' ? (
            <button
              onClick={onPause}
              className="p-2 text-yellow-400 hover:bg-yellow-500/20 rounded-lg transition-colors"
              title="Pause"
            >
              <Pause className="w-4 h-4" />
            </button>
          ) : job.status === 'paused' ? (
            <button
              onClick={onResume}
              className="p-2 text-green-400 hover:bg-green-500/20 rounded-lg transition-colors"
              title="Resume"
            >
              <Play className="w-4 h-4" />
            </button>
          ) : null}
          <button
            onClick={onDelete}
            className="p-2 text-red-400 hover:bg-red-500/20 rounded-lg transition-colors"
            title="Delete"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Expanded Details */}
      {expanded && (
        <div className="border-t border-gray-700 p-4 bg-gray-900/50">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Job Details */}
            <div>
              <h4 className="text-sm font-medium text-gray-300 mb-3 flex items-center gap-2">
                <Settings className="w-4 h-4" />
                Configuration
              </h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">Agent ID</span>
                  <span className="text-white font-mono">{job.agent_id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Trigger Type</span>
                  <span className="text-white">{job.trigger.trigger_type}</span>
                </div>
                {job.trigger.cron_expression && (
                  <div className="flex justify-between">
                    <span className="text-gray-400">Cron Expression</span>
                    <span className="text-white font-mono">{job.trigger.cron_expression}</span>
                  </div>
                )}
                {job.trigger.interval_seconds && (
                  <div className="flex justify-between">
                    <span className="text-gray-400">Interval</span>
                    <span className="text-white">{job.trigger.interval_seconds}s</span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span className="text-gray-400">Timeout</span>
                  <span className="text-white">{job.timeout_seconds}s</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Max Retries</span>
                  <span className="text-white">{job.max_retries}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Concurrent</span>
                  <span className="text-white">{job.allow_concurrent ? 'Yes' : 'No'}</span>
                </div>
              </div>
            </div>

            {/* Recent Executions */}
            <div>
              <h4 className="text-sm font-medium text-gray-300 mb-3 flex items-center gap-2">
                <History className="w-4 h-4" />
                Recent Executions
              </h4>
              {loadingExecs ? (
                <div className="text-sm text-gray-400">Loading...</div>
              ) : executions.length === 0 ? (
                <div className="text-sm text-gray-400">No executions yet</div>
              ) : (
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {executions.slice(0, 5).map((exec) => (
                    <div
                      key={exec.execution_id}
                      className="flex items-center gap-3 p-2 bg-gray-800/50 rounded-lg"
                    >
                      {exec.status === 'completed' ? (
                        <CheckCircle className="w-4 h-4 text-green-400" />
                      ) : exec.status === 'failed' ? (
                        <XCircle className="w-4 h-4 text-red-400" />
                      ) : exec.status === 'running' ? (
                        <RefreshCw className="w-4 h-4 text-purple-400 animate-spin" />
                      ) : (
                        <Clock className="w-4 h-4 text-gray-400" />
                      )}
                      <div className="flex-1 min-w-0">
                        <div className="text-xs text-white font-mono truncate">
                          {exec.execution_id.slice(0, 8)}...
                        </div>
                        <div className="text-xs text-gray-400">
                          {formatDate(exec.started_at)}
                        </div>
                      </div>
                      <StatusBadge status={exec.status} />
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Input Template Preview */}
          {job.input_template && (
            <div className="mt-4">
              <h4 className="text-sm font-medium text-gray-300 mb-2">Input Template</h4>
              <pre className="p-3 bg-gray-800 rounded-lg text-xs text-gray-300 overflow-x-auto">
                {job.input_template}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Create Job Modal
function CreateJobModal({
  onClose,
  onCreate,
}: {
  onClose: () => void;
  onCreate: (job: any) => void;
}) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [agentId, setAgentId] = useState('default');
  const [triggerType, setTriggerType] = useState<string>('cron');
  const [cronExpression, setCronExpression] = useState('0 9 * * *');
  const [intervalSeconds, setIntervalSeconds] = useState(3600);
  const [inputTemplate, setInputTemplate] = useState('');
  const [cronValidation, setCronValidation] = useState<CronValidation | null>(null);
  const [validating, setValidating] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Validate cron expression
  useEffect(() => {
    if (triggerType === 'cron' && cronExpression) {
      setValidating(true);
      const timer = setTimeout(() => {
        validateCron(cronExpression)
          .then(setCronValidation)
          .catch(() => setCronValidation({ valid: false, error: 'Validation failed' }))
          .finally(() => setValidating(false));
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [cronExpression, triggerType]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setCreating(true);

    try {
      const jobData = {
        name,
        description: description || undefined,
        agent_id: agentId,
        input_template: inputTemplate || undefined,
        trigger: {
          trigger_type: triggerType,
          cron_expression: triggerType === 'cron' ? cronExpression : undefined,
          interval_seconds: triggerType === 'interval' ? intervalSeconds : undefined,
        },
        timeout_seconds: 300,
        max_retries: 3,
        allow_concurrent: false,
      };

      await createJob(jobData);
      onCreate(jobData);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-xl border border-gray-700 w-full max-w-xl max-h-[90vh] overflow-y-auto">
        <div className="p-4 border-b border-gray-700 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">Create Scheduled Job</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white">
            <XCircle className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          {error && (
            <div className="p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400 text-sm">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Job Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
              placeholder="Daily Report Generator"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Description</label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
              placeholder="Generates daily summary reports"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Agent ID</label>
            <input
              type="text"
              value={agentId}
              onChange={(e) => setAgentId(e.target.value)}
              required
              className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
              placeholder="default"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Trigger Type</label>
            <select
              value={triggerType}
              onChange={(e) => setTriggerType(e.target.value)}
              className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
            >
              <option value="cron">Cron Schedule</option>
              <option value="interval">Fixed Interval</option>
              <option value="webhook">Webhook</option>
              <option value="event">Event-based</option>
            </select>
          </div>

          {triggerType === 'cron' && (
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Cron Expression
              </label>
              <input
                type="text"
                value={cronExpression}
                onChange={(e) => setCronExpression(e.target.value)}
                className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white font-mono focus:outline-none focus:ring-2 focus:ring-purple-500"
                placeholder="0 9 * * *"
              />
              {validating ? (
                <p className="text-xs text-gray-400 mt-1">Validating...</p>
              ) : cronValidation ? (
                <div className="mt-2">
                  {cronValidation.valid ? (
                    <div className="text-xs">
                      <p className="text-green-400">{cronValidation.description}</p>
                      {cronValidation.next_runs && (
                        <p className="text-gray-400 mt-1">
                          Next: {new Date(cronValidation.next_runs[0]).toLocaleString()}
                        </p>
                      )}
                    </div>
                  ) : (
                    <p className="text-xs text-red-400">{cronValidation.error}</p>
                  )}
                </div>
              ) : null}
            </div>
          )}

          {triggerType === 'interval' && (
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Interval (seconds)
              </label>
              <input
                type="number"
                value={intervalSeconds}
                onChange={(e) => setIntervalSeconds(Number(e.target.value))}
                min={60}
                className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
              <p className="text-xs text-gray-400 mt-1">
                Run every {Math.floor(intervalSeconds / 60)} minutes
              </p>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Input Template (optional)
            </label>
            <textarea
              value={inputTemplate}
              onChange={(e) => setInputTemplate(e.target.value)}
              rows={3}
              className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white font-mono text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
              placeholder="Generate a report for {{date}}"
            />
          </div>

          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={creating || (triggerType === 'cron' && !cronValidation?.valid)}
              className="flex-1 px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
            >
              {creating ? 'Creating...' : 'Create Job'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Main Scheduler Manager component
export default function SchedulerManager() {
  const [jobs, setJobs] = useState<ScheduledJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedJobId, setExpandedJobId] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);

  const loadJobs = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchJobs();
      setJobs(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadJobs();
  }, [loadJobs]);

  const handlePause = async (jobId: string) => {
    try {
      await pauseJob(jobId);
      loadJobs();
    } catch (err: any) {
      alert(`Failed to pause job: ${err.message}`);
    }
  };

  const handleResume = async (jobId: string) => {
    try {
      await resumeJob(jobId);
      loadJobs();
    } catch (err: any) {
      alert(`Failed to resume job: ${err.message}`);
    }
  };

  const handleDelete = async (jobId: string) => {
    if (!confirm('Are you sure you want to delete this job?')) return;
    try {
      await deleteJob(jobId);
      loadJobs();
    } catch (err: any) {
      alert(`Failed to delete job: ${err.message}`);
    }
  };

  const handleTrigger = async (jobId: string) => {
    try {
      const executionId = await triggerJob(jobId);
      alert(`Job triggered! Execution ID: ${executionId}`);
      loadJobs();
    } catch (err: any) {
      alert(`Failed to trigger job: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Clock className="w-6 h-6 text-purple-400" />
          <div>
            <h2 className="text-xl font-semibold text-white">Scheduled Jobs</h2>
            <p className="text-sm text-gray-400">Manage automated agent executions</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={loadJobs}
            className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
            title="Refresh"
          >
            <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" />
            New Job
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Total Jobs', value: jobs.length, color: 'text-white' },
          { label: 'Active', value: jobs.filter((j) => j.status === 'active').length, color: 'text-green-400' },
          { label: 'Paused', value: jobs.filter((j) => j.status === 'paused').length, color: 'text-yellow-400' },
          { label: 'Total Runs', value: jobs.reduce((sum, j) => sum + j.run_count, 0), color: 'text-cyan-400' },
        ].map((stat, i) => (
          <div key={i} className="bg-gray-800/50 rounded-lg border border-gray-700 p-4">
            <div className="text-sm text-gray-400">{stat.label}</div>
            <div className={`text-2xl font-bold ${stat.color}`}>{stat.value}</div>
          </div>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400">
          {error}
        </div>
      )}

      {/* Jobs List */}
      {loading && jobs.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-2" />
          Loading scheduled jobs...
        </div>
      ) : jobs.length === 0 ? (
        <div className="text-center py-12 bg-gray-800/30 rounded-lg border border-gray-700">
          <Calendar className="w-12 h-12 text-gray-600 mx-auto mb-3" />
          <h3 className="text-lg font-medium text-gray-400 mb-1">No Scheduled Jobs</h3>
          <p className="text-sm text-gray-500 mb-4">
            Create your first scheduled job to automate agent executions
          </p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" />
            Create Job
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {jobs.map((job) => (
            <JobRow
              key={job.job_id}
              job={job}
              expanded={expandedJobId === job.job_id}
              onToggle={() => setExpandedJobId(expandedJobId === job.job_id ? null : job.job_id)}
              onPause={() => handlePause(job.job_id)}
              onResume={() => handleResume(job.job_id)}
              onDelete={() => handleDelete(job.job_id)}
              onTrigger={() => handleTrigger(job.job_id)}
            />
          ))}
        </div>
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <CreateJobModal
          onClose={() => setShowCreateModal(false)}
          onCreate={() => {
            setShowCreateModal(false);
            loadJobs();
          }}
        />
      )}
    </div>
  );
}
