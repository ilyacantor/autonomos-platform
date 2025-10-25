import { useState } from 'react';
import { AutonomyProvider, useAutonomy } from './contexts/AutonomyContext';
import { AuthProvider } from './context/AuthContext';
import { useAuth } from './hooks/useAuth';
import AppLayout from './components/AppLayout';
import DashboardPage from './components/DashboardPage';
import DataLineagePage from './components/DataLineagePage';
import ConnectionsPage from './components/ConnectionsPage';
import XAOPage from './components/xAOPage';
import OntologyPage from './components/OntologyPage';
import LegacyDCLUI from './components/LegacyDCLUI';
import AuthModal from './components/AuthModal';

function AppContent() {
  const [currentPage, setCurrentPage] = useState('dashboard');
  const { legacyMode } = useAutonomy();
  const { isAuthenticated, isLoading } = useAuth();

  const renderPage = () => {
    switch (currentPage) {
      case 'dashboard':
        return <DashboardPage />;
      case 'lineage':
        return <DataLineagePage />;
      case 'connections':
        return <ConnectionsPage />;
      case 'xao':
        return <XAOPage />;
      case 'ontology':
        return <OntologyPage />;
      case 'settings':
        return (
          <div className="text-center py-12">
            <h1 className="text-3xl font-bold text-white mb-4">Settings</h1>
            <p className="text-gray-400">Platform settings coming soon</p>
          </div>
        );
      default:
        return <DashboardPage />;
    }
  };

  // Show loading spinner while checking authentication
  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-400">Loading autonomOS...</p>
        </div>
      </div>
    );
  }

  // PINNED: Legacy mode DISABLED - always use modern TopBar layout
  // if (legacyMode) {
  //   return <LegacyDCLUI />;
  // }
  console.log('[PIN] Legacy UI path BLOCKED - forcing modern TopBar layout');

  // Modern mode requires authentication
  if (!isAuthenticated) {
    return <AuthModal isOpen={true} onClose={() => {}} />;
  }

  return (
    <AppLayout currentPage={currentPage} onNavigate={setCurrentPage}>
      {renderPage()}
    </AppLayout>
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
