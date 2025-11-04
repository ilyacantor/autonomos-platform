export type SourceSystem = "salesforce" | "supabase" | "mongodb" | "filesource" | "system";

export type EventStage = 
  | "ingested" 
  | "canonicalized" 
  | "materialized" 
  | "viewed" 
  | "intent" 
  | "journaled" 
  | "drift";

export interface EventItem {
  id: string;
  ts: string;
  tenant: string;
  source_system: SourceSystem;
  entity: string;
  stage: EventStage;
  meta?: Record<string, any>;
}

export interface EventStreamState {
  events: EventItem[];
  isConnected: boolean;
  error: string | null;
}
