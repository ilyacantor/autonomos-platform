import DemoIframeContainer from './DemoIframeContainer';

const DISCOVER_IFRAME_URL = 'https://discover.autonomos.software/';

export default function DiscoverPage() {
  return (
    <div className="h-full flex flex-col">
      <div className="px-6 py-4 border-b border-gray-800 bg-gray-900/50">
        <h1 className="text-lg font-semibold text-white">Asset & Observability Discovery</h1>
        <p className="text-sm text-gray-400">Discover and catalog everything running in your environment — the foundation for all downstream intelligence.</p>
      </div>
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
