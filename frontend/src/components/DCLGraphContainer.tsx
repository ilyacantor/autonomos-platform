import React from 'react';
import { Activity, ChevronDown, Play, X, CheckCircle } from 'lucide-react';
import { useState, useEffect } from 'react';
import type { AgentNode, DCLStats, MappingReview, SchemaChange } from '../types';
import LiveSankeyGraph from './LiveSankeyGraph';
import { useDCLState } from '../hooks/useDCLState';
import TypingText from './TypingText';
import { aoaApi } from '../services/aoaApi';
import { AUTH_TOKEN_KEY, API_CONFIG } from '../config/api';
import { getDefaultSources, getDefaultAgents } from '../config/dclDefaults';

interface DCLGraphContainerProps {
  mappings: MappingReview[];
  schemaChanges: SchemaChange[];
}

export default function DCLGraphContainer({ mappings, schemaChanges }: DCLGraphContainerProps) {
  const [activeTab, setActiveTab] = useState<'review' | 'schema'>('review');
  const [devMode, setDevMode] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [showProgress, setShowProgress] = useState(false); // Separate flag to control progress bar visibility
  const [selectedMapping, setSelectedMapping] = useState<MappingReview | null>(null);
  const { state: dclState } = useDCLState();
  const [typingEvents, setTypingEvents] = useState<Array<{ text: string; isTyping: boolean; key: string }>>([]);
  const [selectedModel, setSelectedModel] = useState('gemini-2.5-flash');
  
  // Timer and progress state
  const [elapsedTime, setElapsedTime] = useState(0);
  const [progress, setProgress] = useState(0);
  const [timerStarted, setTimerStarted] = useState(false);

  // Get persisted selections from localStorage, fallback to all sources/agents
  // Ensures we never send empty query params to backend
  const getPersistedSources = () => {
    const defaultSources = getDefaultSources();
    // getDefaultSources always returns non-empty array (fallback to all sources)
    return defaultSources.join(',');
  };
  
  const getPersistedAgents = () => {
    const defaultAgents = getDefaultAgents();
    // getDefaultAgents always returns non-empty array (fallback to all agents)
    return defaultAgents.join(',');
  };

  // Sync dev mode from backend state
  useEffect(() => {
    if (dclState) {
      setDevMode(dclState.dev_mode || false);
    }
  }, [dclState?.dev_mode]);

  // Listen for connection-triggered run events from ConnectionsPage
  useEffect(() => {
    const handleTriggerRun = (event: Event) => {
      const customEvent = event as CustomEvent;
      const source = customEvent.detail?.source;
      console.log(`[DCL] Received trigger-run event from: ${source}`);
      
      // Trigger run with progress bar
      if (!isProcessing) {
        handleRun();
      }
    };

    window.addEventListener('dcl:trigger-run', handleTriggerRun);
    return () => {
      window.removeEventListener('dcl:trigger-run', handleTriggerRun);
    };
  }, [isProcessing]);

  // Track new events and animate them with typing effect
  useEffect(() => {
    if (!dclState) return;
    
    const eventsChanged = dclState.events.length !== typingEvents.length || 
      dclState.events.some((event, idx) => typingEvents[idx]?.text !== event);
    
    if (eventsChanged) {
      if (dclState.events.length === 0) {
        setTypingEvents([]);
      } else {
        setTypingEvents(dclState.events.map((event, idx) => ({
          text: event,
          isTyping: idx === dclState.events.length - 1,
          key: `${idx}-${event.substring(0, 20)}-${Date.now()}`
        })));
      }
    }
  }, [dclState?.events, typingEvents]);

  // Auto-run graph on page load to display all nodes, sources, and agents
  // Note: showProgress remains false during auto-run at mount
  useEffect(() => {
    if (!dclState) return;
    
    // Check if graph is empty (no nodes) and we haven't run yet
    const hasNodes = dclState.graph?.nodes && dclState.graph.nodes.length > 0;
    
    if (!hasNodes && !isProcessing) {
      // Auto-run the mapping to populate the graph (background operation - no progress bar)
      const autoRun = async () => {
        setIsProcessing(true);
        // showProgress stays false - no visual indicator for auto-run
        try {
          const sources = getPersistedSources();
          const agents = getPersistedAgents();
          await fetch(API_CONFIG.buildDclUrl(`/connect?sources=${sources}&agents=${agents}&llm_model=${selectedModel}`));
          // Notify graph to update (event-driven)
          window.dispatchEvent(new Event('dcl-state-changed'));
        } catch (error) {
          console.error('Error auto-running graph:', error);
        } finally {
          setTimeout(() => setIsProcessing(false), 1500);
        }
      };
      autoRun();
    }
  }, [dclState, isProcessing]);

  // Timer effect - tracks elapsed time during processing
  useEffect(() => {
    let interval: NodeJS.Timeout;
    
    if (timerStarted && isProcessing) {
      interval = setInterval(() => {
        setElapsedTime(prev => prev + 0.1);
      }, 100);
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [timerStarted, isProcessing]);

  // Progress simulation effect - incremental progress during processing
  useEffect(() => {
    let progressInterval: NodeJS.Timeout;
    
    if (isProcessing && showProgress) {
      setProgress(0);
      let currentProgress = 0;
      
      progressInterval = setInterval(() => {
        // Simulate realistic progress: fast start, slower end
        if (currentProgress < 30) {
          currentProgress += 2;
        } else if (currentProgress < 60) {
          currentProgress += 1;
        } else if (currentProgress < 90) {
          currentProgress += 0.5;
        } else if (currentProgress < 95) {
          currentProgress += 0.2;
        }
        
        setProgress(Math.min(currentProgress, 95)); // Cap at 95% until actually complete
      }, 100);
    } else if (!isProcessing && progress > 0 && progress < 100) {
      // Complete to 100% when done and KEEP IT
      setProgress(100);
    }
    
    return () => {
      if (progressInterval) clearInterval(progressInterval);
    };
  }, [isProcessing, showProgress, progress]);

  // Run - calls /connect with persisted sources, agents, and selected LLM model
  // Shows progress bar for manual user-triggered runs
  const handleRun = async () => {
    // Reset timer and progress on NEW run
    setElapsedTime(0);
    setProgress(0);
    setTimerStarted(true);
    setIsProcessing(true);
    setShowProgress(true); // Enable progress bar for manual runs
    
    try {
      const sources = getPersistedSources();
      const agents = getPersistedAgents();
      const response = await fetch(API_CONFIG.buildDclUrl(`/connect?sources=${sources}&agents=${agents}&llm_model=${selectedModel}`));
      await response.json();
      // Notify graph to update (event-driven)
      window.dispatchEvent(new Event('dcl-state-changed'));
    } catch (error) {
      console.error('Error running:', error);
    } finally {
      setTimeout(() => {
        setIsProcessing(false);
        // Keep timer and progress visible with final values (don't hide)
      }, 1500);
    }
  };

  // Toggle dev mode handler
  const handleToggleDevMode = async () => {
    try {
      const newMode = !devMode;
      const response = await fetch(API_CONFIG.buildDclUrl(`/toggle_dev_mode?enabled=${newMode}`));
      const data = await response.json();
      setDevMode(data.dev_mode);
      // Notify graph to update
      window.dispatchEvent(new Event('dcl-state-changed'));
    } catch (error) {
      console.error('Error toggling dev mode:', error);
    }
  };

  return (
    <div className="bg-black border-t border-b border-cyan-500/30 py-12 -mx-6 px-6">
      {/* Top-Mounted Progress Bar - Shows only for manual/connection-triggered runs */}
      {showProgress && (
        <div className="relative -mx-6 -mt-12 mb-4 h-4 bg-gray-900 overflow-hidden">
          {/* Actual progress bar */}
          <div 
            className="absolute left-0 top-0 h-full bg-gradient-to-r from-emerald-500 via-teal-500 to-cyan-500 transition-all duration-300 ease-out"
            style={{ width: `${progress}%` }}
          />
          {/* Shimmer effect on progress */}
          <div 
            className="absolute left-0 top-0 h-full bg-gradient-to-r from-transparent via-white/20 to-transparent"
            style={{ 
              width: `${progress}%`,
              animation: 'shimmer 1.5s linear infinite',
              backgroundSize: '200% 100%'
            }} 
          />
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-white text-[10px] font-semibold tracking-wide drop-shadow-lg">
              {Math.round(progress)}% Complete
            </span>
          </div>
        </div>
      )}
      
      {/* Title */}
      <div className="mb-8">
        <h2 
          className="text-3xl font-semibold text-cyan-400 cursor-help uppercase" 
          title="The Data Connectivity Layer (DCL) links heterogeneous data sources without migrations or ETL. It maps entities to a unified ontology for domain agents to act on."
        >
          Live Data Connectivity Layer (DCL)
        </h2>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-4 lg:gap-6">
        <div className="flex flex-col">
          <div className="relative w-full bg-gradient-to-br from-blue-900/20 to-purple-900/20 rounded-lg border border-blue-500/30 p-2 sm:p-3 backdrop-blur-sm mb-4">
            <div className="absolute inset-0 bg-blue-500/5 rounded-lg animate-pulse" />

            <div className="relative z-10 flex flex-col sm:flex-row items-start sm:items-center gap-2 sm:gap-3">
              <div className="w-8 h-8 sm:w-10 sm:h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center shadow-lg shadow-blue-500/50 flex-shrink-0">
                <Activity className="w-4 h-4 sm:w-5 sm:h-5 text-white animate-pulse" />
              </div>

              <div className="flex-1 w-full sm:w-auto">
                <div className="flex flex-col sm:flex-row items-start sm:items-center sm:justify-between gap-2 mb-2 sm:mb-1">
                  <h3 className="text-xs sm:text-sm font-semibold text-white">
                    Intelligent Mapping & Ontology Engine
                  </h3>
                  <div className="flex items-center gap-2 w-full sm:w-auto">
                    {/* LLM Model Selector */}
                    <select
                      value={selectedModel}
                      onChange={(e) => setSelectedModel(e.target.value)}
                      disabled={isProcessing}
                      className="px-2 py-1 bg-gray-800 border border-gray-700 rounded text-[10px] text-white focus:outline-none focus:border-blue-500 hover:border-gray-600 transition-colors disabled:opacity-50 cursor-pointer"
                      title="Select LLM model for intelligent mapping"
                    >
                      <option value="gemini-2.5-flash">Gemini 2.5 Flash</option>
                      <option value="gpt-5-mini">GPT-5 mini ⚡</option>
                      <option value="gpt-5-nano">GPT-5 nano 🚀</option>
                    </select>
                    
                    {/* Run Button */}
                    <button
                      onClick={handleRun}
                      disabled={isProcessing}
                      className="flex items-center gap-1.5 px-3 sm:px-2 py-2 sm:py-1 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 rounded-md text-xs sm:text-[10px] font-semibold text-white shadow-lg shadow-emerald-500/30 transition-all disabled:opacity-50 justify-center"
                    >
                      {isProcessing ? (
                        <>
                          <svg className="animate-spin h-3 w-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                          Processing...
                        </>
                      ) : (
                        <>
                          <Play className="w-3 h-3" />
                          Run
                        </>
                      )}
                    </button>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2 sm:gap-4 text-[10px] sm:text-[10px] text-blue-300">
                  <div className="flex items-center gap-1">
                    <div className={`w-1.5 h-1.5 rounded-full ${devMode ? 'bg-purple-400 animate-pulse' : 'bg-gray-500'}`} />
                    <span>LLM Calls: {dclState?.llm?.calls || 0}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Activity className="w-3 h-3 text-blue-400" />
                    <span className="whitespace-nowrap">9 sources → 2 agents</span>
                  </div>
                  {(timerStarted || elapsedTime > 0) && (
                    <div className="flex items-center gap-1 bg-blue-900/30 px-2 py-0.5 rounded">
                      <svg className="w-3 h-3 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <span className="font-mono">{elapsedTime.toFixed(1)}s</span>
                    </div>
                  )}
                </div>

                {/* Dev Mode / Prod Mode Toggle */}
                <div className="mt-2 pt-2 border-t border-blue-500/20">
                  <button
                    onClick={handleToggleDevMode}
                    className={`w-full flex items-center justify-between px-3 py-1.5 rounded-md text-[11px] font-semibold transition-all ${
                      devMode
                        ? 'bg-amber-600/20 border border-amber-500/40 text-amber-300 hover:bg-amber-600/30'
                        : 'bg-emerald-600/20 border border-emerald-500/40 text-emerald-300 hover:bg-emerald-600/30'
                    }`}
                    title="Toggle between Production Mode (heuristics only) and Dev Mode (AI + RAG active)"
                  >
                    <div className="flex items-center gap-2">
                      <div className={`w-2 h-2 rounded-full ${devMode ? 'bg-amber-400 animate-pulse' : 'bg-emerald-400'}`} />
                      <span>{devMode ? 'Dev Mode' : 'Prod Mode'}</span>
                    </div>
                    <span className="text-[9px] opacity-70">
                      {devMode ? 'AI/RAG Active' : 'Heuristics Only'}
                    </span>
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Graph Container */}
          <div className="relative">
            <LiveSankeyGraph />
            
            {/* Center Description Text Overlay */}
            <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-center px-4 pointer-events-none">
              <p className="text-white text-xl font-semibold max-w-md leading-relaxed">
                Provides persistent, versioned data mappings so AI agents can reason with consistent, validated inputs.
              </p>
            </div>
            
            {/* Robot Agents at Bottom */}
            <div className="flex items-end justify-center gap-8 mt-6">
              <img 
                src="/assets/robot-agent-1.jpg" 
                alt="AI Agent 1"
                className="h-48 w-auto object-contain"
              />
              <img 
                src="/assets/robot-agent-2.jpg" 
                alt="AI Agent 2"
                className="h-48 w-auto object-contain"
              />
            </div>
            
            {/* Try it now CTA */}
            <div className="text-center mt-6">
              <p className="text-white text-2xl font-semibold">
                Try it now &gt;&gt;&gt;
              </p>
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-4">
          {/* Narration Panel with Typing Animation - MOVED TO TOP FOR PROMINENCE */}
          <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-4 flex-1">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-6 h-6 rounded-full bg-purple-500 flex items-center justify-center text-white text-xs font-bold">
                📝
              </div>
              <span 
                className="text-white font-bold text-sm cursor-help" 
                title="Chronological event log showing every decision, mapping, and execution step. Functions as a transparent, auditable trail of autonomous system behavior."
              >
                Narration
              </span>
              <span className="ml-auto text-xs bg-purple-600 text-white px-2 py-0.5 rounded-full font-bold">
                {dclState?.events.length || 0} events
              </span>
            </div>
            <div className="text-xs space-y-1 overflow-y-auto max-h-[400px]">
              {typingEvents.length === 0 ? (
                <div className="text-gray-500 italic text-[11px]">
                  No events yet. Start mapping to see the narration.
                </div>
              ) : (
                typingEvents.map((event, idx) => (
                  <div key={event.key} className="text-gray-300 leading-relaxed">
                    <span className="text-purple-400 font-bold mr-1">[{idx + 1}]</span>
                    {event.isTyping ? <TypingText text={event.text} speed={30} /> : event.text}
                  </div>
                ))
              )}
            </div>
          </div>

          {/* RAG Learning Engine - EXACT LEGACY LAYOUT */}
          <div className="rounded-lg p-4 bg-gradient-to-br from-teal-950 to-cyan-950 border border-teal-700/30">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-6 h-6 rounded-full bg-teal-500 flex items-center justify-center text-white text-xs font-bold">
                🧠
              </div>
              <span 
                className="text-white font-bold text-sm cursor-help" 
                title="Retrieval-Augmented Generation (RAG) component that enriches context for agent reasoning. It stores embeddings, retrieves related knowledge, and continuously self-tunes mappings."
              >
                RAG Learning Engine
              </span>
              <span className="ml-auto text-xs bg-teal-600 text-white px-2 py-0.5 rounded-full font-bold">
                {dclState?.rag?.total_mappings || 0} stored
              </span>
            </div>
            <div className="text-xs space-y-2 overflow-y-scroll overflow-x-hidden min-h-[150px] max-h-[400px]">
              {!dclState?.rag?.retrievals || dclState.rag.retrievals.length === 0 ? (
                <div className="text-teal-300/70 italic text-[11px]">
                  No context retrieved yet. Connect a source to see RAG retrieve historical mappings.
                </div>
              ) : (
                <>
                  <div className="text-white font-semibold mb-2 text-[11px]">
                    Retrieved {dclState.rag.last_retrieval_count} similar mappings:
                  </div>
                  {dclState.rag.retrievals.map((ret: any, i: number) => (
                    <div key={i} className="mb-2 pb-2 border-b border-teal-800/30 last:border-0">
                      <div className="flex justify-between items-start mb-1">
                        <div className="text-white font-semibold text-[11px]">{ret.source_field}</div>
                        <div className="text-[10px] text-white font-bold">
                          {(ret.similarity * 100).toFixed(0)}%
                        </div>
                      </div>
                      <div className="text-teal-300 text-[10px] mb-1">→ {ret.ontology_entity}</div>
                      <div className="w-full bg-slate-900/50 rounded-sm h-1.5 overflow-hidden mb-1">
                        <div
                          className="h-full bg-gradient-to-r from-teal-500 to-cyan-400 transition-all"
                          style={{ width: `${(ret.similarity * 100).toFixed(0)}%` }}
                        />
                      </div>
                      <div className="text-[9px] text-teal-400/70">from: {ret.source_system || 'unknown'}</div>
                    </div>
                  ))}
                </>
              )}
            </div>
          </div>

          {/* Intelligence Review Panel - MOVED TO BOTTOM */}
          <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-6 h-6 rounded-full bg-orange-600 flex items-center justify-center text-white text-xs font-bold">
                🤖
              </div>
              <span 
                className="text-white font-bold text-sm cursor-help" 
                title="Aggregates flagged data quality or mapping anomalies for human or agentic review before execution. Supports auto-correction and retraining triggers."
              >
                Intelligence Review
              </span>
            </div>

            <div className="flex gap-2 mb-3">
              <button
                onClick={() => setActiveTab('review')}
                className={`flex-1 px-2 py-1 text-[11px] font-medium rounded transition-colors ${
                  activeTab === 'review'
                    ? 'bg-orange-600 text-white'
                    : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                }`}
              >
                Review ({mappings.length})
              </button>
              <button
                onClick={() => setActiveTab('schema')}
                className={`flex-1 px-2 py-1 text-[11px] font-medium rounded transition-colors ${
                  activeTab === 'schema'
                    ? 'bg-orange-600 text-white'
                    : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                }`}
              >
                Schema Log ({schemaChanges.length})
              </button>
            </div>

            <div className="text-xs space-y-2 overflow-y-auto max-h-[350px]">
              {activeTab === 'review' ? (
                <div className="space-y-2">
                  {mappings.map((mapping) => (
                    <div key={mapping.id} className="p-2 bg-gray-900 rounded border border-gray-700">
                      <div className="flex items-start justify-between mb-1">
                        <div className="flex-1 min-w-0">
                          <div className="text-blue-400 font-mono text-[10px] truncate">
                            {mapping.sourceField}
                          </div>
                          <div className="text-green-400 font-mono text-[10px] mt-1 truncate">
                            → {mapping.unifiedField}
                          </div>
                        </div>
                        <div
                          className={`ml-2 px-1.5 py-0.5 rounded text-[9px] font-bold flex-shrink-0 ${
                            mapping.confidence >= 80
                              ? 'bg-green-500/20 text-green-400'
                              : mapping.confidence >= 60
                              ? 'bg-orange-500/20 text-orange-400'
                              : 'bg-red-500/20 text-red-400'
                          }`}
                        >
                          {mapping.confidence}%
                        </div>
                      </div>
                      <button
                        onClick={() => setSelectedMapping(mapping)}
                        className="mt-2 w-full px-2 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-[11px] font-medium rounded transition-colors"
                      >
                        Review
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="space-y-2">
                  {schemaChanges.map((change) => (
                    <div key={change.id} className="p-2 bg-gray-900 rounded border border-gray-700">
                      <div className="flex items-center gap-2 mb-1">
                        <span
                          className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
                            change.changeType === 'added'
                              ? 'bg-green-500/20 text-green-400'
                              : change.changeType === 'modified'
                              ? 'bg-blue-500/20 text-blue-400'
                              : 'bg-red-500/20 text-red-400'
                          }`}
                        >
                          {change.changeType.toUpperCase()}
                        </span>
                        <span className="text-gray-400 text-[10px] font-mono">{change.source}</span>
                      </div>
                      <div className="text-[10px] text-gray-300">{change.field}</div>
                      <div className="text-[9px] text-gray-500 mt-1">
                        {new Date(change.timestamp).toLocaleString()}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Review Mapping Modal - Mobile Friendly */}
      {selectedMapping && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-2 sm:p-4">
          <div className="bg-gray-900 rounded-xl border border-gray-700 max-w-4xl w-full max-h-[95vh] sm:max-h-[90vh] overflow-auto">
            <div className="sticky top-0 bg-gray-900 border-b border-gray-700 p-4 sm:p-6 flex items-center justify-between">
              <h3 className="text-lg sm:text-xl font-semibold text-white">Review Mapping</h3>
              <button
                onClick={() => setSelectedMapping(null)}
                className="p-2 sm:p-2 hover:bg-gray-800 rounded-lg transition-colors min-w-[44px] min-h-[44px] sm:min-w-0 sm:min-h-0 flex items-center justify-center"
                aria-label="Close modal"
              >
                <X className="w-5 h-5 sm:w-5 sm:h-5 text-gray-400" />
              </button>
            </div>

            <div className="p-4 sm:p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6 mb-4 sm:mb-6">
                <div>
                  <h4 className="text-xs sm:text-sm font-semibold text-gray-400 mb-2 sm:mb-3 uppercase tracking-wider">
                    Source Data Snippet
                  </h4>
                  <div className="bg-gray-800 rounded-lg p-3 sm:p-4 border border-gray-700">
                    <pre className="text-xs text-green-400 font-mono overflow-x-auto">
                      {selectedMapping.sourceSample}
                    </pre>
                  </div>
                  <div className="mt-3 sm:mt-4">
                    <div className="text-xs sm:text-sm text-gray-400 mb-1">Source Field</div>
                    <div className="text-sm sm:text-base text-blue-400 font-mono break-all">
                      {selectedMapping.sourceField}
                    </div>
                  </div>
                </div>

                <div>
                  <h4 className="text-xs sm:text-sm font-semibold text-gray-400 mb-2 sm:mb-3 uppercase tracking-wider">
                    Proposed Unified Mapping
                  </h4>
                  <div className="bg-gray-800 rounded-lg p-3 sm:p-4 border border-gray-700 mb-3 sm:mb-4">
                    <div className="text-xs sm:text-sm text-gray-400 mb-2">Unified Entity & Field</div>
                    <div className="text-base sm:text-lg text-green-400 font-mono break-all">
                      {selectedMapping.unifiedField}
                    </div>
                    <div className="mt-3 sm:mt-4 pt-3 sm:pt-4 border-t border-gray-700">
                      <div className="text-xs sm:text-sm text-gray-400 mb-1">Confidence Score</div>
                      <div className="flex items-center gap-3">
                        <div className="flex-1 h-2 bg-gray-700 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-orange-500 to-orange-400"
                            style={{ width: `${selectedMapping.confidence}%` }}
                          />
                        </div>
                        <span className="text-orange-400 font-semibold">{selectedMapping.confidence}%</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="mb-4 sm:mb-6">
                <h4 className="text-xs sm:text-sm font-semibold text-gray-400 mb-2 sm:mb-3 uppercase tracking-wider">
                  LLM Reasoning
                </h4>
                <div className="bg-gray-800 rounded-lg p-3 sm:p-4 border border-gray-700">
                  <p className="text-xs sm:text-sm text-gray-300 leading-relaxed">
                    {selectedMapping.llmReasoning}
                  </p>
                </div>
              </div>

              <div className="flex flex-col sm:flex-row gap-2 sm:gap-3">
                <button
                  onClick={() => {
                    console.log('Approved:', selectedMapping.id);
                    setSelectedMapping(null);
                  }}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-3 sm:py-3 bg-green-600 hover:bg-green-700 active:bg-green-800 text-white font-medium rounded-lg transition-colors min-h-[48px] sm:min-h-0"
                >
                  <CheckCircle className="w-5 h-5" />
                  <span className="text-sm sm:text-base">Approve</span>
                </button>
                <button
                  onClick={() => {
                    console.log('Editing:', selectedMapping.id);
                  }}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-3 sm:py-3 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-medium rounded-lg transition-colors min-h-[48px] sm:min-h-0"
                >
                  <span className="text-sm sm:text-base">Edit Mapping</span>
                </button>
                <button
                  onClick={() => {
                    console.log('Ignored:', selectedMapping.id);
                    setSelectedMapping(null);
                  }}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-3 sm:py-3 bg-gray-700 hover:bg-gray-600 active:bg-gray-800 text-white font-medium rounded-lg transition-colors min-h-[48px] sm:min-h-0"
                >
                  <X className="w-5 h-5" />
                  <span className="text-sm sm:text-base">Ignore & Flag</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
