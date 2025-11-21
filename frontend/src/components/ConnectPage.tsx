import { useState, useEffect } from 'react';
import { 
  GitBranch,
  Network,
  Zap,
  Brain,
  Shield,
  AlertTriangle
} from 'lucide-react';

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
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">AOS AAM (Connect)</h1>
          <p className="text-gray-400">
            Adaptive API Mesh - Self-healing data connectivity
          </p>
        </div>
      </div>

      <div className="bg-gradient-to-br from-purple-900/20 via-blue-900/20 to-green-900/20 rounded-xl border border-purple-500/30 overflow-hidden">
        <div className="p-6 border-b border-purple-500/20 bg-black/40">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="relative">
                <Network className="w-6 h-6 text-purple-400" />
                <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full animate-pulse" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-white flex items-center gap-2">
                  AAM Adaptive API Mesh
                  <span className="px-2 py-0.5 bg-amber-500/20 border border-amber-500/40 rounded text-xs font-medium text-amber-400">
                    DEMO
                  </span>
                </h2>
                <p className="text-sm text-gray-400">Real-time orchestration intelligence and self-healing infrastructure</p>
              </div>
            </div>
          </div>
        </div>

        <div className="p-6 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-black/40 backdrop-blur-sm border border-green-500/30 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <GitBranch className="w-4 h-4 text-green-400" />
                  <span className="text-sm font-medium text-gray-300">Active Connections</span>
                </div>
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              </div>
              <div className="text-3xl font-bold text-white mb-1">{meshMetrics.activeConnections}</div>
              <div className="text-xs text-gray-400">Across 47 data sources</div>
            </div>

            <div className="bg-black/40 backdrop-blur-sm border border-blue-500/30 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Shield className="w-4 h-4 text-blue-400" />
                  <span className="text-sm font-medium text-gray-300">Self-Healing Events</span>
                </div>
                <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
              </div>
              <div className="text-3xl font-bold text-white mb-1">{meshMetrics.healingEvents}</div>
              <div className="text-xs text-gray-400">Auto-repairs last hour</div>
            </div>

            <div className="bg-black/40 backdrop-blur-sm border border-orange-500/30 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-orange-400" />
                  <span className="text-sm font-medium text-gray-300">Schema Drift</span>
                </div>
                <div className="w-2 h-2 bg-orange-500 rounded-full animate-pulse" />
              </div>
              <div className="text-3xl font-bold text-white mb-1">{meshMetrics.driftAlerts}</div>
              <div className="text-xs text-gray-400">Alerts detected</div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-black/40 backdrop-blur-sm border border-purple-500/30 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-3">
                <Zap className="w-4 h-4 text-purple-400" />
                <span className="text-sm font-medium text-gray-300">LLM Intelligence</span>
              </div>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-400">Total Calls</span>
                  <span className="text-lg font-bold text-white">{meshMetrics.llmCalls.toLocaleString()}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-400">Tokens Processed</span>
                  <span className="text-lg font-bold text-white">{(meshMetrics.llmTokens / 1000000).toFixed(2)}M</span>
                </div>
                <div className="mt-2 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-purple-500 to-blue-500 animate-pulse" style={{ width: '73%' }} />
                </div>
              </div>
            </div>

            <div className="bg-black/40 backdrop-blur-sm border border-green-500/30 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-3">
                <Brain className="w-4 h-4 text-green-400" />
                <span className="text-sm font-medium text-gray-300">RAG Learning</span>
              </div>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-400">Field Mappings</span>
                  <span className="text-lg font-bold text-white">{meshMetrics.ragMappings.toLocaleString()}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-400">Confidence Score</span>
                  <span className="text-lg font-bold text-green-400">86%</span>
                </div>
                <div className="mt-2 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-green-500 to-emerald-500 animate-pulse" style={{ width: '86%' }} />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-gray-800 rounded-lg border border-cyan-500/30 overflow-hidden">
        <div className="bg-gradient-to-r from-purple-600/20 to-blue-600/20 border-b border-purple-500/30 px-4 py-3">
          <h2 className="text-xl font-semibold text-white flex items-center gap-2">
            <svg className="w-6 h-6 text-purple-400" fill="currentColor" viewBox="0 0 20 20">
              <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z" />
            </svg>
            Interactive AAM Mesh
            <a 
              href="https://autonomos-mesh-ilyacantor.replit.app/" 
              target="_blank" 
              rel="noopener noreferrer"
              className="ml-auto text-sm text-purple-400 hover:text-purple-300 underline font-normal"
            >
              Open in new tab ↗
            </a>
          </h2>
        </div>
        <div className="relative" style={{ paddingBottom: '75%' }}>
          <iframe
            src="https://autonomos-mesh-ilyacantor.replit.app/"
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
  );
}
