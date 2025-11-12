import { useState, useEffect } from 'react';
import { 
  Activity, 
  GitMerge,
  ChevronDown,
  ChevronRight,
  Database,
  AlertTriangle
} from 'lucide-react';
import { API_CONFIG, AUTH_TOKEN_KEY } from '../config/api';
import { useAuth } from '../hooks/useAuth';

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
  const { isAuthenticated } = useAuth();
  const [connectorDetails, setConnectorDetails] = useState<ConnectorDetails[]>([]);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [expandedConnector, setExpandedConnector] = useState<string | null>(null);

  const getAuthHeaders = (): HeadersInit => {
    const token = localStorage.getItem(AUTH_TOKEN_KEY);
    if (token) {
      return { 'Authorization': `Bearer ${token}` };
    }
    return {};
  };

  const fetchConnectorDetails = async () => {
    setDetailsLoading(true);
    try {
      const response = await fetch(API_CONFIG.buildApiUrl('/aam/connector_details'), {
        headers: getAuthHeaders()
      });
      
      if (response.status === 401) {
        console.log('No tenant context — sign in or select tenant.');
        setConnectorDetails([]);
        return;
      }
      
      if (!response.ok) throw new Error('Failed to fetch connector details');
      const data = await response.json();
      setConnectorDetails(data.connectors || []);
    } catch (err) {
      console.error('Error fetching connector details:', err);
    } finally {
      setDetailsLoading(false);
    }
  };

  useEffect(() => {
    fetchConnectorDetails();
  }, [isAuthenticated]);

  const toggleConnectorExpansion = (vendor: string) => {
    setExpandedConnector(expandedConnector === vendor ? null : vendor);
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

  const getConfidenceBadge = (confidence: number) => {
    if (confidence >= 0.9) {
      return <span className="px-2 py-1 bg-green-500/10 text-green-500 border border-green-500/20 rounded text-xs font-medium">High ({(confidence * 100).toFixed(0)}%)</span>;
    } else if (confidence >= 0.7) {
      return <span className="px-2 py-1 bg-yellow-500/10 text-yellow-500 border border-yellow-500/20 rounded text-xs font-medium">Medium ({(confidence * 100).toFixed(0)}%)</span>;
    } else {
      return <span className="px-2 py-1 bg-red-500/10 text-red-500 border border-red-500/20 rounded text-xs font-medium">Low ({(confidence * 100).toFixed(0)}%)</span>;
    }
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">AOS Connector Details</h1>
          <p className="text-gray-400">
            Field mappings, drift events, and repair history per connector
          </p>
        </div>
      </div>

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
                                        className="p-3 bg-yellow-500/5 border border-yellow-500/20 rounded-lg"
                                      >
                                        <div className="flex items-center justify-between mb-2">
                                          <span className="text-sm font-medium text-yellow-400">
                                            {event.event_type}
                                          </span>
                                          <span className="text-xs text-gray-500">
                                            {formatTimestamp(event.detected_at)}
                                          </span>
                                        </div>
                                        <div className="text-xs text-gray-400">
                                          Status: {event.status} | Confidence: {(event.confidence * 100).toFixed(0)}%
                                        </div>
                                        {event.new_schema && (
                                          <div className="mt-2 text-xs text-gray-500">
                                            <pre className="bg-gray-900 p-2 rounded overflow-x-auto">
                                              {JSON.stringify(event.new_schema, null, 2)}
                                            </pre>
                                          </div>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {connector.repair_history && connector.repair_history.length > 0 && (
                                <div>
                                  <h4 className="text-sm font-medium text-gray-400 mb-3">
                                    Repair History ({connector.repair_history.length})
                                  </h4>
                                  <div className="space-y-2">
                                    {connector.repair_history.map((repair, idx) => (
                                      <div
                                        key={idx}
                                        className="p-3 bg-green-500/5 border border-green-500/20 rounded-lg"
                                      >
                                        <div className="flex items-center justify-between">
                                          <span className="text-sm font-medium text-green-400">
                                            {repair.change_type}
                                          </span>
                                          <span className="text-xs text-gray-500">
                                            {formatTimestamp(repair.applied_at)}
                                          </span>
                                        </div>
                                      </div>
                                    ))}
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
  );
}
