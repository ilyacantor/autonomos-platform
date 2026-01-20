/**
 * Agent Control Center Page
 *
 * Main page for agentic orchestration:
 * - Agent chat interface
 * - Run history
 * - Approval queue
 * - Agent workbench
 */

import { useState } from 'react';
import {
  Bot,
  MessageSquare,
  Clock,
  Shield,
  Settings,
  LayoutGrid,
  Calendar,
} from 'lucide-react';
import AgentChat from './AgentChat';
import AgentRunHistory from './AgentRunHistory';
import AgentApprovalQueue from './AgentApprovalQueue';
import AgentWorkbench from './AgentWorkbench';
import SchedulerManager from './SchedulerManager';

type TabId = 'chat' | 'history' | 'approvals' | 'scheduler' | 'workbench';

interface Tab {
  id: TabId;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: number;
}

export default function AgentControlCenter() {
  const [activeTab, setActiveTab] = useState<TabId>('chat');
  const [pendingApprovals, setPendingApprovals] = useState(3); // Mock count

  const tabs: Tab[] = [
    { id: 'chat', label: 'Chat', icon: MessageSquare },
    { id: 'history', label: 'Run History', icon: Clock },
    { id: 'approvals', label: 'Approvals', icon: Shield, badge: pendingApprovals },
    { id: 'scheduler', label: 'Scheduler', icon: Calendar },
    { id: 'workbench', label: 'Workbench', icon: Settings },
  ];

  return (
    <div className="space-y-6 px-4 sm:px-6 py-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-pink-500 rounded-xl flex items-center justify-center shadow-lg">
            <Bot className="w-7 h-7 text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-white">Agent Control Center</h1>
            <p className="text-gray-400">
              Interact with AI agents, review actions, and manage configurations
            </p>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="hidden lg:flex items-center gap-6 bg-gray-800/50 rounded-lg px-6 py-3 border border-gray-700">
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-400">1</div>
            <div className="text-xs text-gray-400">Active Agent</div>
          </div>
          <div className="w-px h-8 bg-gray-700" />
          <div className="text-center">
            <div className="text-2xl font-bold text-cyan-400">24</div>
            <div className="text-xs text-gray-400">Runs Today</div>
          </div>
          <div className="w-px h-8 bg-gray-700" />
          <div className="text-center">
            <div className="text-2xl font-bold text-yellow-400">{pendingApprovals}</div>
            <div className="text-xs text-gray-400">Pending</div>
          </div>
          <div className="w-px h-8 bg-gray-700" />
          <div className="text-center">
            <div className="text-2xl font-bold text-green-400">$2.47</div>
            <div className="text-xs text-gray-400">Cost Today</div>
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex items-center gap-2 border-b border-gray-700 pb-4">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === tab.id
                ? 'bg-purple-600 text-white shadow-lg shadow-purple-500/20'
                : 'text-gray-400 hover:text-white hover:bg-gray-800'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
            {tab.badge !== undefined && tab.badge > 0 && (
              <span
                className={`ml-1 px-2 py-0.5 text-xs rounded-full ${
                  activeTab === tab.id
                    ? 'bg-white/20 text-white'
                    : 'bg-yellow-500/20 text-yellow-400'
                }`}
              >
                {tab.badge}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="min-h-[600px]">
        {activeTab === 'chat' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Main Chat */}
            <div className="lg:col-span-2 h-[600px]">
              <AgentChat
                agentId="default"
                agentName="AOS Agent"
                onRunComplete={() => {
                  // Refresh history if needed
                }}
              />
            </div>

            {/* Side Panel */}
            <div className="space-y-6">
              {/* Quick Actions */}
              <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
                <h3 className="text-sm font-medium text-white mb-3">Quick Actions</h3>
                <div className="space-y-2">
                  {[
                    { label: 'Check connector status', icon: LayoutGrid },
                    { label: 'Show recent data changes', icon: Clock },
                    { label: 'Run data quality check', icon: Shield },
                  ].map((action, i) => (
                    <button
                      key={i}
                      className="w-full flex items-center gap-2 px-3 py-2 bg-gray-900/50 hover:bg-gray-900 rounded-lg text-sm text-gray-300 hover:text-white transition-colors text-left"
                    >
                      <action.icon className="w-4 h-4 text-purple-400" />
                      {action.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Recent Runs Mini */}
              <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-medium text-white">Recent Runs</h3>
                  <button
                    onClick={() => setActiveTab('history')}
                    className="text-xs text-purple-400 hover:text-purple-300"
                  >
                    View all
                  </button>
                </div>
                <div className="space-y-2">
                  {[
                    { query: 'Revenue Q4 2025', status: 'completed', time: '2m ago' },
                    { query: 'Create SF connection', status: 'waiting', time: '10m ago' },
                    { query: 'Data lineage trace', status: 'completed', time: '30m ago' },
                  ].map((run, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-2 px-3 py-2 bg-gray-900/50 rounded-lg"
                    >
                      <div
                        className={`w-2 h-2 rounded-full ${
                          run.status === 'completed'
                            ? 'bg-green-400'
                            : run.status === 'waiting'
                            ? 'bg-yellow-400'
                            : 'bg-gray-400'
                        }`}
                      />
                      <span className="flex-1 text-xs text-gray-300 truncate">{run.query}</span>
                      <span className="text-xs text-gray-500">{run.time}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Pending Approvals Mini */}
              {pendingApprovals > 0 && (
                <div className="bg-yellow-900/20 rounded-lg border border-yellow-500/30 p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <Shield className="w-4 h-4 text-yellow-400" />
                    <h3 className="text-sm font-medium text-yellow-400">
                      {pendingApprovals} Pending Approvals
                    </h3>
                  </div>
                  <p className="text-xs text-gray-400 mb-3">
                    Agent actions require your review
                  </p>
                  <button
                    onClick={() => setActiveTab('approvals')}
                    className="w-full px-3 py-2 bg-yellow-600 hover:bg-yellow-700 text-white rounded-lg text-sm font-medium transition-colors"
                  >
                    Review Now
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'history' && <AgentRunHistory />}

        {activeTab === 'approvals' && (
          <AgentApprovalQueue
            onApprovalComplete={() => {
              setPendingApprovals((prev) => Math.max(0, prev - 1));
            }}
          />
        )}

        {activeTab === 'scheduler' && <SchedulerManager />}

        {activeTab === 'workbench' && <AgentWorkbench />}
      </div>

      {/* Footer Info */}
      <div className="text-center text-xs text-gray-500">
        Agent Control Center • Powered by LangGraph + MCP •{' '}
        <a href="#" className="text-purple-400 hover:text-purple-300">
          Documentation
        </a>
      </div>
    </div>
  );
}
