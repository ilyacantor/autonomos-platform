# Agentic Orchestration Dashboard Components

This document contains the complete code and documentation for the **Agentic Orchestration** dashboard elements from the AutonomOS platform. This is designed to be handed off to another agent for replication in a new project.

**Excluded from this document:** DCL, Sankey graphs, narration, intelligence review, ontology, and connections-related components.

---

## Table of Contents

1. [Overview](#overview)
2. [Component Architecture](#component-architecture)
3. [TypeScript Types](#typescript-types)
4. [Mock Data (JSON)](#mock-data-json)
5. [Context Providers](#context-providers)
6. [Dashboard Components](#dashboard-components)
   - [AOAStatusCard](#aoastatuscard)
   - [AOAFunctionsPanel](#aoafunctionspanel)
   - [AgentPerformanceMonitor](#agentperformancemonitor)
   - [AutonomyModeToggle](#autonomymodetoggle)
7. [xAO Page Components](#xao-page-components)
   - [xAOPage](#xaopage)
8. [Tooltips Reference](#tooltips-reference)
9. [Dependencies](#dependencies)

---

## Overview

The Agentic Orchestration Dashboard provides:

- **AOA (AutonomOS Orchestration Agent)**: A meta-level agent that observes, coordinates, and optimizes all domain agents
- **xAO (Cross-Agentic Orchestration)**: Coordinates multiple autonomOS instances across federated domains
- **Autonomy Modes**: 5 levels of agent autonomy from "Observe" to "Federated (xAO)"
- **Real-time Metrics**: Live updates on agent health, performance, and orchestration status

---

## Component Architecture

```
Dashboard Page
├── AOAStatusCard (Overall orchestration status + vitals)
├── AOAFunctionsPanel (10 core AOA function metrics)
├── AgentPerformanceMonitor (Per-agent runtime metrics)
└── AutonomyModeToggle (Global autonomy level control)

xAO Page
└── xAO Metrics Panel (12 cross-enterprise metrics)
```

---

## TypeScript Types

```typescript
// File: types/index.ts

export type AOAState = 'Active' | 'Planning' | 'Executing' | 'Learning';

export type AutonomyMode = 
  | 'Observe' 
  | 'Recommend' 
  | 'Approve-to-Act' 
  | 'Auto (Guardrails)' 
  | 'Federated (xAO)';

export interface AOAMetric {
  id: string;
  name: string;
  metric: number;
  target: number;
  status: 'optimal' | 'warning' | 'critical';
  unit: string;
}

export interface xAOMetric {
  id: string;
  name: string;
  value: string;
  trend: 'up' | 'down' | 'stable';
  description: string;
}

export interface AOAVitals {
  agentUptime: number;
  activeAgents: {
    current: number;
    total: number;
  };
  failedSteps24h: number;
  anomalyDetections24h: number;
  humanOverrides: number;
  triggerCountPerMin: number;
  computeLoadAvg: number;
}

export interface AOAStatus {
  state: AOAState;
  vitals: AOAVitals;
}

export interface AgentPerformance {
  id: string;
  name: string;
  status: 'running' | 'warning' | 'error';
  executionsPerHour: number;
  cpuPercent: number;
  memoryMB: number;
}
```

---

## Mock Data (JSON)

```json
// File: data/aoaMetrics.json
{
  "vitals": {
    "agentUptime": 99.2,
    "activeAgents": {
      "current": 12,
      "total": 15
    },
    "failedSteps24h": 3,
    "anomalyDetections24h": 7,
    "humanOverrides": 2,
    "triggerCountPerMin": 147,
    "computeLoadAvg": 42
  },
  "aoaFunctions": [
    {
      "id": "discover",
      "name": "Discover",
      "metric": 87,
      "target": 90,
      "status": "optimal",
      "unit": "%"
    },
    {
      "id": "sense",
      "name": "Sense",
      "metric": 94,
      "target": 85,
      "status": "optimal",
      "unit": "%"
    },
    {
      "id": "policy",
      "name": "Policy",
      "metric": 76,
      "target": 80,
      "status": "warning",
      "unit": "%"
    },
    {
      "id": "plan",
      "name": "Plan",
      "metric": 91,
      "target": 90,
      "status": "optimal",
      "unit": "%"
    },
    {
      "id": "prioritize",
      "name": "Prioritize",
      "metric": 88,
      "target": 85,
      "status": "optimal",
      "unit": "%"
    },
    {
      "id": "execute",
      "name": "Execute",
      "metric": 82,
      "target": 90,
      "status": "warning",
      "unit": "%"
    },
    {
      "id": "budget",
      "name": "Budget",
      "metric": 95,
      "target": 90,
      "status": "optimal",
      "unit": "%"
    },
    {
      "id": "observe",
      "name": "Observe",
      "metric": 98,
      "target": 95,
      "status": "optimal",
      "unit": "%"
    },
    {
      "id": "learn",
      "name": "Learn",
      "metric": 72,
      "target": 80,
      "status": "warning",
      "unit": "%"
    },
    {
      "id": "lifecycle",
      "name": "Lifecycle",
      "metric": 89,
      "target": 85,
      "status": "optimal",
      "unit": "%"
    }
  ],
  "xaoFunctions": [
    {
      "id": "cross_discovery",
      "name": "Cross-Enterprise Discovery",
      "value": "847 endpoints",
      "trend": "up",
      "description": "Active API endpoints across federated systems"
    },
    {
      "id": "federation_health",
      "name": "Federation Health",
      "value": "96.2%",
      "trend": "stable",
      "description": "Overall health of federated orchestration"
    },
    {
      "id": "trust_score",
      "name": "Trust Score",
      "value": "8.7/10",
      "trend": "up",
      "description": "Inter-enterprise trust and reliability metric"
    },
    {
      "id": "data_sovereignty",
      "name": "Data Sovereignty",
      "value": "100%",
      "trend": "stable",
      "description": "Compliance with regional data requirements"
    },
    {
      "id": "cost_allocation",
      "name": "Cost Allocation",
      "value": "$124k/mo",
      "trend": "down",
      "description": "Distributed compute and resource costs"
    },
    {
      "id": "sla_compliance",
      "name": "SLA Compliance",
      "value": "99.7%",
      "trend": "stable",
      "description": "Service level agreement adherence"
    },
    {
      "id": "security_posture",
      "name": "Security Posture",
      "value": "A+",
      "trend": "stable",
      "description": "Federated security assessment score"
    },
    {
      "id": "consensus_rate",
      "name": "Consensus Rate",
      "value": "94.3%",
      "trend": "up",
      "description": "Multi-party agreement on orchestration decisions"
    },
    {
      "id": "latency_p95",
      "name": "Cross-Enterprise Latency (P95)",
      "value": "127ms",
      "trend": "down",
      "description": "95th percentile latency for federated operations"
    },
    {
      "id": "shared_agents",
      "name": "Shared Agents",
      "value": "42 active",
      "trend": "up",
      "description": "Agents operating across enterprise boundaries"
    },
    {
      "id": "interop_score",
      "name": "Interoperability Score",
      "value": "9.1/10",
      "trend": "stable",
      "description": "System compatibility and integration health"
    },
    {
      "id": "dispute_resolution",
      "name": "Dispute Resolution Time",
      "value": "4.2min",
      "trend": "down",
      "description": "Average time to resolve orchestration conflicts"
    }
  ]
}
```

**Agent Performance Mock Data:**

```typescript
// File: mocks/data.ts
export const mockAgentPerformance: AgentPerformance[] = [
  { id: 'ap1', name: 'RevOps Agent', status: 'running', executionsPerHour: 342, cpuPercent: 23, memoryMB: 512 },
  { id: 'ap2', name: 'FinOps Agent', status: 'running', executionsPerHour: 189, cpuPercent: 18, memoryMB: 448 },
  { id: 'ap3', name: 'Sales Forecasting', status: 'warning', executionsPerHour: 67, cpuPercent: 45, memoryMB: 892 },
  { id: 'ap4', name: 'Churn Predictor', status: 'running', executionsPerHour: 124, cpuPercent: 31, memoryMB: 674 },
  { id: 'ap5', name: 'Lead Scoring', status: 'running', executionsPerHour: 298, cpuPercent: 19, memoryMB: 423 },
];
```

---

## Context Providers

```typescript
// File: contexts/AutonomyContext.tsx
import { createContext, useContext, useState, ReactNode } from 'react';
import type { AutonomyMode } from '../types';

interface AutonomyContextType {
  autonomyMode: AutonomyMode;
  setAutonomyMode: (mode: AutonomyMode) => void;
  isModalOpen: boolean;
  setIsModalOpen: (open: boolean) => void;
  legacyMode: boolean;
  setLegacyMode: (legacy: boolean) => void;
}

const AutonomyContext = createContext<AutonomyContextType | undefined>(undefined);

export function AutonomyProvider({ children }: { children: ReactNode }) {
  const [autonomyMode, setAutonomyMode] = useState<AutonomyMode>('Auto (Guardrails)');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [legacyMode, setLegacyMode] = useState(false);

  return (
    <AutonomyContext.Provider value={{ autonomyMode, setAutonomyMode, isModalOpen, setIsModalOpen, legacyMode, setLegacyMode }}>
      {children}
    </AutonomyContext.Provider>
  );
}

export function useAutonomy() {
  const context = useContext(AutonomyContext);
  if (context === undefined) {
    throw new Error('useAutonomy must be used within an AutonomyProvider');
  }
  return context;
}
```

---

## Dashboard Components

### AOAStatusCard

**Purpose:** Displays overall orchestration status with real-time vitals.

**Tooltip:** "AutonomOS Agentic Orchestration Agent (AOA): A persistent, meta-level agent that observes, coordinates, and optimizes the behavior of all other domain agents (FinOps, RevOps, HR, etc.) running on the Data Connectivity Layer (DCL)."

```typescript
// File: components/AOAStatusCard.tsx
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
```

---

### AOAFunctionsPanel

**Purpose:** Displays 10 core AOA function metrics with status indicators and tooltips.

```typescript
// File: components/AOAFunctionsPanel.tsx
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
                  className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(metric.status)}`}
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
                  Target: {metric.target}{metric.unit}
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
```

---

### AgentPerformanceMonitor

**Purpose:** Displays real-time operational metrics for each domain agent.

**Tooltip:** "Displays real-time operational metrics for each domain agent. Each row represents execution throughput, CPU, and memory usage per active agent."

```typescript
// File: components/AgentPerformanceMonitor.tsx
import { ExternalLink } from 'lucide-react';
import type { AgentPerformance } from '../types';

interface AgentPerformanceMonitorProps {
  agents: AgentPerformance[];
}

export default function AgentPerformanceMonitor({ agents }: AgentPerformanceMonitorProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'bg-green-500';
      case 'warning':
        return 'bg-yellow-500';
      case 'error':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  const handleAgentClick = (agentName: string) => {
    if (agentName.includes('FinOps')) {
      window.open('https://finopsagent.onrender.com/', '_blank');
    } else if (agentName.includes('RevOps')) {
      window.open('https://autonomos-revops-agent.onrender.com', '_blank');
    }
  };

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 h-full flex flex-col">
      <h2 
        className="text-lg font-semibold text-white mb-4 cursor-help" 
        title="Displays real-time operational metrics for each domain agent. Each row represents execution throughput, CPU, and memory usage per active agent."
      >
        Active Agent Performance
      </h2>

      <div className="flex-1 overflow-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-800">
              <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider pb-3">Agent</th>
              <th className="text-center text-xs font-semibold text-gray-500 uppercase tracking-wider pb-3">Status</th>
              <th className="text-right text-xs font-semibold text-gray-500 uppercase tracking-wider pb-3">Exec/hr</th>
              <th className="text-right text-xs font-semibold text-gray-500 uppercase tracking-wider pb-3">CPU</th>
              <th className="text-right text-xs font-semibold text-gray-500 uppercase tracking-wider pb-3">Memory</th>
            </tr>
          </thead>
          <tbody>
            {agents.map((agent) => (
              <tr
                key={agent.id}
                className="border-b border-gray-800 hover:bg-gray-800/50 cursor-pointer transition-colors"
                onClick={() => handleAgentClick(agent.name)}
              >
                <td className="py-3">
                  <div className="flex items-center gap-2">
                    <div className="text-sm font-medium text-white">{agent.name}</div>
                    {(agent.name.includes('FinOps') || agent.name.includes('RevOps')) && (
                      <ExternalLink className="w-3.5 h-3.5 text-blue-400" />
                    )}
                  </div>
                </td>
                <td className="py-3">
                  <div className="flex justify-center">
                    <div
                      className={`w-2 h-2 rounded-full ${getStatusColor(agent.status)} ${
                        agent.status === 'running' ? 'animate-pulse' : ''
                      }`}
                    />
                  </div>
                </td>
                <td className="py-3 text-right">
                  <span className="text-sm text-gray-300">{agent.executionsPerHour}</span>
                </td>
                <td className="py-3 text-right">
                  <span
                    className={`text-sm font-medium ${
                      agent.cpuPercent > 40
                        ? 'text-red-400'
                        : agent.cpuPercent > 25
                        ? 'text-yellow-400'
                        : 'text-green-400'
                    }`}
                  >
                    {agent.cpuPercent}%
                  </span>
                </td>
                <td className="py-3 text-right">
                  <span className="text-sm text-gray-300">{agent.memoryMB} MB</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

---

### AutonomyModeToggle

**Purpose:** Global control for selecting the autonomy level of the orchestration system.

**Tooltip:** "Autonomy Mode controls how AutonomOS manages itself. 'Auto (Guardrails)' allows self-directed agent decisions within preset boundaries, while 'Manual' requires human confirmation for major actions."

```typescript
// File: components/AutonomyModeToggle.tsx
import { useState } from 'react';
import { Settings, ChevronDown } from 'lucide-react';
import { useAutonomy } from '../contexts/AutonomyContext';
import type { AutonomyMode } from '../types';

export default function AutonomyModeToggle() {
  const { autonomyMode, setAutonomyMode } = useAutonomy();
  const [isOpen, setIsOpen] = useState(false);

  const modes: AutonomyMode[] = [
    'Observe',
    'Recommend',
    'Approve-to-Act',
    'Auto (Guardrails)',
    'Federated (xAO)',
  ];

  const handleModeSelect = (mode: AutonomyMode) => {
    setAutonomyMode(mode);
    setIsOpen(false);
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition-colors"
        title="Autonomy Mode controls how AutonomOS manages itself. 'Auto (Guardrails)' allows self-directed agent decisions within preset boundaries, while 'Manual' requires human confirmation for major actions."
      >
        <Settings className="w-4 h-4 text-cyan-400" />
        <div className="text-left">
          <div className="text-xs text-slate-500">Autonomy Mode</div>
          <div className="text-sm font-medium text-slate-200">{autonomyMode}</div>
        </div>
        <ChevronDown className="w-4 h-4 text-slate-400" />
      </button>

      {isOpen && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setIsOpen(false)} />
          <div className="absolute right-0 mt-2 w-64 bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-20">
            <div className="p-2">
              <div className="px-3 py-2 text-xs font-semibold text-slate-500 uppercase tracking-wider border-b border-slate-700 mb-2">
                Select Autonomy Mode
              </div>
              {modes.map((mode) => (
                <button
                  key={mode}
                  onClick={() => handleModeSelect(mode)}
                  className={`w-full text-left px-3 py-2 rounded-md transition-colors ${
                    autonomyMode === mode
                      ? 'bg-cyan-600 text-white'
                      : 'text-slate-300 hover:bg-slate-700'
                  }`}
                >
                  <div className="font-medium">{mode}</div>
                  <div className="text-xs text-slate-400 mt-0.5">
                    {mode === 'Observe' && 'Monitor only, no actions'}
                    {mode === 'Recommend' && 'Suggest actions for review'}
                    {mode === 'Approve-to-Act' && 'Require approval before execution'}
                    {mode === 'Auto (Guardrails)' && 'Autonomous with safety limits'}
                    {mode === 'Federated (xAO)' && 'Cross-enterprise orchestration'}
                  </div>
                </button>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
```

---

## xAO Page Components

### xAOPage

**Purpose:** Full page for Cross-Agentic Orchestration metrics across federated domains.

**Page Tooltip:** "Cross-Agentic Orchestration (xAO) coordinates multiple autonomOS instances across federated domains."

```typescript
// File: components/xAOPage.tsx
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
```

---

## Tooltips Reference

### AOA Functions Tooltips

| Function ID | Label | Short Description | Full Description |
|------------|-------|-------------------|------------------|
| `discover` | Agent Registry Health | % of known agents responding to heartbeat pings | Discovers and registers all active domain agents and their capabilities across the organization. |
| `sense` | Event Classification Accuracy | % of incoming events correctly identified and enriched | Monitors real-time events, anomalies, and trigger patterns across all agents and connected systems. |
| `policy` | Policy Compliance | % of actions executing within guardrails (scope, permissions, SLAs) | Ensures compliance with internal and external governance rules during orchestration. |
| `plan` | Plan Generation Success | % of triggers converted into executable plans | Generates, adjusts, and simulates coordination plans based on agent readiness and data flow states. |
| `prioritize` | Conflict Resolution Rate | % of plan conflicts resolved automatically | Assigns execution order and resource priority across competing agentic workflows. |
| `execute` | Execution Success Rate | % of plan steps completed without errors | Carries out automated corrective or optimization actions orchestrated by AOA in live environments. |
| `budget` | Guardrail Integrity | % of actions staying within cost/time/risk thresholds | Manages financial control and cost integrity across autonomous compute and resource allocations. |
| `observe` | Trace Completeness | % of plans producing full observability traces | Continuously tracks operational signals, telemetry, and feedback loops to evaluate performance. |
| `learn` | Learning Impact | % of recurring plans that improved results | Continuously refines orchestration policies and mappings through reinforcement learning. |
| `lifecycle` | Agent Health Coverage | % of agents updated and resource-balanced | Oversees agent onboarding, updates, health, and retirement cycles across the federated network. |

### xAO Metrics Tooltips

| Metric ID | Tooltip |
|-----------|---------|
| `cross_discovery` | Shows the total number of active API endpoints discovered across federated enterprises. |
| `federation_health` | Represents the synchronization and uptime status of federated orchestrations. |
| `trust_score` | Quantifies the inter-enterprise trust, reliability, and data fidelity score of cross-domain exchanges. |
| `data_sovereignty` | Measures compliance with regional data residency and sovereignty requirements. |
| `cost_allocation` | Displays the distribution of compute and resource costs across federated orchestration domains. |
| `sla_compliance` | Tracks the service-level adherence of each orchestrated component relative to enterprise SLAs. |

### Autonomy Mode Descriptions

| Mode | Description |
|------|-------------|
| Observe | Monitor only, no actions |
| Recommend | Suggest actions for review |
| Approve-to-Act | Require approval before execution |
| Auto (Guardrails) | Autonomous with safety limits |
| Federated (xAO) | Cross-enterprise orchestration |

---

## Dependencies

```json
{
  "dependencies": {
    "lucide-react": "^0.300.0",
    "react": "^18.2.0"
  },
  "devDependencies": {
    "typescript": "^5.0.0",
    "tailwindcss": "^3.4.0"
  }
}
```

**Required Lucide Icons:**
- `Activity`, `Zap`, `Users`, `XCircle`, `AlertTriangle`, `UserCheck`, `Cpu`
- `HelpCircle`, `Settings`, `ChevronDown`
- `TrendingUp`, `TrendingDown`, `Minus`
- `ExternalLink`

---

## Implementation Notes

1. **Real-time Updates:** Components use `setInterval` to simulate real-time metric fluctuations. Replace with WebSocket or API polling for production.

2. **Styling:** Uses Tailwind CSS with a dark slate theme. Primary accent color is `cyan-400/500`.

3. **Color Thresholds:**
   - **Green:** Optimal/running
   - **Yellow:** Warning
   - **Red:** Critical/error

4. **Context Usage:** Wrap your app with `<AutonomyProvider>` to enable the autonomy mode toggle functionality.

5. **Mock Data:** Replace `aoaMetrics.json` with actual API data in production.

---

*Generated from AutonomOS Platform - October 2025*
