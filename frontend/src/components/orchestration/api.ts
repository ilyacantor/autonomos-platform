/**
 * Orchestration Dashboard API Client
 *
 * Provides functions to fetch data from the orchestration API endpoints.
 */

import type {
  OrchestrationVitals,
  AOAFunctionsResponse,
  AgentPerformanceResponse,
  AutonomyMode,
  AutonomyModeResponse,
} from './types';

const API_BASE = '/api/v1/orchestration';

/**
 * Fetch orchestration vitals (real-time system health).
 */
export async function fetchVitals(): Promise<OrchestrationVitals> {
  const response = await fetch(`${API_BASE}/vitals`);
  if (!response.ok) {
    throw new Error(`Failed to fetch vitals: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Fetch AOA function metrics.
 */
export async function fetchFunctions(): Promise<AOAFunctionsResponse> {
  const response = await fetch(`${API_BASE}/functions`);
  if (!response.ok) {
    throw new Error(`Failed to fetch functions: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Fetch agent performance metrics.
 */
export async function fetchAgentPerformance(
  limit: number = 20
): Promise<AgentPerformanceResponse> {
  const response = await fetch(`${API_BASE}/agents/performance?limit=${limit}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch agent performance: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Fetch current autonomy mode.
 */
export async function fetchAutonomyMode(): Promise<AutonomyModeResponse> {
  const response = await fetch(`${API_BASE}/autonomy-mode`);
  if (!response.ok) {
    throw new Error(`Failed to fetch autonomy mode: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Update autonomy mode.
 */
export async function updateAutonomyMode(
  mode: AutonomyMode
): Promise<AutonomyModeResponse> {
  const response = await fetch(`${API_BASE}/autonomy-mode`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode }),
  });
  if (!response.ok) {
    throw new Error(`Failed to update autonomy mode: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Seed demo agents response.
 */
export interface SeedResponse {
  created: string[];
  existing: string[];
  message: string;
}

/**
 * Seed demo agents for the dashboard.
 */
export async function seedDemoAgents(): Promise<SeedResponse> {
  const response = await fetch(`${API_BASE}/seed-demo-agents`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!response.ok) {
    throw new Error(`Failed to seed agents: ${response.statusText}`);
  }
  return response.json();
}
