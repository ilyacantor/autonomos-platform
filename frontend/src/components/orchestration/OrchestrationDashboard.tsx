/**
 * Orchestration Dashboard Page
 *
 * Main dashboard for Agentic Orchestration featuring:
 * - AOA Status Card (real-time vitals)
 * - AOA Functions Panel (10 core function metrics)
 * - Agent Performance Monitor (per-agent metrics)
 * - Autonomy Mode Toggle (global control)
 *
 * All data is fetched from real API endpoints and updated via polling.
 */

import { Activity } from 'lucide-react';
import AOAStatusCard from './AOAStatusCard';
import AOAFunctionsPanel from './AOAFunctionsPanel';
import AgentPerformanceMonitor from './AgentPerformanceMonitor';
import AutonomyModeToggle from './AutonomyModeToggle';

export default function OrchestrationDashboard() {
  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-xl flex items-center justify-center shadow-lg shadow-cyan-500/20">
            <Activity className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Agentic Orchestration</h1>
            <p className="text-gray-400 text-sm">
              Real-time monitoring and control of autonomous agent operations
            </p>
          </div>
        </div>

        <AutonomyModeToggle />
      </div>

      {/* AOA Status Card - Full Width */}
      <AOAStatusCard />

      {/* AOA Functions Panel - Full Width */}
      <AOAFunctionsPanel />

      {/* Agent Performance Monitor - Full Width */}
      <AgentPerformanceMonitor />

      {/* Footer Note */}
      <div className="text-center py-4 text-xs text-slate-500">
        Dashboard data refreshes automatically. All metrics are derived from real agent execution data.
      </div>
    </div>
  );
}
