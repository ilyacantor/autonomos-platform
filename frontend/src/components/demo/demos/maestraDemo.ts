import type { DemoDefinition } from '../demoTypes';

export const maestraDemo: DemoDefinition = {
  id: 'maestra-guided-tour',
  name: 'Maestra Guided Tour',
  description:
    'Investor-grade narrated walkthrough — Maestra walks you through live module UIs with AI-guided narration.',
  icon: '🎙️',
  layout: 'maestra',
  steps: [
    // ── Step 1: Introduction + Discovery ─────────────────────────────
    {
      id: 'maestra-discovery',
      phase: 'Discovery',
      title: 'Meet Maestra',
      body: 'Maestra introduces herself and the live environment you are about to explore.',
      page: 'discover',
      messages: [
        {
          text: "Hi, I'm Maestra — I'm the onboarding and engagement manager for autonomOS.",
          delay: 0,
        },
        {
          text: "I handle everything from initial discovery through deployment and ongoing customer development.",
          delay: 1200,
        },
        {
          text: "Think of me as the person who actually understands your enterprise before the first meeting — and keeps understanding it as things change.",
          delay: 2400,
        },
        {
          text: "Everything you're about to see is running live against synthetic data that represents a messy, realistic enterprise environment.",
          delay: 3800,
        },
        {
          text: "Our data farm generated tens of thousands of signals — ingesting over 400 raw assets and cataloging roughly 100 into structured records across 6 sources of record and 4 fabric planes.",
          delay: 5000,
        },
        {
          text: "Real conflicts, real naming mismatches, real hierarchy gaps. Nothing is hardcoded or staged.",
          delay: 6200,
        },
        {
          text: "I'm going to walk you through the full platform end to end — how we discover what's in your environment, map the connections, resolve the conflicts, and build a unified context layer that humans and AI agents can both query with confidence.",
          delay: 7600,
        },
        {
          text: "At the end, I'll give you a quick look at Convergence, our multi-entity product for M&A and post-merger integration — which I'm really excited about.",
          delay: 9000,
        },
        {
          text: "Let's start with what I found when I scanned this environment.",
          delay: 10200,
        },
      ],
    },

    // ── Step 2: Run Discovery + Handoff ────────────────────────────────
    {
      id: 'maestra-handoff',
      phase: 'Handoff',
      title: 'Catalog Handoff',
      body: 'Running discovery and handing the full catalog off to the connection engine.',
      page: 'discover',
      iframeMessages: [
        // First: switch to Console tab
        { targetPage: 'discover', payload: { action: 'switchToConsole' }, delay: 300 },
        // Then: trigger Run Discovery
        { targetPage: 'discover', payload: { action: 'runDiscovery' }, delay: 1500 },
        // Then: trigger Handoff to AAM (after discovery has time to complete)
        { targetPage: 'discover', payload: { action: 'triggerHandoff' }, delay: 25000 },
      ],
      messages: [
        {
          text: "Now I'm running a full discovery scan and building the catalog in real time. Watch the console — you'll see the pipeline execute.",
          delay: 0,
        },
        {
          text: "Once the catalog is complete, every system and data source is automatically handed off to the connection engine — ready to be mapped and wired up.",
          delay: 1200,
        },
      ],
    },

    // ── Step 3: Connection Mapping ─────────────────────────────────────
    {
      id: 'maestra-connection',
      phase: 'Connection',
      title: 'Connection Mapping',
      body: 'Visual topology of every connection between your systems.',
      page: 'connect',
      messages: [
        {
          text: "This is the topology view — a visual map of every connection between your systems.",
          delay: 0,
        },
        {
          text: "The platform mapped all of these automatically from the catalog handoff. You're looking at over a hundred active connections.",
          delay: 1200,
        },
        {
          text: "Click any object in the visual to see details — source, destination, and what kind of data travels through it.",
          delay: 2400,
        },
      ],
    },

    // ── Step 4: Semantic Layer ──────────────────────────────────────────
    {
      id: 'maestra-semantic',
      phase: 'Semantic Layer',
      title: 'Unified Data Model',
      body: 'Context graph showing how source systems map into common business concepts.',
      page: 'unify-ask',
      messages: [
        {
          text: "This is the context graph. On the left side is the pipeline from AAM — the mapped connections you just saw. On the right side are unified business concepts like Revenue, Customer, and Product.",
          delay: 0,
        },
        {
          text: "Each node is a data entity. The lines between them show how metadata from each source system gets mapped into those common concepts.",
          delay: 1500,
        },
        {
          text: "This graph represents the actual unification of the various metadata concepts issued by often disparate systems — so that information is always relevant, contextual, and consistent, regardless of where it originally came from.",
          delay: 3000,
        },
        {
          text: "The unified data entities are then available to humans and agents to consume — without risk of hallucinations.",
          delay: 4500,
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
      iframeMessage: {
        targetPage: 'nlq',
        payload: { action: 'navigateTo', tab: 'galaxy' },
      },
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

    // ── Step 7: Reports / Convergence — Combined ───────────────────────
    {
      id: 'maestra-reports',
      phase: 'Reports',
      title: 'Reporting Portal',
      body: 'M&A reporting portal powered by Convergence — pre-deal through post-merger.',
      page: 'nlq',
      iframeMessage: {
        targetPage: 'nlq',
        payload: { action: 'reportNavigate', entity: 'combined', tab: 'crosssell' },
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
          text: "Click through the tabs — Cross-Sell for revenue synergy opportunities, EBITDA Bridge for normalized earnings, What-If for sensitivity analysis, and QofE for automated quality of earnings.",
          delay: 2800,
        },
      ],
    },

    // ── Step 8: Maestra Onboarding — Demo Conclusion ───────────────────
    {
      id: 'maestra-onboarding',
      phase: 'Maestra',
      title: 'Onboarding Portal',
      body: 'Maestra AI onboarding — start an engagement and explore the deal.',
      page: 'nlq',
      iframeMessage: {
        targetPage: 'nlq',
        payload: { action: 'reportNavigate', entity: 'combined', tab: 'maestra' },
      },
      messages: [
        {
          text: "And this is my onboarding portal. This is where every new engagement starts.",
          delay: 0,
        },
        {
          text: "Click Start Engagement, then in the chat click 'Tell me about the deal' — I'll walk you through everything I know about the Meridian-Cascadia acquisition.",
          delay: 1400,
        },
        {
          text: "This concludes the guided tour. Everything you've seen — discovery, connection mapping, semantic unification, natural language query, dashboards, and M&A reporting — is one integrated platform.",
          delay: 3000,
        },
      ],
    },
  ],
};
