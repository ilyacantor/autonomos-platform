/**
 * Agent Approval Queue Component
 *
 * HITL approval interface for agent actions:
 * - Pending approvals list
 * - Action details review
 * - Approve/Reject with notes
 * - Expiration countdown
 *
 * Uses the following reusable hooks:
 * - usePolledData: For automatic data fetching with polling
 * - useStatusColors: For consistent risk level color mapping
 */

import { useState } from 'react';
import {
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  Bot,
  Wrench,
  Shield,
  RefreshCw,
  ChevronRight,
  ExternalLink,
  MessageSquare,
} from 'lucide-react';
import { usePolledData } from '../../hooks/usePolledData';
import { useStatusColors } from '../../hooks/useStatusColors';

interface ApprovalRequest {
  approval_id: string;
  run_id: string;
  agent_id: string;
  agent_name: string;
  action_type: string;
  action_details: Record<string, any>;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  created_at: string;
  expires_at: string;
  context: {
    user_query: string;
    step_number: number;
    previous_actions: string[];
  };
}

interface AgentApprovalQueueProps {
  onApprovalComplete?: () => void;
}

// Fetch function for approvals
const fetchApprovalsFromApi = async (): Promise<ApprovalRequest[]> => {
  const token = localStorage.getItem('token');
  const response = await fetch('/api/v1/agents/approvals?status=pending', {
    headers: {
      Authorization: token ? `Bearer ${token}` : '',
    },
  });

  if (response.ok) {
    const data = await response.json();
    return data.approvals || [];
  }
  throw new Error('Failed to fetch approvals');
};

