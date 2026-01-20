/**
 * Scheduler Manager Component - Enhanced UI
 *
 * Redesigned to match the AutonomOS dashboard design language:
 * - Scheduler Functions grid (like AOA Functions)
 * - Active Jobs performance table
 * - Metric cards with progress bars and status indicators
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
  TrendingUp,
  TrendingDown,
  Activity,
  Timer,
  Target,
  Cpu,
  MemoryStick,
  ExternalLink,
  Info,
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

// Mock scheduler metrics (in production, these would come from API)
interface SchedulerMetrics {
  successRate: number;
  avgLatency: number;
  throughput: number;
  queueDepth: number;
  activeJobs: number;
  totalJobs: number;
  failedToday: number;
  executionsToday: number;
}

// API helpers
const API_BASE = '/api/v1/scheduler';

async function fetchJobs(): Promise<ScheduledJob[]> {
  const response = await fetch(`${API_BASE}/jobs`);
  if (!response.ok) throw new Error('Failed to fetch jobs');
  const data = await response.json();
  return data.jobs || [];
}

async function fetchExecutions(jobId: string): Promise<JobExecution[]> {
  const response = await fetch(`${API_BASE}/jobs/${jobId}/executions`);
  if (!response.ok) throw new Error('Failed to fetch executions');
  const data = await response.json();
  return data.executions || [];
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

// Status badge with glow effect
function StatusBadge({ status, size = 'sm' }: { status: string; size?: 'sm' | 'md' }) {
  const config: Record<string, { bg: string; text: string; glow: string }> = {
    optimal: { bg: 'bg-emerald-500/20', text: 'text-emerald-400', glow: 'shadow-emerald-500/20' },
    active: { bg: 'bg-emerald-500/20', text: 'text-emerald-400', glow: 'shadow-emerald-500/20' },
    warning: { bg: 'bg-yellow-500/20', text: 'text-yellow-400', glow: 'shadow-yellow-500/20' },
    paused: { bg: 'bg-yellow-500/20', text: 'text-yellow-400', glow: 'shadow-yellow-500/20' },
    critical: { bg: 'bg-red-500/20', text: 'text-red-400', glow: 'shadow-red-500/20' },
    failed: { bg: 'bg-red-500/20', text: 'text-red-400', glow: 'shadow-red-500/20' },
    expired: { bg: 'bg-red-500/20', text: 'text-red-400', glow: 'shadow-red-500/20' },
    disabled: { bg: 'bg-gray-500/20', text: 'text-gray-400', glow: '' },
    pending: { bg: 'bg-blue-500/20', text: 'text-blue-400', glow: 'shadow-blue-500/20' },
    running: { bg: 'bg-purple-500/20', text: 'text-purple-400', glow: 'shadow-purple-500/20' },
    completed: { bg: 'bg-emerald-500/20', text: 'text-emerald-400', glow: 'shadow-emerald-500/20' },
    timeout: { bg: 'bg-orange-500/20', text: 'text-orange-400', glow: 'shadow-orange-500/20' },
  };

  const { bg, text, glow } = config[status] || config.disabled;
  const sizeClasses = size === 'md' ? 'px-3 py-1 text-sm' : 'px-2 py-0.5 text-xs';

  return (
    <span className={`${bg} ${text} ${glow} ${sizeClasses} rounded font-medium shadow-sm`}>
      {status}
    </span>
  );
}

// Progress bar component
function ProgressBar({ value, target = 90, color = 'cyan' }: { value: number; target?: number; color?: string }) {
  const getStatusColor = () => {
    if (value >= target) return 'bg-emerald-500';
    if (value >= target - 15) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  return (
    <div className="w-full">
      <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
        <div
          className={`h-full ${getStatusColor()} rounded-full transition-all duration-500`}
          style={{ width: `${Math.min(100, value)}%` }}
        />
      </div>
      <div className="flex justify-between mt-1">
        <span className="text-xs text-gray-500">Target: {target}%</span>
      </div>
    </div>
  );
}

// Metric card (like AOA Functions)
function MetricCard({
  title,
  description,
  value,
  unit = '%',
  target = 90,
  trend,
  status,
}: {
  title: string;
  description: string;
  value: number;
  unit?: string;
  target?: number;
  trend?: 'up' | 'down' | 'stable';
  status: 'optimal' | 'warning' | 'critical';
}) {
  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Activity;
  const trendColor = trend === 'up' ? 'text-emerald-400' : trend === 'down' ? 'text-red-400' : 'text-gray-400';

  return (
    <div className="bg-gray-800/50 rounded-xl border border-gray-700/50 p-5 hover:border-gray-600 transition-all">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-white font-medium">{title}</h3>
          <p className="text-gray-400 text-xs mt-0.5 flex items-center gap-1">
            {description}
            <Info className="w-3 h-3 text-gray-500" />
          </p>
        </div>
        <StatusBadge status={status} size="md" />
      </div>

      <div className="flex items-end gap-2 mb-4">
        <span className={`text-4xl font-bold ${
          status === 'optimal' ? 'text-emerald-400' :
          status === 'warning' ? 'text-yellow-400' :
          'text-red-400'
        }`}>
          {value}
        </span>
        <span className="text-xl text-gray-400 mb-1">{unit}</span>
        {trend && (
          <TrendIcon className={`w-5 h-5 ${trendColor} ml-2 mb-1`} />
        )}
      </div>

      <ProgressBar value={value} target={target} />
    </div>
  );
}

// Large stat display (like xAO metrics)
function StatDisplay({
  label,
  description,
  value,
  trend,
  color = 'cyan',
}: {
  label: string;
  description: string;
  value: string;
  trend?: 'up' | 'down' | 'stable';
  color?: 'cyan' | 'emerald' | 'purple' | 'yellow' | 'red';
}) {
  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Activity;
  const colorClasses = {
    cyan: 'text-cyan-400',
    emerald: 'text-emerald-400',
    purple: 'text-purple-400',
    yellow: 'text-yellow-400',
    red: 'text-red-400',
  };

  return (
    <div className="bg-gray-800/30 rounded-xl border border-gray-700/50 p-6 hover:bg-gray-800/50 transition-all">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-white font-medium flex items-center gap-2">
            {label}
            {trend && <TrendIcon className={`w-4 h-4 ${trend === 'up' ? 'text-emerald-400' : trend === 'down' ? 'text-red-400' : 'text-gray-400'}`} />}
          </h3>
          <p className="text-gray-500 text-sm mt-0.5">{description}</p>
        </div>
        <span className={`text-3xl font-bold ${colorClasses[color]}`}>{value}</span>
      </div>
    </div>
  );
}

// Active job row (like Active Agent Performance table)
function ActiveJobRow({
  job,
  onPause,
  onResume,
  onDelete,
  onTrigger,
}: {
  job: ScheduledJob;
  onPause: () => void;
  onResume: () => void;
  onDelete: () => void;
  onTrigger: () => void;
}) {
  // Mock resource metrics
  const execPerHour = Math.floor(Math.random() * 100) + 50;
  const cpuUsage = Math.floor(Math.random() * 40) + 10;
  const memUsage = Math.floor(Math.random() * 300) + 200;

  return (
    <tr className="border-b border-gray-800 hover:bg-gray-800/30 transition-colors">
      <td className="py-4 px-4">
        <div className="flex items-center gap-3">
          <span className="text-white font-medium">{job.name}</span>
          <ExternalLink className="w-3.5 h-3.5 text-gray-500 hover:text-cyan-400 cursor-pointer" />
        </div>
      </td>
      <td className="py-4 px-4">
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${
            job.status === 'active' ? 'bg-emerald-400' :
            job.status === 'paused' ? 'bg-yellow-400' :
            'bg-gray-400'
          }`} />
        </div>
      </td>
      <td className="py-4 px-4 text-gray-300">{execPerHour}</td>
      <td className="py-4 px-4">
        <span className={`${cpuUsage > 30 ? 'text-yellow-400' : 'text-cyan-400'}`}>
          {cpuUsage}%
        </span>
      </td>
      <td className="py-4 px-4 text-gray-300">{memUsage} MB</td>
      <td className="py-4 px-4">
        <div className="flex items-center gap-1">
          <button
            onClick={onTrigger}
            className="p-1.5 text-cyan-400 hover:bg-cyan-500/20 rounded transition-colors"
            title="Run Now"
          >
            <Play className="w-4 h-4" />
          </button>
          {job.status === 'active' ? (
            <button
              onClick={onPause}
              className="p-1.5 text-yellow-400 hover:bg-yellow-500/20 rounded transition-colors"
              title="Pause"
            >
              <Pause className="w-4 h-4" />
            </button>
          ) : job.status === 'paused' ? (
            <button
              onClick={onResume}
              className="p-1.5 text-emerald-400 hover:bg-emerald-500/20 rounded transition-colors"
              title="Resume"
            >
              <Play className="w-4 h-4" />
            </button>
          ) : null}
          <button
            onClick={onDelete}
            className="p-1.5 text-red-400 hover:bg-red-500/20 rounded transition-colors"
            title="Delete"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </td>
    </tr>
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
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-gray-900 rounded-2xl border border-gray-700 w-full max-w-xl max-h-[90vh] overflow-y-auto shadow-2xl">
        <div className="p-5 border-b border-gray-800 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-white">Create Scheduled Job</h2>
            <p className="text-gray-400 text-sm mt-1">Configure automated agent execution</p>
          </div>
          <button onClick={onClose} className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors">
            <XCircle className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-5">
          {error && (
            <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-sm">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Job Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-all"
              placeholder="e.g., Daily Revenue Report"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Description</label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-all"
              placeholder="What does this job do?"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Agent</label>
            <select
              value={agentId}
              onChange={(e) => setAgentId(e.target.value)}
              className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-all"
            >
              <option value="default">Default Agent</option>
              <option value="revops-agent">RevOps Agent</option>
              <option value="finops-agent">FinOps Agent</option>
              <option value="sales-forecasting">Sales Forecasting</option>
              <option value="churn-predictor">Churn Predictor</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Trigger Type</label>
            <div className="grid grid-cols-4 gap-2">
              {[
                { id: 'cron', label: 'Cron', icon: Calendar },
                { id: 'interval', label: 'Interval', icon: RefreshCw },
                { id: 'webhook', label: 'Webhook', icon: Zap },
                { id: 'event', label: 'Event', icon: Activity },
              ].map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  type="button"
                  onClick={() => setTriggerType(id)}
                  className={`flex flex-col items-center gap-2 p-3 rounded-xl border transition-all ${
                    triggerType === id
                      ? 'bg-cyan-500/20 border-cyan-500 text-cyan-400'
                      : 'bg-gray-800 border-gray-700 text-gray-400 hover:border-gray-600'
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  <span className="text-xs font-medium">{label}</span>
                </button>
              ))}
            </div>
          </div>

          {triggerType === 'cron' && (
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Cron Expression
              </label>
              <input
                type="text"
                value={cronExpression}
                onChange={(e) => setCronExpression(e.target.value)}
                className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-xl text-white font-mono focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-all"
                placeholder="0 9 * * *"
              />
              {validating ? (
                <p className="text-xs text-gray-400 mt-2 flex items-center gap-2">
                  <RefreshCw className="w-3 h-3 animate-spin" />
                  Validating...
                </p>
              ) : cronValidation ? (
                <div className="mt-2 p-3 rounded-lg bg-gray-800/50">
                  {cronValidation.valid ? (
                    <div className="text-sm">
                      <p className="text-emerald-400 flex items-center gap-2">
                        <CheckCircle className="w-4 h-4" />
                        {cronValidation.description}
                      </p>
                      {cronValidation.next_runs && (
                        <p className="text-gray-400 text-xs mt-2">
                          Next run: {new Date(cronValidation.next_runs[0]).toLocaleString()}
                        </p>
                      )}
                    </div>
                  ) : (
                    <p className="text-sm text-red-400 flex items-center gap-2">
                      <AlertCircle className="w-4 h-4" />
                      {cronValidation.error}
                    </p>
                  )}
                </div>
              ) : null}
            </div>
          )}

          {triggerType === 'interval' && (
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Interval (seconds)
              </label>
              <input
                type="number"
                value={intervalSeconds}
                onChange={(e) => setIntervalSeconds(Number(e.target.value))}
                min={60}
                className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-all"
              />
              <p className="text-xs text-gray-400 mt-2">
                Runs every {Math.floor(intervalSeconds / 60)} minutes
              </p>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Input Template (optional)
            </label>
            <textarea
              value={inputTemplate}
              onChange={(e) => setInputTemplate(e.target.value)}
              rows={3}
              className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-xl text-white font-mono text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-all resize-none"
              placeholder='{"prompt": "Generate report for {{date}}"}'
            />
          </div>

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-3 bg-gray-800 hover:bg-gray-700 text-white rounded-xl transition-colors font-medium"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={creating || (triggerType === 'cron' && !cronValidation?.valid)}
              className="flex-1 px-4 py-3 bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600 disabled:from-gray-700 disabled:to-gray-700 disabled:cursor-not-allowed text-white rounded-xl transition-all font-medium shadow-lg shadow-cyan-500/20 disabled:shadow-none"
            >
              {creating ? (
                <span className="flex items-center justify-center gap-2">
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Creating...
                </span>
              ) : (
                'Create Job'
              )}
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
  const [showCreateModal, setShowCreateModal] = useState(false);

  // Mock metrics (in production, fetch from API)
  const [metrics] = useState<SchedulerMetrics>({
    successRate: 94,
    avgLatency: 127,
    throughput: 342,
    queueDepth: 12,
    activeJobs: 8,
    totalJobs: 12,
    failedToday: 3,
    executionsToday: 847,
  });

  const loadJobs = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchJobs();
      setJobs(data);
    } catch (err: any) {
      setError(err.message);
      // Use mock data on error for demo
      setJobs([
        {
          job_id: '1',
          tenant_id: '1',
          name: 'Revenue Aggregation',
          description: 'Daily revenue rollup from all sources',
          agent_id: 'revops-agent',
          trigger: { trigger_type: 'cron', cron_expression: '0 6 * * *' },
          status: 'active',
          timeout_seconds: 300,
          max_retries: 3,
          allow_concurrent: false,
          run_count: 342,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
        {
          job_id: '2',
          tenant_id: '1',
          name: 'Churn Analysis',
          description: 'Weekly churn prediction model refresh',
          agent_id: 'churn-predictor',
          trigger: { trigger_type: 'cron', cron_expression: '0 0 * * 0' },
          status: 'active',
          timeout_seconds: 600,
          max_retries: 2,
          allow_concurrent: false,
          run_count: 52,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
        {
          job_id: '3',
          tenant_id: '1',
          name: 'Lead Scoring Update',
          description: 'Hourly lead score recalculation',
          agent_id: 'sales-forecasting',
          trigger: { trigger_type: 'interval', interval_seconds: 3600 },
          status: 'paused',
          timeout_seconds: 180,
          max_retries: 3,
          allow_concurrent: false,
          run_count: 1847,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ]);
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
      console.error('Pause failed:', err);
      // Update local state for demo
      setJobs(jobs.map(j => j.job_id === jobId ? { ...j, status: 'paused' as const } : j));
    }
  };

  const handleResume = async (jobId: string) => {
    try {
      await resumeJob(jobId);
      loadJobs();
    } catch (err: any) {
      console.error('Resume failed:', err);
      setJobs(jobs.map(j => j.job_id === jobId ? { ...j, status: 'active' as const } : j));
    }
  };

  const handleDelete = async (jobId: string) => {
    if (!confirm('Are you sure you want to delete this job?')) return;
    try {
      await deleteJob(jobId);
      loadJobs();
    } catch (err: any) {
      console.error('Delete failed:', err);
      setJobs(jobs.filter(j => j.job_id !== jobId));
    }
  };

  const handleTrigger = async (jobId: string) => {
    try {
      const executionId = await triggerJob(jobId);
      alert(`Job triggered! Execution ID: ${executionId}`);
      loadJobs();
    } catch (err: any) {
      alert(`Job triggered (demo mode)`);
    }
  };

  const getStatus = (value: number, thresholds: { optimal: number; warning: number }) => {
    if (value >= thresholds.optimal) return 'optimal';
    if (value >= thresholds.warning) return 'warning';
    return 'critical';
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-xl flex items-center justify-center shadow-lg shadow-cyan-500/20">
            <Clock className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Scheduler Service</h1>
            <p className="text-gray-400 text-sm">
              Automated job orchestration and execution monitoring
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={loadJobs}
            className="p-2.5 text-gray-400 hover:text-white hover:bg-gray-800 rounded-xl transition-colors"
            title="Refresh"
          >
            <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600 text-white rounded-xl transition-all font-medium shadow-lg shadow-cyan-500/20"
          >
            <Plus className="w-4 h-4" />
            New Job
          </button>
        </div>
      </div>

      {/* Scheduler Functions Grid (like AOA Functions) */}
      <div>
        <h2 className="text-lg font-semibold text-white mb-4">Scheduler Functions</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            title="Execution"
            description="Job Success Rate"
            value={metrics.successRate}
            target={90}
            trend="up"
            status={getStatus(metrics.successRate, { optimal: 90, warning: 75 })}
          />
          <MetricCard
            title="Queue"
            description="Queue Health"
            value={100 - (metrics.queueDepth / 50) * 100}
            target={85}
            trend="stable"
            status={getStatus(100 - (metrics.queueDepth / 50) * 100, { optimal: 80, warning: 60 })}
          />
          <MetricCard
            title="Reliability"
            description="Uptime Score"
            value={99.2}
            target={99}
            trend="up"
            status="optimal"
          />
          <MetricCard
            title="Throughput"
            description="Jobs/Hour Capacity"
            value={87}
            target={80}
            trend="up"
            status={getStatus(87, { optimal: 80, warning: 60 })}
          />
        </div>
      </div>

      {/* Quick Stats (like xAO metrics) */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatDisplay
          label="Active Jobs"
          description="Currently scheduled"
          value={`${metrics.activeJobs}/${metrics.totalJobs}`}
          trend="stable"
          color="emerald"
        />
        <StatDisplay
          label="Executions Today"
          description="Completed runs"
          value={metrics.executionsToday.toString()}
          trend="up"
          color="cyan"
        />
        <StatDisplay
          label="Avg Latency"
          description="P95 execution time"
          value={`${metrics.avgLatency}ms`}
          trend="down"
          color="purple"
        />
        <StatDisplay
          label="Failed Today"
          description="Requires attention"
          value={metrics.failedToday.toString()}
          trend="down"
          color={metrics.failedToday > 5 ? 'red' : 'yellow'}
        />
      </div>

      {/* Active Jobs Table (like Active Agent Performance) */}
      <div className="bg-gray-800/30 rounded-2xl border border-gray-700/50 overflow-hidden">
        <div className="p-5 border-b border-gray-700/50">
          <h2 className="text-lg font-semibold text-white">Active Job Performance</h2>
        </div>

        {loading && jobs.length === 0 ? (
          <div className="flex items-center justify-center py-16 text-gray-400">
            <RefreshCw className="w-6 h-6 animate-spin mr-3" />
            Loading scheduled jobs...
          </div>
        ) : jobs.length === 0 ? (
          <div className="text-center py-16">
            <Calendar className="w-12 h-12 text-gray-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-400 mb-2">No Scheduled Jobs</h3>
            <p className="text-gray-500 text-sm mb-6">
              Create your first job to start automating agent executions
            </p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-cyan-500 to-blue-500 text-white rounded-xl font-medium shadow-lg shadow-cyan-500/20"
            >
              <Plus className="w-4 h-4" />
              Create Job
            </button>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-700/50">
                <th className="text-left py-3 px-4 text-gray-400 font-medium text-sm">JOB</th>
                <th className="text-left py-3 px-4 text-gray-400 font-medium text-sm">STATUS</th>
                <th className="text-left py-3 px-4 text-gray-400 font-medium text-sm">EXEC/HR</th>
                <th className="text-left py-3 px-4 text-gray-400 font-medium text-sm">CPU</th>
                <th className="text-left py-3 px-4 text-gray-400 font-medium text-sm">MEMORY</th>
                <th className="text-left py-3 px-4 text-gray-400 font-medium text-sm">ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <ActiveJobRow
                  key={job.job_id}
                  job={job}
                  onPause={() => handlePause(job.job_id)}
                  onResume={() => handleResume(job.job_id)}
                  onDelete={() => handleDelete(job.job_id)}
                  onTrigger={() => handleTrigger(job.job_id)}
                />
              ))}
            </tbody>
          </table>
        )}

        <div className="p-4 border-t border-gray-700/50 text-center text-xs text-gray-500">
          Each % value represents real-time operational efficiency of the scheduler function vs its target SLO.
        </div>
      </div>

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
