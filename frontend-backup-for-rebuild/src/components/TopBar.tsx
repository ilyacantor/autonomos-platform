import { useState } from 'react';
import { Search, Bell, ChevronDown, LogOut, Menu } from 'lucide-react';
import AutonomyModeToggle from './AutonomyModeToggle';
import { useAuth } from '../hooks/useAuth';
import type { User, PersonaType } from '../types';

interface TopBarProps {
  user: User;
  onPersonaChange: (persona: PersonaType) => void;
  onMobileMenuToggle?: () => void;
}

export default function TopBar({ user, onPersonaChange, onMobileMenuToggle }: TopBarProps) {
  const [showDropdown, setShowDropdown] = useState(false);
  const [hasNotifications] = useState(true);
  const { logout } = useAuth();

  const personas: PersonaType[] = ['Data Engineer', 'RevOps', 'FinOps'];

  const handleLogout = () => {
    logout();
    setShowDropdown(false);
  };

  return (
    <div className="h-16 bg-gray-900 border-b border-gray-800 flex items-center px-3 sm:px-6 gap-2 sm:gap-6">
      {/* Mobile Hamburger Menu - only visible on <768px */}
      <button
        onClick={onMobileMenuToggle}
        className="md:hidden p-2 hover:bg-gray-800 rounded-lg transition-colors text-gray-400 min-w-[44px] min-h-[44px] flex items-center justify-center"
      >
        <Menu className="w-5 h-5" />
      </button>

      {/* Search Bar - hidden on small mobile, visible on tablet+ */}
      <div className="flex-1 max-w-2xl hidden sm:block">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            placeholder="Search or type a command..."
            className="w-full bg-gray-800 text-gray-200 pl-10 pr-4 py-2 rounded-lg border border-gray-700 focus:outline-none focus:border-blue-500 transition-colors"
          />
        </div>
      </div>

      {/* Autonomy Toggle */}
      <div className="flex items-center gap-3">
        <AutonomyModeToggle />
      </div>

      {/* Notifications - hidden on very small screens */}
      <div className="relative hidden xs:block">
        <button className="p-2 hover:bg-gray-800 rounded-lg transition-colors relative min-w-[44px] min-h-[44px] flex items-center justify-center">
          <Bell className="w-5 h-5 text-gray-400" />
          {hasNotifications && (
            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full"></span>
          )}
        </button>
      </div>

      {/* User Profile - compact on mobile */}
      <div className="relative">
        <button
          onClick={() => setShowDropdown(!showDropdown)}
          className="flex items-center gap-2 sm:gap-3 hover:bg-gray-800 px-2 sm:px-3 py-2 rounded-lg transition-colors min-h-[44px]"
        >
          <img
            src={user.avatar}
            alt={user.name}
            className="w-8 h-8 rounded-full"
          />
          {/* User info - hidden on very small screens */}
          <div className="text-left hidden sm:block">
            <div className="text-sm font-medium text-gray-200">{user.name}</div>
            <div className="text-xs text-gray-500">{user.persona}</div>
          </div>
          <ChevronDown className="w-4 h-4 text-gray-400" />
        </button>

        {showDropdown && (
          <>
            <div
              className="fixed inset-0 z-10"
              onClick={() => setShowDropdown(false)}
            />
            <div className="absolute right-0 mt-2 w-56 bg-gray-800 border border-gray-700 rounded-lg shadow-xl z-20">
              <div className="p-2">
                <div className="px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Select Persona
                </div>
                {personas.map((persona) => (
                  <button
                    key={persona}
                    onClick={() => {
                      onPersonaChange(persona);
                      setShowDropdown(false);
                    }}
                    className={`w-full text-left px-3 py-2 rounded-md transition-colors ${
                      user.persona === persona
                        ? 'bg-blue-600 text-white'
                        : 'text-gray-300 hover:bg-gray-700'
                    }`}
                  >
                    {persona}
                  </button>
                ))}
                <div className="border-t border-gray-700 my-2" />
                <button
                  onClick={handleLogout}
                  className="w-full text-left px-3 py-2 rounded-md text-red-400 hover:bg-gray-700 transition-colors flex items-center gap-2"
                >
                  <LogOut className="w-4 h-4" />
                  Logout
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
