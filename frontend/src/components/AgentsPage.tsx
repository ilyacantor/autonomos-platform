import LiveStatusBadge from './LiveStatusBadge';
import { getLiveStatus } from '../config/liveStatus';

export default function AgentsPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-white">Agents</h1>
        <p className="text-gray-400 mt-2">
          AI-powered agents for domain-specific automation
        </p>
      </div>

      {/* Live Agent Demos */}
      <div className="bg-slate-800/40 rounded-xl border border-cyan-500/30 p-6">
        <div className="mb-6">
          <h3 className="text-2xl font-medium text-cyan-400 mb-2">
            Live Agent Demos
          </h3>
          <p className="text-sm text-gray-400">
            Interactive demonstrations of specialized agents in production
          </p>
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* FinOps Agent */}
          <div className="bg-slate-800/60 rounded-xl border border-slate-700 overflow-hidden">
            <div className="bg-slate-900/50 px-4 py-3 border-b border-slate-700 flex items-center justify-between">
              <div>
                <h4 className="text-lg font-medium text-blue-400">FinOps Agent</h4>
                <p className="text-xs text-gray-400 mt-1">Financial operations optimization and cost management</p>
              </div>
              <LiveStatusBadge {...getLiveStatus('finops-agent')!} />
            </div>
            <div className="relative" style={{ height: '600px' }}>
              <iframe
                src="https://axiom-finops-demo.replit.app/"
                className="w-full h-full"
                title="FinOps Agent Demo"
                style={{ border: 'none' }}
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              />
            </div>
          </div>

          {/* RevOps Agent */}
          <div className="bg-slate-800/60 rounded-xl border border-slate-700 overflow-hidden">
            <div className="bg-slate-900/50 px-4 py-3 border-b border-slate-700 flex items-center justify-between">
              <div>
                <h4 className="text-lg font-medium text-purple-400">RevOps Agent</h4>
                <p className="text-xs text-gray-400 mt-1">Revenue operations analytics and pipeline management</p>
              </div>
              <LiveStatusBadge {...getLiveStatus('revops-agent')!} />
            </div>
            <div className="relative" style={{ height: '600px' }}>
              <iframe
                src="https://autonomos-dcl-light.replit.app/"
                className="w-full h-full"
                title="RevOps Agent Demo"
                style={{ border: 'none' }}
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
