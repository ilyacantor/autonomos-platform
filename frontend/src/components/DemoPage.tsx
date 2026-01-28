import { useState, useEffect, useCallback } from 'react';
import { Play, CheckCircle, Circle, Loader2, XCircle, Eye, Network, Database, Bot, ArrowRight } from 'lucide-react';
import DemoStep from './DemoStep';
import { API_CONFIG } from '../config/api';

interface PipelineStep {
  name: string;
  display_name: string;
  status: 'pending' | 'running' | 'success' | 'failed';
  message?: string;
  started_at?: string;
  completed_at?: string;
  data?: Record<string, any>;
}

interface PipelineJob {
  job_id: string;
  status: string;
  started_at: string;
  completed_at?: string;
  steps: PipelineStep[];
  current_step: number;
  total_steps: number;
  message: string;
}

const STEP_ICONS = {
  aod_discovery: Eye,
  aam_connect: Network,
  dcl_unify: Database,
};

const STEP_COLORS = {
  pending: 'text-gray-400 border-gray-600/40',
  running: 'text-cyan-400 border-cyan-500/50 animate-pulse',
  success: 'text-green-400 border-green-500/50',
  failed: 'text-red-400 border-red-500/50',
};

const NAV_LINKS = [
  { page: 'aos-overview', label: 'Overview', icon: Eye },
  { page: 'discover', label: 'AOD', icon: Eye },
  { page: 'connect', label: 'AAM', icon: Network },
  { page: 'unify-ask', label: 'DCL', icon: Database },
];

