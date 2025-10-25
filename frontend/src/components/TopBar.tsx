import { useState } from 'react';
import { LayoutDashboard, Cable, Bot, Network, Settings, Bell, ChevronDown, LogOut } from 'lucide-react';
import AutonomyModeToggle from './AutonomyModeToggle';
import { useAuth } from '../hooks/useAuth';
import type { User, PersonaType } from '../types';
import autonomosLogo from '../assets/autonomos-logo.png';

interface TopBarProps {
  user: User;
  onPersonaChange: (persona: PersonaType) => void;
  currentPage: string;
  onNavigate: (page: string) => void;
}

interface NavItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  tooltip?: string;
}

export default function TopBar({ user, onPersonaChange, currentPage, onNavigate }: TopBarProps) {
  const [showDropdown, setShowDropdown] = useState(false);
  const [hasNotifications] = useState(true);
  const { logout } = useAuth();

  const personas: PersonaType[] = ['Data Engineer', 'RevOps', 'FinOps'];

  const navItems: NavItem[] = [
    { id: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard className="w-5 h-5" /> },
    { id: 'connections', label: 'Connections', icon: <Cable className="w-5 h-5" /> },
    { id: 'xao', label: 'xAO', icon: <Bot className="w-5 h-5" />, tooltip: 'Cross-Agentic Orchestration (xAO) coordinates multiple autonomOS instances across federated domains.' },
    { id: 'ontology', label: 'Ontology', icon: <Network className="w-5 h-5" /> },
    { id: 'settings', label: 'Settings', icon: <Settings className="w-5 h-5" /> },
  ];

  const handleLogout = () => {
    logout();
    setShowDropdown(false);
  };

  return (
    <div className="h-16 bg-gray-900 border-b border-gray-800 flex items-center px-6 gap-6">
      {/* Logo */}
      <div className="flex-shrink-0">
        <img 
          src={autonomosLogo} 
          alt="autonomOS" 
          className="h-[42px] object-contain"
        />
      </div>

      {/* Navigation Items */}
      <nav className="flex-1 flex items-center gap-1">
        {navItems.map((item) => (
          <button
            key={item.id}
            onClick={() => onNavigate(item.id)}
            title={item.tooltip}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all ${
              currentPage === item.id
                ? 'bg-blue-600 text-white'
                : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
            }`}
          >
            {item.icon}
            <span className="font-medium text-sm">{item.label}</span>
          </button>
        ))}
      </nav>

      {/* Right Side: Autonomy Toggle, Notifications, Profile */}
      <div className="flex items-center gap-3">
        {/* Autonomy Toggle */}
        <AutonomyModeToggle />

        {/* Notifications */}
        <div className="relative">
          <button className="p-2 hover:bg-gray-800 rounded-lg transition-colors relative min-w-[44px] min-h-[44px] flex items-center justify-center">
            <Bell className="w-5 h-5 text-gray-400" />
            {hasNotifications && (
              <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full"></span>
            )}
          </button>
        </div>

        {/* User Profile */}
        <div className="relative">
          <button
            onClick={() => setShowDropdown(!showDropdown)}
            className="flex items-center gap-3 hover:bg-gray-800 px-3 py-2 rounded-lg transition-colors min-h-[44px]"
          >
            <img
              src={user.avatar}
              alt={user.name}
              className="w-8 h-8 rounded-full"
            />
            <div className="text-left">
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
    </div>
  );
}
