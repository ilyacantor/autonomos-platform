import { useState } from 'react';
import { AlertCircle } from 'lucide-react';

interface EmbeddedAppProps {
  url: string;
  title: string;
  className?: string;
}

export default function EmbeddedApp({ url, title, className = '' }: EmbeddedAppProps) {
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [iframeKey, setIframeKey] = useState(0);

  const handleLoad = () => {
    setIsLoading(false);
    setHasError(false);
  };

  const handleError = () => {
    setIsLoading(false);
    setHasError(true);
  };

  const handleRetry = () => {
    setIsLoading(true);
    setHasError(false);
    setIframeKey(prev => prev + 1);
  };

  return (
    <div className={`relative w-full h-full ${className}`}>
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-900/50 z-10">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-500 mx-auto mb-4"></div>
            <p className="text-gray-400 text-sm">Loading {title}...</p>
          </div>
        </div>
      )}

      {hasError && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-900/80 z-10">
          <div className="text-center max-w-md px-4">
            <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">Failed to Load</h3>
            <p className="text-gray-400 mb-4">
              Unable to load {title}. Please check your connection and try again.
            </p>
            <button
              onClick={handleRetry}
              className="px-4 py-2 bg-cyan-600 hover:bg-cyan-700 text-white rounded-lg transition-colors"
            >
              Retry
            </button>
          </div>
        </div>
      )}

      <iframe
        key={iframeKey}
        src={url}
        title={title}
        className="w-full h-full border-0 rounded-lg"
        sandbox="allow-scripts allow-forms allow-popups"
        onLoad={handleLoad}
        onError={handleError}
        loading="lazy"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
      />
    </div>
  );
}
