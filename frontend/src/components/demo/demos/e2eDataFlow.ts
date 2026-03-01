import type { DemoDefinition } from '../demoTypes';

// ── AAM base URL (must match IFRAME_PAGES in App.tsx) ────────────────
const AAM_BASE = 'https://aos-aam.onrender.com';

export const e2eDataFlowDemo: DemoDefinition = {
  id: 'e2e-data-flow',
  name: 'E2E Data Flow',
  description: 'Walk through the full AutonomOS pipeline — from asset discovery to natural language querying.',
  icon: '🔄',
  steps: [
    // ── Phase 1: AOD Discovery ───────────────────────────────────────
    {
      id: 'aod-discovery-start',
      phase: 'AOD Discovery',
      title: 'Discovering Enterprise Assets',
      body: 'AOS Discover performs deep discovery across 7 observation planes, building a comprehensive IT asset catalog. The Console shows real-time discovery activity and observation sources.',
      page: 'discover',
      iframeMessage: {
        targetPage: 'discover',
        payload: { action: 'switchToConsole' },
      },
      apiTrigger: {
        path: '/aoa/demo-scan',
        method: 'POST',
      },
      blocksOnApi: false,
    },
    {
      id: 'aod-discovery-complete',
      phase: 'AOD Discovery',
      title: 'Discovery Complete',
      body: 'The catalog shows all discovered IT assets with classification, governance status, and confidence scores. You can view as-is or perform asset-level triage.',
      page: 'discover',
      iframeMessage: {
        targetPage: 'discover',
        payload: { action: 'switchToConsole' },
      },
    },

    // ── Phase 2: Triage & Handoff ────────────────────────────────────
    {
      id: 'triage-start',
      phase: 'Triage & Handoff',
      title: 'Asset Triage',
      body: 'Click the Triage tab above to see asset classification. Each asset is evaluated as a System of Record, Fabric Plane, or connectivity target — with governance readiness and data quality scores.',
      page: 'discover',
    },
    {
      id: 'triage-handoff',
      phase: 'Triage & Handoff',
      title: 'Handoff to AAM',
      body: 'Click the Handoff tab to see the export summary. The triaged catalog identifies Systems of Record, Fabric Planes, and connectivity patterns — curated assets ready to export to AAM.',
      page: 'discover',
    },

    // ── Phase 3: AAM Connection ──────────────────────────────────────
    {
      id: 'aam-receives',
      phase: 'AAM Connection',
      title: 'AAM Receives Curated Assets',
      body: 'AAM receives the curated catalog and begins provisioning — validating credentials, discovering schemas, and establishing fabric plane connectivity.',
      page: 'connect',
      iframeSrc: `${AAM_BASE}/ui/topology`,
    },
    {
      id: 'aam-candidates',
      phase: 'AAM Connection',
      title: 'Exploring: Candidates',
      body: 'Connection candidates are evaluated for schema compatibility, credential validity, and risk posture before admission.',
      page: 'connect',
      iframeSrc: `${AAM_BASE}/ui/candidates`,
    },
    {
      id: 'aam-declared-pipes',
      phase: 'AAM Connection',
      title: 'Exploring: Declared Pipes',
      body: 'Logical channels between systems — each defines source, destination, schema contract, and transport modality.',
      page: 'connect',
      iframeSrc: `${AAM_BASE}/ui/pipes`,
    },
    {
      id: 'aam-topology',
      phase: 'AAM Connection',
      title: 'Topology & Dispatch',
      body: 'The full connectivity mesh — active connections, healing connections, and dispatch details showing real-time provisioning activity.',
      page: 'connect',
      iframeSrc: `${AAM_BASE}/ui/topology`,
    },
    {
      id: 'aam-pipeline-complete',
      phase: 'AAM Connection',
      title: 'Pipeline Complete',
      body: 'Provisioned data structures are now transferring to DCL for semantic intelligence. All connections validated and schemas discovered.',
      page: 'connect',
      iframeSrc: `${AAM_BASE}/ui/topology`,
    },

    // ── Phase 4: DCL Unification ─────────────────────────────────────
    {
      id: 'dcl-unification',
      phase: 'DCL Unification',
      title: 'Data Normalized & Unified',
      body: 'The unified data layer has received provisioned pipes, Systems of Record, and fabric planes — normalized, unified, contextualized, ready for humans and agents.',
      page: 'unify-ask',
    },

    // ── Phase 5: NLQ ─────────────────────────────────────────────────
    {
      id: 'nlq-access',
      phase: 'NLQ',
      title: 'Query Your Unified Data',
      body: 'The unified data layer is accessible through Natural Language Query. Ask questions in plain English, grounded in cataloged, triaged, and verified enterprise data.',
      page: 'nlq',
    },

    // ── Complete ─────────────────────────────────────────────────────
    {
      id: 'demo-complete',
      phase: 'Complete',
      title: 'Full Pipeline Demonstrated',
      body: 'Full AutonomOS pipeline demonstrated — from raw asset discovery through intelligent data unification to natural language access.',
      page: 'nlq',
    },
  ],
};
