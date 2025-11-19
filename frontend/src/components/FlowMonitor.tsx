import { useState, useEffect, useRef } from 'react';
import { Activity, CheckCircle, AlertCircle, Clock, Zap, Database, Brain, Settings } from 'lucide-react';

interface FlowEvent {
  event_id: string;
  entity_id: string;
  layer: string;
  stage: string;
  status: string;
  tenant_id: string;
  timestamp: string;
  duration_ms?: number;
  metadata: any;
  stream_id?: string;
}

interface FlowSnapshot {
  aam_events: FlowEvent[];
  dcl_events: FlowEvent[];
  agent_events: FlowEvent[];
  total_count: number;
  tenant_id: string;
  timestamp: string;
}

const statusColors: Record<string, string> = {
  success: 'bg-green-500',
  failure: 'bg-red-500',
  in_progress: 'bg-purple-500',
  degraded: 'bg-blue-500',
  pending: 'bg-gray-500',
};

const statusIcons: Record<string, any> = {
  success: CheckCircle,
  failure: AlertCircle,
  in_progress: Clock,
  degraded: Settings,
  pending: Clock,
};

const FlowMonitor = () => {
  const [aamEvents, setAamEvents] = useState<FlowEvent[]>([]);
  const [dclEvents, setDclEvents] = useState<FlowEvent[]>([]);
  const [agentEvents, setAgentEvents] = useState<FlowEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // Fetch initial snapshot
  useEffect(() => {
    const fetchSnapshot = async () => {
      try {
        const response = await fetch('/api/v1/flow-monitor?tenant_id=default&limit_per_layer=100');
        if (response.ok) {
          const data: FlowSnapshot = await response.json();
          setAamEvents(data.aam_events || []);
          setDclEvents(data.dcl_events || []);
          setAgentEvents(data.agent_events || []);
        } else {
          setError('Failed to fetch flow snapshot');
        }
      } catch (err) {
        console.error('Error fetching flow snapshot:', err);
        setError('Failed to connect to Flow Monitor API');
      }
    };

    fetchSnapshot();
  }, []);

  // WebSocket connection for live updates
  useEffect(() => {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/api/v1/ws/flow-monitor?tenant_id=default`;

    const connectWebSocket = () => {
      try {
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          console.log('Flow Monitor WebSocket connected');
          setConnected(true);
          setError(null);
        };

        ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);

            if (message.type === 'flow_event') {
              const flowEvent: FlowEvent = message.event;
              const layer = message.layer;

              // Add new event to appropriate list (prepend for newest first)
              if (layer === 'aam') {
                setAamEvents(prev => [flowEvent, ...prev].slice(0, 100)); // Keep last 100
              } else if (layer === 'dcl') {
                setDclEvents(prev => [flowEvent, ...prev].slice(0, 100));
              } else if (layer === 'agent') {
                setAgentEvents(prev => [flowEvent, ...prev].slice(0, 100));
              }
            } else if (message.type === 'error') {
              console.error('WebSocket error:', message.message);
              setError(message.message);
            }
          } catch (err) {
            console.error('Failed to parse WebSocket message:', err);
          }
        };

        ws.onerror = (err) => {
          console.error('WebSocket error:', err);
          setConnected(false);
          setError('WebSocket connection error');
        };

        ws.onclose = () => {
          console.log('WebSocket disconnected, reconnecting...');
          setConnected(false);
          setTimeout(connectWebSocket, 3000); // Reconnect after 3 seconds
        };

        wsRef.current = ws;
      } catch (err) {
        console.error('Failed to create WebSocket:', err);
        setError('Failed to create WebSocket connection');
      }
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const renderEventTimeline = (events: FlowEvent[], title: string, icon: any, color: string) => {
    const Icon = icon;

    return (
      <div className="flex-1 bg-gray-800 rounded-lg shadow-lg p-6 overflow-hidden flex flex-col border border-gray-700">
        <div className="flex items-center gap-3 mb-4 border-b border-gray-700 pb-3">
          <Icon className={`w-6 h-6 ${color}`} />
          <h2 className="text-lg font-semibold text-white">{title}</h2>
          <span className="ml-auto bg-gray-700 px-3 py-1 rounded-full text-sm text-gray-300">
            {events.length} events
          </span>
        </div>

        <div className="flex-1 overflow-y-auto space-y-3 pr-2" style={{ maxHeight: '600px' }}>
          {events.length === 0 ? (
            <div className="text-center text-gray-500 py-8">
              <Activity className="w-12 h-12 mx-auto mb-2 opacity-30" />
              <p>No events yet</p>
            </div>
          ) : (
            events.slice(0, 20).map((event, idx) => {
              const StatusIcon = statusIcons[event.status] || Clock;
              const statusColor = statusColors[event.status] || 'bg-gray-500';
              const metadata = typeof event.metadata === 'string' ? JSON.parse(event.metadata) : event.metadata;

              return (
                <div
                  key={event.stream_id || `${event.event_id}-${idx}`}
                  className="border border-gray-700 rounded-lg p-3 hover:border-gray-600 transition-colors bg-gray-900"
                >
                  <div className="flex items-start gap-3">
                    <div className={`${statusColor} rounded-full p-1.5 mt-0.5`}>
                      <StatusIcon className="w-4 h-4 text-white" />
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-medium text-white truncate">{event.entity_id}</span>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${statusColor} bg-opacity-20 text-gray-300`}>
                          {event.stage.replace(/_/g, ' ')}
                        </span>
                      </div>

                      <div className="text-xs text-gray-400 space-y-0.5">
                        <div className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          <span>{new Date(event.timestamp).toLocaleTimeString()}</span>
                          {event.duration_ms && <span className="ml-2">({event.duration_ms}ms)</span>}
                        </div>

                        {metadata && Object.keys(metadata).length > 0 && (
                          <div className="mt-1 text-xs text-gray-300 bg-gray-800 rounded px-2 py-1 border border-gray-700">
                            {Object.entries(metadata).slice(0, 3).map(([key, value]) => (
                              <div key={key} className="truncate">
                                <span className="font-medium">{key}:</span>{' '}
                                {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 p-6">
      <div className="max-w-[1800px] mx-auto">
        <div className="mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-white mb-2">Live Flow Monitoring</h1>
              <p className="text-gray-400">Real-time telemetry across AAM → DCL → Agent pipeline</p>
            </div>

            <div className="flex items-center gap-3">
              <div className={`flex items-center gap-2 px-4 py-2 rounded-lg border ${connected ? 'bg-green-900/30 border-green-700 text-green-400' : 'bg-red-900/30 border-red-700 text-red-400'}`}>
                <div className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
                <span className="text-sm font-medium">{connected ? 'Connected' : 'Disconnected'}</span>
              </div>

              {error && (
                <div className="bg-red-900/30 border border-red-700 text-red-400 px-4 py-2 rounded-lg text-sm flex items-center gap-2">
                  <AlertCircle className="w-4 h-4" />
                  {error}
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="flex gap-6" style={{ height: 'calc(100vh - 180px)' }}>
          {renderEventTimeline(aamEvents, 'AAM Connections', Database, 'text-green-400')}
          {renderEventTimeline(dclEvents, 'DCL Intelligence', Brain, 'text-purple-400')}
          {renderEventTimeline(agentEvents, 'Agent Execution', Zap, 'text-blue-400')}
        </div>
      </div>
    </div>
  );
};

export default FlowMonitor;
