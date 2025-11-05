import { TrendingUp, TrendingDown, Minus, Database, AlertTriangle } from 'lucide-react';

export interface DataQualityScoreProps {
  score: number;
  sources_with_drift: string[];
  low_confidence_sources: string[];
  total_sources?: number;
}

export default function DataQualityScore({
  score,
  sources_with_drift,
  low_confidence_sources,
  total_sources = 0
}: DataQualityScoreProps) {
  const percentage = Math.round(score * 100);
  
  const getScoreLevel = () => {
    if (score >= 0.8) return 'high';
    if (score >= 0.6) return 'medium';
    return 'low';
  };
  
  const level = getScoreLevel();
  
  const colors = {
    high: {
      bg: 'bg-green-900/30',
      border: 'border-green-500/50',
      text: 'text-green-400',
      scoreText: 'text-green-500',
      ring: 'ring-green-500/20'
    },
    medium: {
      bg: 'bg-yellow-900/30',
      border: 'border-yellow-500/50',
      text: 'text-yellow-400',
      scoreText: 'text-yellow-500',
      ring: 'ring-yellow-500/20'
    },
    low: {
      bg: 'bg-red-900/30',
      border: 'border-red-500/50',
      text: 'text-red-400',
      scoreText: 'text-red-500',
      ring: 'ring-red-500/20'
    }
  };
  
  const style = colors[level];
  
  const healthySourcesCount = total_sources - sources_with_drift.length - low_confidence_sources.length;
  
  const getTrendIcon = () => {
    if (score >= 0.85) return <TrendingUp className="w-5 h-5 text-green-400" />;
    if (score >= 0.7) return <Minus className="w-5 h-5 text-gray-400" />;
    return <TrendingDown className="w-5 h-5 text-red-400" />;
  };
  
  return (
    <div className={`${style.bg} border ${style.border} rounded-xl p-6 ring-4 ${style.ring}`}>
      <div className="flex items-start justify-between mb-6">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <Database className={`w-5 h-5 ${style.text}`} />
            <h2 className="text-sm font-medium text-gray-400">Overall Data Quality</h2>
          </div>
          <div className="flex items-baseline gap-3">
            <span className={`text-5xl font-bold ${style.scoreText}`}>
              {percentage}
            </span>
            <span className="text-2xl text-gray-500">/100</span>
            {getTrendIcon()}
          </div>
        </div>
      </div>
      
      <div className="grid grid-cols-3 gap-4">
        <div className="text-center">
          <div className="text-2xl font-bold text-white mb-1">
            {healthySourcesCount >= 0 ? healthySourcesCount : 0}
          </div>
          <div className="text-xs text-gray-400">Healthy sources</div>
        </div>
        
        <div className="text-center border-x border-gray-700">
          <div className="text-2xl font-bold text-orange-400 mb-1">
            {sources_with_drift.length}
          </div>
          <div className="text-xs text-gray-400">With drift</div>
        </div>
        
        <div className="text-center">
          <div className="text-2xl font-bold text-yellow-400 mb-1">
            {low_confidence_sources.length}
          </div>
          <div className="text-xs text-gray-400">Low confidence</div>
        </div>
      </div>
      
      {(sources_with_drift.length > 0 || low_confidence_sources.length > 0) && (
        <div className="mt-4 pt-4 border-t border-gray-700">
          <div className="space-y-2">
            {sources_with_drift.length > 0 && (
              <div className="flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-orange-400 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="text-xs text-gray-400">
                    Schema drift in: <span className="text-orange-400">{sources_with_drift.join(', ')}</span>
                  </p>
                </div>
              </div>
            )}
            
            {low_confidence_sources.length > 0 && (
              <div className="flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-yellow-400 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="text-xs text-gray-400">
                    Low confidence: <span className="text-yellow-400">{low_confidence_sources.join(', ')}</span>
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
