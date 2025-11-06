import { LayoutDashboard, GitBranch, Cable, Network, X, Activity, Search, HelpCircle } from 'lucide-react';
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
    { id: 'control-center', label: 'Control Center', icon: <LayoutDashboard className="w-5 h-5" /> },
    { id: 'discover', label: 'Discover', icon: <Search className="w-5 h-5" /> },
    { id: 'connect', label: 'Connect', icon: <Cable className="w-5 h-5" />, highlight: true, tooltip: 'AAM Connect - Self-healing data connectivity' },
    { id: 'ontology', label: 'Ontology', icon: <Network className="w-5 h-5" /> },
    { id: 'orchestration', label: 'Orchestrate', icon: <Activity className="w-5 h-5" /> },
    { id: 'faq', label: 'FAQ', icon: <HelpCircle className="w-5 h-5" /> },
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
