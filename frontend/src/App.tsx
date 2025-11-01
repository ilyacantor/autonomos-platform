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

function AppContent() {
  const [currentPage, setCurrentPage] = useState('dashboard');
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
      }
    };

    window.addEventListener('navigate', handleNavigation);
    return () => {
      window.removeEventListener('navigate', handleNavigation);
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
