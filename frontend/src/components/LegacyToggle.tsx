import { RotateCcw } from 'lucide-react';
import { useAutonomy } from '../contexts/AutonomyContext';

export default function LegacyToggle() {
  const { legacyMode, setLegacyMode } = useAutonomy();

  return (
    <button
      onClick={() => setLegacyMode(!legacyMode)}
      className={`flex items-center gap-2 px-3 py-2 border rounded-lg transition-all ${
        legacyMode
          ? 'bg-cyan-600 border-cyan-500 text-white'
          : 'bg-slate-800 hover:bg-slate-700 border-slate-700 text-slate-300'
      }`}
      title="Switch between Modern (current UI framework) and Legacy (classic layout) to visualize platform evolution or ensure compatibility with older modules."
    >
      <RotateCcw className="w-4 h-4" />
      <div className="text-left">
        <div className="text-xs text-slate-400">UI Mode</div>
        <div className="text-sm font-medium">{legacyMode ? 'Legacy' : 'Modern'}</div>
      </div>
    </button>
  );
}
