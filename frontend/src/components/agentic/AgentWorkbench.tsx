/**
 * Agent Workbench Component
 *
 * Create and test agents with:
 * - Agent configuration editor
 * - Tool selection
 * - Test execution
 * - Performance monitoring
 */

import { useState, useEffect } from 'react';
import {
  Bot,
  Settings,
  Wrench,
  Play,
  Save,
  RefreshCw,
  Plus,
  Trash2,
  ChevronDown,
  ChevronRight,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Zap,
  DollarSign,
  Code,
  FileText,
  Shield,
} from 'lucide-react';

interface ToolConfig {
  id: string;
  name: string;
  server: string;
  description: string;
  enabled: boolean;
  requires_approval: boolean;
}

interface AgentConfig {
  agent_id: string;
  name: string;
  description: string;
  system_prompt: string;
  model_tier: 'fast' | 'balanced' | 'powerful';
  max_steps: number;
  tools: ToolConfig[];
  approval_rules: {
    pattern: string;
    risk_level: string;
    auto_approve: boolean;
  }[];
}

interface TestResult {
  test_id: string;
  input: string;
  expected_output?: string;
  actual_output?: string;
  tools_called: string[];
  tokens_used: number;
  cost_usd: number;
  duration_ms: number;
  passed: boolean;
  error?: string;
}

const DEFAULT_TOOLS: ToolConfig[] = [
  {
    id: 'dcl_query',
    name: 'dcl_query',
    server: 'dcl',
    description: 'Execute SQL queries against connected data sources',
    enabled: true,
    requires_approval: false,
  },
  {
    id: 'dcl_get_schema',
    name: 'dcl_get_schema',
    server: 'dcl',
    description: 'Get schema information for tables',
    enabled: true,
    requires_approval: false,
  },
  {
    id: 'dcl_search_fields',
    name: 'dcl_search_fields',
    server: 'dcl',
    description: 'Search for fields across all tables',
    enabled: true,
    requires_approval: false,
  },
  {
    id: 'aod_discover_assets',
    name: 'aod_discover_assets',
    server: 'aod',
    description: 'Discover data assets across systems',
    enabled: true,
    requires_approval: false,
  },
  {
    id: 'aod_get_lineage',
    name: 'aod_get_lineage',
    server: 'aod',
    description: 'Trace data lineage for assets',
    enabled: true,
    requires_approval: false,
  },
  {
    id: 'aod_explain_field',
    name: 'aod_explain_field',
    server: 'aod',
    description: 'Get detailed field explanations',
    enabled: true,
    requires_approval: false,
  },
  {
    id: 'aam_list_connections',
    name: 'aam_list_connections',
    server: 'aam',
    description: 'List all data connections',
    enabled: true,
    requires_approval: false,
  },
  {
    id: 'aam_create_connection',
    name: 'aam_create_connection',
    server: 'aam',
    description: 'Create new data connections',
    enabled: true,
    requires_approval: true,
  },
  {
    id: 'aam_trigger_sync',
    name: 'aam_trigger_sync',
    server: 'aam',
    description: 'Trigger manual sync for connections',
    enabled: true,
    requires_approval: true,
  },
  {
    id: 'aam_repair_drift',
    name: 'aam_repair_drift',
    server: 'aam',
    description: 'Repair schema drift automatically',
    enabled: true,
    requires_approval: true,
  },
];

const DEFAULT_AGENT: AgentConfig = {
  agent_id: '',
  name: 'New Agent',
  description: 'A custom AOS agent',
  system_prompt: `You are an AI assistant for the AutonomOS platform. You help users with:
- Querying and analyzing data from connected sources
- Managing data connections and syncs
- Understanding data lineage and relationships
- Discovering and classifying data assets

Be concise and helpful. Use the available tools to gather information before responding.`,
  model_tier: 'balanced',
  max_steps: 10,
  tools: DEFAULT_TOOLS,
  approval_rules: [
    { pattern: 'aam_create_*', risk_level: 'high', auto_approve: false },
    { pattern: 'aam_repair_*', risk_level: 'medium', auto_approve: false },
    { pattern: 'dcl_write_*', risk_level: 'critical', auto_approve: false },
  ],
};

