import { useState, useEffect, lazy, Suspense } from 'react';
import { AutonomyProvider, useAutonomy } from './contexts/AutonomyContext';
import AppLayout from './components/AppLayout';
import DemoIframeContainer from './components/DemoIframeContainer';

const AOSOverviewPage = lazy(() => import('./components/AOSOverviewPage'));
const OrchestrationDashboard = lazy(() => import('./components/orchestration/OrchestrationDashboard'));
const FAQPage = lazy(() => import('./components/FAQPage'));

const IFRAME_PAGES: Record<string, { src: string; title: string }> = {
  'nlq': { src: 'https://nlq.autonomos.software', title: 'NLQ - Natural Language Query' },
  'discover': { src: 'https://discover.autonomos.software/', title: 'AOD Discovery' },
  'connect': { src: 'https://aam.autonomos.software/ui/topology', title: 'AAM Mesh Interface' },
  'unify-ask': { src: 'https://dcl.autonomos.software', title: 'DCL - Data Connectivity Layer' },
  'farm': { src: 'https://autonomos.farm', title: 'Farm' },
};

function PageLoader() {
  return (
    <div className="flex items-center justify-center min-h-[400px]">
      <div className="flex flex-col items-center gap-4">
        <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        <span className="text-gray-400 text-sm">Loading...</span>
      </div>
    </div>
  );
}

function AppContent() {
  const getInitialPage = () => {
    const path = window.location.pathname.slice(1);
    const validPages = ['aos-overview', 'nlq', 'discover', 'connect', 'unify-ask', 'orchestration', 'farm', 'faq'];
    return validPages.includes(path) ? path : 'nlq';
  };

  const [currentPage, setCurrentPage] = useState(getInitialPage());
  const { legacyMode } = useAutonomy();
  const allIframeKeys = Object.keys(IFRAME_PAGES);

  useEffect(() => {
    const handleNavigation = (event: Event) => {
      const customEvent = event as CustomEvent;
      const page = customEvent.detail?.page;
      if (page) {
        setCurrentPage(page);
        window.history.pushState({}, '', `/${page}`);
      }
    };

    window.addEventListener('navigate', handleNavigation);
    return () => {
      window.removeEventListener('navigate', handleNavigation);
    };
  }, []);

  useEffect(() => {
    const handlePopState = () => {
      const path = window.location.pathname.slice(1);
      const validPages = ['aos-overview', 'nlq', 'discover', 'connect', 'unify-ask', 'orchestration', 'farm', 'faq'];
      if (validPages.includes(path)) {
        setCurrentPage(path);
      }
    };

    window.addEventListener('popstate', handlePopState);
    return () => {
      window.removeEventListener('popstate', handlePopState);
    };
  }, []);

  const isIframePage = IFRAME_PAGES[currentPage] !== undefined;

  const renderNonIframePage = () => {
    switch (currentPage) {
      case 'aos-overview':
        return <AOSOverviewPage />;
      case 'orchestration':
        return <OrchestrationDashboard />;
      case 'faq':
        return <FAQPage />;
      default:
        return <AOSOverviewPage />;
    }
  };

  return (
    <AppLayout currentPage={currentPage} onNavigate={setCurrentPage}>
      {!isIframePage && (
        <Suspense fallback={<PageLoader />}>
          {renderNonIframePage()}
        </Suspense>
      )}

      {allIframeKeys.map(pageKey => {
        const config = IFRAME_PAGES[pageKey];
        return (
          <div
            key={pageKey}
            className="h-full"
            style={{ display: currentPage === pageKey ? 'block' : 'none' }}
          >
            <DemoIframeContainer src={config.src} title={config.title} />
          </div>
        );
      })}
    </AppLayout>
  );
}

function App() {
  return (
    <AutonomyProvider>
      <AppContent />
    </AutonomyProvider>
  );
}

export default App;
