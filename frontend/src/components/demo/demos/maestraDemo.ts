import type { DemoDefinition, DemoStep } from '../demoTypes';
import { loadNarrative } from '../demoNarrative';

// ── Structural config (non-editable) — page routing, iframe messages ──
// Keyed by step id so narrative text can be merged in at runtime.

interface StepStructure {
  page: string;
  iframeMessage?: DemoStep['iframeMessage'];
  iframeMessages?: DemoStep['iframeMessages'];
}

const STEP_STRUCTURE: Record<string, StepStructure> = {
  'maestra-discovery': {
    page: 'discover',
  },
  'maestra-handoff': {
    page: 'discover',
    iframeMessage: {
      targetPage: 'discover',
      payload: { action: 'switchToConsole' },
    },
  },
  'maestra-connection': {
    page: 'connect',
  },
  'maestra-semantic': {
    page: 'unify-ask',
  },
  'maestra-nlq': {
    page: 'nlq',
    iframeMessage: {
      targetPage: 'nlq',
      payload: { action: 'navigateTo', tab: 'galaxy' },
    },
  },
  'maestra-dashboard': {
    page: 'nlq',
    iframeMessage: {
      targetPage: 'nlq',
      payload: { action: 'navigateTo', tab: 'dashboard' },
    },
  },
  'maestra-reports': {
    page: 'nlq',
    iframeMessage: {
      targetPage: 'nlq',
      payload: { action: 'reportNavigate', entity: 'combined', tab: 'crosssell' },
    },
  },
  'maestra-onboarding': {
    page: 'nlq',
    iframeMessage: {
      targetPage: 'nlq',
      payload: { action: 'reportNavigate', entity: 'combined', tab: 'maestra' },
    },
  },
};

/** Build the Maestra demo definition, merging current narrative with structural config */
export function buildMaestraDemo(): DemoDefinition {
  const narrative = loadNarrative();

  const steps: DemoStep[] = narrative.map((step) => {
    const structure = STEP_STRUCTURE[step.id] ?? { page: 'nlq' };
    return {
      id: step.id,
      phase: step.phase,
      title: step.title,
      body: step.body,
      page: structure.page,
      ...(structure.iframeMessage && { iframeMessage: structure.iframeMessage }),
      ...(structure.iframeMessages && { iframeMessages: structure.iframeMessages }),
      messages: step.messages,
    };
  });

  return {
    id: 'maestra-guided-tour',
    name: 'Guided Tour',
    description:
      'Investor-grade narrated walkthrough — Maestra walks you through live module UIs with AI-guided narration.',
    icon: '\uD83C\uDF99\uFE0F',
    layout: 'maestra',
    steps,
  };
}

// Export a static instance for the demo picker (will be rebuilt on each startDemo)
export const maestraDemo: DemoDefinition = buildMaestraDemo();
