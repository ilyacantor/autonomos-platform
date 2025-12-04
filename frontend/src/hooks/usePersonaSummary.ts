import { useState, useEffect } from 'react';
import type { PersonaSlug, PersonaSummaryResponse } from '../types/persona';

export function usePersonaSummary(slug: PersonaSlug) {
  const [data, setData] = useState<PersonaSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    async function fetchSummary() {
      setLoading(true);
      setError(null);
      
      try {
        const token = localStorage.getItem('token');
        const response = await fetch(`/nlp/v1/persona/summary?persona=${slug}`, {
          method: 'GET',
          headers: {
            'Authorization': token ? `Bearer ${token}` : '',
            'Content-Type': 'application/json'
          }
        });

        if (!response.ok) {
          throw new Error(`Failed to fetch persona summary: ${response.statusText}`);
        }

        const result = await response.json();
        
        if (mounted) {
          setData(result);
        }
      } catch (err) {
        if (mounted) {
          setError(err instanceof Error ? err.message : 'Unknown error');
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    fetchSummary();

    return () => {
      mounted = false;
    };
  }, [slug]);

  return { data, loading, error };
}
