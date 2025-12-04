import { ReactNode } from 'react';
import { ExternalLink } from 'lucide-react';

interface DemoStepProps {
  stepNumber?: string | number;
  title: string;
  description: string;
  children: ReactNode;
  instructions?: string;
  openInNewTabHref?: string;
}

export default function DemoStep({
  stepNumber,
  title,
  description,
  children,
  instructions,
  openInNewTabHref
}: DemoStepProps) {
  return (
    <div className="flex flex-col h-full min-h-0">
      <div className="flex-shrink-0 px-3 sm:px-4 lg:px-6 pt-4 sm:pt-6 pb-3 sm:pb-4">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2 sm:gap-4">
          <div className="flex-1 min-w-0">
            <h1 className="text-xl sm:text-2xl lg:text-3xl font-bold text-white mb-1 sm:mb-2 flex items-center gap-2 sm:gap-3 flex-wrap">
              {stepNumber && (
                <span className="inline-flex items-center justify-center w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-gradient-to-br from-cyan-500 to-purple-600 text-white text-sm sm:text-base font-bold flex-shrink-0">
                  {stepNumber}
                </span>
              )}
              <span className="truncate">{title}</span>
            </h1>
            <p className="text-sm sm:text-base text-gray-300 leading-relaxed line-clamp-2 sm:line-clamp-none">
              {description}
            </p>
          </div>
          
          {openInNewTabHref && (
            <a
              href={openInNewTabHref}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 sm:px-4 sm:py-2 bg-cyan-600/20 hover:bg-cyan-600/30 border border-cyan-500/40 hover:border-cyan-500/60 rounded-lg text-cyan-400 hover:text-cyan-300 text-xs sm:text-sm font-medium transition-all duration-200 flex-shrink-0 self-start"
            >
              <span className="hidden xs:inline">Open</span> Full Screen
              <ExternalLink className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
            </a>
          )}
        </div>
      </div>

      <div className="flex-1 min-h-0 px-3 sm:px-4 lg:px-6 pb-2">
        <div className="h-full bg-gray-800 rounded-lg border border-gray-700/50 overflow-hidden shadow-lg">
          {children}
        </div>
      </div>

      {instructions && (
        <div className="flex-shrink-0 px-3 sm:px-4 lg:px-6 py-2 sm:py-3">
          <div className="flex items-start gap-2 text-xs sm:text-sm text-gray-400 bg-gray-800/50 rounded-lg px-3 py-2 border border-gray-700/30">
            <span className="text-cyan-400 font-medium flex-shrink-0">Try this:</span>
            <span className="text-gray-300">{instructions}</span>
          </div>
        </div>
      )}
    </div>
  );
}
