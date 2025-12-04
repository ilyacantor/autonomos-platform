import TopBar from './TopBar';

interface AppLayoutProps {
  children: React.ReactNode;
  currentPage: string;
  onNavigate: (page: string) => void;
  onAuthOpen: (mode: 'login' | 'signup') => void;
}

export default function AppLayout({ children, currentPage, onNavigate, onAuthOpen }: AppLayoutProps) {
  return (
    <div className="h-screen flex flex-col bg-gray-950">
      <TopBar 
        onAuthOpen={onAuthOpen}
        currentPage={currentPage}
        onNavigate={onNavigate}
      />

      <div className="flex-1 overflow-auto">
        <div className="p-6">
          {children}
        </div>
      </div>
    </div>
  );
}
