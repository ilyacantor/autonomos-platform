// ── Demo System Shared Types ──────────────────────────────────────────

/** API trigger attached to a demo step */
export interface DemoStepApiTrigger {
  /** API path (appended to /api/v1) */
  path: string;
  method: 'GET' | 'POST' | 'PUT' | 'DELETE';
  /** If set, the runner will poll a status endpoint until completion */
  pollForCompletion?: {
    /** Path to poll for status (receives job_id as query param) */
    statusPath: string;
    /** Polling interval in milliseconds */
    intervalMs: number;
    /** Max time before giving up */
    timeoutMs: number;
  };
}

/** postMessage payload to send into an iframe */
export interface DemoIframeMessage {
  /** Page key whose iframe should receive the message */
  targetPage: string;
  /** The message payload (sent via postMessage) */
  payload: Record<string, unknown>;
}

/** A single step in a guided demo */
export interface DemoStep {
  id: string;
  phase: string;
  title: string;
  body: string;
  /** Target iframe/page key to navigate to */
  page: string;
  /** Override the iframe src URL for this step (e.g. AAM sub-route) */
  iframeSrc?: string;
  /** Optional postMessage to send into an iframe on this step */
  iframeMessage?: DemoIframeMessage;
  /** Optional API call to fire when entering this step */
  apiTrigger?: DemoStepApiTrigger;
  /** If true, Next button is disabled until the API trigger resolves */
  blocksOnApi?: boolean;
}

/** A complete demo definition */
export interface DemoDefinition {
  id: string;
  name: string;
  description: string;
  icon: string;
  steps: DemoStep[];
}

/** Runtime state for the demo system */
export interface DemoState {
  status: 'idle' | 'running' | 'completed';
  activeDemo: DemoDefinition | null;
  currentStepIndex: number;
  stepResults: Record<string, unknown>;
  isApiLoading: boolean;
  apiError: string | null;
  pipelineJobId: string | null;
}
