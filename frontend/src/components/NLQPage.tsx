import DemoIframeContainer from './DemoIframeContainer';

const NLQ_IFRAME_URL = 'https://nlq.autonomos.software';

export default function NLQPage() {
  return (
    <div className="h-full flex flex-col">
      <div className="px-6 py-4 border-b border-gray-800 bg-gray-900/50">
        <h1 className="text-lg font-semibold text-white">Natural Language Query</h1>
        <p className="text-sm text-gray-400">Ask questions in plain English and get instant, self-generating dashboards across all your unified data.</p>
      </div>
      <div className="flex-1 min-h-0">
        <DemoIframeContainer
          src={NLQ_IFRAME_URL}
          title="NLQ - Natural Language Query"
          allow="fullscreen"
          minHeight="700px"
        />
      </div>
    </div>
  );
}
