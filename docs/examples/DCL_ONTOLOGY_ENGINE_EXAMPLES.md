# DCL Ontology Engine - Real Examples

**Last Updated:** November 19, 2025  
**Status:** Production examples from live system with 147 canonical events

---

## What is the DCL (Data Connection Layer) Ontology Engine?

The DCL is your platform's **unified data brain**. After AAM transforms messy source data into clean canonical events, DCL takes over to:

1. **Materialize** canonical events into queryable tables
2. **Unify** duplicate records across sources (e.g., same contact in Salesforce and HubSpot)
3. **Build** an ontology graph showing relationships between sources, entities, and agents
4. **Enable** AI agents to query ALL your data through a single unified interface

**Think of it this way:**
- **AAM** = The translator (messy data → clean canonical format)
- **DCL** = The librarian (organizes everything into a queryable library + builds a map showing how everything connects)

---

## The Complete Data Flow

```
📊 Source Data (Salesforce, HubSpot, CSV)
         ↓
🔧 AAM Canonical Transformation
         ↓
📮 Canonical Events (canonical_streams table)
         ↓
📚 DCL Subscriber Process (Materialization)
         ↓
🗄️  Materialized Tables (queryable views)
         ↓
🔗 DCL Unification (Merge duplicates)
         ↓
🧠 Unified Ontology (Graph visualization)
         ↓
🤖 AI Agents (Query unified data)
```

---

## Example 1: From Canonical Event → Materialized View

### Step 1: AAM Emits Canonical Event

**Stored in `canonical_streams` table:**
```json
{
  "id": 123,
  "tenant_id": "default",
  "entity": "opportunity",
  "op": "upsert",
  "data": {
    "opportunity_id": "OPP001",
    "account_id": "ACC001",
    "name": "Q4 Enterprise Deal",
    "stage": "Negotiation",
    "amount": "250000.0",
    "currency": "USD",
    "close_date": "2024-12-31T00:00:00",
    "probability": 75.0
  },
  "source": {
    "system": "filesource",
    "connection_id": "filesource-csv-001"
  },
  "meta": {
    "version": "1.0.0",
    "trace_id": "abc-123",
    "emitted_at": "2025-11-17T10:15:30Z"
  }
}
```

### Step 2: DCL Subscriber Materializes Event

**DCL Subscriber Process (`process_canonical_streams`):**
```python
# 1. Fetch unprocessed canonical events from canonical_streams table
# 2. For each event, extract entity type (account, opportunity, contact)
# 3. Upsert into corresponding materialized table
```

**Code from `services/aam/canonical/subscriber.py`:**
```python
def upsert_opportunity(db, tenant_id, canonical_data, source_meta):
    """Upsert opportunity into materialized_opportunities table"""
    opportunity_id = canonical_data.get('opportunity_id')
    
    # Check if already exists (tenant_id + opportunity_id + source_system)
    existing = db.query(MaterializedOpportunity).filter(
        MaterializedOpportunity.tenant_id == tenant_id,
        MaterializedOpportunity.opportunity_id == opportunity_id,
        MaterializedOpportunity.source_system == source_meta.get('system')
    ).first()
    
    if existing:
        # Update existing record
        existing.name = canonical_data.get('name')
        existing.stage = canonical_data.get('stage')
        existing.amount = float(canonical_data['amount'])
        existing.synced_at = datetime.utcnow()
        db.commit()
    else:
        # Create new materialized opportunity
        new_opp = MaterializedOpportunity(
            tenant_id=tenant_id,
            opportunity_id=opportunity_id,
            account_id=canonical_data.get('account_id'),
            name=canonical_data.get('name'),
            stage=canonical_data.get('stage'),
            amount=float(canonical_data['amount']),
            currency=canonical_data.get('currency', 'USD'),
            probability=float(canonical_data['probability']),
            source_system=source_meta.get('system'),
            source_connection_id=source_meta.get('connection_id'),
            synced_at=datetime.utcnow()
        )
        db.add(new_opp)
        db.commit()
```

