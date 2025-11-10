import { useState } from 'react';
import { Play, Loader2, CheckCircle, AlertCircle, Database } from 'lucide-react';
import { aoaApi } from '../services/aoaApi';

interface ScanStatus {
  status: 'idle' | 'running' | 'completed' | 'error';
  message?: string;
  total_assets?: number;
  high_risk?: number;
  medium_risk?: number;
  low_risk?: number;
  processing_time_ms?: number;
}

export default function DemoScanPanel() {
  const [scanStatus, setScanStatus] = useState<ScanStatus>({ status: 'idle' });
  const [isScanning, setIsScanning] = useState(false);

  const handleDemoScan = async () => {
    setIsScanning(true);
    setScanStatus({ status: 'running', message: 'Initiating full asset discovery scan...' });

    try {
      const result = await aoaApi.demoScan();
      
      setScanStatus({
        status: 'completed',
        message: 'Full asset scan completed successfully!',
        total_assets: result.total_assets_discovered,
        high_risk: result.high_risk_count,
        medium_risk: result.medium_risk_count,
        low_risk: result.low_risk_count,
        processing_time_ms: result.processing_time_ms
      });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Demo scan failed';
      setScanStatus({ 
        status: 'error', 
        message: errorMessage 
      });
      console.error('[Demo Scan] Error:', err);
    } finally {
      setIsScanning(false);
    }
  };

  return (
    <div className="bg-gradient-to-br from-purple-900/30 via-gray-900/40 to-cyan-900/30 rounded-xl border-2 border-cyan-500/40 p-6 shadow-2xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 bg-gradient-to-br from-cyan-500 to-purple-600 rounded-xl flex items-center justify-center">
            <Database className="w-7 h-7 text-white" />
          </div>
          <div>
            <h3 className="text-2xl font-bold text-white">Demo Asset Scanner</h3>
            <p className="text-sm text-gray-400">
              Trigger full discovery scan of all assets from AOD training data
            </p>
          </div>
        </div>
        
        {/* Scan Button */}
        <button
          onClick={handleDemoScan}
          disabled={isScanning}
          className={`flex items-center gap-2 px-6 py-3 rounded-lg font-medium transition-all ${
            isScanning
              ? 'bg-gray-600 cursor-not-allowed opacity-70'
              : 'bg-gradient-to-r from-cyan-500 to-purple-600 hover:from-cyan-600 hover:to-purple-700 shadow-lg shadow-cyan-500/50'
          } text-white`}
        >
          {isScanning ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Scanning...
            </>
          ) : (
            <>
              <Play className="w-5 h-5" />
              Start Demo Scan
            </>
          )}
        </button>
      </div>

      {/* Status Display */}
      {scanStatus.status !== 'idle' && (
        <div className="space-y-4">
          {/* Status Message */}
          <div className={`flex items-start gap-3 p-4 rounded-lg border ${
            scanStatus.status === 'running' 
              ? 'bg-blue-500/10 border-blue-500/30'
              : scanStatus.status === 'completed'
              ? 'bg-green-500/10 border-green-500/30'
              : 'bg-red-500/10 border-red-500/30'
          }`}>
            {scanStatus.status === 'running' && <Loader2 className="w-5 h-5 text-blue-400 animate-spin flex-shrink-0 mt-0.5" />}
            {scanStatus.status === 'completed' && <CheckCircle className="w-5 h-5 text-green-400 flex-shrink-0 mt-0.5" />}
            {scanStatus.status === 'error' && <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />}
            
            <div>
              <div className={`font-medium mb-1 ${
                scanStatus.status === 'running' ? 'text-blue-400' :
                scanStatus.status === 'completed' ? 'text-green-400' :
                'text-red-400'
              }`}>
                {scanStatus.status === 'running' && 'Scanning in progress...'}
                {scanStatus.status === 'completed' && 'Scan completed!'}
                {scanStatus.status === 'error' && 'Scan failed'}
              </div>
              <div className="text-sm text-gray-300">{scanStatus.message}</div>
            </div>
          </div>

          {/* Results Stats */}
          {scanStatus.status === 'completed' && scanStatus.total_assets !== undefined && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-gray-800/60 rounded-lg p-4 border border-gray-700">
                <div className="text-sm text-gray-400 mb-1">Total Assets</div>
                <div className="text-3xl font-bold text-cyan-400">{scanStatus.total_assets}</div>
              </div>
              
              <div className="bg-gray-800/60 rounded-lg p-4 border border-red-700/50">
                <div className="text-sm text-gray-400 mb-1">High Risk</div>
                <div className="text-3xl font-bold text-red-400">{scanStatus.high_risk || 0}</div>
                <div className="text-xs text-gray-500 mt-1">Requires HITL review</div>
              </div>
              
              <div className="bg-gray-800/60 rounded-lg p-4 border border-yellow-700/50">
                <div className="text-sm text-gray-400 mb-1">Medium Risk</div>
                <div className="text-3xl font-bold text-yellow-400">{scanStatus.medium_risk || 0}</div>
                <div className="text-xs text-gray-500 mt-1">Needs validation</div>
              </div>
              
              <div className="bg-gray-800/60 rounded-lg p-4 border border-green-700/50">
                <div className="text-sm text-gray-400 mb-1">Low Risk</div>
                <div className="text-3xl font-bold text-green-400">{scanStatus.low_risk || 0}</div>
                <div className="text-xs text-gray-500 mt-1">Auto-approved</div>
              </div>
            </div>
          )}

          {/* Processing Time */}
          {scanStatus.processing_time_ms !== undefined && (
            <div className="text-center text-sm text-gray-400">
              Processing time: <span className="text-cyan-400 font-medium">{scanStatus.processing_time_ms}ms</span>
            </div>
          )}

          {/* Next Steps */}
          {scanStatus.status === 'completed' && (scanStatus.high_risk || 0) + (scanStatus.medium_risk || 0) > 0 && (
            <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4">
              <div className="text-yellow-400 font-medium mb-2">⚠️ Human Review Required</div>
              <div className="text-sm text-gray-300">
                {(scanStatus.high_risk || 0) + (scanStatus.medium_risk || 0)} assets flagged for Human-in-the-Loop (HITL) review. 
                Check the Discovery tab to review and make decisions on edge cases.
              </div>
            </div>
          )}
        </div>
      )}

      {/* Info Box (when idle) */}
      {scanStatus.status === 'idle' && (
        <div className="bg-gray-800/40 border border-gray-700 rounded-lg p-4">
          <div className="text-sm text-gray-400 space-y-2">
            <p>
              <span className="font-medium text-cyan-400">What happens when you start the scan?</span>
            </p>
            <ul className="list-disc list-inside space-y-1 ml-2">
              <li>Full discovery scan of all assets from AOD training data</li>
              <li>Assets categorized by risk level (High, Medium, Low)</li>
              <li>High/medium risk assets queued for HITL review</li>
              <li>Results viewable in Discovery tab dashboard</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
