import { useState, useEffect } from 'react'
import TopologyView from './components/TopologyView'
import MetricsChart from './components/MetricsChart'
import ConnectorStatus from './components/ConnectorStatus'
import ChaosControl from './components/ChaosControl'
import { apiClient } from './api/client'

interface Metrics {
  connectors: number
  metrics_summary: any
  dlq_stats: any
  workflows: any
}

function App() {
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [connectors, setConnectors] = useState([])
  const [workflows, setWorkflows] = useState([])
  const [refreshInterval, setRefreshInterval] = useState(2000)

  // Fetch metrics periodically
  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const metricsData = await apiClient.getMetrics()
        setMetrics(metricsData)
      } catch (error) {
        console.error('Failed to fetch metrics:', error)
      }
    }

    const fetchConnectors = async () => {
      try {
        const data = await apiClient.getConnectors()
        setConnectors(data.connectors)
      } catch (error) {
        console.error('Failed to fetch connectors:', error)
      }
    }

    const fetchWorkflows = async () => {
      try {
        const data = await apiClient.getWorkflows()
        setWorkflows(data.workflows)
      } catch (error) {
        console.error('Failed to fetch workflows:', error)
      }
    }

    // Initial fetch
    fetchMetrics()
    fetchConnectors()
    fetchWorkflows()

    // Set up intervals
    const metricsInterval = setInterval(fetchMetrics, refreshInterval)
    const connectorsInterval = setInterval(fetchConnectors, refreshInterval * 2)
    const workflowsInterval = setInterval(fetchWorkflows, refreshInterval)

    return () => {
      clearInterval(metricsInterval)
      clearInterval(connectorsInterval)
      clearInterval(workflowsInterval)
    }
  }, [refreshInterval])

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <header className="bg-gray-800 shadow-lg">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-blue-400">AAM Gauntlet</h1>
              <p className="text-gray-400">Adaptive API Mesh Stress Testing Demo</p>
            </div>
            <div className="flex items-center space-x-4">
              <div className="text-sm">
                <span className="text-gray-400">Refresh Rate: </span>
                <select
                  value={refreshInterval}
                  onChange={(e) => setRefreshInterval(Number(e.target.value))}
                  className="bg-gray-700 text-white px-2 py-1 rounded"
                >
                  <option value={1000}>1s</option>
                  <option value={2000}>2s</option>
                  <option value={5000}>5s</option>
                  <option value={10000}>10s</option>
                </select>
              </div>
              {metrics && (
                <div className="flex items-center space-x-4 text-sm">
                  <div>
                    <span className="text-gray-400">Connectors: </span>
                    <span className="text-green-400 font-bold">{metrics.connectors}</span>
                  </div>
                  <div>
                    <span className="text-gray-400">Workflows: </span>
                    <span className="text-blue-400 font-bold">
                      {metrics.workflows?.running || 0} running
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-400">DLQ: </span>
                    <span className="text-yellow-400 font-bold">
                      {metrics.dlq_stats?.pending || 0} pending
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-6">
        {/* Chaos Control */}
        <div className="mb-6">
          <ChaosControl onScenarioRun={(scenario) => console.log('Running scenario:', scenario)} />
        </div>

        {/* Topology and Metrics */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <div>
            <h2 className="text-xl font-bold mb-4 text-gray-300">System Topology</h2>
            <TopologyView connectors={connectors} workflows={workflows} />
          </div>
          <div>
            <h2 className="text-xl font-bold mb-4 text-gray-300">Live Metrics</h2>
            {metrics && <MetricsChart metrics={metrics.metrics_summary} />}
          </div>
        </div>

        {/* Connector Status */}
        <div>
          <h2 className="text-xl font-bold mb-4 text-gray-300">Connector Status</h2>
          <ConnectorStatus connectors={connectors} workflows={workflows} />
        </div>
      </main>
    </div>
  )
}

export default App