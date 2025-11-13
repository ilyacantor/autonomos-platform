/**
 * DCL (Data Connectivity Layer) Type Definitions
 *
 * Defines all types related to the DCL engine including:
 * - State management
 * - Graph structures
 * - RAG (Retrieval Augmented Generation) context
 * - LLM statistics
 * - Preview data
 */

/**
 * Represents a RAG retrieval result for field mappings
 */
export interface RAGRetrieval {
  source_field: string;
  ontology_entity: string;
  similarity: number;
}

/**
 * RAG context for tracking retrievals and mappings
 */
export interface RAGContext {
  retrievals: RAGRetrieval[];
  total_mappings: number;
  last_retrieval_count: number;
  mappings_retrieved?: number;
}

/**
 * LLM usage statistics
 */
export interface LLMStats {
  calls: number;
  tokens: number;
  calls_saved?: number;
}

/**
 * Field mapping from source to ontology
 */
export interface FieldMapping {
  source: string;
  onto_field: string;
  confidence?: number;
}

/**
 * Data source information
 */
export interface SourceInfo {
  id: string;
  name: string;
  type: string;
  schema?: SourceSchema;
  fields?: string[];
  status?: 'online' | 'offline' | 'syncing';
}

/**
 * Source schema definition
 */
export interface SourceSchema {
  tables?: Record<string, TableSchema>;
  fields?: string[];
  metadata?: Record<string, unknown>;
}

/**
 * Table schema definition
 */
export interface TableSchema {
  fields: string[];
  primary_key?: string;
  metadata?: Record<string, unknown>;
}

/**
 * Agent information
 */
export interface AgentInfo {
  id: string;
  name: string;
  type: string;
  consuming_entities?: string[];
  status?: 'active' | 'inactive' | 'error';
}

/**
 * Ontology entity definition
 */
export interface OntologyEntity {
  id: string;
  name: string;
  fields: string[];
  sources?: string[];
}

/**
 * Connection information for data sources
 */
export interface ConnectionInfo {
  source_id: string;
  connector_type: string;
  status: 'connected' | 'disconnected' | 'error';
  last_sync?: string;
  error_message?: string;
}

/**
 * Preview data for DCL state visualization
 */
export interface PreviewData {
  sources: Record<string, SourceInfo>;
  ontology: Record<string, OntologyEntity>;
  connectionInfo: ConnectionInfo | null;
}

/**
 * Complete DCL state
 */
export interface DCLState {
  events: string[];
  graph: Graph;
  llm: LLMStats;
  preview: PreviewData;
  rag: RAGContext;
  selected_sources: string[];
  selected_agents: string[];
  dev_mode: boolean;
  blended_confidence?: number | null;
}

/**
 * Graph node representation
 */
export interface GraphNode {
  id: string;
  label: string;
  type: 'source_parent' | 'source' | 'ontology' | 'agent';
  fields?: string[];
  sourceSystem?: string;
  parentId?: string;
}

/**
 * Graph edge representation
 */
export interface GraphEdge {
  source: string;
  target: string;
  label?: string;
  edgeType?: 'hierarchy' | 'dataflow';
  edge_type?: 'hierarchy' | 'dataflow';
  field_mappings?: FieldMapping[];
  entity_fields?: string[];
  entity_name?: string;
}

/**
 * Graph structure containing nodes and edges
 */
export interface Graph {
  nodes: GraphNode[];
  edges: GraphEdge[];
  confidence?: number | null;
  last_updated?: string | null;
}

/**
 * WebSocket message structure for DCL state updates
 */
export interface DCLWebSocketMessage {
  type: 'state_update' | 'rag_coverage_check' | 'mapping_progress' | 'error';
  timestamp: number;
  data?: DCLWebSocketData;
  // RAG coverage check specific fields
  source?: string;
  coverage_pct?: number;
  matched_count?: number;
  total_count?: number;
  recommendation?: 'skip' | 'proceed';
  estimated_cost_savings?: number;
  missing_fields?: string[];
  message?: string;
}

/**
 * WebSocket data payload
 */
export interface DCLWebSocketData {
  sources: string[];
  agents: string[];
  devMode: boolean;
  graph: Graph;
  llmCalls: number;
  llmTokens: number;
  llmCallsSaved?: number;
  ragContext: RAGContext;
  events?: string[];
  blendedConfidence?: number;
  entitySources?: Record<string, string[]>;
  sourceSchemas?: Record<string, SourceSchema>;
  agentConsumption?: Record<string, string[]>;
}

/**
 * DCL API response types
 */
export interface DCLConnectResponse {
  success: boolean;
  message: string;
  sources: string[];
  agents: string[];
  graph?: Graph;
}

export interface DCLToggleDevModeResponse {
  success: boolean;
  dev_mode: boolean;
  message: string;
}

export interface DCLStateResponse extends DCLState {
  timestamp?: string;
}

/**
 * DCL event types for custom events
 */
export type DCLEventType =
  | 'new_source'
  | 'source_removed'
  | 'fault'
  | 'schema_drift'
  | 'mapping_updated'
  | 'agent_added'
  | 'agent_removed';

/**
 * DCL graph event detail
 */
export interface DCLGraphEventDetail {
  type: DCLEventType;
  sourceId?: string;
  targetId?: string;
  timestamp?: number;
  metadata?: Record<string, unknown>;
}
