import DemoStep from './DemoStep';
import DemoIframeContainer from './DemoIframeContainer';

const DISCOVER_IFRAME_URL = 'https://discover.autonomos.software/';

export default function DiscoverPage() {
  return (
    <div className="h-full flex flex-col">
      <div className="flex-1 min-h-0">
        <DemoStep
          title="Asset & Observability Discovery (AOD)"
          description="Discover, catalog, and score everything running in your environment. AOD builds the Asset Graph, flags shadow IT, risky assets, and anomalies."
          openInNewTabHref={DISCOVER_IFRAME_URL}
          instructions="Explore your infrastructure and SaaS telemetry through the discovery interface."
        >
          <DemoIframeContainer
            src={DISCOVER_IFRAME_URL}
            title="AOD Discovery"
            allow="fullscreen"
            minHeight="700px"
          />
        </DemoStep>
      </div>
    </div>
  );
}
