import { useState, useEffect, useRef } from 'react';
import { 
  Activity, 
  CheckCircle, 
  AlertTriangle, 
  XCircle, 
  Clock, 
  Zap,
  Database,
  Server,
  Brain,
  Eye,
  Wrench,
  TrendingUp,
  RefreshCw,
  Map,
  GitMerge,
  Target,
  BarChart3
} from 'lucide-react';
import { API_CONFIG } from '../config/api';
import LiveFlow from './monitor/LiveFlow';

interface ServiceStatus {
  name: string;
  status: 'running' | 'stopped' | 'error';
  port: number;
  error?: string;
}

interface AAMMetrics {
  total_connections: number;
  active_connections?: number;
  active_drift_detections_24h: number;
  successful_repairs_24h: number;
  manual_reviews_required_24h: number;
  average_confidence_score: number;
  average_repair_time_seconds: number;
  timestamp: string;
  data_source?: string;
}

interface AAMConnection {
  id: string;
  name: string;
  source_type: string;
  status: 'ACTIVE' | 'PENDING' | 'FAILED' | 'HEALING' | 'INACTIVE';
  created_at: string;
  updated_at: string;
}

interface AAMEvent {
  id: string;
  connection_name: string;
  source_type?: string;
  event_type: string;
  status: string;
  started_at?: string;
  timestamp?: string;
  error_message?: string;
  message?: string;
}

interface IntelligenceMappingsData {
  total: number;
  autofix_pct: number;
  hitl_pct: number;
}

interface IntelligenceDriftData {
  total: number;
  by_source: Record<string, number>;
}

interface IntelligenceRAGData {
  pending: number;
  accepted: number;
  rejected: number;
}

interface IntelligenceRepairData {
  avg_confidence: number;
  test_pass_rate: number;
}

