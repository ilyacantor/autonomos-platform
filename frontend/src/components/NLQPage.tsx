import DemoIframeContainer from './DemoIframeContainer';

const NLQ_IFRAME_URL = 'https://nlq.autonomos.software';

export default function NLQPage() {
  return (
    <div className="h-full flex flex-col">
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
