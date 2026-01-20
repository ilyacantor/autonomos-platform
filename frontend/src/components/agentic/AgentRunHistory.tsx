/**
 * Agent Run History Component
 *
 * Displays history of agent runs with:
 * - Run status and metadata
 * - Token/cost tracking
 * - Expandable run details
 * - Filtering and search
 */

import { useState, useEffect } from 'react';
import {
  Clock,
  CheckCircle,
  XCircle,
  AlertTriangle,
  DollarSign,
  Zap,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  Search,
  Filter,
  Bot,
  Wrench,
  Play,
} from 'lucide-react';

interface RunStep {
  step_number: number;
  tool_name?: string;
  tool_server?: string;
  status: 'completed' | 'failed';
  duration_ms: number;
}

interface AgentRun {
  run_id: string;
  agent_id: string;
  agent_name: string;
  input: string;
  output?: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'waiting_approval';
  started_at: string;
  completed_at?: string;
  tokens_input: number;
  tokens_output: number;
  cost_usd: number;
  steps: RunStep[];
  error?: string;
}

interface AgentRunHistoryProps {
  agentId?: string;
  onSelectRun?: (run: AgentRun) => void;
  limit?: number;
}

export default function AgentRunHistory({
  agentId,
  onSelectRun,
  limit = 20,
}: AgentRunHistoryProps) {
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedRuns, setExpandedRuns] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  // Fetch runs on mount and when filters change
  useEffect(() => {
    fetchRuns();
  }, [agentId, statusFilter]);

  const fetchRuns = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const params = new URLSearchParams({
        limit: limit.toString(),
        ...(agentId && { agent_id: agentId }),
        ...(statusFilter !== 'all' && { status: statusFilter }),
      });

      const response = await fetch(`/api/v1/agents/runs?${params}`, {
        headers: {
          Authorization: token ? `Bearer ${token}` : '',
        },
      });

      if (response.ok) {
        const data = await response.json();
        setRuns(data.runs || []);
      }
    } catch (error) {
      console.error('Failed to fetch runs:', error);
      // Use mock data for demo
      setRuns(getMockRuns());
    } finally {
      setLoading(false);
    }
  };

  // Mock data for demonstration
  const getMockRuns = (): AgentRun[] => [
    {
      run_id: 'run-001',
      agent_id: 'agent-default',
      agent_name: 'AOS Agent',
      input: 'What is the total revenue for Q4 2025?',
      output: 'Based on the data from Snowflake, the total revenue for Q4 2025 was $4.2M...',
      status: 'completed',
      started_at: new Date(Date.now() - 300000).toISOString(),
      completed_at: new Date(Date.now() - 295000).toISOString(),
      tokens_input: 1245,
      tokens_output: 892,
      cost_usd: 0.0156,
      steps: [
        { step_number: 1, tool_name: 'dcl_query', tool_server: 'dcl', status: 'completed', duration_ms: 1200 },
        { step_number: 2, tool_name: 'dcl_get_schema', tool_server: 'dcl', status: 'completed', duration_ms: 450 },
      ],
    },
    {
      run_id: 'run-002',
      agent_id: 'agent-default',
      agent_name: 'AOS Agent',
      input: 'Create a new Salesforce connection to production',
      status: 'waiting_approval',
      started_at: new Date(Date.now() - 600000).toISOString(),
      tokens_input: 856,
      tokens_output: 234,
      cost_usd: 0.0089,
      steps: [
        { step_number: 1, tool_name: 'aam_validate_credentials', tool_server: 'aam', status: 'completed', duration_ms: 2300 },
      ],
    },
    {
      run_id: 'run-003',
      agent_id: 'agent-default',
      agent_name: 'AOS Agent',
      input: 'Show me the data lineage for the customers table',
      output: 'The customers table has the following lineage...',
      status: 'completed',
      started_at: new Date(Date.now() - 1800000).toISOString(),
      completed_at: new Date(Date.now() - 1795000).toISOString(),
      tokens_input: 2100,
      tokens_output: 1567,
      cost_usd: 0.0298,
      steps: [
        { step_number: 1, tool_name: 'aod_get_lineage', tool_server: 'aod', status: 'completed', duration_ms: 890 },
        { step_number: 2, tool_name: 'aod_get_related_assets', tool_server: 'aod', status: 'completed', duration_ms: 650 },
      ],
    },
    {
      run_id: 'run-004',
      agent_id: 'agent-default',
      agent_name: 'AOS Agent',
      input: 'Run sync for all Snowflake connectors',
      status: 'failed',
      started_at: new Date(Date.now() - 3600000).toISOString(),
      completed_at: new Date(Date.now() - 3595000).toISOString(),
      tokens_input: 567,
      tokens_output: 123,
      cost_usd: 0.0045,
      steps: [
        { step_number: 1, tool_name: 'aam_trigger_sync', tool_server: 'aam', status: 'failed', duration_ms: 4500 },
      ],
      error: 'Connection timeout: Snowflake cluster not responding',
    },
  ];

  // Toggle run expansion
  const toggleRunExpansion = (runId: string) => {
    setExpandedRuns((prev) => {
      const next = new Set(prev);
      if (next.has(runId)) {
        next.delete(runId);
      } else {
        next.add(runId);
      }
      return next;
    });
  };

  // Filter runs by search query
  const filteredRuns = runs.filter((run) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      run.input.toLowerCase().includes(query) ||
      run.output?.toLowerCase().includes(query) ||
      run.agent_name.toLowerCase().includes(query)
    );
  });

  // Get status icon and color
  const getStatusDisplay = (status: string) => {
    switch (status) {
      case 'completed':
        return { icon: CheckCircle, color: 'text-green-400', bg: 'bg-green-500/20' };
      case 'failed':
        return { icon: XCircle, color: 'text-red-400', bg: 'bg-red-500/20' };
      case 'running':
        return { icon: RefreshCw, color: 'text-yellow-400', bg: 'bg-yellow-500/20' };
      case 'waiting_approval':
        return { icon: AlertTriangle, color: 'text-orange-400', bg: 'bg-orange-500/20' };
      default:
        return { icon: Clock, color: 'text-gray-400', bg: 'bg-gray-500/20' };
    }
  };

  // Format duration
  const formatDuration = (startedAt: string, completedAt?: string) => {
    if (!completedAt) return 'In progress...';
    const duration = new Date(completedAt).getTime() - new Date(startedAt).getTime();
    if (duration < 1000) return `${duration}ms`;
    if (duration < 60000) return `${(duration / 1000).toFixed(1)}s`;
    return `${Math.floor(duration / 60000)}m ${Math.floor((duration % 60000) / 1000)}s`;
  };

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-700 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Clock className="w-5 h-5 text-gray-400" />
          <h3 className="text-lg font-semibold text-white">Run History</h3>
          <span className="text-sm text-gray-500">({filteredRuns.length} runs)</span>
        </div>
        <button
          onClick={fetchRuns}
          className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
          title="Refresh"
        >
          <RefreshCw className={`w-4 h-4 text-gray-400 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Filters */}
      <div className="px-4 py-3 border-b border-gray-700 flex items-center gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search runs..."
            className="w-full pl-10 pr-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-gray-500" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-gray-700 border border-gray-600 rounded-lg text-white text-sm px-3 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500"
          >
            <option value="all">All Status</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
            <option value="running">Running</option>
            <option value="waiting_approval">Waiting Approval</option>
          </select>
        </div>
      </div>

      {/* Runs List */}
      <div className="divide-y divide-gray-700">
        {loading ? (
          <div className="px-4 py-8 text-center">
            <RefreshCw className="w-8 h-8 text-gray-500 animate-spin mx-auto mb-3" />
            <p className="text-gray-500">Loading runs...</p>
          </div>
        ) : filteredRuns.length === 0 ? (
          <div className="px-4 py-8 text-center">
            <Bot className="w-12 h-12 text-gray-600 mx-auto mb-3" />
            <p className="text-gray-500">No runs found</p>
            <p className="text-sm text-gray-600 mt-1">
              Start a conversation to create your first run
            </p>
          </div>
        ) : (
          filteredRuns.map((run) => {
            const isExpanded = expandedRuns.has(run.run_id);
            const statusDisplay = getStatusDisplay(run.status);
            const StatusIcon = statusDisplay.icon;

            return (
              <div key={run.run_id} className="hover:bg-gray-750">
                {/* Run Header */}
                <div
                  className="px-4 py-3 cursor-pointer"
                  onClick={() => toggleRunExpansion(run.run_id)}
                >
                  <div className="flex items-start gap-3">
                    {/* Expand Toggle */}
                    <button className="mt-1 text-gray-500 hover:text-gray-300">
                      {isExpanded ? (
                        <ChevronDown className="w-4 h-4" />
                      ) : (
                        <ChevronRight className="w-4 h-4" />
                      )}
                    </button>

                    {/* Status Icon */}
                    <div className={`p-2 rounded-lg ${statusDisplay.bg}`}>
                      <StatusIcon className={`w-4 h-4 ${statusDisplay.color}`} />
                    </div>

                    {/* Run Info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-medium text-white truncate">
                          {run.input.length > 60 ? `${run.input.slice(0, 60)}...` : run.input}
                        </span>
                      </div>
                      <div className="flex items-center gap-3 text-xs text-gray-500">
                        <span className="flex items-center gap-1">
                          <Bot className="w-3 h-3" />
                          {run.agent_name}
                        </span>
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {formatDuration(run.started_at, run.completed_at)}
                        </span>
                        <span className="flex items-center gap-1">
                          <Zap className="w-3 h-3" />
                          {run.tokens_input + run.tokens_output} tokens
                        </span>
                        <span className="flex items-center gap-1">
                          <DollarSign className="w-3 h-3" />
                          ${run.cost_usd.toFixed(4)}
                        </span>
                        <span className="flex items-center gap-1">
                          <Wrench className="w-3 h-3" />
                          {run.steps.length} steps
                        </span>
                      </div>
                    </div>

                    {/* Time */}
                    <div className="text-xs text-gray-500">
                      {new Date(run.started_at).toLocaleString()}
                    </div>
                  </div>
                </div>

                {/* Expanded Details */}
                {isExpanded && (
                  <div className="px-4 pb-4 ml-12">
                    <div className="bg-gray-900/50 rounded-lg border border-gray-700 p-4 space-y-4">
                      {/* Input/Output */}
                      <div>
                        <div className="text-xs text-gray-400 mb-1">Input</div>
                        <div className="text-sm text-gray-300 bg-gray-800 rounded p-2">
                          {run.input}
                        </div>
                      </div>

                      {run.output && (
                        <div>
                          <div className="text-xs text-gray-400 mb-1">Output</div>
                          <div className="text-sm text-gray-300 bg-gray-800 rounded p-2 max-h-40 overflow-y-auto">
                            {run.output}
                          </div>
                        </div>
                      )}

                      {run.error && (
                        <div>
                          <div className="text-xs text-red-400 mb-1">Error</div>
                          <div className="text-sm text-red-300 bg-red-900/30 border border-red-500/30 rounded p-2">
                            {run.error}
                          </div>
                        </div>
                      )}

                      {/* Steps */}
                      {run.steps.length > 0 && (
                        <div>
                          <div className="text-xs text-gray-400 mb-2">Steps</div>
                          <div className="space-y-2">
                            {run.steps.map((step) => (
                              <div
                                key={step.step_number}
                                className="flex items-center gap-3 text-sm bg-gray-800 rounded p-2"
                              >
                                <span className="text-gray-500">#{step.step_number}</span>
                                <Wrench className="w-4 h-4 text-cyan-400" />
                                <span className="text-white">{step.tool_name}</span>
                                <span className="text-xs text-gray-500">({step.tool_server})</span>
                                <div className="flex-1" />
                                {step.status === 'completed' ? (
                                  <CheckCircle className="w-4 h-4 text-green-400" />
                                ) : (
                                  <XCircle className="w-4 h-4 text-red-400" />
                                )}
                                <span className="text-xs text-gray-500">{step.duration_ms}ms</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Actions */}
                      <div className="flex gap-2 pt-2 border-t border-gray-700">
                        {onSelectRun && (
                          <button
                            onClick={() => onSelectRun(run)}
                            className="flex items-center gap-2 px-3 py-1.5 bg-purple-600 hover:bg-purple-700 text-white text-sm rounded-lg transition-colors"
                          >
                            <Play className="w-4 h-4" />
                            Continue
                          </button>
                        )}
                        <button className="flex items-center gap-2 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded-lg transition-colors">
                          View Details
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
