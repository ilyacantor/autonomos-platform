/**
 * useStatusColors - Hook for consistent status color mapping across the application
 *
 * This hook provides a unified interface to all status color utilities,
 * making it easy for components to access consistent color mappings for
 * various status types (function status, agent status, health, severity, etc.)
 *
 * @example
 * ```tsx
 * const { getAgentStatusColor, getHealthStatusColor, getSeverityColors } = useStatusColors();
 *
 * // Use in components
 * <div className={`w-2 h-2 rounded-full ${getAgentStatusColor('running')}`} />
 * <span className={getHealthStatusColor('healthy')}>Healthy</span>
 * <div className={getSeverityColors('error').badge}>Error</div>
 * ```
 */

import { useMemo } from 'react';
import {
  getStatusColor,
  getProgressColor,
  getAOAStateColor,
  getAgentStatusColor,
  getVitalColor,
  getHealthStatusColor,
  getSeverityColors,
  type FunctionStatus,
  type AOAState,
  type AgentStatus,
  type VitalType,
  type HealthStatus,
  type Severity,
} from '../utils/statusColors';

export interface UseStatusColorsResult {
  /**
   * Returns badge-style color classes for function status (optimal, warning, critical)
   * @example getStatusColor('optimal') => 'bg-green-500/20 text-green-400'
   */
  getStatusColor: (status: string) => string;

  /**
   * Returns solid background color for progress bars
   * @example getProgressColor('warning') => 'bg-yellow-500'
   */
  getProgressColor: (status: string) => string;

  /**
   * Returns color classes for AOA state badges with border
   * @example getAOAStateColor('Active') => 'bg-green-500/20 text-green-400 border-green-500/30'
   */
  getAOAStateColor: (state: string) => string;

  /**
   * Returns solid background color for agent status indicators
   * @example getAgentStatusColor('running') => 'bg-green-500'
   */
  getAgentStatusColor: (status: string) => string;

  /**
   * Returns text color based on vital type and value thresholds
   * @example getVitalColor('uptime', 99.5) => 'text-green-400'
   */
  getVitalColor: (type: string, value: number) => string;

  /**
   * Returns text color for health status
   * @example getHealthStatusColor('healthy') => 'text-green-500'
   */
  getHealthStatusColor: (status: string) => string;

  /**
   * Returns color classes object for generic severity-based styling
   * @example getSeverityColors('error') => { badge: '...', text: '...', bg: '...', border: '...' }
   */
  getSeverityColors: (severity: string) => {
    badge: string;
    text: string;
    bg: string;
    border: string;
  };
}

/**
 * Hook that provides access to all status color utility functions.
 *
 * Benefits of using this hook:
 * - Consistent color scheme across the entire application
 * - Easy to update colors in one place (statusColors.ts)
 * - Type-safe with TypeScript support
 * - Memoized for performance
 *
 * @returns Object containing all status color functions
 */
export function useStatusColors(): UseStatusColorsResult {
  // Memoize the return object to maintain referential equality
  // This prevents unnecessary re-renders in consuming components
  return useMemo(
    () => ({
      getStatusColor,
      getProgressColor,
      getAOAStateColor,
      getAgentStatusColor,
      getVitalColor,
      getHealthStatusColor,
      getSeverityColors,
    }),
    []
  );
}

// Re-export types for convenience
export type {
  FunctionStatus,
  AOAState,
  AgentStatus,
  VitalType,
  HealthStatus,
  Severity,
};

export default useStatusColors;
