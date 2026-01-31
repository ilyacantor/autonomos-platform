import DemoIframeContainer from './DemoIframeContainer';

const DCL_IFRAME_URL = 'https://dcl.autonomos.software';

export default function UnifyAskPage() {
  return (
    <div className="h-full flex flex-col">
      <div className="px-6 py-4 border-b border-gray-800 bg-gray-900/50">
        <h1 className="text-lg font-semibold text-white">Data Connectivity Layer</h1>
        <p className="text-sm text-gray-400">Map raw data fields to a unified business ontology — so agents understand what "revenue" actually means.</p>
      </div>
      <div className="flex-1 min-h-0">
        <DemoIframeContainer
          src={DCL_IFRAME_URL}
          title="DCL - Data Connectivity Layer"
          allow="fullscreen"
          minHeight="700px"
        />
      </div>
    </div>
  );
}
