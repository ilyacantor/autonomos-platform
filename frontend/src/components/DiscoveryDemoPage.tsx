import { useState, useEffect } from 'react';
import { X, Check, Loader2, Play, Database, Cloud, Server, FileText } from 'lucide-react';
import { 
  mockAssets, 
  getVendorSummary, 
  getTotalCounts, 
  getAssetsByVendor,
  type AodAsset,
  type Vendor,
  type VendorSummary
} from '../demo/aodMockData';

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
  const [selectedAssets, setSelectedAssets] = useState<SelectedAssets>({});
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatus>({
    aodDiscovery: 'idle',
    aamConnections: 'idle',
    dclMapping: 'idle',
    agentExecution: 'idle',
  });
  const [showWarning, setShowWarning] = useState(false);

  const vendorSummary = getVendorSummary(mockAssets);
  const totalCounts = getTotalCounts(mockAssets);
  const selectedCount = Object.values(selectedAssets).filter(Boolean).length;
  const selectedVendors = new Set(
    Object.keys(selectedAssets)
      .filter(id => selectedAssets[id])
      .map(id => mockAssets.find(a => a.id === id)?.vendor)
      .filter(Boolean)
  );

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
                {assets.map((asset) => (
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
                        disabled={asset.state === 'CONNECTED'}
                      />
                    </td>
                  </tr>
                ))}
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

  const PipelineStage = ({ 
    stage, 
    status, 
    title, 
    description 
  }: { 
    stage: string; 
    status: StageStatus; 
    title: string; 
    description: string;
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
      <p className="text-sm text-gray-400">{description}</p>
    </div>
  );

  return (
    <div className="space-y-6 px-4 sm:px-6 py-6">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-white mb-4">AOS Discovery & Connection (Demo)</h1>
        <p className="text-lg text-gray-300 leading-relaxed">
          Simulated AOD asset catalog across 4 vendors (Salesforce, MongoDB, Supabase, Legacy Files). 
          Select assets and run the full pipeline demo: <span className="text-cyan-400 font-semibold">AOD → AAM → DCL → Agent</span>.
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
            You've selected <span className="font-bold text-cyan-400">{selectedCount}</span> assets 
            across <span className="font-bold text-cyan-400">{selectedVendors.size}</span> vendors for the demo pipeline.
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
            ⚠️ Please select at least one asset to connect
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
          <PipelineStage
            stage="aod"
            status={pipelineStatus.aodDiscovery}
            title="1. AOD Discovery"
            description="Static asset catalog (fake AOD). Assets pre-discovered and ready."
          />
          <PipelineStage
            stage="aam"
            status={pipelineStatus.aamConnections}
            title="2. AAM Connections"
            description="Simulating connector activation for selected vendors."
          />
          <PipelineStage
            stage="dcl"
            status={pipelineStatus.dclMapping}
            title="3. DCL Mapping"
            description="Simulating unified view creation (customer_360)."
          />
          <PipelineStage
            stage="agent"
            status={pipelineStatus.agentExecution}
            title="4. Agent Execution"
            description="Simulating a simple cross-source query."
          />
        </div>
      </div>

      <VendorModal />
    </div>
  );
}
