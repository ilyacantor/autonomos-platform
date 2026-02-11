import DemoIframeContainer from './DemoIframeContainer';

const DISCOVER_IFRAME_URL = 'https://discover.autonomos.software/';

export default function DiscoverPage() {
  return (
    <div className="h-full flex flex-col">
      <div className="flex-1 min-h-0">
        <DemoIframeContainer
          src={DISCOVER_IFRAME_URL}
          title="AOD Discovery"
          allow="fullscreen"
          minHeight="700px"
        />
      </div>
    </div>
  );
}
