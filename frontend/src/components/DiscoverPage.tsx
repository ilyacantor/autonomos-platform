import HITLQueue from './HITLQueue';
import LiveStatusBadge from './LiveStatusBadge';
import { getLiveStatus } from '../config/liveStatus';

export default function DiscoverPage() {
  return (
    <div className="space-y-6 px-4 sm:px-6 py-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-white mb-4">AOS Discover</h1>
        <p className="text-lg text-gray-300 leading-relaxed">
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
            <LiveStatusBadge {...getLiveStatus('aod-dashboard')!} />
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

      {/* HITL Decision Queue */}
      <HITLQueue />
    </div>
  );
}
