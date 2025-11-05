import { useState } from 'react';
import { AlertTriangle, ChevronDown, ChevronRight, X } from 'lucide-react';

export interface DriftAlert {
  source_id: string;
  connector_type: string;
  drift_severity: 'low' | 'medium' | 'high';
  fields_changed: string[];
  detected_at: string | null;
}

interface DriftAlertBannerProps {
  alerts: DriftAlert[];
  onDismiss?: () => void;
  onReview?: (alert: DriftAlert) => void;
}

export default function DriftAlertBanner({ alerts, onDismiss, onReview }: DriftAlertBannerProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  
  if (!alerts || alerts.length === 0) return null;
  
  const severityCounts = {
    high: alerts.filter(a => a.drift_severity === 'high').length,
    medium: alerts.filter(a => a.drift_severity === 'medium').length,
    low: alerts.filter(a => a.drift_severity === 'low').length
  };
  
  const highestSeverity = severityCounts.high > 0 ? 'high' : 
                          severityCounts.medium > 0 ? 'medium' : 'low';
  
  const severityStyles = {
    high: {
      bg: 'bg-red-900/20',
      border: 'border-red-500/50',
      text: 'text-red-400',
      icon: 'text-red-500'
    },
    medium: {
      bg: 'bg-orange-900/20',
      border: 'border-orange-500/50',
      text: 'text-orange-400',
      icon: 'text-orange-500'
    },
    low: {
      bg: 'bg-yellow-900/20',
      border: 'border-yellow-500/50',
      text: 'text-yellow-400',
      icon: 'text-yellow-500'
    }
  };
  
  const style = severityStyles[highestSeverity];
  
  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'Recently';
    try {
      return new Date(dateStr).toLocaleString();
    } catch {
      return 'Recently';
    }
  };
  
  return (
    <div className={`${style.bg} border ${style.border} rounded-lg overflow-hidden`}>
      <div className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3 flex-1">
            <AlertTriangle className={`w-6 h-6 ${style.icon} flex-shrink-0`} />
            <div className="flex-1">
              <h3 className={`font-medium ${style.text}`}>
                Schema drift detected in {alerts.length} {alerts.length === 1 ? 'source' : 'sources'}
              </h3>
              <p className="text-sm text-gray-400 mt-1">
                {severityCounts.high > 0 && `${severityCounts.high} high severity, `}
                {severityCounts.medium > 0 && `${severityCounts.medium} medium severity, `}
                {severityCounts.low > 0 && `${severityCounts.low} low severity`}
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 border border-gray-600 rounded-lg text-sm text-gray-300 transition-colors flex items-center gap-1"
            >
              {isExpanded ? (
                <>
                  <ChevronDown className="w-4 h-4" />
                  Hide Details
                </>
              ) : (
                <>
                  <ChevronRight className="w-4 h-4" />
                  View Details
                </>
              )}
            </button>
            
            {onDismiss && (
              <button
                onClick={onDismiss}
                className="p-1.5 hover:bg-gray-700 rounded transition-colors"
                aria-label="Dismiss alert"
              >
                <X className="w-4 h-4 text-gray-400" />
              </button>
            )}
          </div>
        </div>
      </div>
      
      {isExpanded && (
        <div className="border-t border-gray-700 bg-gray-900/30 p-4">
          <div className="space-y-3">
            {alerts.map((alert, index) => {
              const alertStyle = severityStyles[alert.drift_severity];
              
              return (
                <div
                  key={index}
                  className="bg-gray-800/50 border border-gray-700 rounded-lg p-3"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${alertStyle.bg} border ${alertStyle.border} ${alertStyle.text}`}>
                          {alert.drift_severity.toUpperCase()}
                        </span>
                        <span className="font-medium text-white">{alert.source_id}</span>
                        <span className="text-xs text-gray-500">{alert.connector_type}</span>
                      </div>
                      
                      <div className="mt-2">
                        <p className="text-sm text-gray-400 mb-1">
                          {alert.fields_changed.length} {alert.fields_changed.length === 1 ? 'field' : 'fields'} changed:
                        </p>
                        <div className="flex flex-wrap gap-1">
                          {alert.fields_changed.map((field, fieldIdx) => (
                            <code
                              key={fieldIdx}
                              className="px-2 py-0.5 bg-gray-900 border border-gray-600 rounded text-xs text-gray-300"
                            >
                              {field}
                            </code>
                          ))}
                        </div>
                      </div>
                      
                      <p className="text-xs text-gray-500 mt-2">
                        Detected: {formatDate(alert.detected_at)}
                      </p>
                    </div>
                    
                    {onReview && (
                      <button
                        onClick={() => onReview(alert)}
                        className="ml-3 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm transition-colors flex-shrink-0"
                      >
                        Review Changes
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
