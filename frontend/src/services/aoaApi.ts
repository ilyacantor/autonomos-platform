import { API_CONFIG, AUTH_TOKEN_KEY } from '../config/api';
import type { DiscoveryResponse } from '../types/api';

const TOKEN_EXPIRY_KEY = 'auth_token_expiry';

class AOAApiService {
  private getAuthHeader(): Record<string, string> {
    const token = localStorage.getItem(AUTH_TOKEN_KEY);
    return token ? { 'Authorization': `Bearer ${token}` } : {};
  }

  private handleUnauthorized() {
    console.log('[AOA API] 401 Unauthorized - clearing auth state');
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(TOKEN_EXPIRY_KEY);
    // Trigger a custom event for the auth context to listen to
    window.dispatchEvent(new CustomEvent('auth:unauthorized'));
  }

  private async handleResponse(response: Response) {
    if (response.status === 401) {
      this.handleUnauthorized();
      throw new Error('Session expired. Please login again.');
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(error.detail || `HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  async getState() {
    const response = await fetch(API_CONFIG.buildApiUrl('/aoa/state'), {
      headers: {
        ...this.getAuthHeader(),
      },
    });
    return this.handleResponse(response);
  }

  async run(sources?: string, agents?: string) {
    const params = new URLSearchParams();
    if (sources) params.append('sources', sources);
    if (agents) params.append('agents', agents);

    const url = `${API_CONFIG.buildApiUrl('/aoa/run')}${params.toString() ? `?${params.toString()}` : ''}`;
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        ...this.getAuthHeader(),
        'Content-Type': 'application/json',
      },
    });
    return this.handleResponse(response);
  }

  async reset() {
    const response = await fetch(API_CONFIG.buildApiUrl('/aoa/reset'), {
      method: 'POST',
      headers: {
        ...this.getAuthHeader(),
        'Content-Type': 'application/json',
      },
    });
    return this.handleResponse(response);
  }

  async toggleProdMode(enabled: boolean) {
    const response = await fetch(API_CONFIG.buildApiUrl('/aoa/prod-mode'), {
      method: 'POST',
      headers: {
        ...this.getAuthHeader(),
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ enabled }),
    });
    return this.handleResponse(response);
  }

  async discover(nlpQuery: string) {
    const payload = {
      nlp_query: nlpQuery,
      tenant_id: '',
      discovery_types: ['entity_mapping'],
      max_results: 10,
      min_confidence: 0.7,
    };

    console.log('[Discover] Sending request:', payload);

    const response = await fetch(API_CONFIG.buildApiUrl('/aoa/discover'), {
      method: 'POST',
      headers: {
        ...this.getAuthHeader(),
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    const data: DiscoveryResponse = await this.handleResponse(response);

    console.log('[Discover] Received response:', data);

    if (data.agent_recommendations && data.agent_recommendations.length > 0) {
      const assignedAgents = data.agent_recommendations.map(rec => rec.agent_name);
      console.log('[Discover] Handing to agents:', {
        assigned_agents: assignedAgents,
        processing_priority: data.agent_recommendations[0]?.priority || 'medium',
        total_entities: data.total_entities_found,
        overall_confidence: data.overall_confidence,
      });
    }

    return data;
  }

  async demoScan() {
    console.log('[Demo Scan] Starting full asset scan...');

    const response = await fetch(API_CONFIG.buildApiUrl('/aoa/demo-scan'), {
      method: 'POST',
      headers: {
        ...this.getAuthHeader(),
        'Content-Type': 'application/json',
      },
    });

    const data = await this.handleResponse(response);
    
    console.log('[Demo Scan] Scan completed:', data);
    
    return data;
  }
}

export const aoaApi = new AOAApiService();
