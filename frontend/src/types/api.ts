/**
 * API Response Type Definitions
 *
 * Defines types for all API responses across the application including:
 * - NLP Gateway responses
 * - Authentication responses
 * - Discovery API responses
 * - Error responses
 */

/**
 * Generic API response wrapper
 */
export interface APIResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: APIError;
  timestamp?: string;
}

/**
 * API error structure
 */
export interface APIError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
  stack?: string;
}

/**
 * NLP Gateway query match
 */
export interface NLPMatch {
  title: string;
  content: string;
  score: number;
  section: string;
  metadata?: Record<string, unknown>;
}

/**
 * NLP Gateway query response
 */
export interface NLPQueryResponse {
  response?: string;
  matches?: NLPMatch[];
  trace_id?: string;
  resolved_persona?: string;
  timestamp?: string;
}

/**
 * Authentication login response
 */
export interface AuthLoginResponse {
  success: boolean;
  token: string;
  user: UserInfo;
  expires_at: string;
}

/**
 * Authentication register response
 */
export interface AuthRegisterResponse {
  success: boolean;
  token: string;
  user: UserInfo;
  expires_at: string;
}

/**
 * User information
 */
export interface UserInfo {
  id: string;
  name: string;
  email: string;
  persona?: string;
  created_at?: string;
}

/**
 * Discovered entity from discovery API
 */
export interface DiscoveredEntity {
  entity_id: string;
  entity_type: string;
  entity_name: string;
  source_system: string;
  source_schema?: string;
  confidence_score: number;
  confidence_level: 'high' | 'medium' | 'low' | 'very_low';
  attributes: Record<string, unknown>;
  metadata: Record<string, unknown>;
}

/**
 * Agent recommendation from discovery API
 */
export interface AgentRecommendation {
  agent_name: string;
  agent_type: string;
  reason: string;
  confidence_score: number;
  suggested_actions: string[];
  priority: 'high' | 'medium' | 'low';
}

/**
 * Discovery provenance metadata
 */
export interface DiscoveryProvenance {
  discovery_method: 'llm' | 'rag' | 'heuristic' | 'hybrid';
  llm_model?: string;
  rag_sources: string[];
  processing_time_ms: number;
  timestamp: string;
  human_review_required: boolean;
  review_reason?: string;
}

/**
 * Discovery API response
 */
export interface DiscoveryResponse {
  success: boolean;
  request_id: string;
  entities: DiscoveredEntity[];
  agent_recommendations: AgentRecommendation[];
  provenance: DiscoveryProvenance;
  total_entities_found: number;
  filtered_count: number;
  overall_confidence: number;
  quality_issues: string[];
  errors: string[];
  warnings: string[];
  timestamp: string;
}

/**
 * Connector information
 */
export interface ConnectorInfo {
  id: string;
  name: string;
  type: string;
  status: 'connected' | 'disconnected' | 'syncing' | 'error';
  last_sync?: string;
  error_message?: string;
  metadata?: Record<string, unknown>;
}

/**
 * Connector list response
 */
export interface ConnectorsResponse {
  connectors: ConnectorInfo[];
  total: number;
  timestamp?: string;
}

/**
 * Generic list response with pagination
 */
export interface ListResponse<T> {
  items: T[];
  total: number;
  page?: number;
  page_size?: number;
  has_more?: boolean;
}

/**
 * Health check response
 */
export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  services: Record<string, ServiceHealth>;
  timestamp: string;
}

/**
 * Service health status
 */
export interface ServiceHealth {
  status: 'up' | 'down' | 'degraded';
  latency_ms?: number;
  error?: string;
  last_check?: string;
}

/**
 * Validation error detail
 */
export interface ValidationError {
  field: string;
  message: string;
  code?: string;
}

/**
 * API error response with validation details
 */
export interface ErrorResponse {
  success: false;
  error: {
    code: string;
    message: string;
    validation_errors?: ValidationError[];
    details?: Record<string, unknown>;
  };
  timestamp: string;
}
