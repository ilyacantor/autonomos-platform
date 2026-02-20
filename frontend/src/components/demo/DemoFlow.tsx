import { useState, useEffect, useCallback } from 'react';
import { ChevronLeft, ChevronRight, Play } from 'lucide-react';
import DemoModal from './DemoModal';
import LaserPointer from './LaserPointer';
import DemoIframeContainer from '../DemoIframeContainer';

// ---------------------------------------------------------------------------
// Step definitions — the shell owns ALL narrative
// ---------------------------------------------------------------------------

interface PointerTarget {
  /** X position as percentage of iframe area (0-100) */
  x: number;
  /** Y position as percentage of iframe area (0-100) */
  y: number;
  /** Hint label shown next to the dot */
  label?: string;
}

interface DemoStep {
  id: string;
  /** Which iframe to show */
  iframeSrc: string;
  iframeTitle: string;
  /** Tab label shown in the step indicator */
  label: string;
  /** Modal content */
  modalTitle: string;
  modalBody: React.ReactNode;
  /** Button label to advance (omitted on last step) */
  nextLabel?: string;
  /** Laser pointer target — where the user should click */
  pointer?: PointerTarget;
}

const STEPS: DemoStep[] = [
  {
    id: 'nlq-start',
    iframeSrc: 'https://nlq.autonomos.software',
    iframeTitle: 'NLQ - Natural Language Query',
    label: 'NLQ',
    modalTitle: 'Step 1 — Ask a Question',
    modalBody: (
      <>
        <p className="text-gray-300 text-sm leading-relaxed mb-3">
          A user asks: <span className="text-cyan-400 font-medium">"Why did revenue increase last quarter?"</span>
        </p>
        <p className="text-gray-400 text-sm leading-relaxed mb-4">
          Select the preset in the NLQ console to see the answer generated in real-time.
          Under the hood, four systems coordinate to produce this answer.
        </p>
        <p className="text-gray-500 text-xs">
          The answer you see is live — not a screenshot.
        </p>
      </>
    ),
    nextLabel: 'See how this works under the hood →',
    pointer: { x: 50, y: 35, label: 'Select a preset query' },
  },
  {
    id: 'aod',
    iframeSrc: 'https://discover.autonomos.software/',
    iframeTitle: 'AOD Discovery',
    label: 'AOD',
    modalTitle: 'Step 2 — Discover What Exists',
    modalBody: (
      <>
        <p className="text-gray-300 text-sm leading-relaxed mb-3">
          <span className="text-cyan-400 font-medium">AOS Discover (AOD)</span> scans the enterprise
          to find every system, API, and data source.
        </p>
        <p className="text-gray-400 text-sm leading-relaxed mb-4">
          The console tab shows pre-loaded scan results — Salesforce, HubSpot, Stripe,
          and internal databases detected automatically.
        </p>
        <p className="text-gray-500 text-xs">
          No credentials needed — AOD uses metadata discovery.
        </p>
      </>
    ),
    nextLabel: 'How do we connect to them? →',
    pointer: { x: 50, y: 45, label: 'View scan results' },
  },
  {
    id: 'aam',
    iframeSrc: 'https://aam.autonomos.software/ui/topology',
    iframeTitle: 'AAM Mesh Interface',
    label: 'AAM',
    modalTitle: 'Step 3 — Blueprint the Connections',
    modalBody: (
      <>
        <p className="text-gray-300 text-sm leading-relaxed mb-3">
          <span className="text-cyan-400 font-medium">Adaptive API Mesh (AAM)</span> blueprints
          how to connect to each discovered system and dispatches work orders.
        </p>
        <p className="text-gray-400 text-sm leading-relaxed mb-4">
          The topology view shows live pipe configurations and dispatch runners.
          AAM handles auth, rate limiting, and schema negotiation.
        </p>
        <div className="bg-cyan-900/30 border border-cyan-700/40 rounded p-2.5 mb-3">
          <p className="text-cyan-300 text-xs font-medium mb-1">Action required</p>
          <p className="text-gray-300 text-xs leading-relaxed">
            Click the <span className="text-white font-semibold">Reset</span> button on the left
            side panel to load the topology visualization.
          </p>
        </div>
        <p className="text-gray-500 text-xs">
          Each connection is a managed pipe — not a point-to-point integration.
        </p>
      </>
    ),
    nextLabel: 'How does the data get meaning? →',
    pointer: { x: 4, y: 50, label: 'Click Reset' },
  },
  {
    id: 'dcl',
    iframeSrc: 'https://dcl.autonomos.software',
    iframeTitle: 'DCL - Data Connectivity Layer',
    label: 'DCL',
    modalTitle: 'Step 4 — Map Fields to Business Concepts',
    modalBody: (
      <>
        <p className="text-gray-300 text-sm leading-relaxed mb-3">
          <span className="text-cyan-400 font-medium">Data Connectivity Layer (DCL)</span> maps
          every raw field to a canonical business concept.
        </p>
        <p className="text-gray-400 text-sm leading-relaxed mb-4">
          The Sankey visualization shows how vendor-specific fields (e.g. sf_amount,
          hs_dealvalue) unify into a single <code className="text-cyan-400/80">revenue</code> concept.
        </p>
        <p className="text-gray-500 text-xs">
          This is schema-on-write — validation happens before storage.
        </p>
      </>
    ),
    nextLabel: 'Back to the answer →',
    pointer: { x: 50, y: 50, label: 'Explore the field mappings' },
  },
  {
    id: 'nlq-return',
    iframeSrc: 'https://nlq.autonomos.software',
    iframeTitle: 'NLQ - Natural Language Query',
    label: 'NLQ',
    modalTitle: 'Step 5 — The Complete Answer',
    modalBody: (
      <>
        <p className="text-gray-300 text-sm leading-relaxed mb-3">
          All of that happened in under 2 seconds to answer the question.
        </p>
        <div className="bg-gray-800/60 border border-gray-700 rounded p-3 mb-4">
          <p className="text-xs text-gray-500 mb-2 font-medium uppercase tracking-wide">Provenance trail</p>
          <div className="space-y-1.5 text-xs">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-cyan-400 shrink-0" />
              <span className="text-gray-400"><span className="text-gray-300">AOD</span> discovered 4 connected systems</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-green-400 shrink-0" />
              <span className="text-gray-400"><span className="text-gray-300">AAM</span> pulled revenue data via 3 pipes</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-orange-400 shrink-0" />
              <span className="text-gray-400"><span className="text-gray-300">DCL</span> unified 12 fields into canonical revenue</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-purple-400 shrink-0" />
              <span className="text-gray-400"><span className="text-gray-300">NLQ</span> composed the answer with citations</span>
            </div>
          </div>
        </div>
        <p className="text-gray-500 text-xs">
          Every answer in AOS carries full provenance — no black boxes.
        </p>
      </>
    ),
    // No nextLabel or pointer — this is the summary step
  },
];

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

