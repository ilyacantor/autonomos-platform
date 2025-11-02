import { useState, useEffect, useRef, useCallback } from 'react';
import { EventItem } from '../types/events';
import { API_CONFIG, AUTH_TOKEN_KEY } from '../config/api';

interface UseEventStreamResult {
  events: EventItem[];
  isConnected: boolean;
  isMockMode: boolean;
  error: string | null;
}

const RECONNECT_DELAYS = [1000, 2000, 4000, 8000];
const CONNECTION_TIMEOUT = 30000; // 30 seconds
const MAX_EVENTS = 120;

function generateMockEvent(): EventItem {
  const sources: EventItem['source_system'][] = ['salesforce', 'supabase', 'mongodb', 'filesource', 'system'];
  const stages: EventItem['stage'][] = ['ingested', 'canonicalized', 'materialized', 'viewed', 'intent', 'journaled', 'drift'];
  const entities = ['Account', 'Contact', 'Opportunity', 'Lead', 'User', 'Order', 'Product'];
  
  const source = sources[Math.floor(Math.random() * sources.length)];
  const stage = stages[Math.floor(Math.random() * stages.length)];
  
  return {
    id: `mock_${Date.now()}_${Math.floor(Math.random() * 10000)}`,
    ts: new Date().toISOString(),
    tenant: '00000000-0000-0000-0000-000000000001',
    source_system: source,
    entity: entities[Math.floor(Math.random() * entities.length)],
    stage: stage,
    meta: {
      record_count: Math.floor(Math.random() * 100) + 1,
      processing_time_ms: Math.floor(Math.random() * 500) + 50
    }
  };
}

export function useEventStream(): UseEventStreamResult {
  const [events, setEvents] = useState<EventItem[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isMockMode, setIsMockMode] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const connectionTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const mockGeneratorRef = useRef<NodeJS.Timeout | null>(null);

  const addEvent = useCallback((event: EventItem) => {
    setEvents(prev => {
      const newEvents = [event, ...prev].slice(0, MAX_EVENTS);
      return newEvents;
    });
  }, []);

  const startMockGenerator = useCallback(() => {
    if (isMockMode) return;
    
    setIsMockMode(true);
    console.log('[EventStream] Starting mock event generator (fallback mode)');
    
    // Clear events when switching to mock mode
    setEvents([]);
    
    const generateMock = () => {
      const event = generateMockEvent();
      addEvent(event);
      
      const nextDelay = Math.random() * 3000 + 1000;
      mockGeneratorRef.current = setTimeout(generateMock, nextDelay);
    };
    
    generateMock();
  }, [isMockMode, addEvent]);

  const stopMockGenerator = useCallback(() => {
    if (mockGeneratorRef.current) {
      clearTimeout(mockGeneratorRef.current);
      mockGeneratorRef.current = null;
    }
    if (isMockMode) {
      setIsMockMode(false);
      console.log('[EventStream] Stopping mock mode, switching to real events');
      // Clear mock events when switching to real mode
      setEvents([]);
    }
  }, [isMockMode]);

  const connect = useCallback(() => {
    if (eventSourceRef.current) {
      return;
    }

    // Get JWT token from localStorage for authentication
    const token = localStorage.getItem(AUTH_TOKEN_KEY);
    if (!token) {
      console.warn('[EventStream] No auth token found, falling back to mock mode');
      startMockGenerator();
      return;
    }

    // Pass token as query parameter since EventSource doesn't support custom headers
    const url = `${API_CONFIG.buildApiUrl('/events/stream')}?token=${encodeURIComponent(token)}`;
    console.log('[EventStream] Connecting to SSE endpoint...');

    try {
      const eventSource = new EventSource(url);
      eventSourceRef.current = eventSource;

      // Set timeout for connection - fall back to mock mode if not connected
      connectionTimeoutRef.current = setTimeout(() => {
        const readyState = eventSourceRef.current?.readyState;
        if (readyState !== EventSource.OPEN) {
          console.warn('[EventStream] Connection timeout after 30s - falling back to mock mode');
          if (eventSourceRef.current) {
            eventSourceRef.current.close();
            eventSourceRef.current = null;
          }
          setIsConnected(false);
          setError('Connection timeout');
          startMockGenerator();
        }
      }, CONNECTION_TIMEOUT);

      // Handle connection opened - only mark connected when actually OPEN
      eventSource.onopen = () => {
        if (connectionTimeoutRef.current) {
          clearTimeout(connectionTimeoutRef.current);
          connectionTimeoutRef.current = null;
        }

        // Stop mock mode if it was running
        if (isMockMode) {
          stopMockGenerator();
        }

        // Only set connected when readyState is OPEN
        if (eventSource.readyState === EventSource.OPEN) {
          console.log('[EventStream] Connected to real-time event stream');
          setIsConnected(true);
          setError(null);
          reconnectAttemptRef.current = 0;
        }
      };

      // Handle incoming events
      eventSource.addEventListener('event', (e: MessageEvent) => {
        try {
          const eventData: EventItem = JSON.parse(e.data);
          addEvent(eventData);
        } catch (err) {
          console.error('[EventStream] Failed to parse event:', err);
        }
      });

      // Handle heartbeat
      eventSource.addEventListener('heartbeat', () => {
        // Heartbeat keeps connection alive
      });

      // Handle errors
      eventSource.onerror = () => {
        console.error('[EventStream] Connection error');
        setIsConnected(false);
        
        if (eventSourceRef.current) {
          eventSourceRef.current.close();
          eventSourceRef.current = null;
        }

        // Retry with exponential backoff, then fall back to mock mode
        if (reconnectAttemptRef.current < RECONNECT_DELAYS.length) {
          const delay = RECONNECT_DELAYS[reconnectAttemptRef.current];
          reconnectAttemptRef.current++;
          
          console.log(`[EventStream] Reconnecting in ${delay}ms (attempt ${reconnectAttemptRef.current})`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        } else {
          console.warn('[EventStream] Max reconnection attempts reached, falling back to mock mode');
          setError('Connection failed after multiple retries');
          startMockGenerator();
        }
      };

    } catch (err) {
      console.error('[EventStream] Failed to create EventSource:', err);
      setError(err instanceof Error ? err.message : 'Connection failed');
      setIsConnected(false);
      startMockGenerator();
    }
  }, [isMockMode, addEvent, startMockGenerator, stopMockGenerator]);

  const disconnect = useCallback(() => {
    if (connectionTimeoutRef.current) {
      clearTimeout(connectionTimeoutRef.current);
      connectionTimeoutRef.current = null;
    }

    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    stopMockGenerator();

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    setIsConnected(false);
  }, [stopMockGenerator]);

  useEffect(() => {
    connect();

    return () => {
      disconnect();
    };
  }, []);

  return {
    events,
    isConnected,
    isMockMode,
    error
  };
}
