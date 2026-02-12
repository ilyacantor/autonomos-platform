import DemoIframeContainer from './DemoIframeContainer';

const AAM_IFRAME_URL = 'https://aam.autonomos.software/ui/topology';

export default function ConnectPage() {
  return (
    <div className="h-full flex flex-col">
      <div className="flex-1 min-h-0">
        <DemoIframeContainer
          src={AAM_IFRAME_URL}
          title="AAM Mesh Interface"
        />
      </div>
    </div>
  );
}
