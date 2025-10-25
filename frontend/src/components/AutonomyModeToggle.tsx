import { useState } from 'react';
import { Settings, ChevronDown } from 'lucide-react';
import { useAutonomy } from '../contexts/AutonomyContext';
import type { AutonomyMode } from '../types';

export default function AutonomyModeToggle() {
  const { autonomyMode, setAutonomyMode } = useAutonomy();
  const [isOpen, setIsOpen] = useState(false);

  const modes: AutonomyMode[] = [
    'Observe',
    'Recommend',
    'Approve-to-Act',
    'Auto (Guardrails)',
    'Federated (xAO)',
  ];

  const handleModeSelect = (mode: AutonomyMode) => {
    setAutonomyMode(mode);
    setIsOpen(false);
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 h-10 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition-colors"
        title="Autonomy Mode controls how AutonomOS manages itself. 'Auto (Guardrails)' allows self-directed agent decisions within preset boundaries, while 'Manual' requires human confirmation for major actions."
      >
        <Settings className="w-4 h-4 text-cyan-400 flex-shrink-0" />
        <div className="text-left min-w-0">
          <div className="text-xs text-slate-500">Autonomy Mode</div>
          <div className="text-sm font-medium text-slate-200 truncate">{autonomyMode}</div>
        </div>
        <ChevronDown className="w-4 h-4 text-slate-400 flex-shrink-0" />
      </button>

      {isOpen && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />
          <div className="absolute right-0 mt-2 w-64 bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-50">
            <div className="p-2">
              <div className="px-3 py-2 text-xs font-semibold text-slate-500 uppercase tracking-wider border-b border-slate-700 mb-2">
                Select Autonomy Mode
              </div>
              {modes.map((mode) => (
                <button
                  key={mode}
                  onClick={() => handleModeSelect(mode)}
                  className={`w-full text-left px-3 py-2 rounded-md transition-colors ${
                    autonomyMode === mode
                      ? 'bg-cyan-600 text-white'
                      : 'text-slate-300 hover:bg-slate-700'
                  }`}
                >
                  <div className="font-medium">{mode}</div>
                  <div className="text-xs text-slate-400 mt-0.5">
                    {mode === 'Observe' && 'Monitor only, no actions'}
                    {mode === 'Recommend' && 'Suggest actions for review'}
                    {mode === 'Approve-to-Act' && 'Require approval before execution'}
                    {mode === 'Auto (Guardrails)' && 'Autonomous with safety limits'}
                    {mode === 'Federated (xAO)' && 'Cross-enterprise orchestration'}
                  </div>
                </button>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
