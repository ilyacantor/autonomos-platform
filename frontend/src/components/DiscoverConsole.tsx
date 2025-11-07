import { useState } from 'react';
import { Search, Loader2, CheckCircle, AlertCircle, TrendingUp } from 'lucide-react';
import { aoaApi } from '../services/aoaApi';
import type { DiscoveryResponse, DiscoveredEntity, AgentRecommendation } from '../types';

export default function DiscoverConsole() {
  const [nlpQuery, setNlpQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [discoveryResult, setDiscoveryResult] = useState<DiscoveryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleDiscover = async () => {
    if (!nlpQuery.trim()) {
      setError('Please enter a query');
      return;
    }

    setIsLoading(true);
    setError(null);
    setDiscoveryResult(null);

    try {
      const result = await aoaApi.discover(nlpQuery);
      setDiscoveryResult(result);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Discovery failed';
      setError(errorMessage);
      console.error('[Discover] Error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleDiscover();
    }
  };

  const getConfidenceColor = (score: number) => {
    if (score >= 0.9) return 'text-green-400';
    if (score >= 0.7) return 'text-cyan-400';
    if (score >= 0.5) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'bg-red-500/20 text-red-400 border-red-500/30';
      case 'medium':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
      case 'low':
        return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
      default:
        return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
    }
  };

  return (
    <div className="bg-slate-800/40 rounded-xl border border-cyan-500/30 p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-xl flex items-center justify-center">
            <Search className="w-6 h-6 text-white" />
          </div>
          <div>
            <h3 className="text-2xl font-medium text-cyan-400">NLP Discovery Console</h3>
            <p className="text-sm text-gray-400">
              Discover entities and get agent recommendations using natural language
            </p>
          </div>
        </div>
      </div>

      {/* Input Section */}
      <div className="mb-6">
        <div className="flex gap-3">
          <input
            type="text"
            value={nlpQuery}
            onChange={(e) => setNlpQuery(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder='Try: "Find all opportunities related to cloud spending"'
            className="flex-1 bg-slate-900/60 border border-slate-700 rounded-lg px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500/50 transition-colors"
            disabled={isLoading}
          />
          <button
            onClick={handleDiscover}
            disabled={isLoading || !nlpQuery.trim()}
            className="px-6 py-3 bg-gradient-to-r from-cyan-500 to-blue-600 text-white rounded-lg font-medium hover:from-cyan-600 hover:to-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center gap-2"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Discovering...
              </>
            ) : (
              <>
                <Search className="w-5 h-5" />
                Discover
              </>
            )}
          </button>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="mb-6 bg-red-500/10 border border-red-500/30 rounded-lg p-4 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
          <div>
            <div className="text-red-400 font-medium mb-1">Discovery Error</div>
            <div className="text-sm text-red-300">{error}</div>
          </div>
        </div>
      )}

      {/* Results Section */}
      {discoveryResult && discoveryResult.success && (
        <div className="space-y-6">
          {/* Summary Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-700">
              <div className="text-sm text-slate-400 mb-1">Entities Found</div>
              <div className="text-2xl font-bold text-cyan-400">
                {discoveryResult.total_entities_found}
              </div>
            </div>
            <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-700">
              <div className="text-sm text-slate-400 mb-1">Agent Recommendations</div>
              <div className="text-2xl font-bold text-cyan-400">
                {discoveryResult.agent_recommendations.length}
              </div>
            </div>
            <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-700">
              <div className="text-sm text-slate-400 mb-1">Overall Confidence</div>
              <div className={`text-2xl font-bold ${getConfidenceColor(discoveryResult.overall_confidence)}`}>
                {(discoveryResult.overall_confidence * 100).toFixed(1)}%
              </div>
            </div>
            <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-700">
              <div className="text-sm text-slate-400 mb-1">Processing Time</div>
              <div className="text-2xl font-bold text-cyan-400">
                {discoveryResult.provenance.processing_time_ms.toFixed(0)}ms
              </div>
            </div>
          </div>

          {/* Agent Recommendations */}
          {discoveryResult.agent_recommendations.length > 0 && (
            <div>
              <h4 className="text-lg font-medium text-cyan-400 mb-3 flex items-center gap-2">
                <TrendingUp className="w-5 h-5" />
                Agent Recommendations
              </h4>
              <div className="space-y-3">
                {discoveryResult.agent_recommendations.map((agent: AgentRecommendation, idx: number) => (
                  <div
                    key={idx}
                    className="bg-slate-900/60 rounded-lg p-4 border border-slate-700 hover:border-cyan-500/50 transition-colors"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <h5 className="text-base font-medium text-white">{agent.agent_name}</h5>
                          <span className="text-xs text-slate-400 bg-slate-800 px-2 py-1 rounded">
                            {agent.agent_type}
                          </span>
                        </div>
                        <p className="text-sm text-slate-300 mb-2">{agent.reason}</p>
                      </div>
                      <div className="flex flex-col items-end gap-2">
                        <span className={`px-3 py-1 rounded border text-xs font-medium ${getPriorityColor(agent.priority)}`}>
                          {agent.priority.toUpperCase()}
                        </span>
                        <div className={`text-sm font-medium ${getConfidenceColor(agent.confidence_score)}`}>
                          {(agent.confidence_score * 100).toFixed(0)}% confidence
                        </div>
                      </div>
                    </div>
                    {agent.suggested_actions.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-slate-700">
                        <div className="text-xs text-slate-400 mb-2">Suggested Actions:</div>
                        <ul className="space-y-1">
                          {agent.suggested_actions.map((action, actionIdx) => (
                            <li key={actionIdx} className="text-sm text-slate-300 flex items-start gap-2">
                              <CheckCircle className="w-4 h-4 text-green-400 flex-shrink-0 mt-0.5" />
                              {action}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Discovered Entities */}
          {discoveryResult.entities.length > 0 && (
            <div>
              <h4 className="text-lg font-medium text-cyan-400 mb-3">Discovered Entities</h4>
              <div className="space-y-3">
                {discoveryResult.entities.map((entity: DiscoveredEntity, idx: number) => (
                  <div
                    key={idx}
                    className="bg-slate-900/60 rounded-lg p-4 border border-slate-700"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <h5 className="text-base font-medium text-white">{entity.entity_name}</h5>
                          <span className="text-xs text-slate-400 bg-slate-800 px-2 py-1 rounded">
                            {entity.entity_type}
                          </span>
                        </div>
                        <div className="text-sm text-slate-400">
                          Source: {entity.source_system}
                          {entity.source_schema && ` / ${entity.source_schema}`}
                        </div>
                      </div>
                      <div className={`text-sm font-medium ${getConfidenceColor(entity.confidence_score)}`}>
                        {(entity.confidence_score * 100).toFixed(0)}%
                      </div>
                    </div>
                    {Object.keys(entity.attributes).length > 0 && (
                      <div className="mt-3 pt-3 border-t border-slate-700">
                        <div className="text-xs text-slate-400 mb-2">Attributes:</div>
                        <div className="grid grid-cols-2 gap-2">
                          {Object.entries(entity.attributes).slice(0, 6).map(([key, value]) => (
                            <div key={key} className="text-sm">
                              <span className="text-slate-500">{key}:</span>{' '}
                              <span className="text-slate-300">{String(value)}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Provenance Info */}
          <div className="bg-slate-900/30 rounded-lg p-4 border border-slate-700">
            <div className="text-xs text-slate-400 mb-2">Discovery Provenance</div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-slate-500">Method:</span>{' '}
                <span className="text-slate-300">{discoveryResult.provenance.discovery_method}</span>
              </div>
              {discoveryResult.provenance.llm_model && (
                <div>
                  <span className="text-slate-500">LLM:</span>{' '}
                  <span className="text-slate-300">{discoveryResult.provenance.llm_model}</span>
                </div>
              )}
              <div>
                <span className="text-slate-500">Request ID:</span>{' '}
                <span className="text-slate-300 font-mono text-xs">{discoveryResult.request_id}</span>
              </div>
              <div>
                <span className="text-slate-500">Timestamp:</span>{' '}
                <span className="text-slate-300">{new Date(discoveryResult.timestamp).toLocaleTimeString()}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Empty State */}
      {!discoveryResult && !error && !isLoading && (
        <div className="text-center py-12 text-slate-500">
          <Search className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>Enter a natural language query to discover entities and get agent recommendations</p>
        </div>
      )}
    </div>
  );
}
