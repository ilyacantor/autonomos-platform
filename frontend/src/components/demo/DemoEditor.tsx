import { useState, useCallback, useEffect } from 'react';
import {
  loadNarrative,
  saveNarrative,
  resetNarrative,
  DEFAULT_NARRATIVE,
  type DemoNarrativeData,
  type StepNarrative,
} from './demoNarrative';
import { useDemo } from '../../contexts/DemoContext';
import { buildMaestraDemo } from './demos/maestraDemo';
import { ChevronDown, ChevronRight, Plus, Trash2, Save, RotateCcw, Play, GripVertical } from 'lucide-react';

export default function DemoEditor() {
  const [narrative, setNarrative] = useState<DemoNarrativeData>(loadNarrative);
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set(narrative.map((s) => s.id)));
  const [dirty, setDirty] = useState(false);
  const [saved, setSaved] = useState(false);
  const { startDemo } = useDemo();

  // Reload if another tab resets
  useEffect(() => {
    const handler = () => {
      setNarrative(loadNarrative());
      setDirty(false);
    };
    window.addEventListener('narrative-updated', handler);
    return () => window.removeEventListener('narrative-updated', handler);
  }, []);

  const toggleStep = (id: string) => {
    setExpandedSteps((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const updateStep = useCallback((stepIdx: number, patch: Partial<StepNarrative>) => {
    setNarrative((prev) => prev.map((s, i) => (i === stepIdx ? { ...s, ...patch } : s)));
    setDirty(true);
    setSaved(false);
  }, []);

  const updateMessage = useCallback((stepIdx: number, msgIdx: number, text: string) => {
    setNarrative((prev) =>
      prev.map((s, i) => {
        if (i !== stepIdx) return s;
        const msgs = [...s.messages];
        msgs[msgIdx] = { ...msgs[msgIdx], text };
        return { ...s, messages: msgs };
      }),
    );
    setDirty(true);
    setSaved(false);
  }, []);

  const updateDelay = useCallback((stepIdx: number, msgIdx: number, delay: number) => {
    setNarrative((prev) =>
      prev.map((s, i) => {
        if (i !== stepIdx) return s;
        const msgs = [...s.messages];
        msgs[msgIdx] = { ...msgs[msgIdx], delay };
        return { ...s, messages: msgs };
      }),
    );
    setDirty(true);
    setSaved(false);
  }, []);

  const addMessage = useCallback((stepIdx: number) => {
    setNarrative((prev) =>
      prev.map((s, i) => {
        if (i !== stepIdx) return s;
        const lastDelay = s.messages.length > 0 ? s.messages[s.messages.length - 1].delay + 1200 : 0;
        return { ...s, messages: [...s.messages, { text: '', delay: lastDelay }] };
      }),
    );
    setDirty(true);
    setSaved(false);
  }, []);

  const removeMessage = useCallback((stepIdx: number, msgIdx: number) => {
    setNarrative((prev) =>
      prev.map((s, i) => {
        if (i !== stepIdx) return s;
        return { ...s, messages: s.messages.filter((_, j) => j !== msgIdx) };
      }),
    );
    setDirty(true);
    setSaved(false);
  }, []);

  const moveMessage = useCallback((stepIdx: number, msgIdx: number, direction: -1 | 1) => {
    setNarrative((prev) =>
      prev.map((s, i) => {
        if (i !== stepIdx) return s;
        const target = msgIdx + direction;
        if (target < 0 || target >= s.messages.length) return s;
        const msgs = [...s.messages];
        [msgs[msgIdx], msgs[target]] = [msgs[target], msgs[msgIdx]];
        return { ...s, messages: msgs };
      }),
    );
    setDirty(true);
    setSaved(false);
  }, []);

  const handleSave = () => {
    saveNarrative(narrative);
    setDirty(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleReset = () => {
    if (!window.confirm('Reset all narrative text to defaults? This cannot be undone.')) return;
    resetNarrative();
    setNarrative(DEFAULT_NARRATIVE);
    setDirty(false);
  };

  const handlePreview = () => {
    saveNarrative(narrative);
    setDirty(false);
    startDemo(buildMaestraDemo());
  };

  const totalMessages = narrative.reduce((sum, s) => sum + s.messages.length, 0);

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* ── Sticky header ──────────────────────────────────────────── */}
      <div className="sticky top-0 z-40 bg-gray-900/95 backdrop-blur-sm border-b border-gray-800">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-white">Demo Narrative Editor</h1>
            <p className="text-xs text-gray-400 mt-0.5">
              {narrative.length} steps, {totalMessages} messages
              {dirty && <span className="ml-2 text-amber-400">— unsaved changes</span>}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleReset}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-gray-400 hover:text-white hover:bg-gray-800 rounded transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Reset Defaults
            </button>
            <button
              onClick={handlePreview}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-green-400 hover:text-white hover:bg-green-600/20 border border-green-600/40 rounded transition-colors"
            >
              <Play className="w-3.5 h-3.5" />
              Save & Preview
            </button>
            <button
              onClick={handleSave}
              disabled={!dirty}
              className={`flex items-center gap-1.5 px-4 py-1.5 text-xs font-medium rounded transition-all ${
                saved
                  ? 'bg-green-600 text-white'
                  : dirty
                    ? 'bg-purple-600 text-white hover:bg-purple-500'
                    : 'bg-gray-700 text-gray-500 cursor-not-allowed'
              }`}
            >
              <Save className="w-3.5 h-3.5" />
              {saved ? 'Saved!' : 'Save'}
            </button>
          </div>
        </div>
      </div>

      {/* ── Steps ─────────────────────────────────────────────────── */}
      <div className="max-w-5xl mx-auto px-6 py-6 space-y-4">
        {narrative.map((step, stepIdx) => {
          const isExpanded = expandedSteps.has(step.id);
          return (
            <div
              key={step.id}
              className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden"
            >
              {/* Step header */}
              <button
                onClick={() => toggleStep(step.id)}
                className="w-full flex items-center gap-3 px-5 py-3.5 text-left hover:bg-gray-800/50 transition-colors"
              >
                {isExpanded ? (
                  <ChevronDown className="w-4 h-4 text-purple-400 flex-shrink-0" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-gray-500 flex-shrink-0" />
                )}
                <span className="text-[10px] text-purple-400 uppercase tracking-wider font-medium bg-purple-600/10 px-2 py-0.5 rounded flex-shrink-0">
                  Step {stepIdx + 1}
                </span>
                <span className="font-semibold text-sm text-white">{step.title}</span>
                <span className="text-xs text-gray-500 ml-auto flex-shrink-0">
                  {step.phase} — {step.messages.length} message{step.messages.length !== 1 ? 's' : ''}
                </span>
              </button>

              {/* Expanded content */}
              {isExpanded && (
                <div className="px-5 pb-5 border-t border-gray-800/50">
                  {/* Step metadata */}
                  <div className="grid grid-cols-2 gap-4 mt-4 mb-5">
                    <div>
                      <label className="block text-[10px] text-gray-500 uppercase tracking-wider mb-1">Title</label>
                      <input
                        type="text"
                        value={step.title}
                        onChange={(e) => updateStep(stepIdx, { title: e.target.value })}
                        className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-white focus:border-purple-500 focus:outline-none transition-colors"
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] text-gray-500 uppercase tracking-wider mb-1">Phase</label>
                      <input
                        type="text"
                        value={step.phase}
                        onChange={(e) => updateStep(stepIdx, { phase: e.target.value })}
                        className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-white focus:border-purple-500 focus:outline-none transition-colors"
                      />
                    </div>
                    <div className="col-span-2">
                      <label className="block text-[10px] text-gray-500 uppercase tracking-wider mb-1">
                        Description
                      </label>
                      <input
                        type="text"
                        value={step.body}
                        onChange={(e) => updateStep(stepIdx, { body: e.target.value })}
                        className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-white focus:border-purple-500 focus:outline-none transition-colors"
                      />
                    </div>
                  </div>

                  {/* Messages */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[10px] text-gray-500 uppercase tracking-wider font-medium">
                        Narration Messages
                      </span>
                    </div>
                    {step.messages.map((msg, msgIdx) => (
                      <div
                        key={msgIdx}
                        className="group flex items-start gap-2 bg-gray-800/50 rounded-lg p-3 hover:bg-gray-800 transition-colors"
                      >
                        {/* Drag handle / index */}
                        <div className="flex flex-col items-center gap-0.5 pt-1 flex-shrink-0">
                          <button
                            onClick={() => moveMessage(stepIdx, msgIdx, -1)}
                            disabled={msgIdx === 0}
                            className="text-gray-600 hover:text-gray-300 disabled:opacity-20 transition-colors"
                            title="Move up"
                          >
                            <GripVertical className="w-3 h-3 rotate-180" />
                          </button>
                          <span className="text-[10px] text-gray-600 font-mono">{msgIdx + 1}</span>
                          <button
                            onClick={() => moveMessage(stepIdx, msgIdx, 1)}
                            disabled={msgIdx === step.messages.length - 1}
                            className="text-gray-600 hover:text-gray-300 disabled:opacity-20 transition-colors"
                            title="Move down"
                          >
                            <GripVertical className="w-3 h-3" />
                          </button>
                        </div>

                        {/* Message text */}
                        <textarea
                          value={msg.text}
                          onChange={(e) => updateMessage(stepIdx, msgIdx, e.target.value)}
                          rows={2}
                          className="flex-1 bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm text-gray-100 focus:border-purple-500 focus:outline-none resize-y transition-colors"
                        />

                        {/* Delay + delete */}
                        <div className="flex flex-col items-end gap-1 flex-shrink-0">
                          <div className="flex items-center gap-1">
                            <label className="text-[9px] text-gray-600">ms</label>
                            <input
                              type="number"
                              value={msg.delay}
                              onChange={(e) => updateDelay(stepIdx, msgIdx, parseInt(e.target.value) || 0)}
                              className="w-16 bg-gray-900 border border-gray-700 rounded px-2 py-1 text-xs text-gray-300 text-right focus:border-purple-500 focus:outline-none transition-colors"
                            />
                          </div>
                          <button
                            onClick={() => removeMessage(stepIdx, msgIdx)}
                            className="p-1 text-gray-600 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all"
                            title="Delete message"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    ))}

                    {/* Add message */}
                    <button
                      onClick={() => addMessage(stepIdx)}
                      className="flex items-center gap-1.5 px-3 py-2 text-xs text-gray-400 hover:text-purple-400 hover:bg-gray-800 rounded border border-dashed border-gray-700 hover:border-purple-600/40 w-full justify-center transition-colors"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      Add Message
                    </button>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
