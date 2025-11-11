import { type LiveStatus } from '../config/liveStatus';

interface LiveStatusBadgeProps {
  status: LiveStatus;
  tooltip?: string;
  className?: string;
}

export default function LiveStatusBadge({ status, tooltip, className = '' }: LiveStatusBadgeProps) {
  if (status === 'live') {
    return (
      <div 
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-green-500/10 border border-green-500/30 ${className}`}
        title={tooltip || 'Live data from backend services'}
        role="status"
        aria-label="Live data indicator"
      >
        <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" aria-hidden="true" />
        <span className="text-xs font-medium text-green-400">Live</span>
      </div>
    );
  }

  return null;
}