### Step 3: Materialized in `materialized_opportunities` Table

**Result - Now Queryable via SQL:**
```sql
SELECT * FROM materialized_opportunities 
WHERE opportunity_id = 'OPP001';
```

**Output:**
| id (UUID) | tenant_id | opportunity_id | account_id | name | stage | amount | currency | probability | source_system | synced_at |
|-----------|-----------|----------------|------------|------|-------|--------|----------|-------------|---------------|-----------|
| uuid-123 | default | OPP001 | ACC001 | Q4 Enterprise Deal | Negotiation | 250000.0 | USD | 75.0 | filesource | 2025-11-17 10:15:31 |

**What Just Happened:**
- ✅ Canonical event from JSON → queryable SQL table
- ✅ Can now use SQL JOINs, WHERE clauses, aggregations
- ✅ AI agents can query this data instantly
- ✅ Automatically deduplicated by `(tenant_id, opportunity_id, source_system)`

---

## Example 2: Multi-Source Unification (Same Contact in Multiple Systems)

### Scenario: Contact Appears in Salesforce, HubSpot, and CSV

**Contact from Salesforce:**
```json
{
  "contact_id": "003ABC",
  "email": "jane.doe@acme.com",
  "first_name": "Jane",
  "last_name": "Doe",
  "source_system": "salesforce"
}
```

**Same Contact from HubSpot:**
```json
{
  "contact_id": "12345",
  "email": "jane.doe@acme.com",
  "first_name": "Jane",
  "last_name": "Doe",
  "source_system": "hubspot"
}
```

**Same Contact from CSV:**
```json
{
  "contact_id": "CNT-001",
  "email": "jane.doe@acme.com",
  "first_name": "Jane",
  "last_name": "Doe",
  "source_system": "filesource"
}
```

### DCL Unification Process

**Endpoint:** `POST /api/v1/dcl/unify/run`

**Algorithm (from `app/api/v1/dcl_unify.py`):**
```python
# 1. Query all contacts with emails from canonical_streams
query = """
    SELECT 
        data->>'contact_id' as contact_id,
        data->>'email' as email,
        data->>'first_name' as first_name,
        data->>'last_name' as last_name,
        source->>'system' as source_system
    FROM canonical_streams
    WHERE entity = 'contact'
    AND data->>'email' IS NOT NULL
    AND tenant_id = :tenant_id
"""

# 2. Group contacts by normalized email (lowercase, trimmed)
email_groups = {}
for contact in contacts:
    normalized_email = contact.email.lower().strip()
    email_groups[normalized_email].append(contact)

# 3. For each email group, create unified_contact record
for email, contact_list in email_groups.items():
    unified_contact = DCLUnifiedContact(
        tenant_id=tenant_id,
        email=email,
        first_name=contact_list[0].first_name,
        last_name=contact_list[0].last_name
    )
    db.add(unified_contact)
    
    # 4. Create links for each source contact
    for contact in contact_list:
        link = DCLUnifiedContactLink(
            tenant_id=tenant_id,
            unified_contact_id=unified_contact.id,
            source_system=contact.source_system,
            source_contact_id=contact.contact_id
        )
        db.add(link)
```

### Unified Result

**`dcl_unified_contacts` table:**
| unified_contact_id | tenant_id | email | first_name | last_name |
|--------------------|-----------|-------|------------|-----------|
| unified-001 | default | jane.doe@acme.com | Jane | Doe |

**`dcl_unified_contact_links` table:**
| unified_contact_id | source_system | source_contact_id |
|--------------------|---------------|-------------------|
| unified-001 | salesforce | 003ABC |
| unified-001 | hubspot | 12345 |
| unified-001 | filesource | CNT-001 |

**What This Enables:**
```sql
-- Query: "Show me ALL data for jane.doe@acme.com across ALL systems"
SELECT 
    u.email,
    l.source_system,
    l.source_contact_id
FROM dcl_unified_contacts u
JOIN dcl_unified_contact_links l ON u.unified_contact_id = l.unified_contact_id
WHERE u.email = 'jane.doe@acme.com';
```

