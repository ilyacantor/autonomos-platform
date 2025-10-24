import { useState, useEffect } from 'react';
import { Database, Server, Warehouse, Users, Settings2, Play, Activity, CheckCircle, Loader2, AlertCircle } from 'lucide-react';
import { useDCLState } from '../hooks/useDCLState';
import { API_CONFIG } from '../config/api';
import { DEFAULT_SOURCES, DEFAULT_AGENTS, getDefaultSources, getDefaultAgents, type DCLSource as Connection, type DCLAgent as Agent } from '../config/dclDefaults';

const connections = DEFAULT_SOURCES;
const agents = DEFAULT_AGENTS;

function getIcon(type: string) {
  switch (type) {
    case 'CRM':
      return <Users className="w-5 h-5 text-blue-400" />;
    case 'ERP':
      return <Settings2 className="w-5 h-5 text-green-400" />;
    case 'Database':
      return <Database className="w-5 h-5 text-red-400" />;
    case 'Warehouse':
      return <Warehouse className="w-5 h-5 text-cyan-400" />;
    default:
      return <Server className="w-5 h-5 text-gray-400" />;
  }
}

function getTypeColor(type: string) {
  switch (type) {
    case 'CRM':
      return 'bg-blue-900/30 border-blue-700/50';
    case 'ERP':
      return 'bg-green-900/30 border-green-700/50';
    case 'Database':
      return 'bg-red-900/30 border-red-700/50';
    case 'Warehouse':
      return 'bg-cyan-900/30 border-cyan-700/50';
    default:
      return 'bg-gray-900/30 border-gray-700/50';
  }
}

