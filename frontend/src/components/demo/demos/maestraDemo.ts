import type { DemoDefinition } from '../demoTypes';

// ── AAM base URL (must match IFRAME_PAGES in App.tsx) ────────────────
const AAM_BASE = 'https://aos-aam.onrender.com';

export const maestraDemo: DemoDefinition = {
  id: 'maestra-guided-tour',
  name: 'Maestra Guided Tour',
  description:
    'Investor-grade narrated walkthrough — Maestra walks you through live module UIs with AI-guided narration.',
  icon: '🎙️',
  layout: 'maestra',
  steps: [
    // ── Step 1: Discovery ──────────────────────────────────────────────
    {
      id: 'maestra-discovery',
      phase: 'Discovery',
      title: 'Environment Scan',
      body: 'Pre-loaded scan results showing discovered systems and their classification.',
      page: 'discover',
      iframeMessage: {
        targetPage: 'discover',
        payload: { action: 'switchToConsole' },
      },
      messages: [
        {
          text: "I've already scanned your environment. Here's what I found — 6 source systems across 4 integration layers.",
          delay: 0,
        },
        {
          text: "Each system has been identified, classified, and cataloged automatically. No manual inventory required.",
          delay: 1200,
        },
      ],
    },

    // ── Step 2: Run Discovery + Handoff ────────────────────────────────
    {
      id: 'maestra-handoff',
      phase: 'Handoff',
      title: 'Catalog Handoff',
      body: 'Running discovery and handing the catalog off to the connection engine.',
      page: 'discover',
      iframeMessage: {
        targetPage: 'discover',
        payload: { action: 'switchToConsole' },
      },
      apiTrigger: {
        path: '/demo/run_pipeline',
        method: 'POST',
        pollForCompletion: {
          statusPath: '/demo/pipeline_status',
          intervalMs: 2000,
          timeoutMs: 120000,
        },
      },
      blocksOnApi: true,
      messages: [
        {
          text: "Now I'm running a full discovery scan and building the catalog in real time. You can see the progress below.",
          delay: 0,
        },
        {
          text: "Once the catalog is built, it's automatically handed off to the connection engine — every system, every data source, ready to be wired up.",
          delay: 1200,
        },
      ],
    },

    // ── Step 3: Connection Mapping ─────────────────────────────────────
    {
      id: 'maestra-connection',
      phase: 'Connection',
      title: 'Connection Mapping',
      body: 'Every connection between your systems — mapped automatically.',
      page: 'connect',
      iframeSrc: `${AAM_BASE}/ui/pipes`,
      messages: [
        {
          text: "Here's every connection between your systems. Each row is a data pathway — where information flows from one system to another.",
          delay: 0,
        },
        {
          text: "The platform mapped all of these automatically from the catalog handoff. You're looking at over a hundred active connections.",
          delay: 1200,
        },
        {
          text: "Each connection knows its source, its destination, and what kind of data travels through it. Click any row to see the details.",
          delay: 2400,
        },
      ],
    },

    // ── Step 4: Semantic Layer ──────────────────────────────────────────
    {
      id: 'maestra-semantic',
      phase: 'Semantic Layer',
      title: 'Unified Data Model',
      body: 'Flow diagram showing how source systems map into common business concepts.',
      page: 'unify-ask',
      messages: [
        {
          text: "What you're seeing is a flow diagram. On the left side are your source systems — CRM, ERP, HR, and so on. On the right side are unified business concepts like Revenue, Customer, and Product.",
          delay: 0,
        },
        {
          text: "Each node is a data entity. The lines between them show how raw data from each source system gets mapped into those common concepts.",
          delay: 1500,
        },
        {
          text: "This is what makes it work — disparate systems are unified into common data entities so that information is always relevant, contextual, and consistent, regardless of which system it originally came from.",
          delay: 3000,
        },
      ],
    },

    // ── Step 5: Query ──────────────────────────────────────────────────
    {
      id: 'maestra-nlq',
      phase: 'Query',
      title: 'Ask Anything',
      body: 'Natural language query interface — click a preset or type your own question.',
      page: 'nlq',
      messages: [
        {
          text: "This is the query interface. Click on any preset question, or type your own — plain English, no SQL required.",
          delay: 0,
        },
        {
          text: "Every answer is grounded in the unified data layer you just saw. Real data, real semantics, full traceability back to the source.",
          delay: 1200,
        },
      ],
    },

    // ── Step 6: Dashboard ──────────────────────────────────────────────
    {
      id: 'maestra-dashboard',
      phase: 'Dashboard',
      title: 'Live Dashboard',
      body: 'Persona-driven, interactive dashboards that adjust on the fly.',
      page: 'nlq',
      iframeMessage: {
        targetPage: 'nlq',
        payload: { action: 'navigateTo', tab: 'dashboard' },
      },
      messages: [
        {
          text: "This dashboard is persona-driven. What a CFO sees is different from what a VP of Sales or a data engineer sees — each view is tailored to the role.",
          delay: 0,
        },
        {
          text: "It's fully interactive. Click any chart to drill down, filter by time period, or switch between metrics. Everything adjusts on the fly.",
          delay: 1200,
        },
      ],
    },

    // ── Step 7: Reports / Convergence ──────────────────────────────────
    {
      id: 'maestra-reports',
      phase: 'Reports',
      title: 'Reporting Portal',
      body: 'M&A reporting portal powered by Convergence — pre-deal through post-merger.',
      page: 'nlq',
      iframeMessage: {
        targetPage: 'nlq',
        payload: { action: 'navigateTo', tab: 'reports' },
      },
      messages: [
        {
          text: "This is the reporting portal. Right now it reflects a demo of an acquisition — Meridian acquiring Cascadia.",
          delay: 0,
        },
        {
          text: "Our Convergence product creates an end-to-end M&A platform. Click on Combined to see everything — pre-deal analysis, due diligence, and post-merger integration.",
          delay: 1400,
        },
        {
          text: "You'll find cross-sell and upsell opportunities, normalized EBITDA with automated quality of earnings, and much more — all generated from the same unified data layer.",
          delay: 2800,
        },
      ],
    },
  ],
};