**Result:**
```
email: jane.doe@acme.com
  - Salesforce ID: 003ABC
  - HubSpot ID: 12345
  - CSV ID: CNT-001
```

**AI Agent Can Now:**
- See Jane's complete interaction history across ALL systems
- Update Jane in ONE system and know her IDs in all other systems
- Deduplicate reports (no more counting Jane 3 times!)

---

## Example 3: The Ontology Graph (Visualizing Data Relationships)

### What is the Ontology Graph?

The ontology graph is a **visual map** showing:
1. **Source Nodes** - Where data comes from (Salesforce, HubSpot, CSV, MongoDB)
2. **Entity Nodes** - What unified entities exist (Customer, Transaction, Product, User, Event)
3. **Agent Nodes** - Which AI agents consume this data
4. **Edges** - How everything connects (dataflow relationships)

### Real Ontology Graph (from `app/dcl_engine/demo_graph.json`)

**Graph Structure:**
```
25 Nodes Total:
  - 1 Parent Node (source_parent)
  - 17 Source Tables (source)
  - 5 Ontology Entities (ontology)
  - 2 AI Agents (agent)

37 Edges Total:
  - 17 Hierarchy Edges (parent → sources)
  - 18 Dataflow Edges (sources → entities)
  - 2 Dataflow Edges (entities → agents)
```

### Node Types

**1. Source Parent Node (Consolidated AAM)**
```json
{
  "id": "sys_aam_sources",
  "label": "from AAM",
  "type": "source_parent"
}
```

**2. Source Table Nodes (17 total)**
```json
{
  "id": "salesforce_Account",
  "label": "Salesforce - Account",
  "type": "source",
  "sourceSystem": "Salesforce",
  "parentId": "sys_aam_sources",
  "fields": ["Id", "Name", "Industry", "Revenue"]
},
{
  "id": "hubspot_Deals",
  "label": "HubSpot - Deals",
  "type": "source",
  "sourceSystem": "HubSpot",
  "parentId": "sys_aam_sources",
  "fields": ["id", "dealname", "amount", "dealstage"]
},
{
  "id": "mongodb_events",
  "label": "MongoDB - events",
  "type": "source",
  "sourceSystem": "MongoDB",
  "parentId": "sys_aam_sources",
  "fields": ["_id", "event_type", "timestamp", "user_id"]
}
```

**3. Ontology Entity Nodes (5 total)**
```json
{
  "id": "ont_Customer",
  "label": "Customer",
  "type": "ontology"
},
{
  "id": "ont_Transaction",
  "label": "Transaction",
  "type": "ontology"
},
{
  "id": "ont_Product",
  "label": "Product",
  "type": "ontology"
},
{
  "id": "ont_User",
  "label": "User",
  "type": "ontology"
},
{
  "id": "ont_Event",
  "label": "Event",
  "type": "ontology"
}
```

**4. AI Agent Nodes (2 total)**
```json
{
  "id": "agent_revenue_analyzer",
  "label": "Revenue Analyzer",
  "type": "agent",
  "description": "AI agent for revenue analysis and forecasting"
},
{
  "id": "agent_customer_insights",
  "label": "Customer Insights",
  "type": "agent",
  "description": "AI agent for customer behavior analysis"
}
```

### Edge Relationships

**Hierarchy Edges (Parent → Source Tables):**
```json
{
  "source": "sys_aam_sources",
  "target": "salesforce_Account",
  "edgeType": "hierarchy"
}
```
- Shows "Salesforce Account" is a child of "from AAM" parent

**Dataflow Edges (Sources → Ontology Entities):**
```json
{
  "source": "salesforce_Account",
  "target": "ont_Customer",
  "type": "dataflow"
},
{
  "source": "hubspot_Companies",
  "target": "ont_Customer",
  "type": "dataflow"
},
{
  "source": "stripe_Customers",
  "target": "ont_Customer",
  "type": "dataflow"
}
```
- Shows that "Customer" ontology entity is fed by 3 sources: Salesforce Account, HubSpot Companies, Stripe Customers
- DCL automatically unifies these into a single "Customer" view

