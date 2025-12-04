import { useState, useEffect } from 'react';
import { X, TrendingUp, TrendingDown, Minus, Info, HelpCircle } from 'lucide-react';
import { useAutonomy } from '../contexts/AutonomyContext';
import type { AOAMetric, xAOMetric } from '../types';
import aoaMetricsData from '../data/aoaMetrics.json';

export default function AOADetailsModal() {
  const { isModalOpen, setIsModalOpen } = useAutonomy();
  const [activeTab, setActiveTab] = useState<'aoa' | 'xao' | 'plans'>('aoa');
  const [aoaMetrics, setAoaMetrics] = useState<AOAMetric[]>(aoaMetricsData.aoaFunctions as AOAMetric[]);
  const [xaoMetrics] = useState<xAOMetric[]>(aoaMetricsData.xaoFunctions as xAOMetric[]);

  useEffect(() => {
    if (!isModalOpen) return;

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
  }, [isModalOpen]);

  if (!isModalOpen) return null;

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

  const getFunctionLabel = (id: string): { label: string; description: string } => {
    const labels: Record<string, { label: string; description: string }> = {
      discover: {
        label: 'Agent Registry Health',
        description: '% of known agents responding to heartbeat pings',
      },
      sense: {
        label: 'Event Classification Accuracy',
        description: '% of incoming events correctly identified and enriched',
      },
      policy: {
        label: 'Policy Compliance',
        description: '% of actions executing within guardrails (scope, permissions, SLAs)',
      },
      plan: {
        label: 'Plan Generation Success',
        description: '% of triggers converted into executable plans',
      },
      prioritize: {
        label: 'Conflict Resolution Rate',
        description: '% of plan conflicts resolved automatically',
      },
      execute: {
        label: 'Execution Success Rate',
        description: '% of plan steps completed without errors',
      },
      budget: {
        label: 'Guardrail Integrity',
        description: '% of actions staying within cost/time/risk thresholds',
      },
      observe: {
        label: 'Trace Completeness',
        description: '% of plans producing full observability traces',
      },
      learn: {
        label: 'Learning Impact',
        description: '% of recurring plans that improved results',
      },
      lifecycle: {
        label: 'Agent Health Coverage',
        description: '% of agents updated and resource-balanced',
      },
    };
    return labels[id] || { label: 'Unknown', description: 'No description available' };
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-slate-900 rounded-2xl border border-slate-700 max-w-6xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        <div className="sticky top-0 bg-slate-900 border-b border-slate-700 p-6 flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-slate-200">AutonomOS Orchestration Details</h2>
            <p className="text-sm text-slate-500 mt-1">Real-time orchestration metrics and functions</p>
          </div>
          <button
            onClick={() => setIsModalOpen(false)}
            className="p-2 hover:bg-slate-800 rounded-lg transition-colors"
          >
            <X className="w-6 h-6 text-slate-400" />
          </button>
        </div>

        <div className="flex gap-2 px-6 pt-4 border-b border-slate-800">
          <button
            onClick={() => setActiveTab('aoa')}
            className={`px-4 py-2 rounded-t-lg font-medium transition-colors ${
              activeTab === 'aoa'
                ? 'bg-cyan-600 text-white'
                : 'bg-slate-800 text-slate-400 hover:text-slate-200'
            }`}
          >
            AOA Functions
          </button>
          <button
            onClick={() => setActiveTab('xao')}
            className={`px-4 py-2 rounded-t-lg font-medium transition-colors ${
              activeTab === 'xao'
                ? 'bg-cyan-600 text-white'
                : 'bg-slate-800 text-slate-400 hover:text-slate-200'
            }`}
          >
            xAO Functions
          </button>
          <button
            onClick={() => setActiveTab('plans')}
            className={`px-4 py-2 rounded-t-lg font-medium transition-colors ${
              activeTab === 'plans'
                ? 'bg-cyan-600 text-white'
                : 'bg-slate-800 text-slate-400 hover:text-slate-200'
            }`}
          >
            Live Plans
          </button>
        </div>

        <div className="flex-1 overflow-auto p-6">
          {activeTab === 'aoa' && (
            <>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
                {aoaMetrics.map((metric) => {
                  const { label, description } = getFunctionLabel(metric.id);
                  return (
                    <div
                      key={metric.id}
                      className="bg-slate-800/60 rounded-xl p-4 border border-slate-700 hover:border-cyan-500/50 transition-colors group"
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
              <div className="text-center py-4 px-6 bg-slate-800/30 rounded-lg border border-slate-700">
                <p className="text-sm text-slate-400">
                  Each % value represents real-time operational efficiency of that orchestration function vs its target SLO.
                </p>
              </div>
            </>
          )}

          {activeTab === 'xao' && (
            <div className="space-y-3">
              {xaoMetrics.map((metric) => (
                <div
                  key={metric.id}
                  className="bg-slate-800/60 rounded-xl p-4 border border-slate-700 hover:border-cyan-500/50 transition-colors"
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
          )}

          {activeTab === 'plans' && (
            <div className="bg-gradient-to-br from-slate-800/40 to-slate-900/40 rounded-xl border-2 border-dashed border-slate-700 p-12 text-center min-h-[400px] flex flex-col items-center justify-center">
              <Info className="w-16 h-16 text-cyan-400 mb-4" />
              <h3 className="text-2xl font-bold text-slate-200 mb-3">Live Plans Visualization</h3>
              <p className="text-slate-400 max-w-2xl">
                This area is reserved for your Sankey diagram or other visualization showing
                real-time orchestration plans, agent execution flows, and resource allocation
                decisions.
              </p>
              <div className="mt-6 px-6 py-3 bg-slate-800 rounded-lg border border-slate-700">
                <span className="text-sm text-slate-500">
                  Integration point for existing visualization component
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
