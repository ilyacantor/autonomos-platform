interface DCLState {
  sources: string[];
  agents: string[];
  devMode: boolean;
}

const dclState: DCLState = {
  sources: [],
  agents: [],
  devMode: false,
};

async function fetchDCLState(): Promise<any> {
  try {
    const response = await fetch('/dcl/state');
    const data = await response.json();
    dclState.sources = data.selected_sources || [];
    dclState.agents = data.selected_agents || [];
    dclState.devMode = data.dev_mode || false;
    console.log('[DCL State]', dclState);
    return data;
  } catch (err) {
    console.error('[DCL State Error]', err);
    return null;
  }
}

function createDevModeToggle(): void {
  const toggleContainer = document.createElement('div');
  toggleContainer.id = 'dcl-dev-mode-toggle';
  toggleContainer.style.cssText = `
    position: fixed;
    bottom: 20px;
    right: 20px;
    z-index: 9999;
    background: white;
    border: 2px solid #ddd;
    border-radius: 8px;
    padding: 12px 16px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    cursor: pointer;
    transition: all 0.3s ease;
    user-select: none;
  `;

  function updateToggleUI(): void {
    const isDevMode = dclState.devMode;
    toggleContainer.innerHTML = `
      <div style="display: flex; align-items: center; gap: 10px;">
        <div style="
          width: 12px;
          height: 12px;
          border-radius: 50%;
          background: ${isDevMode ? '#f59e0b' : '#10b981'};
          box-shadow: 0 0 8px ${isDevMode ? '#f59e0b66' : '#10b98166'};
        "></div>
        <div>
          <div style="font-weight: 600; font-size: 13px; color: #333;">
            ${isDevMode ? 'Dev Mode (AI)' : 'Prod Mode'}
          </div>
          <div style="font-size: 11px; color: #666;">
            ${isDevMode ? 'AI + RAG Active' : 'Heuristics Only'}
          </div>
        </div>
        <div style="
          font-size: 11px;
          color: #999;
          margin-left: 8px;
          padding-left: 8px;
          border-left: 1px solid #ddd;
        ">
          Click to toggle
        </div>
      </div>
    `;

    toggleContainer.style.borderColor = isDevMode ? '#f59e0b' : '#10b981';
  }

  updateToggleUI();


  toggleContainer.addEventListener('click', async function() {
    const newMode = !dclState.devMode;
    console.log(`[DCL] Toggling Dev Mode to: ${newMode ? 'ON' : 'OFF'}`);

    try {
      const response = await fetch(`/dcl/toggle_dev_mode?enabled=${newMode}`);
      const data = await response.json();
      console.log('[DCL Dev Mode Toggle Success]', data);
      dclState.devMode = data.dev_mode;
      updateToggleUI();
    } catch (err) {
      console.error('[DCL Dev Mode Toggle Error]', err);
    }
  });

  toggleContainer.addEventListener('mouseenter', function() {
    this.style.transform = 'scale(1.05)';
    this.style.boxShadow = '0 6px 16px rgba(0,0,0,0.2)';
  });

  toggleContainer.addEventListener('mouseleave', function() {
    this.style.transform = 'scale(1)';
    this.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
  });

  document.body.appendChild(toggleContainer);
  console.log('[DCL Bridge] Dev Mode toggle created');
}

export function initDCLBridge(): void {
  console.log('[DCL Bridge] Initializing...');

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      console.log('[DCL Bridge] DOM loaded, setting up DCL controls');
      setupDCLBridge();
    });
  } else {
    console.log('[DCL Bridge] DOM already loaded, setting up DCL controls');
    setupDCLBridge();
  }
}

function setupDCLBridge(): void {
  setTimeout(createDevModeToggle, 1000);

  (window as any).dclConnect = async function(sources?: string, agents?: string) {
    const sourcesParam = sources || 'dynamics,salesforce,hubspot';
    const agentsParam = agents || 'revops_pilot,finops_pilot';

    console.log(`[DCL] Connecting sources: ${sourcesParam}, agents: ${agentsParam}`);

    const encodedSources = encodeURIComponent(sourcesParam);
    const encodedAgents = encodeURIComponent(agentsParam);

    try {
      const response = await fetch(`/dcl/connect?sources=${encodedSources}&agents=${encodedAgents}`);
      const data = await response.json();
      console.log('[DCL Connect Success]', data);
      return data;
    } catch (err) {
      console.error('[DCL Connect Error]', err);
      throw err;
    }
  };

  (window as any).dclReset = async function() {
    console.log('[DCL] ⚠️ DEPRECATED: dclReset() is deprecated. Reset functionality removed - calling dclConnect() instead.');
    console.log('[DCL] Backend /dcl/connect is now idempotent and handles state clearing automatically.');
    
    try {
      // Get current state to preserve sources/agents selection
      const sources = dclState.sources.length > 0 
        ? dclState.sources.join(',') 
        : 'dynamics,salesforce,hubspot';
      const agents = dclState.agents.length > 0 
        ? dclState.agents.join(',') 
        : 'revops_pilot,finops_pilot';
      
      // Call dclConnect instead of reset
      return await (window as any).dclConnect(sources, agents);
    } catch (err) {
      console.error('[DCL] Error in deprecated dclReset():', err);
      throw err;
    }
  };

  (window as any).dclToggleDevMode = async function() {
    console.log('[DCL] Toggling dev mode...');

    try {
      const response = await fetch('/dcl/toggle_dev_mode');
      const data = await response.json();
      console.log('[DCL Toggle Dev Mode Success]', data);
      return data;
    } catch (err) {
      console.error('[DCL Toggle Dev Mode Error]', err);
      throw err;
    }
  };

  console.log('[DCL Bridge] Ready! Use:');
  console.log('  - window.dclConnect() to connect sources');
  console.log('  - window.dclReset() [DEPRECATED] calls dclConnect() - use dclConnect() instead');
  console.log('  - window.dclToggleDevMode() to toggle dev mode');
  console.log('  Note: State updates now use WebSocket instead of polling');
}
