export type Vendor = 'salesforce' | 'mongodb' | 'supabase' | 'legacy';

export interface SourceField {
  vendor: Vendor;
  fieldPath: string;
  confidence: number;
}

export interface FieldMappingRow {
  canonicalField: string;
  type: 'string' | 'number' | 'date' | 'boolean';
  sources: SourceField[];
}

export const demoCustomer360Mappings: FieldMappingRow[] = [
  {
    canonicalField: 'customer_id',
    type: 'string',
    sources: [
      { vendor: 'salesforce', fieldPath: 'Account.Id', confidence: 0.97 },
      { vendor: 'mongodb', fieldPath: 'users._id', confidence: 0.93 },
      { vendor: 'supabase', fieldPath: 'customers.customer_id', confidence: 0.96 },
      { vendor: 'legacy', fieldPath: 'legacy_customers.customer_id', confidence: 0.90 }
    ]
  },
  {
    canonicalField: 'customer_name',
    type: 'string',
    sources: [
      { vendor: 'salesforce', fieldPath: 'Account.Name', confidence: 0.98 },
      { vendor: 'supabase', fieldPath: 'customers.full_name', confidence: 0.94 },
      { vendor: 'legacy', fieldPath: 'legacy_customers.name', confidence: 0.91 }
    ]
  },
  {
    canonicalField: 'arr',
    type: 'number',
    sources: [
      { vendor: 'salesforce', fieldPath: 'Opportunity.Amount', confidence: 0.95 },
      { vendor: 'supabase', fieldPath: 'invoices.total_amount', confidence: 0.90 }
    ]
  },
  {
    canonicalField: 'last_activity_at',
    type: 'date',
    sources: [
      { vendor: 'mongodb', fieldPath: 'events.timestamp', confidence: 0.95 },
      { vendor: 'salesforce', fieldPath: 'Task.LastModifiedDate', confidence: 0.88 }
    ]
  },
  {
    canonicalField: 'churn_flag',
    type: 'boolean',
    sources: [
      { vendor: 'legacy', fieldPath: 'churn_flags.flag', confidence: 0.99 }
    ]
  },
  {
    canonicalField: 'risk_score',
    type: 'number',
    sources: [
      { vendor: 'mongodb', fieldPath: 'events.error_rate', confidence: 0.86 },
      { vendor: 'supabase', fieldPath: 'invoices.overdue_balance', confidence: 0.89 }
    ]
  },
  {
    canonicalField: 'email',
    type: 'string',
    sources: [
      { vendor: 'salesforce', fieldPath: 'Contact.Email', confidence: 0.99 },
      { vendor: 'mongodb', fieldPath: 'users.email', confidence: 0.96 },
      { vendor: 'supabase', fieldPath: 'customers.email_address', confidence: 0.94 }
    ]
  },
  {
    canonicalField: 'account_status',
    type: 'string',
    sources: [
      { vendor: 'salesforce', fieldPath: 'Account.Status__c', confidence: 0.92 },
      { vendor: 'supabase', fieldPath: 'customers.status', confidence: 0.91 },
      { vendor: 'mongodb', fieldPath: 'users.account_state', confidence: 0.88 }
    ]
  },
  {
    canonicalField: 'created_at',
    type: 'date',
    sources: [
      { vendor: 'salesforce', fieldPath: 'Account.CreatedDate', confidence: 0.98 },
      { vendor: 'mongodb', fieldPath: 'users.created_at', confidence: 0.97 },
      { vendor: 'supabase', fieldPath: 'customers.created_at', confidence: 0.96 },
      { vendor: 'legacy', fieldPath: 'legacy_customers.signup_date', confidence: 0.89 }
    ]
  }
];

export function getVendorDisplayName(vendor: Vendor): string {
  const names: Record<Vendor, string> = {
    salesforce: 'Salesforce',
    mongodb: 'MongoDB',
    supabase: 'Supabase',
    legacy: 'Legacy Files'
  };
  return names[vendor];
}

export function getVendorColor(vendor: Vendor): string {
  const colors: Record<Vendor, string> = {
    salesforce: '#0BCAD9',
    mongodb: '#10B981',
    supabase: '#A855F7',
    legacy: '#F97316'
  };
  return colors[vendor];
}
