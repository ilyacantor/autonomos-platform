import { Network, ArrowRight, CheckCircle, AlertCircle, Info, ExternalLink } from 'lucide-react';

const connectionLogs = [
  { time: '17:02:45', type: 'success', message: 'Salesforce API authenticated successfully via OAuth2' },
  { time: '17:02:46', type: 'info', message: 'HubSpot rate limit: 95/100 requests remaining' },
  { time: '17:02:47', type: 'success', message: 'MongoDB connection pool initialized (10 connections)' },
  { time: '17:02:48', type: 'info', message: 'Supabase REST API endpoint responding in 45ms' },
  { time: '17:02:50', type: 'success', message: 'Snowflake warehouse AUTO_RESUME completed' },
  { time: '17:02:52', type: 'warning', message: 'SAP API latency elevated: 320ms (threshold: 250ms)' },
  { time: '17:02:53', type: 'success', message: 'DataBricks cluster scaled to 4 nodes' },
  { time: '17:02:55', type: 'info', message: 'NetSuite SOAP API session refreshed' },
  { time: '17:02:57', type: 'success', message: 'Dynamics 365 Web API connection established' },
  { time: '17:02:59', type: 'info', message: 'Legacy SQL connection keepalive sent' },
  { time: '17:03:01', type: 'success', message: 'Salesforce bulk API job #8821 completed (1.2K records)' },
  { time: '17:03:03', type: 'info', message: 'HubSpot webhook verified and registered' },
  { time: '17:03:05', type: 'success', message: 'MongoDB Change Streams listener active' },
  { time: '17:03:07', type: 'warning', message: 'Supabase connection count: 8/10 (80% utilization)' },
  { time: '17:03:09', type: 'success', message: 'Snowflake query cache hit rate: 94%' },
  { time: '17:03:11', type: 'info', message: 'SAP RFC connection pool recycled' },
  { time: '17:03:13', type: 'success', message: 'DataBricks delta table sync completed' },
  { time: '17:03:15', type: 'info', message: 'NetSuite REST API pagination handling optimized' },
  { time: '17:03:17', type: 'success', message: 'Dynamics batch request completed (250ms)' },
  { time: '17:03:19', type: 'info', message: 'All data sources: health check passed ✓' },
];

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
        
        <a 
          href="https://www.autonomos.tech/" 
          target="_blank" 
          rel="noopener noreferrer"
          className="flex items-center gap-2 text-sm text-purple-400 hover:text-purple-300 transition-colors group"
        >
          <span className="font-medium">Visit our full website</span>
          <ArrowRight className="w-4 h-4" />
          <ExternalLink className="w-3 h-3 opacity-70 group-hover:opacity-100" />
        </a>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-6">
        <div className="space-y-6">
          <div className="bg-slate-800/40 rounded-lg border border-slate-700/50 p-6">
            <div className="flex items-center gap-2 mb-4">
              <h3 className="text-sm font-semibold text-slate-200">Connected Data Sources</h3>
              <span className="text-xs text-slate-500">(8 platforms)</span>
            </div>
            
            <div className="flex items-center justify-center py-6">
              <img 
                src="/assets/data-source-logos.png" 
                alt="Connected data sources: Salesforce, HubSpot, MongoDB, Supabase, Snowflake, SAP, DataBricks, and more"
                className="h-32 w-auto object-contain opacity-90 hover:opacity-100 transition-opacity"
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

        <div className="bg-slate-800/40 rounded-lg border border-slate-700/50 p-4">
          <div className="flex items-center gap-2 mb-3">
            <h3 className="text-sm font-semibold text-slate-200">Connection Log</h3>
            <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
          </div>
          
          <div className="bg-slate-900/60 rounded-md border border-slate-700/30 p-3 max-h-[280px] overflow-y-auto">
            <div className="space-y-2 font-mono text-xs">
              {connectionLogs.map((log, index) => (
                <div key={index} className="flex items-start gap-2 pb-2 border-b border-slate-700/20 last:border-0">
                  <span className="text-slate-500 flex-shrink-0">{log.time}</span>
                  {log.type === 'success' && (
                    <CheckCircle className="w-3 h-3 text-green-400 flex-shrink-0 mt-0.5" />
                  )}
                  {log.type === 'warning' && (
                    <AlertCircle className="w-3 h-3 text-yellow-400 flex-shrink-0 mt-0.5" />
                  )}
                  {log.type === 'info' && (
                    <Info className="w-3 h-3 text-blue-400 flex-shrink-0 mt-0.5" />
                  )}
                  <span className="text-slate-300 leading-tight flex-1">{log.message}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
