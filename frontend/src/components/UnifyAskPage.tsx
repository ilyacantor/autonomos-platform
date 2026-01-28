import DemoIframeContainer from './DemoIframeContainer';

const DCL_IFRAME_URL = 'https://dcl.autonomos.software';

export default function UnifyAskPage() {
  return (
    <div className="h-full flex flex-col">
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
