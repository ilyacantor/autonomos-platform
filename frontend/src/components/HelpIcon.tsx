import { HelpCircle } from 'lucide-react';
import { useState } from 'react';

interface HelpIconProps {
  faqId: string;
  tooltip?: string;
  size?: 'sm' | 'md' | 'lg';
}

export default function HelpIcon({ faqId, tooltip, size = 'sm' }: HelpIconProps) {
  const [showTooltip, setShowTooltip] = useState(false);

  const sizeClasses = {
    sm: 'w-3.5 h-3.5',
    md: 'w-4 h-4',
    lg: 'w-5 h-5'
  };

  const handleClick = () => {
    // Navigate to FAQ with hash
    window.dispatchEvent(new CustomEvent('navigate', { detail: { page: 'faq' } }));
    setTimeout(() => {
      window.location.hash = faqId;
    }, 100);
  };

  return (
    <div className="relative inline-block">
      <button
        onClick={handleClick}
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        className="text-cyan-400/60 hover:text-cyan-400 transition-colors cursor-help inline-flex items-center justify-center"
        aria-label="Help"
      >
        <HelpCircle className={sizeClasses[size]} />
      </button>
      
      {tooltip && showTooltip && (
        <div className="absolute z-50 bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg shadow-lg whitespace-nowrap border border-gray-700">
          {tooltip}
          <div className="absolute top-full left-1/2 transform -translate-x-1/2 -mt-1">
            <div className="border-4 border-transparent border-t-gray-900"></div>
          </div>
        </div>
      )}
    </div>
  );
}
