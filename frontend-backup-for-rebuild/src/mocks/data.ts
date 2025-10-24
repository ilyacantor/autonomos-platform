import type {
  SourceNode,
  AgentNode,
  DCLStats,
  MappingReview,
  SchemaChange,
  AgentPerformance,
  Connection
} from '../types';

export const mockSourceNodes: SourceNode[] = [
  { id: 'sf1', name: 'Salesforce Production', type: 'salesforce', status: 'online', recordsPerMin: 1247 },
  { id: 'sn1', name: 'Snowflake DW', type: 'snowflake', status: 'online', recordsPerMin: 3891 },
  { id: 'ns1', name: 'NetSuite ERP', type: 'netsuite', status: 'online', recordsPerMin: 892 },
  { id: 'aws1', name: 'AWS S3 Logs', type: 'aws', status: 'online', recordsPerMin: 5234 },
];

export const mockAgentNodes: AgentNode[] = [
  { id: 'ra1', name: 'RevOps Agent', type: 'revops', dataRequestsPerMin: 342, lastSuccessfulRun: '2 min ago' },
  { id: 'fa1', name: 'FinOps Agent', type: 'finops', dataRequestsPerMin: 189, lastSuccessfulRun: '5 min ago' },
];

export const mockDCLStats: DCLStats = {
  llmCallsPerMin: 127,
  avgTokenUsage: 842,
  ragIndexSize: '2.4 GB',
  ontologyEntities: 1847,
  mappingsInReview: 23,
};

export const mockMappingReviews: MappingReview[] = [
  {
    id: 'mr1',
    timestamp: '2025-10-17T14:32:18Z',
    sourceField: 'sf_account.annual_revenue__c',
    unifiedField: 'Account.AnnualRevenue',
    confidence: 76,
    sourceSample: '{"annual_revenue__c": 2500000, "currency": "USD"}',
    llmReasoning: 'Field name suggests annual revenue metric. Custom field suffix indicates Salesforce custom field. High semantic similarity to unified schema.'
  },
  {
    id: 'mr2',
    timestamp: '2025-10-17T14:28:45Z',
    sourceField: 'ns_customer.credit_limit',
    unifiedField: 'Account.CreditLimit',
    confidence: 72,
    sourceSample: '{"credit_limit": 50000.00, "currency_id": 1}',
    llmReasoning: 'NetSuite credit_limit field maps to Account CreditLimit. Moderate confidence due to currency handling differences.'
  },
  {
    id: 'mr3',
    timestamp: '2025-10-17T14:25:12Z',
    sourceField: 'sf_opportunity.close_date_custom__c',
    unifiedField: 'Opportunity.CloseDate',
    confidence: 68,
    sourceSample: '{"close_date_custom__c": "2025-12-31"}',
    llmReasoning: 'Custom close date field. Lower confidence due to potential for alternative close date fields in source.'
  },
];

export const mockSchemaChanges: SchemaChange[] = [
  {
    id: 'sc1',
    timestamp: '2025-10-17T13:15:00Z',
    source: 'Salesforce Production',
    changeType: 'added',
    field: 'Account.customer_segment__c',
    description: 'New custom field detected'
  },
  {
    id: 'sc2',
    timestamp: '2025-10-17T12:48:00Z',
    source: 'NetSuite ERP',
    changeType: 'modified',
    field: 'Customer.email',
    description: 'Data type changed: VARCHAR(100) → VARCHAR(255)'
  },
  {
    id: 'sc3',
    timestamp: '2025-10-17T11:22:00Z',
    source: 'Snowflake DW',
    changeType: 'removed',
    field: 'Orders.legacy_id',
    description: 'Field no longer present in schema'
  },
];

export const mockAgentPerformance: AgentPerformance[] = [
  { id: 'ap1', name: 'RevOps Agent', status: 'running', executionsPerHour: 342, cpuPercent: 23, memoryMB: 512 },
  { id: 'ap2', name: 'FinOps Agent', status: 'running', executionsPerHour: 189, cpuPercent: 18, memoryMB: 448 },
  { id: 'ap3', name: 'Sales Forecasting', status: 'warning', executionsPerHour: 67, cpuPercent: 45, memoryMB: 892 },
  { id: 'ap4', name: 'Churn Predictor', status: 'running', executionsPerHour: 124, cpuPercent: 31, memoryMB: 674 },
  { id: 'ap5', name: 'Lead Scoring', status: 'running', executionsPerHour: 298, cpuPercent: 19, memoryMB: 423 },
];

export const mockConnections: Connection[] = [
  {
    id: 'c1',
    name: 'Salesforce Production CRM',
    type: 'salesforce',
    status: 'connected',
    lastSync: '2 minutes ago',
    isPaused: false
  },
  {
    id: 'c2',
    name: 'Snowflake Data Warehouse',
    type: 'snowflake',
    status: 'connected',
    lastSync: '5 minutes ago',
    isPaused: false
  },
  {
    id: 'c3',
    name: 'NetSuite ERP',
    type: 'netsuite',
    status: 'connected',
    lastSync: '1 hour ago',
    isPaused: false
  },
  {
    id: 'c4',
    name: 'AWS S3 Storage',
    type: 'aws',
    status: 'connected',
    lastSync: '10 minutes ago',
    isPaused: false
  },
];
