import { useEffect, useRef, useState, useCallback } from 'react';
import { ChevronLeft, ChevronRight, X } from 'lucide-react';
import { useDemo } from '../../contexts/DemoContext';
import type { MaestraMessage } from './demoTypes';

// ── Iframe pages (same source of truth as App.tsx) ───────────────────
const IFRAME_PAGES: Record<string, { src: string; title: string }> = {
  nlq: { src: 'https://aos-nlq.onrender.com', title: 'NLQ - Natural Language Query' },
  discover: { src: 'https://aodv3-1.onrender.com/', title: 'AOD Discovery' },
  connect: { src: 'https://aos-aam.onrender.com/ui/topology', title: 'AAM Mesh Interface' },
  'unify-ask': { src: 'https://aos-dclv2.onrender.com', title: 'DCL - Data Connectivity Layer' },
  farm: { src: 'https://farmv2.onrender.com', title: 'Farm' },
  finops: { src: 'https://aosfinopsagent.onrender.com', title: 'FinOps Agent' },
};

// ── Typing indicator (3 bouncing dots) ───────────────────────────────
function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 px-4 py-3">
      <div className="flex items-center gap-1">
        <span className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
        <span className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
        <span className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
      </div>
    </div>
  );
}

// ── Single chat bubble ───────────────────────────────────────────────
function ChatBubble({ text, dimmed }: { text: string; dimmed?: boolean }) {
  return (
    <div
      className={`bg-gray-800 rounded-2xl rounded-tl-sm px-4 py-3 text-sm leading-relaxed max-w-[95%] transition-opacity duration-300 ${
        dimmed ? 'opacity-40' : 'text-gray-100'
      }`}
    >
      {text}
    </div>
  );
}

