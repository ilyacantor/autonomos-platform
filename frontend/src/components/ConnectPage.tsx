import { useState, useEffect } from 'react';
import {
  GitBranch,
  Shield,
  AlertTriangle,
  Loader2
} from 'lucide-react';
import DemoIframeContainer from './DemoIframeContainer';

const AAM_IFRAME_URL = 'https://autonomos-mesh-ilyacantor.replit.app/';

interface MeshMetrics {
  activeConnections: number;
  healingEvents: number;
  driftAlerts: number;
  loading: boolean;
  error: string | null;
}

export default function ConnectPage() {
  const [meshMetrics, setMeshMetrics] = useState<MeshMetrics>({
    activeConnections: 0,
    healingEvents: 0,
    driftAlerts: 0,
    loading: true,
    error: null
  });

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const response = await fetch('/api/v1/aam/metrics');
        if (!response.ok) {
          throw new Error(`API error: ${response.status}`);
        }
        const data = await response.json();

        setMeshMetrics({
          activeConnections: data.active_connections ?? data.total_connections ?? 0,
          healingEvents: data.successful_repairs_24h ?? 0,
          driftAlerts: data.active_drift_detections_24h ?? 0,
          loading: false,
          error: null
        });
      } catch (err) {
        setMeshMetrics(prev => ({
          ...prev,
          loading: false,
          error: err instanceof Error ? err.message : 'Failed to fetch metrics'
        }));
      }
    };

    fetchMetrics();

    // Refresh every 30 seconds
    const interval = setInterval(fetchMetrics, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <div className="flex-shrink-0 px-3 sm:px-4 lg:px-6 pt-3 pb-2">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div className="flex items-center gap-4">
            <h1 className="text-lg sm:text-xl font-bold text-white flex items-center gap-2">
              <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-gradient-to-br from-cyan-500 to-purple-600 text-white text-xs font-bold">
                2
              </span>
              Connect Your Systems
            </h1>
            <div className="hidden md:flex items-center gap-4 text-xs">
              {meshMetrics.loading ? (
                <div className="flex items-center gap-1.5 text-gray-400">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Loading...</span>
                </div>
              ) : meshMetrics.error ? (
                <div className="flex items-center gap-1.5 text-red-400">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  <span>API unavailable</span>
                </div>
              ) : (
                <>
                  <div className="flex items-center gap-1.5 text-green-400">
                    <GitBranch className="w-3.5 h-3.5" />
                    <span>{meshMetrics.activeConnections} active</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-blue-400">
                    <Shield className="w-3.5 h-3.5" />
                    <span>{meshMetrics.healingEvents} repairs/24h</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-orange-400">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    <span>{meshMetrics.driftAlerts} drift/24h</span>
                  </div>
                </>
              )}
            </div>
          </div>
          <a
            href={AAM_IFRAME_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-cyan-600/20 hover:bg-cyan-600/30 border border-cyan-500/40 hover:border-cyan-500/60 rounded-lg text-cyan-400 hover:text-cyan-300 text-xs font-medium transition-all duration-200 self-start"
          >
            Full Screen
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </a>
        </div>
      </div>

      <div className="flex-1 min-h-0 px-3 sm:px-4 lg:px-6 pb-3">
        <div className="h-full bg-gray-800 rounded-lg border border-gray-700/50 overflow-hidden shadow-lg">
          <DemoIframeContainer
            src={AAM_IFRAME_URL}
            title="AAM Mesh Interface"
            allow="fullscreen"
            minHeight="800px"
          />
        </div>
      </div>
    </div>
  );
}
