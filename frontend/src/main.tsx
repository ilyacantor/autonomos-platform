import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.tsx';
import './index.css';
import { initDCLBridge } from './services/dclBridgeService';

declare global {
  interface Window {
    __BUILD_ID__: string;
  }
}

const BUILD_ID = '2025-10-25T12:10:00Z';
window.__BUILD_ID__ = BUILD_ID;

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>
);

initDCLBridge();
