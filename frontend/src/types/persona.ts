export type PersonaSlug = 'cto' | 'cro' | 'coo' | 'cfo';

export type PersonaDisplay = 'Data Engineer' | 'RevOps' | 'FinOps' | 'Finance';

export interface PersonaTile {
  key: string;
  title: string;
  value: string | null;
  delta: string | null;
  timeframe: string;
  last_updated: string | null;
  href: string;
  note?: string;
}

export interface PersonaTable {
  title: string;
  columns: string[];
  rows: string[][];
  href: string;
  note?: string;
}

export interface PersonaSummaryResponse {
  persona: PersonaSlug;
  tiles: PersonaTile[];
  table: PersonaTable;
  trace_id: string;
}

export const PERSONA_LABELS: Record<PersonaSlug, PersonaDisplay> = {
  cto: 'Data Engineer',
  cro: 'RevOps',
  coo: 'FinOps',
  cfo: 'Finance'
};

export const PERSONA_ICONS: Record<PersonaSlug, string> = {
  cto: '🔧',
  cro: '📊',
  coo: '💰',
  cfo: '💼'
};

export const PERSONA_COLORS: Record<PersonaSlug, string> = {
  cto: 'blue',
  cro: 'purple',
  coo: 'green',
  cfo: 'amber'
};

export function slugToLabel(slug: PersonaSlug): PersonaDisplay {
  return PERSONA_LABELS[slug];
}

export function getPersonaIcon(slug: PersonaSlug): string {
  return PERSONA_ICONS[slug];
}

export function getPersonaColor(slug: PersonaSlug): string {
  return PERSONA_COLORS[slug];
}
