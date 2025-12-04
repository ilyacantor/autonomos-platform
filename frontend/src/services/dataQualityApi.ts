import { API_CONFIG } from '../config/api';

export interface DataQualityMetadata {
  overall_data_quality_score: number;
  drift_detected: boolean;
  repair_processed: boolean;
  auto_applied_repairs: number;
  hitl_pending_repairs: number;
  sources_with_drift: string[];
  low_confidence_sources: string[];
  overall_confidence: number | null;
  sources: Record<string, any>;
}

export interface DriftAlert {
  source_id: string;
  connector_type: string;
  drift_severity: 'low' | 'medium' | 'high';
  fields_changed: string[];
  detected_at: string | null;
}

export interface HitlReview {
  source_id: string;
  connector_type: string;
  pending_repairs: number;
  confidence_score: number;
  queued_at: string | null;
}

export interface RepairHistoryItem {
  source_id: string;
  connector_type: string;
  repair_type: 'auto_applied' | 'hitl_pending';
  count: number;
  confidence: number;
  applied_at?: string | null;
  queued_at?: string | null;
  fields_repaired?: string[];
  fields_requiring_review?: string[];
}

export async function getDataQualityMetadata(tenant_id: string = 'default'): Promise<DataQualityMetadata> {
  const response = await fetch(
    API_CONFIG.buildDclUrl(`/metadata?tenant_id=${encodeURIComponent(tenant_id)}`)
  );
  
  if (!response.ok) {
    throw new Error(`Failed to fetch data quality metadata: ${response.statusText}`);
  }
  
  return response.json();
}

export async function getDriftAlerts(tenant_id: string = 'default'): Promise<DriftAlert[]> {
  const response = await fetch(
    API_CONFIG.buildDclUrl(`/drift-alerts?tenant_id=${encodeURIComponent(tenant_id)}`)
  );
  
  if (!response.ok) {
    throw new Error(`Failed to fetch drift alerts: ${response.statusText}`);
  }
  
  const data = await response.json();
  return data.alerts || [];
}

export async function getHitlPending(tenant_id: string = 'default'): Promise<{ pending_count: number; reviews: HitlReview[] }> {
  const response = await fetch(
    API_CONFIG.buildDclUrl(`/hitl-pending?tenant_id=${encodeURIComponent(tenant_id)}`)
  );
  
  if (!response.ok) {
    throw new Error(`Failed to fetch HITL pending: ${response.statusText}`);
  }
  
  return response.json();
}

export async function getRepairHistory(tenant_id: string = 'default', limit: number = 50): Promise<RepairHistoryItem[]> {
  const response = await fetch(
    API_CONFIG.buildDclUrl(`/repair-history?tenant_id=${encodeURIComponent(tenant_id)}&limit=${limit}`)
  );
  
  if (!response.ok) {
    throw new Error(`Failed to fetch repair history: ${response.statusText}`);
  }
  
  const data = await response.json();
  return data.repairs || [];
}
