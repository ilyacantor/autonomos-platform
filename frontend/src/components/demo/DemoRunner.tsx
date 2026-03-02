import { useEffect, useRef, useCallback } from 'react';
import { useDemo } from '../../contexts/DemoContext';
import { API_CONFIG } from '../../config/api';

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
  const pipelineCompleteRef = useRef(false);

  // ── Helpers ──────────────────────────────────────────────────────

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
    const allIframes = document.querySelectorAll('iframe');
    for (const iframe of allIframes) {
      const parentDiv = iframe.closest('div.h-full');
      if (parentDiv) {
        const currentSrc = iframe.getAttribute('src') || iframe.src;
        if (targetPage === 'connect' && currentSrc.includes('aos-aam')) {
          if (iframe.src !== newSrc) {
            console.log(`[DemoRunner] Changing iframe src → ${newSrc}`);
            iframe.src = newSrc;
          }
          return;
        }
      }
    }
    console.warn(`[DemoRunner] No iframe found for page "${targetPage}" to change src`);
  };

  /** Force-reload an iframe so it picks up fresh post-pipeline data */
  const reloadIframe = useCallback((targetPage: string) => {
    const iframes = document.querySelectorAll('iframe');
    for (const iframe of iframes) {
      const src = iframe.getAttribute('src') || '';
      if (
        (targetPage === 'discover' && src.includes('aodv3')) ||
        (targetPage === 'connect' && src.includes('aos-aam'))
      ) {
        const base = src.split('?')[0];
        iframe.src = base + '?refresh=' + Date.now();
        console.log(`[DemoRunner] Reloaded iframe for ${targetPage}`);
        return;
      }
    }
  }, []);

  // ── Main effect: react to step changes ──────────────────────────
  useEffect(() => {
    if (status !== 'running' || !activeDemo) return;

    const step = activeDemo.steps[currentStepIndex];
    if (!step) return;

    // Navigate to the target page
    onNavigate(step.page);
    window.history.pushState({}, '', `/${step.page}`);

    // After pipeline completes, reload iframes so they show fresh data
    if (pipelineCompleteRef.current && !step.apiTrigger) {
      setTimeout(() => reloadIframe(step.page), 200);
    }

    // Change iframe src if specified (e.g. AAM sub-routes)
    if (step.iframeSrc) {
      setTimeout(() => changeIframeSrc(step.page, step.iframeSrc!), 100);
    }

    // Send postMessage to iframe if specified (e.g. AOD tab switching)
    if (step.iframeMessage) {
      setTimeout(() => {
        sendIframeMessage(step.iframeMessage!.targetPage, step.iframeMessage!.payload);
      }, 300);
    }

    // Fire API trigger if present
    // Demo pipeline endpoints don't require auth — call them directly
    if (step.apiTrigger) {
      cleanup();
      const controller = new AbortController();
      abortRef.current = controller;

      const { path, method, pollForCompletion } = step.apiTrigger;
      const url = API_CONFIG.buildApiUrl(path);

      setApiLoading(true);
      setApiError(null);

      fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
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
                if (Date.now() - startTime > timeoutMs) {
                  cleanup();
                  setApiLoading(false);
                  console.log('[DemoRunner] Poll timeout — continuing');
                  return;
                }

                const statusUrl = `${API_CONFIG.buildApiUrl(statusPath)}?job_id=${data.job_id}`;
                const statusRes = await fetch(statusUrl);
                if (!statusRes.ok) return;

                const statusData = await statusRes.json();
                console.log('[DemoRunner] Poll →', statusData.status, statusData.message);

                // Stream intermediate results on every tick so the UI
                // can show live per-step progress
                setStepResult(step.id, statusData);

                const done = statusData.status === 'completed' ||
                             statusData.status === 'completed_with_errors' ||
                             statusData.status === 'failed';

                if (done) {
                  cleanup();
                  pipelineCompleteRef.current = true;
                  setApiLoading(false);
                }
              } catch (err) {
                console.warn('[DemoRunner] Poll error:', err);
              }
            }, intervalMs);
          } else {
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

  useEffect(() => {
    return cleanup;
  }, []);

  return null;
}
