import { useState, useEffect, useCallback, useRef } from 'react';
import { API_CONFIG, AUTH_TOKEN_KEY } from '../config/api';

const TOKEN_EXPIRY_KEY = 'auth_token_expiry';

interface RAGRetrieval {
  source_field: string;
  ontology_entity: string;
  similarity: number;
}

interface RAGContext {
  retrievals: RAGRetrieval[];
  total_mappings: number;
  last_retrieval_count: number;
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
}

interface UseDCLStateReturn {
  state: DCLState | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
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

export function useDCLState(): UseDCLStateReturn {
  const [state, setState] = useState<DCLState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 10;
  const baseReconnectDelay = 1000;

  const processWebSocketMessage = useCallback((message: any) => {
    try {
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
      };

      setState(newState);
      setError(null);
      setLoading(false);
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
          console.log('[DCL State] 401 Unauthorized - clearing auth state');
          localStorage.removeItem(AUTH_TOKEN_KEY);
          localStorage.removeItem(TOKEN_EXPIRY_KEY);
          window.dispatchEvent(new CustomEvent('auth:unauthorized'));
          return;
        }
        throw new Error(`Failed to fetch state: ${response.statusText}`);
      }
      const data = await response.json();
      setState(data);
      setError(null);
      setLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error'));
      console.error('Error fetching DCL state:', err);
    }
  }, []);

  useEffect(() => {
    connectWebSocket();

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
  }, [connectWebSocket]);

  return { state, loading, error, refetch: fetchState };
}
