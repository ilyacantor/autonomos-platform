/**
 * Status Color Utilities
 *
 * Centralized color functions for consistent status visualization across the application.
 * These utilities map status values to Tailwind CSS color classes.
 */

// ============================================================================
// Function Status Colors (optimal, warning, critical)
// ============================================================================

export type FunctionStatus = 'optimal' | 'warning' | 'critical';

/**
 * Returns badge-style color classes for function status
 * Used for status badges with semi-transparent backgrounds
 *
 * @example
 * <span className={`px-2 py-1 rounded ${getStatusColor('optimal')}`}>optimal</span>
 */
export function getStatusColor(status: string): string {
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
}

/**
 * Returns solid background color for progress bars
 *
 * @example
 * <div className={`h-full ${getProgressColor('optimal')}`} style={{ width: '80%' }} />
 */
export function getProgressColor(status: string): string {
  switch (status) {
    case 'optimal':
      return 'bg-green-500';
    case 'warning':
      return 'bg-yellow-500';
    case 'critical':
      return 'bg-red-500';
    default:
      return 'bg-gray-500';
  }
}

// ============================================================================
// AOA State Colors (Active, Planning, Executing, Learning, Idle)
// ============================================================================

export type AOAState = 'Active' | 'Planning' | 'Executing' | 'Learning' | 'Idle';

/**
 * Returns color classes for AOA state badges with border
 *
 * @example
 * <div className={`px-4 py-2 rounded-lg border ${getAOAStateColor('Active')}`}>Active</div>
 */
export function getAOAStateColor(state: string): string {
  switch (state) {
    case 'Active':
      return 'bg-green-500/20 text-green-400 border-green-500/30';
    case 'Planning':
      return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
    case 'Executing':
      return 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30';
    case 'Learning':
      return 'bg-purple-500/20 text-purple-400 border-purple-500/30';
    case 'Idle':
      return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
    default:
      return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
  }
}

// ============================================================================
// Agent Status Colors (running, idle, error, paused)
// ============================================================================

export type AgentStatus = 'running' | 'idle' | 'error' | 'paused';

/**
 * Returns solid background color for agent status indicators
 *
 * @example
 * <div className={`w-2 h-2 rounded-full ${getAgentStatusColor('running')}`} />
 */
export function getAgentStatusColor(status: string): string {
  switch (status) {
    case 'running':
      return 'bg-green-500';
    case 'idle':
      return 'bg-yellow-500';
    case 'error':
      return 'bg-red-500';
    case 'paused':
      return 'bg-gray-500';
    default:
      return 'bg-gray-500';
  }
}

// ============================================================================
// Vital/Metric Colors (threshold-based)
// ============================================================================

export type VitalType = 'uptime' | 'failed' | 'anomalies' | 'overrides' | 'load';

/**
 * Returns text color based on vital type and value thresholds
 *
 * Thresholds:
 * - uptime: >=99% green, >=95% yellow, <95% red
 * - failed: <=5 green, <=15 yellow, >15 red
 * - anomalies: <=10 green, <=25 yellow, >25 red
 * - overrides: <=5 green, <=15 yellow, >15 red
 * - load: <=60% green, <=80% yellow, >80% red
 *
 * @example
 * <span className={getVitalColor('uptime', 99.5)}>99.5%</span>
 */
export function getVitalColor(type: string, value: number): string {
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
}

// ============================================================================
// Health Status Colors (healthy, degraded, critical)
// ============================================================================

export type HealthStatus = 'healthy' | 'degraded' | 'critical';

/**
 * Returns text color for health status
 *
 * @example
 * <span className={getHealthStatusColor('healthy')}>Healthy</span>
 */
export function getHealthStatusColor(status: string): string {
  switch (status) {
    case 'healthy':
      return 'text-green-500';
    case 'degraded':
      return 'text-yellow-500';
    case 'critical':
      return 'text-red-500';
    default:
      return 'text-gray-500';
  }
}

// ============================================================================
// Generic Severity Colors
// ============================================================================

export type Severity = 'success' | 'info' | 'warning' | 'error';

/**
 * Returns color classes for generic severity-based styling
 *
 * @example
 * <div className={getSeverityColors('error').badge}>Error</div>
 */
export function getSeverityColors(severity: string): {
  badge: string;
  text: string;
  bg: string;
  border: string;
} {
  switch (severity) {
    case 'success':
      return {
        badge: 'bg-green-500/20 text-green-400',
        text: 'text-green-400',
        bg: 'bg-green-500',
        border: 'border-green-500/30',
      };
    case 'info':
      return {
        badge: 'bg-blue-500/20 text-blue-400',
        text: 'text-blue-400',
        bg: 'bg-blue-500',
        border: 'border-blue-500/30',
      };
    case 'warning':
      return {
        badge: 'bg-yellow-500/20 text-yellow-400',
        text: 'text-yellow-400',
        bg: 'bg-yellow-500',
        border: 'border-yellow-500/30',
      };
    case 'error':
      return {
        badge: 'bg-red-500/20 text-red-400',
        text: 'text-red-400',
        bg: 'bg-red-500',
        border: 'border-red-500/30',
      };
    default:
      return {
        badge: 'bg-gray-500/20 text-gray-400',
        text: 'text-gray-400',
        bg: 'bg-gray-500',
        border: 'border-gray-500/30',
      };
  }
}
