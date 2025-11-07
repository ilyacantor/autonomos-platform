import HITLQueue from './HITLQueue';

export default function DiscoverPage() {
  return (
    <div className="space-y-6 px-4 sm:px-6 py-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-white mb-4">AOS Discover</h1>
        <p className="text-lg text-gray-300 max-w-4xl leading-relaxed">
          Autonomously fingerprints your entire tech stack. Catalogs 100s of apps, databases, and tools without manual configuration. 
          Infers relationships instantly. Creates secure architectural views using metadata only.
        </p>
      </div>

      {/* Embedded AOD Dashboard */}
      <div className="mb-8 bg-gray-800 rounded-lg border border-cyan-500/30 overflow-hidden">
        <div className="bg-gradient-to-r from-cyan-600/20 to-purple-600/20 border-b border-cyan-500/30 px-4 py-3">
          <h2 className="text-xl font-semibold text-white flex items-center gap-2">
            <svg className="w-6 h-6 text-cyan-400" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M3 3a1 1 0 000 2v8a2 2 0 002 2h2.586l-1.293 1.293a1 1 0 101.414 1.414L10 15.414l2.293 2.293a1 1 0 001.414-1.414L12.414 15H15a2 2 0 002-2V5a1 1 0 100-2H3zm11 4a1 1 0 10-2 0v4a1 1 0 102 0V7zm-3 1a1 1 0 10-2 0v3a1 1 0 102 0V8zM8 9a1 1 0 00-2 0v2a1 1 0 102 0V9z" clipRule="evenodd"/>
            </svg>
            Live AOD Dashboard
            <a 
              href="https://aos-discover.replit.app/" 
              target="_blank" 
              rel="noopener noreferrer"
              className="ml-auto text-sm text-cyan-400 hover:text-cyan-300 underline font-normal"
            >
              Open in new tab ↗
            </a>
          </h2>
        </div>
        <div className="relative" style={{ paddingBottom: '75%' }}>
          <iframe
            src="https://aos-discover.replit.app/"
            className="absolute inset-0 w-full h-full"
            title="AOS Discover Dashboard"
            allow="fullscreen"
            style={{
              border: 'none',
              backgroundColor: '#1a1a1a'
            }}
          />
        </div>
      </div>

      {/* Stats Bar */}
      <div className="flex justify-end gap-6 mb-6">
        <div className="text-right">
          <div className="text-sm text-gray-400">Total Assets</div>
          <div className="text-2xl font-bold text-cyan-400">1000</div>
        </div>
        <div className="text-right">
          <div className="text-sm text-gray-400">HITL Queue</div>
          <div className="text-2xl font-bold text-yellow-400">247</div>
        </div>
        <div className="text-right">
          <div className="text-sm text-gray-400">Catalogued</div>
          <div className="text-2xl font-bold text-green-400">753</div>
        </div>
      </div>

      {/* Live Connection Pipeline */}
      <div className="bg-gray-800 rounded-lg p-6 mb-6">
        <div className="flex items-center gap-2 mb-4">
          <svg className="w-5 h-5 text-pink-500" fill="currentColor" viewBox="0 0 20 20">
            <path d="M10 12a2 2 0 100-4 2 2 0 000 4z"/>
            <path fillRule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clipRule="evenodd"/>
          </svg>
          <h2 className="text-xl font-semibold text-white">Live Connection Pipeline</h2>
        </div>
        
        {/* Pipeline Stages */}
        <div className="grid grid-cols-5 gap-4 mb-6">
          <div className="bg-gray-900 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-2 h-2 bg-gray-500 rounded-full"></div>
              <div className="text-xs text-gray-400 uppercase">Unknown</div>
            </div>
            <div className="text-3xl font-bold text-white mb-1">0</div>
            <div className="w-full bg-gray-700 rounded-full h-1">
              <div className="bg-gray-500 h-1 rounded-full" style={{ width: '0%' }}></div>
            </div>
          </div>

          <div className="bg-gray-900 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
              <div className="text-xs text-gray-400 uppercase">Processing</div>
            </div>
            <div className="text-3xl font-bold text-white mb-1">0</div>
            <div className="w-full bg-gray-700 rounded-full h-1">
              <div className="bg-blue-500 h-1 rounded-full" style={{ width: '0%' }}></div>
            </div>
          </div>

          <div className="bg-gray-900 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
              <div className="text-xs text-gray-400 uppercase">Parked (HITL)</div>
            </div>
            <div className="text-3xl font-bold text-white mb-1">247</div>
            <div className="w-full bg-gray-700 rounded-full h-1">
              <div className="bg-yellow-500 h-1 rounded-full" style={{ width: '24.7%' }}></div>
            </div>
          </div>

          <div className="bg-gray-900 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <div className="text-xs text-gray-400 uppercase">Ready</div>
            </div>
            <div className="text-3xl font-bold text-white mb-1">110</div>
            <div className="w-full bg-gray-700 rounded-full h-1">
              <div className="bg-green-500 h-1 rounded-full" style={{ width: '100%' }}></div>
            </div>
          </div>

          <div className="bg-gray-900 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-2 h-2 bg-cyan-500 rounded-full"></div>
              <div className="text-xs text-gray-400 uppercase">Connected</div>
            </div>
            <div className="text-3xl font-bold text-white mb-1">643</div>
            <div className="w-full bg-gray-700 rounded-full h-1">
              <div className="bg-cyan-500 h-1 rounded-full" style={{ width: '64.3%' }}></div>
            </div>
          </div>
        </div>

        {/* Pipeline Metrics */}
        <div className="grid grid-cols-3 gap-4 bg-gray-900 rounded-lg p-4">
          <div>
            <div className="text-sm text-gray-400">Throughput</div>
            <div className="text-xl font-semibold text-white">127 <span className="text-sm text-gray-400">assets/min</span></div>
          </div>
          <div>
            <div className="text-sm text-gray-400">Avg Processing</div>
            <div className="text-xl font-semibold text-white">4.2s <span className="text-sm text-gray-400">per asset</span></div>
          </div>
          <div>
            <div className="text-sm text-gray-400">Pipeline Health</div>
            <div className="text-xl font-semibold text-white">98.4% <span className="text-sm text-gray-400">3 failures</span></div>
          </div>
        </div>
      </div>

      {/* Three Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* HITL Triage Queue */}
        <div className="bg-gray-800 rounded-lg p-6">
          <div className="flex items-center gap-2 mb-4">
            <svg className="w-5 h-5 text-pink-500" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd"/>
            </svg>
            <h3 className="text-lg font-semibold text-white">HITL Triage Queue</h3>
          </div>
          <div className="text-3xl font-bold text-yellow-400 mb-6">90 <span className="text-sm text-gray-400 font-normal">assets require review</span></div>
          
          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 bg-gray-900 rounded-lg border-l-4 border-red-500">
              <div className="flex items-center gap-3">
                <svg className="w-5 h-5 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd"/>
                </svg>
                <div>
                  <div className="text-white font-medium">Security Threats</div>
                  <div className="text-sm text-gray-400">AAM scanner detected anomalies</div>
                </div>
              </div>
              <div className="text-2xl font-bold text-red-400">20</div>
            </div>

            <div className="flex items-center justify-between p-3 bg-gray-900 rounded-lg border-l-4 border-yellow-500">
              <div className="flex items-center gap-3">
                <svg className="w-5 h-5 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M5 2a1 1 0 011 1v1h1a1 1 0 010 2H6v1a1 1 0 01-2 0V6H3a1 1 0 010-2h1V3a1 1 0 011-1zm0 10a1 1 0 011 1v1h1a1 1 0 110 2H6v1a1 1 0 11-2 0v-1H3a1 1 0 110-2h1v-1a1 1 0 011-1zM12 2a1 1 0 01.967.744L14.146 7.2 17.5 9.134a1 1 0 010 1.732l-3.354 1.935-1.18 4.455a1 1 0 01-1.933 0L9.854 12.8 6.5 10.866a1 1 0 010-1.732l3.354-1.935 1.18-4.455A1 1 0 0112 2z" clipRule="evenodd"/>
                </svg>
                <div>
                  <div className="text-white font-medium">Shadow IT Risks</div>
                  <div className="text-sm text-gray-400">AAM Supervisor flagged for review</div>
                </div>
              </div>
              <div className="text-2xl font-bold text-yellow-400">10</div>
            </div>

            <div className="flex items-center justify-between p-3 bg-gray-900 rounded-lg border-l-4 border-blue-500">
              <div className="flex items-center gap-3">
                <svg className="w-5 h-5 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd"/>
                </svg>
                <div>
                  <div className="text-white font-medium">Data Conflicts</div>
                  <div className="text-sm text-gray-400">AAM Inspector needs input</div>
                </div>
              </div>
              <div className="text-2xl font-bold text-blue-400">60</div>
            </div>
          </div>
        </div>

        {/* Catalogued Inventory */}
        <div className="bg-gray-800 rounded-lg p-6">
          <div className="flex items-center gap-2 mb-4">
            <svg className="w-5 h-5 text-cyan-500" fill="currentColor" viewBox="0 0 20 20">
              <path d="M7 3a1 1 0 000 2h6a1 1 0 100-2H7zM4 7a1 1 0 011-1h10a1 1 0 110 2H5a1 1 0 01-1-1zM2 11a2 2 0 012-2h12a2 2 0 012 2v4a2 2 0 01-2 2H4a2 2 0 01-2-2v-4z"/>
            </svg>
            <h3 className="text-lg font-semibold text-white">Catalogued Inventory</h3>
          </div>
          <div className="text-3xl font-bold text-cyan-400 mb-6">753 <span className="text-sm text-gray-400 font-normal">assets</span></div>

          <div className="mb-6">
            <div className="text-sm text-gray-400 uppercase mb-3">By Vendor</div>
            <div className="grid grid-cols-4 gap-2">
              <div className="bg-blue-600 rounded p-3 text-center">
                <div className="text-xs text-white mb-1">GCP</div>
                <div className="text-lg font-bold text-white">111</div>
              </div>
              <div className="bg-blue-500 rounded p-3 text-center">
                <div className="text-xs text-white mb-1">Salesforce</div>
                <div className="text-lg font-bold text-white">108</div>
              </div>
              <div className="bg-orange-500 rounded p-3 text-center">
                <div className="text-xs text-white mb-1">AWS</div>
                <div className="text-lg font-bold text-white">107</div>
              </div>
              <div className="bg-green-600 rounded p-3 text-center">
                <div className="text-xs text-white mb-1">MongoDB</div>
                <div className="text-lg font-bold text-white">95</div>
              </div>
              <div className="bg-blue-400 rounded p-3 text-center">
                <div className="text-xs text-white mb-1">Microsoft</div>
                <div className="text-lg font-bold text-white">90</div>
              </div>
              <div className="bg-blue-600 rounded p-3 text-center">
                <div className="text-xs text-white mb-1">Azure</div>
                <div className="text-lg font-bold text-white">88</div>
              </div>
              <div className="bg-green-500 rounded p-3 text-center">
                <div className="text-xs text-white mb-1">Okta</div>
                <div className="text-lg font-bold text-white">77</div>
              </div>
              <div className="bg-purple-600 rounded p-3 text-center">
                <div className="text-xs text-white mb-1">Datadog</div>
                <div className="text-lg font-bold text-white">73</div>
              </div>
            </div>
          </div>

          <div>
            <div className="text-sm text-gray-400 uppercase mb-3">By Asset Kind</div>
            <div className="grid grid-cols-2 gap-2">
              <div className="bg-blue-600 rounded p-3 text-center">
                <div className="text-xs text-white mb-1">Service</div>
                <div className="text-lg font-bold text-white">208</div>
              </div>
              <div className="bg-purple-600 rounded p-3 text-center">
                <div className="text-xs text-white mb-1">Db</div>
                <div className="text-lg font-bold text-white">186</div>
              </div>
              <div className="bg-blue-500 rounded p-3 text-center">
                <div className="text-xs text-white mb-1">Host</div>
                <div className="text-lg font-bold text-white">181</div>
              </div>
              <div className="bg-green-600 rounded p-3 text-center">
                <div className="text-xs text-white mb-1">SaaS</div>
                <div className="text-lg font-bold text-white">178</div>
              </div>
            </div>
          </div>
        </div>

        {/* Live Automated Action Log */}
        <div className="bg-gray-800 rounded-lg p-6">
          <div className="flex items-center gap-2 mb-4">
            <svg className="w-5 h-5 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clipRule="evenodd"/>
            </svg>
            <h3 className="text-lg font-semibold text-white">Live Automated Action Log</h3>
            <div className="ml-auto flex items-center gap-1">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span className="text-xs text-green-400">Live</span>
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-start gap-3 p-2 bg-gray-900 rounded">
              <svg className="w-4 h-4 text-blue-400 mt-1" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd"/>
              </svg>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 text-xs text-gray-400 mb-1">
                  <span>09:45 AM</span>
                  <span className="px-2 py-0.5 bg-blue-900 text-blue-300 rounded">Responder</span>
                  <span className="px-2 py-0.5 bg-gray-700 text-gray-300 rounded text-xs">SYNCED</span>
                </div>
                <div className="text-sm text-white">Asset 'aws-us-east-1-db' synced to ServiceNow.</div>
              </div>
            </div>

            <div className="flex items-start gap-3 p-2 bg-gray-900 rounded">
              <svg className="w-4 h-4 text-green-400 mt-1" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"/>
              </svg>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 text-xs text-gray-400 mb-1">
                  <span>09:43 AM</span>
                  <span className="px-2 py-0.5 bg-green-900 text-green-300 rounded">Scanner</span>
                  <span className="px-2 py-0.5 bg-yellow-900 text-yellow-300 rounded text-xs">QUARANTINE</span>
                </div>
                <div className="text-sm text-white">Quarantined suspicious device 'laptop-user-619' after anomaly detected</div>
              </div>
            </div>

            <div className="flex items-start gap-3 p-2 bg-gray-900 rounded">
              <svg className="w-4 h-4 text-blue-400 mt-1" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd"/>
              </svg>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 text-xs text-gray-400 mb-1">
                  <span>09:42 AM</span>
                  <span className="px-2 py-0.5 bg-blue-900 text-blue-300 rounded">Responder</span>
                  <span className="px-2 py-0.5 bg-gray-700 text-gray-300 rounded text-xs">SCAN</span>
                </div>
                <div className="text-sm text-white">Asset 'aws-us-user-db' synced to ServiceNow.</div>
              </div>
            </div>

            <div className="flex items-start gap-3 p-2 bg-gray-900 rounded">
              <svg className="w-4 h-4 text-yellow-400 mt-1" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd"/>
                </svg>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 text-xs text-gray-400 mb-1">
                  <span>09:41 AM</span>
                  <span className="px-2 py-0.5 bg-yellow-900 text-yellow-300 rounded">Alert</span>
                  <span className="px-2 py-0.5 bg-red-900 text-red-300 rounded text-xs">ALERT</span>
                </div>
                <div className="text-sm text-white">Blocked unauthorized API call from 'api-gateway-03'.</div>
              </div>
            </div>

            <div className="flex items-start gap-3 p-2 bg-gray-900 rounded opacity-75">
              <svg className="w-4 h-4 text-purple-400 mt-1" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clipRule="evenodd"/>
              </svg>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 text-xs text-gray-400 mb-1">
                  <span>09:41 AM</span>
                  <span className="px-2 py-0.5 bg-purple-900 text-purple-300 rounded">Scanner</span>
                  <span className="px-2 py-0.5 bg-blue-900 text-blue-300 rounded text-xs">QUARANTINE</span>
                </div>
                <div className="text-sm text-white">Classified resource 'db-prod-main' as critical infrastructure.</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* HITL Decision Queue */}
      <HITLQueue />
    </div>
  );
}
