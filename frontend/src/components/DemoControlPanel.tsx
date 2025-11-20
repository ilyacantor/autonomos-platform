import { useState } from 'react';
import { Play, CheckCircle, XCircle, Loader, Crown, Database, Zap, GitBranch } from 'lucide-react';

interface DemoStage {
  stage: string;
  status: 'success' | 'error' | 'pending';
  message: string;
  data?: Record<string, any>;
}

interface DemoResponse {
  success: boolean;
  message: string;
  aam_enabled: boolean;
  connection_id?: string;
  entities_discovered?: number;
  agent_execution_id?: string;
  stages: DemoStage[];
}

const CANNED_PROMPTS = [
  {
    id: 'start_demo',
    label: 'Start Demo',
    prompt: 'start demo',
    description: 'Run full AOD → AAM → DCL → Agent pipeline with Salesforce data'
  },
  {
    id: 'enable_aam',
    label: 'Enable AAM',
    prompt: 'enable production connectors',
    description: 'Switch from mock data to real AAM production connectors'
  },
  {
    id: 'check_status',
    label: 'Check Status',
    prompt: 'check pipeline status',
    description: 'Verify all components are ready for demo'
  }
];

const SOURCE_TYPES = [
  { id: 'salesforce', label: 'Salesforce', icon: Database, color: 'blue' },
  { id: 'mongodb', label: 'MongoDB', icon: Database, color: 'green' },
  { id: 'filesource', label: 'FileSource', icon: Database, color: 'purple' },
  { id: 'supabase', label: 'Supabase', icon: Database, color: 'amber' }
];

