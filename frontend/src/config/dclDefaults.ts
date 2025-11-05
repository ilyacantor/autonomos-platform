/**
 * DCL Default Configurations
 * 
 * Centralized source and agent definitions for the DCL system.
 * Used for default selections on login and across Dashboard/Connections pages.
 */

export interface DCLSource {
  id: string;
  name: string;
  value: string;
  type: 'CRM' | 'ERP' | 'Database' | 'Warehouse';
  status: 'connected';
  description: string;
}

export interface DCLAgent {
  id: string;
  name: string;
  value: string;
  description: string;
}

export const DEFAULT_SOURCES: DCLSource[] = [
  { id: '1', name: 'Dynamics CRM', value: 'dynamics', type: 'CRM', status: 'connected', description: 'Customer relationship management' },
  { id: '2', name: 'Salesforce', value: 'salesforce', type: 'CRM', status: 'connected', description: 'Cloud-based CRM platform' },
  { id: '3', name: 'HubSpot', value: 'hubspot', type: 'CRM', status: 'connected', description: 'Marketing and sales platform' },
  { id: '4', name: 'SAP ERP', value: 'sap', type: 'ERP', status: 'connected', description: 'Enterprise resource planning' },
  { id: '5', name: 'NetSuite', value: 'netsuite', type: 'ERP', status: 'connected', description: 'Cloud ERP system' },
  { id: '6', name: 'Legacy SQL', value: 'legacy_sql', type: 'Database', status: 'connected', description: 'On-premise SQL database' },
  { id: '7', name: 'Snowflake', value: 'snowflake', type: 'Warehouse', status: 'connected', description: 'Cloud data warehouse' },
  { id: '8', name: 'Supabase', value: 'supabase', type: 'Database', status: 'connected', description: 'Open source database platform' },
  { id: '9', name: 'MongoDB', value: 'mongodb', type: 'Database', status: 'connected', description: 'NoSQL document database' },
];

/**
 * AAM-specific production connectors (4 sources)
 */
export const AAM_SOURCES: DCLSource[] = [
  { id: '2', name: 'Salesforce', value: 'salesforce', type: 'CRM', status: 'connected', description: 'Cloud-based CRM platform' },
  { id: '8', name: 'Supabase', value: 'supabase', type: 'Database', status: 'connected', description: 'Open source database platform' },
  { id: '9', name: 'MongoDB', value: 'mongodb', type: 'Database', status: 'connected', description: 'NoSQL document database' },
  { id: '10', name: 'FileSource', value: 'filesource', type: 'Database', status: 'connected', description: 'File-based data sources' },
];

export const DEFAULT_AGENTS: DCLAgent[] = [
  { id: '1', name: 'RevOps Pilot', value: 'revops_pilot', description: 'Revenue operations intelligence agent' },
  { id: '2', name: 'FinOps Pilot', value: 'finops_pilot', description: 'Financial operations intelligence agent' },
];

/**
 * Get all source values for default selection
 */
export const getAllSourceValues = (): string[] => {
  return DEFAULT_SOURCES.map(s => s.value);
};

/**
 * Get AAM source values (4 production connectors)
 */
export const getAamSourceValues = (): string[] => {
  return AAM_SOURCES.map(s => s.value);
};

/**
 * Get sources based on mode (AAM or Legacy)
 */
export const getSourcesByMode = (useAamMode: boolean): DCLSource[] => {
  return useAamMode ? AAM_SOURCES : DEFAULT_SOURCES;
};

/**
 * Get all agent values for default selection
 */
export const getAllAgentValues = (): string[] => {
  return DEFAULT_AGENTS.map(a => a.value);
};

/**
 * Initialize localStorage with default selections if empty or invalid
 * Called on successful authentication
 */
export const initializeDCLDefaults = (): void => {
  let shouldInitSources = false;
  let shouldInitAgents = false;

  try {
    const existingSources = localStorage.getItem('aos.selectedSources');
    if (!existingSources) {
      shouldInitSources = true;
    } else {
      const parsed = JSON.parse(existingSources);
      // Reinitialize if empty array
      if (!Array.isArray(parsed) || parsed.length === 0) {
        shouldInitSources = true;
      }
    }
  } catch (e) {
    shouldInitSources = true;
  }

  try {
    const existingAgents = localStorage.getItem('aos.selectedAgents');
    if (!existingAgents) {
      shouldInitAgents = true;
    } else {
      const parsed = JSON.parse(existingAgents);
      // Reinitialize if empty array
      if (!Array.isArray(parsed) || parsed.length === 0) {
        shouldInitAgents = true;
      }
    }
  } catch (e) {
    shouldInitAgents = true;
  }

  if (shouldInitSources) {
    const allSources = getAllSourceValues();
    localStorage.setItem('aos.selectedSources', JSON.stringify(allSources));
    console.log('[DCL Defaults] Initialized all sources:', allSources);
  }

  if (shouldInitAgents) {
    const allAgents = getAllAgentValues();
    localStorage.setItem('aos.selectedAgents', JSON.stringify(allAgents));
    console.log('[DCL Defaults] Initialized all agents:', allAgents);
  }
};

/**
 * Get default source selections from localStorage or fallback to all
 * Returns all sources if saved selection is empty or invalid
 */
export const getDefaultSources = (): string[] => {
  try {
    const saved = localStorage.getItem('aos.selectedSources');
    if (saved) {
      const parsed = JSON.parse(saved);
      // Return all sources if saved selection is empty array
      if (Array.isArray(parsed) && parsed.length > 0) {
        return parsed;
      }
    }
  } catch (e) {
    console.error('[DCL Defaults] Failed to parse saved sources:', e);
  }
  return getAllSourceValues();
};

/**
 * Get default agent selections from localStorage or fallback to all
 * Returns all agents if saved selection is empty or invalid
 */
export const getDefaultAgents = (): string[] => {
  try {
    const saved = localStorage.getItem('aos.selectedAgents');
    if (saved) {
      const parsed = JSON.parse(saved);
      // Return all agents if saved selection is empty array
      if (Array.isArray(parsed) && parsed.length > 0) {
        return parsed;
      }
    }
  } catch (e) {
    console.error('[DCL Defaults] Failed to parse saved agents:', e);
  }
  return getAllAgentValues();
};
