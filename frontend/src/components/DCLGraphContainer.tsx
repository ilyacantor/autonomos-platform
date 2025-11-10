import React from 'react';
import { Activity, ChevronDown, Play, X, CheckCircle } from 'lucide-react';
import { useState, useEffect } from 'react';
import type { AgentNode, DCLStats, MappingReview, SchemaChange } from '../types';
import LazyGraphShell from './LazyGraphShell';
import { useDCLState } from '../hooks/useDCLState';
import TypingText from './TypingText';
import { aoaApi } from '../services/aoaApi';
import { AUTH_TOKEN_KEY, API_CONFIG } from '../config/api';
import { getDefaultSources, getDefaultAgents, getAamSourceValues, getAllSourceValues } from '../config/dclDefaults';

export default function DCLGraphContainer() {
  const [devMode, setDevMode] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [showProgress, setShowProgress] = useState(false); // Separate flag to control progress bar visibility
  const { state: dclState } = useDCLState();
  const [typingEvents, setTypingEvents] = useState<Array<{ text: string; isTyping: boolean; key: string }>>([]);
  const [selectedModel, setSelectedModel] = useState('gemini-2.5-flash');
  const [useAamSource, setUseAamSource] = useState(false);
  
  // Timer and progress state
  const [elapsedTime, setElapsedTime] = useState(0);
  const [progress, setProgress] = useState(0);
  const [timerStarted, setTimerStarted] = useState(false);
  
  // Persist LLM call count across state polls (like timer)
  const [persistedLlmCalls, setPersistedLlmCalls] = useState(0);
  const [startingLlmCalls, setStartingLlmCalls] = useState(0);

  // Auth helper - follows same pattern as aoaApi.ts
  const getAuthHeader = (): Record<string, string> => {
    const token = localStorage.getItem(AUTH_TOKEN_KEY);
    return token ? { 'Authorization': `Bearer ${token}` } : {};
  };

  // Handle 401 unauthorized responses
  const handleUnauthorized = () => {
    console.log('[DCL] 401 Unauthorized - clearing auth state');
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem('auth_token_expiry');
    window.dispatchEvent(new CustomEvent('auth:unauthorized'));
  };

  // Get persisted selections from localStorage, fallback to mode-appropriate sources
  // Ensures we never send empty query params to backend
  const getPersistedSources = () => {
    // Filter sources based on current mode
    const allAvailableSources = useAamSource ? getAamSourceValues() : getAllSourceValues();
    const defaultSources = getDefaultSources();
    
    // Filter to only include sources valid for current mode
    const filteredSources = defaultSources.filter(s => allAvailableSources.includes(s));
    
    // If no valid sources after filtering, use all available for current mode
    const sources = filteredSources.length > 0 ? filteredSources : allAvailableSources;
    
    console.log('[DCL] Current sources from localStorage:', sources);
    return sources.join(',');
  };
  
  const getPersistedAgents = () => {
    const defaultAgents = getDefaultAgents();
    console.log('[DCL] Current agents from localStorage:', defaultAgents);
    // getDefaultAgents always returns non-empty array (fallback to all agents)
    return defaultAgents.join(',');
  };
  
  // Select all sources/agents (selection only, doesn't run)
  const selectAllSources = () => {
    // Select all sources based on current mode
    const allSources = useAamSource ? getAamSourceValues() : getAllSourceValues();
    const allAgents = ['revops_pilot', 'finops_pilot'];
    localStorage.setItem('aos.selectedSources', JSON.stringify(allSources));
    localStorage.setItem('aos.selectedAgents', JSON.stringify(allAgents));
    console.log('[DCL] ✅ Selected ALL sources and agents:', allSources, allAgents);
  };

  // Load feature flags from API
  useEffect(() => {
    fetch(API_CONFIG.buildDclUrl('/feature_flags'))
      .then(res => res.json())
      .then(flags => {
        const aamMode = flags.USE_AAM_AS_SOURCE || false;
        setUseAamSource(aamMode);
        
        // Auto-update selected sources to match mode
        const correctSources = aamMode ? getAamSourceValues() : getAllSourceValues();
        localStorage.setItem('aos.selectedSources', JSON.stringify(correctSources));
        console.log(`[DCL] Initialized sources for ${aamMode ? 'AAM' : 'Legacy'} mode:`, correctSources);
      })
      .catch(err => console.error('Failed to load feature flags:', err));
  }, []);
  
  // Update sources when AAM mode changes
  useEffect(() => {
    const correctSources = useAamSource ? getAamSourceValues() : getAllSourceValues();
    localStorage.setItem('aos.selectedSources', JSON.stringify(correctSources));
    console.log(`[DCL] Updated sources for ${useAamSource ? 'AAM' : 'Legacy'} mode:`, correctSources);
  }, [useAamSource]);

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
          const response = await fetch(API_CONFIG.buildDclUrl(`/connect?sources=${sources}&agents=${agents}&llm_model=${selectedModel}`), {
            headers: {
              ...getAuthHeader(),
            },
          });

          // Handle 401 unauthorized
          if (response.status === 401) {
            handleUnauthorized();
            console.error('[DCL] Session expired during auto-run. Please login again.');
            setIsProcessing(false);
            return;
          }

          if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Auto-run failed' }));
            throw new Error(error.detail || `HTTP error! status: ${response.status}`);
          }

          console.log('[DCL] Auto-run successful');
          // Notify graph to update (event-driven)
          window.dispatchEvent(new Event('dcl-state-changed'));
        } catch (error) {
          console.error('[DCL] Error auto-running graph:', error);
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
        setElapsedTime(prev => prev + 0.01);
      }, 10);
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [timerStarted, isProcessing]);

  // Poll DCL state during processing to capture LLM call count
  useEffect(() => {
    let pollInterval: NodeJS.Timeout;
    
    if (isProcessing && showProgress) {
      // Poll every 2 seconds to get updated LLM call count
      pollInterval = setInterval(async () => {
        try {
          const response = await fetch(API_CONFIG.buildDclUrl('/state'), {
            headers: { ...getAuthHeader() }
          });
          if (response.ok) {
            const state = await response.json();
            const currentLlmCalls = state.llm?.calls || 0;
            // Calculate delta: show only THIS run's LLM calls, not accumulated total
            const deltaLlmCalls = Math.max(0, currentLlmCalls - startingLlmCalls);
            setPersistedLlmCalls(deltaLlmCalls);
          }
        } catch (error) {
          console.error('[DCL] Error polling state for LLM count:', error);
        }
      }, 2000);
    }
    
    return () => {
      if (pollInterval) clearInterval(pollInterval);
    };
  }, [isProcessing, showProgress, startingLlmCalls]);

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
    // Reset timer, progress, and LLM count on NEW run
    setElapsedTime(0);
    setProgress(0);
    setPersistedLlmCalls(0); // Reset displayed LLM count for new run
    setTimerStarted(true);
    setIsProcessing(true);
    setShowProgress(true); // Enable progress bar for manual runs
    
    // Fetch current LLM count from backend as baseline (not from stale dclState)
    try {
      const stateResponse = await fetch(API_CONFIG.buildDclUrl('/state'), {
        headers: { ...getAuthHeader() }
      });
      if (stateResponse.ok) {
        const state = await stateResponse.json();
        const currentCount = state.llm?.calls || 0;
        setStartingLlmCalls(currentCount);
        console.log('[DCL] Starting LLM baseline:', currentCount);
      }
    } catch (error) {
      console.error('[DCL] Failed to fetch starting LLM count:', error);
      setStartingLlmCalls(0);
    }
    
    try {
      const sources = getPersistedSources();
      const agents = getPersistedAgents();
      const response = await fetch(API_CONFIG.buildDclUrl(`/connect?sources=${sources}&agents=${agents}&llm_model=${selectedModel}`), {
        headers: {
          ...getAuthHeader(),
        },
      });

      // Handle 401 unauthorized
      if (response.status === 401) {
        handleUnauthorized();
        console.error('[DCL] Session expired. Please login again.');
        setIsProcessing(false);
        return;
      }

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(error.detail || `HTTP error! status: ${response.status}`);
      }

      await response.json();
      console.log('[DCL] Connection successful');
      // Notify graph to update (event-driven)
      window.dispatchEvent(new Event('dcl-state-changed'));
    } catch (error) {
      console.error('[DCL] Error running:', error);
    } finally {
      setTimeout(() => {
        setIsProcessing(false);
        // Keep timer and progress visible with final values (don't hide)
      }, 1500);
    }
  };

  // Toggle dev mode handler with JWT authentication
  const handleToggleDevMode = async () => {
    try {
      const newMode = !devMode;
      const response = await fetch(API_CONFIG.buildDclUrl(`/toggle_dev_mode?enabled=${newMode}`), {
        headers: {
          ...getAuthHeader(),
        },
      });

      // Handle 401 unauthorized
      if (response.status === 401) {
        handleUnauthorized();
        console.error('[DCL] Session expired. Please login again.');
        return;
      }

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(error.detail || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setDevMode(data.dev_mode);
      console.log(`[DCL] Dev mode toggled: ${data.dev_mode ? 'ON' : 'OFF'}`);
      // Notify graph to update
      window.dispatchEvent(new Event('dcl-state-changed'));
    } catch (error) {
      console.error('[DCL] Error toggling dev mode:', error);
    }
  };

  // Toggle source mode handler
  const toggleSourceMode = async () => {
    const newValue = !useAamSource;
    try {
      const response = await fetch(API_CONFIG.buildDclUrl('/feature_flags/toggle'), {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          ...getAuthHeader(),
        },
        body: JSON.stringify({
          flag: 'USE_AAM_AS_SOURCE',
          enabled: newValue
        })
      });
      const data = await response.json();
      if (data.ok) {
        setUseAamSource(newValue);
        console.log(`[DCL] Switched to ${newValue ? 'AAM Connectors' : 'Legacy File Sources'}`);
      }
    } catch (err) {
      console.error('[DCL] Failed to toggle source mode:', err);
    }
  };

  return (
    <div id="dcl-graph-container" className="bg-gray-900 rounded-xl border border-gray-800 p-2 sm:p-3 -mt-[5px]">
      {/* Top-Mounted Progress Bar - Shows only for manual/connection-triggered runs */}
      {showProgress && (
        <div className="relative -mx-2 sm:-mx-3 -mt-2 sm:-mt-3 mb-3 h-4 bg-gray-800 rounded-t-xl overflow-hidden">
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
            <span className="text-white text-[10px] tracking-wide drop-shadow-lg">
              {Math.round(progress)}% Complete
            </span>
          </div>
        </div>
      )}
      
      <div className="mb-4">
        <h2 
          className="text-lg font-medium text-cyan-400 cursor-help" 
          title="The Data Connectivity Layer (DCL) links heterogeneous data sources without migrations or ETL. It maps entities to a unified ontology for domain agents to act on."
        >
          Data Connection Layer (DCL)
        </h2>
        <p className="text-sm text-gray-400 mt-1">
          Provides persistent, versioned entity mappings so AI Agents can reason with consistent, validated inputs.
        </p>
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
                <div className="flex flex-col sm:flex-row items-start sm:items-center sm:justify-between gap-2 sm:gap-3 mb-3 sm:mb-1">
                  <h3 className="text-sm sm:text-sm font-medium text-white">
                    Ontology Graph
                  </h3>
                  {/* Mobile: 2x2 Grid, Desktop: Row */}
                  <div className="grid grid-cols-2 sm:flex items-center gap-2 w-full sm:w-auto">
                    {/* Dev Mode / Prod Mode Toggle */}
                    <button
                      onClick={handleToggleDevMode}
                      className={`touch-target-h mobile-tap-highlight px-3 py-2 sm:px-2 sm:py-1 rounded text-xs sm:text-[10px] transition-all ${
                        devMode
                          ? 'bg-amber-600/20 border border-amber-500/40 text-amber-300 hover:bg-amber-600/30'
                          : 'bg-emerald-600/20 border border-emerald-500/40 text-emerald-300 hover:bg-emerald-600/30'
                      }`}
                      title="Toggle between Production Mode (heuristics only) and Dev Mode (AI + RAG active)"
                    >
                      <div className="flex items-center gap-2 justify-center">
                        <div className={`w-2 h-2 rounded-full ${devMode ? 'bg-amber-400 animate-pulse' : 'bg-emerald-400'}`} />
                        <span className="whitespace-nowrap">{devMode ? 'Dev Mode' : 'Prod Mode'}</span>
                      </div>
                    </button>

                    {/* Data Source Mode Toggle */}
                    <button
                      onClick={toggleSourceMode}
                      className={`touch-target-h mobile-tap-highlight px-3 py-2 sm:px-2 sm:py-1 rounded text-xs sm:text-[10px] transition-all ${
                        useAamSource
                          ? 'bg-blue-600/20 border border-blue-500/40 text-blue-300 hover:bg-blue-600/30'
                          : 'bg-green-600/20 border border-green-500/40 text-green-300 hover:bg-green-600/30'
                      }`}
                      title={useAamSource ? 'Using AAM Connectors (Redis Streams)' : 'Using Legacy File Sources (CSV)'}
                    >
                      <div className="flex items-center gap-2 justify-center">
                        <div className={`w-2 h-2 rounded-full ${useAamSource ? 'bg-blue-400' : 'bg-green-400'}`} />
                        <span className="whitespace-nowrap">{useAamSource ? 'AAM' : 'Legacy'}</span>
                      </div>
                    </button>

                    {/* Data Source Selector */}
                    <select
                      onChange={(e) => {
                        if (e.target.value === 'select') {
                          window.dispatchEvent(new CustomEvent('navigate', { detail: { page: 'connections' } }));
                        } else if (e.target.value === 'all') {
                          selectAllSources();
                        }
                        e.target.value = 'all';
                      }}
                      disabled={isProcessing}
                      className="touch-target-h mobile-tap-highlight px-3 py-2 sm:px-2 sm:py-1 bg-gray-800 border border-gray-700 rounded text-xs sm:text-[10px] text-white focus:outline-none focus:border-blue-500 hover:border-gray-600 transition-colors disabled:opacity-50 cursor-pointer"
                      title="Select data sources"
                    >
                      <option value="all">All Sources</option>
                      <option value="select">Select Sources...</option>
                    </select>

                    {/* LLM Model Selector */}
                    <select
                      value={selectedModel}
                      onChange={(e) => setSelectedModel(e.target.value)}
                      disabled={isProcessing}
                      className="touch-target-h mobile-tap-highlight px-3 py-2 sm:px-2 sm:py-1 bg-gray-800 border border-gray-700 rounded text-xs sm:text-[10px] text-white focus:outline-none focus:border-blue-500 hover:border-gray-600 transition-colors disabled:opacity-50 cursor-pointer"
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
                      className="touch-target-h mobile-tap-highlight flex items-center gap-1.5 px-4 sm:px-2 py-2 sm:py-1 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 rounded-md text-xs sm:text-[10px] text-white shadow-lg shadow-emerald-500/30 transition-all disabled:opacity-50 justify-center"
                      title="Run mapping with selected configuration"
                    >
                      {isProcessing ? (
                        <>
                          <svg className="animate-spin h-3 w-3 sm:h-3 sm:w-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                          <span className="hidden sm:inline">Processing...</span>
                        </>
                      ) : (
                        <>
                          <Play className="w-3 h-3 sm:w-3 sm:h-3" />
                          <span>Run</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2 sm:gap-4 text-[10px] sm:text-[10px] text-blue-300">
                  <div className="flex items-center gap-1">
                    <div className={`w-1.5 h-1.5 rounded-full ${devMode ? 'bg-purple-400 animate-pulse' : 'bg-gray-500'}`} />
                    <span>LLM Calls: {persistedLlmCalls}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Activity className="w-3 h-3 text-blue-400" />
                    <span className="whitespace-nowrap">
                      {getDefaultSources().length} sources → {getDefaultAgents().length} agent{getDefaultAgents().length !== 1 ? 's' : ''}
                    </span>
                  </div>
                  <div className="flex items-center gap-1" title="RAG mappings retrieved from inventory">
                    <svg className="w-3 h-3 text-teal-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <span>RAG: {dclState?.rag?.mappings_retrieved || 0}</span>
                  </div>
                  <div className="flex items-center gap-1" title="LLM calls saved via RAG inventory">
                    <svg className="w-3 h-3 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span>Saved: {dclState?.llm?.calls_saved || 0}</span>
                  </div>
                  <div className="flex items-center gap-1" title="Blended confidence from graph and RAG">
                    <svg className="w-3 h-3 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                    <span>Confidence: {dclState?.blended_confidence ? Math.round(dclState.blended_confidence * 100) : '--'}%</span>
                  </div>
                  {(timerStarted || elapsedTime > 0) && (
                    <div className="flex items-center gap-1 bg-blue-900/30 px-2 py-0.5 rounded">
                      <svg className="w-3 h-3 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <span className="font-mono">{elapsedTime.toFixed(2)}s</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          <div className="relative pb-2 md:min-h-[500px]">
            <LazyGraphShell />
          </div>
        </div>

        <div className="flex flex-col gap-4">
          {/* Narration Panel with Typing Animation - MOVED TO TOP FOR PROMINENCE */}
          <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-4 flex-1 max-w-md mx-auto w-full">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-6 h-6 rounded-full bg-purple-500 flex items-center justify-center text-white text-xs">
                📝
              </div>
              <span 
                className="text-white text-sm cursor-help" 
                title="Chronological event log showing every decision, mapping, and execution step. Functions as a transparent, auditable trail of autonomous system behavior."
              >
                Narration
              </span>
              <span className="ml-auto text-xs bg-purple-600 text-white px-2 py-0.5 rounded-full">
                {dclState?.events.length || 0} events
              </span>
            </div>
            <div className="text-xs space-y-1 overflow-y-auto max-h-[200px]">
              {typingEvents.length === 0 ? (
                <div className="text-gray-500 italic text-[11px]">
                  No events yet. Start mapping to see the narration.
                </div>
              ) : (
                typingEvents.map((event, idx) => (
                  <div key={event.key} className="text-gray-300 leading-relaxed">
                    <span className="text-purple-400 mr-1">[{idx + 1}]</span>
                    {event.isTyping ? <TypingText text={event.text} speed={30} /> : event.text}
                  </div>
                ))
              )}
            </div>
          </div>

          {/* RAG Learning Engine - EXACT LEGACY LAYOUT */}
          <div className="rounded-lg p-4 bg-gradient-to-br from-teal-950 to-cyan-950 border border-teal-700/30 max-w-md mx-auto w-full">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-6 h-6 rounded-full bg-teal-500 flex items-center justify-center text-white text-xs">
                🧠
              </div>
              <span 
                className="text-white text-sm cursor-help" 
                title="Retrieval-Augmented Generation (RAG) component that enriches context for agent reasoning. It stores embeddings, retrieves related knowledge, and continuously self-tunes mappings."
              >
                RAG Learning Engine
              </span>
              <span className="ml-auto text-xs bg-teal-600 text-white px-2 py-0.5 rounded-full">
                {dclState?.rag?.total_mappings || 0} stored
              </span>
            </div>
            <div className="text-xs space-y-2 overflow-y-auto overflow-x-hidden min-h-[150px] max-h-[400px]">
              {!dclState?.rag?.retrievals || dclState.rag.retrievals.length === 0 ? (
                <div className="text-teal-300/70 italic text-[11px]">
                  No context retrieved yet. Connect a source to see RAG retrieve historical mappings.
                </div>
              ) : (
                <>
                  <div className="text-white mb-2 text-[11px]">
                    Retrieved {dclState.rag.last_retrieval_count} similar mappings:
                  </div>
                  {dclState.rag.retrievals.map((ret: any, i: number) => (
                    <div key={i} className="mb-2 pb-2 border-b border-teal-800/30 last:border-0">
                      <div className="flex justify-between items-start mb-1">
                        <div className="text-white text-[11px]">{ret.source_field}</div>
                        <div className="text-[10px] text-white">
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

        </div>
      </div>
    </div>
  );
}
