import DemoStep from './DemoStep';
import HITLQueue from './HITLQueue';

const AOD_IFRAME_URL = 'https://autonomos.network';

export default function DiscoverPage() {
  return (
    <div className="h-full flex flex-col">
      <div className="flex-1 min-h-0">
        <DemoStep
          stepNumber={1}
          title="Discover Your Assets"
          description="Autonomously fingerprints your entire tech stack. Catalogs hundreds of apps, databases, and tools without manual configuration. Infers relationships instantly."
          openInNewTabHref={AOD_IFRAME_URL}
          instructions="Click on any discovered asset to see its relationships, dependencies, and metadata."
        >
          <div className="relative w-full h-full" style={{ minHeight: '400px' }}>
            <iframe
              src={AOD_IFRAME_URL}
              className="absolute inset-0 w-full h-full"
              title="AOS Discover Dashboard"
              allow="fullscreen"
              style={{
                border: 'none',
                backgroundColor: '#1a1a1a'
              }}
            />
          </div>
        </DemoStep>
      </div>

      <div className="flex-shrink-0 px-3 sm:px-4 lg:px-6 pb-4">
        <HITLQueue />
      </div>
    </div>
  );
}
