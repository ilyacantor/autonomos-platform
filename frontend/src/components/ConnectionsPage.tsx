import { useState, useEffect } from 'react';
import { Database, Server, Warehouse, Users, Settings2, Activity, Search } from 'lucide-react';
import { DEFAULT_SOURCES, DEFAULT_AGENTS, getDefaultSources, getDefaultAgents } from '../config/dclDefaults';

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
  const [lineageSearchQuery, setLineageSearchQuery] = useState('');

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


  const handleSelectAll = () => {
    setSelectedSources(connections.map(c => c.value));
    setSelectedAgents(agents.map(a => a.value));
  };

  const handleLineageSearch = () => {
    if (lineageSearchQuery.trim()) {
      // Navigate to Data Lineage page with search query
      window.location.hash = '#/data-lineage';
      // Store search query for the lineage page to pick up
      sessionStorage.setItem('lineageSearchQuery', lineageSearchQuery);
    }
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

          {/* Data Lineage Search */}
          <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-3 sm:p-4">
            <h3 className="text-base sm:text-lg font-semibold text-white mb-3 sm:mb-4 flex items-center gap-2">
              <Search className="w-5 h-5 text-orange-400" />
              Trace Data Lineage
            </h3>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input
                type="text"
                placeholder="Search for KPI, Report, or Unified Entity..."
                value={lineageSearchQuery}
                onChange={(e) => setLineageSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleLineageSearch()}
                className="w-full bg-gray-900 text-gray-200 pl-10 pr-3 py-3 rounded-lg border border-gray-700 focus:outline-none focus:border-orange-500 transition-colors text-sm"
              />
            </div>
            <button
              onClick={handleLineageSearch}
              disabled={!lineageSearchQuery.trim()}
              className="mt-3 w-full px-4 py-2.5 bg-orange-600 hover:bg-orange-700 disabled:bg-gray-700 disabled:text-gray-500 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors text-sm"
            >
              Trace Lineage
            </button>
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


        </div>
      </div>
    </div>
  );
}
