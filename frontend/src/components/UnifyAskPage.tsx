import DemoStep from './DemoStep';
import DemoIframeContainer from './DemoIframeContainer';

const DCL_IFRAME_URL = 'https://dcl.autonomos.software';

export default function UnifyAskPage() {
  return (
    <div className="h-full flex flex-col">
      <div className="flex-1 min-h-0">
        <DemoStep
          title="Data Connectivity Layer (DCL)"
          description="Unify your data into a canonical ontology. DCL maps source fields to canonical fields, performs entity resolution, and produces canonical streams for agents and dashboards."
          openInNewTabHref={DCL_IFRAME_URL}
          instructions="Explore the unified ontology, data mappings, and canonical entity streams."
        >
          <DemoIframeContainer
            src={DCL_IFRAME_URL}
            title="DCL - Data Connectivity Layer"
            allow="fullscreen"
            minHeight="700px"
          />
        </DemoStep>
      </div>
    </div>
  );
}
