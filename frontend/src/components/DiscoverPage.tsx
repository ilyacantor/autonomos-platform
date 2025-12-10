import { ExternalLink, Search } from 'lucide-react';

const DISCOVER_URL = 'https://discover.autonomos.software/';

export default function DiscoverPage() {
  return (
    <div className="h-full flex flex-col items-center justify-center p-8">
      <div className="max-w-2xl text-center space-y-6">
        <div className="flex justify-center">
          <div className="p-4 bg-blue-500/20 rounded-full">
            <Search className="w-12 h-12 text-blue-400" />
          </div>
        </div>
        
        <h1 className="text-3xl font-bold text-white">
          Asset & Observability Discovery (AOD)
        </h1>
        
        <p className="text-gray-400 text-lg">
          Discover, catalog, and score everything running in your environment. 
          AOD builds the Asset Graph, flags shadow IT, risky assets, and anomalies.
        </p>
        
        <div className="pt-4">
          <a
            href={DISCOVER_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
          >
            Open Discovery Dashboard
            <ExternalLink className="w-5 h-5" />
          </a>
        </div>
        
        <p className="text-gray-500 text-sm">
          Opens in a new tab for the full discovery experience.
        </p>
      </div>
    </div>
  );
}
