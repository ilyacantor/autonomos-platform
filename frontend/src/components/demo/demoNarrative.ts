// ── Demo Narrative — editable text layer ──────────────────────────────
// This is the default narrative. The DemoEditor saves overrides to localStorage.
// maestraDemo.ts merges overrides at runtime so edits take effect immediately.

export interface StepNarrative {
  id: string;
  phase: string;
  title: string;
  body: string;
  messages: { text: string; delay: number }[];
}

export type DemoNarrativeData = StepNarrative[];

const STORAGE_KEY = 'maestra-demo-narrative';

export const DEFAULT_NARRATIVE: DemoNarrativeData = [
  {
    id: 'maestra-discovery',
    phase: 'Discovery',
    title: 'Meet Maestra',
    body: "Maestra introduces herself and the live environment you're about to explore.",
    messages: [
      { text: "Hi, I'm Maestra — I'm the onboarding and engagement manager for autonomOS. I handle everything from initial discovery through deployment and ongoing monitoring. I'm the one who actually understands your enterprise before our first real conversation — and keeps understanding it as things change.", delay: 0 },
      { text: "Everything you're about to see is running live against synthetic data representing a messy enterprise environment. Our data farm generated tens of thousands of signals — ingesting over 400 raw assets and cataloging roughly 100 into structured records across 6 sources of record and 4 fabric planes. Real conflicts, real naming mismatches, real hierarchy gaps. Nothing is hardcoded or staged.", delay: 2400 },
      { text: "I'll walk you through the full platform — how we discover what's in your environment, map the connections, resolve conflicts, and build a unified context layer that both people and AI agents can query. At the end I'll show you Convergence, our multi-entity product for M&A — which I'm really excited about. Let's start with what I found when I scanned this environment.", delay: 5000 },
    ],
  },
  {
    id: 'maestra-handoff',
    phase: 'Catalog',
    title: 'Discovery Console',
    body: 'The Console view — where discovery runs and the asset catalog is built.',
    messages: [
      { text: "This is the discovery console — where we scan your environment and build the asset catalog.", delay: 0 },
      { text: "The platform identified and classified every IT asset it could find — source systems, integration layers, data stores, APIs. What you're seeing is the result of that scan, organized by system type and classification status.", delay: 1400 },
      { text: "Once the catalog is built, it gets handed off to the connection engine so we can map how all these systems actually talk to each other.", delay: 2800 },
    ],
  },
  {
    id: 'maestra-connection',
    phase: 'Topology',
    title: 'Connection Mapping',
    body: 'Visual topology of connections between systems.',
    messages: [
      { text: "This is the topology view — a map of the connections between your systems.", delay: 0 },
      { text: "The platform built this automatically from the discovery catalog. Each line represents a real data flow — what travels between systems, through which fabric plane, and in which direction.", delay: 1400 },
      { text: "Click any connection to see the details. This is the foundation for everything that comes next — you can't build a semantic layer if you don't know how the data moves.", delay: 2800 },
    ],
  },
  {
    id: 'maestra-semantic',
    phase: 'Semantic Graph',
    title: 'Context Layer',
    body: 'How source system data maps into unified business concepts.',
    messages: [
      { text: 'This is where it gets interesting. On the left, the raw data flows from the systems you just saw. On the right, unified business concepts — revenue, customer, headcount, product.', delay: 0 },
      { text: 'Each line shows how a field from a source system maps to a common concept. When your CRM calls it "bookings" and your ERP calls it "recognized revenue," this is where those get reconciled — or flagged as a conflict if they genuinely mean different things.', delay: 1800 },
      { text: "The result is a single context layer where every concept traces back to its source. When someone asks a question downstream, the answer comes with provenance — which system it came from, what mapping produced it, and how confident we are.", delay: 3600 },
    ],
  },
  {
    id: 'maestra-nlq',
    phase: 'Query',
    title: 'Ask Anything',
    body: 'Natural language query interface — click a preset or type your own.',
    messages: [
      { text: "This is the query interface. Pick a preset question or type your own — plain English.", delay: 0 },
      { text: "Every answer comes from the context layer you just saw. It's not a search engine guessing — it's resolving your question against mapped, reconciled data and showing you exactly where the answer came from.", delay: 1400 },
    ],
  },
  {
    id: 'maestra-dashboard',
    phase: 'Persona Views',
    title: 'Dashboards',
    body: 'Role-specific dashboards built from the same unified data.',
    messages: [
      { text: "These dashboards are built from the same context layer. The difference is who's looking — a CFO sees financial metrics and margin trends, a CRO sees pipeline and conversion, a CTO sees system health and technical debt.", delay: 0 },
      { text: "Same underlying data, different lens. The persona determines what's relevant, not a custom build for each executive.", delay: 1400 },
    ],
  },
  {
    id: 'maestra-reports',
    phase: 'M&A',
    title: 'Convergence — Reporting Portal',
    body: 'Multi-entity reporting for M&A — the Convergence product.',
    messages: [
      { text: "This is where Convergence comes in. Everything you've seen so far works for a single enterprise. Convergence does the same thing across two entities — an acquirer and a target.", delay: 0 },
      { text: "What you're looking at is Meridian acquiring Cascadia. The platform took both companies through the same discovery, mapping, and semantic process — then unified them into one view with every conflict and overlap identified.", delay: 1600 },
      { text: "The tabs show the work product — combined financials, overlap analysis, and the conflict register showing where the two entities define things differently.", delay: 3200 },
    ],
  },
  {
    id: 'maestra-onboarding',
    phase: 'Engagement Start',
    title: 'Maestra Onboarding',
    body: 'Start a new engagement and see Maestra work live.',
    messages: [
      { text: "And this is where every engagement starts — my onboarding portal.", delay: 0 },
      { text: "This is a live conversation, not a recording. Start an engagement and ask me about the deal — I'll walk you through what I know about both entities, what I've found, and what still needs to be confirmed with stakeholders.", delay: 1400 },
      { text: "That's the full platform — discovery, connection mapping, semantic unification, natural language query, role-based dashboards, and M&A reporting. One system, end to end.", delay: 3000 },
    ],
  },
  {
    id: 'maestra-handover',
    phase: 'Handover',
    title: 'Chat with Maestra',
    body: 'Tour complete — continue the conversation directly with Maestra.',
    messages: [
      { text: "Now that the tour is complete, I'll introduce you to my onboarding process. Click the M on the bottom right of the screen, and chat with me either with presets or with your own words. See you soon!", delay: 0 },
    ],
  },
];

/** Load narrative from localStorage, falling back to defaults */
export function loadNarrative(): DemoNarrativeData {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) return JSON.parse(stored);
  } catch {
    // corrupt data — fall back
  }
  return DEFAULT_NARRATIVE;
}

/** Save narrative overrides to localStorage */
export function saveNarrative(data: DemoNarrativeData): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  // Dispatch event so running demos pick up changes immediately
  window.dispatchEvent(new CustomEvent('narrative-updated'));
}

/** Reset to defaults */
export function resetNarrative(): void {
  localStorage.removeItem(STORAGE_KEY);
  window.dispatchEvent(new CustomEvent('narrative-updated'));
}
