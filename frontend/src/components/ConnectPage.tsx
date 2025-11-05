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
  BarChart3,
  ChevronDown,
  ChevronRight,
  Plus,
  Trash2,
  X
} from 'lucide-react';
import { API_CONFIG, AUTH_TOKEN_KEY } from '../config/api';
import ConfidenceGauge from './ConfidenceGauge';
import { getDataQualityMetadata, DataQualityMetadata } from '../services/dataQualityApi';
import AdaptiveAPIMesh from './AdaptiveAPIMesh';
import LiveFlow from './archive/LiveFlow';

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
  last_health_check?: string;
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

interface ConnectorDetails {
  vendor: string;
  status: string;
  total_mappings: number;
  high_confidence_mappings: number;
  field_mappings: FieldMapping[];
  recent_drift_events: DriftEvent[];
  repair_history: RepairAction[];
}

interface FieldMapping {
  source_field: string;
  canonical_field: string;
  confidence: number;
  transform: string;
  version?: number;
}

interface DriftEvent {
  event_type: string;
  detected_at: string;
  status: string;
  confidence: number;
  old_schema?: any;
  new_schema?: any;
}

interface RepairAction {
  change_type: string;
  applied_at: string;
  details: any;
}

export default function ConnectPage() {
  const [metrics, setMetrics] = useState<AAMMetrics | null>(null);
  const [connections, setConnections] = useState<AAMConnection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [mappingsData, setMappingsData] = useState<IntelligenceMappingsData | null>(null);
  const [driftData, setDriftData] = useState<IntelligenceDriftData | null>(null);
  const [ragData, setRAGData] = useState<IntelligenceRAGData | null>(null);
  const [repairData, setRepairData] = useState<IntelligenceRepairData | null>(null);
  const [intelligenceLoading, setIntelligenceLoading] = useState(true);
  const [intelligenceError, setIntelligenceError] = useState<string | null>(null);

  const [connectorDetails, setConnectorDetails] = useState<ConnectorDetails[]>([]);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'details'>('overview');
  const [expandedConnector, setExpandedConnector] = useState<string | null>(null);

  const [showRegisterModal, setShowRegisterModal] = useState(false);
  const [registerForm, setRegisterForm] = useState({
    name: '',
    source_type: 'Salesforce',
    connector_config: '{}'
  });
  const [registerLoading, setRegisterLoading] = useState(false);
  const [registerError, setRegisterError] = useState<string | null>(null);

  const [operationLoading, setOperationLoading] = useState<Record<string, boolean>>({});
  const [operationError, setOperationError] = useState<Record<string, string>>({});
  
  const [dataQualityMetadata, setDataQualityMetadata] = useState<DataQualityMetadata | null>(null);
  const [qualityLoading, setQualityLoading] = useState(false);

  const fetchDataQuality = async () => {
    setQualityLoading(true);
    try {
      const metadata = await getDataQualityMetadata();
      setDataQualityMetadata(metadata);
    } catch (err) {
      console.error('Error fetching data quality:', err);
    } finally {
      setQualityLoading(false);
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
      setMetrics({
        total_connections: 0,
        active_drift_detections_24h: 0,
        successful_repairs_24h: 0,
        manual_reviews_required_24h: 0,
        average_confidence_score: 0,
        average_repair_time_seconds: 0,
        timestamp: new Date().toISOString(),
        data_source: 'error_fallback'
      });
    }
  };

  const getAuthHeaders = (): HeadersInit => {
    const token = localStorage.getItem(AUTH_TOKEN_KEY);
    if (token) {
      return { 'Authorization': `Bearer ${token}` };
    }
    return {};
  };

  const fetchAAMConnections = async () => {
    try {
      const response = await fetch(API_CONFIG.buildApiUrl('/aam/connections'), {
        headers: getAuthHeaders()
      });
      if (!response.ok) throw new Error('Failed to fetch AAM connections');
      const data = await response.json();
      setConnections(data.connections || []);
    } catch (err) {
      console.error('Error fetching AAM connections:', err);
    }
  };

  const handleRegisterConnection = async () => {
    setRegisterLoading(true);
    setRegisterError(null);

    try {
      let configJson;
      try {
        configJson = JSON.parse(registerForm.connector_config);
      } catch (err) {
        throw new Error('Invalid JSON in connector configuration');
      }

      const response = await fetch(API_CONFIG.buildApiUrl('/aam/connections'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders()
        },
        body: JSON.stringify({
          name: registerForm.name,
          source_type: registerForm.source_type,
          connector_config: configJson
        })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to register connection');
      }

      await fetchAAMConnections();
      await fetchAAMMetrics();
      
      setShowRegisterModal(false);
      setRegisterForm({
        name: '',
        source_type: 'Salesforce',
        connector_config: '{}'
      });
    } catch (err: any) {
      console.error('Error registering connection:', err);
      setRegisterError(err.message || 'Failed to register connection');
    } finally {
      setRegisterLoading(false);
    }
  };

  const handleHealthCheck = async (connectionId: string) => {
    setOperationLoading(prev => ({ ...prev, [connectionId]: true }));
    setOperationError(prev => ({ ...prev, [connectionId]: '' }));

    try {
      const response = await fetch(
        API_CONFIG.buildApiUrl(`/aam/connections/${connectionId}/health-check`),
        {
          method: 'POST',
          headers: getAuthHeaders()
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Health check failed');
      }

      await fetchAAMConnections();
      await fetchAAMMetrics();
    } catch (err: any) {
      console.error('Error running health check:', err);
      setOperationError(prev => ({ 
        ...prev, 
        [connectionId]: err.message || 'Health check failed' 
      }));
    } finally {
      setOperationLoading(prev => ({ ...prev, [connectionId]: false }));
    }
  };

  const handleDeleteConnection = async (connectionId: string, connectionName: string) => {
    if (!confirm(`Are you sure you want to delete "${connectionName}"? This action cannot be undone.`)) {
      return;
    }

    setOperationLoading(prev => ({ ...prev, [`delete_${connectionId}`]: true }));
    setOperationError(prev => ({ ...prev, [`delete_${connectionId}`]: '' }));

    try {
      const response = await fetch(
        API_CONFIG.buildApiUrl(`/aam/connections/${connectionId}`),
        {
          method: 'DELETE',
          headers: getAuthHeaders()
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to delete connection');
      }

      await fetchAAMConnections();
      await fetchAAMMetrics();
    } catch (err: any) {
      console.error('Error deleting connection:', err);
      setOperationError(prev => ({ 
        ...prev, 
        [`delete_${connectionId}`]: err.message || 'Failed to delete connection' 
      }));
    } finally {
      setOperationLoading(prev => ({ ...prev, [`delete_${connectionId}`]: false }));
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

  const fetchConnectorDetails = async () => {
    setDetailsLoading(true);
    try {
      const response = await fetch(API_CONFIG.buildApiUrl('/aam/connector_details'));
      if (!response.ok) throw new Error('Failed to fetch connector details');
      const data = await response.json();
      setConnectorDetails(data.connectors || []);
    } catch (err) {
      console.error('Error fetching connector details:', err);
    } finally {
      setDetailsLoading(false);
    }
  };

  const fetchAllData = async () => {
    setLoading(true);
    await Promise.all([
      fetchAAMMetrics(),
      fetchAAMConnections(),
      fetchIntelligenceData(),
      fetchDataQuality()
    ]);
    setLoading(false);
  };

  useEffect(() => {
    fetchAllData();
  }, []);

  useEffect(() => {
    if (activeTab === 'details' && connectorDetails.length === 0 && !detailsLoading) {
      fetchConnectorDetails();
    }
  }, [activeTab, connectorDetails.length, detailsLoading]);

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

  const getConfidenceBadge = (confidence: number) => {
    const percentage = Math.round(confidence * 100);
    let colorClass = '';
    
    if (confidence >= 0.9) {
      colorClass = 'bg-green-900/30 border-green-500/30 text-green-400';
    } else if (confidence >= 0.7) {
      colorClass = 'bg-yellow-900/30 border-yellow-500/30 text-yellow-400';
    } else {
      colorClass = 'bg-orange-900/30 border-orange-500/30 text-orange-400';
    }
    
    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs border ${colorClass}`}>
        {percentage}%
      </span>
    );
  };

  const toggleConnectorExpansion = (vendor: string) => {
    setExpandedConnector(prev => prev === vendor ? null : vendor);
  };

  if (loading && !metrics) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <Activity className="w-12 h-12 text-blue-500 animate-spin mx-auto mb-4" />
          <p className="text-gray-400">Loading AAM Connect...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* 1. Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-white">AAM Connect</h1>
        <p className="text-gray-400 mt-2">
          Adaptive API Mesh - Self-healing data connectivity with real-time monitoring
        </p>
      </div>

      {/* 2. 3D Adaptive API Mesh Visual */}
      <AdaptiveAPIMesh />

      {/* 4. AAM Overview & Connector Details */}
      <div className="space-y-6 pb-8">
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <h2 className="text-2xl font-bold text-white mb-2">AAM Monitor</h2>
            <p className="text-gray-400">
              Adaptive API Mesh intelligence metrics and connection health
            </p>
          </div>
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
        </div>

        <div className="flex gap-2 border-b border-gray-800">
          <button
            onClick={() => setActiveTab('overview')}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === 'overview'
                ? 'text-white border-b-2 border-blue-500'
                : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            Overview
          </button>
          <button
            onClick={() => setActiveTab('details')}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === 'details'
                ? 'text-white border-b-2 border-blue-500'
                : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            Connector Details
          </button>
        </div>

        {activeTab === 'overview' && (
          <>
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
                  {intelligenceLoading ? '...' : mappingsData?.total ?? 0}
                </div>
                <div className="text-sm text-gray-500 mt-2 space-y-1">
                  <div>Autofix: {intelligenceLoading ? '...' : `${mappingsData?.autofix_pct ?? 0}%`}</div>
                  <div>HITL: {intelligenceLoading ? '...' : `${mappingsData?.hitl_pct ?? 0}%`}</div>
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
                  {intelligenceLoading ? '...' : driftData?.total ?? 0}
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
                  {intelligenceLoading ? '...' : ragData?.pending ?? 0}
                </div>
                <div className="text-sm text-gray-500 mt-2 space-y-1">
                  <div>Pending: {intelligenceLoading ? '...' : ragData?.pending ?? 0}</div>
                  <div>
                    Accepted: {intelligenceLoading ? '...' : ragData?.accepted ?? 0} | 
                    Rejected: {intelligenceLoading ? '...' : ragData?.rejected ?? 0}
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
                  {intelligenceLoading ? '...' : `${((repairData?.avg_confidence ?? 0) * 100).toFixed(0)}%`}
                </div>
                <div className="text-sm text-gray-500 mt-2">
                  Test Pass Rate: {intelligenceLoading ? '...' : `${((repairData?.test_pass_rate ?? 0) * 100).toFixed(0)}%`}
                </div>
                {intelligenceError && (
                  <div className="text-xs text-red-400 mt-2">{intelligenceError}</div>
                )}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Database className="w-5 h-5 text-blue-400" />
                    <h3 className="text-sm font-medium text-gray-400">Total Connections</h3>
                  </div>
                </div>
                <div className="text-3xl font-bold text-white">{metrics?.total_connections ?? 0}</div>
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
                  {metrics?.active_drift_detections_24h ?? 0}
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
                  {metrics?.successful_repairs_24h ?? 0}
                </div>
              </div>

              <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Eye className="w-5 h-5 text-orange-400" />
                    <h3 className="text-sm font-medium text-gray-400">Manual Reviews (24h)</h3>
                  </div>
                </div>
                <div className="text-3xl font-bold text-white">
                  {metrics?.manual_reviews_required_24h ?? 0}
                </div>
              </div>

              <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <TrendingUp className="w-5 h-5 text-cyan-400" />
                    <h3 className="text-sm font-medium text-gray-400">Avg Confidence</h3>
                  </div>
                </div>
                <div className="text-3xl font-bold text-white">
                  {((metrics?.average_confidence_score ?? 0) * 100).toFixed(1)}%
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
                  {formatTime(metrics?.average_repair_time_seconds ?? 0)}
                </div>
              </div>
            </div>

            {dataQualityMetadata && (
              <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <BarChart3 className="w-5 h-5 text-blue-400" />
                    <h3 className="text-lg font-semibold text-white">Data Quality Score</h3>
                  </div>
                  {qualityLoading && <Activity className="w-4 h-4 text-gray-400 animate-spin" />}
                </div>
                <div className="flex items-center gap-8">
                  <div className="flex-shrink-0">
                    <ConfidenceGauge 
                      confidence={dataQualityMetadata.overall_data_quality_score} 
                      label="Data Quality"
                      size="large" 
                    />
                  </div>
                  <div className="flex-1 grid grid-cols-2 gap-4">
                    <div>
                      <div className="text-sm text-gray-400 mb-1">Auto-Applied Repairs</div>
                      <div className="text-2xl font-bold text-green-400">{dataQualityMetadata.auto_applied_repairs}</div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-400 mb-1">Pending HITL Reviews</div>
                      <div className="text-2xl font-bold text-yellow-400">{dataQualityMetadata.hitl_pending_repairs}</div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-400 mb-1">Sources with Drift</div>
                      <div className="text-2xl font-bold text-red-400">{dataQualityMetadata.sources_with_drift.length}</div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-400 mb-1">Overall Confidence</div>
                      <div className="text-2xl font-bold text-blue-400">{((dataQualityMetadata.overall_confidence ?? 0) * 100).toFixed(1)}%</div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div className="bg-gray-900 rounded-xl border border-gray-800">
              <div className="p-6 border-b border-gray-800">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Server className="w-5 h-5 text-blue-400" />
                    <h3 className="text-lg font-semibold text-white">Active Connections</h3>
                  </div>
                  <button
                    onClick={() => setShowRegisterModal(true)}
                    className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
                  >
                    <Plus className="w-4 h-4" />
                    Register Connection
                  </button>
                </div>
              </div>

              <div className="p-6">
                {connections.length === 0 ? (
                  <div className="text-center py-12">
                    <Database className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                    <p className="text-gray-500">No connections registered</p>
                    <button
                      onClick={() => setShowRegisterModal(true)}
                      className="mt-4 text-blue-400 hover:text-blue-300 text-sm"
                    >
                      Register your first connection
                    </button>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {connections.map(conn => (
                      <div
                        key={conn.id}
                        className="flex items-center justify-between p-4 bg-gray-800/50 border border-gray-700 rounded-lg hover:border-gray-600 transition-colors"
                      >
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2">
                            <h4 className="text-white font-medium">{conn.name}</h4>
                            {getStatusBadge(conn.status)}
                          </div>
                          <div className="text-sm text-gray-500 space-y-1">
                            <div>Type: {conn.source_type}</div>
                            <div>Created: {formatTimestamp(conn.created_at)}</div>
                            {conn.last_health_check && (
                              <div>Last Health Check: {formatTimestamp(conn.last_health_check)}</div>
                            )}
                          </div>
                          {operationError[conn.id] && (
                            <div className="mt-2 text-sm text-red-400">
                              {operationError[conn.id]}
                            </div>
                          )}
                        </div>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handleHealthCheck(conn.id)}
                            disabled={operationLoading[conn.id]}
                            className="flex items-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-lg transition-colors text-sm"
                          >
                            {operationLoading[conn.id] ? (
                              <>
                                <Activity className="w-4 h-4 animate-spin" />
                                Checking...
                              </>
                            ) : (
                              <>
                                <Activity className="w-4 h-4" />
                                Health Check
                              </>
                            )}
                          </button>
                          <button
                            onClick={() => handleDeleteConnection(conn.id, conn.name)}
                            disabled={operationLoading[`delete_${conn.id}`]}
                            className="p-2 bg-red-600/10 hover:bg-red-600/20 disabled:bg-gray-700 text-red-400 disabled:text-gray-500 rounded-lg transition-colors"
                            title="Delete connection"
                          >
                            {operationLoading[`delete_${conn.id}`] ? (
                              <Activity className="w-4 h-4 animate-spin" />
                            ) : (
                              <Trash2 className="w-4 h-4" />
                            )}
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </>
        )}

        {activeTab === 'details' && (
          <div className="bg-gray-900 rounded-xl border border-gray-800">
            <div className="p-6 border-b border-gray-800">
              <div className="flex items-center gap-2">
                <GitMerge className="w-5 h-5 text-purple-400" />
                <h3 className="text-lg font-semibold text-white">Connector Details</h3>
              </div>
              <p className="text-sm text-gray-400 mt-1">
                Field mappings, drift events, and repair history per connector
              </p>
            </div>

            {detailsLoading ? (
              <div className="flex items-center justify-center py-12">
                <Activity className="w-8 h-8 text-blue-400 animate-spin" />
              </div>
            ) : connectorDetails.length === 0 ? (
              <div className="text-center py-12">
                <Database className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                <p className="text-gray-500">No connector details available</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-800/50 border-b border-gray-700">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                        Connector
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                        Status
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                        Mappings
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                        High Confidence
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-800">
                    {connectorDetails.map((connector) => {
                      const isExpanded = expandedConnector === connector.vendor;
                      
                      return (
                        <>
                          <tr key={connector.vendor} className="hover:bg-gray-800/30 transition-colors">
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="text-sm font-medium text-white">{connector.vendor}</div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              {getStatusBadge(connector.status)}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="text-sm text-white">{connector.total_mappings}</div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="text-sm text-white">
                                {connector.high_confidence_mappings} / {connector.total_mappings}
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <button
                                onClick={() => toggleConnectorExpansion(connector.vendor)}
                                className="flex items-center gap-2 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors text-sm"
                              >
                                {isExpanded ? (
                                  <>
                                    <ChevronDown className="w-4 h-4" />
                                    Hide Details
                                  </>
                                ) : (
                                  <>
                                    <ChevronRight className="w-4 h-4" />
                                    Show Details
                                  </>
                                )}
                              </button>
                            </td>
                          </tr>
                          
                          {isExpanded && (
                            <tr>
                              <td colSpan={5} className="px-6 py-4 bg-gray-950/50">
                                <div className="space-y-6">
                                  {connector.field_mappings && connector.field_mappings.length > 0 && (
                                    <div>
                                      <h4 className="text-sm font-medium text-gray-400 mb-3 flex items-center gap-2">
                                        <GitMerge className="w-4 h-4" />
                                        Field Mappings ({connector.field_mappings.length})
                                      </h4>
                                      <div className="space-y-2">
                                        {connector.field_mappings.map((mapping, idx) => (
                                          <div
                                            key={idx}
                                            className="flex items-center gap-3 p-3 bg-gray-800/50 border border-gray-700 rounded-lg hover:bg-gray-700/30 transition-colors"
                                          >
                                            <code className="px-3 py-1.5 bg-gray-800 border border-gray-600 rounded text-sm text-gray-300 font-mono">
                                              {mapping.source_field}
                                            </code>
                                            <span className="text-gray-500 font-bold">→</span>
                                            <code className="px-3 py-1.5 bg-blue-900/30 border border-blue-500/30 rounded text-sm text-blue-400 font-mono">
                                              {mapping.canonical_field}
                                            </code>
                                            <div className="ml-auto flex items-center gap-2">
                                              {getConfidenceBadge(mapping.confidence)}
                                              {mapping.version && (
                                                <span className="text-xs text-gray-500">v{mapping.version}</span>
                                              )}
                                            </div>
                                            {mapping.transform && mapping.transform !== 'direct' && (
                                              <span className="px-2 py-1 bg-yellow-900/20 border border-yellow-500/20 rounded text-xs text-yellow-400">
                                                {mapping.transform}
                                              </span>
                                            )}
                                          </div>
                                        ))}
                                      </div>
                                    </div>
                                  )}

                                  {connector.recent_drift_events && connector.recent_drift_events.length > 0 && (
                                    <div>
                                      <h4 className="text-sm font-medium text-gray-400 mb-3 flex items-center gap-2">
                                        <AlertTriangle className="w-4 h-4" />
                                        Recent Drift Events ({connector.recent_drift_events.length})
                                      </h4>
                                      <div className="space-y-2">
                                        {connector.recent_drift_events.map((event, idx) => (
                                          <div
                                            key={idx}
                                            className="flex items-center gap-3 p-3 bg-gray-800/50 border border-gray-700 rounded-lg"
                                          >
                                            <div className="flex-1">
                                              <div className="flex items-center gap-2 mb-1">
                                                <span className="text-sm text-white font-medium">{event.event_type}</span>
                                                {getStatusBadge(event.status)}
                                              </div>
                                              <div className="text-xs text-gray-500">
                                                Detected: {formatTimestamp(event.detected_at)}
                                              </div>
                                            </div>
                                            {getConfidenceBadge(event.confidence)}
                                          </div>
                                        ))}
                                      </div>
                                    </div>
                                  )}

                                  {connector.repair_history && connector.repair_history.length > 0 && (
                                    <div>
                                      <h4 className="text-sm font-medium text-gray-400 mb-3 flex items-center gap-2">
                                        <Wrench className="w-4 h-4" />
                                        Repair History ({connector.repair_history.length})
                                      </h4>
                                      <div className="space-y-2">
                                        {connector.repair_history.map((repair, idx) => (
                                          <div
                                            key={idx}
                                            className="flex items-center gap-3 p-3 bg-gray-800/50 border border-gray-700 rounded-lg"
                                          >
                                            <div className="flex-1">
                                              <div className="flex items-center gap-2 mb-1">
                                                <span className="text-sm text-white font-medium">{repair.change_type}</span>
                                                <CheckCircle className="w-4 h-4 text-green-400" />
                                              </div>
                                              <div className="text-xs text-gray-500">
                                                Applied: {formatTimestamp(repair.applied_at)}
                                              </div>
                                            </div>
                                            {repair.details && (
                                              <code className="px-2 py-1 bg-gray-900/50 border border-gray-600 rounded text-xs text-gray-400">
                                                {JSON.stringify(repair.details).substring(0, 50)}...
                                              </code>
                                            )}
                                          </div>
                                        ))}
                                      </div>
                                    </div>
                                  )}

                                  {(!connector.field_mappings || connector.field_mappings.length === 0) &&
                                   (!connector.recent_drift_events || connector.recent_drift_events.length === 0) &&
                                   (!connector.repair_history || connector.repair_history.length === 0) && (
                                    <div className="text-center py-8 text-gray-500">
                                      <Database className="w-8 h-8 text-gray-600 mx-auto mb-2" />
                                      <p className="text-sm">No detailed information available for this connector</p>
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
        )}
      </div>

      {/* 5. Live Flow Monitor */}
      <LiveFlow />

      {showRegisterModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 border border-gray-700 rounded-xl max-w-2xl w-full max-h-[90vh] overflow-auto">
            <div className="sticky top-0 bg-gray-900 border-b border-gray-700 px-6 py-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Database className="w-5 h-5 text-green-400" />
                <h2 className="text-xl font-semibold text-white">Register New Connection</h2>
              </div>
              <button
                onClick={() => {
                  setShowRegisterModal(false);
                  setRegisterError(null);
                }}
                className="text-gray-400 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-4">
              {registerError && (
                <div className="bg-red-900/20 border border-red-800/30 rounded-lg p-3 text-sm text-red-400">
                  {registerError}
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-400 mb-2">
                  Connection Name *
                </label>
                <input
                  type="text"
                  value={registerForm.name}
                  onChange={(e) => setRegisterForm({ ...registerForm, name: e.target.value })}
                  placeholder="e.g., Salesforce Production"
                  className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-400 mb-2">
                  Source Type *
                </label>
                <select
                  value={registerForm.source_type}
                  onChange={(e) => setRegisterForm({ ...registerForm, source_type: e.target.value })}
                  className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
                >
                  <option value="Salesforce">Salesforce</option>
                  <option value="Supabase">Supabase</option>
                  <option value="MongoDB">MongoDB</option>
                  <option value="FileSource">FileSource</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-400 mb-2">
                  Connector Configuration (JSON) *
                </label>
                <div className="text-xs text-gray-500 mb-2">
                  {registerForm.source_type === 'Salesforce' && (
                    <div className="bg-gray-800/50 border border-gray-700 rounded p-2">
                      Example: {'{'}
                      <br />
                      &nbsp;&nbsp;"instance_url": "https://yourcompany.salesforce.com",
                      <br />
                      &nbsp;&nbsp;"access_token": "00D..."
                      <br />
                      {'}'}
                    </div>
                  )}
                  {registerForm.source_type === 'Supabase' && (
                    <div className="bg-gray-800/50 border border-gray-700 rounded p-2">
                      Example: {'{'}
                      <br />
                      &nbsp;&nbsp;"url": "https://yourproject.supabase.co",
                      <br />
                      &nbsp;&nbsp;"service_key": "eyJ..."
                      <br />
                      {'}'}
                    </div>
                  )}
                  {registerForm.source_type === 'MongoDB' && (
                    <div className="bg-gray-800/50 border border-gray-700 rounded p-2">
                      Example: {'{'}
                      <br />
                      &nbsp;&nbsp;"connection_string": "mongodb+srv://...",
                      <br />
                      &nbsp;&nbsp;"database": "mydb"
                      <br />
                      {'}'}
                    </div>
                  )}
                  {registerForm.source_type === 'FileSource' && (
                    <div className="bg-gray-800/50 border border-gray-700 rounded p-2">
                      Example: {'{'}
                      <br />
                      &nbsp;&nbsp;"file_path": "/path/to/data.csv",
                      <br />
                      &nbsp;&nbsp;"format": "csv"
                      <br />
                      {'}'}
                    </div>
                  )}
                </div>
                <textarea
                  value={registerForm.connector_config}
                  onChange={(e) => setRegisterForm({ ...registerForm, connector_config: e.target.value })}
                  placeholder='{"key": "value"}'
                  rows={8}
                  className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 font-mono text-sm focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  onClick={handleRegisterConnection}
                  disabled={registerLoading || !registerForm.name || !registerForm.connector_config}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-lg transition-colors"
                >
                  {registerLoading ? (
                    <>
                      <Activity className="w-4 h-4 animate-spin" />
                      Registering...
                    </>
                  ) : (
                    <>
                      <Plus className="w-4 h-4" />
                      Register Connection
                    </>
                  )}
                </button>
                <button
                  onClick={() => {
                    setShowRegisterModal(false);
                    setRegisterError(null);
                  }}
                  disabled={registerLoading}
                  className="px-4 py-2 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 text-white rounded-lg transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
