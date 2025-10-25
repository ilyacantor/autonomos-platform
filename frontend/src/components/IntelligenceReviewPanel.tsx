import { useState } from 'react';
import { Clock, TrendingUp, AlertTriangle, CheckCircle, X, Edit2 } from 'lucide-react';
import type { MappingReview, SchemaChange } from '../types';

interface IntelligenceReviewPanelProps {
  mappings: MappingReview[];
  schemaChanges: SchemaChange[];
}

export default function IntelligenceReviewPanel({ mappings, schemaChanges }: IntelligenceReviewPanelProps) {
  const [activeTab, setActiveTab] = useState<'review' | 'schema'>('review');
  const [selectedMapping, setSelectedMapping] = useState<MappingReview | null>(null);

  const handleApprove = (id: string) => {
    console.log('Approved mapping:', id);
    setSelectedMapping(null);
  };

  const handleEdit = (id: string) => {
    console.log('Edit mapping:', id);
  };

  const handleIgnore = (id: string) => {
    console.log('Ignored mapping:', id);
    setSelectedMapping(null);
  };

  return (
    <>
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 h-full flex flex-col">
        <h2 className="text-lg font-semibold text-white mb-4">Intelligence Review & Schema Drift</h2>

        <div className="flex gap-2 mb-4">
          <button
            onClick={() => setActiveTab('review')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'review'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-800 text-gray-400 hover:text-gray-200'
            }`}
          >
            Review Required
          </button>
          <button
            onClick={() => setActiveTab('schema')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'schema'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-800 text-gray-400 hover:text-gray-200'
            }`}
          >
            Schema Log
          </button>
        </div>

        <div className="flex-1 overflow-auto">
          {activeTab === 'review' ? (
            <div className="space-y-3">
              {mappings.map((mapping) => (
                <div
                  key={mapping.id}
                  className="bg-gray-800 rounded-lg p-4 border border-gray-700 hover:border-orange-500/50 transition-colors"
                >
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <Clock className="w-3 h-3 text-gray-500" />
                        <span className="text-xs text-gray-500">
                          {new Date(mapping.timestamp).toLocaleString()}
                        </span>
                      </div>
                      <div className="text-sm text-gray-300 mb-1">
                        <span className="text-blue-400">Source:</span> {mapping.sourceField}
                      </div>
                      <div className="text-sm text-gray-300 flex items-center gap-2">
                        <TrendingUp className="w-3 h-3 text-green-400" />
                        <span className="text-green-400">Unified:</span> {mapping.unifiedField}
                      </div>
                    </div>
                    <div
                      className={`px-2 py-1 rounded text-xs font-semibold ${
                        mapping.confidence >= 75
                          ? 'bg-orange-500/20 text-orange-400'
                          : 'bg-red-500/20 text-red-400'
                      }`}
                    >
                      {mapping.confidence}%
                    </div>
                  </div>
                  <button
                    onClick={() => setSelectedMapping(mapping)}
                    className="mt-3 w-full px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors"
                  >
                    Review
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <div className="space-y-3">
              {schemaChanges.map((change) => (
                <div
                  key={change.id}
                  className="bg-gray-800 rounded-lg p-4 border border-gray-700"
                >
                  <div className="flex items-start gap-3">
                    <div
                      className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                        change.changeType === 'added'
                          ? 'bg-green-500/20'
                          : change.changeType === 'modified'
                          ? 'bg-yellow-500/20'
                          : 'bg-red-500/20'
                      }`}
                    >
                      <AlertTriangle
                        className={`w-4 h-4 ${
                          change.changeType === 'added'
                            ? 'text-green-400'
                            : change.changeType === 'modified'
                            ? 'text-yellow-400'
                            : 'text-red-400'
                        }`}
                      />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-medium text-white">{change.source}</span>
                        <span
                          className={`px-2 py-0.5 rounded text-xs font-semibold uppercase ${
                            change.changeType === 'added'
                              ? 'bg-green-500/20 text-green-400'
                              : change.changeType === 'modified'
                              ? 'bg-yellow-500/20 text-yellow-400'
                              : 'bg-red-500/20 text-red-400'
                          }`}
                        >
                          {change.changeType}
                        </span>
                      </div>
                      <div className="text-sm text-blue-400 mb-1">{change.field}</div>
                      <div className="text-xs text-gray-500">{change.description}</div>
                      <div className="text-xs text-gray-600 mt-2">
                        {new Date(change.timestamp).toLocaleString()}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {selectedMapping && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 rounded-xl border border-gray-700 max-w-4xl w-full max-h-[90vh] overflow-auto">
            <div className="sticky top-0 bg-gray-900 border-b border-gray-700 p-6 flex items-center justify-between">
              <h3 className="text-xl font-semibold text-white">Review Mapping</h3>
              <button
                onClick={() => setSelectedMapping(null)}
                className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-gray-400" />
              </button>
            </div>

            <div className="p-6">
              <div className="grid grid-cols-2 gap-6 mb-6">
                <div>
                  <h4 className="text-sm font-semibold text-gray-400 mb-3 uppercase tracking-wider">
                    Source Data Snippet
                  </h4>
                  <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
                    <pre className="text-xs text-green-400 font-mono overflow-x-auto">
                      {selectedMapping.sourceSample}
                    </pre>
                  </div>
                  <div className="mt-4">
                    <div className="text-sm text-gray-400 mb-1">Source Field</div>
                    <div className="text-base text-blue-400 font-mono">
                      {selectedMapping.sourceField}
                    </div>
                  </div>
                </div>

                <div>
                  <h4 className="text-sm font-semibold text-gray-400 mb-3 uppercase tracking-wider">
                    Proposed Unified Mapping
                  </h4>
                  <div className="bg-gray-800 rounded-lg p-4 border border-gray-700 mb-4">
                    <div className="text-sm text-gray-400 mb-2">Unified Entity & Field</div>
                    <div className="text-lg text-green-400 font-mono">
                      {selectedMapping.unifiedField}
                    </div>
                    <div className="mt-4 pt-4 border-t border-gray-700">
                      <div className="text-sm text-gray-400 mb-1">Confidence Score</div>
                      <div className="flex items-center gap-3">
                        <div className="flex-1 h-2 bg-gray-700 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-orange-500 to-orange-400"
                            style={{ width: `${selectedMapping.confidence}%` }}
                          />
                        </div>
                        <span className="text-lg font-bold text-orange-400">
                          {selectedMapping.confidence}%
                        </span>
                      </div>
                    </div>
                  </div>

                  <div>
                    <h4 className="text-sm font-semibold text-gray-400 mb-2 uppercase tracking-wider">
                      LLM Reasoning
                    </h4>
                    <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
                      <p className="text-sm text-gray-300 leading-relaxed">
                        {selectedMapping.llmReasoning}
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex gap-3 pt-6 border-t border-gray-700">
                <button
                  onClick={() => handleApprove(selectedMapping.id)}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-green-600 hover:bg-green-700 text-white font-medium rounded-lg transition-colors"
                >
                  <CheckCircle className="w-5 h-5" />
                  Approve Mapping
                </button>
                <button
                  onClick={() => handleEdit(selectedMapping.id)}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
                >
                  <Edit2 className="w-5 h-5" />
                  Edit Mapping
                </button>
                <button
                  onClick={() => handleIgnore(selectedMapping.id)}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-gray-700 hover:bg-gray-600 text-white font-medium rounded-lg transition-colors"
                >
                  <X className="w-5 h-5" />
                  Ignore & Flag
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