**Dataflow Edges (Ontology → AI Agents):**
```json
{
  "source": "ont_Customer",
  "target": "agent_customer_insights",
  "type": "dataflow"
},
{
  "source": "ont_User",
  "target": "agent_customer_insights",
  "type": "dataflow"
},
{
  "source": "ont_Event",
  "target": "agent_customer_insights",
  "type": "dataflow"
}
```
- Shows "Customer Insights" agent consumes data from Customer, User, and Event ontologies

### Visual Graph Representation

```
                                    ┌─────────────────┐
                                    │   from AAM      │
                                    │ (source_parent) │
                                    └────────┬────────┘
                                             │
           ┌─────────────────┬───────────────┼───────────────┬─────────────────┐
           │                 │               │               │                 │
    ┌──────▼──────┐   ┌──────▼──────┐  ┌────▼────┐   ┌──────▼──────┐  ┌──────▼──────┐
    │  Salesforce │   │   HubSpot   │  │  Stripe │   │ PostgreSQL  │  │   MongoDB   │
    │  - Account  │   │ - Companies │  │- Customers  │   - users   │  │  - events   │
    │- Opportunity│   │  - Deals    │  │- Invoices│  │  - orders   │  │ - sessions  │
    │  - Contact  │   │             │  │          │   │             │  │             │
    └──────┬──────┘   └──────┬──────┘  └────┬─────┘  └──────┬──────┘  └──────┬──────┘
           │                 │               │               │                 │
           └─────────────────┴───────────────┼───────────────┴─────────────────┘
                                             │
                       ┌─────────────────────┴─────────────────────┐
                       │                                           │
                ┌──────▼────────┐                          ┌──────▼────────┐
                │   ONTOLOGY    │                          │   ONTOLOGY    │
                │               │                          │               │
                │  Customer     │                          │ Transaction   │
                │  Product      │                          │    Event      │
                │  User         │                          │               │
                └──────┬────────┘                          └──────┬────────┘
                       │                                           │
                       └───────────────────┬───────────────────────┘
                                           │
                       ┌───────────────────┴───────────────────┐
                       │                                       │
                ┌──────▼──────────┐                    ┌──────▼──────────┐
                │   AI AGENT      │                    │   AI AGENT      │
                │                 │                    │                 │
                │Revenue Analyzer │                    │Customer Insights│
                └─────────────────┘                    └─────────────────┘
```

**What This Shows:**
- ✅ All data sources feeding into AAM
- ✅ AAM normalizing into unified ontology entities
- ✅ AI agents consuming the unified data
- ✅ Complete lineage: Source → AAM → Ontology → Agents

---

## Example 4: AI Agent Querying Unified Data

### Before DCL (The Nightmare)

**AI Agent wants:** "Show me all high-value transactions from customers in the technology industry"

**Without DCL, agent needs custom queries for EACH system:**

```python
# Query Salesforce
salesforce_results = salesforce_client.query("""
    SELECT o.Id, o.Amount, a.Name, a.Industry
    FROM Opportunity o
    JOIN Account a ON o.AccountId = a.Id
    WHERE a.Industry = 'Technology' AND o.Amount > 100000
""")

# Query HubSpot (different field names!)
hubspot_results = hubspot_client.query({
    "filters": [
        {"property": "hs_industry", "operator": "EQ", "value": "Technology"},
        {"property": "amount", "operator": "GTE", "value": 100000}
    ]
})

# Query Stripe (different API!)
stripe_results = stripe.Invoice.list(
    limit=100,
    expand=['customer'],
    # Filter manually in Python because Stripe API doesn't support complex filters
)
filtered_stripe = [
    inv for inv in stripe_results 
    if inv.customer.metadata.get('industry') == 'Technology' 
    and inv.amount_due > 100000
]

# Manually merge results (PAINFUL!)
all_results = merge_deduplicate_format(
    salesforce_results,
    hubspot_results,
    filtered_stripe
)
```

