import { useState } from 'react';
import { Search, ArrowRight, Info } from 'lucide-react';

interface LineageNodeData {
  id: string;
  label: string;
  stage: string;
  metadata: Record<string, string>;
}

export default function DataLineagePage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedNode, setSelectedNode] = useState<LineageNodeData | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = () => {
    if (searchQuery.trim()) {
      setHasSearched(true);
    }
  };

  const mockLineageData: LineageNodeData = {
    id: 'node1',
    label: 'Annual Revenue',
    stage: 'Unified Ontology',
    metadata: {
      'Data Type': 'DECIMAL(18,2)',
      'Source': 'Salesforce.Account.AnnualRevenue',
      'Transformation': 'Currency normalization to USD',
      'Last Updated': '2025-10-17 14:32:18',
      'Owner': 'Data Engineering Team',
      'Confidence Score': '94%',
      'Used By': 'RevOps Agent, FinOps Agent',
    },
  };

  const stages = [
    { id: 'sources', label: 'Raw Sources', color: 'bg-blue-500' },
    { id: 'transform', label: 'DCL Transformations', color: 'bg-purple-500' },
    { id: 'ontology', label: 'Unified Ontology', color: 'bg-green-500' },
    { id: 'agent', label: 'Agent Consumption', color: 'bg-orange-500' },
    { id: 'output', label: 'Final Output', color: 'bg-pink-500' },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Data Lineage</h1>
        <p className="text-gray-400">
          Trace data origins and transformations from source to output
        </p>
      </div>

      <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
        <div className="relative max-w-3xl">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
          <input
            type="text"
            placeholder="Trace Data Origin: Search for KPI, Report, or Unified Entity..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            className="w-full bg-gray-800 text-gray-200 pl-12 pr-4 py-4 rounded-xl border border-gray-700 focus:outline-none focus:border-blue-500 transition-colors text-lg"
          />
        </div>
        <button
          onClick={handleSearch}
          className="mt-4 px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
        >
          Trace Lineage
        </button>
      </div>

      {hasSearched && (
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-8">
          <div className="mb-8">
            <h2 className="text-xl font-semibold text-white mb-6">Lineage Flow</h2>
            <div className="flex items-center justify-between">
              {stages.map((stage, index) => (
                <div key={stage.id} className="flex items-center">
                  <div className="text-center">
                    <div
                      className={`w-32 h-32 ${stage.color} rounded-xl flex items-center justify-center mb-3 shadow-lg cursor-pointer hover:scale-105 transition-transform`}
                      onClick={() => setSelectedNode(mockLineageData)}
                    >
                      <span className="text-white font-semibold text-sm px-2 text-center">
                        {stage.label}
                      </span>
                    </div>
                    <div className="text-xs text-gray-500">Click to explore</div>
                  </div>
                  {index < stages.length - 1 && (
                    <ArrowRight className="w-8 h-8 text-gray-600 mx-4" />
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="bg-gradient-to-r from-blue-900/20 via-purple-900/20 to-pink-900/20 rounded-xl border border-gray-700 p-6 text-center">
            <Info className="w-8 h-8 text-blue-400 mx-auto mb-3" />
            <h3 className="text-lg font-semibold text-white mb-2">
              Sankey Diagram Integration Area
            </h3>
            <p className="text-gray-400 max-w-2xl mx-auto">
              This is the designated space for your existing Sankey visualization. The flow diagram
              will animate from left to right, showing data transformation through each stage. Click
              any node to view detailed properties in the side panel.
            </p>
          </div>
        </div>
      )}

      {selectedNode && (
        <div className="fixed inset-y-0 right-0 w-96 bg-gray-900 border-l border-gray-800 shadow-2xl z-50 overflow-auto animate-in slide-in-from-right">
          <div className="sticky top-0 bg-gray-900 border-b border-gray-800 p-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-lg font-semibold text-white">Node Properties</h3>
              <button
                onClick={() => setSelectedNode(null)}
                className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
              >
                <span className="text-gray-400 text-xl">×</span>
              </button>
            </div>
            <div className="text-sm text-blue-400">{selectedNode.label}</div>
            <div className="text-xs text-gray-500 mt-1">{selectedNode.stage}</div>
          </div>

          <div className="p-6 space-y-4">
            {Object.entries(selectedNode.metadata).map(([key, value]) => (
              <div key={key} className="pb-4 border-b border-gray-800">
                <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">
                  {key}
                </div>
                <div className="text-sm text-gray-200">{value}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
