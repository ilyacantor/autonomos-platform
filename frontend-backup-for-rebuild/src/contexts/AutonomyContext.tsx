import { createContext, useContext, useState, ReactNode } from 'react';
import type { AutonomyMode } from '../types';

interface AutonomyContextType {
  autonomyMode: AutonomyMode;
  setAutonomyMode: (mode: AutonomyMode) => void;
  isModalOpen: boolean;
  setIsModalOpen: (open: boolean) => void;
  legacyMode: boolean;
  setLegacyMode: (legacy: boolean) => void;
}

const AutonomyContext = createContext<AutonomyContextType | undefined>(undefined);

export function AutonomyProvider({ children }: { children: ReactNode }) {
  const [autonomyMode, setAutonomyMode] = useState<AutonomyMode>('Auto (Guardrails)');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [legacyMode, setLegacyMode] = useState(false);

  return (
    <AutonomyContext.Provider value={{ autonomyMode, setAutonomyMode, isModalOpen, setIsModalOpen, legacyMode, setLegacyMode }}>
      {children}
    </AutonomyContext.Provider>
  );
}

export function useAutonomy() {
  const context = useContext(AutonomyContext);
  if (context === undefined) {
    throw new Error('useAutonomy must be used within an AutonomyProvider');
  }
  return context;
}
