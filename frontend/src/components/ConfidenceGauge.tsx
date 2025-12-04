import { Target, AlertTriangle, CheckCircle } from 'lucide-react';

interface ConfidenceGaugeProps {
  confidence: number;
  label: string;
  size?: 'small' | 'medium' | 'large';
  showLabel?: boolean;
}

export default function ConfidenceGauge({ 
  confidence, 
  label, 
  size = 'medium',
  showLabel = true 
}: ConfidenceGaugeProps) {
  const percentage = Math.round(confidence * 100);
  
  const getConfidenceLevel = () => {
    if (confidence >= 0.85) return 'high';
    if (confidence >= 0.60) return 'medium';
    return 'low';
  };
  
  const level = getConfidenceLevel();
  
  const sizes = {
    small: { gauge: 40, stroke: 4, text: 'text-xs', icon: 'w-3 h-3' },
    medium: { gauge: 60, stroke: 6, text: 'text-sm', icon: 'w-4 h-4' },
    large: { gauge: 80, stroke: 8, text: 'text-lg', icon: 'w-5 h-5' }
  };
  
  const config = sizes[size];
  const radius = (config.gauge - config.stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percentage / 100) * circumference;
  
  const colors = {
    high: {
      bg: 'bg-green-900/30',
      border: 'border-green-500/30',
      text: 'text-green-400',
      stroke: 'stroke-green-500',
      icon: CheckCircle
    },
    medium: {
      bg: 'bg-yellow-900/30',
      border: 'border-yellow-500/30',
      text: 'text-yellow-400',
      stroke: 'stroke-yellow-500',
      icon: Target
    },
    low: {
      bg: 'bg-red-900/30',
      border: 'border-red-500/30',
      text: 'text-red-400',
      stroke: 'stroke-red-500',
      icon: AlertTriangle
    }
  };
  
  const style = colors[level];
  const Icon = style.icon;
  
  return (
    <div className="flex items-center gap-2">
      <div className="relative" style={{ width: config.gauge, height: config.gauge }}>
        <svg className="transform -rotate-90" width={config.gauge} height={config.gauge}>
          <circle
            cx={config.gauge / 2}
            cy={config.gauge / 2}
            r={radius}
            className="stroke-gray-700"
            strokeWidth={config.stroke}
            fill="none"
          />
          <circle
            cx={config.gauge / 2}
            cy={config.gauge / 2}
            r={radius}
            className={style.stroke}
            strokeWidth={config.stroke}
            fill="none"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={`${config.text} font-bold ${style.text}`}>
            {percentage}%
          </span>
        </div>
      </div>
      
      {showLabel && (
        <div className="flex flex-col">
          <span className="text-xs text-gray-400">{label}</span>
          {level === 'medium' && (
            <span className="text-xs text-yellow-400">Review suggested</span>
          )}
          {level === 'low' && (
            <div className="flex items-center gap-1 text-xs text-red-400">
              <AlertTriangle className="w-3 h-3" />
              <span>Low confidence</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
