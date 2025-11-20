import axios from 'axios'

const aamAPI = axios.create({
  baseURL: '/api/aam',
  timeout: 10000,
})

const farmAPI = axios.create({
  baseURL: '/api/farm',
  timeout: 10000,
})

export const apiClient = {
  // AAM endpoints
  async getMetrics() {
    const response = await aamAPI.get('/metrics')
    return response.data
  },

  async getConnectors() {
    const response = await aamAPI.get('/connectors')
    return response.data
  },

  async createConnector(config: any) {
    const response = await aamAPI.post('/connectors', config)
    return response.data
  },

  async deleteConnector(connectorId: string) {
    const response = await aamAPI.delete(`/connectors/${connectorId}`)
    return response.data
  },

  async getWorkflows() {
    const response = await aamAPI.get('/workflows')
    return response.data
  },

  async runWorkflow(config: any) {
    const response = await aamAPI.post('/workflows/run', config)
    return response.data
  },

  async getWorkflowStatus(workflowId: string) {
    const response = await aamAPI.get(`/workflows/${workflowId}`)
    return response.data
  },

  async runScenario(scenario: any) {
    const response = await aamAPI.post('/scenarios/run', scenario)
    return response.data
  },

  async getDLQ(status = 'pending', limit = 100) {
    const response = await aamAPI.get(`/dlq?status=${status}&limit=${limit}`)
    return response.data
  },

  async retryDLQEntry(entryId: number) {
    const response = await aamAPI.post(`/dlq/${entryId}/retry`)
    return response.data
  },

  // Farm endpoints
  async getFarmStatus() {
    const response = await farmAPI.get('/admin/status')
    return response.data
  },

  async setChaosLevel(level: string) {
    const response = await farmAPI.post('/admin/chaos', { level })
    return response.data
  },

  async resetFarmMetrics() {
    const response = await farmAPI.post('/admin/reset')
    return response.data
  },
}