import { useState, useEffect, useCallback, lazy, Suspense } from 'react';
import { AutonomyProvider, useAutonomy } from './contexts/AutonomyContext';
import AppLayout from './components/AppLayout';
import DemoIframeContainer from './components/DemoIframeContainer';
const AOSOverviewPage = lazy(() => import('./components/AOSOverviewPage'));
const OrchestrationDashboard = lazy(() => import('./components/orchestration/OrchestrationDashboard'));
const FAQPage = lazy(() => import('./components/FAQPage'));
const DemoFlow = lazy(() => import('./components/demo/DemoFlow'));

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
    const validPages = ['aos-overview', 'nlq', 'discover', 'connect', 'unify-ask', 'orchestration', 'farm', 'faq', 'demo'];
    return validPages.includes(path) ? path : 'nlq';
  };

  const [currentPage, setCurrentPage] = useState(getInitialPage());
  const { legacyMode } = useAutonomy();
  // Track visited iframe pages so we only mount them when first navigated to
  const [visitedIframes, setVisitedIframes] = useState<Set<string>>(() => {
    const initial = getInitialPage();
    return IFRAME_PAGES[initial] ? new Set([initial]) : new Set();
  });

  const navigateTo = useCallback((page: string) => {
    setCurrentPage(page);
    if (IFRAME_PAGES[page]) {
      setVisitedIframes(prev => new Set(prev).add(page));
    }
  }, []);

  const handleExitDemo = useCallback(() => {
    navigateTo('nlq');
    window.history.pushState({}, '', '/nlq');
  }, [navigateTo]);

  useEffect(() => {
    const handleNavigation = (event: Event) => {
      const customEvent = event as CustomEvent;
      const page = customEvent.detail?.page;
      if (page) {
        navigateTo(page);
        window.history.pushState({}, '', `/${page}`);
      }
    };

    window.addEventListener('navigate', handleNavigation);
    return () => {
      window.removeEventListener('navigate', handleNavigation);
    };
  }, [navigateTo]);

  useEffect(() => {
    const handlePopState = () => {
      const path = window.location.pathname.slice(1);
      const validPages = ['aos-overview', 'nlq', 'discover', 'connect', 'unify-ask', 'orchestration', 'farm', 'faq', 'demo'];
      if (validPages.includes(path)) {
        navigateTo(path);
      }
    };

    window.addEventListener('popstate', handlePopState);
    return () => {
      window.removeEventListener('popstate', handlePopState);
    };
  }, [navigateTo]);

  // Demo mode — takes over the full viewport below TopBar
  if (currentPage === 'demo') {
    return (
      <AppLayout currentPage={currentPage} onNavigate={navigateTo}>
        <Suspense fallback={<PageLoader />}>
          <DemoFlow onExit={handleExitDemo} />
        </Suspense>
      </AppLayout>
    );
  }

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
    <AppLayout currentPage={currentPage} onNavigate={navigateTo}>
      {!isIframePage && (
        <Suspense fallback={<PageLoader />}>
          {renderNonIframePage()}
        </Suspense>
      )}

      {/* Only mount iframes the user has actually navigated to */}
      {Object.keys(IFRAME_PAGES).filter(k => visitedIframes.has(k)).map(pageKey => {
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
