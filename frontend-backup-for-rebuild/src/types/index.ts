export type PersonaType = 'Data Engineer' | 'RevOps' | 'FinOps';

export interface User {
  name: string;
  avatar: string;
  persona: PersonaType;
}

export interface SourceNode {
  id: string;
  name: string;
  type: 'salesforce' | 'snowflake' | 'netsuite' | 'aws';
  status: 'online' | 'offline';
  recordsPerMin: number;
}

export interface AgentNode {
  id: string;
  name: string;
  type: 'revops' | 'finops';
  dataRequestsPerMin: number;
  lastSuccessfulRun: string;
}

export interface DCLStats {
  llmCallsPerMin: number;
  avgTokenUsage: number;
  ragIndexSize: string;
  ontologyEntities: number;
  mappingsInReview: number;
}

export interface MappingReview {
  id: string;
  timestamp: string;
  sourceField: string;
  unifiedField: string;
  confidence: number;
  sourceSample?: string;
  llmReasoning?: string;
}

export interface SchemaChange {
  id: string;
  timestamp: string;
  source: string;
  changeType: 'added' | 'modified' | 'removed';
  field: string;
  description: string;
}

export interface AgentPerformance {
  id: string;
  name: string;
  status: 'running' | 'warning' | 'error';
  executionsPerHour: number;
  cpuPercent: number;
  memoryMB: number;
}

export interface Connection {
  id: string;
  name: string;
  type: 'salesforce' | 'snowflake' | 'netsuite' | 'aws' | 'other';
  status: 'connected' | 'disconnected' | 'syncing';
  lastSync: string;
  isPaused: boolean;
}

export interface LineageNode {
  id: string;
  label: string;
  stage: 'source' | 'transformation' | 'ontology' | 'agent' | 'output';
  metadata?: Record<string, unknown>;
}

export type AOAState = 'Active' | 'Planning' | 'Executing' | 'Learning';
export type AutonomyMode = 'Observe' | 'Recommend' | 'Approve-to-Act' | 'Auto (Guardrails)' | 'Federated (xAO)';

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
