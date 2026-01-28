import { useState, useEffect } from 'react';
import { Send, Loader2, Database, Users, TrendingUp, DollarSign, Activity, Bot, RefreshCw } from 'lucide-react';
import DemoStep from './DemoStep';
import { API_CONFIG } from '../config/api';

interface GraphNode {
  id: string;
  label: string;
  type: string;
  metadata?: Record<string, any>;
}

interface GraphEdge {
  source: string;
  target: string;
  relationship: string;
}

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  summary: {
    total_sources?: number;
    total_entities?: number;
    total_agents?: number;
    records_unified?: number;
    confidence_score?: number;
    last_sync?: string;
  };
  source: string;
}

interface QueryResponse {
  question: string;
  persona: string;
  intent: string;
  answer: string;
  confidence: number;
  entities_referenced: string[];
  source: string;
}

const PERSONA_OPTIONS = [
  { value: 'CFO', label: 'CFO (Finance)', icon: DollarSign, color: 'text-green-400' },
  { value: 'CRO', label: 'CRO (Revenue)', icon: TrendingUp, color: 'text-blue-400' },
  { value: 'general', label: 'General', icon: Bot, color: 'text-purple-400' },
];

function getNodeIcon(type: string) {
  switch (type) {
    case 'source':
      return <Database className="w-4 h-4" />;
    case 'ontology':
      return <Activity className="w-4 h-4" />;
    case 'agent':
      return <Bot className="w-4 h-4" />;
    default:
      return <Database className="w-4 h-4" />;
  }
}

function getNodeColor(type: string) {
  switch (type) {
    case 'source':
      return 'bg-blue-500/20 border-blue-500/40 text-blue-400';
    case 'ontology':
      return 'bg-purple-500/20 border-purple-500/40 text-purple-400';
    case 'agent':
      return 'bg-green-500/20 border-green-500/40 text-green-400';
    default:
      return 'bg-gray-500/20 border-gray-500/40 text-gray-400';
  }
}

