import type { DemoDefinition } from '../demoTypes';

// ── AAM base URL (must match IFRAME_PAGES in App.tsx) ────────────────
const AAM_BASE = 'https://aos-aam.onrender.com';

export const e2eDataFlowDemo: DemoDefinition = {
  id: 'e2e-data-flow',
  name: 'E2E Data Flow',
  description: 'Run the full AutonomOS pipeline — discovery scan, triage, AAM provisioning, DCL unification, and NLQ access.',
  icon: '🔄',
  steps: [
    // ── Phase 1: Pipeline Trigger ────────────────────────────────────
    {
      id: 'pipeline-start',
      phase: 'Pipeline',
      title: 'Starting E2E Pipeline',
      body: 'Launching the full pipeline: AOD discovery scan → AAM handoff → pipe inference → DCL push. This triggers real API calls to each service. Progress updates below.',
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
    },

    // ── Phase 2: AOD Discovery ───────────────────────────────────────
    {
      id: 'aod-discovery-complete',
      phase: 'AOD Discovery',
      title: 'Discovery Scan Complete',
      body: 'The AOD scan ran against the latest Farm snapshot, discovering IT assets across 7 observation planes. The Console shows discovered assets with classification, governance status, and confidence scores.',
      page: 'discover',
      iframeMessage: {
        targetPage: 'discover',
        payload: { action: 'switchToConsole' },
      },
    },

    // ── Phase 3: Triage & Handoff ────────────────────────────────────
    {
      id: 'triage-view',
      phase: 'Triage & Handoff',
      title: 'Asset Triage',
      body: 'Click the Triage tab to see asset classification. Each asset is evaluated as a System of Record, Fabric Plane, or connectivity target — with governance readiness and data quality scores.',
      page: 'discover',
    },
    {
      id: 'handoff-view',
      phase: 'Triage & Handoff',
      title: 'Handoff to AAM',
      body: 'Click the Handoff tab to see the export summary. The pipeline already pushed these candidates to AAM — you can see the handoff log showing systems, fabric planes, and connection intent.',
      page: 'discover',
    },

    // ── Phase 4: AAM Connection ──────────────────────────────────────
    {
      id: 'aam-topology',
      phase: 'AAM Connection',
      title: 'Topology & Connections',
      body: 'AAM received the candidates and inferred pipe definitions. The topology view shows the full connectivity mesh — active connections, fabric planes, and dispatch status.',
      page: 'connect',
      iframeSrc: `${AAM_BASE}/ui/topology`,
    },
    {
      id: 'aam-candidates',
      phase: 'AAM Connection',
      title: 'Connection Candidates',
      body: 'Each connection candidate was evaluated for schema compatibility, credential validity, and risk posture. Candidates are matched to declared pipes or deferred for review.',
      page: 'connect',
      iframeSrc: `${AAM_BASE}/ui/candidates`,
    },
    {
      id: 'aam-declared-pipes',
      phase: 'AAM Connection',
      title: 'Declared Pipes',
      body: 'Logical channels between systems — each defines source, destination, schema contract, and transport modality. These pipes carry data from source systems to DCL.',
      page: 'connect',
      iframeSrc: `${AAM_BASE}/ui/pipes`,
    },

    // ── Phase 5: DCL Unification ─────────────────────────────────────
    {
      id: 'dcl-unification',
      phase: 'DCL Unification',
      title: 'Data Normalized & Unified',
      body: 'The pipeline pushed declared pipes to DCL. The unified data layer has received provisioned pipes, Systems of Record, and fabric planes — normalized, unified, contextualized.',
      page: 'unify-ask',
    },

    // ── Phase 6: NLQ ─────────────────────────────────────────────────
    {
      id: 'nlq-access',
      phase: 'NLQ',
      title: 'Query Your Unified Data',
      body: 'The unified data layer is accessible through Natural Language Query. Ask questions in plain English — grounded in cataloged, triaged, and verified enterprise data.',
      page: 'nlq',
    },

    // ── Complete ─────────────────────────────────────────────────────
    {
      id: 'demo-complete',
      phase: 'Complete',
      title: 'Full Pipeline Demonstrated',
      body: 'Full AutonomOS pipeline executed — real discovery scan, real AAM handoff, real pipe inference, real DCL push. From raw asset discovery to natural language access.',
      page: 'nlq',
    },
  ],
};
