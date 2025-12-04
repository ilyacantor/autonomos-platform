/**
 * Generated TypeScript client for /api/v1/aam/connectors
 * Based on OpenAPI ConnectorDTO schema
 * 
 * To regenerate:
 * 1. Ensure backend is running
 * 2. Fetch http://localhost:5000/openapi.json
 * 3. Update types below to match ConnectorDTO schema
 */

export interface ConnectorDTO {
  /** Unique connector identifier */
  id: string;
  /** Connector name */
  name: string;
  /** Data source type (e.g., salesforce, filesource) */
  source_type: string;
  /** Connection status (ACTIVE, PENDING, FAILED, etc.) */
  status: string;
  /** Number of field mappings for this connector */
  mapping_count: number;
  /** Type of last drift event (e.g., DRIFT_DETECTED) */
  last_event_type?: string | null;
  /** Timestamp of last drift event */
  last_event_at?: string | null;
  /** Whether connector has detected drift */
  has_drift: boolean;
}

export interface ConnectorsResponse {
  /** List of connectors */
  connectors: ConnectorDTO[];
  /** Total number of connectors */
  total: number;
}

export interface ConnectorsError {
  detail: string;
}

/**
 * Typed fetch wrapper for GET /api/v1/aam/connectors
 */
export async function fetchConnectors(
  baseUrl: string,
  token: string
): Promise<ConnectorsResponse> {
  const response = await fetch(`${baseUrl}/api/v1/aam/connectors`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (response.status === 401) {
    throw new Error('Unauthorized: Invalid or missing authentication token');
  }

  if (!response.ok) {
    const error: ConnectorsError = await response.json();
    throw new Error(error.detail || 'Failed to fetch connectors');
  }

  const data: ConnectorsResponse = await response.json();
  return data;
}