export default function ConnectionsPage() {
  const [selectedSources, setSelectedSources] = useState<string[]>([]);
  const [selectedAgents, setSelectedAgents] = useState<string[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progressStatus, setProgressStatus] = useState<'idle' | 'connecting' | 'completed'>('idle');
  const { state: dclState } = useDCLState();

  // Load selections from localStorage on mount (with defaults if empty)
  useEffect(() => {
    setSelectedSources(getDefaultSources());
    setSelectedAgents(getDefaultAgents());
  }, []);

  // Save selections to localStorage whenever they change
  useEffect(() => {
    if (selectedSources.length > 0) {
      localStorage.setItem('aos.selectedSources', JSON.stringify(selectedSources));
    }
  }, [selectedSources]);

  useEffect(() => {
    if (selectedAgents.length > 0) {
      localStorage.setItem('aos.selectedAgents', JSON.stringify(selectedAgents));
    }
  }, [selectedAgents]);

  // Update progress status based on DCL state
  useEffect(() => {
    if (isProcessing) {
      setProgressStatus('connecting');
    } else if (dclState?.selected_sources && dclState.selected_sources.length > 0) {
      setProgressStatus('completed');
    } else {
      setProgressStatus('idle');
    }
  }, [isProcessing, dclState?.selected_sources]);

  const toggleSource = (value: string) => {
    setSelectedSources(prev =>
      prev.includes(value)
        ? prev.filter(v => v !== value)
        : [...prev, value]
    );
  };

  const toggleAgent = (value: string) => {
    setSelectedAgents(prev =>
      prev.includes(value)
        ? prev.filter(v => v !== value)
        : [...prev, value]
    );
  };

  const handleConnect = async () => {
    if (selectedSources.length === 0) {
      alert('Please select at least one data source');
      return;
    }
    if (selectedAgents.length === 0) {
      alert('Please select at least one agent');
      return;
    }

    setIsProcessing(true);
    try {
      const sourcesParam = selectedSources.join(',');
      const agentsParam = selectedAgents.join(',');
      
      const response = await fetch(
        API_CONFIG.buildDclUrl(`/connect?sources=${sourcesParam}&agents=${agentsParam}`)
      );
      
      if (!response.ok) {
        throw new Error(`Connection failed: ${response.statusText}`);
      }
      
      // Notify state change
      window.dispatchEvent(new Event('dcl-state-changed'));
      
      // Trigger Dashboard auto-run with progress bar
      window.dispatchEvent(new CustomEvent('dcl:trigger-run', { 
        detail: { source: 'connections' } 
      }));
    } catch (error) {
      console.error('Error connecting:', error);
      alert('Connection failed. Please try again.');
    } finally {
      setTimeout(() => setIsProcessing(false), 1500);
    }
  };

  const handleSelectAll = () => {
    setSelectedSources(connections.map(c => c.value));
    setSelectedAgents(agents.map(a => a.value));
  };

  return (
    <div className="space-y-4 sm:space-y-6">
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold text-white mb-2">Data Connection Layer (DCL)</h1>
        <p className="text-sm sm:text-base text-gray-400">
          Select data sources and agents to create unified entity mappings
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
        {/* Left Column: Data Sources */}
        <div className="space-y-4 sm:space-y-6">
          <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-3 sm:p-4">
            <h3 className="text-base sm:text-lg font-semibold text-white mb-3 sm:mb-4 flex items-center gap-2">
              <Database className="w-5 h-5 text-blue-400" />
              Data Sources ({selectedSources.length}/{connections.length})
            </h3>
            <div className="space-y-2 max-h-[600px] overflow-y-auto">
              {connections.map((connection) => (
                <label
                  key={connection.id}
                  className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-all min-h-[44px] active:opacity-80 ${
                    selectedSources.includes(connection.value)
                      ? 'bg-blue-900/40 border-blue-500/50 ring-1 ring-blue-500/30'
                      : `${getTypeColor(connection.type)} hover:border-gray-600`
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedSources.includes(connection.value)}
                    onChange={() => toggleSource(connection.value)}
                    className="mt-1 w-5 h-5 rounded border-gray-600 text-blue-500 focus:ring-blue-500 focus:ring-offset-gray-900"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      {getIcon(connection.type)}
                      <span className="font-semibold text-white text-sm">{connection.name}</span>
                    </div>
                    <p className="text-xs text-gray-400 truncate">{connection.description}</p>
                  </div>
                </label>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column: Agents, Actions, Progress, Status */}
        <div className="space-y-4 sm:space-y-6">
          {/* Select All Button */}
          <button
            onClick={handleSelectAll}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 min-h-[44px] bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 active:from-blue-800 active:to-purple-800 text-white font-semibold rounded-lg shadow-lg shadow-blue-500/30 transition-all"
          >
            <Database className="w-4 h-4" />
            <span className="text-sm sm:text-base">Select All Sources & Agents</span>
          </button>

          {/* Agents Selection */}
          <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-3 sm:p-4">
            <h3 className="text-base sm:text-lg font-semibold text-white mb-3 sm:mb-4 flex items-center gap-2">
              <Activity className="w-5 h-5 text-purple-400" />
              Intelligence Agents ({selectedAgents.length}/{agents.length})
            </h3>
            <div className="space-y-2">
              {agents.map((agent) => (
                <label
                  key={agent.id}
                  className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-all min-h-[44px] active:opacity-80 ${
                    selectedAgents.includes(agent.value)
                      ? 'bg-purple-900/40 border-purple-500/50 ring-1 ring-purple-500/30'
                      : 'bg-gray-900/30 border-gray-700/50 hover:border-gray-600'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedAgents.includes(agent.value)}
                    onChange={() => toggleAgent(agent.value)}
                    className="mt-1 w-5 h-5 rounded border-gray-600 text-purple-500 focus:ring-purple-500 focus:ring-offset-gray-900"
                  />
                  <div className="flex-1 min-w-0">
                    <span className="font-semibold text-white text-sm block mb-1">{agent.name}</span>
                    <p className="text-xs text-gray-400">{agent.description}</p>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Action Buttons */}
          <div className="space-y-3">
            <button
              onClick={handleConnect}
              disabled={isProcessing || selectedSources.length === 0 || selectedAgents.length === 0}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white font-semibold rounded-lg shadow-lg shadow-emerald-500/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isProcessing ? (
                <>
                  <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Processing...
                </>
              ) : (
                <>
                  <Play className="w-5 h-5" />
                  Connect Sources
                </>
              )}
            </button>
          </div>

          {/* Progress Container */}
          <div className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 border border-gray-700 rounded-lg p-4">
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Activity className="w-5 h-5 text-orange-400" />
              Connection Progress
            </h3>

            {progressStatus === 'idle' && (
              <div className="text-center py-6">
                <div className="w-16 h-16 mx-auto mb-3 rounded-full bg-gray-700/50 flex items-center justify-center">
                  <Database className="w-8 h-8 text-gray-500" />
                </div>
                <p className="text-gray-400 text-sm">
                  Select sources and click Connect to begin
                </p>
              </div>
            )}

            {progressStatus === 'connecting' && (
              <div className="space-y-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-400">Connecting sources...</span>
                  <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2 overflow-hidden">
                  <div className="bg-gradient-to-r from-blue-500 to-purple-500 h-full animate-pulse" style={{ width: '60%' }} />
                </div>
                <p className="text-xs text-gray-500 text-center mt-2">
                  Processing mappings and creating unified views...
                </p>
              </div>
            )}

            {progressStatus === 'completed' && dclState && (
              <div className="space-y-3">
                {/* Overall Stats */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-blue-900/30 border border-blue-500/30 rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <Database className="w-4 h-4 text-blue-400" />
                      <span className="text-xs text-gray-400">Sources</span>
                    </div>
                    <div className="text-xl font-bold text-blue-400">
                      {dclState.selected_sources?.length || 0}
                    </div>
                  </div>
                  <div className="bg-purple-900/30 border border-purple-500/30 rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <Activity className="w-4 h-4 text-purple-400" />
                      <span className="text-xs text-gray-400">Agents</span>
                    </div>
                    <div className="text-xl font-bold text-purple-400">
                      {dclState.selected_agents?.length || 0}
                    </div>
                  </div>
                </div>

                {/* Confidence Score */}
                {dclState.graph?.confidence !== null && dclState.graph?.confidence !== undefined && (
                  <div className="bg-green-900/20 border border-green-500/30 rounded-lg p-3">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm text-gray-400">Mapping Confidence</span>
                      <span className="text-lg font-bold text-green-400">
                        {Math.round((dclState.graph.confidence || 0) * 100)}%
                      </span>
                    </div>
                    <div className="w-full bg-gray-700 rounded-full h-2 overflow-hidden">
                      <div 
                        className="bg-gradient-to-r from-green-500 to-emerald-400 h-full transition-all duration-500"
                        style={{ width: `${Math.round((dclState.graph.confidence || 0) * 100)}%` }}
                      />
                    </div>
                  </div>
                )}

                {/* Connected Sources List */}
                <div className="mt-3">
                  <div className="text-xs text-gray-400 mb-2 font-semibold">Connected Sources:</div>
                  <div className="space-y-1 max-h-32 overflow-y-auto">
                    {dclState.selected_sources?.map((source: string) => {
                      const connection = connections.find(c => c.value === source);
                      return (
                        <div key={source} className="flex items-center gap-2 text-xs text-gray-300 bg-gray-800/50 rounded px-2 py-1.5">
                          <CheckCircle className="w-3 h-3 text-green-400 flex-shrink-0" />
                          <span className="flex-1">{connection?.name || source}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Last Update Time */}
                {dclState.graph?.last_updated && (
                  <div className="text-xs text-gray-500 text-center pt-2 border-t border-gray-700">
                    Last updated: {dclState.graph.last_updated}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Status Info */}
          {dclState && (
            <div className="bg-blue-900/20 border border-blue-500/30 rounded-lg p-4">
              <div className="text-sm space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-gray-400">Connected Sources:</span>
                  <span className="text-blue-400 font-semibold">{dclState.selected_sources?.length || 0}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-400">Active Agents:</span>
                  <span className="text-purple-400 font-semibold">{dclState.selected_agents?.length || 0}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-400">Mode:</span>
                  <span className={`font-semibold ${dclState.dev_mode ? 'text-purple-400' : 'text-gray-400'}`}>
                    {dclState.dev_mode ? 'Dev (AI)' : 'Prod'}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
