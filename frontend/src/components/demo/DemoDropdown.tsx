import { useState, useRef, useEffect } from 'react';
import { Play, ChevronDown, X } from 'lucide-react';
import { useDemo } from '../../contexts/DemoContext';
import { AVAILABLE_DEMOS } from './demos';

// ── DemoDropdown: TopBar trigger for guided demos ────────────────────

export default function DemoDropdown() {
  const { status, activeDemo, currentStepIndex, startDemo, exitDemo } = useDemo();
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  const isRunning = status === 'running';
  const totalSteps = activeDemo?.steps.length ?? 0;

  return (
    <div ref={containerRef} className="relative">
      {/* Trigger button */}
      <button
        onClick={() => setOpen(!open)}
        className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
          isRunning
            ? 'bg-blue-600/20 text-blue-400 border border-blue-500/40'
            : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
        }`}
      >
        {isRunning ? (
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500" />
          </span>
        ) : (
          <Play className="w-4 h-4" />
        )}
        <span>Demos</span>
        <ChevronDown className={`w-3 h-3 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown panel */}
      {open && (
        <div className="absolute right-0 top-full mt-2 w-80 bg-gray-900 border border-gray-700 rounded-xl shadow-xl shadow-black/40 overflow-hidden z-50">
          {isRunning && activeDemo ? (
            // ── Running state ─────────────────────────────────
            <div className="p-4">
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-white font-semibold text-sm">{activeDemo.name}</h4>
                <span className="text-xs text-blue-400 font-medium">
                  Step {currentStepIndex + 1} / {totalSteps}
                </span>
              </div>

              {/* Progress bar */}
              <div className="w-full bg-gray-700 rounded-full h-1.5 mb-3">
                <div
                  className="bg-blue-500 h-1.5 rounded-full transition-all duration-300"
                  style={{ width: `${((currentStepIndex + 1) / totalSteps) * 100}%` }}
                />
              </div>

              <p className="text-gray-400 text-xs mb-3">
                {activeDemo.steps[currentStepIndex]?.title}
              </p>

              <button
                onClick={() => {
                  exitDemo();
                  setOpen(false);
                }}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-red-400 hover:text-red-300 hover:bg-red-950/30 border border-red-800/30 rounded-lg transition-colors w-full justify-center"
              >
                <X className="w-3 h-3" />
                Exit Demo
              </button>
            </div>
          ) : (
            // ── Idle state — list available demos ─────────────
            <div>
              <div className="px-4 pt-3 pb-2 border-b border-gray-800">
                <h4 className="text-gray-300 text-xs font-semibold uppercase tracking-wider">
                  Guided Demos
                </h4>
              </div>

              {AVAILABLE_DEMOS.map((demo) => (
                <div key={demo.id} className="p-4 hover:bg-gray-800/50 transition-colors">
                  <div className="flex items-start gap-3">
                    <span className="text-xl">{demo.icon}</span>
                    <div className="flex-1 min-w-0">
                      <h5 className="text-white font-medium text-sm">{demo.name}</h5>
                      <p className="text-gray-400 text-xs mt-0.5 leading-relaxed">
                        {demo.description}
                      </p>
                      <button
                        onClick={() => {
                          startDemo(demo);
                          setOpen(false);
                        }}
                        className="mt-2 flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors"
                      >
                        <Play className="w-3 h-3" />
                        Start Demo
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
