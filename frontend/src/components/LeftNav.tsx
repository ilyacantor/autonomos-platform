import { Cable, X, Search, Sparkles, Play, Database } from 'lucide-react';
import autonomosLogo from '../assets/autonomos-logo.png';

interface LeftNavProps {
  isCollapsed: boolean;
  currentPage: string;
  onNavigate: (page: string) => void;
  isMobileMenuOpen?: boolean;
  onCloseMobile?: () => void;
}

interface NavItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  highlight?: boolean;
  tooltip?: string;
}

export default function LeftNav({ isCollapsed, currentPage, onNavigate, isMobileMenuOpen, onCloseMobile }: LeftNavProps) {
  const navItems: NavItem[] = [
    { id: 'aos-overview', label: 'Overview', icon: <Sparkles className="w-5 h-5" />, tooltip: 'Interactive platform overview' },
    { id: 'nlq', label: 'NLQ', icon: <Search className="w-5 h-5" />, tooltip: 'Natural Language Query' },
    { id: 'discover', label: 'AOD', icon: <Search className="w-5 h-5" />, tooltip: 'Asset & Observability Discovery' },
    { id: 'connect', label: 'AAM', icon: <Cable className="w-5 h-5" />, tooltip: 'Adaptive API Mesh' },
    { id: 'unify-ask', label: 'DCL', icon: <Database className="w-5 h-5" />, tooltip: 'Data Connectivity Layer' },
    { id: 'orchestration', label: 'AOA', icon: <Play className="w-5 h-5" />, tooltip: 'Agentic Orchestration Architecture' },
  ];

  return (
    <div
      className={`
        ${isCollapsed ? 'md:w-18' : 'md:w-60'}
        ${isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
        fixed md:relative
        w-64 md:w-auto
        h-full
        z-50
        bg-gray-900 border-r border-gray-800 
        transition-all duration-300 
        flex flex-col
      `}
    >
      {/* Header with Logo and Mobile Close Button */}
      <div className="h-16 flex items-center justify-between border-b border-gray-800 px-3">
        <img 
          src={autonomosLogo} 
          alt="autonomOS" 
          className={`h-[42px] object-contain ${isCollapsed && !isMobileMenuOpen ? 'mx-auto' : '-ml-3'}`}
        />
        {/* Close button - only visible on mobile */}
        <button
          onClick={onCloseMobile}
          className="md:hidden p-2 hover:bg-gray-800 rounded-lg transition-colors text-gray-400"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      <nav className="flex-1 p-3 space-y-1">
        {navItems.map((item) => (
          <button
            key={item.id}
            onClick={() => onNavigate(item.id)}
            title={item.tooltip}
            className={`w-full flex items-center gap-3 px-3 py-3 rounded-lg transition-all min-h-[44px] ${
              currentPage === item.id
                ? 'bg-blue-600 text-white'
                : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200 active:bg-gray-700'
            } ${item.highlight && currentPage !== item.id ? 'ring-1 ring-blue-500/30' : ''}`}
          >
            <span className={isCollapsed && !isMobileMenuOpen ? 'mx-auto' : ''}>{item.icon}</span>
            {(!isCollapsed || isMobileMenuOpen) && <span className="font-medium text-left">{item.label}</span>}
          </button>
        ))}
      </nav>
    </div>
  );
}
