import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.tsx';
import './index.css';
import { initDCLBridge } from './services/dclBridgeService';

// Build ID for cache verification
const BUILD_ID = '2025-10-25T12:10:00Z';
(window as any).__BUILD_ID__ = BUILD_ID;
console.log('[UI] BUILD_ID:', BUILD_ID);

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>
);

initDCLBridge();
