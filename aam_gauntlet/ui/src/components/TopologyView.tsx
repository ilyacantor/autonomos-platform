import { useMemo } from 'react'
import { Activity, Database, Zap, AlertCircle, CheckCircle } from 'lucide-react'

interface TopologyViewProps {
  connectors: any[]
  workflows: any[]
}

export default function TopologyView({ connectors, workflows }: TopologyViewProps) {
  // Group services
  const services = useMemo(() => {
    const serviceMap = new Map()
    
    connectors.forEach(connector => {
      if (!serviceMap.has(connector.service_id)) {
        serviceMap.set(connector.service_id, {
          id: connector.service_id,
          connectors: [],
          status: 'healthy'
        })
      }
      serviceMap.get(connector.service_id).connectors.push(connector)
    })
    
    return Array.from(serviceMap.values())
  }, [connectors])

  // Get workflow status
  const getWorkflowStatus = (connectorId: string) => {
    const activeWorkflows = workflows.filter(
      w => w.connector_id === connectorId && w.status === 'running'
    )
    return activeWorkflows.length > 0 ? 'active' : 'idle'
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
      case 'completed':
        return 'text-green-400'
      case 'degraded':
      case 'running':
      case 'active':
        return 'text-yellow-400'
      case 'failed':
      case 'failing':
        return 'text-red-400'
      default:
        return 'text-gray-400'
    }
  }

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <div className="grid grid-cols-3 gap-8">
        {/* Synthetic APIs */}
        <div>
          <h3 className="text-lg font-semibold mb-4 text-blue-400 flex items-center">
            <Database className="mr-2" size={20} />
            Synthetic APIs
          </h3>
          <div className="space-y-3">
            {services.map(service => (
              <div
                key={service.id}
                className="bg-gray-700 rounded p-3 hover:bg-gray-600 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium">{service.id.replace('_mock', '')}</span>
                  <CheckCircle className={`${getStatusColor(service.status)}`} size={16} />
                </div>
                <div className="text-xs text-gray-400 mt-1">
                  {service.connectors.length} connector(s)
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* AAM Connectors */}
        <div>
          <h3 className="text-lg font-semibold mb-4 text-green-400 flex items-center">
            <Zap className="mr-2" size={20} />
            AAM Connectors
          </h3>
          <div className="space-y-3">
            {connectors.map(connector => (
              <div
                key={connector.connector_id}
                className="bg-gray-700 rounded p-3 hover:bg-gray-600 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium text-sm">{connector.connector_id}</div>
                    <div className="text-xs text-gray-400">{connector.auth_type}</div>
                  </div>
                  <Activity
                    className={`${
                      getWorkflowStatus(connector.connector_id) === 'active'
                        ? 'text-green-400 animate-pulse'
                        : 'text-gray-500'
                    }`}
                    size={16}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Workflows */}
        <div>
          <h3 className="text-lg font-semibold mb-4 text-purple-400 flex items-center">
            <Activity className="mr-2" size={20} />
            Workflows
          </h3>
          <div className="space-y-3">
            {workflows.slice(0, 5).map(workflow => (
              <div
                key={workflow.workflow_id}
                className="bg-gray-700 rounded p-3 hover:bg-gray-600 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium text-sm">{workflow.workflow_type}</div>
                    <div className="text-xs text-gray-400">
                      {workflow.connector_id.split(':')[0]}
                    </div>
                  </div>
                  <span className={`text-xs ${getStatusColor(workflow.status)}`}>
                    {workflow.status}
                  </span>
                </div>
              </div>
            ))}
            {workflows.length > 5 && (
              <div className="text-center text-gray-400 text-sm">
                +{workflows.length - 5} more
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Connection Lines Visualization (simplified) */}
      <div className="mt-6 pt-6 border-t border-gray-700">
        <div className="flex items-center justify-center space-x-4 text-sm">
          <div className="flex items-center">
            <div className="w-3 h-3 bg-green-400 rounded-full mr-2"></div>
            <span className="text-gray-400">Healthy</span>
          </div>
          <div className="flex items-center">
            <div className="w-3 h-3 bg-yellow-400 rounded-full mr-2"></div>
            <span className="text-gray-400">Active/Degraded</span>
          </div>
          <div className="flex items-center">
            <div className="w-3 h-3 bg-red-400 rounded-full mr-2"></div>
            <span className="text-gray-400">Failed</span>
          </div>
          <div className="flex items-center">
            <div className="w-3 h-3 bg-gray-400 rounded-full mr-2"></div>
            <span className="text-gray-400">Idle</span>
          </div>
        </div>
      </div>
    </div>
  )
}