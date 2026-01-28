import DemoStep from './DemoStep';
import DemoIframeContainer from './DemoIframeContainer';

const NLQ_IFRAME_URL = 'https://nlq.autonomos.software';

export default function NLQPage() {
  return (
    <div className="h-full flex flex-col">
      <div className="flex-1 min-h-0">
        <DemoStep
          title="Natural Language Query (NLQ)"
          description="Ask questions in natural language and get answers powered by AI across your unified data."
          openInNewTabHref={NLQ_IFRAME_URL}
          instructions="Enter natural language queries to explore your data."
        >
          <DemoIframeContainer
            src={NLQ_IFRAME_URL}
            title="NLQ - Natural Language Query"
            allow="fullscreen"
            minHeight="700px"
          />
        </DemoStep>
      </div>
    </div>
  );
}