export default function AgentApprovalQueue({ onApprovalComplete }: AgentApprovalQueueProps) {
  // Use the reusable hook for data fetching with polling (30 second interval)
  const { data: fetchedApprovals, loading, refresh } = usePolledData<ApprovalRequest[]>(
    fetchApprovalsFromApi,
    30000
  );

  // Use the reusable hook for consistent status colors
  const { getSeverityColors } = useStatusColors();

  // Local state for approvals (can be modified when approving/rejecting)
  const [localApprovals, setLocalApprovals] = useState<ApprovalRequest[] | null>(null);
  const [selectedApproval, setSelectedApproval] = useState<ApprovalRequest | null>(null);
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // Use fetched approvals, fall back to mock data on error, allow local overrides
  const approvals = localApprovals ?? fetchedApprovals ?? getMockApprovals();

  // Mock data for demonstration
  const getMockApprovals = (): ApprovalRequest[] => [
    {
      approval_id: 'apr-001',
      run_id: 'run-002',
      agent_id: 'agent-default',
      agent_name: 'AOS Agent',
      action_type: 'aam_create_connection',
      action_details: {
        connection_name: 'salesforce-prod',
        connection_type: 'salesforce',
        environment: 'production',
        oauth_scope: 'full',
        sync_schedule: '0 * * * *',
      },
      risk_level: 'high',
      created_at: new Date(Date.now() - 600000).toISOString(),
      expires_at: new Date(Date.now() + 3000000).toISOString(),
      context: {
        user_query: 'Create a new Salesforce connection to production',
        step_number: 2,
        previous_actions: ['aam_validate_credentials'],
      },
    },
    {
      approval_id: 'apr-002',
      run_id: 'run-005',
      agent_id: 'agent-default',
      agent_name: 'AOS Agent',
      action_type: 'aam_repair_drift',
      action_details: {
        connection_id: 'conn-snowflake-01',
        drift_type: 'schema_change',
        changes: [
          { field: 'revenue', old_type: 'integer', new_type: 'decimal' },
          { field: 'customer_id', action: 'added' },
        ],
        auto_apply: true,
      },
      risk_level: 'medium',
      created_at: new Date(Date.now() - 300000).toISOString(),
      expires_at: new Date(Date.now() + 3600000).toISOString(),
      context: {
        user_query: 'Fix the schema drift on Snowflake connector',
        step_number: 1,
        previous_actions: [],
      },
    },
    {
      approval_id: 'apr-003',
      run_id: 'run-006',
      agent_id: 'agent-default',
      agent_name: 'AOS Agent',
      action_type: 'dcl_write_query',
      action_details: {
        table: 'analytics.customer_segments',
        operation: 'UPDATE',
        affected_rows_estimate: 15420,
        query_preview: 'UPDATE analytics.customer_segments SET segment = ? WHERE score > ?',
      },
      risk_level: 'critical',
      created_at: new Date(Date.now() - 120000).toISOString(),
      expires_at: new Date(Date.now() + 1800000).toISOString(),
      context: {
        user_query: 'Update customer segments based on new scoring model',
        step_number: 3,
        previous_actions: ['dcl_query', 'dcl_get_schema'],
      },
    },
  ];

  // Handle approval decision
  const handleDecision = async (approved: boolean) => {
    if (!selectedApproval) return;

    setSubmitting(true);
    try {
      const token = localStorage.getItem('token');
      await fetch(`/api/v1/agents/approvals/${selectedApproval.approval_id}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: token ? `Bearer ${token}` : '',
        },
        body: JSON.stringify({ approved, notes }),
      });

      // Remove from local list (optimistic update)
      setLocalApprovals(
        approvals.filter((a) => a.approval_id !== selectedApproval.approval_id)
      );
      setSelectedApproval(null);
      setNotes('');

      onApprovalComplete?.();
    } catch (error) {
      console.error('Failed to submit approval:', error);
    } finally {
      setSubmitting(false);
    }
  };

  // Get risk level display using the centralized color utility
  // Maps risk levels to severity types for consistent styling
  const getRiskDisplay = (level: string) => {
    // Map risk levels to severity types
    const severityMap: Record<string, string> = {
      critical: 'error',
      high: 'warning',
      medium: 'warning',
      low: 'success',
    };
    const severity = severityMap[level] || 'info';
    const colors = getSeverityColors(severity);

    // Add border color for risk display
    const borderMap: Record<string, string> = {
      critical: 'border-red-500/50',
      high: 'border-orange-500/50',
      medium: 'border-yellow-500/50',
      low: 'border-green-500/50',
    };

    return {
      color: colors.text,
      bg: colors.badge.split(' ')[0], // Get just the bg class
      border: borderMap[level] || 'border-gray-500/50',
    };
  };

  // Calculate time remaining
  const getTimeRemaining = (expiresAt: string) => {
    const remaining = new Date(expiresAt).getTime() - Date.now();
    if (remaining <= 0) return 'Expired';
    const minutes = Math.floor(remaining / 60000);
    const hours = Math.floor(minutes / 60);
    if (hours > 0) return `${hours}h ${minutes % 60}m`;
    return `${minutes}m`;
  };

  // Count by risk level
  const criticalCount = approvals.filter((a) => a.risk_level === 'critical').length;
  const highCount = approvals.filter((a) => a.risk_level === 'high').length;

  return (
    <div className="bg-gray-800 rounded-lg border border-yellow-500/30">
      {/* Header */}
      <div className="px-4 py-4 border-b border-gray-700 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-yellow-500 to-orange-600 rounded-lg flex items-center justify-center">
            <Shield className="w-6 h-6 text-white" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">Agent Approval Queue</h3>
            <p className="text-xs text-gray-400">Human-in-the-loop decisions for agent actions</p>
          </div>
        </div>

        {/* Stats */}
        <div className="flex items-center gap-4">
          {criticalCount > 0 && (
            <div className="flex items-center gap-2 px-3 py-1 bg-red-500/20 rounded-lg">
              <AlertTriangle className="w-4 h-4 text-red-400" />
              <span className="text-sm font-medium text-red-400">{criticalCount} Critical</span>
            </div>
          )}
          {highCount > 0 && (
            <div className="flex items-center gap-2 px-3 py-1 bg-orange-500/20 rounded-lg">
              <AlertTriangle className="w-4 h-4 text-orange-400" />
              <span className="text-sm font-medium text-orange-400">{highCount} High</span>
            </div>
          )}
          <button
            onClick={refresh}
            className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 text-gray-400 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-gray-700">
        {/* Approvals List */}
        <div className="p-4">
          <div className="text-xs text-gray-400 uppercase tracking-wider mb-3">
            Pending Approvals ({approvals.length})
          </div>

          {loading ? (
            <div className="py-8 text-center">
              <RefreshCw className="w-8 h-8 text-gray-500 animate-spin mx-auto mb-3" />
              <p className="text-gray-500">Loading approvals...</p>
            </div>
          ) : approvals.length === 0 ? (
            <div className="py-8 text-center">
              <CheckCircle className="w-12 h-12 text-green-500/50 mx-auto mb-3" />
              <p className="text-gray-400">No pending approvals</p>
              <p className="text-xs text-gray-500 mt-1">All agent actions are approved</p>
            </div>
          ) : (
            <div className="space-y-3">
              {approvals.map((approval) => {
                const riskDisplay = getRiskDisplay(approval.risk_level);
                const isSelected = selectedApproval?.approval_id === approval.approval_id;

                return (
                  <button
                    key={approval.approval_id}
                    onClick={() => setSelectedApproval(approval)}
                    className={`w-full text-left p-4 rounded-lg border transition-all ${
                      isSelected
                        ? 'bg-purple-900/30 border-purple-500'
                        : `bg-gray-900/50 ${riskDisplay.border} hover:bg-gray-900`
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <div className={`p-2 rounded-lg ${riskDisplay.bg}`}>
                        <Wrench className={`w-4 h-4 ${riskDisplay.color}`} />
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-sm font-medium text-white">
                            {approval.action_type}
                          </span>
                          <span
                            className={`text-xs px-2 py-0.5 rounded ${riskDisplay.bg} ${riskDisplay.color}`}
                          >
                            {approval.risk_level.toUpperCase()}
                          </span>
                        </div>

                        <p className="text-xs text-gray-400 truncate mb-2">
                          {approval.context.user_query}
                        </p>

                        <div className="flex items-center gap-3 text-xs text-gray-500">
                          <span className="flex items-center gap-1">
                            <Bot className="w-3 h-3" />
                            {approval.agent_name}
                          </span>
                          <span className="flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {getTimeRemaining(approval.expires_at)}
                          </span>
                        </div>
                      </div>

                      <ChevronRight className="w-4 h-4 text-gray-500" />
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Detail Panel */}
        <div className="p-4">
          {selectedApproval ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="text-lg font-medium text-white">Review Action</h4>
                <a
                  href={`/agents/runs/${selectedApproval.run_id}`}
                  className="flex items-center gap-1 text-xs text-purple-400 hover:text-purple-300"
                >
                  View Run <ExternalLink className="w-3 h-3" />
                </a>
              </div>

              {/* Action Type */}
              <div className="bg-gray-900/50 rounded-lg p-4 border border-gray-700">
                <div className="text-xs text-gray-400 mb-1">Action Type</div>
                <div className="flex items-center gap-2">
                  <Wrench className="w-5 h-5 text-cyan-400" />
                  <span className="text-lg font-medium text-white">
                    {selectedApproval.action_type}
                  </span>
                </div>
              </div>

              {/* Risk Level */}
              <div className="bg-gray-900/50 rounded-lg p-4 border border-gray-700">
                <div className="text-xs text-gray-400 mb-2">Risk Assessment</div>
                {(() => {
                  const riskDisplay = getRiskDisplay(selectedApproval.risk_level);
                  return (
                    <div className="flex items-center gap-2">
                      <div className={`p-2 rounded-lg ${riskDisplay.bg}`}>
                        <AlertTriangle className={`w-5 h-5 ${riskDisplay.color}`} />
                      </div>
                      <span className={`text-lg font-medium ${riskDisplay.color}`}>
                        {selectedApproval.risk_level.toUpperCase()} RISK
                      </span>
                    </div>
                  );
                })()}
              </div>

              {/* Action Details */}
              <div className="bg-gray-900/50 rounded-lg p-4 border border-gray-700">
                <div className="text-xs text-gray-400 mb-2">Action Details</div>
                <pre className="text-xs text-gray-300 bg-gray-900 rounded p-3 overflow-x-auto max-h-48">
                  {JSON.stringify(selectedApproval.action_details, null, 2)}
                </pre>
              </div>

              {/* Context */}
              <div className="bg-gray-900/50 rounded-lg p-4 border border-gray-700">
                <div className="text-xs text-gray-400 mb-2">Context</div>
                <div className="space-y-2 text-sm">
                  <div>
                    <span className="text-gray-400">User Query:</span>{' '}
                    <span className="text-white">{selectedApproval.context.user_query}</span>
                  </div>
                  <div>
                    <span className="text-gray-400">Step:</span>{' '}
                    <span className="text-white">#{selectedApproval.context.step_number}</span>
                  </div>
                  {selectedApproval.context.previous_actions.length > 0 && (
                    <div>
                      <span className="text-gray-400">Previous Actions:</span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {selectedApproval.context.previous_actions.map((action, i) => (
                          <span
                            key={i}
                            className="text-xs bg-gray-800 px-2 py-1 rounded text-gray-300"
                          >
                            {action}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Expiration */}
              <div className="flex items-center gap-2 text-sm">
                <Clock className="w-4 h-4 text-yellow-400" />
                <span className="text-gray-400">Expires in:</span>
                <span className="text-yellow-400 font-medium">
                  {getTimeRemaining(selectedApproval.expires_at)}
                </span>
              </div>

              {/* Notes */}
              <div>
                <label className="text-xs text-gray-400 mb-2 flex items-center gap-1">
                  <MessageSquare className="w-3 h-3" />
                  Decision Notes (Optional)
                </label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Add notes about your decision..."
                  className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-purple-500 transition-colors resize-none"
                  rows={3}
                />
              </div>

              {/* Decision Buttons */}
              <div className="grid grid-cols-2 gap-3">
                <button
                  onClick={() => handleDecision(true)}
                  disabled={submitting}
                  className="flex items-center justify-center gap-2 px-4 py-3 bg-green-600 hover:bg-green-700 disabled:bg-gray-700 text-white rounded-lg font-medium transition-colors"
                >
                  <CheckCircle className="w-5 h-5" />
                  Approve
                </button>
                <button
                  onClick={() => handleDecision(false)}
                  disabled={submitting}
                  className="flex items-center justify-center gap-2 px-4 py-3 bg-red-600 hover:bg-red-700 disabled:bg-gray-700 text-white rounded-lg font-medium transition-colors"
                >
                  <XCircle className="w-5 h-5" />
                  Reject
                </button>
              </div>
            </div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-center py-12">
              <Shield className="w-16 h-16 text-gray-600 mb-4" />
              <p className="text-gray-400 mb-2">Select an approval to review</p>
              <p className="text-sm text-gray-500 max-w-xs">
                Review action details and context before making a decision
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
