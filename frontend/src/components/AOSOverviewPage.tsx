export default function AOSOverviewPage() {
  return (
    <div className="space-y-6 px-4 sm:px-6 py-6">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-white mb-4">AOS Overview</h1>
        <p className="text-lg text-gray-300 leading-relaxed">
          Interactive demonstration of AutonomOS platform capabilities. Explore the complete data orchestration pipeline 
          from discovery to intelligent mapping to agent execution.
        </p>
      </div>

      <div className="bg-gray-800 rounded-lg border border-cyan-500/30 overflow-hidden">
        <div className="bg-gradient-to-r from-cyan-600/20 to-purple-600/20 border-b border-cyan-500/30 px-4 py-3">
          <h2 className="text-xl font-semibold text-white flex items-center gap-2">
            <svg className="w-6 h-6 text-cyan-400" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M6 2a2 2 0 00-2 2v12a2 2 0 002 2h8a2 2 0 002-2V7.414A2 2 0 0015.414 6L12 2.586A2 2 0 0010.586 2H6zm5 6a1 1 0 10-2 0v3.586l-1.293-1.293a1 1 0 10-1.414 1.414l3 3a1 1 0 001.414 0l3-3a1 1 0 00-1.414-1.414L11 11.586V8z" clipRule="evenodd"/>
            </svg>
            Discovery Demo - Interactive Pipeline
            <a 
              href="https://discovery-demo-standalone-ilyacantor.replit.app/" 
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
            src="https://discovery-demo-standalone-ilyacantor.replit.app/"
            className="absolute inset-0 w-full h-full"
            title="AOS Discovery Demo"
            allow="fullscreen"
            style={{
              border: 'none',
              backgroundColor: '#1a1a1a'
            }}
          />
        </div>
      </div>
    </div>
  );
}
