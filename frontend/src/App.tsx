import { useState, useEffect } from 'react';
import { AutonomyProvider, useAutonomy } from './contexts/AutonomyContext';
import { AuthProvider } from './context/AuthContext';
import { useAuth } from './hooks/useAuth';
import AppLayout from './components/AppLayout';
import DashboardPage from './components/DashboardPage';
import DataLineagePage from './components/DataLineagePage';
import ConnectionsPage from './components/ConnectionsPage';
import OntologyPage from './components/OntologyPage';
import FAQPage from './components/FAQPage';
import LegacyDCLUI from './components/LegacyDCLUI';
import AuthModal from './components/AuthModal';
import AAMDashboard from './components/AAMDashboard';
import LiveFlow from './components/monitor/LiveFlow';

function AppContent() {
  // Initialize page from URL path
  const getInitialPage = () => {
    const path = window.location.pathname.slice(1); // Remove leading slash
    const validPages = ['dashboard', 'lineage', 'connections', 'ontology', 'aam-monitor', 'live-flow', 'faq'];
    return validPages.includes(path) ? path : 'dashboard';
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
      const validPages = ['dashboard', 'lineage', 'connections', 'ontology', 'aam-monitor', 'live-flow', 'faq'];
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
      case 'dashboard':
        return <DashboardPage />;
      case 'lineage':
        return <DataLineagePage />;
      case 'connections':
        return <ConnectionsPage />;
      case 'ontology':
        return <OntologyPage />;
      case 'aam-monitor':
        return <AAMDashboard />;
      case 'live-flow':
        return <LiveFlow />;
      case 'faq':
        return <FAQPage />;
      default:
        return <DashboardPage />;
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
