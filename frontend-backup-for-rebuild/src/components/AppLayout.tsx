import { useState } from 'react';
import TopBar from './TopBar';
import type { User, PersonaType } from '../types';

interface AppLayoutProps {
  children: React.ReactNode;
  currentPage: string;
  onNavigate: (page: string) => void;
}

export default function AppLayout({ children, currentPage, onNavigate }: AppLayoutProps) {
  const [user, setUser] = useState<User>({
    name: 'Alex Johnson',
    avatar: 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=100&h=100&fit=crop',
    persona: 'Data Engineer',
  });

  const handlePersonaChange = (persona: PersonaType) => {
    setUser({ ...user, persona });
  };

  return (
    <div className="h-screen flex flex-col bg-gray-950">
      <TopBar 
        user={user} 
        onPersonaChange={handlePersonaChange}
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
