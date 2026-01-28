export type LiveStatus = 'live' | 'demo';

export interface LiveStatusConfig {
  status: LiveStatus;
  tooltip?: string;
}

export const liveStatusRegistry: Record<string, LiveStatusConfig> = {
  'nlp-gateway': {
    status: 'live',
    tooltip: 'Connected to backend NLP services with real-time API responses'
  },
  'aam-monitor': {
    status: 'live',
    tooltip: 'Live AAM metrics from backend connectors and event streams'
  },
  'aam-connections': {
    status: 'live',
    tooltip: 'Real-time connection status from backend AAM service'
  },
  'aam-events': {
    status: 'live',
    tooltip: 'Live event stream from AAM monitoring'
  },
  'aam-intelligence': {
    status: 'live',
    tooltip: 'Real-time drift detection and repair metrics from AAM'
  },
  'dcl-graph': {
    status: 'live',
    tooltip: 'Live unified ontology from backend DCL engine'
  },
  'dcl-sankey': {
    status: 'live',
    tooltip: 'Real-time data flow visualization from DCL materialized views'
  },
  'aod-dashboard': {
    status: 'live',
    tooltip: 'Live external AOD Dashboard (discover.autonomos.software)'
  },
  'finops-agent': {
    status: 'live',
    tooltip: 'Live FinOps agent demo (axiom-finops-demo.replit.app)'
  },
  'revops-agent': {
    status: 'live',
    tooltip: 'Live RevOps agent demo (autonomos-dcl-light.replit.app)'
  },
  'aoa-status': {
    status: 'demo',
    tooltip: 'Simulated orchestration metrics with client-side animations'
  },
  'agent-performance': {
    status: 'demo',
    tooltip: 'Mock agent performance data for demonstration purposes'
  },
  'xao-metrics': {
    status: 'demo',
    tooltip: 'Demo cross-agentic orchestration metrics'
  },
  'hitl-queue': {
    status: 'demo',
    tooltip: 'Static demonstration data for HITL workflow'
  },
  'discover-stats': {
    status: 'demo',
    tooltip: 'Fixed demo statistics for asset discovery pipeline'
  },
  'discover-pipeline': {
    status: 'demo',
    tooltip: 'Demo pipeline metrics showing typical processing flow'
  },
  'discover-triage': {
    status: 'demo',
    tooltip: 'Example HITL triage categories with static counts'
  },
  'discover-catalog': {
    status: 'demo',
    tooltip: 'Sample catalogued inventory data'
  },
  'discover-action-log': {
    status: 'demo',
    tooltip: 'Demo automated action log with sample events'
  },
};

export function getLiveStatus(componentId: string): LiveStatusConfig | undefined {
  return liveStatusRegistry[componentId];
}
