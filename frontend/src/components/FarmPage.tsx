import DemoIframeContainer from './DemoIframeContainer';

const FARM_IFRAME_URL = 'https://autonomos.farm';

export default function FarmPage() {
  return (
    <div className="h-full flex flex-col">
      <div className="flex-1 min-h-0">
        <DemoIframeContainer
          src={FARM_IFRAME_URL}
          title="Farm"
        />
      </div>
    </div>
  );
}
