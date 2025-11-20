export interface Connector {
  connector_id: string;
  service_id: string;
  tenant_id: string;
  auth_type: string;
  base_url: string;
}

export interface Workflow {
  workflow_id: string;
  workflow_type: string;
  connector_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  start_time?: string;
  end_time?: string;
  result?: any;
  error?: string;
}

export interface MetricsSummary {
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  avg_latency_ms: number;
  by_status: Record<string, number>;
  by_service: Record<string, ServiceStats>;
  error_breakdown: Record<string, number>;
  dlq_stats?: DLQStats;
  rate_limiter_stats?: Record<string, RateLimiterStats>;
}

export interface ServiceStats {
  total: number;
  success: number;
  errors: number;
  avg_latency: number;
}

export interface DLQStats {
  pending: number;
  processed: number;
  failed: number;
}

export interface RateLimiterStats {
  tokens_available: number;
  capacity: number;
  consecutive_errors: number;
  in_backoff: boolean;
  backoff_until?: number;
}

export interface Metrics {
  connectors: number;
  metrics_summary: MetricsSummary;
  dlq_stats: DLQStats;
  workflows: {
    running: number;
    completed: number;
    failed: number;
  };
}

export interface WorkflowRequest {
  connector_id: string;
  workflow_type: 'high_volume' | 'idempotent_write' | 'drift_sensitive' | 'drift_monitor';
  duration_seconds?: number;
  params?: Record<string, any>;
}

export interface ScenarioRequest {
  mode: 'mild' | 'storm' | 'hell';
  duration_seconds: number;
  connectors: string[];
}

export interface CreateConnectorRequest {
  service_id: string;
  tenant_id: string;
  base_url?: string;
  auth_type?: string;
  client_id?: string;
  client_secret?: string;
  api_key?: string;
}
