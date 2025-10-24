import { useState, useEffect } from 'react';
import { HelpCircle } from 'lucide-react';
import type { AOAMetric } from '../types';
import aoaMetricsData from '../data/aoaMetrics.json';

export default function AOAFunctionsPanel() {
  const [aoaMetrics, setAoaMetrics] = useState<AOAMetric[]>(aoaMetricsData.aoaFunctions as AOAMetric[]);

  useEffect(() => {
    const interval = setInterval(() => {
      setAoaMetrics((prev) =>
        prev.map((metric) => {
          const randomChange = Math.floor(Math.random() * 10) - 5;
          const newMetric = Math.max(0, Math.min(100, metric.metric + randomChange));
          let status: 'optimal' | 'warning' | 'critical' = 'optimal';

          if (newMetric < metric.target - 10) {
            status = 'critical';
          } else if (newMetric < metric.target) {
            status = 'warning';
          }

          return { ...metric, metric: newMetric, status };
        })
      );
    }, 8000);

    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'optimal':
        return 'bg-green-500/20 text-green-400';
      case 'warning':
        return 'bg-yellow-500/20 text-yellow-400';
      case 'critical':
        return 'bg-red-500/20 text-red-400';
      default:
        return 'bg-gray-500/20 text-gray-400';
    }
  };

  const getFunctionLabel = (id: string): { label: string; description: string; fullDescription: string } => {
    const labels: Record<string, { label: string; description: string; fullDescription: string }> = {
      discover: {
        label: 'Agent Registry Health',
        description: '% of known agents responding to heartbeat pings',
        fullDescription: 'Discovers and registers all active domain agents and their capabilities across the organization.',
      },
      sense: {
        label: 'Event Classification Accuracy',
        description: '% of incoming events correctly identified and enriched',
        fullDescription: 'Monitors real-time events, anomalies, and trigger patterns across all agents and connected systems.',
      },
      policy: {
        label: 'Policy Compliance',
        description: '% of actions executing within guardrails (scope, permissions, SLAs)',
        fullDescription: 'Ensures compliance with internal and external governance rules during orchestration.',
      },
      plan: {
        label: 'Plan Generation Success',
        description: '% of triggers converted into executable plans',
        fullDescription: 'Generates, adjusts, and simulates coordination plans based on agent readiness and data flow states.',
      },
      prioritize: {
        label: 'Conflict Resolution Rate',
        description: '% of plan conflicts resolved automatically',
        fullDescription: 'Assigns execution order and resource priority across competing agentic workflows.',
      },
      execute: {
        label: 'Execution Success Rate',
        description: '% of plan steps completed without errors',
        fullDescription: 'Carries out automated corrective or optimization actions orchestrated by AOA in live environments.',
      },
      budget: {
        label: 'Guardrail Integrity',
        description: '% of actions staying within cost/time/risk thresholds',
        fullDescription: 'Manages financial control and cost integrity across autonomous compute and resource allocations.',
      },
      observe: {
        label: 'Trace Completeness',
        description: '% of plans producing full observability traces',
        fullDescription: 'Continuously tracks operational signals, telemetry, and feedback loops to evaluate performance.',
      },
      learn: {
        label: 'Learning Impact',
        description: '% of recurring plans that improved results',
        fullDescription: 'Continuously refines orchestration policies and mappings through reinforcement learning.',
      },
      lifecycle: {
        label: 'Agent Health Coverage',
        description: '% of agents updated and resource-balanced',
        fullDescription: 'Oversees agent onboarding, updates, health, and retirement cycles across the federated network.',
      },
    };
    return labels[id] || { label: 'Unknown', description: 'No description available', fullDescription: 'No description available' };
  };

  return (
    <div className="bg-slate-800/60 rounded-xl border border-slate-700 p-6">
      <h2 className="text-xl font-semibold text-slate-200 mb-4">AOA Functions</h2>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {aoaMetrics.map((metric) => {
          const { label, description, fullDescription } = getFunctionLabel(metric.id);
          return (
            <div
              key={metric.id}
              className="bg-slate-800/60 rounded-xl p-4 border border-slate-700 hover:border-cyan-500/50 transition-colors group cursor-help"
              title={fullDescription}
            >
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-slate-200">{metric.name}</h3>
                <span
                  className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(
                    metric.status
                  )}`}
                >
                  {metric.status}
                </span>
              </div>
              <div className="mb-2">
                <div className="flex items-center gap-1 mb-1 group relative">
                  <span className="text-xs font-medium text-cyan-400">{label}</span>
                  <HelpCircle className="w-3 h-3 text-slate-500 hover:text-cyan-400 cursor-help" />
                  <div className="absolute left-0 top-full mt-2 w-48 bg-slate-950 border border-slate-700 rounded-lg p-3 text-xs text-slate-300 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10 shadow-xl">
                    {description}
                  </div>
                </div>
                <div className="text-3xl font-bold text-cyan-400">
                  {metric.metric}
                  <span className="text-lg text-slate-500">{metric.unit}</span>
                </div>
                <div className="text-xs text-slate-500 mt-1">
                  Target: {metric.target}
                  {metric.unit}
                </div>
              </div>
              <div className="w-full h-2 bg-slate-700 rounded-full overflow-hidden">
                <div
                  className={`h-full transition-all duration-500 ${
                    metric.status === 'optimal'
                      ? 'bg-green-500'
                      : metric.status === 'warning'
                      ? 'bg-yellow-500'
                      : 'bg-red-500'
                  }`}
                  style={{ width: `${metric.metric}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
      <div className="mt-4 text-center py-3 px-6 bg-slate-800/30 rounded-lg border border-slate-700">
        <p className="text-sm text-slate-400">
          Each % value represents real-time operational efficiency of that orchestration function vs its target SLO.
        </p>
      </div>
    </div>
  );
}
