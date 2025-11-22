export default function AOSOverviewPage() {
  return (
    <div className="space-y-4 sm:space-y-6 px-3 sm:px-4 lg:px-6 py-4 sm:py-6">
      <div className="mb-4 sm:mb-8">
        <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-white mb-3 sm:mb-4">
          AOS Overview
        </h1>
        <p className="text-sm sm:text-base lg:text-lg text-gray-300 leading-relaxed">
          Interactive demonstration of AutonomOS platform capabilities. Explore the complete data orchestration pipeline 
          from discovery to intelligent mapping to agent execution.
        </p>
      </div>

      <div className="bg-gray-800 rounded-lg border border-cyan-500/30 overflow-hidden shadow-lg">
        <div className="bg-gradient-to-r from-cyan-600/20 to-purple-600/20 border-b border-cyan-500/30 px-3 sm:px-4 py-2.5 sm:py-3">
          <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-0">
            <h2 className="text-base sm:text-lg lg:text-xl font-semibold text-white flex items-center gap-2">
              <svg className="w-5 h-5 sm:w-6 sm:h-6 text-cyan-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M6 2a2 2 0 00-2 2v12a2 2 0 002 2h8a2 2 0 002-2V7.414A2 2 0 0015.414 6L12 2.586A2 2 0 0010.586 2H6zm5 6a1 1 0 10-2 0v3.586l-1.293-1.293a1 1 0 10-1.414 1.414l3 3a1 1 0 001.414 0l3-3a1 1 0 00-1.414-1.414L11 11.586V8z" clipRule="evenodd"/>
              </svg>
              <span className="truncate">Discovery Demo - Interactive Pipeline</span>
            </h2>
            <a 
              href="https://discovery-demo-standalone-ilyacantor.replit.app/" 
              target="_blank" 
              rel="noopener noreferrer"
              className="sm:ml-auto text-xs sm:text-sm text-cyan-400 hover:text-cyan-300 underline font-normal inline-flex items-center gap-1 flex-shrink-0"
            >
              Open in new tab
              <svg className="w-3 h-3 sm:w-4 sm:h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </a>
          </div>
        </div>
        
        <div className="relative bg-gray-900" style={{ 
          paddingBottom: 'clamp(400px, 85vh, 75%)',
          minHeight: '400px',
          maxHeight: '85vh'
        }}>
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

      <div className="text-xs sm:text-sm text-gray-400 text-center pt-2">
        <p>💡 Tip: For best experience on mobile, use the "Open in new tab" link above</p>
      </div>
    </div>
  );
}