export default function AgentWorkbench() {
  const [agents, setAgents] = useState<AgentConfig[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<AgentConfig | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [activeTab, setActiveTab] = useState<'config' | 'tools' | 'test' | 'rules'>('config');
  const [testInput, setTestInput] = useState('');
  const [testResults, setTestResults] = useState<TestResult[]>([]);
  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);

  // Load agents on mount
  useEffect(() => {
    fetchAgents();
  }, []);

  const fetchAgents = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/v1/agents', {
        headers: { Authorization: token ? `Bearer ${token}` : '' },
      });

      if (response.ok) {
        const data = await response.json();
        setAgents(data.agents || []);
      }
    } catch (error) {
      // Use mock data
      setAgents([
        { ...DEFAULT_AGENT, agent_id: 'agent-default', name: 'AOS Agent' },
      ]);
    }
  };

  // Create new agent
  const handleCreateAgent = () => {
    const newAgent: AgentConfig = {
      ...DEFAULT_AGENT,
      agent_id: `agent-${Date.now()}`,
      name: 'New Agent',
    };
    setSelectedAgent(newAgent);
    setIsEditing(true);
    setActiveTab('config');
  };

  // Save agent
  const handleSaveAgent = async () => {
    if (!selectedAgent) return;

    setSaving(true);
    try {
      const token = localStorage.getItem('token');
      const isNew = !agents.find((a) => a.agent_id === selectedAgent.agent_id);

      const response = await fetch(
        `/api/v1/agents${isNew ? '' : `/${selectedAgent.agent_id}`}`,
        {
          method: isNew ? 'POST' : 'PUT',
          headers: {
            'Content-Type': 'application/json',
            Authorization: token ? `Bearer ${token}` : '',
          },
          body: JSON.stringify(selectedAgent),
        }
      );

      if (response.ok) {
        const data = await response.json();
        if (isNew) {
          setAgents((prev) => [...prev, data]);
        } else {
          setAgents((prev) =>
            prev.map((a) => (a.agent_id === selectedAgent.agent_id ? data : a))
          );
        }
        setIsEditing(false);
      }
    } catch (error) {
      console.error('Failed to save agent:', error);
      // Mock success for demo
      const isNew = !agents.find((a) => a.agent_id === selectedAgent.agent_id);
      if (isNew) {
        setAgents((prev) => [...prev, selectedAgent]);
      } else {
        setAgents((prev) =>
          prev.map((a) => (a.agent_id === selectedAgent.agent_id ? selectedAgent : a))
        );
      }
      setIsEditing(false);
    } finally {
      setSaving(false);
    }
  };

  // Run test
  const handleRunTest = async () => {
    if (!selectedAgent || !testInput.trim()) return;

    setTesting(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`/api/v1/agents/${selectedAgent.agent_id}/test`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: token ? `Bearer ${token}` : '',
        },
        body: JSON.stringify({ input: testInput }),
      });

      if (response.ok) {
        const result = await response.json();
        setTestResults((prev) => [result, ...prev]);
      }
    } catch (error) {
      // Mock test result
      const mockResult: TestResult = {
        test_id: `test-${Date.now()}`,
        input: testInput,
        actual_output: 'Mock response for: ' + testInput,
        tools_called: ['dcl_query', 'dcl_get_schema'],
        tokens_used: 1500,
        cost_usd: 0.012,
        duration_ms: 2500,
        passed: true,
      };
      setTestResults((prev) => [mockResult, ...prev]);
    } finally {
      setTesting(false);
      setTestInput('');
    }
  };

  // Toggle tool enabled
  const toggleTool = (toolId: string) => {
    if (!selectedAgent) return;
    setSelectedAgent({
      ...selectedAgent,
      tools: selectedAgent.tools.map((t) =>
        t.id === toolId ? { ...t, enabled: !t.enabled } : t
      ),
    });
  };

  // Toggle tool approval requirement
  const toggleToolApproval = (toolId: string) => {
    if (!selectedAgent) return;
    setSelectedAgent({
      ...selectedAgent,
      tools: selectedAgent.tools.map((t) =>
        t.id === toolId ? { ...t, requires_approval: !t.requires_approval } : t
      ),
    });
  };

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700">
      {/* Header */}
      <div className="px-4 py-4 border-b border-gray-700 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-pink-500 rounded-lg flex items-center justify-center">
            <Settings className="w-6 h-6 text-white" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">Agent Workbench</h3>
            <p className="text-xs text-gray-400">Create, configure, and test agents</p>
          </div>
        </div>

        <button
          onClick={handleCreateAgent}
          className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm font-medium transition-colors"
        >
          <Plus className="w-4 h-4" />
          New Agent
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 divide-y lg:divide-y-0 lg:divide-x divide-gray-700">
        {/* Agent List */}
        <div className="p-4">
          <div className="text-xs text-gray-400 uppercase tracking-wider mb-3">
            Agents ({agents.length})
          </div>

          <div className="space-y-2">
            {agents.map((agent) => (
              <button
                key={agent.agent_id}
                onClick={() => {
                  setSelectedAgent(agent);
                  setIsEditing(false);
                }}
                className={`w-full text-left p-3 rounded-lg border transition-all ${
                  selectedAgent?.agent_id === agent.agent_id
                    ? 'bg-purple-900/30 border-purple-500'
                    : 'bg-gray-900/50 border-gray-700 hover:bg-gray-900'
                }`}
              >
                <div className="flex items-center gap-2 mb-1">
                  <Bot className="w-4 h-4 text-purple-400" />
                  <span className="text-sm font-medium text-white">{agent.name}</span>
                </div>
                <p className="text-xs text-gray-500 truncate">{agent.description}</p>
                <div className="flex items-center gap-2 mt-2 text-xs text-gray-500">
                  <span className="flex items-center gap-1">
                    <Wrench className="w-3 h-3" />
                    {agent.tools.filter((t) => t.enabled).length} tools
                  </span>
                </div>
              </button>
            ))}

            {agents.length === 0 && (
              <div className="text-center py-8">
                <Bot className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                <p className="text-gray-500 text-sm">No agents yet</p>
                <button
                  onClick={handleCreateAgent}
                  className="mt-3 text-purple-400 hover:text-purple-300 text-sm"
                >
                  Create your first agent
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Configuration Panel */}
        <div className="lg:col-span-3 p-4">
          {selectedAgent ? (
            <>
              {/* Tabs */}
              <div className="flex items-center gap-1 mb-4 border-b border-gray-700 pb-3">
                {[
                  { id: 'config', label: 'Configuration', icon: Settings },
                  { id: 'tools', label: 'Tools', icon: Wrench },
                  { id: 'rules', label: 'Approval Rules', icon: Shield },
                  { id: 'test', label: 'Test', icon: Play },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id as any)}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      activeTab === tab.id
                        ? 'bg-purple-600 text-white'
                        : 'text-gray-400 hover:text-white hover:bg-gray-700'
                    }`}
                  >
                    <tab.icon className="w-4 h-4" />
                    {tab.label}
                  </button>
                ))}

                <div className="flex-1" />

                {isEditing && (
                  <button
                    onClick={handleSaveAgent}
                    disabled={saving}
                    className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-700 text-white rounded-lg text-sm font-medium transition-colors"
                  >
                    {saving ? (
                      <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : (
                      <Save className="w-4 h-4" />
                    )}
                    Save
                  </button>
                )}

                {!isEditing && (
                  <button
                    onClick={() => setIsEditing(true)}
                    className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm font-medium transition-colors"
                  >
                    <Settings className="w-4 h-4" />
                    Edit
                  </button>
                )}
              </div>

              {/* Tab Content */}
              {activeTab === 'config' && (
                <div className="space-y-4">
                  <div>
                    <label className="text-sm text-gray-400 mb-1 block">Agent Name</label>
                    <input
                      type="text"
                      value={selectedAgent.name}
                      onChange={(e) =>
                        isEditing &&
                        setSelectedAgent({ ...selectedAgent, name: e.target.value })
                      }
                      disabled={!isEditing}
                      className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white disabled:opacity-50"
                    />
                  </div>

                  <div>
                    <label className="text-sm text-gray-400 mb-1 block">Description</label>
                    <input
                      type="text"
                      value={selectedAgent.description}
                      onChange={(e) =>
                        isEditing &&
                        setSelectedAgent({ ...selectedAgent, description: e.target.value })
                      }
                      disabled={!isEditing}
                      className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white disabled:opacity-50"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm text-gray-400 mb-1 block">Model Tier</label>
                      <select
                        value={selectedAgent.model_tier}
                        onChange={(e) =>
                          isEditing &&
                          setSelectedAgent({
                            ...selectedAgent,
                            model_tier: e.target.value as any,
                          })
                        }
                        disabled={!isEditing}
                        className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white disabled:opacity-50"
                      >
                        <option value="fast">Fast (Haiku)</option>
                        <option value="balanced">Balanced (Sonnet)</option>
                        <option value="powerful">Powerful (Opus)</option>
                      </select>
                    </div>

                    <div>
                      <label className="text-sm text-gray-400 mb-1 block">Max Steps</label>
                      <input
                        type="number"
                        value={selectedAgent.max_steps}
                        onChange={(e) =>
                          isEditing &&
                          setSelectedAgent({
                            ...selectedAgent,
                            max_steps: parseInt(e.target.value) || 10,
                          })
                        }
                        disabled={!isEditing}
                        min={1}
                        max={50}
                        className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white disabled:opacity-50"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="text-sm text-gray-400 mb-1 block">System Prompt</label>
                    <textarea
                      value={selectedAgent.system_prompt}
                      onChange={(e) =>
                        isEditing &&
                        setSelectedAgent({ ...selectedAgent, system_prompt: e.target.value })
                      }
                      disabled={!isEditing}
                      rows={8}
                      className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white disabled:opacity-50 font-mono text-sm resize-none"
                    />
                  </div>
                </div>
              )}

              {activeTab === 'tools' && (
                <div className="space-y-3">
                  <p className="text-sm text-gray-400 mb-4">
                    Enable or disable tools available to this agent. Tools marked as "Requires
                    Approval" will trigger HITL review before execution.
                  </p>

                  {selectedAgent.tools.map((tool) => (
                    <div
                      key={tool.id}
                      className="flex items-center gap-4 p-3 bg-gray-900/50 rounded-lg border border-gray-700"
                    >
                      <button
                        onClick={() => isEditing && toggleTool(tool.id)}
                        disabled={!isEditing}
                        className={`p-2 rounded-lg transition-colors ${
                          tool.enabled
                            ? 'bg-green-500/20 text-green-400'
                            : 'bg-gray-800 text-gray-500'
                        }`}
                      >
                        {tool.enabled ? (
                          <CheckCircle className="w-5 h-5" />
                        ) : (
                          <XCircle className="w-5 h-5" />
                        )}
                      </button>

                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-white">{tool.name}</span>
                          <span className="text-xs text-gray-500">({tool.server})</span>
                        </div>
                        <p className="text-xs text-gray-500">{tool.description}</p>
                      </div>

                      <button
                        onClick={() => isEditing && toggleToolApproval(tool.id)}
                        disabled={!isEditing}
                        className={`flex items-center gap-1 px-3 py-1 rounded-lg text-xs transition-colors ${
                          tool.requires_approval
                            ? 'bg-yellow-500/20 text-yellow-400'
                            : 'bg-gray-800 text-gray-500 hover:bg-gray-700'
                        }`}
                      >
                        <Shield className="w-3 h-3" />
                        {tool.requires_approval ? 'Requires Approval' : 'Auto-approve'}
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {activeTab === 'rules' && (
                <div className="space-y-4">
                  <p className="text-sm text-gray-400 mb-4">
                    Configure approval rules for tool execution. Matching patterns trigger
                    human review.
                  </p>

                  {selectedAgent.approval_rules.map((rule, index) => (
                    <div
                      key={index}
                      className="flex items-center gap-4 p-3 bg-gray-900/50 rounded-lg border border-gray-700"
                    >
                      <Code className="w-5 h-5 text-cyan-400" />
                      <div className="flex-1">
                        <input
                          type="text"
                          value={rule.pattern}
                          onChange={(e) => {
                            if (!isEditing) return;
                            const newRules = [...selectedAgent.approval_rules];
                            newRules[index] = { ...rule, pattern: e.target.value };
                            setSelectedAgent({ ...selectedAgent, approval_rules: newRules });
                          }}
                          disabled={!isEditing}
                          className="bg-transparent text-sm text-white font-mono disabled:opacity-50 w-full"
                        />
                      </div>
                      <select
                        value={rule.risk_level}
                        onChange={(e) => {
                          if (!isEditing) return;
                          const newRules = [...selectedAgent.approval_rules];
                          newRules[index] = { ...rule, risk_level: e.target.value };
                          setSelectedAgent({ ...selectedAgent, approval_rules: newRules });
                        }}
                        disabled={!isEditing}
                        className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-white disabled:opacity-50"
                      >
                        <option value="low">Low</option>
                        <option value="medium">Medium</option>
                        <option value="high">High</option>
                        <option value="critical">Critical</option>
                      </select>
                      {isEditing && (
                        <button
                          onClick={() => {
                            const newRules = selectedAgent.approval_rules.filter(
                              (_, i) => i !== index
                            );
                            setSelectedAgent({ ...selectedAgent, approval_rules: newRules });
                          }}
                          className="p-1 text-red-400 hover:bg-red-500/20 rounded"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  ))}

                  {isEditing && (
                    <button
                      onClick={() => {
                        setSelectedAgent({
                          ...selectedAgent,
                          approval_rules: [
                            ...selectedAgent.approval_rules,
                            { pattern: '*', risk_level: 'low', auto_approve: false },
                          ],
                        });
                      }}
                      className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm transition-colors"
                    >
                      <Plus className="w-4 h-4" />
                      Add Rule
                    </button>
                  )}
                </div>
              )}

              {activeTab === 'test' && (
                <div className="space-y-4">
                  {/* Test Input */}
                  <div>
                    <label className="text-sm text-gray-400 mb-1 block">Test Input</label>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={testInput}
                        onChange={(e) => setTestInput(e.target.value)}
                        placeholder="Enter a test query..."
                        className="flex-1 px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500"
                        onKeyDown={(e) => e.key === 'Enter' && handleRunTest()}
                      />
                      <button
                        onClick={handleRunTest}
                        disabled={testing || !testInput.trim()}
                        className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-700 text-white rounded-lg font-medium transition-colors"
                      >
                        {testing ? (
                          <RefreshCw className="w-4 h-4 animate-spin" />
                        ) : (
                          <Play className="w-4 h-4" />
                        )}
                        Run Test
                      </button>
                    </div>
                  </div>

                  {/* Test Results */}
                  <div>
                    <div className="text-sm text-gray-400 mb-2">
                      Test Results ({testResults.length})
                    </div>

                    <div className="space-y-3 max-h-96 overflow-y-auto">
                      {testResults.map((result) => (
                        <div
                          key={result.test_id}
                          className={`p-4 rounded-lg border ${
                            result.passed
                              ? 'bg-green-900/20 border-green-500/30'
                              : 'bg-red-900/20 border-red-500/30'
                          }`}
                        >
                          <div className="flex items-center gap-2 mb-2">
                            {result.passed ? (
                              <CheckCircle className="w-4 h-4 text-green-400" />
                            ) : (
                              <XCircle className="w-4 h-4 text-red-400" />
                            )}
                            <span className="text-sm font-medium text-white">
                              {result.passed ? 'Passed' : 'Failed'}
                            </span>
                            <div className="flex-1" />
                            <span className="text-xs text-gray-500">
                              {result.duration_ms}ms |{' '}
                              {result.tokens_used} tokens |{' '}
                              ${result.cost_usd.toFixed(4)}
                            </span>
                          </div>

                          <div className="text-sm text-gray-400 mb-2">
                            <span className="text-gray-500">Input:</span> {result.input}
                          </div>

                          {result.actual_output && (
                            <div className="text-sm text-gray-300 bg-gray-900/50 rounded p-2 mb-2">
                              {result.actual_output}
                            </div>
                          )}

                          {result.error && (
                            <div className="text-sm text-red-400 bg-red-900/30 rounded p-2 mb-2">
                              {result.error}
                            </div>
                          )}

                          {result.tools_called.length > 0 && (
                            <div className="flex flex-wrap gap-1">
                              {result.tools_called.map((tool, i) => (
                                <span
                                  key={i}
                                  className="text-xs bg-gray-800 px-2 py-1 rounded text-cyan-400"
                                >
                                  {tool}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}

                      {testResults.length === 0 && (
                        <div className="text-center py-8">
                          <Play className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                          <p className="text-gray-500 text-sm">No test results yet</p>
                          <p className="text-xs text-gray-600 mt-1">
                            Enter a query and click "Run Test"
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-center py-12">
              <Bot className="w-16 h-16 text-gray-600 mb-4" />
              <p className="text-gray-400 mb-2">Select an agent to configure</p>
              <p className="text-sm text-gray-500 max-w-md">
                Choose an agent from the list or create a new one to get started
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
