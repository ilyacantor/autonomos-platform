import { useState } from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import type { xAOMetric } from '../types';
import aoaMetricsData from '../data/aoaMetrics.json';

export default function XAOPage() {
  const [xaoMetrics] = useState<xAOMetric[]>(aoaMetricsData.xaoFunctions as xAOMetric[]);

  const getMetricTooltip = (id: string): string => {
    const tooltips: Record<string, string> = {
      cross_discovery: 'Shows the total number of active API endpoints discovered across federated enterprises.',
      federation_health: 'Represents the synchronization and uptime status of federated orchestrations.',
      trust_score: 'Quantifies the inter-enterprise trust, reliability, and data fidelity score of cross-domain exchanges.',
      data_sovereignty: 'Measures compliance with regional data residency and sovereignty requirements.',
      cost_allocation: 'Displays the distribution of compute and resource costs across federated orchestration domains.',
      sla_compliance: 'Tracks the service-level adherence of each orchestrated component relative to enterprise SLAs.',
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
    <div className="space-y-6">
      <div>
        <h1 
          className="text-3xl font-bold text-white mb-2 cursor-help" 
          title="Cross-Agentic Orchestration (xAO) coordinates multiple autonomOS instances across federated domains."
        >
          xAO
        </h1>
        <p className="text-gray-400">
          Cross-agentic orchestration metrics and coordination details
        </p>
      </div>

      <div className="bg-slate-800/60 rounded-xl border border-slate-700 p-6">
        <h2 className="text-xl font-semibold text-slate-200 mb-4">xAO Metrics</h2>
        <div className="space-y-3">
          {xaoMetrics.map((metric) => (
            <div
              key={metric.id}
              className="bg-slate-800/60 rounded-xl p-4 border border-slate-700 hover:border-cyan-500/50 transition-colors cursor-help"
              title={getMetricTooltip(metric.id)}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-base font-semibold text-slate-200">{metric.name}</h3>
                    {getTrendIcon(metric.trend)}
                  </div>
                  <p className="text-sm text-slate-500 mb-2">{metric.description}</p>
                </div>
                <div className="text-right">
                  <div className="text-2xl font-bold text-cyan-400">{metric.value}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
