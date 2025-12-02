import { useState, useEffect } from 'react';
import { 
  GitBranch,
  Network,
  Zap,
  Brain,
  Shield,
  AlertTriangle
} from 'lucide-react';
import DemoStep from './DemoStep';

const AAM_IFRAME_URL = 'https://autonomos-mesh-ilyacantor.replit.app/';

export default function ConnectPage() {
  const [meshMetrics, setMeshMetrics] = useState({
    activeConnections: 287,
    healingEvents: 12,
    driftAlerts: 3,
    llmCalls: 1234,
    llmTokens: 2100000,
    ragMappings: 14876
  });

  useEffect(() => {
    const interval = setInterval(() => {
      setMeshMetrics(prev => ({
        activeConnections: prev.activeConnections + Math.floor(Math.random() * 3) - 1,
        healingEvents: Math.max(0, prev.healingEvents + Math.floor(Math.random() * 3) - 1),
        driftAlerts: Math.max(0, prev.driftAlerts + Math.floor(Math.random() * 2) - 0.5),
        llmCalls: prev.llmCalls + Math.floor(Math.random() * 5),
        llmTokens: prev.llmTokens + Math.floor(Math.random() * 1000),
        ragMappings: prev.ragMappings + Math.floor(Math.random() * 10)
      }));
    }, 3000);
    
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <div className="flex-shrink-0 px-3 sm:px-4 lg:px-6 pt-4 sm:pt-6 pb-3">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-4">
          <div>
            <h1 className="text-xl sm:text-2xl lg:text-3xl font-bold text-white flex items-center gap-2 sm:gap-3">
              <span className="inline-flex items-center justify-center w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-gradient-to-br from-cyan-500 to-purple-600 text-white text-sm sm:text-base font-bold">
                2
              </span>
              Connect Your Systems
            </h1>
            <p className="text-sm sm:text-base text-gray-300 mt-1">
              Adaptive API Mesh with self-healing data connectivity
            </p>
          </div>
          <a
            href={AAM_IFRAME_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 sm:px-4 sm:py-2 bg-cyan-600/20 hover:bg-cyan-600/30 border border-cyan-500/40 hover:border-cyan-500/60 rounded-lg text-cyan-400 hover:text-cyan-300 text-xs sm:text-sm font-medium transition-all duration-200 self-start"
          >
            Full Screen
            <svg className="w-3.5 h-3.5 sm:w-4 sm:h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </a>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-3 gap-2 sm:gap-3">
          <div className="bg-black/40 backdrop-blur-sm border border-green-500/30 rounded-lg p-2 sm:p-3">
            <div className="flex items-center justify-between mb-1 sm:mb-2">
              <div className="flex items-center gap-1.5">
                <GitBranch className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-green-400" />
                <span className="text-xs font-medium text-gray-300 hidden sm:inline">Active Connections</span>
                <span className="text-xs font-medium text-gray-300 sm:hidden">Connections</span>
              </div>
              <div className="w-1.5 h-1.5 sm:w-2 sm:h-2 bg-green-500 rounded-full animate-pulse" />
            </div>
            <div className="text-xl sm:text-2xl font-bold text-white">{meshMetrics.activeConnections}</div>
          </div>

          <div className="bg-black/40 backdrop-blur-sm border border-blue-500/30 rounded-lg p-2 sm:p-3">
            <div className="flex items-center justify-between mb-1 sm:mb-2">
              <div className="flex items-center gap-1.5">
                <Shield className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-blue-400" />
                <span className="text-xs font-medium text-gray-300 hidden sm:inline">Self-Healing</span>
                <span className="text-xs font-medium text-gray-300 sm:hidden">Healing</span>
              </div>
              <div className="w-1.5 h-1.5 sm:w-2 sm:h-2 bg-blue-500 rounded-full animate-pulse" />
            </div>
            <div className="text-xl sm:text-2xl font-bold text-white">{meshMetrics.healingEvents}</div>
          </div>

          <div className="bg-black/40 backdrop-blur-sm border border-orange-500/30 rounded-lg p-2 sm:p-3 col-span-2 lg:col-span-1">
            <div className="flex items-center justify-between mb-1 sm:mb-2">
              <div className="flex items-center gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-orange-400" />
                <span className="text-xs font-medium text-gray-300">Schema Drift</span>
              </div>
              <div className="w-1.5 h-1.5 sm:w-2 sm:h-2 bg-orange-500 rounded-full animate-pulse" />
            </div>
            <div className="text-xl sm:text-2xl font-bold text-white">{meshMetrics.driftAlerts}</div>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 sm:gap-3 mt-2 sm:mt-3">
          <div className="bg-black/40 backdrop-blur-sm border border-purple-500/30 rounded-lg p-2 sm:p-3">
            <div className="flex items-center gap-1.5 mb-1 sm:mb-2">
              <Zap className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-purple-400" />
              <span className="text-xs font-medium text-gray-300">LLM Intelligence</span>
            </div>
            <div className="flex items-center justify-between text-xs sm:text-sm">
              <span className="text-gray-400">Calls</span>
              <span className="font-bold text-white">{meshMetrics.llmCalls.toLocaleString()}</span>
            </div>
            <div className="flex items-center justify-between text-xs sm:text-sm mt-0.5">
              <span className="text-gray-400">Tokens</span>
              <span className="font-bold text-white">{(meshMetrics.llmTokens / 1000000).toFixed(2)}M</span>
            </div>
          </div>

          <div className="bg-black/40 backdrop-blur-sm border border-green-500/30 rounded-lg p-2 sm:p-3">
            <div className="flex items-center gap-1.5 mb-1 sm:mb-2">
              <Brain className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-green-400" />
              <span className="text-xs font-medium text-gray-300">RAG Learning</span>
            </div>
            <div className="flex items-center justify-between text-xs sm:text-sm">
              <span className="text-gray-400">Mappings</span>
              <span className="font-bold text-white">{meshMetrics.ragMappings.toLocaleString()}</span>
            </div>
            <div className="flex items-center justify-between text-xs sm:text-sm mt-0.5">
              <span className="text-gray-400">Confidence</span>
              <span className="font-bold text-green-400">86%</span>
            </div>
          </div>
        </div>
      </div>

      <div className="flex-1 min-h-0 px-3 sm:px-4 lg:px-6 pb-4">
        <div className="h-full bg-gray-800 rounded-lg border border-gray-700/50 overflow-hidden shadow-lg">
          <div className="relative w-full h-full" style={{ minHeight: '300px' }}>
            <iframe
              src={AAM_IFRAME_URL}
              className="absolute inset-0 w-full h-full"
              title="AAM Mesh Interface"
              allow="fullscreen"
              style={{
                border: 'none',
                backgroundColor: '#1a1a1a'
              }}
            />
          </div>
        </div>
      </div>

      <div className="flex-shrink-0 px-3 sm:px-4 lg:px-6 pb-3">
        <div className="flex items-start gap-2 text-xs sm:text-sm text-gray-400 bg-gray-800/50 rounded-lg px-3 py-2 border border-gray-700/30">
          <span className="text-cyan-400 font-medium flex-shrink-0">Try this:</span>
          <span className="text-gray-300">Add a new data source and watch the mesh automatically configure the connection and detect schema.</span>
        </div>
      </div>
    </div>
  );
}
