# Discovery Demo - Enterprise-Grade Upgrade

## 🎯 Overview

The Discovery Demo page has been transformed into an **enterprise-grade demo** that showcases real-world complexity and how AutonomOS abstracts it through AI, RAG, and intelligent automation.

**Core Philosophy:** Show complexity → Explain why it's hard → Demonstrate how AOS solves it

---

## ✅ Implementation Complete

All enhancements have been implemented across **2 new files** and **1 updated file**:

### Files Created

1. **`frontend/src/demo/demoDclMappings.ts`** - DCL field mappings data module
2. **`DISCOVERY_DEMO_ENTERPRISE_UPGRADE.md`** - This documentation

### Files Modified

3. **`frontend/src/components/DiscoveryDemoPage.tsx`** - Complete rewrite with enterprise features

---

## 🚀 Part 1: Auto-Selection Semantics

### Behavior Changes

**Before:**
- All assets start unchecked
- User manually selects which assets to include
- No guidance on selection

**After:**
- ✅ All `READY_FOR_CONNECT` assets are **auto-selected by default** on page load
- ✅ Assets in other states (`PARKED`, `UNKNOWN`, `CONNECTED`) are **disabled** (cannot be selected)
- ✅ Selections persist when closing/reopening vendor modals
- ✅ Clear messaging that AOS made the selection, user can deselect

### UI Updates

**Vendor Asset Modal (inside each vendor view):**
```
[Cyan info box at top of modal]
✓ AutonomOS has automatically selected all ready assets for this demo. 
You can deselect any that you don't want to include.
```

**Connect Selected Assets Section (main page):**
```
AutonomOS has automatically selected 22 assets across 4 vendors for this demo pipeline.
You may deselect assets in the vendor views before running the pipeline.

[Connect Selected Assets] button
```

**Guardrail Message (when no assets selected):**
```
⚠️ Select at least one ready asset to include in the demo pipeline.
```

### Technical Implementation

```typescript
// Auto-select on component mount
useEffect(() => {
  const autoSelected: SelectedAssets = {};
  mockAssets.forEach(asset => {
    if (asset.state === 'READY_FOR_CONNECT') {
      autoSelected[asset.id] = true;
    }
  });
  setSelectedAssets(autoSelected);
}, []);

// Disable non-ready assets
<input
  type="checkbox"
  checked={selectedAssets[asset.id] || false}
  onChange={() => handleAssetToggle(asset.id)}
  disabled={asset.state !== 'READY_FOR_CONNECT'}
/>
```

---

## 🏗️ Part 2: Enterprise Pipeline Stage Descriptions

All 4 pipeline stage cards now follow the pattern:
1. **What it does** - Clear, concise description
2. **Why it's hard** - Real enterprise pain points (in italics, gray text)
3. **How AOS handles it** - AI/RAG/automation explanation (in cyan text)

### Stage 1: AOD Discovery

**Text:**
```
Assets discovered and triaged automatically at the SaaS / service / database / host level.

Normally: spreadsheets, interviews, and chasing teams just to figure out what's 
actually running in each tenant.

AOS uses log and config telemetry plus AI classifiers to tag vendor, environment, 
and risk, and to surface shadow IT.
```

**Key Points:**
- Static (no dynamic interpolation)
- Emphasizes automation vs. manual spreadsheets
- Highlights AI classification

### Stage 2: AAM Connections

**Text (with dynamic interpolation):**
```
Configures and validates connectors for the selected assets.

Normally: per-connector OAuth apps, scope tuning, token rotation, API versions, 
rate limits, and per-tenant quirks.

AOS applies connector recipes and AI over our configuration corpus to choose auth flows, 
scopes, and backoff policies for Salesforce, MongoDB, Supabase and 22 selected assets.

[View connector details →]
```

**Key Points:**
- **Dynamic vendor list**: `{selectedVendorNames.join(', ')}`
- **Dynamic asset count**: `{selectedCount}`
- New button: "View connector details" (opens ConnectorDetailsModal)
- Emphasizes AI-driven configuration vs. manual YAML

### Stage 3: DCL Mapping

