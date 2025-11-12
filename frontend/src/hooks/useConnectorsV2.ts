/**
 * useConnectorsV2 - Typed hook for AAM connectors with OpenAPI contract
 * 
 * Feature flag: VITE_CONNECTIONS_V2 (default: false)
 * Set to 'true' to use the generated TypeScript client with drift metadata
 */

import { useState, useEffect } from 'react';
import { API_CONFIG, AUTH_TOKEN_KEY } from '../config/api';
import type { ConnectorDTO, ConnectorsResponse } from '../api/generated/connectors';
import { fetchConnectors } from '../api/generated/connectors';

interface UseConnectorsV2Result {
  connectors: ConnectorDTO[];
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

/**
 * Hook to fetch connectors using the OpenAPI-generated client
 * Includes drift metadata: last_event_type, last_event_at, has_drift
 */
export function useConnectorsV2(): UseConnectorsV2Result {
  const [connectors, setConnectors] = useState<ConnectorDTO[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);

    try {
      const token = localStorage.getItem(AUTH_TOKEN_KEY);
      if (!token) {
        setConnectors([]);
        setLoading(false);
        return;
      }

      const response: ConnectorsResponse = await fetchConnectors(API_CONFIG.BASE_URL, token);
      setConnectors(response.connectors || []);
    } catch (err: any) {
      console.error('Error fetching connectors (v2):', err);
      setError(err.message || 'Failed to load connectors');
      setConnectors([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  return {
    connectors,
    loading,
    error,
    refetch: fetchData,
  };
}
