import { useRef, useCallback, useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ChevronLeft, ChevronRight, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react';
import { useDemo } from '../../contexts/DemoContext';

// ── Draggable modal for guided demo steps ────────────────────────────

export default function DemoModal() {
  const {
    status,
    activeDemo,
    currentStepIndex,
    isApiLoading,
    apiError,
    nextStep,
    prevStep,
    goToStep,
    exitDemo,
    setApiError,
  } = useDemo();

  // ── Drag state ───────────────────────────────────────────────────
  const modalRef = useRef<HTMLDivElement>(null);
  const dragState = useRef({ dragging: false, startX: 0, startY: 0, offsetX: 0, offsetY: 0 });
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [hasCustomPosition, setHasCustomPosition] = useState(false);

  // Reset position when demo starts
  useEffect(() => {
    if (status === 'running') {
      setPosition({ x: 0, y: 0 });
      setHasCustomPosition(false);
    }
  }, [status]);

  const onPointerDown = useCallback((e: React.PointerEvent) => {
    dragState.current = {
      dragging: true,
      startX: e.clientX - position.x,
      startY: e.clientY - position.y,
      offsetX: position.x,
      offsetY: position.y,
    };
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
  }, [position]);

  const onPointerMove = useCallback((e: React.PointerEvent) => {
    if (!dragState.current.dragging) return;
    const newX = e.clientX - dragState.current.startX;
    const newY = e.clientY - dragState.current.startY;
    setPosition({ x: newX, y: newY });
    setHasCustomPosition(true);
  }, []);

  const onPointerUp = useCallback(() => {
    dragState.current.dragging = false;
  }, []);

  // ── Bail early if not running ────────────────────────────────────
  if (status !== 'running' || !activeDemo) return null;

  const step = activeDemo.steps[currentStepIndex];
  const totalSteps = activeDemo.steps.length;
  const isFirst = currentStepIndex === 0;
  const isLast = currentStepIndex === totalSteps - 1;
  const nextDisabled = isApiLoading && step.blocksOnApi;

  // Phase color mapping
  const phaseColors: Record<string, string> = {
    'AOD Discovery': 'bg-emerald-600',
    'Triage & Handoff': 'bg-amber-600',
    'AAM Connection': 'bg-blue-600',
    'DCL Unification': 'bg-purple-600',
    'NLQ': 'bg-cyan-600',
    'Complete': 'bg-green-600',
  };

  return (
    <>
      {/* Backdrop — semi-transparent, does NOT block iframe clicks */}
      <div className="fixed inset-0 bg-black/30 z-[60] pointer-events-none" />

      {/* Modal */}
      <div
        ref={modalRef}
        className="fixed z-[61] pointer-events-auto"
        style={{
          bottom: hasCustomPosition ? 'auto' : '24px',
          right: hasCustomPosition ? 'auto' : '24px',
          top: hasCustomPosition ? `${position.y}px` : undefined,
          left: hasCustomPosition ? `${position.x}px` : undefined,
          transform: hasCustomPosition ? undefined : `translate(${position.x}px, ${position.y}px)`,
        }}
      >
        <div className="w-[440px] max-w-[calc(100vw-32px)] bg-gray-900/95 backdrop-blur-md border border-gray-700 rounded-xl shadow-2xl shadow-black/50 flex flex-col overflow-hidden">

          {/* ── Header (draggable) ──────────────────────────────── */}
          <div
            className="flex items-center justify-between px-4 py-3 border-b border-gray-700/50 cursor-grab active:cursor-grabbing select-none"
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
          >
            <div className="flex items-center gap-2 min-w-0">
              <span className={`text-[11px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded ${phaseColors[step.phase] || 'bg-gray-600'} text-white`}>
                {step.phase}
              </span>
              <span className="text-gray-500 text-xs font-medium">
                {currentStepIndex + 1} of {totalSteps}
              </span>
            </div>
            <button
              onClick={exitDemo}
              className="p-1 hover:bg-gray-700 rounded transition-colors text-gray-400 hover:text-white"
              title="Exit demo"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* ── Body ────────────────────────────────────────────── */}
          <div className="px-5 py-4 min-h-[120px]">
            <AnimatePresence mode="wait">
              <motion.div
                key={step.id}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.2 }}
              >
                <h3 className="text-white font-semibold text-base mb-2">{step.title}</h3>
                <p className="text-gray-300 text-sm leading-relaxed">{step.body}</p>

                {/* Loading indicator */}
                {isApiLoading && step.blocksOnApi && (
                  <div className="flex items-center gap-2 mt-3 text-blue-400 text-sm">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Pipeline running...</span>
                  </div>
                )}

                {/* Error banner */}
                {apiError && (
                  <div className="flex items-start gap-2 mt-3 p-2 bg-red-950/50 border border-red-800/50 rounded-lg">
                    <AlertCircle className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
                    <div className="flex-1">
                      <p className="text-red-300 text-sm">{apiError}</p>
                      <button
                        onClick={() => setApiError(null)}
                        className="text-red-400 hover:text-red-300 text-xs mt-1 underline"
                      >
                        Dismiss
                      </button>
                    </div>
                  </div>
                )}
              </motion.div>
            </AnimatePresence>
          </div>

          {/* ── Footer ──────────────────────────────────────────── */}
          <div className="px-5 py-3 border-t border-gray-700/50 flex items-center justify-between">
            {/* Progress dots */}
            <div className="flex items-center gap-1">
              {activeDemo.steps.map((s, i) => (
                <button
                  key={s.id}
                  onClick={() => i <= currentStepIndex && goToStep(i)}
                  disabled={i > currentStepIndex}
                  className={`w-2 h-2 rounded-full transition-all ${
                    i === currentStepIndex
                      ? 'bg-blue-500 w-4'
                      : i < currentStepIndex
                        ? 'bg-blue-400/60 hover:bg-blue-400 cursor-pointer'
                        : 'bg-gray-600'
                  }`}
                  title={`Step ${i + 1}: ${s.title}`}
                />
              ))}
            </div>

            {/* Navigation buttons */}
            <div className="flex items-center gap-2">
              <button
                onClick={exitDemo}
                className="px-3 py-1.5 text-xs text-gray-400 hover:text-gray-200 hover:bg-gray-700/50 rounded transition-colors"
              >
                Exit
              </button>

              {!isFirst && (
                <button
                  onClick={prevStep}
                  className="flex items-center gap-1 px-3 py-1.5 text-xs text-gray-300 hover:text-white bg-gray-700/50 hover:bg-gray-700 rounded transition-colors"
                >
                  <ChevronLeft className="w-3 h-3" />
                  Back
                </button>
              )}

              <button
                onClick={nextStep}
                disabled={nextDisabled}
                className={`flex items-center gap-1 px-4 py-1.5 text-xs font-medium rounded transition-colors ${
                  nextDisabled
                    ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                    : isLast
                      ? 'bg-green-600 text-white hover:bg-green-500'
                      : 'bg-blue-600 text-white hover:bg-blue-500'
                }`}
              >
                {isLast ? (
                  <>
                    <CheckCircle2 className="w-3 h-3" />
                    Finish
                  </>
                ) : (
                  <>
                    Next
                    <ChevronRight className="w-3 h-3" />
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
