/**
 * useAsyncData - Generic hook for one-time async data fetching
 *
 * Provides a standardized pattern for:
 * - Initial data fetch on mount
 * - Loading and error state management
 * - Manual refresh capability
 * - Optional automatic refetch on dependency changes
 */

import { useEffect, useState, useCallback, useRef } from 'react';

export interface UseAsyncDataOptions {
  /** Whether to fetch immediately on mount (default: true) */
  immediate?: boolean;
  /** Whether to keep showing stale data when a refresh fails (default: true) */
  keepStaleOnError?: boolean;
}

export interface UseAsyncDataResult<T> {
  /** The fetched data, or null if not yet loaded */
  data: T | null;
  /** True while fetching data */
  loading: boolean;
  /** Error message if the fetch failed, null otherwise */
  error: string | null;
  /** Manually trigger a data fetch/refresh */
  refresh: () => Promise<void>;
  /** Reset the state to initial values */
  reset: () => void;
}

/**
 * Hook for fetching data once (with optional manual refresh)
 *
 * @param fetchFn - Async function that fetches the data
 * @param deps - Optional dependency array that triggers a refetch when changed
 * @param options - Additional configuration options
 * @returns Object containing data, loading state, error, refresh function, and reset function
 *
 * @example
 * ```tsx
 * // Basic usage
 * const { data, loading, error, refresh } = useAsyncData(
 *   () => fetchUserProfile(userId),
 *   [userId]
 * );
 *
 * // Deferred fetch
 * const { data, loading, refresh } = useAsyncData(
 *   () => searchUsers(query),
 *   [],
 *   { immediate: false }
 * );
 * // Later: refresh() to trigger the fetch
 * ```
 */
export function useAsyncData<T>(
  fetchFn: () => Promise<T>,
  deps: any[] = [],
  options: UseAsyncDataOptions = {}
): UseAsyncDataResult<T> {
  const { immediate = true, keepStaleOnError = true } = options;

  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(immediate);
  const [error, setError] = useState<string | null>(null);

  // Use ref to track if component is mounted
  const mountedRef = useRef(true);
  // Store the latest fetchFn to avoid stale closures
  const fetchFnRef = useRef(fetchFn);
  fetchFnRef.current = fetchFn;
  // Track if initial fetch has been done
  const initialFetchDone = useRef(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await fetchFnRef.current();
      if (mountedRef.current) {
        setData(result);
        setError(null);
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

  const reset = useCallback(() => {
    setData(null);
    setLoading(false);
    setError(null);
    initialFetchDone.current = false;
  }, []);

  useEffect(() => {
    mountedRef.current = true;

    // If immediate is true, fetch on mount and when deps change
    // If immediate is false, only fetch on deps change after initial mount
    if (immediate || initialFetchDone.current) {
      loadData();
      initialFetchDone.current = true;
    }

    return () => {
      mountedRef.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loadData, immediate, ...deps]);

  const refresh = useCallback(async () => {
    await loadData();
    initialFetchDone.current = true;
  }, [loadData]);

  return {
    data,
    loading,
    error,
    refresh,
    reset,
  };
}

export default useAsyncData;
