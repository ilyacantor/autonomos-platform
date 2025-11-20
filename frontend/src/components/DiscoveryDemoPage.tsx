import { useState, useEffect } from 'react';
import { X, Check, Loader2, Play, Database, Cloud, Server, FileText, ExternalLink } from 'lucide-react';
import { 
  mockAssets, 
  getVendorSummary, 
  getTotalCounts, 
  getAssetsByVendor,
  type AodAsset,
  type Vendor,
  type VendorSummary
} from '../demo/aodMockData';
import {
  demoCustomer360Mappings,
  getVendorDisplayName,
  getVendorColor,
  type FieldMappingRow
} from '../demo/demoDclMappings';

type StageStatus = 'idle' | 'running' | 'success';

interface PipelineStatus {
  aodDiscovery: StageStatus;
  aamConnections: StageStatus;
  dclMapping: StageStatus;
  agentExecution: StageStatus;
}

interface SelectedAssets {
  [assetId: string]: boolean;
}

export default function DiscoveryDemoPage() {
  const [selectedVendor, setSelectedVendor] = useState<Vendor | null>(null);
  const [showConnectorDetails, setShowConnectorDetails] = useState(false);
  const [showFieldMappings, setShowFieldMappings] = useState(false);
  const [selectedAssets, setSelectedAssets] = useState<SelectedAssets>({});
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatus>({
    aodDiscovery: 'idle',
    aamConnections: 'idle',
    dclMapping: 'idle',
    agentExecution: 'idle',
  });
  const [showWarning, setShowWarning] = useState(false);

  useEffect(() => {
    const autoSelected: SelectedAssets = {};
    mockAssets.forEach(asset => {
      if (asset.state === 'READY_FOR_CONNECT') {
        autoSelected[asset.id] = true;
      }
    });
    setSelectedAssets(autoSelected);
  }, []);

  const vendorSummary = getVendorSummary(mockAssets);
  const totalCounts = getTotalCounts(mockAssets);
  const selectedCount = Object.values(selectedAssets).filter(Boolean).length;
  const selectedVendorSet = new Set(
    Object.keys(selectedAssets)
      .filter(id => selectedAssets[id])
      .map(id => mockAssets.find(a => a.id === id)?.vendor)
      .filter(Boolean)
  );
  const selectedVendorNames = Array.from(selectedVendorSet).map(v => {
    const info = vendorSummary.find(vs => vs.vendor === v);
    return info?.displayName || v;
  });

  const getStateColor = (state: string) => {
    switch (state) {
      case 'READY_FOR_CONNECT': return 'bg-green-500/20 text-green-400 border-green-500/30';
      case 'PARKED': return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
      case 'CONNECTED': return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
      case 'PROCESSING': return 'bg-purple-500/20 text-purple-400 border-purple-500/30';
      case 'UNKNOWN': return 'bg-red-500/20 text-red-400 border-red-500/30';
      default: return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
    }
  };

  const getKindIcon = (kind: string) => {
    switch (kind) {
      case 'db': return <Database className="w-4 h-4" />;
      case 'saas': return <Cloud className="w-4 h-4" />;
      case 'service': return <Server className="w-4 h-4" />;
      case 'host': return <FileText className="w-4 h-4" />;
      default: return <Server className="w-4 h-4" />;
    }
  };

  const handleAssetToggle = (assetId: string) => {
    setSelectedAssets(prev => ({
      ...prev,
      [assetId]: !prev[assetId]
    }));
  };

  const handleConnectAssets = () => {
    if (selectedCount === 0) {
      setShowWarning(true);
      setTimeout(() => setShowWarning(false), 3000);
      return;
    }

    setPipelineStatus({
      aodDiscovery: 'success',
      aamConnections: 'idle',
      dclMapping: 'idle',
      agentExecution: 'idle',
    });

    setTimeout(() => {
      setPipelineStatus(prev => ({ ...prev, aamConnections: 'running' }));
    }, 300);

    setTimeout(() => {
      setPipelineStatus(prev => ({ ...prev, aamConnections: 'success', dclMapping: 'running' }));
    }, 1500);

    setTimeout(() => {
      setPipelineStatus(prev => ({ ...prev, dclMapping: 'success', agentExecution: 'running' }));
    }, 2800);

    setTimeout(() => {
      setPipelineStatus(prev => ({ ...prev, agentExecution: 'success' }));
    }, 4100);
  };

  const VendorModal = () => {
    if (!selectedVendor) return null;

    const assets = getAssetsByVendor(mockAssets, selectedVendor);
    const vendorInfo = vendorSummary.find(v => v.vendor === selectedVendor);

    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm animate-fadeIn">
        <div className="bg-gray-900 border border-gray-700 rounded-xl shadow-2xl w-full max-w-5xl mx-4 max-h-[85vh] flex flex-col animate-slideUp">
          <div className="p-6 border-b border-gray-700 flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-white">{vendorInfo?.displayName} Assets</h2>
              <p className="text-sm text-gray-400 mt-1">{assets.length} assets discovered in catalog</p>
            </div>
            <button
              onClick={() => setSelectedVendor(null)}
              className="text-gray-400 hover:text-white transition-colors"
            >
              <X className="w-6 h-6" />
            </button>
          </div>

          <div className="flex-1 overflow-auto p-6">
            <div className="mb-4 p-3 bg-cyan-500/10 border border-cyan-500/30 rounded text-sm text-cyan-300">
              ✓ AutonomOS has automatically selected all ready assets for this demo. You can deselect any that you don't want to include.
            </div>
            
            <table className="w-full">
              <thead className="text-left text-gray-400 text-sm border-b border-gray-700">
                <tr>
                  <th className="pb-3 font-semibold">Asset Name</th>
                  <th className="pb-3 font-semibold">Kind</th>
                  <th className="pb-3 font-semibold">Environment</th>
                  <th className="pb-3 font-semibold">State</th>
                  <th className="pb-3 font-semibold">Owner</th>
                  <th className="pb-3 font-semibold text-center">Include in Demo</th>
                </tr>
              </thead>
              <tbody className="text-gray-300">
                {assets.map((asset) => {
                  const isReady = asset.state === 'READY_FOR_CONNECT';
                  return (
                    <tr key={asset.id} className="border-b border-gray-800 hover:bg-gray-800/50">
                      <td className="py-4">
                        <div className="flex items-center gap-2">
                          {getKindIcon(asset.kind)}
                          <span className="font-medium">{asset.name}</span>
                        </div>
                      </td>
                      <td className="py-4">
                        <span className="text-sm capitalize">{asset.kind}</span>
                      </td>
                      <td className="py-4">
                        <span className={`text-xs px-2 py-1 rounded ${
                          asset.environment === 'prod' ? 'bg-blue-500/20 text-blue-400' :
                          asset.environment === 'staging' ? 'bg-yellow-500/20 text-yellow-400' :
                          'bg-gray-500/20 text-gray-400'
                        }`}>
                          {asset.environment}
                        </span>
                      </td>
                      <td className="py-4">
                        <span className={`text-xs px-2 py-1 rounded border ${getStateColor(asset.state)}`}>
                          {asset.state.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td className="py-4 text-sm text-gray-400">{asset.ownerEmail}</td>
                      <td className="py-4 text-center">
                        <input
                          type="checkbox"
                          checked={selectedAssets[asset.id] || false}
                          onChange={() => handleAssetToggle(asset.id)}
                          className="w-5 h-5 rounded border-gray-600 bg-gray-800 text-cyan-500 focus:ring-2 focus:ring-cyan-500 focus:ring-offset-0 cursor-pointer"
                          disabled={!isReady}
                        />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="p-6 border-t border-gray-700 flex justify-between items-center">
            <div className="text-sm text-gray-400">
              {Object.keys(selectedAssets).filter(id => selectedAssets[id] && assets.find(a => a.id === id)).length} assets selected from {vendorInfo?.displayName}
            </div>
            <button
              onClick={() => setSelectedVendor(null)}
              className="px-6 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    );
  };

  const ConnectorDetailsModal = () => {
    if (!showConnectorDetails) return null;

    const connectorInfo = [
      {
        vendor: 'Salesforce',
        color: '#0BCAD9',
        auth: [
          'OAuth2 with short-lived access tokens; refresh token rotation enabled.',
          'Scopes selected from connector recipes: api, refresh_token, offline_access.'
        ],
        contract: [
          'API version v59.0; endpoints: /sobjects/Account, /sobjects/Opportunity, /query.',
          'Pagination: nextRecordsUrl; rate-limit policy: exponential backoff with jitter.'
        ],
        note: 'Configuration inferred from connector recipes plus AI over our historical configuration corpus. No manual YAML or one-off scripts.'
      },
      {
        vendor: 'MongoDB',
        color: '#10B981',
        auth: [
          'TLS-enforced connection string with SRV; credentials stored in vault.'
        ],
        contract: [
          'Collections: users, events. Read preference: secondaryPreferred.',
          'Topology and timeouts chosen from best-practice heuristics.'
        ],
        note: 'Topology and timeouts chosen from best-practice heuristics and AI analysis.'
      },
      {
        vendor: 'Supabase',
        color: '#A855F7',
        auth: [
          'Service role key with RLS bypass for system operations.',
          'TLS 1.2+ required; certificate pinning enabled.'
        ],
        contract: [
          'Tables: customers, invoices, usage_events. Schema: public.',
          'Connection pooling: PgBouncer session mode with 10 max connections.'
        ],
        note: 'Connection parameters optimized from Supabase best practices and schema analysis.'
      },
      {
        vendor: 'Legacy Files',
        color: '#F97316',
        auth: [
          'S3-compatible bucket access with IAM role credentials.',
          'Server-side encryption (SSE-S3) enforced on all objects.'
        ],
        contract: [
          'Buckets: customer-exports, legacy-backups. Format: CSV, JSON.',
          'Lifecycle: 90-day retention with automatic archival to Glacier.'
        ],
        note: 'Bucket discovery and format detection via AI-powered file sampling.'
      }
    ];

    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm animate-fadeIn">
        <div className="bg-gray-900 border border-gray-700 rounded-xl shadow-2xl w-full max-w-4xl mx-4 max-h-[85vh] flex flex-col animate-slideUp">
          <div className="p-6 border-b border-gray-700 flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-white">AAM Connector Details</h2>
              <p className="text-sm text-gray-400 mt-1">Configuration for demo tenant connectors</p>
            </div>
            <button
              onClick={() => setShowConnectorDetails(false)}
              className="text-gray-400 hover:text-white transition-colors"
            >
              <X className="w-6 h-6" />
            </button>
          </div>

          <div className="flex-1 overflow-auto p-6 space-y-6">
            {connectorInfo.map((connector) => (
              <div key={connector.vendor} className="border border-gray-700 rounded-lg p-5 bg-gray-800/50">
                <h3 className="text-lg font-semibold mb-3" style={{ color: connector.color }}>
                  {connector.vendor} Connector
                </h3>
                
                <div className="space-y-3 text-sm">
                  <div>
                    <div className="text-gray-400 font-medium mb-1">Authentication:</div>
                    {connector.auth.map((line, idx) => (
                      <div key={idx} className="text-gray-300 ml-4">• {line}</div>
                    ))}
                  </div>
                  
                  <div>
                    <div className="text-gray-400 font-medium mb-1">Contract:</div>
                    {connector.contract.map((line, idx) => (
                      <div key={idx} className="text-gray-300 ml-4">• {line}</div>
                    ))}
                  </div>
                  
                  <div className="mt-3 p-3 bg-cyan-500/10 border border-cyan-500/30 rounded text-cyan-300 text-xs">
                    <strong>How AOS configured this:</strong> {connector.note}
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="p-6 border-t border-gray-700 flex justify-end">
            <button
              onClick={() => setShowConnectorDetails(false)}
              className="px-6 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    );
  };

  const FieldMappingsModal = () => {
    if (!showFieldMappings) return null;

    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm animate-fadeIn">
        <div className="bg-gray-900 border border-gray-700 rounded-xl shadow-2xl w-full max-w-6xl mx-4 max-h-[85vh] flex flex-col animate-slideUp">
          <div className="p-6 border-b border-gray-700 flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-white">DCL Field Mappings – <code className="text-cyan-400">customer_360</code></h2>
              <p className="text-sm text-gray-400 mt-1">Unified customer entity for demo tenant</p>
            </div>
            <button
              onClick={() => setShowFieldMappings(false)}
              className="text-gray-400 hover:text-white transition-colors"
            >
              <X className="w-6 h-6" />
            </button>
          </div>

          <div className="flex-1 overflow-auto p-6">
            <div className="mb-4 p-3 bg-purple-500/10 border border-purple-500/30 rounded text-sm text-purple-300">
              DCL analyzes schemas and ingested data across Salesforce, MongoDB, Supabase, and Legacy Files to propose a unified customer entity.
            </div>

            <table className="w-full">
              <thead className="text-left text-gray-400 text-sm border-b border-gray-700">
                <tr>
                  <th className="pb-3 font-semibold">Canonical Field</th>
                  <th className="pb-3 font-semibold">Type</th>
                  <th className="pb-3 font-semibold">Sources</th>
                </tr>
              </thead>
              <tbody className="text-gray-300">
                {demoCustomer360Mappings.map((mapping) => (
                  <tr key={mapping.canonicalField} className="border-b border-gray-800">
                    <td className="py-4">
                      <code className="text-cyan-400 font-mono">{mapping.canonicalField}</code>
                    </td>
                    <td className="py-4">
                      <span className="text-xs px-2 py-1 rounded bg-gray-700 text-gray-300">
                        {mapping.type}
                      </span>
                    </td>
                    <td className="py-4">
                      <div className="flex flex-wrap gap-2">
                        {mapping.sources.map((source, idx) => (
                          <div
                            key={idx}
                            className="text-xs px-3 py-1.5 rounded border flex items-center gap-2"
                            style={{ 
                              backgroundColor: `${getVendorColor(source.vendor)}15`,
                              borderColor: `${getVendorColor(source.vendor)}40`,
                              color: getVendorColor(source.vendor)
                            }}
                          >
                            <span className="font-semibold">{getVendorDisplayName(source.vendor)}</span>
                            <span className="text-gray-400">·</span>
                            <code className="font-mono">{source.fieldPath}</code>
                            <span className="text-gray-400">·</span>
                            <span className="font-semibold">{Math.round(source.confidence * 100)}%</span>
                          </div>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div className="mt-6 p-4 bg-cyan-500/10 border border-cyan-500/30 rounded text-sm text-cyan-300">
              <strong>How AOS generated this:</strong> AOS uses ontologies, naming heuristics, and data profiling to propose canonical fields and joins. Confidence scores indicate how strong each mapping is; lower-confidence candidates can be routed to governance workflows for review (not shown in this demo).
            </div>
          </div>

          <div className="p-6 border-t border-gray-700 flex justify-end">
            <button
              onClick={() => setShowFieldMappings(false)}
              className="px-6 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    );
  };

  const PipelineStage = ({ 
    stage, 
    status, 
    title, 
    children
  }: { 
    stage: string; 
    status: StageStatus; 
    title: string; 
    children: React.ReactNode;
  }) => (
    <div className={`flex-1 p-6 rounded-lg border transition-all ${
      status === 'success' ? 'bg-green-500/10 border-green-500/30' :
      status === 'running' ? 'bg-blue-500/10 border-blue-500/30' :
      'bg-gray-800/50 border-gray-700'
    }`}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-semibold text-white">{title}</h3>
        {status === 'success' && <Check className="w-6 h-6 text-green-400" />}
        {status === 'running' && <Loader2 className="w-6 h-6 text-blue-400 animate-spin" />}
      </div>
      <div className="text-sm text-gray-300 space-y-2">
        {children}
      </div>
    </div>
  );

  return (
    <div className="space-y-6 px-4 sm:px-6 py-6">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-white mb-4">AOS Discovery & Connection (Demo)</h1>
        <p className="text-lg text-gray-300 leading-relaxed">
          Simulated AOD asset catalog across 4 vendors (Salesforce, MongoDB, Supabase, Legacy Files). 
          Experience the full pipeline: <span className="text-cyan-400 font-semibold">AOD → AAM → DCL → Agent</span>.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-gradient-to-br from-cyan-500/10 to-cyan-600/5 border border-cyan-500/30 rounded-lg p-6">
          <div className="text-3xl font-bold text-white mb-2">{totalCounts.total}</div>
          <div className="text-sm text-gray-400">Total Assets</div>
        </div>
        <div className="bg-gradient-to-br from-green-500/10 to-green-600/5 border border-green-500/30 rounded-lg p-6">
          <div className="text-3xl font-bold text-white mb-2">{totalCounts.ready}</div>
          <div className="text-sm text-gray-400">Ready for Connect</div>
        </div>
        <div className="bg-gradient-to-br from-orange-500/10 to-orange-600/5 border border-orange-500/30 rounded-lg p-6">
          <div className="text-3xl font-bold text-white mb-2">{totalCounts.parked}</div>
          <div className="text-sm text-gray-400">Parked (HITL)</div>
        </div>
        <div className="bg-gradient-to-br from-red-500/10 to-red-600/5 border border-red-500/30 rounded-lg p-6">
          <div className="text-3xl font-bold text-white mb-2">{totalCounts.shadowIT}</div>
          <div className="text-sm text-gray-400">Shadow IT / High Risk</div>
        </div>
      </div>

      <div className="bg-gray-800 rounded-lg border border-gray-700 p-6">
        <h2 className="text-xl font-semibold text-white mb-4">Catalogued Inventory by Vendor</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {vendorSummary.map((vendor) => (
            <div 
              key={vendor.vendor}
              className={`bg-gray-900 border rounded-lg p-6 hover:border-${vendor.color}-500/50 transition-all cursor-pointer`}
              onClick={() => setSelectedVendor(vendor.vendor)}
            >
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-lg font-semibold text-white">{vendor.displayName}</h3>
                <div className={`text-2xl font-bold text-${vendor.color}-400`}>{vendor.count}</div>
              </div>
              <button className={`w-full px-4 py-2 bg-${vendor.color}-600 hover:bg-${vendor.color}-500 text-white rounded-lg transition-colors text-sm font-medium`}>
                View Assets
              </button>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-gray-800 rounded-lg border border-gray-700 p-6">
        <h2 className="text-xl font-semibold text-white mb-4">Connect Selected Assets</h2>
        <div className="flex items-center justify-between mb-6">
          <div className="text-gray-300">
            AutonomOS has automatically selected <span className="font-bold text-cyan-400">{selectedCount} assets across {selectedVendorSet.size} vendors</span> for this demo pipeline. You may deselect assets in the vendor views before running the pipeline.
          </div>
          <button
            onClick={handleConnectAssets}
            disabled={pipelineStatus.aamConnections === 'running' || pipelineStatus.dclMapping === 'running' || pipelineStatus.agentExecution === 'running'}
            className="px-6 py-3 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg transition-colors font-semibold flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Play className="w-5 h-5" />
            Connect Selected Assets
          </button>
        </div>

        {showWarning && (
          <div className="mb-6 p-4 bg-orange-500/20 border border-orange-500/30 rounded-lg text-orange-400 text-sm">
            ⚠️ Select at least one ready asset to include in the demo pipeline.
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
          <PipelineStage
            stage="aod"
            status={pipelineStatus.aodDiscovery}
            title="1. AOD Discovery"
          >
            <p>Assets discovered and triaged automatically at the SaaS / service / database / host level.</p>
            <p className="text-gray-400 italic">Normally: spreadsheets, interviews, and chasing teams just to figure out what's actually running in each tenant.</p>
            <p className="text-cyan-300">AOS uses log and config telemetry plus AI classifiers to tag vendor, environment, and risk, and to surface shadow IT.</p>
          </PipelineStage>

          <PipelineStage
            stage="aam"
            status={pipelineStatus.aamConnections}
            title="2. AAM Connections"
          >
            <p>Configures and validates connectors for the selected assets.</p>
            <p className="text-gray-400 italic">Normally: per-connector OAuth apps, scope tuning, token rotation, API versions, rate limits, and per-tenant quirks.</p>
            <p className="text-cyan-300">
              AOS applies connector recipes and AI over our configuration corpus to choose auth flows, scopes, and backoff policies for {selectedVendorNames.join(', ')} and {selectedCount} selected assets.
            </p>
            <button
              onClick={() => setShowConnectorDetails(true)}
              className="mt-3 text-xs text-cyan-400 hover:text-cyan-300 flex items-center gap-1 underline"
            >
              View connector details <ExternalLink className="w-3 h-3" />
            </button>
          </PipelineStage>

          <PipelineStage
            stage="dcl"
            status={pipelineStatus.dclMapping}
            title="3. DCL Mapping"
          >
            <p>Builds unified entities and field mappings (e.g. <code className="text-cyan-400">customer_360</code>) on top of connected systems.</p>
            <p className="text-gray-400 italic">Normally: weeks of debating column names, IDs, and joins across CRM, billing, events, and legacy exports.</p>
            <p className="text-cyan-300">AOS analyzes schemas and ingested data across systems to propose canonical fields and joins, with confidence scores, then surfaces them for review.</p>
            <button
              onClick={() => setShowFieldMappings(true)}
              className="mt-3 text-xs text-cyan-400 hover:text-cyan-300 flex items-center gap-1 underline"
            >
              View field mappings <ExternalLink className="w-3 h-3" />
            </button>
          </PipelineStage>

          <PipelineStage
            stage="agent"
            status={pipelineStatus.agentExecution}
            title="4. Agent Execution"
          >
            <p>Agents query the unified view instead of raw tables.</p>
            <p className="text-gray-400 italic">Normally: hand-written SQL, multiple BI tools, and manual joins across CRM, usage, and billing data.</p>
            <p className="text-cyan-300">AOS agents run over DCL's unified entities, apply risk and business policies, and return explainable results—no manual SQL or join logic.</p>
          </PipelineStage>
        </div>

        {pipelineStatus.agentExecution === 'success' && (
          <div className="mt-6 p-5 bg-gradient-to-br from-purple-500/10 to-purple-600/5 border border-purple-500/30 rounded-lg">
            <h3 className="text-lg font-semibold text-white mb-3">Agent Output</h3>
            <div className="space-y-3 text-sm">
              <div className="p-3 bg-gray-900/50 rounded border border-gray-700">
                <div className="text-gray-400 mb-2">Query:</div>
                <div className="text-cyan-300 font-mono text-xs">
                  "Show risky customer-facing services over $1M ARR across Salesforce, MongoDB, Supabase, and Legacy Files."
                </div>
              </div>
              <div className="p-3 bg-gray-900/50 rounded border border-gray-700">
                <div className="text-gray-400 mb-2">Agent Response:</div>
                <div className="text-gray-300 text-xs space-y-1">
                  <p>• Found <strong className="text-green-400">12 high-value accounts</strong> with ARR &gt; $1M across unified <code className="text-cyan-400">customer_360</code> view</p>
                  <p>• Identified <strong className="text-orange-400">3 risk signals</strong>: elevated error_rate (MongoDB events), overdue invoices (Supabase), churn flags (Legacy)</p>
                  <p>• Cross-referenced with Salesforce opportunity pipeline to surface at-risk renewals</p>
                  <p className="text-cyan-300 mt-2">Result: Unified view enabled in <strong>4.1 seconds</strong> with no manual joins or SQL</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      <VendorModal />
      <ConnectorDetailsModal />
      <FieldMappingsModal />
    </div>
  );
}
