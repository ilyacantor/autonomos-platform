import DemoStep from './DemoStep';
import DemoIframeContainer from './DemoIframeContainer';

const OVERVIEW_IFRAME_URL = 'https://discovery-demo-standalone-ilyacantor.replit.app/';

export default function AOSOverviewPage() {
  return (
    <div className="h-full flex flex-col">
      <div className="flex-shrink-0 px-3 sm:px-4 lg:px-6 pt-4 sm:pt-6 pb-3">
        <div className="bg-gradient-to-r from-cyan-900/30 via-purple-900/30 to-blue-900/30 border border-cyan-500/30 rounded-xl p-4 sm:p-6">
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 sm:gap-4">
            <div className="w-12 h-12 sm:w-16 sm:h-16 rounded-xl bg-gradient-to-br from-cyan-500/20 to-purple-500/20 border border-cyan-500/30 flex items-center justify-center flex-shrink-0">
              <svg className="w-6 h-6 sm:w-8 sm:h-8 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
            <div className="flex-1 min-w-0">
              <h2 className="text-lg sm:text-xl font-bold text-white mb-1">
                AI Startup Ecosystem – Where AutonomOS Fits
              </h2>
              <p className="text-sm text-gray-400 leading-relaxed">
                Hero diagram showing AutonomOS positioning in the AI infrastructure landscape will appear here.
              </p>
            </div>
            <div className="px-3 py-1 bg-amber-500/20 border border-amber-500/40 rounded-full text-xs font-medium text-amber-400 flex-shrink-0">
              Coming Soon
            </div>
          </div>
        </div>
      </div>

      <div className="flex-1 min-h-0">
        <DemoStep
          title="AOS Overview"
          description="Interactive demonstration of AutonomOS platform capabilities. Explore the complete data orchestration pipeline from discovery to intelligent mapping to agent execution."
          openInNewTabHref={OVERVIEW_IFRAME_URL}
          instructions="Navigate through the demo to see how AutonomOS discovers, connects, and unifies your enterprise data stack."
        >
          <DemoIframeContainer
            src={OVERVIEW_IFRAME_URL}
            title="AOS Discovery Demo"
            allow="fullscreen"
          />
        </DemoStep>
      </div>
    </div>
  );
}
