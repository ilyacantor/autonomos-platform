import { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Play, 
  Pause, 
  X, 
  Filter,
  Gauge,
  Database,
  Activity,
  Network,
  Bot,
  AlertTriangle,
  Zap,
  RefreshCw
} from 'lucide-react';
import { useEventStream } from '../../hooks/useEventStream';
import { EventItem, SourceSystem } from '../../types/events';
import { API_CONFIG } from '../../config/api';

const LANE_NAMES = ['Sources', 'AAM', 'DCL', 'Gateway', 'Agents'];

const STAGE_TO_LANE: Record<string, number> = {
  ingested: 0,
  canonicalized: 1,
  materialized: 2,
  viewed: 3,
  intent: 4,
  journaled: 4,
  drift: 1
};

const SOURCE_COLORS: Record<SourceSystem, string> = {
  salesforce: 'bg-sky-500',
  supabase: 'bg-emerald-500',
  mongodb: 'bg-green-600',
  filesource: 'bg-zinc-500',
  system: 'bg-amber-500'
};

const SOURCE_TEXT_COLORS: Record<SourceSystem, string> = {
  salesforce: 'text-sky-500',
  supabase: 'text-emerald-500',
  mongodb: 'text-green-600',
  filesource: 'text-zinc-500',
  system: 'text-amber-500'
};

const LANE_ICONS = [Database, Activity, Network, Bot, AlertTriangle];

