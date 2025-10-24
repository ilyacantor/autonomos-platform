import { useState } from 'react';
import { Menu } from 'lucide-react';
import TopBar from './TopBar';
import LeftNav from './LeftNav';
import type { User, PersonaType } from '../types';

interface AppLayoutProps {
  children: React.ReactNode;
  currentPage: string;
  onNavigate: (page: string) => void;
}

export default function AppLayout({ children, currentPage, onNavigate }: AppLayoutProps) {
  const [isNavCollapsed, setIsNavCollapsed] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [user, setUser] = useState<User>({
    name: 'Alex Johnson',
    avatar: 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=100&h=100&fit=crop',
    persona: 'Data Engineer',
  });

  const handlePersonaChange = (persona: PersonaType) => {
    setUser({ ...user, persona });
  };

  const handleMobileNavigation = (page: string) => {
    onNavigate(page);
    setIsMobileMenuOpen(false); // Close mobile menu after navigation
  };

  return (
    <div className="h-screen flex flex-col bg-gray-950">
      <div className="flex flex-1 overflow-hidden relative">
        {/* Mobile Menu Overlay - only visible on mobile when menu is open */}
        {isMobileMenuOpen && (
          <div
            className="fixed inset-0 bg-black/50 z-40 md:hidden"
            onClick={() => setIsMobileMenuOpen(false)}
          />
        )}

        {/* Left Navigation - responsive behavior */}
        <LeftNav
          isCollapsed={isNavCollapsed}
          currentPage={currentPage}
          onNavigate={handleMobileNavigation}
          isMobileMenuOpen={isMobileMenuOpen}
          onCloseMobile={() => setIsMobileMenuOpen(false)}
        />

        <div className="flex-1 flex flex-col overflow-hidden">
          <TopBar 
            user={user} 
            onPersonaChange={handlePersonaChange}
            onMobileMenuToggle={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          />

          <div className="flex-1 overflow-auto">
            <div className="p-4 md:p-6">
              {/* Desktop menu toggle - hidden on mobile */}
              <button
                onClick={() => setIsNavCollapsed(!isNavCollapsed)}
                className="hidden md:block mb-4 p-2 hover:bg-gray-800 rounded-lg transition-colors text-gray-400"
              >
                <Menu className="w-5 h-5" />
              </button>
              {children}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
