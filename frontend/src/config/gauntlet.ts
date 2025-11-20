export const GAUNTLET_CONFIG = {
  AAM_BACKEND_URL: import.meta.env.VITE_GAUNTLET_AAM_URL || 'http://localhost:8080',
  API_FARM_URL: import.meta.env.VITE_GAUNTLET_API_FARM_URL || 'http://localhost:8000',
  MAIN_API_URL: import.meta.env.VITE_API_URL || 'http://localhost:5000'
};