export default function LiveFlow() {
  const { events, isConnected, isMockMode, error } = useEventStream();
  const [isPaused, setIsPaused] = useState(false);
  const [speed, setSpeed] = useState<0.5 | 1 | 2>(1);
  const [selectedSources, setSelectedSources] = useState<Set<SourceSystem>>(new Set());
  const [selectedEvent, setSelectedEvent] = useState<EventItem | null>(null);
  const [displayedEvents, setDisplayedEvents] = useState<EventItem[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);

  useEffect(() => {
    if (!isPaused) {
      setDisplayedEvents(events);
    }
  }, [events, isPaused]);

  const filteredEvents = useMemo(() => {
    return selectedSources.size === 0 ? displayedEvents : displayedEvents.filter(e => selectedSources.has(e.source_system));
  }, [displayedEvents, selectedSources]);

  const handleClear = () => {
    setDisplayedEvents([]);
  };

  const toggleSource = (source: SourceSystem) => {
    setSelectedSources(prev => {
      const newSet = new Set(prev);
      if (newSet.has(source)) {
        newSet.delete(source);
      } else {
        newSet.add(source);
      }
      return newSet;
    });
  };

  const clearFilters = () => {
    setSelectedSources(new Set());
  };

  const handleGenerateEvents = async () => {
    setIsGenerating(true);
    try {
      // Use the correct endpoint - /dcl/connect (not /api/v1/dcl/connect)
      const baseUrl = API_CONFIG.getBaseUrl();
      const response = await fetch(`${baseUrl}/dcl/connect`, {
        method: 'GET',  // DCL connect uses GET, not POST
        headers: {
          'Content-Type': 'application/json'
        }
      });
      
      if (!response.ok) {
        throw new Error('Failed to generate events');
      }
      
      console.log('[Live Flow] Events generation triggered successfully');
    } catch (err) {
      console.error('[Live Flow] Failed to generate events:', err);
    } finally {
      setIsGenerating(false);
    }
  };

  const getAnimationDuration = () => {
    return 2 / speed;
  };

  const getLaneForEvent = (event: EventItem): number => {
    return STAGE_TO_LANE[event.stage] ?? 0;
  };

  const allSources: SourceSystem[] = ['salesforce', 'supabase', 'mongodb', 'filesource', 'system'];

  return (
    <div className="flex flex-col h-full bg-gray-950">
      <div className="flex-shrink-0 border-b border-gray-800 bg-gray-900 p-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-2">
              <Activity className="w-6 h-6 text-blue-400" />
              Live Flow
              <span className="text-sm font-normal text-gray-400 ml-2">(beta)</span>
            </h1>
            <p className="text-sm text-gray-400 mt-1">
              Real-time event visualization: Sources → AAM → DCL → Gateway → Agents
            </p>
          </div>
          
          <div className="flex items-center gap-2">
            <button
              onClick={handleGenerateEvents}
              disabled={isGenerating}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-lg transition-colors font-medium"
              title="Trigger connectors to generate real events"
            >
              {isGenerating ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4" />
                  Generate Events
                </>
              )}
            </button>
            
            {isMockMode && (
              <div className="flex items-center gap-2 px-3 py-1 rounded-lg bg-amber-500/10 text-amber-500 border border-amber-500/20">
                <AlertTriangle className="w-4 h-4" />
                <span className="text-sm font-medium">
                  Mock Mode
                </span>
              </div>
            )}
            <div className={`flex items-center gap-2 px-3 py-1 rounded-lg ${isConnected ? 'bg-green-500/10 text-green-500' : 'bg-red-500/10 text-red-500'}`}>
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
              <span className="text-sm font-medium">
                {isConnected ? (isMockMode ? 'Mock Data' : 'Live Stream') : 'Disconnected'}
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-2 bg-gray-800 rounded-lg p-1">
            <button
              onClick={() => setIsPaused(!isPaused)}
              className={`p-2 rounded transition-colors ${isPaused ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'}`}
              title={isPaused ? 'Resume' : 'Pause'}
            >
              {isPaused ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
            </button>
          </div>

          <div className="flex items-center gap-2 bg-gray-800 rounded-lg p-1">
            <Gauge className="w-4 h-4 text-gray-400 ml-2" />
            {[0.5, 1, 2].map((s) => (
              <button
                key={s}
                onClick={() => setSpeed(s as 0.5 | 1 | 2)}
                className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                  speed === s 
                    ? 'bg-blue-600 text-white' 
                    : 'text-gray-300 hover:bg-gray-700'
                }`}
              >
                {s}x
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2 bg-gray-800 rounded-lg px-3 py-2">
            <Filter className="w-4 h-4 text-gray-400" />
            <span className="text-sm text-gray-400">Filter:</span>
            <div className="flex gap-1">
              {allSources.map((source) => (
                <button
                  key={source}
                  onClick={() => toggleSource(source)}
                  className={`px-2 py-1 rounded text-xs font-medium transition-colors ${
                    selectedSources.has(source)
                      ? `${SOURCE_COLORS[source]} text-white`
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  }`}
                >
                  {source}
                </button>
              ))}
            </div>
            {selectedSources.size > 0 && (
              <button
                onClick={clearFilters}
                className="ml-2 text-xs text-gray-400 hover:text-white"
              >
                Clear
              </button>
            )}
          </div>

          <button
            onClick={handleClear}
            className="flex items-center gap-2 px-3 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg transition-colors text-sm"
          >
            <X className="w-4 h-4" />
            Clear All
          </button>

          <div className="text-sm text-gray-400">
            {filteredEvents.length} events
          </div>
        </div>

        {error && (
          <div className="mt-3 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}
      </div>

      <div className="flex-1 relative" style={{ minHeight: '500px' }}>
        {LANE_NAMES.map((laneName, laneIndex) => {
          const LaneIcon = LANE_ICONS[laneIndex];
          const laneEvents = filteredEvents.filter(e => getLaneForEvent(e) === laneIndex);

          return (
            <div
              key={laneName}
              className="h-[100px] border-b border-gray-800 last:border-b-0 relative bg-gray-950/50"
            >
              <div className="absolute left-0 top-0 bottom-0 w-32 bg-gradient-to-r from-gray-900 to-transparent z-10 flex items-center px-4">
                <div className="flex items-center gap-2">
                  <LaneIcon className="w-5 h-5 text-gray-400" />
                  <span className="text-sm font-medium text-gray-300">{laneName}</span>
                </div>
              </div>

              <div className="absolute top-0 bottom-0 left-32 right-0">
                <AnimatePresence mode="popLayout">
                  {laneEvents.map((event) => {
                    const yPosition = Math.random() * 60 + 20;
                    
                    return (
                      <motion.div
                        key={event.id}
                        initial={{ x: 0, opacity: 0, scale: 0.8 }}
                        animate={{ 
                          x: window.innerWidth - 400, 
                          opacity: 1, 
                          scale: 1,
                        }}
                        exit={{ opacity: 0, scale: 0.5 }}
                        transition={{
                          x: { 
                            duration: getAnimationDuration(), 
                            ease: 'linear' 
                          },
                          opacity: { duration: 0.5 },
                          scale: { duration: 0.5 }
                        }}
                        className="absolute cursor-pointer z-20"
                        style={{
                          left: '20px',
                          top: `${yPosition}%`,
                          transform: 'translateY(-50%)'
                        }}
                        onClick={() => setSelectedEvent(event)}
                      >
                        <div className={`${SOURCE_COLORS[event.source_system]} rounded-full px-3 py-1 shadow-lg hover:shadow-xl transition-shadow`}>
                          <div className="flex items-center gap-2">
                            <div className="w-2 h-2 bg-white rounded-full" />
                            <span className="text-xs font-medium text-white whitespace-nowrap">
                              {event.entity}
                            </span>
                          </div>
                        </div>
                      </motion.div>
                    );
                  })}
                </AnimatePresence>
              </div>
            </div>
          );
        })}
      </div>

      {selectedEvent && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setSelectedEvent(null)}>
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            className="bg-gray-900 rounded-xl border border-gray-800 p-6 max-w-lg w-full shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-white">Event Details</h3>
              <button
                onClick={() => setSelectedEvent(null)}
                className="p-1 hover:bg-gray-800 rounded transition-colors"
              >
                <X className="w-5 h-5 text-gray-400" />
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="text-xs text-gray-400 uppercase tracking-wide">Event ID</label>
                <p className="text-sm text-white font-mono mt-1">{selectedEvent.id}</p>
              </div>

              <div>
                <label className="text-xs text-gray-400 uppercase tracking-wide">Timestamp</label>
                <p className="text-sm text-white mt-1">
                  {new Date(selectedEvent.ts).toLocaleString()}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-400 uppercase tracking-wide">Source System</label>
                  <p className={`text-sm font-medium mt-1 ${SOURCE_TEXT_COLORS[selectedEvent.source_system]}`}>
                    {selectedEvent.source_system}
                  </p>
                </div>

                <div>
                  <label className="text-xs text-gray-400 uppercase tracking-wide">Entity</label>
                  <p className="text-sm text-white mt-1">{selectedEvent.entity}</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-400 uppercase tracking-wide">Stage</label>
                  <p className="text-sm text-white mt-1">{selectedEvent.stage}</p>
                </div>

                <div>
                  <label className="text-xs text-gray-400 uppercase tracking-wide">Lane</label>
                  <p className="text-sm text-white mt-1">{LANE_NAMES[getLaneForEvent(selectedEvent)]}</p>
                </div>
              </div>

              {selectedEvent.meta && Object.keys(selectedEvent.meta).length > 0 && (
                <div>
                  <label className="text-xs text-gray-400 uppercase tracking-wide">Metadata</label>
                  <div className="mt-2 bg-gray-800 rounded-lg p-3">
                    <pre className="text-xs text-gray-300 overflow-auto max-h-40">
                      {JSON.stringify(selectedEvent.meta, null, 2)}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        </div>
      )}
    </div>
  );
}
