import { Cpu, TrendingUp, Wallet, Banknote, Crown, type LucideIcon } from 'lucide-react';

export type PersonaSlug = 'ceo' | 'cto' | 'cro' | 'coo' | 'cfo';

export type PersonaDisplay = 'CEO' | 'CTO' | 'CRO' | 'COO' | 'CFO';

export interface PersonaTile {
  key: string;
  title: string;
  value: string | null;
  delta: string | null;
  timeframe: string;
  last_updated: string | null;
  href: string;
  note?: string;
  mock?: boolean;
}

export interface PersonaTable {
  title: string;
  columns: string[];
  rows: string[][];
  href: string;
  note?: string;
  mock?: boolean;
}

export interface PersonaSummaryResponse {
  persona: PersonaSlug;
  tiles: PersonaTile[];
  table: PersonaTable;
  trace_id: string;
}

export const PERSONA_LABELS: Record<PersonaSlug, PersonaDisplay> = {
  ceo: 'CEO',
  cto: 'CTO',
  cro: 'CRO',
  coo: 'COO',
  cfo: 'CFO'
};

export const PERSONA_ICON_MAP: Record<PersonaSlug, LucideIcon> = {
  ceo: Crown,
  cto: Cpu,
  cro: TrendingUp,
  coo: Wallet,
  cfo: Banknote
};

export const PERSONA_COLORS: Record<PersonaSlug, string> = {
  ceo: 'yellow',
  cto: 'blue',
  cro: 'purple',
  coo: 'green',
  cfo: 'amber'
};

export function slugToLabel(slug: PersonaSlug): PersonaDisplay {
  return PERSONA_LABELS[slug];
}

export function getPersonaIcon(slug: PersonaSlug): LucideIcon {
  return PERSONA_ICON_MAP[slug];
}

export function getPersonaColor(slug: PersonaSlug): string {
  return PERSONA_COLORS[slug];
}
