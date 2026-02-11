import { useState, useEffect, lazy, Suspense } from 'react';
import { AutonomyProvider, useAutonomy } from './contexts/AutonomyContext';
import AppLayout from './components/AppLayout';

const AOSOverviewPage = lazy(() => import('./components/AOSOverviewPage'));
const DiscoverPage = lazy(() => import('./components/DiscoverPage'));
const ConnectPage = lazy(() => import('./components/ConnectPage'));
const UnifyAskPage = lazy(() => import('./components/UnifyAskPage'));
const NLQPage = lazy(() => import('./components/NLQPage'));
const OrchestrationDashboard = lazy(() => import('./components/orchestration/OrchestrationDashboard'));
const FarmPage = lazy(() => import('./components/FarmPage'));
const FAQPage = lazy(() => import('./components/FAQPage'));

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
    return validPages.includes(path) ? path : 'aos-overview';
  };

  const [currentPage, setCurrentPage] = useState(getInitialPage());
  const { legacyMode } = useAutonomy();

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

  const renderPage = () => {
    switch (currentPage) {
      case 'aos-overview':
        return <AOSOverviewPage />;
      case 'nlq':
        return <NLQPage />;
      case 'discover':
        return <DiscoverPage />;
      case 'connect':
        return <ConnectPage />;
      case 'unify-ask':
        return <UnifyAskPage />;
      case 'orchestration':
        return <OrchestrationDashboard />;
      case 'farm':
        return <FarmPage />;
      case 'faq':
        return <FAQPage />;
      default:
        return <AOSOverviewPage />;
    }
  };

  return (
    <AppLayout currentPage={currentPage} onNavigate={setCurrentPage}>
      <Suspense fallback={<PageLoader />}>
        {renderPage()}
      </Suspense>
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
