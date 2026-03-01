import { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import type { DemoDefinition, DemoState } from '../components/demo/demoTypes';

// ── Context shape ────────────────────────────────────────────────────

interface DemoContextType extends DemoState {
  startDemo: (demo: DemoDefinition) => void;
  nextStep: () => void;
  prevStep: () => void;
  goToStep: (index: number) => void;
  exitDemo: () => void;
  setStepResult: (id: string, data: unknown) => void;
  setApiLoading: (loading: boolean) => void;
  setApiError: (error: string | null) => void;
  setPipelineJobId: (id: string | null) => void;
}

const DemoContext = createContext<DemoContextType | undefined>(undefined);

// ── Initial state ────────────────────────────────────────────────────

const INITIAL_STATE: DemoState = {
  status: 'idle',
  activeDemo: null,
  currentStepIndex: 0,
  stepResults: {},
  isApiLoading: false,
  apiError: null,
  pipelineJobId: null,
};

// ── Provider ─────────────────────────────────────────────────────────

export function DemoProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<DemoState>(INITIAL_STATE);

  const startDemo = useCallback((demo: DemoDefinition) => {
    setState({
      ...INITIAL_STATE,
      status: 'running',
      activeDemo: demo,
      currentStepIndex: 0,
    });
  }, []);

  const nextStep = useCallback(() => {
    setState((prev) => {
      if (!prev.activeDemo) return prev;
      const maxIndex = prev.activeDemo.steps.length - 1;
      if (prev.currentStepIndex >= maxIndex) {
        return { ...prev, status: 'completed' };
      }
      return {
        ...prev,
        currentStepIndex: prev.currentStepIndex + 1,
        isApiLoading: false,
        apiError: null,
      };
    });
  }, []);

  const prevStep = useCallback(() => {
    setState((prev) => {
      if (prev.currentStepIndex <= 0) return prev;
      return {
        ...prev,
        currentStepIndex: prev.currentStepIndex - 1,
        isApiLoading: false,
        apiError: null,
      };
    });
  }, []);

  const goToStep = useCallback((index: number) => {
    setState((prev) => {
      if (!prev.activeDemo) return prev;
      const clamped = Math.max(0, Math.min(index, prev.activeDemo.steps.length - 1));
      return {
        ...prev,
        currentStepIndex: clamped,
        isApiLoading: false,
        apiError: null,
      };
    });
  }, []);

  const exitDemo = useCallback(() => {
    setState(INITIAL_STATE);
  }, []);

  const setStepResult = useCallback((id: string, data: unknown) => {
    setState((prev) => ({
      ...prev,
      stepResults: { ...prev.stepResults, [id]: data },
    }));
  }, []);

  const setApiLoading = useCallback((loading: boolean) => {
    setState((prev) => ({ ...prev, isApiLoading: loading }));
  }, []);

  const setApiError = useCallback((error: string | null) => {
    setState((prev) => ({ ...prev, apiError: error, isApiLoading: false }));
  }, []);

  const setPipelineJobId = useCallback((id: string | null) => {
    setState((prev) => ({ ...prev, pipelineJobId: id }));
  }, []);

  return (
    <DemoContext.Provider
      value={{
        ...state,
        startDemo,
        nextStep,
        prevStep,
        goToStep,
        exitDemo,
        setStepResult,
        setApiLoading,
        setApiError,
        setPipelineJobId,
      }}
    >
      {children}
    </DemoContext.Provider>
  );
}

// ── Hook ─────────────────────────────────────────────────────────────

export function useDemo() {
  const context = useContext(DemoContext);
  if (context === undefined) {
    throw new Error('useDemo must be used within a DemoProvider');
  }
  return context;
}
