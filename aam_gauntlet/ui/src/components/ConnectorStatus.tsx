import { useState, useEffect } from 'react'
import { RefreshCw, AlertTriangle, CheckCircle, XCircle, Clock, Activity } from 'lucide-react'
import { apiClient } from '../api/client'

interface ConnectorStatusProps {
  connectors: any[]
  workflows: any[]
}

export default function ConnectorStatus({ connectors, workflows }: ConnectorStatusProps) {
  const [expandedConnector, setExpandedConnector] = useState<string | null>(null)
  const [connectorMetrics, setConnectorMetrics] = useState<any>({})

  // Fetch metrics for expanded connector
  useEffect(() => {
    if (expandedConnector) {
      const fetchMetrics = async () => {
        try {
          const metrics = await apiClient.getMetrics()
          setConnectorMetrics(metrics.rate_limiter_stats || {})
        } catch (error) {
          console.error('Failed to fetch connector metrics:', error)
        }
      }
      fetchMetrics()
    }
  }, [expandedConnector])

  const getConnectorHealth = (connectorId: string) => {
    const activeWorkflows = workflows.filter(
      w => w.connector_id === connectorId
    )
    
    const failedWorkflows = activeWorkflows.filter(w => w.status === 'failed').length
    const runningWorkflows = activeWorkflows.filter(w => w.status === 'running').length
    
    if (failedWorkflows > 0) return 'error'
    if (runningWorkflows > 0) return 'active'
    return 'idle'
  }

  const getHealthIcon = (health: string) => {
    switch (health) {
      case 'active':
        return <Activity className="text-green-400 animate-pulse" size={16} />
      case 'error':
        return <XCircle className="text-red-400" size={16} />
      case 'warning':
        return <AlertTriangle className="text-yellow-400" size={16} />
      default:
        return <CheckCircle className="text-gray-400" size={16} />
    }
  }

  const runWorkflow = async (connectorId: string, workflowType: string) => {
    try {
      await apiClient.runWorkflow({
        connector_id: connectorId,
        workflow_type: workflowType,
        duration_seconds: 30,
        params: {}
      })
    } catch (error) {
      console.error('Failed to run workflow:', error)
    }
  }

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <div className="space-y-4">
        {connectors.map(connector => {
          const health = getConnectorHealth(connector.connector_id)
          const isExpanded = expandedConnector === connector.connector_id
          const metrics = connectorMetrics[connector.connector_id] || {}
          
          // Get recent workflows for this connector
          const recentWorkflows = workflows
            .filter(w => w.connector_id === connector.connector_id)
            .slice(0, 3)
          
          return (
            <div key={connector.connector_id} className="bg-gray-700 rounded-lg p-4">
              {/* Header */}
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
                  {/* Rate Limiter Status */}
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
                  {/* Expand/Collapse */}
                  <RefreshCw
                    className={`text-gray-400 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
                    size={16}
                  />
                </div>
              </div>

              {/* Expanded Details */}
              {isExpanded && (
                <div className="mt-4 space-y-4">
                  {/* Rate Limiter Metrics */}
                  <div className="grid grid-cols-3 gap-3">
                    <div className="bg-gray-800 rounded p-2">
                      <div className="text-xs text-gray-400">Tokens Available</div>
                      <div className="text-lg font-bold text-blue-400">
                        {metrics.tokens_available || 0}/{metrics.capacity || 0}
                      </div>
                    </div>
                    <div className="bg-gray-800 rounded p-2">
                      <div className="text-xs text-gray-400">Consecutive Errors</div>
                      <div className="text-lg font-bold text-red-400">
                        {metrics.consecutive_errors || 0}
                      </div>
                    </div>
                    <div className="bg-gray-800 rounded p-2">
                      <div className="text-xs text-gray-400">Backoff Until</div>
                      <div className="text-lg font-bold text-yellow-400">
                        {metrics.in_backoff ? 
                          new Date(metrics.backoff_until * 1000).toLocaleTimeString() :
                          'None'
                        }
                      </div>
                    </div>
                  </div>

                  {/* Recent Workflows */}
                  {recentWorkflows.length > 0 && (
                    <div>
                      <div className="text-sm font-medium text-gray-300 mb-2">Recent Workflows</div>
                      <div className="space-y-1">
                        {recentWorkflows.map(workflow => (
                          <div
                            key={workflow.workflow_id}
                            className="flex items-center justify-between bg-gray-800 rounded p-2 text-xs"
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

                  {/* Actions */}
                  <div className="flex space-x-2">
                    <button
                      onClick={() => runWorkflow(connector.connector_id, 'high_volume')}
                      className="flex-1 px-3 py-1 bg-blue-600 text-white rounded text-xs hover:bg-blue-700"
                    >
                      High Volume Test
                    </button>
                    <button
                      onClick={() => runWorkflow(connector.connector_id, 'idempotent_write')}
                      className="flex-1 px-3 py-1 bg-green-600 text-white rounded text-xs hover:bg-green-700"
                    >
                      Idempotent Write
                    </button>
                    <button
                      onClick={() => runWorkflow(connector.connector_id, 'drift_sensitive')}
                      className="flex-1 px-3 py-1 bg-purple-600 text-white rounded text-xs hover:bg-purple-700"
                    >
                      Drift Test
                    </button>
                  </div>
                </div>
              )}
            </div>
          )
        })}

        {connectors.length === 0 && (
          <div className="text-center text-gray-400 py-8">
            No connectors configured. Create connectors to start testing.
          </div>
        )}
      </div>
    </div>
  )
}