// ── Main Maestra Demo component ──────────────────────────────────────
export default function MaestraDemo() {
  const { activeDemo, currentStepIndex, nextStep, prevStep, exitDemo, status } = useDemo();

  // Track which messages have been revealed for the current step
  const [revealedCount, setRevealedCount] = useState(0);
  const [isTyping, setIsTyping] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  // Get current step data
  const step = activeDemo?.steps[currentStepIndex];
  const totalSteps = activeDemo?.steps.length ?? 0;
  const isFirst = currentStepIndex === 0;
  const isLast = currentStepIndex === totalSteps - 1;
  const currentMessages: MaestraMessage[] = step?.messages ?? [];

  // Clear timers on cleanup
  const clearTimers = useCallback(() => {
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];
  }, []);

  // Animate messages appearing for current step
  useEffect(() => {
    clearTimers();
    setRevealedCount(0);
    setIsTyping(false);

    if (!currentMessages.length) return;

    // Show first message immediately (or after its delay)
    const firstDelay = currentMessages[0].delay ?? 0;

    // Show typing indicator then reveal each message
    currentMessages.forEach((msg, i) => {
      const delay = i === 0 ? firstDelay : (msg.delay ?? 1200);

      // Show typing indicator slightly before the message
      const typingTimer = setTimeout(() => {
        setIsTyping(true);
      }, delay > 300 ? delay - 300 : 0);
      timersRef.current.push(typingTimer);

      // Reveal the message
      const revealTimer = setTimeout(() => {
        setRevealedCount((prev) => Math.max(prev, i + 1));
        // Hide typing if this is the last message
        if (i === currentMessages.length - 1) {
          setIsTyping(false);
        }
      }, delay);
      timersRef.current.push(revealTimer);
    });

    return clearTimers;
  }, [currentStepIndex, currentMessages, clearTimers]);

  // Send postMessages into the visible iframe (handles both singular and plural)
  useEffect(() => {
    const allMsgs: { targetPage: string; payload: Record<string, unknown>; delay: number }[] = [];

    // Singular iframeMessage
    if (step?.iframeMessage) {
      allMsgs.push({ ...step.iframeMessage, delay: 300 });
    }
    // Plural iframeMessages (sequenced with delays)
    if (step?.iframeMessages?.length) {
      step.iframeMessages.forEach((msg) => {
        allMsgs.push({ targetPage: msg.targetPage, payload: msg.payload, delay: msg.delay ?? 0 });
      });
    }

    if (!allMsgs.length) return;

    const timers: ReturnType<typeof setTimeout>[] = [];

    allMsgs.forEach((msg) => {
      const timer = setTimeout(() => {
        const iframes = document.querySelectorAll('iframe');
        for (const iframe of iframes) {
          const wrapper = iframe.parentElement;
          if (wrapper && wrapper.style.display !== 'none') {
            try {
              iframe.contentWindow?.postMessage(msg.payload, '*');
              console.log(`[MaestraDemo] postMessage to ${msg.targetPage} →`, msg.payload);
            } catch (err) {
              console.warn('[MaestraDemo] postMessage failed:', err);
            }
            return;
          }
        }
      }, msg.delay);
      timers.push(timer);
    });

    return () => timers.forEach(clearTimeout);
  }, [currentStepIndex, step]);

  // Auto-scroll chat to bottom when new messages appear
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [revealedCount, isTyping, currentStepIndex]);

  // Keyboard navigation
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight' || e.key === ' ') {
        e.preventDefault();
        nextStep();
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        prevStep();
      } else if (e.key === 'Escape') {
        e.preventDefault();
        exitDemo();
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [nextStep, prevStep, exitDemo]);

  if (status !== 'running' || !activeDemo || !step) return null;

  const activePage = step.page;

  return (
    <div className="fixed inset-0 z-50 bg-gray-950 flex flex-col">
      {/* ── Top bar ─────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-800 bg-gray-900/80 backdrop-blur-sm flex-shrink-0">
        <div className="flex items-center gap-3">
          {/* Maestra avatar */}
          <div className="w-8 h-8 rounded-full bg-purple-600 flex items-center justify-center text-white font-bold text-sm">
            M
          </div>
          <span className="text-white font-semibold text-sm">Maestra</span>
        </div>
        <span className="text-gray-400 text-xs font-medium">
          Step {currentStepIndex + 1} of {totalSteps}
        </span>
        <button
          onClick={exitDemo}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-gray-400 hover:text-white hover:bg-gray-800 rounded transition-colors"
        >
          <X className="w-3.5 h-3.5" />
          Exit Demo
        </button>
      </div>

      {/* ── Main split panel ────────────────────────────────────────── */}
      <div className="flex flex-1 min-h-0 flex-col md:flex-row">
        {/* ── Left: Maestra chat panel ────────────────────────────── */}
        <div className="w-full md:w-[30%] md:min-w-[280px] md:max-w-[400px] h-[35vh] md:h-auto flex flex-col border-b md:border-b-0 md:border-r border-gray-800 bg-gray-900/50">
          {/* Scrollable chat area */}
          <div className="flex-1 overflow-y-auto px-4 py-4 space-y-2">
            {/* Previous steps (dimmed) */}
            {activeDemo.steps.slice(0, currentStepIndex).map((prevStepDef, stepIdx) => (
              <div key={prevStepDef.id}>
                {/* Step separator */}
                <div className="flex items-center gap-2 my-3 first:mt-0">
                  <div className="h-px flex-1 bg-gray-700/50" />
                  <span className="text-[10px] text-gray-600 uppercase tracking-wider font-medium whitespace-nowrap">
                    Step {stepIdx + 1} — {prevStepDef.title}
                  </span>
                  <div className="h-px flex-1 bg-gray-700/50" />
                </div>
                {/* Messages from that step */}
                {(prevStepDef.messages ?? []).map((msg, msgIdx) => (
                  <div key={`${prevStepDef.id}-${msgIdx}`} className="mb-2">
                    <ChatBubble text={msg.text} dimmed />
                  </div>
                ))}
              </div>
            ))}

            {/* Current step separator */}
            <div className="flex items-center gap-2 my-3">
              <div className="h-px flex-1 bg-purple-600/30" />
              <span className="text-[10px] text-purple-400 uppercase tracking-wider font-medium whitespace-nowrap">
                Step {currentStepIndex + 1} — {step.title}
              </span>
              <div className="h-px flex-1 bg-purple-600/30" />
            </div>

            {/* Current step messages (revealed progressively) */}
            {currentMessages.slice(0, revealedCount).map((msg, i) => (
              <div key={`current-${i}`} className="mb-2 animate-fadeIn">
                <ChatBubble text={msg.text} />
              </div>
            ))}

            {/* Typing indicator */}
            {isTyping && revealedCount < currentMessages.length && <TypingIndicator />}

            <div ref={chatEndRef} />
          </div>

          {/* ── Footer: nav buttons + progress dots ─────────────── */}
          <div className="px-4 py-3 border-t border-gray-800 flex-shrink-0">
            {/* Progress dots */}
            <div className="flex items-center justify-center gap-1.5 mb-3">
              {activeDemo.steps.map((_, i) => (
                <div
                  key={i}
                  className={`h-2 rounded-full transition-all duration-300 ${
                    i === currentStepIndex
                      ? 'w-6 bg-purple-500'
                      : i < currentStepIndex
                        ? 'w-2 bg-purple-400/50'
                        : 'w-2 bg-gray-600'
                  }`}
                />
              ))}
            </div>

            {/* Navigation buttons */}
            <div className="flex items-center justify-between gap-2">
              <button
                onClick={prevStep}
                disabled={isFirst}
                className={`flex items-center gap-1 px-3 py-1.5 text-xs rounded transition-colors ${
                  isFirst
                    ? 'text-gray-600 cursor-not-allowed'
                    : 'text-gray-300 hover:text-white hover:bg-gray-700'
                }`}
              >
                <ChevronLeft className="w-3.5 h-3.5" />
                Back
              </button>

              <button
                onClick={isLast ? exitDemo : nextStep}
                className={`flex items-center gap-1 px-4 py-1.5 text-xs font-medium rounded transition-colors ${
                  isLast
                    ? 'bg-green-600 text-white hover:bg-green-500'
                    : 'bg-purple-600 text-white hover:bg-purple-500'
                }`}
              >
                {isLast ? 'Finish' : 'Next'}
                {!isLast && <ChevronRight className="w-3.5 h-3.5" />}
              </button>
            </div>
          </div>
        </div>

        {/* ── Right: Iframe panel ─────────────────────────────────── */}
        {/* Iframes rendered WITHOUT inline styles so DemoRunner's
            sendIframeMessage (which uses iframe.closest('[style]'))
            correctly targets the parent wrapper div for visibility. */}
        <div className="flex-1 min-h-0 relative bg-gray-950">
          {Object.entries(IFRAME_PAGES).map(([pageKey, config]) => (
            <div
              key={pageKey}
              className="absolute inset-0 h-full"
              style={{ display: activePage === pageKey ? 'block' : 'none' }}
            >
              <iframe
                src={config.src}
                className="w-full h-full border-0"
                title={config.title}
                allow="fullscreen"
              />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
