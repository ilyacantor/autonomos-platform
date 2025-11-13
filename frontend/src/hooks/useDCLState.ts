import { useState, useEffect, useCallback, useRef } from 'react';
import { API_CONFIG, AUTH_TOKEN_KEY } from '../config/api';

const TOKEN_EXPIRY_KEY = 'auth_token_expiry';

// DCL State Cache constants
const DCL_CACHE_KEY = 'aos.dclState.v1';
const DCL_CACHE_TTL_MS = 10 * 60 * 1000; // 10 minutes
const CACHE_VERSION = 1;

interface RAGRetrieval {
  source_field: string;
  ontology_entity: string;
  similarity: number;
}

interface RAGContext {
  retrievals: RAGRetrieval[];
  total_mappings: number;
  last_retrieval_count: number;
  mappings_retrieved?: number;
}

interface GraphNode {
  id: string;
  label: string;
  type: string;
  fields?: string[];
}

interface GraphEdge {
  source: string;
  target: string;
  label?: string;
  field_mappings?: any[];
  entity_fields?: string[];
  entity_name?: string;
}

interface Graph {
  nodes: GraphNode[];
  edges: GraphEdge[];
  confidence?: number | null;
  last_updated?: string | null;
}

interface LLMStats {
  calls: number;
  tokens: number;
  calls_saved?: number;
}

interface PreviewData {
  sources: Record<string, any>;
  ontology: Record<string, any>;
  connectionInfo: any;
}

export interface DCLState {
  events: string[];
  graph: Graph;
  llm: LLMStats;
  preview: PreviewData;
  rag: RAGContext;
  selected_sources: string[];
  selected_agents: string[];
  dev_mode: boolean;
  blended_confidence?: number | null;
}

interface UseDCLStateReturn {
  state: DCLState | null;
  loading: boolean;
  error: Error | null;
  isStale: boolean;
  refetch: () => Promise<void>;
}

interface CachedState {
  state: DCLState;
  timestamp: number;
  version: number;
}

interface WebSocketMessage {
  type: string;
  timestamp: number;
  data: {
    sources: string[];
    agents: string[];
    devMode: boolean;
    graph: Graph;
    llmCalls: number;
    llmTokens: number;
    ragContext: RAGContext;
    events?: string[];
    entitySources?: Record<string, string[]>;
    sourceSchemas?: Record<string, any>;
    agentConsumption?: Record<string, string[]>;
  };
}

// Cache helper functions
function loadCachedState(): { state: DCLState; isStale: boolean } | null {
  try {
    const cached = localStorage.getItem(DCL_CACHE_KEY);
    if (!cached) return null;

    const parsed: CachedState = JSON.parse(cached);
    
    // Validate version
    if (parsed.version !== CACHE_VERSION) {
      console.log('[DCL Cache] Version mismatch, ignoring cache');
      localStorage.removeItem(DCL_CACHE_KEY);
      return null;
    }

    // Check if state is meaningful (has graph nodes)
    if (!parsed.state?.graph?.nodes || parsed.state.graph.nodes.length === 0) {
      console.log('[DCL Cache] Empty graph in cache, ignoring');
      return null;
    }

    // Check TTL
    const age = Date.now() - parsed.timestamp;
    const isStale = age > DCL_CACHE_TTL_MS;

    console.log(`[DCL Cache] Loaded cached state (age: ${Math.round(age / 1000)}s, stale: ${isStale})`);
    
    return { state: parsed.state, isStale };
  } catch (err) {
    console.error('[DCL Cache] Failed to load cache:', err);
    localStorage.removeItem(DCL_CACHE_KEY);
    return null;
  }
}

function saveCachedState(state: DCLState): void {
  try {
    // Only cache meaningful state (non-empty graph)
    if (!state?.graph?.nodes || state.graph.nodes.length === 0) {
      return;
    }

    const cached: CachedState = {
      state,
      timestamp: Date.now(),
      version: CACHE_VERSION,
    };

    localStorage.setItem(DCL_CACHE_KEY, JSON.stringify(cached));
    console.log('[DCL Cache] State cached successfully');
  } catch (err) {
    console.error('[DCL Cache] Failed to save cache:', err);
  }
}

function clearCachedState(): void {
  try {
    localStorage.removeItem(DCL_CACHE_KEY);
    console.log('[DCL Cache] Cache cleared');
  } catch (err) {
    console.error('[DCL Cache] Failed to clear cache:', err);
  }
}

