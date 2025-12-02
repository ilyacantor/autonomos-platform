import DemoStep from './DemoStep';
import DemoIframeContainer from './DemoIframeContainer';

const OVERVIEW_IFRAME_URL = 'https://overview.autonomos.software';

export default function AOSOverviewPage() {
  return (
    <div className="h-full flex flex-col">
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
            minHeight="600px"
          />
        </DemoStep>
      </div>
    </div>
  );
}
