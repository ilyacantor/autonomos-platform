import { useState } from 'react';
import { LayoutDashboard, Cable, Network, Bell, Menu, X, LogIn, UserPlus, HelpCircle, Activity, Search } from 'lucide-react';
import type { PersonaType } from '../types';
import autonomosLogo from '../assets/autonomos-logo.png';

interface TopBarProps {
  onAuthOpen: (mode: 'login' | 'signup') => void;
  currentPage: string;
  onNavigate: (page: string) => void;
}

interface NavItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  tooltip?: string;
}

export default function TopBar({ onAuthOpen, currentPage, onNavigate }: TopBarProps) {
  const [showMobileMenu, setShowMobileMenu] = useState(false);
  const [hasNotifications] = useState(true);

  const navItems: NavItem[] = [
    { id: 'control-center', label: 'Control Center', icon: <LayoutDashboard className="w-5 h-5" /> },
    { id: 'discover', label: 'Discovery', icon: <Search className="w-5 h-5" /> },
    { id: 'connect', label: 'Connections', icon: <Cable className="w-5 h-5" />, tooltip: 'AAM Connect - Self-healing data connectivity' },
    { id: 'ontology', label: 'Ontology', icon: <Network className="w-5 h-5" /> },
    { id: 'orchestration', label: 'Orchestration', icon: <Activity className="w-5 h-5" /> },
    { id: 'agents', label: 'Agents', icon: <Activity className="w-5 h-5" /> },
    { id: 'faq', label: 'Help', icon: <HelpCircle className="w-5 h-5" /> },
  ];

  return (
    <>
      <div className="h-16 bg-gray-900 border-b border-gray-800 flex items-center px-4 sm:px-6 gap-3 sm:gap-6 safe-x">
        {/* Logo */}
        <div className="flex-shrink-0 -ml-[10px]">
          <button
            onClick={() => onNavigate('control-center')}
            className="hover:opacity-80 transition-opacity cursor-pointer"
          >
            <img 
              src={autonomosLogo} 
              alt="autonomOS" 
              className="h-[36px] sm:h-[42px] object-contain"
            />
          </button>
        </div>

        {/* Desktop Navigation Items - Hidden on Mobile */}
        <nav className="hidden sm:flex flex-1 items-center gap-1">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              title={item.tooltip}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all flex-shrink-0 touch-target-h ${
                currentPage === item.id
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
              } ${
                item.id === 'faq'
                  ? 'ring-2 ring-[#0BCAD9]/50 shadow-lg shadow-[#0BCAD9]/30 animate-pulse'
                  : ''
              }`}
            >
              {item.icon}
              <span className="font-medium text-sm whitespace-nowrap">{item.label}</span>
            </button>
          ))}
        </nav>

        {/* Mobile Spacer */}
        <div className="flex-1 sm:hidden"></div>

        {/* Right Side: Notifications, Profile */}
        <div className="flex items-center gap-2 sm:gap-3 flex-shrink-0">
          {/* Notifications */}
          <div className="relative">
            <button className="p-2 hover:bg-gray-800 rounded-lg transition-colors relative touch-target mobile-tap-highlight">
              <Bell className="w-5 h-5 text-gray-400" />
              {hasNotifications && (
                <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full"></span>
              )}
            </button>
          </div>

          {/* Auth Buttons - Login & Sign Up */}
          <div className="hidden sm:flex items-center gap-2">
            <button
              onClick={() => onAuthOpen('login')}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-200 transition-colors touch-target-h mobile-tap-highlight"
            >
              <LogIn className="w-4 h-4" />
              <span className="font-medium text-sm">Login</span>
            </button>
            <button
              onClick={() => onAuthOpen('signup')}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white transition-colors touch-target-h mobile-tap-highlight"
            >
              <UserPlus className="w-4 h-4" />
              <span className="font-medium text-sm">Sign Up</span>
            </button>
          </div>

          {/* Mobile Menu Button - Show Only on Mobile */}
          <button
            onClick={() => setShowMobileMenu(!showMobileMenu)}
            className="sm:hidden p-2 hover:bg-gray-800 rounded-lg transition-colors touch-target mobile-tap-highlight"
          >
            {showMobileMenu ? (
              <X className="w-6 h-6 text-gray-400" />
            ) : (
              <Menu className="w-6 h-6 text-gray-400" />
            )}
          </button>
        </div>
      </div>

      {/* Mobile Menu Drawer */}
      {showMobileMenu && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/60 z-40 sm:hidden"
            onClick={() => setShowMobileMenu(false)}
          />
          
          {/* Mobile Menu Panel */}
          <div className="fixed top-16 right-0 bottom-0 w-64 bg-gray-900 border-l border-gray-800 z-50 sm:hidden safe-x safe-bottom">
            <div className="flex flex-col h-full p-4">
              {/* Navigation Items */}
              <nav className="flex flex-col gap-2 mb-6">
                {navItems.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => {
                      onNavigate(item.id);
                      setShowMobileMenu(false);
                    }}
                    className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-all touch-target-h mobile-tap-highlight ${
                      currentPage === item.id
                        ? 'bg-blue-600 text-white'
                        : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
                    } ${
                      item.id === 'faq'
                        ? 'ring-2 ring-[#0BCAD9]/50 shadow-lg shadow-[#0BCAD9]/30 animate-pulse'
                        : ''
                    }`}
                  >
                    {item.icon}
                    <span className="font-medium text-base">{item.label}</span>
                  </button>
                ))}
              </nav>

              {/* Auth Buttons for Mobile */}
              <div className="border-t border-gray-800 pt-4 mt-auto">
                <div className="flex flex-col gap-2">
                  <button
                    onClick={() => {
                      onAuthOpen('login');
                      setShowMobileMenu(false);
                    }}
                    className="flex items-center gap-2 px-4 py-3 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-200 transition-colors touch-target-h mobile-tap-highlight justify-center"
                  >
                    <LogIn className="w-5 h-5" />
                    <span className="font-medium">Login</span>
                  </button>
                  <button
                    onClick={() => {
                      onAuthOpen('signup');
                      setShowMobileMenu(false);
                    }}
                    className="flex items-center gap-2 px-4 py-3 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white transition-colors touch-target-h mobile-tap-highlight justify-center"
                  >
                    <UserPlus className="w-5 h-5" />
                    <span className="font-medium">Sign Up</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </>
  );
}