**Text:**
```
Builds unified entities and field mappings (e.g. customer_360) on top of connected systems.

Normally: weeks of debating column names, IDs, and joins across CRM, billing, events, 
and legacy exports.

AOS analyzes schemas and ingested data across systems to propose canonical fields and joins, 
with confidence scores, then surfaces them for review.

[View field mappings →]
```

**Key Points:**
- References `customer_360` canonical entity
- New button: "View field mappings" (opens FieldMappingsModal)
- Emphasizes schema analysis + confidence scoring
- Mentions governance workflows (not implemented in demo)

### Stage 4: Agent Execution

**Text:**
```
Agents query the unified view instead of raw tables.

Normally: hand-written SQL, multiple BI tools, and manual joins across CRM, 
usage, and billing data.

AOS agents run over DCL's unified entities, apply risk and business policies, 
and return explainable results—no manual SQL or join logic.
```

**Key Points:**
- Emphasizes unified view vs. raw tables
- No manual SQL or joins
- References explainable results

### Agent Output Panel (appears after success)

**New section that appears when pipeline completes:**
```
Agent Output
───────────────────────────────────────────────────
Query:
"Show risky customer-facing services over $1M ARR across Salesforce, 
MongoDB, Supabase, and Legacy Files."

Agent Response:
• Found 12 high-value accounts with ARR > $1M across unified customer_360 view
• Identified 3 risk signals: elevated error_rate (MongoDB events), overdue invoices 
  (Supabase), churn flags (Legacy)
• Cross-referenced with Salesforce opportunity pipeline to surface at-risk renewals

Result: Unified view enabled in 4.1 seconds with no manual joins or SQL
```

**Key Points:**
- Realistic cross-vendor query
- Shows how unified view simplifies complex queries
- Highlights risk scoring and business context
- Performance metric (4.1s)

---

## 🔌 Part 3: AAM Connector Details Modal

### Trigger
Click **"View connector details"** button inside AAM Connections stage card.

### Modal Structure

**Header:**
```
AAM Connector Details
Configuration for demo tenant connectors
```

**Content:** One section per vendor with:
- Vendor name (in vendor color)
- **Authentication** section
- **Contract** section
- **How AOS configured this** note (cyan info box)

### Vendor Details

#### Salesforce (Cyan #0BCAD9)

**Authentication:**
- OAuth2 with short-lived access tokens; refresh token rotation enabled.
- Scopes selected from connector recipes: api, refresh_token, offline_access.

**Contract:**
- API version v59.0; endpoints: /sobjects/Account, /sobjects/Opportunity, /query.
- Pagination: nextRecordsUrl; rate-limit policy: exponential backoff with jitter.

**How AOS configured this:**
Configuration inferred from connector recipes plus AI over our historical configuration corpus. No manual YAML or one-off scripts.

#### MongoDB (Green #10B981)

**Authentication:**
- TLS-enforced connection string with SRV; credentials stored in vault.

**Contract:**
- Collections: users, events. Read preference: secondaryPreferred.
- Topology and timeouts chosen from best-practice heuristics.

**How AOS configured this:**
Topology and timeouts chosen from best-practice heuristics and AI analysis.

#### Supabase (Purple #A855F7)

**Authentication:**
- Service role key with RLS bypass for system operations.
- TLS 1.2+ required; certificate pinning enabled.

**Contract:**
- Tables: customers, invoices, usage_events. Schema: public.
- Connection pooling: PgBouncer session mode with 10 max connections.

**How AOS configured this:**
Connection parameters optimized from Supabase best practices and schema analysis.

#### Legacy Files (Orange #F97316)

**Authentication:**
- S3-compatible bucket access with IAM role credentials.
- Server-side encryption (SSE-S3) enforced on all objects.

**Contract:**
- Buckets: customer-exports, legacy-backups. Format: CSV, JSON.
- Lifecycle: 90-day retention with automatic archival to Glacier.

**How AOS configured this:**
Bucket discovery and format detection via AI-powered file sampling.

### Technical Notes

- All data is **static/hard-coded** (no backend calls)
- Color-coded by vendor for visual consistency
- Realistic technical details (OAuth scopes, API versions, connection strings)
- Emphasizes AI-driven configuration vs. manual setup

---

## 🗺️ Part 4: DCL Field Mappings Modal

### Trigger
Click **"View field mappings"** button inside DCL Mapping stage card.

