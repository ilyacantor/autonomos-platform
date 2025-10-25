import { useEffect, useState } from 'react';
import { Activity, Zap, Users, XCircle, AlertTriangle, UserCheck, Cpu } from 'lucide-react';
import { useAutonomy } from '../contexts/AutonomyContext';
import type { AOAState, AOAStatus } from '../types';
import aoaMetricsData from '../data/aoaMetrics.json';

export default function AOAStatusCard() {
  const { autonomyMode } = useAutonomy();
  const [aoaStatus, setAoaStatus] = useState<AOAStatus>({
    state: 'Active',
    vitals: {
      agentUptime: aoaMetricsData.vitals.agentUptime,
      activeAgents: aoaMetricsData.vitals.activeAgents,
      failedSteps24h: aoaMetricsData.vitals.failedSteps24h,
      anomalyDetections24h: aoaMetricsData.vitals.anomalyDetections24h,
      humanOverrides: aoaMetricsData.vitals.humanOverrides,
      triggerCountPerMin: aoaMetricsData.vitals.triggerCountPerMin,
      computeLoadAvg: aoaMetricsData.vitals.computeLoadAvg,
    },
  });

  useEffect(() => {
    const states: AOAState[] = ['Active', 'Planning', 'Executing', 'Learning'];
    let stateIndex = 0;

    const interval = setInterval(() => {
      stateIndex = (stateIndex + 1) % states.length;
      setAoaStatus((prev) => ({
        ...prev,
        state: states[stateIndex],
        vitals: {
          agentUptime: Math.max(95, Math.min(100, prev.vitals.agentUptime + (Math.random() - 0.5) * 0.5)),
          activeAgents: {
            current: Math.max(8, Math.min(15, prev.vitals.activeAgents.current + Math.floor(Math.random() * 3 - 1))),
            total: 15,
          },
          failedSteps24h: Math.max(0, prev.vitals.failedSteps24h + Math.floor(Math.random() * 3 - 1)),
          anomalyDetections24h: Math.max(0, prev.vitals.anomalyDetections24h + Math.floor(Math.random() * 3 - 1)),
          humanOverrides: Math.max(0, prev.vitals.humanOverrides + Math.floor(Math.random() * 2)),
          triggerCountPerMin: Math.max(100, prev.vitals.triggerCountPerMin + Math.floor(Math.random() * 10 - 5)),
          computeLoadAvg: Math.max(20, Math.min(85, prev.vitals.computeLoadAvg + Math.floor(Math.random() * 10 - 5))),
        },
      }));
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  const getStateColor = (state: AOAState) => {
    switch (state) {
      case 'Active':
        return 'bg-green-500/20 text-green-400 border-green-500/30';
      case 'Planning':
        return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
      case 'Executing':
        return 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30';
      case 'Learning':
        return 'bg-purple-500/20 text-purple-400 border-purple-500/30';
    }
  };

  const getVitalColor = (type: string, value: number) => {
    switch (type) {
      case 'uptime':
        return value >= 99 ? 'text-green-400' : value >= 95 ? 'text-yellow-400' : 'text-red-400';
      case 'failed':
        return value <= 5 ? 'text-green-400' : value <= 15 ? 'text-yellow-400' : 'text-red-400';
      case 'anomalies':
        return value <= 10 ? 'text-green-400' : value <= 25 ? 'text-yellow-400' : 'text-red-400';
      case 'overrides':
        return value <= 5 ? 'text-green-400' : value <= 15 ? 'text-yellow-400' : 'text-red-400';
      case 'load':
        return value <= 60 ? 'text-green-400' : value <= 80 ? 'text-yellow-400' : 'text-red-400';
      default:
        return 'text-cyan-400';
    }
  };

  return (
    <div className="rounded-2xl shadow-md p-6 bg-slate-800/60 border border-slate-700 relative overflow-hidden">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-xl flex items-center justify-center">
            <Activity className="w-6 h-6 text-white" />
          </div>
          <div 
            className="cursor-help"
            title="AutonomOS Agentic Orchestration Agent (AOA): A persistent, meta-level agent that observes, coordinates, and optimizes the behavior of all other domain agents (FinOps, RevOps, HR, etc.) running on the Data Connectivity Layer (DCL)."
          >
            <h2 className="text-xl font-semibold text-slate-200">AutonomOS Orchestration Layer</h2>
            <p className="text-sm text-slate-500">Mode: {autonomyMode}</p>
          </div>
        </div>
        <div className={`px-4 py-2 rounded-lg border ${getStateColor(aoaStatus.state)}`}>
          <span className="text-sm font-semibold">{aoaStatus.state}</span>
        </div>
      </div>

      <div className="flex items-center gap-3 mb-6 flex-wrap">
        <div className="flex items-center gap-2 bg-slate-900/50 rounded-lg px-4 py-3 border border-slate-700">
          <Activity className="w-4 h-4 text-cyan-400" />
          <div>
            <div className="text-xs text-slate-500">Agent Uptime</div>
            <div className={`text-lg font-bold transition-colors ${getVitalColor('uptime', aoaStatus.vitals.agentUptime)}`}>
              {aoaStatus.vitals.agentUptime.toFixed(1)}%
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 bg-slate-900/50 rounded-lg px-4 py-3 border border-slate-700">
          <Users className="w-4 h-4 text-cyan-400" />
          <div>
            <div className="text-xs text-slate-500">Active Agents</div>
            <div className="text-lg font-bold text-cyan-400">
              {aoaStatus.vitals.activeAgents.current} / {aoaStatus.vitals.activeAgents.total}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 bg-slate-900/50 rounded-lg px-4 py-3 border border-slate-700">
          <XCircle className="w-4 h-4 text-cyan-400" />
          <div>
            <div className="text-xs text-slate-500">Failed Steps (24h)</div>
            <div className={`text-lg font-bold transition-colors ${getVitalColor('failed', aoaStatus.vitals.failedSteps24h)}`}>
              {aoaStatus.vitals.failedSteps24h}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 bg-slate-900/50 rounded-lg px-4 py-3 border border-slate-700">
          <AlertTriangle className="w-4 h-4 text-cyan-400" />
          <div>
            <div className="text-xs text-slate-500">Anomalies (24h)</div>
            <div className={`text-lg font-bold transition-colors ${getVitalColor('anomalies', aoaStatus.vitals.anomalyDetections24h)}`}>
              {aoaStatus.vitals.anomalyDetections24h}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 bg-slate-900/50 rounded-lg px-4 py-3 border border-slate-700">
          <UserCheck className="w-4 h-4 text-cyan-400" />
          <div>
            <div className="text-xs text-slate-500">Human Overrides</div>
            <div className={`text-lg font-bold transition-colors ${getVitalColor('overrides', aoaStatus.vitals.humanOverrides)}`}>
              {aoaStatus.vitals.humanOverrides}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 bg-slate-900/50 rounded-lg px-4 py-3 border border-slate-700">
          <Zap className="w-4 h-4 text-cyan-400" />
          <div>
            <div className="text-xs text-slate-500">Triggers/min</div>
            <div className="text-lg font-bold text-cyan-400">
              {aoaStatus.vitals.triggerCountPerMin}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 bg-slate-900/50 rounded-lg px-4 py-3 border border-slate-700">
          <Cpu className="w-4 h-4 text-cyan-400" />
          <div>
            <div className="text-xs text-slate-500">Compute Load</div>
            <div className={`text-lg font-bold transition-colors ${getVitalColor('load', aoaStatus.vitals.computeLoadAvg)}`}>
              {aoaStatus.vitals.computeLoadAvg}%
            </div>
          </div>
        </div>
      </div>

      {aoaStatus.state === 'Executing' && (
        <div className="absolute bottom-0 left-0 w-full h-1 bg-slate-700 overflow-hidden">
          <div className="h-full bg-gradient-to-r from-cyan-500 via-blue-500 to-cyan-500 animate-pulse" />
        </div>
      )}
    </div>
  );
}