export default function AAMDashboard() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'live-flow'>('dashboard');
  const [services, setServices] = useState<ServiceStatus[]>([]);
  const [metrics, setMetrics] = useState<AAMMetrics | null>(null);
  const [connections, setConnections] = useState<AAMConnection[]>([]);
  const [events, setEvents] = useState<AAMEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const eventsRef = useRef<HTMLDivElement>(null);

  // Intelligence data state
  const [mappingsData, setMappingsData] = useState<IntelligenceMappingsData | null>(null);
  const [driftData, setDriftData] = useState<IntelligenceDriftData | null>(null);
  const [ragData, setRAGData] = useState<IntelligenceRAGData | null>(null);
  const [repairData, setRepairData] = useState<IntelligenceRepairData | null>(null);
  const [intelligenceLoading, setIntelligenceLoading] = useState(true);
  const [intelligenceError, setIntelligenceError] = useState<string | null>(null);

  const fetchAAMStatus = async () => {
    try {
      const response = await fetch(API_CONFIG.buildApiUrl('/aam/status'));
      if (!response.ok) throw new Error('Failed to fetch AAM status');
      const data = await response.json();
      setServices(data.services || []);
    } catch (err) {
      console.error('Error fetching AAM status:', err);
    }
  };

  const fetchAAMMetrics = async () => {
    try {
      const response = await fetch(API_CONFIG.buildApiUrl('/aam/metrics'));
      if (!response.ok) throw new Error('Failed to fetch AAM metrics');
      const data = await response.json();
      setMetrics(data);
    } catch (err) {
      console.error('Error fetching AAM metrics:', err);
      setError('Failed to load metrics');
    }
  };

  const fetchAAMConnections = async () => {
    try {
      const response = await fetch(API_CONFIG.buildApiUrl('/aam/connections'));
      if (!response.ok) throw new Error('Failed to fetch AAM connections');
      const data = await response.json();
      setConnections(data.connections || []);
    } catch (err) {
      console.error('Error fetching AAM connections:', err);
    }
  };

  const fetchAAMEvents = async () => {
    try {
      const response = await fetch(API_CONFIG.buildApiUrl('/aam/events?limit=50'));
      if (!response.ok) throw new Error('Failed to fetch AAM events');
      const data = await response.json();
      setEvents(data.events || []);
    } catch (err) {
      console.error('Error fetching AAM events:', err);
    }
  };

  const fetchIntelligenceData = async () => {
    setIntelligenceLoading(true);
    setIntelligenceError(null);
    
    try {
      const [mappings, drift, rag, repair] = await Promise.all([
        fetch(API_CONFIG.buildApiUrl('/aam/intelligence/mappings')).then(r => r.json()),
        fetch(API_CONFIG.buildApiUrl('/aam/intelligence/drift_events_24h')).then(r => r.json()),
        fetch(API_CONFIG.buildApiUrl('/aam/intelligence/rag_queue')).then(r => r.json()),
        fetch(API_CONFIG.buildApiUrl('/aam/intelligence/repair_metrics')).then(r => r.json())
      ]);

      setMappingsData(mappings);
      setDriftData(drift);
      setRAGData(rag);
      setRepairData(repair);
    } catch (err) {
      console.error('Error fetching intelligence data:', err);
      setIntelligenceError('Failed to load intelligence data');
    } finally {
      setIntelligenceLoading(false);
    }
  };

  const fetchAllData = async () => {
    setLoading(true);
    await Promise.all([
      fetchAAMStatus(),
      fetchAAMMetrics(),
      fetchAAMConnections(),
      fetchAAMEvents(),
      fetchIntelligenceData()
    ]);
    setLoading(false);
  };

  useEffect(() => {
    fetchAllData();
  }, []);

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'running':
      case 'active':
        return 'text-green-500';
      case 'healing':
      case 'pending':
        return 'text-yellow-500';
      case 'stopped':
      case 'failed':
      case 'error':
        return 'text-red-500';
      default:
        return 'text-gray-500';
    }
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

  const getEventIcon = (eventType: string) => {
    switch (eventType) {
      case 'drift_detected':
        return <AlertTriangle className="w-4 h-4 text-yellow-500" />;
      case 'repair_success':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'sync_completed':
        return <CheckCircle className="w-4 h-4 text-blue-500" />;
      case 'sync_running':
        return <Activity className="w-4 h-4 text-blue-500 animate-pulse" />;
      default:
        return <Activity className="w-4 h-4 text-gray-500" />;
    }
  };

  const formatTimestamp = (timestamp: string | undefined) => {
    if (!timestamp) return 'N/A';
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  const formatTime = (seconds: number) => {
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds.toFixed(0)}s`;
  };

  if (loading && !metrics && activeTab === 'dashboard') {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <Activity className="w-12 h-12 text-blue-500 animate-spin mx-auto mb-4" />
          <p className="text-gray-400">Loading AAM Dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-8">
      {/* Header with Tabs */}
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <h1 className="text-3xl font-bold text-white mb-2">AAM Monitoring</h1>
          <p className="text-gray-400">
            Real-time monitoring of Adaptive API Mesh services and connections
          </p>
        </div>
        {activeTab === 'dashboard' && (
          <div className="flex items-center gap-3">
            <button
              onClick={fetchAllData}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 text-white rounded-lg transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Manual Refresh
            </button>
            <div className="text-sm text-gray-500">
              Manual refresh required
            </div>
          </div>
        )}
      </div>

      {/* Tabs Navigation */}
      <div className="flex items-center gap-2 border-b border-gray-800">
        <button
          onClick={() => setActiveTab('dashboard')}
          className={`flex items-center gap-2 px-4 py-3 font-medium transition-colors border-b-2 ${
            activeTab === 'dashboard'
              ? 'text-blue-400 border-blue-400'
              : 'text-gray-400 border-transparent hover:text-gray-300'
          }`}
        >
          <BarChart3 className="w-4 h-4" />
          Dashboard
        </button>
        <button
          onClick={() => setActiveTab('live-flow')}
          className={`flex items-center gap-2 px-4 py-3 font-medium transition-colors border-b-2 ${
            activeTab === 'live-flow'
              ? 'text-blue-400 border-blue-400'
              : 'text-gray-400 border-transparent hover:text-gray-300'
          }`}
        >
          <Activity className="w-4 h-4" />
          Live Flow
          <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">
            beta
          </span>
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'live-flow' ? (
        <div className="h-[calc(100vh-240px)]">
          <LiveFlow />
        </div>
      ) : (
        <div>

      {/* Service Status Panel */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
        <div className="flex items-center gap-2 mb-4">
          <Server className="w-5 h-5 text-blue-400" />
          <h2 className="text-lg font-medium text-white">Service Status</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {services.map((service) => (
            <div
              key={service.name}
              className="bg-gray-800/50 rounded-lg p-4 border border-gray-700"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  {service.name.includes('Schema') && <Eye className="w-4 h-4 text-purple-400" />}
                  {service.name.includes('RAG') && <Brain className="w-4 h-4 text-cyan-400" />}
                  {service.name.includes('Drift') && <Wrench className="w-4 h-4 text-orange-400" />}
                  {service.name.includes('Orchestrator') && <Database className="w-4 h-4 text-green-400" />}
                  <span className="text-sm font-medium text-white">{service.name}</span>
                </div>
                <div
                  className={`w-2 h-2 rounded-full ${
                    service.status === 'running' ? 'bg-green-500 animate-pulse' : 'bg-red-500'
                  }`}
                />
              </div>
              <div className="text-xs text-gray-400">Port: {service.port}</div>
              {getStatusBadge(service.status)}
            </div>
          ))}
        </div>
      </div>

      {/* Intelligence Readout Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Map className="w-5 h-5 text-purple-400" />
              <h3 className="text-sm font-medium text-gray-400">Mappings</h3>
            </div>
            {intelligenceLoading && <Activity className="w-4 h-4 text-gray-400 animate-spin" />}
          </div>
          <div className="text-3xl font-bold text-white">
            {intelligenceLoading ? '...' : mappingsData?.total || 0}
          </div>
          <div className="text-sm text-gray-500 mt-2 space-y-1">
            <div>Autofix: {intelligenceLoading ? '...' : `${mappingsData?.autofix_pct || 0}%`}</div>
            <div>HITL: {intelligenceLoading ? '...' : `${mappingsData?.hitl_pct || 0}%`}</div>
          </div>
          {intelligenceError && (
            <div className="text-xs text-red-400 mt-2">{intelligenceError}</div>
          )}
        </div>

        <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-orange-400" />
              <h3 className="text-sm font-medium text-gray-400">Drift Events (24h)</h3>
            </div>
            {intelligenceLoading && <Activity className="w-4 h-4 text-gray-400 animate-spin" />}
          </div>
          <div className="text-3xl font-bold text-white">
            {intelligenceLoading ? '...' : driftData?.total || 0}
          </div>
          <div className="text-sm text-gray-500 mt-2">
            {intelligenceLoading ? 'Loading...' : (
              driftData && Object.keys(driftData.by_source).length > 0 ? (
                <div className="space-y-1">
                  {Object.entries(driftData.by_source).map(([source, count]) => (
                    <div key={source}>{source}: {count}</div>
                  ))}
                </div>
              ) : 'No sources detected'
            )}
          </div>
          {intelligenceError && (
            <div className="text-xs text-red-400 mt-2">{intelligenceError}</div>
          )}
        </div>

        <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Brain className="w-5 h-5 text-cyan-400" />
              <h3 className="text-sm font-medium text-gray-400">RAG Suggestions</h3>
            </div>
            {intelligenceLoading && <Activity className="w-4 h-4 text-gray-400 animate-spin" />}
          </div>
          <div className="text-3xl font-bold text-white">
            {intelligenceLoading ? '...' : ragData?.pending || 0}
          </div>
          <div className="text-sm text-gray-500 mt-2 space-y-1">
            <div>Pending: {intelligenceLoading ? '...' : ragData?.pending || 0}</div>
            <div>
              Accepted: {intelligenceLoading ? '...' : ragData?.accepted || 0} | 
              Rejected: {intelligenceLoading ? '...' : ragData?.rejected || 0}
            </div>
          </div>
          {intelligenceError && (
            <div className="text-xs text-red-400 mt-2">{intelligenceError}</div>
          )}
        </div>

        <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Target className="w-5 h-5 text-green-400" />
              <h3 className="text-sm font-medium text-gray-400">Repair Confidence</h3>
            </div>
            {intelligenceLoading && <Activity className="w-4 h-4 text-gray-400 animate-spin" />}
          </div>
          <div className="text-3xl font-bold text-white">
            {intelligenceLoading ? '...' : `${((repairData?.avg_confidence || 0) * 100).toFixed(0)}%`}
          </div>
          <div className="text-sm text-gray-500 mt-2">
            Test Pass Rate: {intelligenceLoading ? '...' : `${((repairData?.test_pass_rate || 0) * 100).toFixed(0)}%`}
          </div>
          {intelligenceError && (
            <div className="text-xs text-red-400 mt-2">{intelligenceError}</div>
          )}
        </div>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Database className="w-5 h-5 text-blue-400" />
              <h3 className="text-sm font-medium text-gray-400">Total Connections</h3>
            </div>
          </div>
          <div className="text-3xl font-bold text-white">{metrics?.total_connections || 0}</div>
          {metrics?.active_connections !== undefined && (
            <div className="text-sm text-gray-500 mt-1">
              {metrics.active_connections} active
            </div>
          )}
        </div>

        <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-yellow-400" />
              <h3 className="text-sm font-medium text-gray-400">Drift Detections (24h)</h3>
            </div>
          </div>
          <div className="text-3xl font-bold text-white">
            {metrics?.active_drift_detections_24h || 0}
          </div>
        </div>

        <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-green-400" />
              <h3 className="text-sm font-medium text-gray-400">Successful Repairs (24h)</h3>
            </div>
          </div>
          <div className="text-3xl font-bold text-white">
            {metrics?.successful_repairs_24h || 0}
          </div>
        </div>

        <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <XCircle className="w-5 h-5 text-red-400" />
              <h3 className="text-sm font-medium text-gray-400">Manual Reviews (24h)</h3>
            </div>
          </div>
          <div className="text-3xl font-bold text-white">
            {metrics?.manual_reviews_required_24h || 0}
          </div>
        </div>

        <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-cyan-400" />
              <h3 className="text-sm font-medium text-gray-400">Avg Confidence Score</h3>
            </div>
          </div>
          <div className="text-3xl font-bold text-white">
            {((metrics?.average_confidence_score || 0) * 100).toFixed(0)}%
          </div>
        </div>

        <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Clock className="w-5 h-5 text-purple-400" />
              <h3 className="text-sm font-medium text-gray-400">Avg Repair Time</h3>
            </div>
          </div>
          <div className="text-3xl font-bold text-white">
            {formatTime(metrics?.average_repair_time_seconds || 0)}
          </div>
        </div>
      </div>

      {/* Connection Health Table and Recent Events */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Connection Health Table */}
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
          <div className="flex items-center gap-2 mb-4">
            <Database className="w-5 h-5 text-green-400" />
            <h2 className="text-lg font-medium text-white">Connection Health</h2>
          </div>
          <div className="overflow-auto max-h-[400px]">
            {connections.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                No connections found
              </div>
            ) : (
              <table className="w-full">
                <thead className="sticky top-0 bg-gray-900">
                  <tr className="border-b border-gray-800">
                    <th className="text-left text-xs font-medium text-gray-500 tracking-wider pb-3">
                      Connection
                    </th>
                    <th className="text-left text-xs font-medium text-gray-500 tracking-wider pb-3">
                      Source
                    </th>
                    <th className="text-center text-xs font-medium text-gray-500 tracking-wider pb-3">
                      Status
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {connections.map((conn) => (
                    <tr
                      key={conn.id}
                      className="border-b border-gray-800 hover:bg-gray-800/50 transition-colors"
                    >
                      <td className="py-3">
                        <div className="text-sm font-medium text-white">{conn.name}</div>
                        <div className="text-xs text-gray-500">
                          {new Date(conn.updated_at).toLocaleDateString()}
                        </div>
                      </td>
                      <td className="py-3">
                        <div className="text-sm text-gray-300">{conn.source_type}</div>
                      </td>
                      <td className="py-3 text-center">
                        {getStatusBadge(conn.status)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Recent Events Log */}
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
          <div className="flex items-center gap-2 mb-4">
            <Activity className="w-5 h-5 text-blue-400" />
            <h2 className="text-lg font-medium text-white">Recent Events</h2>
          </div>
          <div
            ref={eventsRef}
            className="overflow-auto max-h-[400px] space-y-2"
          >
            {events.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                No recent events
              </div>
            ) : (
              events.map((event) => (
                <div
                  key={event.id}
                  className="bg-gray-800/50 rounded-lg p-3 border border-gray-700 hover:border-gray-600 transition-colors"
                >
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5">{getEventIcon(event.event_type)}</div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <span className="text-sm font-medium text-white truncate">
                          {event.connection_name}
                        </span>
                        <span className="text-xs text-gray-500 whitespace-nowrap">
                          {formatTimestamp(event.started_at || event.timestamp)}
                        </span>
                      </div>
                      <div className="text-xs text-gray-400 mb-1">
                        {event.event_type.replace(/_/g, ' ').toUpperCase()}
                        {event.source_type && ` • ${event.source_type}`}
                      </div>
                      {event.error_message && (
                        <div className="text-xs text-red-400 mt-1">
                          {event.error_message}
                        </div>
                      )}
                      {event.message && (
                        <div className="text-xs text-gray-500 mt-1">
                          {event.message}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Data Source Indicator */}
      {metrics?.data_source && (
        <div className="text-center text-xs text-gray-600">
          Data source: {metrics.data_source} • Last updated: {formatTimestamp(metrics.timestamp)}
        </div>
      )}
        </div>
      )}
    </div>
  );
}
