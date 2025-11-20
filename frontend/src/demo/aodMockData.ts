export type AssetState = 'READY_FOR_CONNECT' | 'PARKED' | 'UNKNOWN' | 'CONNECTED' | 'PROCESSING';
export type AssetKind = 'service' | 'db' | 'saas' | 'host';
export type Vendor = 'salesforce' | 'mongodb' | 'supabase' | 'legacy';

export interface AodAsset {
  id: string;
  name: string;
  vendor: Vendor;
  kind: AssetKind;
  environment: 'prod' | 'staging' | 'dev';
  state: AssetState;
  ownerEmail: string;
}

export const mockAssets: AodAsset[] = [
  { id: 'sf-001', name: 'Salesforce Production Instance', vendor: 'salesforce', kind: 'saas', environment: 'prod', state: 'READY_FOR_CONNECT', ownerEmail: 'sarah.chen@example.com' },
  { id: 'sf-002', name: 'Salesforce Accounts API', vendor: 'salesforce', kind: 'service', environment: 'prod', state: 'READY_FOR_CONNECT', ownerEmail: 'sarah.chen@example.com' },
  { id: 'sf-003', name: 'Salesforce Opportunities DB', vendor: 'salesforce', kind: 'db', environment: 'prod', state: 'READY_FOR_CONNECT', ownerEmail: 'mark.johnson@example.com' },
  { id: 'sf-004', name: 'Salesforce Contacts API', vendor: 'salesforce', kind: 'service', environment: 'prod', state: 'READY_FOR_CONNECT', ownerEmail: 'sarah.chen@example.com' },
  { id: 'sf-005', name: 'Salesforce Sandbox', vendor: 'salesforce', kind: 'saas', environment: 'staging', state: 'PARKED', ownerEmail: 'dev-team@example.com' },
  { id: 'sf-006', name: 'Salesforce Custom Objects', vendor: 'salesforce', kind: 'db', environment: 'prod', state: 'READY_FOR_CONNECT', ownerEmail: 'mark.johnson@example.com' },
  { id: 'sf-007', name: 'Salesforce Reports Engine', vendor: 'salesforce', kind: 'service', environment: 'prod', state: 'CONNECTED', ownerEmail: 'analytics@example.com' },
  { id: 'sf-008', name: 'Salesforce Marketing Cloud', vendor: 'salesforce', kind: 'saas', environment: 'prod', state: 'READY_FOR_CONNECT', ownerEmail: 'marketing@example.com' },
  { id: 'sf-009', name: 'Salesforce Dev Environment', vendor: 'salesforce', kind: 'saas', environment: 'dev', state: 'UNKNOWN', ownerEmail: 'dev-team@example.com' },
  { id: 'sf-010', name: 'Salesforce Integration API', vendor: 'salesforce', kind: 'service', environment: 'prod', state: 'READY_FOR_CONNECT', ownerEmail: 'integration@example.com' },

  { id: 'mg-001', name: 'MongoDB Production Cluster', vendor: 'mongodb', kind: 'db', environment: 'prod', state: 'READY_FOR_CONNECT', ownerEmail: 'db-admin@example.com' },
  { id: 'mg-002', name: 'MongoDB User Events Collection', vendor: 'mongodb', kind: 'db', environment: 'prod', state: 'READY_FOR_CONNECT', ownerEmail: 'analytics@example.com' },
  { id: 'mg-003', name: 'MongoDB Analytics DB', vendor: 'mongodb', kind: 'db', environment: 'prod', state: 'READY_FOR_CONNECT', ownerEmail: 'analytics@example.com' },
  { id: 'mg-004', name: 'MongoDB Staging Cluster', vendor: 'mongodb', kind: 'db', environment: 'staging', state: 'PARKED', ownerEmail: 'dev-team@example.com' },
  { id: 'mg-005', name: 'MongoDB Logs Collection', vendor: 'mongodb', kind: 'db', environment: 'prod', state: 'READY_FOR_CONNECT', ownerEmail: 'ops@example.com' },
  { id: 'mg-006', name: 'MongoDB Metrics API', vendor: 'mongodb', kind: 'service', environment: 'prod', state: 'CONNECTED', ownerEmail: 'ops@example.com' },
  { id: 'mg-007', name: 'MongoDB Archive Cluster', vendor: 'mongodb', kind: 'db', environment: 'prod', state: 'PARKED', ownerEmail: 'db-admin@example.com' },
  { id: 'mg-008', name: 'MongoDB Cache Layer', vendor: 'mongodb', kind: 'service', environment: 'prod', state: 'READY_FOR_CONNECT', ownerEmail: 'backend@example.com' },

  { id: 'sb-001', name: 'Supabase Production DB', vendor: 'supabase', kind: 'db', environment: 'prod', state: 'READY_FOR_CONNECT', ownerEmail: 'backend@example.com' },
  { id: 'sb-002', name: 'Supabase Auth Service', vendor: 'supabase', kind: 'service', environment: 'prod', state: 'READY_FOR_CONNECT', ownerEmail: 'backend@example.com' },
  { id: 'sb-003', name: 'Supabase Storage API', vendor: 'supabase', kind: 'service', environment: 'prod', state: 'CONNECTED', ownerEmail: 'storage@example.com' },
  { id: 'sb-004', name: 'Supabase Realtime Service', vendor: 'supabase', kind: 'service', environment: 'prod', state: 'READY_FOR_CONNECT', ownerEmail: 'backend@example.com' },
  { id: 'sb-005', name: 'Supabase Edge Functions', vendor: 'supabase', kind: 'service', environment: 'prod', state: 'READY_FOR_CONNECT', ownerEmail: 'serverless@example.com' },
  { id: 'sb-006', name: 'Supabase Staging DB', vendor: 'supabase', kind: 'db', environment: 'staging', state: 'PARKED', ownerEmail: 'dev-team@example.com' },
  { id: 'sb-007', name: 'Supabase Vector Store', vendor: 'supabase', kind: 'db', environment: 'prod', state: 'READY_FOR_CONNECT', ownerEmail: 'ai-team@example.com' },

  { id: 'lg-001', name: 'Legacy Customer CSV Files', vendor: 'legacy', kind: 'db', environment: 'prod', state: 'READY_FOR_CONNECT', ownerEmail: 'migration@example.com' },
  { id: 'lg-002', name: 'Legacy Excel Reports', vendor: 'legacy', kind: 'service', environment: 'prod', state: 'PARKED', ownerEmail: 'finance@example.com' },
  { id: 'lg-003', name: 'Legacy FTP Server', vendor: 'legacy', kind: 'host', environment: 'prod', state: 'UNKNOWN', ownerEmail: 'ops@example.com' },
  { id: 'lg-004', name: 'Legacy Oracle DB Export', vendor: 'legacy', kind: 'db', environment: 'prod', state: 'READY_FOR_CONNECT', ownerEmail: 'migration@example.com' },
  { id: 'lg-005', name: 'Legacy File Storage', vendor: 'legacy', kind: 'service', environment: 'prod', state: 'READY_FOR_CONNECT', ownerEmail: 'storage@example.com' },
  { id: 'lg-006', name: 'Legacy Backup Server', vendor: 'legacy', kind: 'host', environment: 'prod', state: 'PARKED', ownerEmail: 'ops@example.com' },
  { id: 'lg-007', name: 'Legacy API Gateway', vendor: 'legacy', kind: 'service', environment: 'prod', state: 'UNKNOWN', ownerEmail: 'legacy-team@example.com' },
  { id: 'lg-008', name: 'Legacy Data Warehouse', vendor: 'legacy', kind: 'db', environment: 'prod', state: 'READY_FOR_CONNECT', ownerEmail: 'analytics@example.com' },
  { id: 'lg-009', name: 'Legacy Sharepoint Files', vendor: 'legacy', kind: 'service', environment: 'prod', state: 'PARKED', ownerEmail: 'hr@example.com' },
  { id: 'lg-010', name: 'Legacy Network Share', vendor: 'legacy', kind: 'host', environment: 'prod', state: 'READY_FOR_CONNECT', ownerEmail: 'ops@example.com' },
];