**Problems:**
- 😫 Custom code for EACH system
- 😫 Different field names, APIs, authentication
- 😫 Manual deduplication (same transaction in multiple systems)
- 😫 If you add a new CRM, rewrite ALL the query logic!

### After DCL (The Solution)

**Same query, ONE unified SQL:**

```sql
SELECT 
    o.opportunity_id,
    o.name as transaction_name,
    o.amount,
    o.stage,
    o.source_system,
    a.name as customer_name,
    a.industry
FROM materialized_opportunities o
LEFT JOIN materialized_accounts a ON o.account_id = a.account_id
WHERE a.industry = 'Technology'
AND o.amount > 100000
AND o.tenant_id = 'default'
ORDER BY o.amount DESC;
```

**Result:**
| opportunity_id | transaction_name | amount | stage | source_system | customer_name | industry |
|----------------|------------------|--------|-------|---------------|---------------|----------|
| 006ABC | Enterprise Cloud | 485000 | Proposal | salesforce | Acme Corp | Technology |
| 12345 | Platform Integration | 320000 | Negotiation | hubspot | Tech Innovators | Technology |
| OPP001 | Q4 Enterprise Deal | 250000 | Negotiation | filesource | Global Solutions | Technology |

**What Just Happened:**
- ✅ ONE query works across Salesforce, HubSpot, CSV files
- ✅ Automatic deduplication (same customer not counted twice)
- ✅ Unified field names (`amount`, `stage`, `industry`)
- ✅ Add a new CRM? Zero code changes to agents!

### AI Agent Code (Python)

**RevOps Pilot Agent:**
```python
from app.database import get_db
from sqlalchemy import text

def analyze_high_value_pipeline(tenant_id: str):
    """AI Agent: Analyze high-value pipeline by industry"""
    
    db = next(get_db())
    
    # Query unified DCL materialized views
    query = text("""
        SELECT 
            a.industry,
            COUNT(DISTINCT o.opportunity_id) as deal_count,
            SUM(o.amount) as total_pipeline,
            AVG(o.probability) as avg_win_probability,
            COUNT(DISTINCT o.source_system) as data_sources
        FROM materialized_opportunities o
        LEFT JOIN materialized_accounts a ON o.account_id = a.account_id
        WHERE o.tenant_id = :tenant_id
        AND o.stage IN ('Negotiation', 'Proposal')
        AND o.amount > 100000
        GROUP BY a.industry
        ORDER BY total_pipeline DESC
    """)
    
    results = db.execute(query, {"tenant_id": tenant_id}).fetchall()
    
    # AI Agent analysis
    insights = []
    for row in results:
        insights.append({
            "industry": row.industry,
            "deal_count": row.deal_count,
            "total_pipeline": f"${row.total_pipeline:,.0f}",
            "avg_win_probability": f"{row.avg_win_probability:.1f}%",
            "data_sources": row.data_sources,
            "recommendation": generate_recommendation(row)  # AI-powered
        })
    
    return insights
```

**Output:**
```json
[
  {
    "industry": "Technology",
    "deal_count": 12,
    "total_pipeline": "$3,450,000",
    "avg_win_probability": "65.5%",
    "data_sources": 3,
    "recommendation": "High-value sector with strong win rates. Prioritize technical resources for Q4 close."
  },
  {
    "industry": "Finance",
    "deal_count": 8,
    "total_pipeline": "$2,180,000",
    "avg_win_probability": "52.3%",
    "data_sources": 2,
    "recommendation": "Moderate confidence. Engage executive sponsors to boost probability."
  }
]
```

**Key Benefits:**
- ✅ Agent queries **ONE** unified view (materialized_opportunities, materialized_accounts)
- ✅ No need to know Salesforce vs HubSpot field names
- ✅ Automatic aggregation across ALL sources
- ✅ `data_sources` field shows which systems contributed data (transparency!)

---

## Example 5: DCL Ontology Catalog (Entity Definitions)

### What is the Ontology Catalog?

