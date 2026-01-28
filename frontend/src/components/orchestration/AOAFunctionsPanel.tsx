/**
 * AOA Functions Panel Component
 *
 * Displays the 10 core AOA function metrics with real-time data from the API.
 * Each function represents a core orchestration capability.
 */

import { HelpCircle, RefreshCw, AlertTriangle } from 'lucide-react';
import type { AOAFunctionsResponse } from './types';
import { fetchFunctions } from './api';
import { usePolledData } from '../../hooks/usePolledData';
import { getStatusColor, getProgressColor } from '../../utils/statusColors';

// Polling interval in milliseconds
const POLL_INTERVAL = 15000;

export default function AOAFunctionsPanel() {
  const {
    data,
    loading,
    error,
    refresh: loadFunctions,
  } = usePolledData<AOAFunctionsResponse>(fetchFunctions, POLL_INTERVAL);

  if (loading && !data) {
    return (
      <div className="bg-slate-800/60 rounded-xl border border-slate-700 p-6">
        <div className="flex items-center justify-center py-8">
          <RefreshCw className="w-6 h-6 text-cyan-400 animate-spin" />
          <span className="ml-3 text-slate-400">Loading functions...</span>
        </div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="bg-slate-800/60 rounded-xl border border-red-500/30 p-6">
        <div className="flex items-center gap-3 text-red-400">
          <AlertTriangle className="w-6 h-6" />
          <span>Failed to load functions: {error}</span>
        </div>
        <button
          onClick={loadFunctions}
          className="mt-4 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-slate-200 text-sm"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="bg-slate-800/60 rounded-xl border border-slate-700 p-6">
      <div className="mb-4">
        <h2 className="text-xl font-medium text-cyan-400 mb-1">AOA Functions</h2>
        <p className="text-sm text-gray-400">Core orchestration capability metrics</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {data.functions.map((func) => (
          <div
            key={func.id}
            className="bg-slate-800/60 rounded-xl p-4 border border-slate-700 hover:border-cyan-500/50 transition-colors group cursor-help"
            title={func.description}
          >
            {/* Header */}
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-medium text-slate-200">{func.name}</h3>
              <span
                className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(func.status)}`}
              >
                {func.status}
              </span>
            </div>

            {/* Metric */}
            <div className="mb-2">
              <div className="flex items-center gap-1 mb-1 relative">
                <span className="text-xs font-medium text-cyan-400 truncate">
                  {func.description.split(' - ')[0]}
                </span>
                <HelpCircle className="w-3 h-3 text-slate-500 hover:text-cyan-400 cursor-help flex-shrink-0" />
                <div className="absolute left-0 top-full mt-2 w-48 bg-slate-950 border border-slate-700 rounded-lg p-3 text-xs text-slate-300 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10 shadow-xl">
                  {func.description}
                </div>
              </div>
              <div className="text-3xl text-cyan-400">
                {func.metric}
                <span className="text-lg text-slate-500">{func.unit}</span>
              </div>
              <div className="text-xs text-slate-500 mt-1">
                Target: {func.target}{func.unit}
              </div>
            </div>

            {/* Progress Bar */}
            <div className="w-full h-2 bg-slate-700 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all duration-500 ${getProgressColor(func.status)}`}
                style={{ width: `${Math.min(100, func.metric)}%` }}
              />
            </div>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="mt-4 text-center py-3 px-6 bg-slate-800/30 rounded-lg border border-slate-700">
        <p className="text-sm text-slate-400">
          Each % value represents real-time operational efficiency of that orchestration function vs its target SLO.
        </p>
      </div>
    </div>
  );
}
