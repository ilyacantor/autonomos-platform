import { useState, useEffect } from 'react';
import { 
  Activity, 
  GitMerge,
  ChevronDown,
  ChevronRight,
  Database,
  AlertTriangle,
  Network,
  Zap,
  Brain,
  Shield,
  GitBranch,
  MonitorDot
} from 'lucide-react';
import { API_CONFIG, AUTH_TOKEN_KEY } from '../config/api';
import { useAuth } from '../hooks/useAuth';
import FlowMonitor from './FlowMonitor';

interface Connector {
  id: string;
  name: string;
  source_type: string;
  status: string;
  mapping_count: number;
  has_drift: boolean;
  last_event_type: string | null;
  last_event_at: string | null;
  last_sync_status: string | null;
  last_sync_records: number | null;
  last_sync_bytes: number | null;
  last_sync_at: string | null;
}

type SubTab = 'connectors' | 'flow-monitor';

export default function ConnectPage() {
  const { isAuthenticated } = useAuth();
  const [activeSubTab, setActiveSubTab] = useState<SubTab>('connectors');
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [loading, setLoading] = useState(false);
  const [expandedConnector, setExpandedConnector] = useState<string | null>(null);
  
  const [meshMetrics, setMeshMetrics] = useState({
    activeConnections: 287,
    healingEvents: 12,
    driftAlerts: 3,
    llmCalls: 1234,
    llmTokens: 2100000,
    ragMappings: 14876
  });

  useEffect(() => {
    const interval = setInterval(() => {
      setMeshMetrics(prev => ({
        activeConnections: prev.activeConnections + Math.floor(Math.random() * 3) - 1,
        healingEvents: Math.max(0, prev.healingEvents + Math.floor(Math.random() * 3) - 1),
        driftAlerts: Math.max(0, prev.driftAlerts + Math.floor(Math.random() * 2) - 0.5),
        llmCalls: prev.llmCalls + Math.floor(Math.random() * 5),
        llmTokens: prev.llmTokens + Math.floor(Math.random() * 1000),
        ragMappings: prev.ragMappings + Math.floor(Math.random() * 10)
      }));
    }, 3000);
    
    return () => clearInterval(interval);
  }, []);

  const getAuthHeaders = (): HeadersInit => {
    const token = localStorage.getItem(AUTH_TOKEN_KEY);
    if (token) {
      return { 'Authorization': `Bearer ${token}` };
    }
    return {};
  };

  const fetchConnectors = async () => {
    setLoading(true);
    try {
      const response = await fetch(API_CONFIG.buildApiUrl('/aam/connectors'), {
        headers: getAuthHeaders()
      });
      
      if (response.status === 401) {
        console.log('No tenant context — sign in or select tenant.');
        setConnectors([]);
        return;
      }
      
      if (!response.ok) throw new Error('Failed to fetch connectors');
      const data = await response.json();
      setConnectors(data.connectors || []);
    } catch (err) {
      console.error('Error fetching connectors:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConnectors();
    
    // Auto-refresh every 30 seconds when a connector is expanded
    const interval = setInterval(() => {
      if (expandedConnector) {
        fetchConnectors();
      }
    }, 30000);
    
    return () => clearInterval(interval);
  }, [isAuthenticated, expandedConnector]);

  const toggleConnectorExpansion = (id: string) => {
    setExpandedConnector(expandedConnector === id ? null : id);
  };

  const getStatusBadge = (status: string) => {
    const colors = {
      running: 'bg-green-500/10 text-green-500 border-green-500/20',
      active: 'bg-green-500/10 text-green-500 border-green-500/20',
      healing: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20',
      pending: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20',
      stopped: 'bg-red-500/10 text-red-500 border-red-500/20',
      failed: 'bg-red-500/10 text-red-500 border-red-500/20',
      error: 'bg-red-500/10 text-red-500 border-red-500/20',
      inactive: 'bg-gray-500/10 text-gray-500 border-gray-500/20',
    };

    const colorClass = colors[status.toLowerCase() as keyof typeof colors] || colors.inactive;

    return (
      <span className={`px-2 py-1 rounded-md text-xs font-medium border ${colorClass}`}>
        {status.toUpperCase()}
      </span>
    );
  };

  const formatTimestamp = (timestamp: string | null) => {
    if (!timestamp) return 'N/A';
    return new Date(timestamp).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatBytes = (bytes: number | null) => {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
  };

  const getSyncStatusBadge = (status: string | null) => {
    if (!status) return <span className="text-xs text-gray-500">No sync data</span>;
    
    const colors = {
      succeeded: 'bg-green-500/10 text-green-500 border-green-500/20',
      running: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
      failed: 'bg-red-500/10 text-red-500 border-red-500/20',
      pending: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20',
    };

    const colorClass = colors[status.toLowerCase() as keyof typeof colors] || 'bg-gray-500/10 text-gray-500 border-gray-500/20';

    return (
      <span className={`px-2 py-1 rounded-md text-xs font-medium border ${colorClass}`}>
        {status.toUpperCase()}
      </span>
    );
  };

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">AOS AAM (Connect)</h1>
          <p className="text-gray-400">
            Adaptive API Mesh - Self-healing data connectivity and flow monitoring
          </p>
        </div>
      </div>

      {/* Subtabs */}
      <div className="flex gap-2 border-b border-gray-700">
        <button
          onClick={() => setActiveSubTab('connectors')}
          className={`flex items-center gap-2 px-4 py-3 font-medium transition-all ${
            activeSubTab === 'connectors'
              ? 'text-blue-400 border-b-2 border-blue-400'
              : 'text-gray-400 hover:text-gray-300'
          }`}
        >
          <Database className="w-4 h-4" />
          Connector Details
        </button>
        <button
          onClick={() => setActiveSubTab('flow-monitor')}
          className={`flex items-center gap-2 px-4 py-3 font-medium transition-all ${
            activeSubTab === 'flow-monitor'
              ? 'text-blue-400 border-b-2 border-blue-400'
              : 'text-gray-400 hover:text-gray-300'
          }`}
        >
          <MonitorDot className="w-4 h-4" />
          Flow Monitor
        </button>
      </div>

      {activeSubTab === 'flow-monitor' ? (
        <div className="-mx-6 -mb-6">
          <FlowMonitor />
        </div>
      ) : (
        <div className="space-y-6">

      <div className="bg-gradient-to-br from-purple-900/20 via-blue-900/20 to-green-900/20 rounded-xl border border-purple-500/30 overflow-hidden">
        <div className="p-6 border-b border-purple-500/20 bg-black/40">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="relative">
                <Network className="w-6 h-6 text-purple-400" />
                <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full animate-pulse" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-white flex items-center gap-2">
                  AAM Adaptive API Mesh
                  <span className="px-2 py-0.5 bg-amber-500/20 border border-amber-500/40 rounded text-xs font-medium text-amber-400">
                    DEMO
                  </span>
                </h2>
                <p className="text-sm text-gray-400">Real-time orchestration intelligence and self-healing infrastructure</p>
              </div>
            </div>
          </div>
        </div>

        <div className="p-6 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-black/40 backdrop-blur-sm border border-green-500/30 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <GitBranch className="w-4 h-4 text-green-400" />
                  <span className="text-sm font-medium text-gray-300">Active Connections</span>
                </div>
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              </div>
              <div className="text-3xl font-bold text-white mb-1">{meshMetrics.activeConnections}</div>
              <div className="text-xs text-gray-400">Across 47 data sources</div>
            </div>

            <div className="bg-black/40 backdrop-blur-sm border border-blue-500/30 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Shield className="w-4 h-4 text-blue-400" />
                  <span className="text-sm font-medium text-gray-300">Self-Healing Events</span>
                </div>
                <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
              </div>
              <div className="text-3xl font-bold text-white mb-1">{meshMetrics.healingEvents}</div>
              <div className="text-xs text-gray-400">Auto-repairs last hour</div>
            </div>

            <div className="bg-black/40 backdrop-blur-sm border border-orange-500/30 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-orange-400" />
                  <span className="text-sm font-medium text-gray-300">Schema Drift</span>
                </div>
                <div className="w-2 h-2 bg-orange-500 rounded-full animate-pulse" />
              </div>
              <div className="text-3xl font-bold text-white mb-1">{meshMetrics.driftAlerts}</div>
              <div className="text-xs text-gray-400">Alerts detected</div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-black/40 backdrop-blur-sm border border-purple-500/30 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-3">
                <Zap className="w-4 h-4 text-purple-400" />
                <span className="text-sm font-medium text-gray-300">LLM Intelligence</span>
              </div>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-400">Total Calls</span>
                  <span className="text-lg font-bold text-white">{meshMetrics.llmCalls.toLocaleString()}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-400">Tokens Processed</span>
                  <span className="text-lg font-bold text-white">{(meshMetrics.llmTokens / 1000000).toFixed(2)}M</span>
                </div>
                <div className="mt-2 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-purple-500 to-blue-500 animate-pulse" style={{ width: '73%' }} />
                </div>
              </div>
            </div>

            <div className="bg-black/40 backdrop-blur-sm border border-green-500/30 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-3">
                <Brain className="w-4 h-4 text-green-400" />
                <span className="text-sm font-medium text-gray-300">RAG Learning</span>
              </div>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-400">Field Mappings</span>
                  <span className="text-lg font-bold text-white">{meshMetrics.ragMappings.toLocaleString()}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-400">Confidence Score</span>
                  <span className="text-lg font-bold text-green-400">86%</span>
                </div>
                <div className="mt-2 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-green-500 to-emerald-500 animate-pulse" style={{ width: '86%' }} />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-gray-900 rounded-xl border border-gray-800">
        <div className="p-6 border-b border-gray-800">
          <div className="flex items-center gap-2">
            <GitMerge className="w-5 h-5 text-purple-400" />
            <h3 className="text-lg font-semibold text-white">Connector Details</h3>
          </div>
          <p className="text-sm text-gray-400 mt-1">
            {connectors.length} connection{connectors.length !== 1 ? 's' : ''} configured
          </p>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Activity className="w-8 h-8 text-blue-400 animate-spin" />
          </div>
        ) : connectors.length === 0 ? (
          <div className="text-center py-12">
            <Database className="w-12 h-12 text-gray-600 mx-auto mb-3" />
            <p className="text-gray-500">No connectors found. Please sign in to view your connections.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-800/50 border-b border-gray-700">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    Connection Name
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    Type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    Mappings
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    Drift
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {connectors.map((connector) => {
                  const isExpanded = expandedConnector === connector.id;
                  
                  return (
                    <>
                      <tr key={connector.id} className="hover:bg-gray-800/30 transition-colors">
                        <td className="px-6 py-4">
                          <div className="text-sm font-medium text-white">{connector.name}</div>
                          <div className="text-xs text-gray-500 mt-1">ID: {connector.id.substring(0, 8)}...</div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="px-2 py-1 bg-blue-500/10 border border-blue-500/30 rounded text-xs font-medium text-blue-400">
                            {connector.source_type}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          {getStatusBadge(connector.status)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-white">{connector.mapping_count}</div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          {connector.has_drift ? (
                            <span className="px-2 py-1 bg-orange-500/10 border border-orange-500/30 rounded text-xs font-medium text-orange-400 flex items-center gap-1 w-fit">
                              <AlertTriangle className="w-3 h-3" />
                              DRIFT
                            </span>
                          ) : (
                            <span className="text-xs text-gray-500">None</span>
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <button
                            onClick={() => toggleConnectorExpansion(connector.id)}
                            className="flex items-center gap-2 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors text-sm"
                          >
                            {isExpanded ? (
                              <>
                                <ChevronDown className="w-4 h-4" />
                                Hide
                              </>
                            ) : (
                              <>
                                <ChevronRight className="w-4 h-4" />
                                Details
                              </>
                            )}
                          </button>
                        </td>
                      </tr>
                      
                      {isExpanded && (
                        <tr>
                          <td colSpan={6} className="px-6 py-4 bg-gray-950/50">
                            <div className="space-y-6">
                              <div className="grid grid-cols-2 gap-4 text-sm">
                                <div>
                                  <div className="text-gray-400 mb-1">Connection ID</div>
                                  <code className="text-gray-300 bg-gray-800 px-2 py-1 rounded text-xs">
                                    {connector.id}
                                  </code>
                                </div>
                                <div>
                                  <div className="text-gray-400 mb-1">Source Type</div>
                                  <div className="text-white">{connector.source_type}</div>
                                </div>
                                <div>
                                  <div className="text-gray-400 mb-1">Mapping Count</div>
                                  <div className="text-white">{connector.mapping_count} field mappings</div>
                                </div>
                                <div>
                                  <div className="text-gray-400 mb-1">Drift Status</div>
                                  <div className="text-white">
                                    {connector.has_drift ? (
                                      <span className="text-orange-400">Drift Detected</span>
                                    ) : (
                                      <span className="text-green-400">No Drift</span>
                                    )}
                                  </div>
                                </div>
                                {connector.last_event_type && (
                                  <>
                                    <div>
                                      <div className="text-gray-400 mb-1">Last Event</div>
                                      <div className="text-white">{connector.last_event_type}</div>
                                    </div>
                                    <div>
                                      <div className="text-gray-400 mb-1">Event Time</div>
                                      <div className="text-white">{formatTimestamp(connector.last_event_at)}</div>
                                    </div>
                                  </>
                                )}
                              </div>

                              {connector.last_sync_status && (
                                <div className="border-t border-gray-800 pt-4">
                                  <h4 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                                    <Activity className="w-4 h-4 text-blue-400" />
                                    Last Sync Activity
                                  </h4>
                                  <div className="grid grid-cols-2 gap-4 text-sm">
                                    <div>
                                      <div className="text-gray-400 mb-1">Sync Status</div>
                                      <div>{getSyncStatusBadge(connector.last_sync_status)}</div>
                                    </div>
                                    <div>
                                      <div className="text-gray-400 mb-1">Sync Time</div>
                                      <div className="text-white">{formatTimestamp(connector.last_sync_at)}</div>
                                    </div>
                                    <div>
                                      <div className="text-gray-400 mb-1">Records Synced</div>
                                      <div className="text-white font-mono">
                                        {connector.last_sync_records !== null ? connector.last_sync_records.toLocaleString() : 'N/A'}
                                      </div>
                                    </div>
                                    <div>
                                      <div className="text-gray-400 mb-1">Data Transferred</div>
                                      <div className="text-white font-mono">
                                        {formatBytes(connector.last_sync_bytes)}
                                      </div>
                                    </div>
                                  </div>
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
        </div>
      )}
    </div>
  );
}