### Modal Structure

**Header:**
```
DCL Field Mappings – customer_360
Unified customer entity for demo tenant
```

**Description (purple info box):**
```
DCL analyzes schemas and ingested data across Salesforce, MongoDB, Supabase, 
and Legacy Files to propose a unified customer entity.
```

### Field Mappings Table

**Columns:**
- Canonical Field (cyan monospace code)
- Type (gray badge: string, number, date, boolean)
- Sources (vendor-colored chips with field path and confidence %)

**9 Canonical Fields with Source Mappings:**

#### 1. customer_id (string)
- **Salesforce** · Account.Id · **97%**
- **MongoDB** · users._id · **93%**
- **Supabase** · customers.customer_id · **96%**
- **Legacy Files** · legacy_customers.customer_id · **90%**

#### 2. customer_name (string)
- **Salesforce** · Account.Name · **98%**
- **Supabase** · customers.full_name · **94%**
- **Legacy Files** · legacy_customers.name · **91%**

#### 3. arr (number)
- **Salesforce** · Opportunity.Amount · **95%**
- **Supabase** · invoices.total_amount · **90%**

#### 4. last_activity_at (date)
- **MongoDB** · events.timestamp · **95%**
- **Salesforce** · Task.LastModifiedDate · **88%**

#### 5. churn_flag (boolean)
- **Legacy Files** · churn_flags.flag · **99%**

#### 6. risk_score (number)
- **MongoDB** · events.error_rate · **86%**
- **Supabase** · invoices.overdue_balance · **89%**

#### 7. email (string)
- **Salesforce** · Contact.Email · **99%**
- **MongoDB** · users.email · **96%**
- **Supabase** · customers.email_address · **94%**

#### 8. account_status (string)
- **Salesforce** · Account.Status__c · **92%**
- **Supabase** · customers.status · **91%**
- **MongoDB** · users.account_state · **88%**

#### 9. created_at (date)
- **Salesforce** · Account.CreatedDate · **98%**
- **MongoDB** · users.created_at · **97%**
- **Supabase** · customers.created_at · **96%**
- **Legacy Files** · legacy_customers.signup_date · **89%**

### Footer Explanation (cyan info box)

```
How AOS generated this: AOS uses ontologies, naming heuristics, and data profiling 
to propose canonical fields and joins. Confidence scores indicate how strong each 
mapping is; lower-confidence candidates can be routed to governance workflows for 
review (not shown in this demo).
```

### Technical Implementation

**Data Module (`demoDclMappings.ts`):**
```typescript
export type Vendor = 'salesforce' | 'mongodb' | 'supabase' | 'legacy';

export interface SourceField {
  vendor: Vendor;
  fieldPath: string;
  confidence: number; // 0-1
}

export interface FieldMappingRow {
  canonicalField: string;
  type: 'string' | 'number' | 'date' | 'boolean';
  sources: SourceField[];
}

export const demoCustomer360Mappings: FieldMappingRow[];
```

**Helper Functions:**
```typescript
getVendorDisplayName(vendor: Vendor): string
getVendorColor(vendor: Vendor): string // Returns hex color
```

**UI Rendering:**
- Vendor-colored chips with inline styles
- Field paths in monospace font
- Confidence percentages (0-100)
- Responsive table layout

---

## 🧹 Part 5: Removed "Sample" from UI

### Search & Replace Actions

**All instances of "sample" removed from demo UI:**

| Before | After |
|--------|-------|
| "sample data" | "demo tenant dataset" or "ingested dataset" |
| "sample mapping" | "field mapping" |
| "sample query" | "demo query" or "query" |

### Verification

Searched entire `DiscoveryDemoPage.tsx` and demo modules:
- ✅ No "sample" in user-facing strings
- ✅ Uses "demo tenant" or "demo pipeline" instead
- ✅ Technical terms like "dataset", "query", "mapping" without "sample" qualifier

---

## 📊 Key Metrics

### Code Changes

- **Lines added:** ~700+
- **New TypeScript types:** 3 interfaces, 1 type alias
- **New modals:** 2 (ConnectorDetailsModal, FieldMappingsModal)
- **Updated components:** VendorModal, PipelineStage, main page
- **Static data entries:** 4 connectors, 9 field mappings, 35 assets

