import { useState, useEffect } from 'react';
import { AutonomyProvider, useAutonomy } from './contexts/AutonomyContext';
import { AuthProvider } from './context/AuthContext';
import { useAuth } from './hooks/useAuth';
import AppLayout from './components/AppLayout';
import PlatformGuidePage from './components/PlatformGuidePage';
import AOSOverviewPage from './components/AOSOverviewPage';
import ControlCenterPage from './components/ControlCenterPage';
import DiscoverPage from './components/DiscoverPage';
import ConnectPage from './components/ConnectPage';
import NewOntologyPage from './components/NewOntologyPage';
import OrchestrationPage from './components/OrchestrationPage';
import FAQPage from './components/FAQPage';
import AuthModal from './components/AuthModal';

function AppContent() {
  // Initialize page from URL path
  const getInitialPage = () => {
    const path = window.location.pathname.slice(1); // Remove leading slash
    const validPages = ['architecture', 'aos-overview', 'control-center', 'discover', 'connect', 'ontology', 'orchestration', 'faq'];
    return validPages.includes(path) ? path : 'architecture';
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
      const validPages = ['architecture', 'aos-overview', 'control-center', 'discover', 'connect', 'ontology', 'orchestration', 'faq'];
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
      case 'architecture':
        return <PlatformGuidePage />;
      case 'aos-overview':
        return <AOSOverviewPage />;
      case 'control-center':
        return <ControlCenterPage />;
      case 'discover':
        return <DiscoverPage />;
      case 'connect':
        return <ConnectPage />;
      case 'ontology':
        return <NewOntologyPage />;
      case 'orchestration':
        return <OrchestrationPage />;
      case 'faq':
        return <FAQPage />;
      default:
        return <PlatformGuidePage />;
    }
  };

  return (
    <>
      <AppLayout currentPage={currentPage} onNavigate={setCurrentPage} onAuthOpen={handleAuthOpen}>
        {renderPage()}
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
