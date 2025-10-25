import { useState } from 'react';
import { Play, ChevronDown } from 'lucide-react';

export default function RunAllDropdown() {
  const [showDropdown, setShowDropdown] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  const handleRunAll = async (devMode: boolean) => {
    setShowDropdown(false);
    setIsProcessing(true);
    
    try {
      const allSources = 'dynamics,salesforce,supabase,mongodb,hubspot,snowflake,sap,netsuite,legacy_sql';
      const allAgents = 'finops_pilot,revops_pilot';
      const response = await fetch(`/connect?sources=${allSources}&agents=${allAgents}&dev_mode=${devMode}`);
      await response.json();
    } catch (error) {
      console.error('Error running all:', error);
    } finally {
      setTimeout(() => setIsProcessing(false), 1500);
    }
  };

  return (
    <div className="relative">
      <button
        onClick={() => setShowDropdown(!showDropdown)}
        disabled={isProcessing}
        className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 rounded-lg text-sm font-medium text-white shadow-lg shadow-emerald-500/30 transition-all disabled:opacity-50"
      >
        {isProcessing ? (
          <>
            <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Processing...
          </>
        ) : (
          <>
            <Play className="w-4 h-4" />
            Run All
            <ChevronDown className="w-4 h-4" />
          </>
        )}
      </button>
      
      {showDropdown && !isProcessing && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setShowDropdown(false)}
          />
          <div className="absolute right-0 mt-2 w-64 bg-gray-800 border border-gray-700 rounded-lg shadow-xl z-20">
            <button
              onClick={() => handleRunAll(false)}
              className="w-full px-4 py-3 text-left hover:bg-gray-700 transition-colors rounded-t-lg"
            >
              <div className="text-sm font-medium text-white">Run All in Production Mode</div>
              <div className="text-xs text-gray-400 mt-1">Uses AI/RAG for intelligent mapping</div>
            </button>
            <button
              onClick={() => handleRunAll(true)}
              className="w-full px-4 py-3 text-left hover:bg-gray-700 transition-colors rounded-b-lg border-t border-gray-700"
            >
              <div className="text-sm font-medium text-white">Run All in Heuristic Mode</div>
              <div className="text-xs text-gray-400 mt-1">Uses heuristic-only mapping</div>
            </button>
          </div>
        </>
      )}
    </div>
  );
}
