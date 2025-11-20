import { Shield, Info, Activity } from 'lucide-react';
import AAMGauntlet from '../features/aam-gauntlet';

export default function AAMGauntletPage() {
  return (
    <div className="max-w-full mx-auto">
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-red-500/10 rounded-lg">
            <Shield className="w-8 h-8 text-red-400" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-white">AAM Gauntlet</h1>
            <p className="text-gray-400">Stress Testing Demo for Adaptive API Mesh</p>
          </div>
        </div>

        <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6 mb-6">
          <div className="flex items-start gap-3 mb-4">
            <Info className="w-5 h-5 text-cyan-400 mt-1 flex-shrink-0" />
            <div className="space-y-3">
              <p className="text-gray-300 leading-relaxed">
                Test the resilience and adaptive capabilities of our Adaptive API Mesh (AAM) under various chaos conditions. 
                This demo simulates real-world failure scenarios including network issues, rate limiting, token expiry, and schema drift.
              </p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div className="bg-gray-800/30 border border-gray-700 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-2xl">🔐</span>
              <h3 className="text-sm font-semibold text-cyan-400">Token Expiry</h3>
            </div>
            <p className="text-xs text-gray-400">Watch AAM auto-refresh OAuth tokens when they expire</p>
          </div>
          <div className="bg-gray-800/30 border border-gray-700 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-2xl">⚡</span>
              <h3 className="text-sm font-semibold text-cyan-400">Rate Limiting</h3>
            </div>
            <p className="text-xs text-gray-400">See intelligent backoff and retry under API pressure</p>
          </div>
          <div className="bg-gray-800/30 border border-gray-700 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-2xl">🔄</span>
              <h3 className="text-sm font-semibold text-cyan-400">Schema Drift</h3>
            </div>
            <p className="text-xs text-gray-400">Observe adaptation to changing API schemas</p>
          </div>
          <div className="bg-gray-800/30 border border-gray-700 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-2xl">🌐</span>
              <h3 className="text-sm font-semibold text-cyan-400">Network Chaos</h3>
            </div>
            <p className="text-xs text-gray-400">Test resilience to connection issues and timeouts</p>
          </div>
        </div>

        <div className="bg-blue-600/10 border border-blue-500/30 rounded-lg p-4 mb-6">
          <div className="flex items-start gap-3">
            <Activity className="w-5 h-5 text-blue-400 mt-0.5" />
            <div className="text-sm text-blue-300">
              <span className="font-semibold">Quick Start:</span> Click on any connector in the topology view below to see detailed metrics. 
              Run chaos scenarios to watch the AAM adapt in real-time. Monitor the DLQ (Dead Letter Queue) for failed requests and automatic retries.
            </div>
          </div>
        </div>
      </div>

      <AAMGauntlet />

      <div className="mt-6 text-center text-sm text-gray-500">
        <p>AAM Gauntlet runs on separate services (API Farm: 8000, AAM: 8080)</p>
        <p className="mt-1">Components integrated natively into AutonomOS frontend</p>
      </div>
    </div>
  );
}