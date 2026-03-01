import { useEffect, useRef } from 'react';
import { useDemo } from '../../contexts/DemoContext';
import { API_CONFIG, AUTH_TOKEN_KEY } from '../../config/api';

// ── DemoRunner: invisible orchestrator for navigation + API triggers ─

interface DemoRunnerProps {
  onNavigate: (page: string) => void;
}

export default function DemoRunner({ onNavigate }: DemoRunnerProps) {
  const {
    status,
    activeDemo,
    currentStepIndex,
    setStepResult,
    setApiLoading,
    setApiError,
    setPipelineJobId,
  } = useDemo();

  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // ── Helpers ──────────────────────────────────────────────────────
  const getAuthHeaders = (): Record<string, string> => {
    const token = localStorage.getItem(AUTH_TOKEN_KEY);
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    return headers;
  };

  const hasAuthToken = (): boolean => {
    return !!localStorage.getItem(AUTH_TOKEN_KEY);
  };

  const cleanup = () => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
  };

  /** Send a postMessage into a specific iframe by page key */
  const sendIframeMessage = (targetPage: string, payload: Record<string, unknown>) => {
    const iframes = document.querySelectorAll('iframe');
    for (const iframe of iframes) {
      // Match iframe by checking if its parent container is visible
      const container = iframe.closest('[style]');
      if (container && (container as HTMLElement).style.display !== 'none') {
        try {
          iframe.contentWindow?.postMessage(payload, '*');
          console.log(`[DemoRunner] postMessage to ${targetPage} →`, payload);
        } catch (err) {
          console.warn('[DemoRunner] postMessage failed:', err);
        }
        return;
      }
    }
    console.warn(`[DemoRunner] No visible iframe found for ${targetPage}`);
  };

  /** Change an iframe's src URL by page key */
  const changeIframeSrc = (targetPage: string, newSrc: string) => {
    // Find all iframes, match the one in the container for targetPage
    const containers = document.querySelectorAll('[style*="display"]');
    // The iframes are in div[key=pageKey] containers; find by iterating
    const allIframes = document.querySelectorAll('iframe');
    for (const iframe of allIframes) {
      const parentDiv = iframe.closest('div.h-full');
      if (parentDiv) {
        // Check the iframe's current src to identify which page it belongs to
        const currentSrc = iframe.getAttribute('src') || iframe.src;
        // For the connect page, match on AAM URL
        if (targetPage === 'connect' && currentSrc.includes('aos-aam')) {
          if (iframe.src !== newSrc) {
            console.log(`[DemoRunner] Changing iframe src: ${currentSrc} → ${newSrc}`);
            iframe.src = newSrc;
          }
          return;
        }
      }
    }
    console.warn(`[DemoRunner] No iframe found for page "${targetPage}" to change src`);
  };

  // ── Main effect: react to step changes ──────────────────────────
  useEffect(() => {
    if (status !== 'running' || !activeDemo) return;

    const step = activeDemo.steps[currentStepIndex];
    if (!step) return;

    // Navigate to the target page
    onNavigate(step.page);
    window.history.pushState({}, '', `/${step.page}`);

    // Change iframe src if specified (e.g. AAM sub-routes)
    if (step.iframeSrc) {
      // Small delay to ensure the page container is visible before changing src
      setTimeout(() => changeIframeSrc(step.page, step.iframeSrc!), 100);
    }

    // Send postMessage to iframe if specified (e.g. AOD tab switching)
    if (step.iframeMessage) {
      // Small delay to ensure iframe is visible and ready
      setTimeout(() => {
        sendIframeMessage(step.iframeMessage!.targetPage, step.iframeMessage!.payload);
      }, 300);
    }

    // Fire API trigger if present AND we have an auth token
    if (step.apiTrigger) {
      if (!hasAuthToken()) {
        console.log(`[DemoRunner] Skipping API ${step.apiTrigger.method} ${step.apiTrigger.path} — no auth token`);
        return;
      }

      cleanup();
      const controller = new AbortController();
      abortRef.current = controller;

      const { path, method, pollForCompletion } = step.apiTrigger;
      const url = API_CONFIG.buildApiUrl(path);

      setApiLoading(true);
      setApiError(null);

      fetch(url, {
        method,
        headers: getAuthHeaders(),
        signal: controller.signal,
      })
        .then(async (res) => {
          if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: 'Request failed' }));
            throw new Error(err.detail || `HTTP ${res.status}`);
          }
          return res.json();
        })
        .then((data) => {
          console.log(`[DemoRunner] API ${method} ${path} →`, data);
          setStepResult(step.id, data);

          // If polling is configured, start polling
          if (pollForCompletion && data.job_id) {
            setPipelineJobId(data.job_id);
            const startTime = Date.now();
            const { statusPath, intervalMs, timeoutMs } = pollForCompletion;

            pollIntervalRef.current = setInterval(async () => {
              try {
                // Timeout check
                if (Date.now() - startTime > timeoutMs) {
                  cleanup();
                  setApiLoading(false);
                  console.log('[DemoRunner] Poll timeout — continuing');
                  return;
                }

                const statusUrl = `${API_CONFIG.buildApiUrl(statusPath)}?job_id=${data.job_id}`;
                const statusRes = await fetch(statusUrl, { headers: getAuthHeaders() });
                if (!statusRes.ok) return; // Retry on next interval

                const statusData = await statusRes.json();
                console.log('[DemoRunner] Poll status →', statusData);

                if (statusData.status === 'completed' || statusData.status === 'done') {
                  cleanup();
                  setStepResult(step.id, statusData);
                  setApiLoading(false);
                }
              } catch (err) {
                // Silently retry on poll errors
                console.warn('[DemoRunner] Poll error:', err);
              }
            }, intervalMs);
          } else {
            // Fire-and-forget — mark complete immediately
            setApiLoading(false);
          }
        })
        .catch((err) => {
          if (err.name === 'AbortError') return;
          console.warn('[DemoRunner] API error:', err);
          if (step.blocksOnApi) {
            setApiError(err.message || 'API request failed');
          } else {
            setApiLoading(false);
          }
        });
    }

    return cleanup;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, currentStepIndex]);

  // ── Cleanup on unmount or demo exit ─────────────────────────────
  useEffect(() => {
    return cleanup;
  }, []);

  // Invisible component — no rendered output
  return null;
}