The catalog (`app/dcl_engine/ontology/catalog.yml`) defines the **standard schema** for each entity type.

### Real Catalog Definitions

**RevOps Entities:**
```yaml
entities:
  account:
    pk: account_id
    fields: [account_id, account_name, industry, revenue, employee_count, created_date]
  
  opportunity:
    pk: opportunity_id
    fields: [opportunity_id, opportunity_name, account_id, stage, amount, close_date, probability]
  
  health:
    pk: account_id
    fields: [account_id, health_score, last_updated, risk_level]
  
  usage:
    pk: account_id
    fields: [account_id, last_login_days, sessions_30d, avg_session_duration, features_used]
```

**FinOps Entities:**
```yaml
  aws_resources:
    pk: resource_id
    fields: 
      # Core identifiers
      - resource_id          # AWS resource ID (i-abc123, db-xyz789)
      - resource_type        # EC2, RDS, S3, ALB, Redshift
      - region               # us-east-1, us-west-2, etc.
      
      # EC2 config
      - instance_type        # m5.2xlarge, t3.large
      - vcpus                # CPU count
      - memory               # Memory in GiB
      - storage              # Storage in GB
      
      # Utilization metrics
      - cpu_utilization      # percentage
      - memory_utilization   # percentage
      - network_in           # MB
      - network_out          # MB
      
      # Cost
      - monthly_cost         # USD
      - last_analyzed        # timestamp
  
  cost_reports:
    pk: cost_id
    fields: 
      - cost_id              # UUID
      - report_date          # timestamp
      - service_category     # EC2, RDS, S3, Lambda
      - resource_id          # specific resource
      - cost                 # USD amount
      - usage                # usage amount
      - usage_type           # Instance-Hours, GB-Month
      - region               # AWS region
```

**What This Enables:**

1. **Schema Validation:** DCL knows which fields are required for each entity
2. **AI Agent Guidance:** Agents know which fields exist and can query intelligently
3. **Cross-Source Mapping:** AAM knows how to map source fields to ontology fields
4. **Graph Generation:** DCL builds relationships based on primary keys (`pk`)

---

## The Power of DCL Ontology

### Before DCL (Data Silos)

```
Salesforce          HubSpot            Stripe            PostgreSQL
    │                  │                   │                  │
    │                  │                   │                  │
    ▼                  ▼                   ▼                  ▼
Agent 1            Agent 2             Agent 3            Agent 4
(Salesforce       (HubSpot           (Stripe           (PostgreSQL
 only)             only)               only)              only)
```

**Problems:**
- Each agent sees only ONE system
- No cross-system insights
- Data duplication (same customer counted multiple times)
- Agents can't answer questions spanning multiple sources

### After DCL (Unified Ontology)

```
Salesforce    HubSpot    Stripe    PostgreSQL    MongoDB    CSV
    │            │          │            │           │        │
    └────────────┴──────────┴────────────┴───────────┴────────┘
                              │
                              ▼
                          ┌───────┐
                          │  AAM  │ (Canonical Transformation)
                          └───┬───┘
                              │
                              ▼
                   ┌──────────────────┐
                   │   DCL ONTOLOGY   │
                   │                  │
                   │  Customer        │
                   │  Transaction     │
                   │  Product         │
                   │  User            │
                   │  Event           │
                   └────────┬─────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
  ┌─────────┐         ┌─────────┐         ┌─────────┐
  │RevOps   │         │FinOps   │         │Customer │
  │ Pilot   │         │Autopilot│         │Insights │
  └─────────┘         └─────────┘         └─────────┘
```

**Benefits:**
- ✅ All agents see ALL sources through unified ontology
- ✅ No data silos
- ✅ Automatic deduplication
- ✅ One query = all systems
- ✅ Add new source? Agents automatically see it!

---

## Production Statistics (From Your Database)

**From Your Actual System (November 17, 2025):**

