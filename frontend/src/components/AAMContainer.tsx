import { Network } from 'lucide-react';

export default function AAMContainer() {
  return (
    <div className="bg-gradient-to-br from-slate-900/80 to-slate-800/40 backdrop-blur-sm rounded-xl border border-slate-700/50 p-6 shadow-xl">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-purple-500/10 rounded-lg border border-purple-500/20">
            <Network className="w-5 h-5 text-purple-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">Adaptive API Mesh</h2>
            <p className="text-sm text-gray-400">
              Dynamic API orchestration and intelligent routing layer
            </p>
          </div>
        </div>
      </div>

      <div className="bg-slate-800/40 rounded-lg border-2 border-dashed border-slate-700 p-12 text-center min-h-[200px] flex items-center justify-center">
        <div className="text-slate-400">
          <Network className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p className="text-sm font-medium">AAM visualization will appear here</p>
        </div>
      </div>
    </div>
  );
}
