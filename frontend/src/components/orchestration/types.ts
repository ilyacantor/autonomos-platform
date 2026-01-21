/**
 * Orchestration Dashboard Types
 *
 * Type definitions for the Agentic Orchestration Dashboard API responses.
 */

// Enums
export type AOAState = 'Active' | 'Planning' | 'Executing' | 'Learning' | 'Idle';

export type AutonomyMode =
  | 'Observe'
  | 'Recommend'
  | 'Approve-to-Act'
  | 'Auto (Guardrails)'
  | 'Federated (xAO)';

export type FunctionStatus = 'optimal' | 'warning' | 'critical';

export type AgentStatus = 'running' | 'warning' | 'error' | 'idle';

// API Response Types
export interface ActiveAgentsCount {
  current: number;
  total: number;
}

export interface OrchestrationVitals {
  state: AOAState;
  autonomy_mode: AutonomyMode;
  agent_uptime_pct: number;
  active_agents: ActiveAgentsCount;
  failed_steps_24h: number;
  anomaly_detections_24h: number;
  human_overrides_24h: number;
  triggers_per_min: number;
  compute_load_pct: number;
  pending_approvals: number;
  total_runs_24h: number;
  avg_run_duration_ms: number;
}

export interface AOAFunction {
  id: string;
  name: string;
  metric: number;
  target: number;
  status: FunctionStatus;
  unit: string;
  description: string;
}

export interface AOAFunctionsResponse {
  functions: AOAFunction[];
  timestamp: string;
}

export interface AgentPerformance {
  id: string;
  name: string;
  agent_type: string;
  status: AgentStatus;
  executions_per_hour: number;
  success_rate_pct: number;
  avg_duration_ms: number;
  total_runs_24h: number;
  failed_runs_24h: number;
  pending_approvals: number;
  last_run_at: string | null;
  cost_24h_usd: number;
  tokens_24h: number;
}

export interface AgentPerformanceResponse {
  agents: AgentPerformance[];
  total_agents: number;
  timestamp: string;
}

export interface AutonomyModeResponse {
  mode: AutonomyMode;
  updated_at: string;
}
