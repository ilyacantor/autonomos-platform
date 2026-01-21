/**
 * Agent Control Center Page
 *
 * Scheduler management for automated agent runs.
 */

import { Calendar } from 'lucide-react';
import SchedulerManager from './SchedulerManager';

export default function AgentControlCenter() {
  return (
    <div className="space-y-6 px-4 sm:px-6 py-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-pink-500 rounded-xl flex items-center justify-center shadow-lg">
          <Calendar className="w-7 h-7 text-white" />
        </div>
        <div>
          <h1 className="text-3xl font-bold text-white">Agent Scheduler</h1>
          <p className="text-gray-400">
            Schedule and manage automated agent runs
          </p>
        </div>
      </div>

      {/* Scheduler Content */}
      <SchedulerManager />
    </div>
  );
}
