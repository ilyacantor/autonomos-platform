import { Network, ArrowRight } from 'lucide-react';

export default function AAMContainer() {
  return (
    <div className="bg-gradient-to-br from-slate-900/80 to-slate-800/40 backdrop-blur-sm rounded-xl border border-slate-700/50 p-6 shadow-xl">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-purple-500/10 rounded-lg border border-purple-500/20">
            <Network className="w-5 h-5 text-purple-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">Adaptive API Mesh</h2>
            <p className="text-sm text-gray-400">
              iPaaS-style integration layer: Connect → Normalize → Unify
            </p>
          </div>
        </div>
      </div>

      <div className="space-y-6">
        <div className="bg-slate-800/40 rounded-lg border border-slate-700/50 p-6">
          <div className="flex items-center gap-2 mb-4">
            <h3 className="text-sm font-semibold text-slate-200">Connected Data Sources</h3>
            <span className="text-xs text-slate-500">(8 platforms)</span>
          </div>
          
          <div className="flex items-center justify-center py-4">
            <img 
              src="/assets/data-source-logos.png" 
              alt="Connected data sources: Salesforce, HubSpot, MongoDB, Supabase, Snowflake, SAP, DataBricks, and more"
              className="h-16 w-auto object-contain opacity-90 hover:opacity-100 transition-opacity"
            />
          </div>
        </div>

        <div className="bg-gradient-to-r from-purple-900/20 via-cyan-900/20 to-blue-900/20 rounded-lg border border-purple-500/20 p-4">
          <div className="flex items-center justify-between text-xs text-slate-300">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-purple-400 rounded-full animate-pulse"></div>
              <span className="font-medium">Data Sources</span>
            </div>
            
            <ArrowRight className="w-4 h-4 text-purple-400" />
            
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
              <span className="font-medium">AAM Normalize</span>
            </div>
            
            <ArrowRight className="w-4 h-4 text-cyan-400" />
            
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-cyan-400 rounded-full"></div>
              <span className="font-medium">DCL Mapping</span>
            </div>
            
            <ArrowRight className="w-4 h-4 text-blue-400" />
            
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-blue-400 rounded-full"></div>
              <span className="font-medium">Agents</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
