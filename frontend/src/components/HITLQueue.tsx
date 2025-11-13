import { useState, useEffect } from 'react';
import { AlertTriangle, CheckCircle, XCircle, Clock, Eye } from 'lucide-react';

interface HITLAsset {
  id: string;
  asset_name: string;
  asset_type: string;
  risk_level: 'high' | 'medium';
  risk_score: number;
  vendor: string;
  discovered_at: string;
  reason: string;
  metadata: Record<string, unknown>;
}

interface HITLDecision {
  asset_id: string;
  decision: 'approve' | 'reject' | 'flag';
  notes?: string;
}

export default function HITLQueue() {
  const [queue, setQueue] = useState<HITLAsset[]>([
    // Mock data for demonstration
    {
      id: '1',
      asset_name: 'aws-prod-db-01',
      asset_type: 'Database',
      risk_level: 'high',
      risk_score: 0.92,
      vendor: 'AWS',
      discovered_at: new Date().toISOString(),
      reason: 'Unencrypted database with public access detected',
      metadata: { region: 'us-east-1', size: '2TB', connections: 247 }
    },
    {
      id: '2',
      asset_name: 'shadow-saas-tool-42',
      asset_type: 'SaaS',
      risk_level: 'high',
      risk_score: 0.88,
      vendor: 'Unknown',
      discovered_at: new Date().toISOString(),
      reason: 'Unauthorized SaaS tool with company data access',
      metadata: { users: 15, data_access: 'full', cost_monthly: '$299' }
    },
    {
      id: '3',
      asset_name: 'staging-api-gateway',
      asset_type: 'Service',
      risk_level: 'medium',
      risk_score: 0.65,
      vendor: 'GCP',
      discovered_at: new Date().toISOString(),
      reason: 'Staging environment with production credentials',
      metadata: { region: 'us-central1', requests_per_day: 1200 }
    },
    {
      id: '4',
      asset_name: 'legacy-payment-processor',
      asset_type: 'Service',
      risk_level: 'medium',
      risk_score: 0.58,
      vendor: 'On-Premise',
      discovered_at: new Date().toISOString(),
      reason: 'Outdated SSL certificate and deprecated API version',
      metadata: { ssl_expires: '2024-12-01', api_version: '1.2' }
    }
  ]);
  
  const [selectedAsset, setSelectedAsset] = useState<HITLAsset | null>(null);
  const [decisionNotes, setDecisionNotes] = useState('');
  const [filter, setFilter] = useState<'all' | 'high' | 'medium'>('all');

  const handleDecision = (decision: 'approve' | 'reject' | 'flag') => {
    if (!selectedAsset) return;

    console.log('[HITL] Decision made:', {
      asset_id: selectedAsset.id,
      asset_name: selectedAsset.asset_name,
      decision,
      notes: decisionNotes
    });

    // Remove from queue after decision
    setQueue(queue.filter(asset => asset.id !== selectedAsset.id));
    setSelectedAsset(null);
    setDecisionNotes('');
  };

  const filteredQueue = filter === 'all' 
    ? queue 
    : queue.filter(asset => asset.risk_level === filter);

  const highRiskCount = queue.filter(a => a.risk_level === 'high').length;
  const mediumRiskCount = queue.filter(a => a.risk_level === 'medium').length;

  return (
    <div className="bg-gray-800 rounded-lg border border-yellow-500/30 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 bg-gradient-to-br from-yellow-500 to-orange-600 rounded-xl flex items-center justify-center">
            <AlertTriangle className="w-7 h-7 text-white" />
          </div>
          <div>
            <h3 className="text-2xl font-bold text-white">HITL Review Queue</h3>
            <p className="text-sm text-gray-400">
              Human-in-the-Loop decisions for edge case assets
            </p>
          </div>
        </div>
        
        {/* Queue Stats */}
        <div className="flex items-center gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-red-400">{highRiskCount}</div>
            <div className="text-xs text-gray-400">High Risk</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-yellow-400">{mediumRiskCount}</div>
            <div className="text-xs text-gray-400">Medium Risk</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-cyan-400">{queue.length}</div>
            <div className="text-xs text-gray-400">Total Queue</div>
          </div>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setFilter('all')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            filter === 'all'
              ? 'bg-cyan-600 text-white'
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          }`}
        >
          All ({queue.length})
        </button>
        <button
          onClick={() => setFilter('high')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            filter === 'high'
              ? 'bg-red-600 text-white'
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          }`}
        >
          High Risk ({highRiskCount})
        </button>
        <button
          onClick={() => setFilter('medium')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            filter === 'medium'
              ? 'bg-yellow-600 text-white'
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          }`}
        >
          Medium Risk ({mediumRiskCount})
        </button>
      </div>

      {/* Queue Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Asset List */}
        <div className="space-y-3">
          <h4 className="text-sm font-medium text-gray-400 uppercase mb-2">Pending Review</h4>
          {filteredQueue.length === 0 ? (
            <div className="bg-gray-900/50 rounded-lg p-8 text-center">
              <CheckCircle className="w-12 h-12 text-green-400 mx-auto mb-3 opacity-50" />
              <p className="text-gray-400">No assets in queue</p>
              <p className="text-sm text-gray-500 mt-1">All {filter} risk items reviewed</p>
            </div>
          ) : (
            filteredQueue.map(asset => (
              <div
                key={asset.id}
                onClick={() => setSelectedAsset(asset)}
                className={`bg-gray-900/60 rounded-lg p-4 cursor-pointer transition-all border-l-4 ${
                  asset.risk_level === 'high'
                    ? 'border-red-500 hover:bg-red-900/20'
                    : 'border-yellow-500 hover:bg-yellow-900/20'
                } ${
                  selectedAsset?.id === asset.id
                    ? 'ring-2 ring-cyan-500'
                    : ''
                }`}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h5 className="text-base font-medium text-white">{asset.asset_name}</h5>
                      <span className="text-xs text-gray-400 bg-gray-800 px-2 py-1 rounded">
                        {asset.asset_type}
                      </span>
                    </div>
                    <div className="text-sm text-gray-400">{asset.vendor}</div>
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      asset.risk_level === 'high'
                        ? 'bg-red-500/20 text-red-400'
                        : 'bg-yellow-500/20 text-yellow-400'
                    }`}>
                      {asset.risk_level.toUpperCase()}
                    </span>
                    <div className="text-xs text-gray-500">
                      Score: {(asset.risk_score * 100).toFixed(0)}%
                    </div>
                  </div>
                </div>
                <div className="text-sm text-gray-300 mt-2 line-clamp-2">
                  {asset.reason}
                </div>
                <div className="flex items-center gap-2 mt-3 text-xs text-gray-500">
                  <Clock className="w-3 h-3" />
                  {new Date(asset.discovered_at).toLocaleString()}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Decision Panel */}
        <div className="bg-gray-900/50 rounded-lg p-6 border border-gray-700">
          {selectedAsset ? (
            <>
              <div className="flex items-center gap-2 mb-4">
                <Eye className="w-5 h-5 text-cyan-400" />
                <h4 className="text-lg font-medium text-white">Asset Review</h4>
              </div>

              {/* Asset Details */}
              <div className="space-y-4 mb-6">
                <div>
                  <div className="text-sm text-gray-400 mb-1">Asset Name</div>
                  <div className="text-white font-medium">{selectedAsset.asset_name}</div>
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-sm text-gray-400 mb-1">Type</div>
                    <div className="text-white">{selectedAsset.asset_type}</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-400 mb-1">Vendor</div>
                    <div className="text-white">{selectedAsset.vendor}</div>
                  </div>
                </div>

                <div>
                  <div className="text-sm text-gray-400 mb-1">Risk Assessment</div>
                  <div className={`text-white font-medium ${
                    selectedAsset.risk_level === 'high' ? 'text-red-400' : 'text-yellow-400'
                  }`}>
                    {selectedAsset.risk_level.toUpperCase()} - {(selectedAsset.risk_score * 100).toFixed(0)}%
                  </div>
                </div>

                <div>
                  <div className="text-sm text-gray-400 mb-1">Reason</div>
                  <div className="text-white text-sm">{selectedAsset.reason}</div>
                </div>

                <div>
                  <div className="text-sm text-gray-400 mb-2">Metadata</div>
                  <div className="bg-gray-800 rounded p-3 text-xs font-mono text-gray-300 space-y-1">
                    {Object.entries(selectedAsset.metadata).map(([key, value]) => (
                      <div key={key}>
                        <span className="text-cyan-400">{key}:</span> {JSON.stringify(value)}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Decision Notes */}
                <div>
                  <label className="text-sm text-gray-400 mb-2 block">Decision Notes (Optional)</label>
                  <textarea
                    value={decisionNotes}
                    onChange={(e) => setDecisionNotes(e.target.value)}
                    placeholder="Add notes about your decision..."
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-cyan-500 transition-colors resize-none"
                    rows={3}
                  />
                </div>
              </div>

              {/* Decision Buttons */}
              <div className="space-y-2">
                <button
                  onClick={() => handleDecision('approve')}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors"
                >
                  <CheckCircle className="w-5 h-5" />
                  Approve & Catalog
                </button>
                
                <button
                  onClick={() => handleDecision('reject')}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors"
                >
                  <XCircle className="w-5 h-5" />
                  Reject & Quarantine
                </button>
                
                <button
                  onClick={() => handleDecision('flag')}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-yellow-600 hover:bg-yellow-700 text-white rounded-lg font-medium transition-colors"
                >
                  <AlertTriangle className="w-5 h-5" />
                  Flag for Further Review
                </button>
              </div>
            </>
          ) : (
            <div className="text-center py-12 text-gray-500">
              <Eye className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p>Select an asset from the queue to review</p>
              <p className="text-sm mt-1">Make decisions on high and medium risk items</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
