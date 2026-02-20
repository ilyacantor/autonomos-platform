import { useState } from 'react';
import { Cable, Menu, X, HelpCircle, Search, Sparkles, Database, Activity, Wheat, Play } from 'lucide-react';
import autonomosLogo from '../assets/autonomos-logo.png';

interface TopBarProps {
  currentPage: string;
  onNavigate: (page: string) => void;
}

interface NavItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  tooltip?: string;
}

export default function TopBar({ currentPage, onNavigate }: TopBarProps) {
  const [showMobileMenu, setShowMobileMenu] = useState(false);

  const navItems: NavItem[] = [
    { id: 'demo', label: 'Demo', icon: <Play className="w-5 h-5" />, tooltip: 'Guided product walkthrough' },
    { id: 'aos-overview', label: 'Overview', icon: <Sparkles className="w-5 h-5" />, tooltip: 'Interactive platform overview' },
    { id: 'nlq', label: 'NLQ', icon: <Search className="w-5 h-5" />, tooltip: 'Natural Language Query' },
    { id: 'discover', label: 'AOD', icon: <Search className="w-5 h-5" />, tooltip: 'Asset & Observability Discovery' },
    { id: 'connect', label: 'AAM', icon: <Cable className="w-5 h-5" />, tooltip: 'Adaptive API Mesh' },
    { id: 'unify-ask', label: 'DCL', icon: <Database className="w-5 h-5" />, tooltip: 'Data Connectivity Layer' },
    { id: 'orchestration', label: 'AOA', icon: <Activity className="w-5 h-5" />, tooltip: 'Agentic Orchestration Architecture' },
    { id: 'farm', label: 'Farm', icon: <Wheat className="w-5 h-5" />, tooltip: 'Agent Farm' },
    { id: 'faq', label: 'Help', icon: <HelpCircle className="w-5 h-5" /> },
  ];

  return (
    <>
      <div className="h-16 bg-gray-900 border-b border-gray-800 flex items-center px-4 sm:px-6 gap-3 sm:gap-6 safe-x">
        <div className="flex-shrink-0 -ml-[10px]">
          <button
            onClick={() => onNavigate('aos-overview')}
            className="hover:opacity-80 transition-opacity cursor-pointer"
          >
            <img 
              src={autonomosLogo} 
              alt="autonomOS" 
              className="h-[36px] sm:h-[42px] object-contain"
            />
          </button>
        </div>

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
                item.id === 'demo' && currentPage !== 'demo'
                  ? 'ring-1 ring-cyan-500/50 text-cyan-400 hover:bg-cyan-900/30'
                  : ''
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

        <div className="flex-1 sm:hidden"></div>

        <div className="flex items-center gap-2 sm:gap-3 flex-shrink-0">
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

      {showMobileMenu && (
        <>
          <div
            className="fixed inset-0 bg-black/60 z-40 sm:hidden"
            onClick={() => setShowMobileMenu(false)}
          />
          
          <div className="fixed top-16 right-0 bottom-0 w-64 bg-gray-900 border-l border-gray-800 z-50 sm:hidden safe-x safe-bottom">
            <div className="flex flex-col h-full p-4">
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
            </div>
          </div>
        </>
      )}
    </>
  );
}
