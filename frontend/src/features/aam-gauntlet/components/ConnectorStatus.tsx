import { useState, useEffect } from 'react';
import { RefreshCw, AlertTriangle, CheckCircle, XCircle, Clock, Activity } from 'lucide-react';
import { gauntletClient } from '../api/gauntletClient';
import type { Connector, Workflow } from '../types';

interface ConnectorStatusProps {
  connectors: Connector[];
  workflows: Workflow[];
}

export default function ConnectorStatus({ connectors, workflows }: ConnectorStatusProps) {
  const [expandedConnector, setExpandedConnector] = useState<string | null>(null);
  const [connectorMetrics, setConnectorMetrics] = useState<any>({});

  useEffect(() => {
    if (expandedConnector) {
      const fetchMetrics = async () => {
        try {
          const metrics = await gauntletClient.getMetrics();
          setConnectorMetrics(metrics.metrics_summary.rate_limiter_stats || {});
        } catch (error) {
          console.error('Failed to fetch connector metrics:', error);
        }
      };
      fetchMetrics();
    }
  }, [expandedConnector]);

  const getConnectorHealth = (connectorId: string) => {
    const activeWorkflows = workflows.filter(
      w => w.connector_id === connectorId
    );
    
    const failedWorkflows = activeWorkflows.filter(w => w.status === 'failed').length;
    const runningWorkflows = activeWorkflows.filter(w => w.status === 'running').length;
    
    if (failedWorkflows > 0) return 'error';
    if (runningWorkflows > 0) return 'active';
    return 'idle';
  };

  const getHealthIcon = (health: string) => {
    switch (health) {
      case 'active':
        return <Activity className="text-green-400 animate-pulse" size={16} />;
      case 'error':
        return <XCircle className="text-red-400" size={16} />;
      case 'warning':
        return <AlertTriangle className="text-yellow-400" size={16} />;
      default:
        return <CheckCircle className="text-gray-400" size={16} />;
    }
  };

  const runWorkflow = async (connectorId: string, workflowType: string) => {
    try {
      await gauntletClient.runWorkflow({
        connector_id: connectorId,
        workflow_type: workflowType as any,
        duration_seconds: 30,
        params: {}
      });
    } catch (error) {
      console.error('Failed to run workflow:', error);
    }
  };

  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6">
      <div className="space-y-4">
        {connectors.map(connector => {
          const health = getConnectorHealth(connector.connector_id);
          const isExpanded = expandedConnector === connector.connector_id;
          const metrics = connectorMetrics[connector.connector_id] || {};
          
          const recentWorkflows = workflows
            .filter(w => w.connector_id === connector.connector_id)
            .slice(0, 3);
          
          return (
            <div key={connector.connector_id} className="bg-gray-700/50 border border-gray-600 rounded-lg p-4">
              <div
                className="flex items-center justify-between cursor-pointer"
                onClick={() => setExpandedConnector(isExpanded ? null : connector.connector_id)}
              >
                <div className="flex items-center space-x-3">
                  {getHealthIcon(health)}
                  <div>
                    <div className="font-medium text-white">{connector.connector_id}</div>
                    <div className="text-xs text-gray-400">
                      {connector.service_id.replace('_mock', '')} • {connector.auth_type}
                    </div>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  {metrics.in_backoff && (
                    <span className="text-xs text-yellow-400 flex items-center">
                      <Clock size={12} className="mr-1" />
                      Backoff
                    </span>
                  )}
                  {metrics.consecutive_errors > 0 && (
                    <span className="text-xs text-red-400">
                      {metrics.consecutive_errors} errors
                    </span>
                  )}
                  <RefreshCw
                    className={`text-gray-400 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
                    size={16}
                  />
                </div>
              </div>

              {isExpanded && (
                <div className="mt-4 space-y-4">
                  <div className="grid grid-cols-3 gap-3">
                    <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-2">
                      <div className="text-xs text-gray-400">Tokens Available</div>
                      <div className="text-lg font-bold text-cyan-400">
                        {metrics.tokens_available || 0}/{metrics.capacity || 0}
                      </div>
                    </div>
                    <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-2">
                      <div className="text-xs text-gray-400">Consecutive Errors</div>
                      <div className="text-lg font-bold text-red-400">
                        {metrics.consecutive_errors || 0}
                      </div>
                    </div>
                    <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-2">
                      <div className="text-xs text-gray-400">Backoff Until</div>
                      <div className="text-lg font-bold text-yellow-400">
                        {metrics.in_backoff ? 
                          new Date(metrics.backoff_until * 1000).toLocaleTimeString() :
                          'None'
                        }
                      </div>
                    </div>
                  </div>

                  {recentWorkflows.length > 0 && (
                    <div>
                      <div className="text-sm font-medium text-gray-300 mb-2">Recent Workflows</div>
                      <div className="space-y-1">
                        {recentWorkflows.map(workflow => (
                          <div
                            key={workflow.workflow_id}
                            className="flex items-center justify-between bg-gray-800/50 border border-gray-700 rounded-lg p-2 text-xs"
                          >
                            <span className="text-gray-300">{workflow.workflow_type}</span>
                            <span className={`${
                              workflow.status === 'running' ? 'text-yellow-400' :
                              workflow.status === 'completed' ? 'text-green-400' :
                              workflow.status === 'failed' ? 'text-red-400' :
                              'text-gray-400'
                            }`}>
                              {workflow.status}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="flex space-x-2">
                    <button
                      onClick={() => runWorkflow(connector.connector_id, 'high_volume')}
                      className="flex-1 px-3 py-1 bg-cyan-600 text-white rounded text-xs hover:bg-cyan-700 transition-colors"
                    >
                      High Volume Test
                    </button>
                    <button
                      onClick={() => runWorkflow(connector.connector_id, 'idempotent_write')}
                      className="flex-1 px-3 py-1 bg-green-600 text-white rounded text-xs hover:bg-green-700 transition-colors"
                    >
                      Idempotent Write
                    </button>
                    <button
                      onClick={() => runWorkflow(connector.connector_id, 'drift_sensitive')}
                      className="flex-1 px-3 py-1 bg-purple-600 text-white rounded text-xs hover:bg-purple-700 transition-colors"
                    >
                      Drift Test
                    </button>
                  </div>
                </div>
              )}
            </div>
          );
        })}

        {connectors.length === 0 && (
          <div className="text-center text-gray-400 py-8">
            No connectors configured. Create connectors to start testing.
          </div>
        )}
      </div>
    </div>
  );
}