export default function DemoPage() {
  const [isRunning, setIsRunning] = useState(false);
  const [currentJob, setCurrentJob] = useState<PipelineJob | null>(null);
  const [error, setError] = useState<string | null>(null);

  const pollStatus = useCallback(async (jobId: string) => {
    try {
      const response = await fetch(API_CONFIG.buildApiUrl(`/demo/pipeline_status?job_id=${jobId}`));
      if (!response.ok) throw new Error('Failed to fetch status');
      const data: PipelineJob = await response.json();
      setCurrentJob(data);
      
      if (data.status === 'completed' || data.status === 'failed') {
        setIsRunning(false);
      } else {
        setTimeout(() => pollStatus(jobId), 1000);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      setIsRunning(false);
    }
  }, []);

  const runPipeline = async () => {
    setIsRunning(true);
    setError(null);
    setCurrentJob(null);
    
    try {
      const response = await fetch(API_CONFIG.buildApiUrl('/demo/run_pipeline'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      
      if (!response.ok) throw new Error('Failed to start pipeline');
      const data = await response.json();
      
      pollStatus(data.job_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      setIsRunning(false);
    }
  };

  const getStepIcon = (step: PipelineStep) => {
    const Icon = STEP_ICONS[step.name as keyof typeof STEP_ICONS] || Database;
    
    if (step.status === 'running') {
      return <Loader2 className="w-5 h-5 animate-spin" />;
    }
    if (step.status === 'success') {
      return <CheckCircle className="w-5 h-5" />;
    }
    if (step.status === 'failed') {
      return <XCircle className="w-5 h-5" />;
    }
    return <Circle className="w-5 h-5" />;
  };

  const navigateTo = (page: string) => {
    window.dispatchEvent(new CustomEvent('navigate', { detail: { page } }));
  };

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <DemoStep
        title="Run Full Demo"
        description="Execute the complete AutonomOS pipeline in one click. Watch as data flows from Discovery through Connection to Unification."
        instructions="Click 'Run Full Demo' to see the entire pipeline in action. Then explore each step individually."
      >
        <div className="h-full overflow-auto p-4 sm:p-6 lg:p-8">
          <div className="max-w-3xl mx-auto space-y-6">
            <div className="text-center">
              <button
                onClick={runPipeline}
                disabled={isRunning}
                className={`inline-flex items-center gap-3 px-8 py-4 rounded-xl text-lg font-bold transition-all duration-300 ${
                  isRunning
                    ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
                    : 'bg-gradient-to-r from-cyan-600 to-purple-600 hover:from-cyan-500 hover:to-purple-500 text-white shadow-lg hover:shadow-xl hover:scale-105'
                }`}
              >
                {isRunning ? (
                  <>
                    <Loader2 className="w-6 h-6 animate-spin" />
                    Running Pipeline...
                  </>
                ) : (
                  <>
                    <Play className="w-6 h-6" />
                    Run Full Demo
                  </>
                )}
              </button>
              
              {currentJob?.status === 'completed' && (
                <div className="mt-4 text-green-400 font-medium">
                  Pipeline completed successfully!
                </div>
              )}
              
              {error && (
                <div className="mt-4 text-red-400 font-medium">
                  {error}
                </div>
              )}
            </div>

            {(currentJob || isRunning) && (
              <div className="bg-gray-900/50 rounded-xl border border-gray-700/50 overflow-hidden">
                <div className="bg-gradient-to-r from-gray-800 to-gray-900 px-4 py-3 border-b border-gray-700/50">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">Pipeline Progress</h3>
                    {currentJob && (
                      <span className={`text-xs font-medium px-2 py-1 rounded-full ${
                        currentJob.status === 'completed' ? 'bg-green-500/20 text-green-400' :
                        currentJob.status === 'failed' ? 'bg-red-500/20 text-red-400' :
                        'bg-cyan-500/20 text-cyan-400'
                      }`}>
                        {currentJob.status.toUpperCase()}
                      </span>
                    )}
                  </div>
                </div>
                
                <div className="p-4">
                  <div className="space-y-4">
                    {(currentJob?.steps || [
                      { name: 'aod_discovery', display_name: 'Discover (AOD)', status: 'pending' as const, message: 'Waiting...' },
                      { name: 'aam_connect', display_name: 'Connect (AAM)', status: 'pending' as const, message: 'Waiting...' },
                      { name: 'dcl_unify', display_name: 'Unify & Ask (DCL)', status: 'pending' as const, message: 'Waiting...' },
                    ]).map((step, index) => (
                      <div key={step.name} className="flex items-start gap-4">
                        <div className={`flex-shrink-0 w-10 h-10 rounded-full border-2 flex items-center justify-center ${STEP_COLORS[step.status]}`}>
                          {getStepIcon(step)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-white">{step.display_name}</span>
                            <span className={`text-xs px-2 py-0.5 rounded-full ${
                              step.status === 'success' ? 'bg-green-500/20 text-green-400' :
                              step.status === 'running' ? 'bg-cyan-500/20 text-cyan-400' :
                              step.status === 'failed' ? 'bg-red-500/20 text-red-400' :
                              'bg-gray-700/50 text-gray-500'
                            }`}>
                              {step.status}
                            </span>
                          </div>
                          <p className="text-sm text-gray-400 mt-0.5">{step.message}</p>
                          
                          {step.data && Object.keys(step.data).length > 0 && (
                            <div className="mt-2 flex flex-wrap gap-2">
                              {Object.entries(step.data).slice(0, 3).map(([key, value]) => (
                                <span key={key} className="text-xs bg-gray-800 px-2 py-1 rounded text-gray-300">
                                  {key}: {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                        
                        {index < 2 && (
                          <div className="hidden sm:flex items-center text-gray-600 ml-2">
                            <ArrowRight className="w-4 h-4" />
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            <div className="bg-gray-900/50 rounded-xl border border-gray-700/50 overflow-hidden">
              <div className="bg-gradient-to-r from-gray-800 to-gray-900 px-4 py-3 border-b border-gray-700/50">
                <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">Explore Each Step</h3>
              </div>
              <div className="p-4">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {NAV_LINKS.map(link => {
                    const Icon = link.icon;
                    return (
                      <button
                        key={link.page}
                        onClick={() => navigateTo(link.page)}
                        className="flex flex-col items-center gap-2 p-4 rounded-lg bg-gray-800/50 border border-gray-700/40 hover:border-cyan-500/50 hover:bg-gray-800 transition-all duration-200 group"
                      >
                        <Icon className="w-6 h-6 text-gray-400 group-hover:text-cyan-400 transition-colors" />
                        <span className="text-sm font-medium text-gray-300 group-hover:text-white transition-colors">{link.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>

            <div className="bg-amber-900/20 border border-amber-500/30 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <Bot className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-sm font-medium text-amber-300">Demo Mode Active</h4>
                  <p className="text-sm text-amber-200/70 mt-1">
                    Running with stub responses. Connect AOD, AAM, and DCL v2 services for live data.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </DemoStep>
    </div>
  );
}