interface DemoFlowProps {
  onExit: () => void;
}

export default function DemoFlow({ onExit }: DemoFlowProps) {
  const [stepIndex, setStepIndex] = useState(0);
  const [modalVisible, setModalVisible] = useState(true);
  // Track which steps have been visited so we can lazy-mount iframes
  const [visited, setVisited] = useState<Set<number>>(() => new Set([0]));

  const step = STEPS[stepIndex];
  const isFirst = stepIndex === 0;
  const isLast = stepIndex === STEPS.length - 1;

  // ---- Navigation helpers ----
  const goNext = useCallback(() => {
    if (!isLast) {
      const next = stepIndex + 1;
      setStepIndex(next);
      setVisited(prev => new Set(prev).add(next));
      setModalVisible(true);
    }
  }, [isLast, stepIndex]);

  const goBack = useCallback(() => {
    if (!isFirst) {
      const prev = stepIndex - 1;
      setStepIndex(prev);
      setVisited(v => new Set(v).add(prev));
      setModalVisible(true);
    }
  }, [isFirst, stepIndex]);

  const closeModal = useCallback(() => {
    setModalVisible(false);
  }, []);

  // ---- Keyboard navigation ----
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't capture if user is typing in an input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

      switch (e.key) {
        case 'ArrowRight':
          e.preventDefault();
          goNext();
          break;
        case 'ArrowLeft':
          e.preventDefault();
          goBack();
          break;
        case 'Escape':
          e.preventDefault();
          if (modalVisible) {
            closeModal();
          } else {
            onExit();
          }
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [goNext, goBack, closeModal, modalVisible, onExit]);

  return (
    <div className="h-full flex flex-col">
      {/* ---- Step indicator bar ---- */}
      <div className="h-12 bg-gray-900/95 border-b border-gray-800 flex items-center px-4 gap-3 shrink-0">
        {/* Back button */}
        <button
          onClick={goBack}
          disabled={isFirst}
          className={`p-1.5 rounded transition-colors ${
            isFirst
              ? 'text-gray-700 cursor-not-allowed'
              : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
          }`}
          title="Previous step (←)"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>

        {/* Step pills */}
        <div className="flex items-center gap-1.5">
          {STEPS.map((s, i) => (
            <button
              key={s.id}
              onClick={() => { setStepIndex(i); setVisited(v => new Set(v).add(i)); setModalVisible(true); }}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium transition-all ${
                i === stepIndex
                  ? 'bg-cyan-500/20 text-cyan-400 ring-1 ring-cyan-500/40'
                  : i < stepIndex
                  ? 'bg-gray-800 text-gray-400 hover:text-gray-300'
                  : 'bg-gray-800/50 text-gray-600 hover:text-gray-500'
              }`}
            >
              <span className="w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-bold bg-gray-700/80">
                {i + 1}
              </span>
              {s.label}
            </button>
          ))}
        </div>

        {/* Forward button */}
        <button
          onClick={goNext}
          disabled={isLast}
          className={`p-1.5 rounded transition-colors ${
            isLast
              ? 'text-gray-700 cursor-not-allowed'
              : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
          }`}
          title="Next step (→)"
        >
          <ChevronRight className="w-4 h-4" />
        </button>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Toggle modal / keyboard hint */}
        {!modalVisible && (
          <button
            onClick={() => setModalVisible(true)}
            className="text-xs text-gray-500 hover:text-gray-300 transition-colors px-2 py-1 rounded hover:bg-gray-800"
          >
            Show info panel
          </button>
        )}

        <span className="text-[10px] text-gray-600 hidden sm:inline">
          ← → navigate &middot; Esc close
        </span>

        {/* Exit demo button */}
        <button
          onClick={onExit}
          className="text-xs text-gray-500 hover:text-gray-300 px-2 py-1 rounded hover:bg-gray-800 transition-colors"
        >
          Exit demo
        </button>
      </div>

      {/* ---- Iframe area + modal overlay ---- */}
      <div className="flex-1 relative min-h-0">
        {/* Lazy-mount iframes: only mount when the step has been visited.
            Dedupe by src so NLQ (used in steps 1 & 5) isn't mounted twice. */}
        {getVisitedIframes(STEPS, visited).map(({ src, title }) => (
          <div
            key={src}
            className="absolute inset-0"
            style={{ display: isCurrentSrc(step, src) ? 'block' : 'none' }}
          >
            <DemoIframeContainer src={src} title={title} />
          </div>
        ))}

        {/* Overlay layer — sits above the iframe to host the laser pointer.
            pointer-events:none so clicks pass through to the iframe. */}
        {step.pointer && (
          <div
            style={{
              position: 'absolute',
              inset: 0,
              zIndex: 40,
              pointerEvents: 'none',
            }}
          >
            <LaserPointer
              x={step.pointer.x}
              y={step.pointer.y}
              label={step.pointer.label}
              visible
            />
          </div>
        )}

        {/* Modal overlay — shell-owned, on top of iframe */}
        <DemoModal
          title={step.modalTitle}
          onClose={closeModal}
          visible={modalVisible}
        >
          {step.modalBody}

          {/* Next button inside modal */}
          {step.nextLabel && (
            <button
              onClick={goNext}
              className="mt-2 w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-cyan-600 hover:bg-cyan-500 text-white text-sm font-medium rounded-lg transition-colors"
            >
              {step.nextLabel}
            </button>
          )}

          {isLast && (
            <button
              onClick={onExit}
              className="mt-2 w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-gray-700 hover:bg-gray-600 text-gray-200 text-sm font-medium rounded-lg transition-colors"
            >
              <Play className="w-3.5 h-3.5" />
              Explore freely
            </button>
          )}
        </DemoModal>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Helpers — dedupe iframes by src URL so NLQ isn't mounted twice
// ---------------------------------------------------------------------------

/** Only mount iframes for steps the user has actually visited (dedupe by src). */
function getVisitedIframes(steps: DemoStep[], visited: Set<number>): { src: string; title: string }[] {
  const seen = new Set<string>();
  const result: { src: string; title: string }[] = [];
  for (let i = 0; i < steps.length; i++) {
    if (!visited.has(i)) continue;
    const s = steps[i];
    if (!seen.has(s.iframeSrc)) {
      seen.add(s.iframeSrc);
      result.push({ src: s.iframeSrc, title: s.iframeTitle });
    }
  }
  return result;
}

function isCurrentSrc(step: DemoStep, src: string): boolean {
  return step.iframeSrc === src;
}