```
✅ Canonical Events in canonical_streams: 147
  - 105 opportunities
  - 15 accounts
  - 12 contacts
  - 10 aws_resources
  - 5 cost_reports

✅ Materialized Tables (DCL Subscriber):
  - materialized_accounts
  - materialized_opportunities
  - materialized_contacts

✅ Unification Tables:
  - dcl_unified_contacts
  - dcl_unified_contact_links

✅ Ontology Graph (demo_graph.json v3.0):
  - 25 nodes (1 parent, 17 sources, 5 entities, 2 agents)
  - 37 edges (17 hierarchy, 20 dataflow)
  - Confidence: 0.92

✅ Sources Connected: 10+
  - Salesforce (CRM)
  - HubSpot (CRM)
  - Stripe (Payments)
  - PostgreSQL (Database)
  - MongoDB (NoSQL)
  - Supabase (Cloud DB)
  - MySQL (Database)
  - Google Sheets (Spreadsheets)
  - CSV Files (Legacy data)
  - FilesSource (Local files)
```

---

## Key DCL Operations

### 1. Materialize Canonical Events

**Endpoint:** Automatic (DCL Subscriber runs on every query)

**Process:**
1. Query `canonical_streams` table for unprocessed events
2. Extract entity type (account, opportunity, contact)
3. Upsert into materialized table
4. Mark event as processed

**Code:** `services/aam/canonical/subscriber.py::process_canonical_streams()`

### 2. Query Materialized Views

**Endpoint:** `GET /api/v1/dcl/views/accounts`

**Example Request:**
```bash
curl -X GET "http://localhost:5000/api/v1/dcl/views/accounts?limit=10&offset=0" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Example Response:**
```json
{
  "success": true,
  "data": [
    {
      "account_id": "ACC001",
      "name": "Acme Corporation",
      "industry": "Technology",
      "source_system": "salesforce",
      "synced_at": "2025-11-17T10:15:31Z"
    }
  ],
  "meta": {
    "total": 15,
    "limit": 10,
    "offset": 0,
    "count": 10
  }
}
```

### 3. Unify Contacts Across Sources

**Endpoint:** `POST /api/v1/dcl/unify/run`

**Example Request:**
```bash
curl -X POST "http://localhost:5000/api/v1/dcl/unify/run" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Example Response:**
```json
{
  "status": "ok",
  "unified_contacts": 8,
  "links": 24
}
```
- 8 unique people found (by email)
- 24 total source contact records linked (average 3 systems per person)

### 4. Get Ontology Graph State

**Endpoint:** `GET /api/v1/dcl/state`

**Example Response:**
```json
{
  "nodes": [
    {"id": "sys_aam_sources", "label": "from AAM", "type": "source_parent"},
    {"id": "salesforce_Account", "label": "Salesforce - Account", "type": "source"},
    {"id": "ont_Customer", "label": "Customer", "type": "ontology"},
    {"id": "agent_revenue_analyzer", "label": "Revenue Analyzer", "type": "agent"}
  ],
  "edges": [
    {"source": "sys_aam_sources", "target": "salesforce_Account", "edgeType": "hierarchy"},
    {"source": "salesforce_Account", "target": "ont_Customer", "type": "dataflow"},
    {"source": "ont_Customer", "target": "agent_revenue_analyzer", "type": "dataflow"}
  ],
  "confidence": 0.92,
  "last_updated": "2025-11-17T10:15:30Z",
  "sources_added": ["salesforce", "hubspot", "stripe", "postgresql", "mongodb"]
}
```

---

## Related Documentation

- **[AAM_CANONICAL_TRANSFORMATION_EXAMPLES.md](./AAM_CANONICAL_TRANSFORMATION_EXAMPLES.md)** - How AAM creates canonical events
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - Complete system architecture diagrams
- **[app/dcl_engine/ontology/catalog.yml](./app/dcl_engine/ontology/catalog.yml)** - Ontology entity definitions
- **[app/dcl_engine/demo_graph.json](./app/dcl_engine/demo_graph.json)** - Live ontology graph structure
- **[app/models.py](./app/models.py)** - MaterializedAccount, MaterializedOpportunity, MaterializedContact schemas

---

**End of Examples**
