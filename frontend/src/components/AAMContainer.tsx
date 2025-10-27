import { CheckCircle, AlertCircle, Info } from 'lucide-react';

const connectionLogs = [
  { time: '17:07:43', type: 'success', message: 'Salesforce API authenticated successfully via OAuth2' },
  { time: '17:07:56', type: 'info', message: 'Budget rate limit: 50/100 requests remaining' },
  { time: '17:07:47', type: 'success', message: 'MongoDB connection pool initialized (20 connections)' },
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
    <div className="bg-black border-t border-b border-cyan-500/30 py-12 -mx-6 px-6">
      {/* Title */}
      <div className="mb-8">
        <h2 className="text-3xl font-medium text-cyan-400">Adaptive API Mesh (AAM)</h2>
      </div>

      {/* Data Source Logos */}
      <div className="mb-6">
        <div className="flex items-center justify-center mb-4">
          <img 
            src="/assets/data-source-logos.png" 
            alt="Connected data sources: SAP, HubSpot, Snowflake, Database, Supabase, Datadog, Salesforce, MongoDB"
            className="h-48 w-auto object-contain"
            style={{ maxWidth: '100%' }}
          />
        </div>
        
        {/* Connection lines below logos - aligned to match logo positions */}
        <div className="flex items-start justify-between" style={{ width: '680px', margin: '0 auto' }}>
          {Array(8).fill(0).map((_, i) => (
            <div key={i} className="w-1 h-16 bg-cyan-400/60"></div>
          ))}
        </div>
      </div>

      {/* Main Content: Connection Log + Description */}
      <div className="grid grid-cols-1 lg:grid-cols-[400px_1fr] gap-12 mb-8">
        {/* Left: Connection Log */}
        <div className="bg-slate-900/80 rounded-lg border border-slate-700/50 p-4">
          <div className="flex items-center gap-2 mb-3">
            <h3 className="text-sm font-medium text-slate-200">Connection Log</h3>
            <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
          </div>
          
          <div className="bg-slate-950/60 rounded-md border border-slate-700/30 p-3 max-h-[200px] overflow-y-auto">
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

        {/* Right: Description */}
        <div className="flex items-center">
          <p className="text-2xl text-white leading-relaxed">
            Connects both data, on-prem systems, databases, SaaS platforms / APIs, CSV, Agents, and more through a low-code or no-code interface.
          </p>
        </div>
      </div>

      {/* Connection lines at bottom - aligned to match logo positions */}
      <div className="flex items-start justify-between" style={{ width: '680px', margin: '0 auto' }}>
        {Array(8).fill(0).map((_, i) => (
          <div key={i} className="w-1 h-16 bg-cyan-400/60"></div>
        ))}
      </div>
    </div>
  );
}
