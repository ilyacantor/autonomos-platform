import { CheckCircle, Clock, XCircle, Wrench, ChevronRight } from 'lucide-react';

export interface RepairStatus {
  auto_applied_count: number;
  hitl_queued_count: number;
  rejected_count: number;
  last_repair_at: string | null;
}

interface RepairStatusCardProps {
  status: RepairStatus;
  onViewHistory?: () => void;
}

export default function RepairStatusCard({ status, onViewHistory }: RepairStatusCardProps) {
  const {
    auto_applied_count,
    hitl_queued_count,
    rejected_count,
    last_repair_at
  } = status;
  
  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'Never';
    try {
      const date = new Date(dateStr);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      
      if (diffMins < 1) return 'Just now';
      if (diffMins < 60) return `${diffMins}m ago`;
      if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
      return date.toLocaleDateString();
    } catch {
      return 'Recently';
    }
  };
  
  const totalRepairs = auto_applied_count + hitl_queued_count + rejected_count;
  
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Wrench className="w-5 h-5 text-blue-400" />
          <h3 className="text-sm font-medium text-gray-400">Repair Activity</h3>
        </div>
        
        {last_repair_at && (
          <span className="text-xs text-gray-500">
            Last: {formatDate(last_repair_at)}
          </span>
        )}
      </div>
      
      {totalRepairs === 0 ? (
        <div className="text-center py-8">
          <Wrench className="w-12 h-12 text-gray-600 mx-auto mb-3 opacity-50" />
          <p className="text-gray-500 text-sm">No repairs processed yet</p>
        </div>
      ) : (
        <div className="space-y-3">
          {auto_applied_count > 0 && (
            <div className="flex items-center justify-between p-3 bg-green-900/20 border border-green-500/30 rounded-lg">
              <div className="flex items-center gap-3">
                <CheckCircle className="w-5 h-5 text-green-400 flex-shrink-0" />
                <div>
                  <p className="text-sm font-medium text-green-400">Auto-applied</p>
                  <p className="text-xs text-gray-400">High confidence repairs</p>
                </div>
              </div>
              <span className="text-2xl font-bold text-green-400">
                {auto_applied_count}
              </span>
            </div>
          )}
          
          {hitl_queued_count > 0 && (
            <div className="flex items-center justify-between p-3 bg-yellow-900/20 border border-yellow-500/30 rounded-lg">
              <div className="flex items-center gap-3">
                <Clock className="w-5 h-5 text-yellow-400 flex-shrink-0" />
                <div>
                  <p className="text-sm font-medium text-yellow-400">Pending review</p>
                  <p className="text-xs text-gray-400">Requires human approval</p>
                </div>
              </div>
              <span className="text-2xl font-bold text-yellow-400">
                {hitl_queued_count}
              </span>
            </div>
          )}
          
          {rejected_count > 0 && (
            <div className="flex items-center justify-between p-3 bg-red-900/20 border border-red-500/30 rounded-lg">
              <div className="flex items-center gap-3">
                <XCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
                <div>
                  <p className="text-sm font-medium text-red-400">Rejected</p>
                  <p className="text-xs text-gray-400">Low confidence</p>
                </div>
              </div>
              <span className="text-2xl font-bold text-red-400">
                {rejected_count}
              </span>
            </div>
          )}
        </div>
      )}
      
      {onViewHistory && totalRepairs > 0 && (
        <button
          onClick={onViewHistory}
          className="mt-4 w-full flex items-center justify-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg text-sm text-gray-300 transition-colors"
        >
          View Repair History
          <ChevronRight className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}
