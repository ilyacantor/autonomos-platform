import { useState, useEffect, lazy, Suspense } from 'react';
import { AutonomyProvider, useAutonomy } from './contexts/AutonomyContext';
import { AuthProvider } from './context/AuthContext';
import { useAuth } from './hooks/useAuth';
import AppLayout from './components/AppLayout';
import AuthModal from './components/AuthModal';

// Lazy load all page components for faster initial load
const AOSOverviewPage = lazy(() => import('./components/AOSOverviewPage'));
const ControlCenterPage = lazy(() => import('./components/ControlCenterPage'));
const DiscoverPage = lazy(() => import('./components/DiscoverPage'));
const ConnectPage = lazy(() => import('./components/ConnectPage'));
const UnifyAskPage = lazy(() => import('./components/UnifyAskPage'));
const DemoPage = lazy(() => import('./components/DemoPage'));
const OrchestrationDashboard = lazy(() => import('./components/orchestration/OrchestrationDashboard'));

// Loading spinner for lazy-loaded pages
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
  // Initialize page from URL path
  const getInitialPage = () => {
    const path = window.location.pathname.slice(1); // Remove leading slash
    const validPages = ['aos-overview', 'control-center', 'discover', 'connect', 'unify-ask', 'demo', 'orchestration'];
    return validPages.includes(path) ? path : 'control-center';
  };

  const [currentPage, setCurrentPage] = useState(getInitialPage());
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [authMode, setAuthMode] = useState<'login' | 'signup'>('login');
  const { legacyMode } = useAutonomy();

  // Listen for navigation events from components
  useEffect(() => {
    const handleNavigation = (event: Event) => {
      const customEvent = event as CustomEvent;
      const page = customEvent.detail?.page;
      if (page) {
        setCurrentPage(page);
        // Update URL to match page
        window.history.pushState({}, '', `/${page}`);
      }
    };

    window.addEventListener('navigate', handleNavigation);
    return () => {
      window.removeEventListener('navigate', handleNavigation);
    };
  }, []);

  // Sync URL changes (browser back/forward) with currentPage
  useEffect(() => {
    const handlePopState = () => {
      const path = window.location.pathname.slice(1);
      const validPages = ['aos-overview', 'control-center', 'discover', 'connect', 'unify-ask', 'demo', 'orchestration'];
      if (validPages.includes(path)) {
        setCurrentPage(path);
      }
    };

    window.addEventListener('popstate', handlePopState);
    return () => {
      window.removeEventListener('popstate', handlePopState);
    };
  }, []);

  const handleAuthOpen = (mode: 'login' | 'signup') => {
    setAuthMode(mode);
    setAuthModalOpen(true);
  };

  const handleAuthClose = () => {
    setAuthModalOpen(false);
  };

  const renderPage = () => {
    switch (currentPage) {
      case 'aos-overview':
        return <AOSOverviewPage />;
      case 'control-center':
        return <ControlCenterPage />;
      case 'discover':
        return <DiscoverPage />;
      case 'connect':
        return <ConnectPage />;
      case 'unify-ask':
        return <UnifyAskPage />;
      case 'demo':
        return <DemoPage />;
      case 'orchestration':
        return <OrchestrationDashboard />;
      default:
        return <ControlCenterPage />;
    }
  };

  return (
    <>
      <AppLayout currentPage={currentPage} onNavigate={setCurrentPage} onAuthOpen={handleAuthOpen}>
        <Suspense fallback={<PageLoader />}>
          {renderPage()}
        </Suspense>
      </AppLayout>

      {/* Auth modal only shows when user clicks Login or Sign Up */}
      {authModalOpen && (
        <AuthModal
          isOpen={authModalOpen}
          onClose={handleAuthClose}
          initialMode={authMode}
        />
      )}
    </>
  );
}

function App() {
  return (
    <AuthProvider>
      <AutonomyProvider>
        <AppContent />
      </AutonomyProvider>
    </AuthProvider>
  );
}

export default App;
