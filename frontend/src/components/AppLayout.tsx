import TopBar from './TopBar';

interface AppLayoutProps {
  children: React.ReactNode;
  currentPage: string;
  onNavigate: (page: string) => void;
}

export default function AppLayout({ children, currentPage, onNavigate }: AppLayoutProps) {
  return (
    <div className="h-screen flex flex-col bg-gray-950">
      <TopBar 
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
