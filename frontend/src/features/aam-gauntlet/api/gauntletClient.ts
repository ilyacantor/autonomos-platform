import axios from 'axios';
import { GAUNTLET_CONFIG } from '../../../config/gauntlet';
import type {
  Metrics,
  Connector,
  Workflow,
  WorkflowRequest,
  ScenarioRequest,
  CreateConnectorRequest
} from '../types';

const aamAPI = axios.create({
  baseURL: GAUNTLET_CONFIG.AAM_BACKEND_URL,
  timeout: 10000,
});

const farmAPI = axios.create({
  baseURL: GAUNTLET_CONFIG.API_FARM_URL,
  timeout: 10000,
});

export const gauntletClient = {
  async getMetrics(): Promise<Metrics> {
    const response = await aamAPI.get('/metrics');
    return response.data;
  },

  async getConnectors(): Promise<{ connectors: Connector[] }> {
    const response = await aamAPI.get('/connectors');
    return response.data;
  },

  async createConnector(config: CreateConnectorRequest): Promise<any> {
    const response = await aamAPI.post('/connectors', config);
    return response.data;
  },

  async deleteConnector(connectorId: string): Promise<any> {
    const response = await aamAPI.delete(`/connectors/${connectorId}`);
    return response.data;
  },

  async getWorkflows(): Promise<{ workflows: Workflow[] }> {
    const response = await aamAPI.get('/workflows');
    return response.data;
  },

  async runWorkflow(config: WorkflowRequest): Promise<any> {
    const response = await aamAPI.post('/workflows/run', config);
    return response.data;
  },

  async getWorkflowStatus(workflowId: string): Promise<Workflow> {
    const response = await aamAPI.get(`/workflows/${workflowId}`);
    return response.data;
  },

  async runScenario(scenario: ScenarioRequest): Promise<any> {
    const response = await aamAPI.post('/scenarios/run', scenario);
    return response.data;
  },

  async getDLQ(status = 'pending', limit = 100): Promise<any> {
    const response = await aamAPI.get(`/dlq?status=${status}&limit=${limit}`);
    return response.data;
  },

  async retryDLQEntry(entryId: number): Promise<any> {
    const response = await aamAPI.post(`/dlq/${entryId}/retry`);
    return response.data;
  },

  async getFarmStatus(): Promise<any> {
    const response = await farmAPI.get('/admin/status');
    return response.data;
  },

  async setChaosLevel(level: string): Promise<any> {
    const response = await farmAPI.post('/admin/chaos', { level });
    return response.data;
  },

  async resetFarmMetrics(): Promise<any> {
    const response = await farmAPI.post('/admin/reset');
    return response.data;
  },
};