export default function UnifyAskPage() {
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [isLoadingGraph, setIsLoadingGraph] = useState(true);
  const [graphError, setGraphError] = useState<string | null>(null);
  
  const [question, setQuestion] = useState('');
  const [selectedPersona, setSelectedPersona] = useState('general');
  const [isQuerying, setIsQuerying] = useState(false);
  const [queryResponse, setQueryResponse] = useState<QueryResponse | null>(null);
  const [queryError, setQueryError] = useState<string | null>(null);

  const fetchGraph = async () => {
    setIsLoadingGraph(true);
    setGraphError(null);
    try {
      const response = await fetch(API_CONFIG.buildApiUrl('/demo/dcl/graph'));
      if (!response.ok) throw new Error('Failed to fetch graph');
      const data = await response.json();
      setGraphData(data);
    } catch (err) {
      setGraphError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoadingGraph(false);
    }
  };

  useEffect(() => {
    fetchGraph();
  }, []);

  const handleQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;

    setIsQuerying(true);
    setQueryError(null);
    try {
      const response = await fetch(API_CONFIG.buildApiUrl('/demo/dcl/query'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, persona: selectedPersona }),
      });
      if (!response.ok) throw new Error('Query failed');
      const data = await response.json();
      setQueryResponse(data);
    } catch (err) {
      setQueryError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsQuerying(false);
    }
  };

  const sourceNodes = graphData?.nodes.filter(n => n.type === 'source') || [];
  const ontologyNodes = graphData?.nodes.filter(n => n.type === 'ontology') || [];
  const agentNodes = graphData?.nodes.filter(n => n.type === 'agent') || [];

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <DemoStep
        stepNumber={3}
        title="Data Connectivity Layer (DCL)"
        description="Your data is unified into a canonical ontology. Ask questions in natural language and get answers powered by AI."
        instructions="Select a persona (CFO, CRO) to get role-specific insights, then ask a question about your unified data."
      >
        <div className="h-full overflow-auto p-3 sm:p-4 lg:p-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 lg:gap-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">Canonical Graph</h3>
                <button
                  onClick={fetchGraph}
                  disabled={isLoadingGraph}
                  className="p-1.5 rounded-lg bg-gray-700/50 hover:bg-gray-700 text-gray-400 hover:text-white transition-colors disabled:opacity-50"
                >
                  <RefreshCw className={`w-4 h-4 ${isLoadingGraph ? 'animate-spin' : ''}`} />
                </button>
              </div>

              {isLoadingGraph ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-8 h-8 text-cyan-400 animate-spin" />
                </div>
              ) : graphError ? (
                <div className="text-red-400 text-sm bg-red-900/20 border border-red-500/30 rounded-lg p-3">
                  {graphError}
                </div>
              ) : graphData ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-3 gap-2 sm:gap-3">
                    <div className="bg-blue-900/20 border border-blue-500/30 rounded-lg p-2 sm:p-3 text-center">
                      <div className="text-xl sm:text-2xl font-bold text-blue-400">{graphData.summary.total_sources || sourceNodes.length}</div>
                      <div className="text-xs text-gray-400">Sources</div>
                    </div>
                    <div className="bg-purple-900/20 border border-purple-500/30 rounded-lg p-2 sm:p-3 text-center">
                      <div className="text-xl sm:text-2xl font-bold text-purple-400">{graphData.summary.total_entities || ontologyNodes.length}</div>
                      <div className="text-xs text-gray-400">Entities</div>
                    </div>
                    <div className="bg-green-900/20 border border-green-500/30 rounded-lg p-2 sm:p-3 text-center">
                      <div className="text-xl sm:text-2xl font-bold text-green-400">{graphData.summary.total_agents || agentNodes.length}</div>
                      <div className="text-xs text-gray-400">Agents</div>
                    </div>
                  </div>

                  {graphData.summary.records_unified && (
                    <div className="bg-cyan-900/20 border border-cyan-500/30 rounded-lg p-3 flex items-center justify-between">
                      <span className="text-sm text-gray-300">Records Unified</span>
                      <span className="text-lg font-bold text-cyan-400">{graphData.summary.records_unified.toLocaleString()}</span>
                    </div>
                  )}

                  <div className="space-y-3">
                    <div>
                      <h4 className="text-xs font-medium text-blue-400 mb-2">Data Sources</h4>
                      <div className="flex flex-wrap gap-2">
                        {sourceNodes.map(node => (
                          <div key={node.id} className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs border ${getNodeColor('source')}`}>
                            {getNodeIcon('source')}
                            {node.label}
                          </div>
                        ))}
                      </div>
                    </div>

                    <div>
                      <h4 className="text-xs font-medium text-purple-400 mb-2">Canonical Entities</h4>
                      <div className="flex flex-wrap gap-2">
                        {ontologyNodes.map(node => (
                          <div key={node.id} className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs border ${getNodeColor('ontology')}`}>
                            {getNodeIcon('ontology')}
                            {node.label}
                          </div>
                        ))}
                      </div>
                    </div>

                    <div>
                      <h4 className="text-xs font-medium text-green-400 mb-2">Active Agents</h4>
                      <div className="flex flex-wrap gap-2">
                        {agentNodes.map(node => (
                          <div key={node.id} className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs border ${getNodeColor('agent')}`}>
                            {getNodeIcon('agent')}
                            {node.label}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  {graphData.source === 'stub' && (
                    <div className="text-xs text-amber-400/70 bg-amber-900/20 border border-amber-500/30 rounded-lg px-3 py-2">
                      Demo mode: showing sample data. Connect DCL v2 for live data.
                    </div>
                  )}
                </div>
              ) : null}
            </div>

            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">Ask Your Data</h3>

              <form onSubmit={handleQuery} className="space-y-3">
                <div className="flex flex-wrap gap-2">
                  {PERSONA_OPTIONS.map(persona => {
                    const Icon = persona.icon;
                    return (
                      <button
                        key={persona.value}
                        type="button"
                        onClick={() => setSelectedPersona(persona.value)}
                        className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                          selectedPersona === persona.value
                            ? 'bg-cyan-600/30 border-cyan-500/60 text-cyan-300'
                            : 'bg-gray-700/30 border-gray-600/40 text-gray-400 hover:border-gray-500/60 hover:text-gray-300'
                        }`}
                      >
                        <Icon className={`w-3.5 h-3.5 ${persona.color}`} />
                        {persona.label}
                      </button>
                    );
                  })}
                </div>

                <div className="relative">
                  <textarea
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    placeholder="Ask a question about your unified data..."
                    className="w-full h-24 sm:h-28 bg-gray-900/50 border border-gray-600/40 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500/50 resize-none"
                  />
                  <button
                    type="submit"
                    disabled={isQuerying || !question.trim()}
                    className="absolute bottom-2 right-2 p-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {isQuerying ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Send className="w-4 h-4" />
                    )}
                  </button>
                </div>

                <div className="flex flex-wrap gap-1.5 text-xs text-gray-500">
                  <span>Try:</span>
                  <button
                    type="button"
                    onClick={() => setQuestion('What is my current MRR and churn risk?')}
                    className="text-cyan-400/70 hover:text-cyan-400 underline"
                  >
                    "What is my current MRR?"
                  </button>
                  <span>or</span>
                  <button
                    type="button"
                    onClick={() => setQuestion('Show me pipeline analysis')}
                    className="text-cyan-400/70 hover:text-cyan-400 underline"
                  >
                    "Pipeline analysis"
                  </button>
                </div>
              </form>

              {queryError && (
                <div className="text-red-400 text-sm bg-red-900/20 border border-red-500/30 rounded-lg p-3">
                  {queryError}
                </div>
              )}

              {queryResponse && (
                <div className="bg-gray-900/50 border border-gray-600/40 rounded-lg overflow-hidden">
                  <div className="bg-gradient-to-r from-cyan-900/30 to-purple-900/30 border-b border-gray-600/40 px-3 py-2 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Bot className="w-4 h-4 text-cyan-400" />
                      <span className="text-sm font-medium text-white">AI Response</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-gray-400">Confidence:</span>
                      <span className={`text-xs font-medium ${
                        queryResponse.confidence >= 0.9 ? 'text-green-400' :
                        queryResponse.confidence >= 0.7 ? 'text-yellow-400' : 'text-red-400'
                      }`}>
                        {Math.round(queryResponse.confidence * 100)}%
                      </span>
                    </div>
                  </div>
                  <div className="p-3 space-y-3">
                    <p className="text-sm text-gray-200 leading-relaxed">{queryResponse.answer}</p>
                    
                    <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-gray-700/50">
                      <span className="text-xs text-gray-500">Referenced:</span>
                      {queryResponse.entities_referenced.map(entity => (
                        <span key={entity} className="px-2 py-0.5 rounded-full text-xs bg-purple-500/20 border border-purple-500/40 text-purple-300">
                          {entity}
                        </span>
                      ))}
                    </div>

                    {queryResponse.source === 'stub' && (
                      <div className="text-xs text-amber-400/70 italic">
                        Demo response (DCL v2 not connected)
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </DemoStep>
    </div>
  );
}