export function useDCLState(): UseDCLStateReturn {
  // Hydrate state from cache synchronously on mount
  const [state, setState] = useState<DCLState | null>(() => {
    const cached = loadCachedState();
    if (cached) {
      console.log('[DCL] Hydrated from cache');
      return cached.state;
    }
    return null;
  });
  
  const [loading, setLoading] = useState(() => {
    // If we have cached state, we're not loading
    const cached = loadCachedState();
    return !cached;
  });
  
  const [isStale, setIsStale] = useState(() => {
    const cached = loadCachedState();
    return cached ? cached.isStale : false;
  });
  
  const [error, setError] = useState<Error | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 10;
  const baseReconnectDelay = 1000;
  const initialFetchDoneRef = useRef(false);

  const processWebSocketMessage = useCallback((message: any) => {
    try {
      // Handle RAG coverage check events (intelligent LLM decision prompts)
      if (message.type === 'rag_coverage_check') {
        console.log('[DCL] 🎯 RAG Coverage Check:', {
          source: message.source,
          coverage: `${message.coverage_pct}%`,
          matched: `${message.matched_count}/${message.total_count} fields`,
          recommendation: message.recommendation,
          savings: `$${message.estimated_cost_savings}`,
          missing_fields: message.missing_fields,
        });
        
        // Show coverage info in console (UI modal to be added in future iteration)
        console.log(`💡 ${message.message}`);
        console.log(`   Recommendation: ${message.recommendation === 'skip' ? 'Skip LLM (use RAG + heuristics)' : 'Proceed with LLM'}`);
        console.log(`   Cost savings if skipped: ~$${message.estimated_cost_savings}`);
        
        return; // Don't update state for this event type
      }
      
      // Only process state update messages (with data field)
      // Ignore progress messages (mapping_progress, etc.)
      if (!message.data) {
        return;
      }

      const newState: DCLState = {
        events: message.data.events || [],
        graph: message.data.graph,
        llm: {
          calls: message.data.llmCalls,
          tokens: message.data.llmTokens,
          calls_saved: message.data.llmCallsSaved || 0,
        },
        preview: {
          sources: {},
          ontology: {},
          connectionInfo: null,
        },
        rag: message.data.ragContext,
        selected_sources: message.data.sources || [],
        selected_agents: message.data.agents || [],
        dev_mode: message.data.devMode,
        blended_confidence: message.data.blendedConfidence,
      };

      setState(newState);
      saveCachedState(newState); // Write-through to cache
      setError(null);
      setLoading(false);
      setIsStale(false); // Fresh data from server
    } catch (err) {
      console.error('Error processing WebSocket message:', err);
      setError(err instanceof Error ? err : new Error('Failed to process message'));
    }
  }, []);

  const connectWebSocket = useCallback(() => {
    try {
      // Build absolute WebSocket URL
      let wsUrl: string;

      if (API_CONFIG.BASE_URL && API_CONFIG.BASE_URL.match(/^https?:\/\//)) {
        // BASE_URL is an absolute URL, use it and replace protocol
        wsUrl = API_CONFIG.buildDclUrl('/ws').replace(/^http/, 'ws');
      } else {
        // BASE_URL is empty or relative, construct from window.location
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        wsUrl = `${protocol}//${host}/dcl/ws`;
      }

      console.log('[DCL WebSocket] Connecting to:', wsUrl);

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('[DCL WebSocket] Connected');
        reconnectAttemptsRef.current = 0;
        
        const token = localStorage.getItem(AUTH_TOKEN_KEY);
        if (token) {
          try {
            ws.send(JSON.stringify({ type: 'auth', token }));
          } catch (err) {
            console.error('[DCL WebSocket] Failed to send auth token:', err);
          }
        }
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          console.log('[DCL WebSocket] Received message:', message.type);
          processWebSocketMessage(message);
        } catch (err) {
          console.error('[DCL WebSocket] Failed to parse message:', err);
          console.error('[DCL WebSocket] Raw message data:', event.data?.substring(0, 200));
        }
      };

      ws.onerror = (event) => {
        console.error('[DCL WebSocket] Error:', event);
        setError(new Error('WebSocket connection error'));
      };

      ws.onclose = (event) => {
        console.log('[DCL WebSocket] Disconnected:', event.code, event.reason);
        wsRef.current = null;

        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          const delay = Math.min(
            baseReconnectDelay * Math.pow(2, reconnectAttemptsRef.current),
            30000
          );
          
          console.log(
            `[DCL WebSocket] Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current + 1}/${maxReconnectAttempts})`
          );

          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttemptsRef.current++;
            connectWebSocket();
          }, delay);
        } else {
          console.error('[DCL WebSocket] Max reconnection attempts reached');
          setError(new Error('WebSocket connection lost. Please refresh the page.'));
        }
      };
    } catch (err) {
      console.error('[DCL WebSocket] Failed to create WebSocket:', err);
      setError(err instanceof Error ? err : new Error('Failed to create WebSocket'));
    }
  }, [processWebSocketMessage]);

  const fetchState = useCallback(async () => {
    try {
      const token = localStorage.getItem(AUTH_TOKEN_KEY);
      
      const headers: HeadersInit = {};
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
      
      const response = await fetch(API_CONFIG.buildDclUrl('/state'), {
        headers,
      });
      
      if (!response.ok) {
        if (response.status === 401 && token) {
          console.log('[DCL State] 401 Unauthorized - clearing auth and cache');
          localStorage.removeItem(AUTH_TOKEN_KEY);
          localStorage.removeItem(TOKEN_EXPIRY_KEY);
          clearCachedState(); // Clear cache on auth failure
          window.dispatchEvent(new CustomEvent('auth:unauthorized'));
          return;
        }
        throw new Error(`Failed to fetch state: ${response.statusText}`);
      }
      const data = await response.json();
      setState(data);
      saveCachedState(data); // Write-through to cache
      setError(null);
      setLoading(false);
      setIsStale(false); // Fresh data from server
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error'));
      console.error('Error fetching DCL state:', err);
    }
  }, []);

  useEffect(() => {
    connectWebSocket();
    
    // If we hydrated from cache, trigger an immediate fetch to refresh
    if (!initialFetchDoneRef.current) {
      initialFetchDoneRef.current = true;
      console.log('[DCL] Triggering initial state fetch for refresh');
      fetchState();
    }

    return () => {
      console.log('[DCL WebSocket] Cleaning up...');
      
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }

      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connectWebSocket, fetchState]);

  return { state, loading, error, isStale, refetch: fetchState };
}
