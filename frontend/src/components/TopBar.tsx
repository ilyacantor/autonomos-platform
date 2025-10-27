import { useState } from 'react';
import { LayoutDashboard, Cable, Network, Settings, Bell, ChevronDown, LogOut, Menu, X } from 'lucide-react';
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
  const [showMobileMenu, setShowMobileMenu] = useState(false);
  const [hasNotifications] = useState(true);
  const { logout } = useAuth();

  const personas: PersonaType[] = ['Data Engineer', 'RevOps', 'FinOps'];

  const navItems: NavItem[] = [
    { id: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard className="w-5 h-5" /> },
    { id: 'connections', label: 'Connections', icon: <Cable className="w-5 h-5" /> },
    { id: 'ontology', label: 'Ontology', icon: <Network className="w-5 h-5" /> },
    { id: 'settings', label: 'Settings', icon: <Settings className="w-5 h-5" /> },
  ];

  const handleLogout = () => {
    logout();
    setShowDropdown(false);
  };

  return (
    <>
      <div className="h-16 bg-gray-900 border-b border-gray-800 flex items-center px-4 sm:px-6 gap-3 sm:gap-6 safe-x">
        {/* Logo */}
        <div className="flex-shrink-0">
          <img 
            src={autonomosLogo} 
            alt="autonomOS" 
            className="h-[36px] sm:h-[42px] object-contain"
          />
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
              }`}
            >
              {item.icon}
              <span className="font-medium text-sm whitespace-nowrap">{item.label}</span>
            </button>
          ))}
        </nav>

        {/* Mobile Spacer */}
        <div className="flex-1 sm:hidden"></div>

        {/* Right Side: Autonomy Toggle, Notifications, Profile */}
        <div className="flex items-center gap-2 sm:gap-3 flex-shrink-0">
          {/* Autonomy Toggle - Hidden on Mobile */}
          <div className="hidden sm:block">
            <AutonomyModeToggle />
          </div>

          {/* Notifications */}
          <div className="relative">
            <button className="p-2 hover:bg-gray-800 rounded-lg transition-colors relative touch-target mobile-tap-highlight">
              <Bell className="w-5 h-5 text-gray-400" />
              {hasNotifications && (
                <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full"></span>
              )}
            </button>
          </div>

          {/* User Profile - Compact on Mobile */}
          <div className="relative">
            <button
              onClick={() => setShowDropdown(!showDropdown)}
              className="flex items-center gap-2 sm:gap-3 hover:bg-gray-800 px-2 sm:px-3 py-2 rounded-lg transition-colors touch-target-h mobile-tap-highlight"
            >
              <img
                src={user.avatar}
                alt={user.name}
                className="w-8 h-8 rounded-full"
              />
              {/* Hide name and persona on mobile */}
              <div className="text-left hide-mobile">
                <div className="text-sm font-medium text-gray-200">{user.name}</div>
                <div className="text-xs text-gray-500">{user.persona}</div>
              </div>
              <ChevronDown className="w-4 h-4 text-gray-400" />
            </button>

            {showDropdown && (
              <>
                <div
                  className="fixed inset-0 z-40"
                  onClick={() => setShowDropdown(false)}
                />
                <div className="absolute right-0 mt-2 w-56 bg-gray-800 border border-gray-700 rounded-lg shadow-xl z-50">
                  <div className="p-2">
                    <div className="px-3 py-2 text-xs text-gray-500 tracking-wider">
                      Select Persona
                    </div>
                    {personas.map((persona) => (
                      <button
                        key={persona}
                        onClick={() => {
                          onPersonaChange(persona);
                          setShowDropdown(false);
                        }}
                        className={`w-full text-left px-3 py-2 rounded-md transition-colors touch-target-h ${
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
                      className="w-full text-left px-3 py-2 rounded-md text-red-400 hover:bg-gray-700 transition-colors flex items-center gap-2 touch-target-h"
                    >
                      <LogOut className="w-4 h-4" />
                      Logout
                    </button>
                  </div>
                </div>
              </>
            )}
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
                    }`}
                  >
                    {item.icon}
                    <span className="font-medium text-base">{item.label}</span>
                  </button>
                ))}
              </nav>

              {/* Autonomy Mode Toggle */}
              <div className="border-t border-gray-800 pt-4 mb-4">
                <div className="text-xs text-gray-500 mb-2 px-2">Autonomy Mode</div>
                <AutonomyModeToggle />
              </div>

              {/* User Info */}
              <div className="border-t border-gray-800 pt-4 mt-auto">
                <div className="flex items-center gap-3 px-2 mb-4">
                  <img
                    src={user.avatar}
                    alt={user.name}
                    className="w-10 h-10 rounded-full"
                  />
                  <div>
                    <div className="text-sm font-medium text-gray-200">{user.name}</div>
                    <div className="text-xs text-gray-500">{user.persona}</div>
                  </div>
                </div>
                
                {/* Persona Switcher */}
                <div className="text-xs text-gray-500 mb-2 px-2">Switch Persona</div>
                <div className="flex flex-col gap-1 mb-4">
                  {personas.map((persona) => (
                    <button
                      key={persona}
                      onClick={() => {
                        onPersonaChange(persona);
                        setShowMobileMenu(false);
                      }}
                      className={`text-left px-3 py-2 rounded-md transition-colors touch-target-h mobile-tap-highlight ${
                        user.persona === persona
                          ? 'bg-blue-600 text-white'
                          : 'text-gray-300 hover:bg-gray-700'
                      }`}
                    >
                      {persona}
                    </button>
                  ))}
                </div>

                {/* Logout Button */}
                <button
                  onClick={() => {
                    handleLogout();
                    setShowMobileMenu(false);
                  }}
                  className="w-full text-left px-3 py-3 rounded-md text-red-400 hover:bg-gray-800 transition-colors flex items-center gap-2 touch-target-h mobile-tap-highlight"
                >
                  <LogOut className="w-5 h-5" />
                  <span className="font-medium">Logout</span>
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </>
  );
}
