/**
 * Autonomy Mode Toggle Component
 *
 * Global control for selecting the autonomy level of the orchestration system.
 * Persists the mode to the backend via API.
 */

import { useState, useEffect, useCallback } from 'react';
import { Settings, ChevronDown, AlertCircle, Check } from 'lucide-react';
import type { AutonomyMode } from './types';
import { fetchAutonomyMode, updateAutonomyMode } from './api';

const MODES: { mode: AutonomyMode; description: string }[] = [
  { mode: 'Observe', description: 'Monitor only, no agent actions' },
  { mode: 'Recommend', description: 'Suggest actions for review' },
  { mode: 'Approve-to-Act', description: 'Require approval before execution' },
  { mode: 'Auto (Guardrails)', description: 'Autonomous with safety limits' },
  { mode: 'Federated (xAO)', description: 'Cross-enterprise orchestration' },
];

interface AutonomyModeToggleProps {
  className?: string;
}

export default function AutonomyModeToggle({ className = '' }: AutonomyModeToggleProps) {
  const [currentMode, setCurrentMode] = useState<AutonomyMode>('Auto (Guardrails)');
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadMode = useCallback(async () => {
    try {
      const response = await fetchAutonomyMode();
      setCurrentMode(response.mode);
      setError(null);
    } catch (err: any) {
      // Keep default mode on error
      console.error('Failed to fetch autonomy mode:', err);
    }
  }, []);

  useEffect(() => {
    loadMode();
  }, [loadMode]);

  const handleModeSelect = async (mode: AutonomyMode) => {
    if (mode === currentMode) {
      setIsOpen(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await updateAutonomyMode(mode);
      setCurrentMode(mode);
      setIsOpen(false);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getModeColor = (mode: AutonomyMode) => {
    switch (mode) {
      case 'Observe':
        return 'text-gray-400';
      case 'Recommend':
        return 'text-blue-400';
      case 'Approve-to-Act':
        return 'text-yellow-400';
      case 'Auto (Guardrails)':
        return 'text-green-400';
      case 'Federated (xAO)':
        return 'text-purple-400';
      default:
        return 'text-cyan-400';
    }
  };

  return (
    <div className={`relative ${className}`}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={loading}
        className="flex items-center gap-2 px-3 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition-colors disabled:opacity-50"
        title="Autonomy Mode controls how AutonomOS manages itself. 'Auto (Guardrails)' allows self-directed agent decisions within preset boundaries."
      >
        <Settings className={`w-4 h-4 ${loading ? 'animate-spin' : ''} text-cyan-400`} />
        <div className="text-left">
          <div className="text-xs text-slate-500">Autonomy Mode</div>
          <div className={`text-sm font-medium ${getModeColor(currentMode)}`}>
            {currentMode}
          </div>
        </div>
        <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />

          {/* Dropdown */}
          <div className="absolute right-0 mt-2 w-72 bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-20">
            <div className="p-2">
              <div className="px-3 py-2 text-xs font-semibold text-slate-500 uppercase tracking-wider border-b border-slate-700 mb-2">
                Select Autonomy Mode
              </div>

              {error && (
                <div className="mx-2 mb-2 p-2 bg-red-500/20 border border-red-500/30 rounded text-sm text-red-400 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              {MODES.map(({ mode, description }) => (
                <button
                  key={mode}
                  onClick={() => handleModeSelect(mode)}
                  disabled={loading}
                  className={`w-full text-left px-3 py-2 rounded-md transition-colors flex items-center justify-between ${
                    currentMode === mode
                      ? 'bg-cyan-600 text-white'
                      : 'text-slate-300 hover:bg-slate-700'
                  } disabled:opacity-50`}
                >
                  <div>
                    <div className="font-medium">{mode}</div>
                    <div className={`text-xs mt-0.5 ${currentMode === mode ? 'text-cyan-100' : 'text-slate-400'}`}>
                      {description}
                    </div>
                  </div>
                  {currentMode === mode && (
                    <Check className="w-4 h-4 flex-shrink-0" />
                  )}
                </button>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
