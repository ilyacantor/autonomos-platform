import { useState } from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import AOAFunctionsPanel from './orchestration/AOAFunctionsPanel';
import AgentPerformanceMonitor from './orchestration/AgentPerformanceMonitor';
import type { AgentPerformance, xAOMetric } from '../types';
import aoaMetricsData from '../data/aoaMetrics.json';

interface AgenticOrchestrationContainerProps {
  agents: AgentPerformance[];
}

export default function AgenticOrchestrationContainer({ agents }: AgenticOrchestrationContainerProps) {
  const [xaoMetrics] = useState<xAOMetric[]>(aoaMetricsData.xaoFunctions as xAOMetric[]);

  const getMetricTooltip = (id: string): string => {
    const tooltips: Record<string, string> = {
      cross_discovery: 'Total number of active API endpoints discovered across all orchestrated agents (internal and 3rd party).',
      federation_health: 'Synchronization and uptime status of all orchestrated agents.',
      trust_score: 'Trust, reliability, and data fidelity score of agent interactions.',
      data_sovereignty: 'Compliance with regional data residency and sovereignty requirements.',
      cost_allocation: 'Distribution of compute and resource costs across orchestrated agents.',
      sla_compliance: 'Service-level adherence of each orchestrated agent relative to SLAs.',
      security_posture: 'Security assessment score across all orchestrated agents.',
      consensus_rate: 'Agreement rate on orchestration decisions across agents.',
      latency_p95: '95th percentile latency for cross-agent operations.',
      shared_agents: 'Number of agents operating across multiple domains.',
      interop_score: 'System compatibility and integration health score for all agents.',
      dispute_resolution: 'Average time to resolve orchestration conflicts between agents.',
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
      {/* Content */}
      <div className="space-y-6">
        {/* Agent Performance Monitor */}
        <div id="agent-performance-monitor">
          <AgentPerformanceMonitor agents={agents} />
        </div>
        
        {/* AOA Functions Panel */}
        <AOAFunctionsPanel />

        {/* xAO Metrics */}
        <div className="bg-slate-800/40 rounded-xl border border-cyan-500/30 p-6">
          <div className="mb-4">
            <h3 
              className="text-2xl font-medium text-cyan-400 mb-2 cursor-help" 
              title="Cross-Agentic Orchestration (xAO) orchestrates all agents—our own internal agents and 3rd party agents—providing unified coordination and governance."
            >
              xAO Metrics
            </h3>
            <p className="text-sm text-gray-400">
              Orchestration metrics for all agents (internal + 3rd party)
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