export default function DemoControlPanel() {
  const [isRunning, setIsRunning] = useState(false);
  const [result, setResult] = useState<DemoResponse | null>(null);
  const [selectedSource, setSelectedSource] = useState('salesforce');
  const [error, setError] = useState<string | null>(null);

  const handleEnableAAM = async () => {
    setIsRunning(true);
    setError(null);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/v1/admin/feature-flags/enable-aam', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : ''
        }
      });

      if (!response.ok) {
        throw new Error(`Failed to enable AAM: ${response.statusText}`);
      }

      const data = await response.json();
      alert(`✅ ${data.message}`);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMsg);
      alert(`❌ Error: ${errorMsg}`);
    } finally {
      setIsRunning(false);
    }
  };

  const handleCheckStatus = async () => {
    setIsRunning(true);
    setError(null);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/v1/demo/pipeline/status', {
        headers: {
          'Authorization': token ? `Bearer ${token}` : ''
        }
      });
      
      if (!response.ok) {
        throw new Error(`Failed to check status: ${response.statusText}`);
      }

      const data = await response.json();
      const statusMessage = data.ready 
        ? `✅ Pipeline Ready!\n\nAAM: ${data.status.aam_enabled ? 'Enabled' : 'Disabled'}\nOnboarding: ${data.status.onboarding_service_ready ? 'Ready' : 'Not Ready'}\nDCL: ${data.status.dcl_client_ready ? 'Ready' : 'Not Ready'}\nAgent: ${data.status.agent_executor_ready ? 'Ready' : 'Not Ready'}`
        : `⚠️ ${data.message}\n\nNext Steps:\n${data.next_steps?.join('\n') || 'Check component status'}`;
      
      alert(statusMessage);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMsg);
      alert(`❌ Error: ${errorMsg}`);
    } finally {
      setIsRunning(false);
    }
  };

  const handleStartDemo = async () => {
    setIsRunning(true);
    setError(null);
    setResult(null);

    try {
      const token = localStorage.getItem('token');
      const response = await fetch(
        `/api/v1/demo/pipeline/end-to-end?source_type=${selectedSource}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': token ? `Bearer ${token}` : ''
          }
        }
      );

      if (!response.ok) {
        throw new Error(`Demo failed: ${response.statusText}`);
      }

      const data: DemoResponse = await response.json();
      setResult(data);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMsg);
    } finally {
      setIsRunning(false);
    }
  };

  const getStageIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="w-5 h-5 text-green-400" />;
      case 'error':
        return <XCircle className="w-5 h-5 text-red-400" />;
      default:
        return <Loader className="w-5 h-5 text-gray-400 animate-spin" />;
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-gradient-to-r from-yellow-900/20 to-amber-900/20 border border-yellow-600/30 rounded-lg p-6">
        <div className="flex items-center gap-3 mb-4">
          <Crown className="w-8 h-8 text-yellow-400" />
          <div>
            <h2 className="text-2xl font-bold text-white">CEO Demo Control Panel</h2>
            <p className="text-gray-300 text-sm">Execute end-to-end pipeline demonstrations</p>
          </div>
        </div>

        <div className="space-y-4">
          <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
            <h3 className="text-sm font-semibold text-gray-300 mb-3">Quick Actions</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <button
                onClick={handleEnableAAM}
                disabled={isRunning}
                className="flex items-center justify-center gap-2 px-4 py-3 bg-green-600 hover:bg-green-700 disabled:bg-gray-700 text-white rounded-lg font-medium transition-colors disabled:cursor-not-allowed"
              >
                <Zap className="w-4 h-4" />
                Enable AAM
              </button>

              <button
                onClick={handleCheckStatus}
                disabled={isRunning}
                className="flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 text-white rounded-lg font-medium transition-colors disabled:cursor-not-allowed"
              >
                <GitBranch className="w-4 h-4" />
                Check Status
              </button>

              <button
                onClick={handleStartDemo}
                disabled={isRunning}
                className="flex items-center justify-center gap-2 px-4 py-3 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-700 text-white rounded-lg font-medium transition-colors disabled:cursor-not-allowed"
              >
                {isRunning ? (
                  <Loader className="w-4 h-4 animate-spin" />
                ) : (
                  <Play className="w-4 h-4" />
                )}
                Start Demo
              </button>
            </div>
          </div>

          <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
            <h3 className="text-sm font-semibold text-gray-300 mb-3">Select Data Source</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              {SOURCE_TYPES.map((source) => {
                const IconComponent = source.icon;
                return (
                  <button
                    key={source.id}
                    onClick={() => setSelectedSource(source.id)}
                    className={`flex items-center gap-2 px-3 py-2 rounded-lg font-medium transition-all ${
                      selectedSource === source.id
                        ? `bg-${source.color}-600 text-white shadow-lg`
                        : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    }`}
                  >
                    <IconComponent className="w-4 h-4" />
                    <span className="text-sm">{source.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {error && (
            <div className="bg-red-900/20 border border-red-600/50 rounded-lg p-4">
              <div className="flex items-center gap-2 text-red-400">
                <XCircle className="w-5 h-5" />
                <span className="font-medium">Error:</span>
                <span>{error}</span>
              </div>
            </div>
          )}

          {result && (
            <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
              <div className="flex items-center gap-2 mb-4">
                {result.success ? (
                  <CheckCircle className="w-6 h-6 text-green-400" />
                ) : (
                  <XCircle className="w-6 h-6 text-red-400" />
                )}
                <h3 className="text-lg font-semibold text-white">{result.message}</h3>
              </div>

              <div className="space-y-3">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <div className="bg-gray-900/50 rounded p-3">
                    <div className="text-xs text-gray-400 mb-1">AAM Status</div>
                    <div className={`text-sm font-medium ${result.aam_enabled ? 'text-green-400' : 'text-yellow-400'}`}>
                      {result.aam_enabled ? 'Production' : 'Legacy'}
                    </div>
                  </div>
                  {result.connection_id && (
                    <div className="bg-gray-900/50 rounded p-3">
                      <div className="text-xs text-gray-400 mb-1">Connection ID</div>
                      <div className="text-sm font-medium text-blue-400 truncate">
                        {result.connection_id}
                      </div>
                    </div>
                  )}
                  {result.entities_discovered !== undefined && (
                    <div className="bg-gray-900/50 rounded p-3">
                      <div className="text-xs text-gray-400 mb-1">Entities</div>
                      <div className="text-sm font-medium text-purple-400">
                        {result.entities_discovered}
                      </div>
                    </div>
                  )}
                  {result.agent_execution_id && (
                    <div className="bg-gray-900/50 rounded p-3">
                      <div className="text-xs text-gray-400 mb-1">Execution ID</div>
                      <div className="text-sm font-medium text-amber-400 truncate">
                        {result.agent_execution_id}
                      </div>
                    </div>
                  )}
                </div>

                <div className="space-y-2">
                  <h4 className="text-sm font-semibold text-gray-300">Pipeline Stages</h4>
                  {result.stages.map((stage, idx) => (
                    <div
                      key={idx}
                      className="flex items-start gap-3 bg-gray-900/30 rounded p-3"
                    >
                      <div className="mt-0.5">{getStageIcon(stage.status)}</div>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-white mb-1">
                          {stage.stage.replace(/_/g, ' ')}
                        </div>
                        <div className="text-xs text-gray-400">{stage.message}</div>
                        {stage.data && Object.keys(stage.data).length > 0 && (
                          <div className="mt-2 text-xs text-gray-500 font-mono">
                            {JSON.stringify(stage.data, null, 2)}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          <div className="bg-gray-900/30 border border-gray-700/50 rounded-lg p-4">
            <h3 className="text-sm font-semibold text-gray-300 mb-2">Canned Prompts</h3>
            <p className="text-xs text-gray-400 mb-3">
              Type any of these phrases in the chat to trigger actions:
            </p>
            <div className="space-y-2">
              {CANNED_PROMPTS.map((prompt) => (
                <div key={prompt.id} className="flex items-start gap-2 text-xs">
                  <code className="bg-gray-800 text-green-400 px-2 py-1 rounded font-mono">
                    {prompt.prompt}
                  </code>
                  <span className="text-gray-500">→ {prompt.description}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
