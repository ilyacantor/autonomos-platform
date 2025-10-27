import { useState } from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import AOAStatusCard from './AOAStatusCard';
import AOAFunctionsPanel from './AOAFunctionsPanel';
import AgentPerformanceMonitor from './AgentPerformanceMonitor';
import type { AgentPerformance, xAOMetric } from '../types';
import aoaMetricsData from '../data/aoaMetrics.json';

interface AgenticOrchestrationContainerProps {
  agents: AgentPerformance[];
}

export default function AgenticOrchestrationContainer({ agents }: AgenticOrchestrationContainerProps) {
  const [xaoMetrics] = useState<xAOMetric[]>(aoaMetricsData.xaoFunctions as xAOMetric[]);

  const getMetricTooltip = (id: string): string => {
    const tooltips: Record<string, string> = {
      cross_discovery: 'Shows the total number of active API endpoints discovered across federated enterprises.',
      federation_health: 'Represents the synchronization and uptime status of federated orchestrations.',
      trust_score: 'Quantifies the inter-enterprise trust, reliability, and data fidelity score of cross-domain exchanges.',
      data_sovereignty: 'Measures compliance with regional data residency and sovereignty requirements.',
      cost_allocation: 'Displays the distribution of compute and resource costs across federated orchestration domains.',
      sla_compliance: 'Tracks the service-level adherence of each orchestrated component relative to enterprise SLAs.',
      security_posture: 'Federated security assessment score across all connected systems.',
      consensus_rate: 'Multi-party agreement rate on orchestration decisions.',
      latency_p95: '95th percentile latency for cross-enterprise federated operations.',
      shared_agents: 'Number of agents operating across enterprise boundaries.',
      interop_score: 'System compatibility and integration health score.',
      dispute_resolution: 'Average time to resolve orchestration conflicts between systems.',
    };
    return tooltips[id] || '';
  };

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'up':
        return <TrendingUp className="w-4 h-4 text-green-400" />;
      case 'down':
        return <TrendingDown className="w-4 h-4 text-red-400" />;
      case 'stable':
        return <Minus className="w-4 h-4 text-gray-400" />;
    }
  };

  return (
    <div className="bg-black border-t border-b border-cyan-500/30 py-12 -mx-6 px-6">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-3xl font-medium text-cyan-400 mb-3">
          Agentic Orchestration at Scale
        </h2>
        <div className="space-y-1 text-white">
          <p className="text-base font-normal">Orchestrate agents across ecosystems</p>
          <p className="text-base font-normal">Observe every agent interaction in real time</p>
          <p className="text-base font-normal">Govern any agent, built anywhere</p>
        </div>
      </div>

      {/* Content */}
      <div className="space-y-6">
        {/* AOA Status and Agent Performance */}
        <div id="agent-performance-monitor" className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-6">
          <AOAStatusCard />
          <AgentPerformanceMonitor agents={agents} />
        </div>
        
        {/* AOA Functions Panel */}
        <AOAFunctionsPanel />

        {/* xAO Metrics */}
        <div className="bg-slate-800/40 rounded-xl border border-cyan-500/30 p-6">
          <div className="mb-4">
            <h3 
              className="text-2xl font-medium text-cyan-400 mb-2 cursor-help" 
              title="Cross-Agentic Orchestration (xAO) coordinates multiple autonomOS instances across federated domains."
            >
              xAO Metrics
            </h3>
            <p className="text-sm text-gray-400">
              Cross-agentic orchestration metrics and coordination details
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {xaoMetrics.map((metric) => (
              <div
                key={metric.id}
                className="bg-slate-800/60 rounded-xl p-4 border border-slate-700 hover:border-cyan-500/50 transition-colors cursor-help"
                title={getMetricTooltip(metric.id)}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h4 className="text-sm font-medium text-slate-200">{metric.name}</h4>
                      {getTrendIcon(metric.trend)}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-xl font-bold text-cyan-400">{metric.value}</div>
                  </div>
                </div>
                <p className="text-xs text-slate-500">{metric.description}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
