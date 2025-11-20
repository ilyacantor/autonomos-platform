import { useState, useEffect } from 'react';
import TopologyView from './components/TopologyView';
import MetricsChart from './components/MetricsChart';
import ConnectorStatus from './components/ConnectorStatus';
import ChaosControl from './components/ChaosControl';
import { gauntletClient } from './api/gauntletClient';
import type { Connector, Workflow, Metrics } from './types';

export default function AAMGauntlet() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [refreshInterval, setRefreshInterval] = useState(2000);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const metricsData = await gauntletClient.getMetrics();
        setMetrics(metricsData);
        setError(null);
      } catch (error) {
        console.error('Failed to fetch metrics:', error);
        setError('Failed to connect to AAM Backend. Make sure the AAM services are running.');
      }
    };

    const fetchConnectors = async () => {
      try {
        const data = await gauntletClient.getConnectors();
        setConnectors(data.connectors);
      } catch (error) {
        console.error('Failed to fetch connectors:', error);
      }
    };

    const fetchWorkflows = async () => {
      try {
        const data = await gauntletClient.getWorkflows();
        setWorkflows(data.workflows);
      } catch (error) {
        console.error('Failed to fetch workflows:', error);
      }
    };

    fetchMetrics();
    fetchConnectors();
    fetchWorkflows();

    const metricsInterval = setInterval(fetchMetrics, refreshInterval);
    const connectorsInterval = setInterval(fetchConnectors, refreshInterval * 2);
    const workflowsInterval = setInterval(fetchWorkflows, refreshInterval);

    return () => {
      clearInterval(metricsInterval);
      clearInterval(connectorsInterval);
      clearInterval(workflowsInterval);
    };
  }, [refreshInterval]);

  if (error) {
    return (
      <div className="bg-red-900/20 border border-red-700 rounded-xl p-6">
        <div className="text-red-400 text-center">
          <div className="text-lg font-semibold mb-2">Connection Error</div>
          <div className="text-sm">{error}</div>
          <div className="text-xs mt-2 text-gray-400">
            Ensure AAM Gauntlet API Farm (port 8000) and AAM Backend (port 8080) workflows are running.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="bg-gray-800/30 border border-gray-700 rounded-xl p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4 text-sm">
            {metrics && (
              <>
                <div>
                  <span className="text-gray-400">Connectors: </span>
                  <span className="text-green-400 font-bold">{metrics.connectors}</span>
                </div>
                <div>
                  <span className="text-gray-400">Workflows: </span>
                  <span className="text-cyan-400 font-bold">
                    {metrics.workflows?.running || 0} running
                  </span>
                </div>
                <div>
                  <span className="text-gray-400">DLQ: </span>
                  <span className="text-yellow-400 font-bold">
                    {metrics.dlq_stats?.pending || 0} pending
                  </span>
                </div>
              </>
            )}
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-400">Refresh Rate:</span>
            <select
              value={refreshInterval}
              onChange={(e) => setRefreshInterval(Number(e.target.value))}
              className="bg-gray-700 border border-gray-600 text-white px-2 py-1 rounded text-sm"
            >
              <option value={1000}>1s</option>
              <option value={2000}>2s</option>
              <option value={5000}>5s</option>
              <option value={10000}>10s</option>
            </select>
          </div>
        </div>
      </div>

      <ChaosControl onScenarioRun={(scenario) => console.log('Running scenario:', scenario)} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div>
          <h2 className="text-xl font-bold mb-4 text-gray-300">System Topology</h2>
          <TopologyView connectors={connectors} workflows={workflows} />
        </div>
        <div>
          <h2 className="text-xl font-bold mb-4 text-gray-300">Live Metrics</h2>
          <MetricsChart metrics={metrics?.metrics_summary || null} />
        </div>
      </div>

      <div>
        <h2 className="text-xl font-bold mb-4 text-gray-300">Connector Status</h2>
        <ConnectorStatus connectors={connectors} workflows={workflows} />
      </div>
    </div>
  );
}
