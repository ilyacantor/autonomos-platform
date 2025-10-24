// Unified backend configuration
const BASE_URL = import.meta.env.VITE_BASE_URL || window.location.origin;

export const API_CONFIG = {
  BASE_URL,
  // Helper functions for consistent endpoint construction
  buildApiUrl: (path: string) => `${BASE_URL}/api/v1${path}`,
  buildDclUrl: (path: string) => `${BASE_URL}/dcl${path}`,
};

export const AUTH_TOKEN_KEY = 'aoa_jwt';
