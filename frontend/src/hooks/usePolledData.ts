/**
 * usePolledData - Generic hook for fetching data with automatic polling
 *
 * Provides a standardized pattern for:
 * - Initial data fetch
 * - Automatic polling at configurable intervals
 * - Loading and error state management
 * - Manual refresh capability
 * - Stale data preservation on errors
 */

import { useEffect, useState, useCallback, useRef } from 'react';

export interface UsePolledDataOptions {
  /** Whether to keep showing stale data when a refresh fails (default: true) */
  keepStaleOnError?: boolean;
  /** Whether to start polling immediately (default: true) */
  enabled?: boolean;
}

export interface UsePolledDataResult<T> {
  /** The fetched data, or null if not yet loaded */
  data: T | null;
  /** True during the initial load (before any data is available) */
  loading: boolean;
  /** Error message if the last fetch failed, null otherwise */
  error: string | null;
  /** Timestamp of the last successful data fetch */
  lastUpdated: Date | null;
  /** Manually trigger a data refresh */
  refresh: () => void;
}

/**
 * Hook for fetching and polling data at regular intervals
 *
 * @param fetchFn - Async function that fetches the data
 * @param pollInterval - Polling interval in milliseconds
 * @param deps - Optional dependency array that triggers a refetch when changed
 * @param options - Additional configuration options
 * @returns Object containing data, loading state, error, lastUpdated timestamp, and refresh function
 *
 * @example
 * ```tsx
 * const { data, loading, error, refresh } = usePolledData(
 *   () => fetchVitals(),
 *   10000, // Poll every 10 seconds
 *   [userId] // Refetch when userId changes
 * );
 * ```
 */
export function usePolledData<T>(
  fetchFn: () => Promise<T>,
  pollInterval: number,
  deps: any[] = [],
  options: UsePolledDataOptions = {}
): UsePolledDataResult<T> {
  const { keepStaleOnError = true, enabled = true } = options;

  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  // Use ref to track if component is mounted
  const mountedRef = useRef(true);
  // Store the latest fetchFn to avoid stale closures
  const fetchFnRef = useRef(fetchFn);
  fetchFnRef.current = fetchFn;

  const loadData = useCallback(async () => {
    try {
      const result = await fetchFnRef.current();
      if (mountedRef.current) {
        setData(result);
        setError(null);
        setLastUpdated(new Date());
      }
    } catch (err: any) {
      if (mountedRef.current) {
        setError(err.message || 'An error occurred');
        if (!keepStaleOnError) {
          setData(null);
        }
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [keepStaleOnError]);

  useEffect(() => {
    mountedRef.current = true;

    if (!enabled) {
      setLoading(false);
      return;
    }

    // Initial fetch
    loadData();

    // Set up polling
    const interval = setInterval(loadData, pollInterval);

    return () => {
      mountedRef.current = false;
      clearInterval(interval);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loadData, pollInterval, enabled, ...deps]);

  const refresh = useCallback(() => {
    loadData();
  }, [loadData]);

  return {
    data,
    loading,
    error,
    lastUpdated,
    refresh,
  };
}

export default usePolledData;