export interface VendorSummary {
  vendor: Vendor;
  count: number;
  displayName: string;
  color: string;
}

export interface TotalCounts {
  total: number;
  ready: number;
  parked: number;
  shadowIT: number;
}

export function getVendorSummary(assets: AodAsset[]): VendorSummary[] {
  const vendors: Vendor[] = ['salesforce', 'mongodb', 'supabase', 'legacy'];
  
  return vendors.map(vendor => ({
    vendor,
    count: assets.filter(a => a.vendor === vendor).length,
    displayName: vendor === 'salesforce' ? 'Salesforce' :
                 vendor === 'mongodb' ? 'MongoDB' :
                 vendor === 'supabase' ? 'Supabase' :
                 'Legacy Files',
    color: vendor === 'salesforce' ? 'cyan' :
           vendor === 'mongodb' ? 'green' :
           vendor === 'supabase' ? 'purple' :
           'orange'
  }));
}

export function getTotalCounts(assets: AodAsset[]): TotalCounts {
  return {
    total: assets.length,
    ready: assets.filter(a => a.state === 'READY_FOR_CONNECT').length,
    parked: assets.filter(a => a.state === 'PARKED').length,
    shadowIT: assets.filter(a => a.state === 'UNKNOWN').length,
  };
}

export function getAssetsByVendor(assets: AodAsset[], vendor: Vendor): AodAsset[] {
  return assets.filter(a => a.vendor === vendor);
}