### User Experience Improvements

1. **Auto-selection:** 22 assets selected by default (saves 22 clicks)
2. **Enterprise context:** 4 stage cards × 3 paragraphs = 12 educational text blocks
3. **Deep dive modals:** 2 modals with detailed technical information
4. **Visual enhancements:** Color-coded vendor chips, confidence percentages
5. **Dynamic interpolation:** Real-time asset/vendor counts in descriptions

### Enterprise Storytelling

**Pain Points Highlighted:**
- Spreadsheets and manual discovery
- Per-connector OAuth complexity
- Weeks of schema mapping debates
- Hand-written SQL and manual joins

**AOS Solutions Demonstrated:**
- AI classifiers for discovery
- Connector recipes + configuration corpus
- Schema analysis + confidence scoring
- Unified entities for agent queries

---

## 🎨 Design Patterns

### Color Coding

- **Salesforce:** Cyan (#0BCAD9)
- **MongoDB:** Green (#10B981)
- **Supabase:** Purple (#A855F7)
- **Legacy Files:** Orange (#F97316)

### Text Styling Hierarchy

1. **What it does** - Normal gray text
2. **Why it's hard** - Italic gray text (normalizes pain points)
3. **How AOS handles it** - Cyan text (highlights solution)

### Modal Structure

- Dark gray background (#1F2937, #111827)
- Bordered sections for clarity
- Info boxes with cyan/purple backgrounds
- Vendor-specific accent colors
- Consistent "Close" button placement

### Confidence Visualization

- High confidence (95-100%): Strong mapping
- Medium confidence (85-94%): Good mapping
- Lower confidence (80-84%): Review candidate
- Displayed as percentage with vendor color

---

## 🚀 How to Use (User Guide)

### Step 1: Review Auto-Selected Assets

1. Navigate to `/demo-discovery`
2. See **22 assets auto-selected** across 4 vendors
3. Click any **"View Assets"** button
4. Modal shows: ✓ "AutonomOS has automatically selected all ready assets"
5. Deselect any assets you don't want (optional)

### Step 2: Explore Vendor Details

1. In AAM Connections stage card, click **"View connector details"**
2. Review auth flows, API versions, rate limits for each vendor
3. See how AOS uses AI to configure connectors
4. Close modal

### Step 3: Explore Field Mappings

1. In DCL Mapping stage card, click **"View field mappings"**
2. Review 9 canonical fields with source mappings
3. See confidence scores for each mapping
4. Understand how AOS proposes unified schema
5. Close modal

### Step 4: Run Pipeline

1. Click **"Connect Selected Assets"** button
2. Watch 4-stage animation:
   - AOD Discovery (instant)
   - AAM Connections (1.5s)
   - DCL Mapping (2.8s)
   - Agent Execution (4.1s)
3. See Agent Output panel with unified query results

### Step 5: Read Stage Descriptions

Each stage card explains:
- What the system does
- Why it's hard in enterprises
- How AOS solves it with AI/RAG

---

## 🔧 Technical Architecture

### Component Hierarchy

```
DiscoveryDemoPage
├── Summary Cards (4)
├── Vendor Cards (4)
│   └── → VendorModal (conditional)
│       └── Asset Table with auto-selection
├── Connect Section
│   ├── Selection Summary (dynamic)
│   ├── Connect Button
│   ├── Warning (conditional)
│   └── Pipeline Stages (4)
│       ├── AOD Discovery
│       ├── AAM Connections → ConnectorDetailsModal
│       ├── DCL Mapping → FieldMappingsModal
│       └── Agent Execution
└── Agent Output Panel (conditional on success)
```

### State Management

```typescript
// Auto-selected on mount
const [selectedAssets, setSelectedAssets] = useState<SelectedAssets>({});

// Modal visibility
const [selectedVendor, setSelectedVendor] = useState<Vendor | null>(null);
const [showConnectorDetails, setShowConnectorDetails] = useState(false);
const [showFieldMappings, setShowFieldMappings] = useState(false);

// Pipeline animation
const [pipelineStatus, setPipelineStatus] = useState<PipelineStatus>({...});
const [showWarning, setShowWarning] = useState(false);
```

### Data Flow

```
Page Load
  └─> Auto-select READY_FOR_CONNECT assets (useEffect)
      └─> Update selectedAssets state
          └─> Compute selectedCount, selectedVendorSet
              └─> Render dynamic text in UI

User Clicks "View Assets"
  └─> Open VendorModal
      └─> Show cyan info box about auto-selection
          └─> User can deselect assets
              └─> Selection persists when modal closes

User Clicks "View connector details"
  └─> Open ConnectorDetailsModal
      └─> Render static connector configs
          └─> Show auth, contract, AOS notes

User Clicks "View field mappings"
  └─> Open FieldMappingsModal
      └─> Render demoCustomer360Mappings table
          └─> Show canonical fields + sources + confidence

User Clicks "Connect Selected Assets"
  └─> Validate selectedCount > 0
      └─> Run 4-stage animation with setTimeout
          └─> Show Agent Output on success
```

---

## ✅ Success Criteria Met

### Part 1: Selection Semantics ✓
- ✅ Auto-select `READY_FOR_CONNECT` assets on load
- ✅ Disable non-ready assets
- ✅ Persist selections across modal open/close
- ✅ Update modal text: "AutonomOS has automatically selected..."
- ✅ Update main section text: "AutonomOS has automatically selected X assets..."
- ✅ Guardrail message: "Select at least one ready asset..."

### Part 2: Pipeline Cards ✓
- ✅ Stage 1 (AOD): What/Why/How text
- ✅ Stage 2 (AAM): Dynamic vendor list + count, "View connector details" button
- ✅ Stage 3 (DCL): References customer_360, "View field mappings" button
- ✅ Stage 4 (Agent): Unified view explanation
- ✅ Agent Output panel: Realistic cross-vendor query with results

### Part 3: AAM Connector Details ✓
- ✅ Modal with 4 vendor sections
- ✅ Auth + Contract details per vendor
- ✅ "How AOS configured this" notes
- ✅ Realistic technical specifications
- ✅ Color-coded by vendor

### Part 4: DCL Field Mappings ✓
- ✅ Created `demoDclMappings.ts` module
- ✅ TypeScript types: Vendor, SourceField, FieldMappingRow
- ✅ 9 canonical fields with source mappings
- ✅ Modal with table displaying mappings
- ✅ Vendor-colored chips with confidence percentages
- ✅ "How AOS generated this" explanation

### Part 5: Remove "Sample" ✓
- ✅ Searched all demo UI code
- ✅ No "sample" in user-facing strings
- ✅ Uses "demo tenant", "query", "mapping" instead

---

## 🎯 Key Takeaways

### For Technical Stakeholders

**This demo proves:**
1. AOS automates complex enterprise tasks (discovery, connection, mapping)
2. AI/RAG powers intelligent configuration and schema analysis
3. Unified entities eliminate manual SQL and joins
4. Confidence scoring enables governance workflows
5. Platform handles OAuth, rate limits, pagination, encryption

### For Non-Technical Stakeholders

**This demo shows:**
1. Weeks of work → Seconds of automation
2. Manual spreadsheets → AI-powered discovery
3. Per-connector setup → Recipe-driven configuration
4. Schema debates → Automated proposals with confidence
5. Complex SQL → Natural language queries

### Enterprise Value Proposition

**Without AOS:**
- Spreadsheets to track assets
- Manual OAuth app setup per connector
- Weeks of schema mapping debates
- Hand-written SQL for cross-system queries
- Shadow IT risk

**With AOS:**
- Automated discovery with AI classification
- Connector recipes + AI configuration
- Schema analysis with confidence scoring
- Unified entities for agent queries
- Risk detection and governance

---

## 📝 Future Enhancements (Out of Scope)

- Real AOD API integration (optional toggle)
- Real AAM connector status from backend
- Real DCL graph visualization integration
- Edit/approve field mappings inline
- Export mappings to CSV/JSON
- Filtering and search in modals
- Historical confidence score trends
- Governance workflow simulation
- Multi-tenant demo (switch tenants)
- Agent marketplace integration

---

## 🎉 Status: Complete and Production-Ready

All enterprise-grade enhancements have been implemented, tested, and deployed.

**Access the demo:** Navigate to `/demo-discovery` in the AutonomOS platform.

**Last Updated:** November 20, 2025
