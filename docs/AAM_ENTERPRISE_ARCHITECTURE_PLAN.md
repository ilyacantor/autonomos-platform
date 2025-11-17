# AAM Enterprise Architecture Plan
## Scaling to 1000+ Connectors in Production

**Date:** November 17, 2025  
**Status:** Architecture Review & Planning  
**Focus:** Auto-connection and auto-mapping capabilities for enterprise-scale deployment

---

## Executive Summary

**Challenge:** Scale AutonomOS Adaptive API Mesh (AAM) to handle 100s-1000s of data connectors in production while maintaining intelligent auto-connection and auto-mapping with minimal human intervention.

**Critical Finding:** Initial plan would NOT scale to enterprise requirements due to:
- Unsustainable LLM costs ($500 per onboarding cycle for 1000 connectors)
- Multi-hour onboarding latency (27+ hours sequential)
- YAML file management doesn't scale (1000s of git files)
- Hand-coded connectors require 500 lines per connector
- No multi-tenant resource isolation

**Solution:** Enterprise architecture with 6 core principles:
1. RAG-First, LLM-Last (95% RAG, 5% LLM) → 20x cost reduction
2. Database-Backed Mapping Registry → Runtime updates, versioning, audit trail
3. Generic Connector Framework → Config-driven, not hand-coded
4. Distributed Event-Driven Workers → Parallel processing, auto-scaling
5. Multi-Tenant Resource Isolation → Quotas, rate limiting, table partitioning
6. Enterprise Observability → OpenTelemetry, per-tenant metrics

**Impact:**
- Onboarding time: 27 hours → <10 minutes (162x faster)
- LLM costs: $500 → $25 per cycle (20x cheaper)
- Code per connector: 500 lines → 100 line JSON config
- Scalability: 10-20 connectors → 1000+ connectors

---

## Context: Initial Plan

### Objectives
1. **Expand AAM Connections:** Increase from 4 → 10+ active connectors across equal domains (RevOps, FinOps, SupportOps, MarketingOps)
2. **Build Monitoring Dashboard:** Real-time visibility into auto-connection, auto-mapping coverage, HITL review queue, LLM proposals

### Proposed Connector Expansion

**Priority 1: Activate Existing YAML Mappings (8 available)**
- HubSpot (RevOps) - YAML exists
- Zendesk (SupportOps) - YAML exists
- Pipedrive (RevOps) - YAML exists
- Dynamics 365 (RevOps) - YAML exists

**Priority 2: Add New Entity Types**
- Stripe (FinOps) - Need YAML
- Intercom (MarketingOps) - Need YAML
- Google Analytics (MarketingOps) - Need YAML
- AWS CloudWatch (FinOps) - Partial YAML

**Target:** 10-12 active connectors demonstrating cross-domain unification

### Proposed Monitoring Dashboard

**7 Core Components:**
1. Service Status Panel (Schema Observer, RAG Engine, Drift Repair Agent)
2. Key Metrics Cards (Connections, Drift Events, Auto-Repairs, Avg Confidence)
3. Connection Health Table (Status, Last Sync, Events/hr, Coverage %)
4. Drift Detection Timeline (7-day time-series)
5. Mapping Coverage Chart (Bar chart by connector)
6. Auto-Repair Activity Feed (Real-time repair log)
7. Canonical Event Stats (Entity breakdown donut chart)

---

## Scalability Analysis: Why Initial Plan Fails at Enterprise Scale

### Issue 1: LLM-per-Field Approach (Cost/Latency Explosion)

**Problem:**
```
1000 connectors × 50 fields avg = 50,000 LLM calls
Cost: $0.01/call × 50,000 = $500 per onboarding cycle
Latency: 2s/call × 50,000 = 27 hours sequential
```

**Why This Fails:**
- ❌ Unsustainable cost at scale ($6,000/year for monthly re-scanning)
- ❌ Multi-hour onboarding time blocks user productivity
- ❌ LLM rate limits (10k requests/min) throttle concurrent onboarding
- ❌ No way to batch/parallelize effectively with sequential field processing

---

### Issue 2: YAML Files Don't Scale

**Problem:**
```
services/aam/canonical/mappings/
├── connector1.yaml
├── connector2.yaml
├── ... (1000 files)
└── connector1000.yaml
```

**Why This Fails:**
- ❌ Git repo bloat (1000s of files, slow clones/pulls)
- ❌ No versioning/rollback per mapping (file replace only)
- ❌ No approval workflow (manual PR process)
- ❌ Merge conflicts at scale (multiple teams editing mappings)
- ❌ No runtime updates (requires redeploy to add mapping)
- ❌ No A/B testing (can't test two mapping versions simultaneously)

---

### Issue 3: Hand-Coded Connectors Don't Scale

**Problem:**
```python
class SalesforceConnector:  # 500 lines
    def __init__(self): ...
    def fetch_opportunities(self): ...
    def normalize_field(self): ...
    # ... repeat for every entity

class HubSpotConnector:  # 500 lines
    # Duplicate 90% of Salesforce logic
    # Only API URLs differ

# Repeat 1000 times? NO.
```

**Why This Fails:**
- ❌ Can't hand-code 1000 connectors (50,000 lines of code)
- ❌ Maintenance nightmare (bug fix = update 1000 files)
- ❌ No standardization (each connector implements auth differently)
- ❌ Slow to add new connectors (3-5 days per connector)
- ❌ Testing burden (unit tests × 1000 connectors)

---

### Issue 4: Synchronous Schema Scanning

**Problem:**
```python
for connector in connectors:  # 1000 iterations
    schema = await scan_schema(connector)  # 5s each
    mappings = await propose_mappings(schema)  # 10s each
# Total: 15s × 1000 = 15,000s = 4.2 hours
```

**Why This Fails:**
- ❌ Hours to scan all connectors on system startup
- ❌ Blocks other operations (no concurrency)
- ❌ Single point of failure (one connector timeout = entire scan fails)
- ❌ No priority queuing (critical connectors wait behind slow ones)

---

### Issue 5: No Multi-Tenant Resource Isolation

**Problem:**
- All tenants share same connector pool
- No quotas, no rate limiting
- One tenant can DOS entire system
- No SLA guarantees per tenant

**Why This Fails:**
- ❌ Noisy neighbor problem (Tenant A's 1000 connectors slow Tenant B)
- ❌ No SLA guarantees (can't promise uptime per tenant)
- ❌ Security/compliance risk (tenant data not isolated)
- ❌ No billing fairness (all tenants pay same despite usage)

---

## Enterprise Architecture: Production-Ready Design

### Principle 1: RAG-First, LLM-Last

**Strategy:** 95% of mappings from RAG (cheap, instant), 5% from LLM (expensive, slow)

**Implementation:**
```python
async def propose_mapping(field_name: str, field_type: str):
    # Step 1: RAG lookup (99% of the time this works)
    rag_results = await rag.retrieve_similar_mappings(
        field_name=field_name,
        field_type=field_type,
        similarity_threshold=0.85  # High bar
    )
    
    if rag_results and rag_results[0].similarity > 0.85:
        # RAG has high-confidence match - USE IT
        return MappingProposal(
            source=field_name,
            target=rag_results[0].canonical_field,
            confidence=rag_results[0].similarity,
            method="rag",
            cost=0.0001  # Nearly free
        )
    
    # Step 2: LLM only for truly novel fields (1% of cases)
    llm_proposal = await llm.propose_mapping(field_name, field_type)
    
    # Step 3: Store LLM result in RAG for future reuse
    await rag.store_mapping(llm_proposal)
    
    return llm_proposal
```

**Impact:**
```
Before: 50,000 LLM calls = $500
After:  2,500 LLM calls (5%) = $25  (20x cheaper!)

Before: 27 hours sequential
After:  RAG lookups in parallel = <5 minutes (324x faster!)
```

**Key Insight:** After the first 100 connectors, RAG hit rate approaches 95%+ because most CRM/ERP systems use similar field names (`customer_id`, `email`, `name`, etc.)

---

### Principle 2: Database-Backed Mapping Registry

**Replace YAML with PostgreSQL:**

```sql
CREATE TABLE mapping_registry (
    id UUID PRIMARY KEY,
    source_system VARCHAR NOT NULL,
    source_entity VARCHAR NOT NULL,
    source_field VARCHAR NOT NULL,
    canonical_entity VARCHAR NOT NULL,
    canonical_field VARCHAR NOT NULL,
    
    confidence FLOAT NOT NULL,
    method VARCHAR NOT NULL,  -- 'rag', 'llm', 'manual'
    
    approved_by VARCHAR,      -- User who approved
    approved_at TIMESTAMP,
    
    version INT NOT NULL DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(source_system, source_entity, source_field, version)
);

CREATE INDEX idx_mapping_lookup 
ON mapping_registry(source_system, source_entity, source_field) 
WHERE is_active = TRUE;
```

**Benefits:**
- ✅ Version control (rollback any mapping to previous version)
- ✅ Approval workflow built-in (track who approved what)
- ✅ Runtime updates (no redeploy needed)
- ✅ Fast lookups (<1ms with index)
- ✅ Audit trail (compliance requirement)
- ✅ A/B testing (version 1 vs version 2 comparison)

**Example Query:**
```sql
-- Get current active mapping
SELECT canonical_field, confidence, method
FROM mapping_registry
WHERE source_system = 'stripe' 
  AND source_entity = 'customer'
  AND source_field = 'email'
  AND is_active = TRUE
LIMIT 1;
```

---

### Principle 3: Generic Connector Framework

**Stop hand-coding connectors. Use configuration:**

```python
class GenericAPIConnector:
    """
    Universal connector that works with any REST API
    Configured via JSON, not code
    """
    
    def __init__(self, config: ConnectorConfig):
        self.config = config
        # config.api_base_url
        # config.auth_type (oauth2, api_key, basic)
        # config.entities (which endpoints to sync)
        # config.pagination_style (offset, cursor, page)
    
    async def discover_schema(self):
        """Auto-discover schema via OpenAPI/introspection"""
        if self.config.openapi_spec_url:
            return await self._discover_from_openapi()
        else:
            return await self._discover_from_sample_data()
    
    async def sync_entity(self, entity_name: str):
        """Generic sync logic works for any API"""
        endpoint = self.config.entities[entity_name]
        
        async for page in self._paginate(endpoint):
            for record in page:
                # Auto-map using mapping_registry (database)
                canonical = await self._apply_mappings(
                    source_system=self.config.name,
                    entity=entity_name,
                    record=record
                )
                
                await self._emit_canonical_event(canonical)
```

**Connector Configuration (JSON, not code):**

```json
{
  "name": "stripe",
  "api_base_url": "https://api.stripe.com/v1",
  "auth_type": "bearer_token",
  "rate_limit": "100/second",
  "entities": {
    "customers": {
      "endpoint": "/customers",
      "pagination": "cursor",
      "canonical_entity": "customer"
    },
    "invoices": {
      "endpoint": "/invoices",
      "pagination": "cursor",
      "canonical_entity": "invoice"
    }
  },
  "openapi_spec_url": "https://stripe.com/docs/api/openapi.yaml"
}
```

**Scaling Impact:**
```
Hand-coded: 10 connectors = 5,000 lines of code
Generic:    1000 connectors = 1,000 JSON configs (100 lines each)
            = 90% less code to maintain
```

---

### Principle 4: Distributed, Event-Driven Architecture

**Replace synchronous loops with distributed workers:**

**Before (Synchronous):**
```python
for connector in connectors:
    await scan_schema(connector)  # Sequential, slow
```

**After (Distributed):**
```python
# API publishes to Redis Stream
await redis.xadd("schema_scan_jobs", {
    "connector_id": connector.id,
    "tenant_id": tenant.id,
    "priority": "high"
})

# Worker pool processes in parallel (10 workers)
# 1000 connectors ÷ 10 workers = 100 connectors each
# 100 × 5s = 500s = 8 minutes (vs 83 minutes sequential)
```

**Architecture:**
```
┌─────────────────────────────────────────────┐
│ API Gateway (Rate Limiting, Auth)           │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ Redis Streams (Job Queue)                   │
│ - schema_scan_jobs                          │
│ - canonical_event_stream                    │
│ - drift_detection_jobs                      │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ Worker Pool (Auto-Scaling)                  │
│ - SchemaScanner Workers (10-100)            │
│ - CanonicalPublisher Workers (10-100)       │
│ - DriftDetector Workers (10-100)            │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ PostgreSQL (Multi-Tenant, Partitioned)      │
│ - mapping_registry                          │
│ - canonical_streams (partitioned by tenant) │
│ - drift_events                              │
└─────────────────────────────────────────────┘
```

**Benefits:**
- ✅ Horizontal scaling (add more workers = process more connectors)
- ✅ Fault tolerance (worker crash = job reprocessed)
- ✅ Priority queuing (critical connectors first)
- ✅ Backpressure handling (queue full = API returns 429)

---

### Principle 5: Multi-Tenant Resource Isolation

**Enforce quotas and rate limits per tenant:**

```python
class TenantResourceManager:
    """Enforce quotas per tenant"""
    
    async def check_quota(self, tenant_id: str, resource: str) -> bool:
        quotas = await self._get_tenant_quotas(tenant_id)
        usage = await self._get_current_usage(tenant_id, resource)
        
        if resource == "active_connectors":
            return usage < quotas.max_connectors
        elif resource == "llm_calls_monthly":
            return usage < quotas.max_llm_calls
        elif resource == "canonical_events_hourly":
            return usage < quotas.max_events_per_hour
        
        return True
    
    async def enforce_rate_limit(self, tenant_id: str):
        """Per-tenant rate limiting"""
        key = f"rate_limit:{tenant_id}:api_calls"
        count = await redis.incr(key)
        
        if count == 1:
            await redis.expire(key, 60)  # 1 minute window
        
        limit = await self._get_tenant_rate_limit(tenant_id)
        
        if count > limit:
            raise RateLimitExceeded(f"Tenant {tenant_id} exceeded {limit} calls/min")
```

**PostgreSQL Table Partitioning:**
```sql
-- Partition canonical_streams by tenant_id for isolation
CREATE TABLE canonical_streams (
    id UUID,
    tenant_id VARCHAR NOT NULL,
    entity VARCHAR,
    data JSONB,
    created_at TIMESTAMP
) PARTITION BY HASH (tenant_id);

-- Create 100 partitions for horizontal scaling
CREATE TABLE canonical_streams_p0 PARTITION OF canonical_streams
FOR VALUES WITH (MODULUS 100, REMAINDER 0);

-- ... 99 more partitions
```

**Benefits:**
- ✅ SLA guarantees (each tenant gets reserved capacity)
- ✅ Billing fairness (pay for what you use)
- ✅ Security compliance (data physically isolated)
- ✅ Performance isolation (one tenant can't slow others)

---

### Principle 6: Enterprise Observability

**OpenTelemetry instrumentation:**

```python
from opentelemetry import trace, metrics

tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

# Metrics
connector_sync_counter = meter.create_counter(
    "aam.connector.syncs",
    description="Number of connector syncs"
)

mapping_confidence_histogram = meter.create_histogram(
    "aam.mapping.confidence",
    description="Distribution of mapping confidence scores"
)

# Tracing
@tracer.start_as_current_span("sync_connector")
async def sync_connector(connector_id: str, tenant_id: str):
    span = trace.get_current_span()
    span.set_attribute("connector.id", connector_id)
    span.set_attribute("tenant.id", tenant_id)
    
    with tracer.start_span("fetch_data") as fetch_span:
        data = await fetch_from_api(connector_id)
        fetch_span.set_attribute("records.count", len(data))
    
    with tracer.start_span("apply_mappings") as map_span:
        canonical = await apply_mappings(data)
        map_span.set_attribute("mappings.rag", rag_count)
        map_span.set_attribute("mappings.llm", llm_count)
    
    connector_sync_counter.add(1, {"connector": connector_id})
```

**Dashboard Metrics:**
- Connector sync success rate (per tenant, per connector)
- Mapping confidence distribution
- RAG hit rate (target: >95%)
- LLM call volume (target: <5%)
- P50/P95/P99 latencies
- Cost per tenant

---

## Scalability Comparison Table

| Metric | Initial Plan | Enterprise Architecture |
|--------|--------------|------------------------|
| **Onboarding 1000 Connectors** | 27 hours | <10 minutes |
| **LLM Call Cost** | $500/cycle | $25/cycle (20x cheaper) |
| **Mapping Storage** | 1000 YAML files | PostgreSQL database |
| **Schema Scan Time** | 83 min sequential | 8 min parallel (10x faster) |
| **Code per Connector** | 500 lines Python | 100 lines JSON config |
| **Mapping Versioning** | ❌ None (file replace) | ✅ Full history + rollback |
| **Runtime Updates** | ❌ Requires redeploy | ✅ Instant via database |
| **Multi-Tenant Isolation** | ❌ None | ✅ Full isolation + quotas |
| **Rate Limiting** | ❌ Global only | ✅ Per-tenant granular |
| **Observability** | ❌ Basic logs | ✅ OpenTelemetry traces |
| **Horizontal Scaling** | ❌ Monolith | ✅ Worker pools + auto-scale |
| **Fault Tolerance** | ❌ Single point failure | ✅ Job retry + worker failover |
| **A/B Testing Mappings** | ❌ Not possible | ✅ Version-based testing |

---

## Implementation Phases

### Phase 1: Foundation (Enterprise-Ready Core)
**Goal:** Build database-backed mapping system with RAG-first strategy

**Tasks:**
1. Create `mapping_registry` PostgreSQL table with versioning
2. Migrate existing 8 YAML files to database (preserve history)
3. Build RAG-first mapping lookup service
4. Add mapping approval workflow API endpoints
5. Implement mapping versioning/rollback logic

**Success Criteria:**
- ✅ All mappings stored in database
- ✅ RAG hit rate >85% on existing connectors
- ✅ Sub-100ms mapping lookup latency
- ✅ Approval workflow functional

---

### Phase 2: Generic Connector Framework
**Goal:** Replace hand-coded connectors with config-driven approach

**Tasks:**
1. Build `GenericAPIConnector` base class
2. Add OpenAPI schema introspection
3. Add auto-pagination detection (cursor, offset, page)
4. Convert 3 existing connectors to config-driven (Salesforce, Stripe, HubSpot)
5. Test with 10 different connector configs

**Success Criteria:**
- ✅ 10 connectors running with JSON config only
- ✅ Zero Python code changes to add new connector
- ✅ OpenAPI introspection working for 5+ APIs
- ✅ Config validation prevents misconfigurations

---

### Phase 3: Distributed Workers
**Goal:** Enable parallel processing for scale

**Tasks:**
1. Refactor schema scanner to Redis Streams job queue
2. Build worker pool (10 schema scanner workers)
3. Add auto-scaling logic based on queue depth
4. Partition `canonical_streams` table by tenant_id (100 partitions)
5. Implement backpressure handling (429 when queue full)

**Success Criteria:**
- ✅ 100 connectors scanned in <10 minutes
- ✅ Workers auto-scale from 10 → 50 under load
- ✅ Job retry on worker failure
- ✅ Per-tenant partition isolation working

---

### Phase 4: Multi-Tenant & Observability
**Goal:** Production-grade resource isolation and monitoring

**Tasks:**
1. Implement `TenantResourceManager` with quotas
2. Add per-tenant rate limiting (Redis-based)
3. Add OpenTelemetry instrumentation (traces + metrics)
4. Build enterprise monitoring dashboard with per-tenant views
5. Add cost attribution per tenant

**Success Criteria:**
- ✅ Tenant quotas enforced (connectors, LLM calls, events/hour)
- ✅ Rate limiting prevents DOS
- ✅ OpenTelemetry traces visible in Jaeger/Grafana
- ✅ Per-tenant cost dashboard functional

---

### Phase 5: Scale Test & Validation
**Goal:** Validate 1000+ connector scalability

**Tasks:**
1. Load test with 100 mock connectors (different schemas)
2. Validate RAG hit rate >95% after initial seeding
3. Verify sub-10-minute onboarding for 100 connectors
4. Stress test multi-tenant isolation (10 tenants × 100 connectors each)
5. Measure P99 latency under load

**Success Criteria:**
- ✅ 1000 connectors onboarded in <10 minutes
- ✅ RAG hit rate >95%
- ✅ LLM cost <$50 for 1000 connectors
- ✅ No cross-tenant interference
- ✅ P99 latency <500ms for mapping lookup

---

## Decision Framework

### Critical Question 1: Demo vs Production?

**Option A: Demonstrate Concepts (Initial Plan)**
- ✅ Faster to build (10-20 connectors)
- ✅ Shows auto-mapping capabilities
- ❌ Won't scale beyond demo
- ❌ Complete rewrite needed for production
- **Timeline:** Ready for demo in 1-2 phases
- **Risk:** Technical debt, rewrite costs

**Option B: Build for Production (Enterprise Architecture)**
- ✅ Scales to 1000+ connectors
- ✅ Production-ready from day 1
- ✅ No rewrite needed
- ❌ Takes longer to build all 5 phases
- **Timeline:** Production-ready after all 5 phases
- **Risk:** Over-engineering if only demo needed

---

### Critical Question 2: Real API Integrations?

**Real APIs (via Replit Integrations or OAuth):**
- ✅ Demonstrates live data flow
- ✅ More impressive for evaluators
- ❌ Requires API credentials management
- ❌ Rate limiting concerns
- **Best For:** Stripe, GitHub, Slack (Replit Integrations available)

**Mock Connectors (CSV/JSON data):**
- ✅ Fast to build (no OAuth setup)
- ✅ Predictable test data
- ✅ No rate limiting
- ❌ Less realistic
- **Best For:** Custom/proprietary systems, rare APIs

**Recommendation:** Mix of 3 real APIs (Stripe, GitHub, Slack) + 7-10 mock connectors

---

### Critical Question 3: Evaluation Timeline?

**If demo-focused (next 2-3 phases):**
- Implement Phases 1-2 (Foundation + Generic Connectors)
- Use initial plan for monitoring dashboard
- Acceptable: 10-20 connectors, won't scale beyond demo

**If production-bound (all 5 phases):**
- Implement full enterprise architecture
- Build for 1000+ connectors from start
- Mandatory: All 6 principles implemented

---

## Recommendation

**Given that this is a "KEY part of a production-ready enterprise system that is supposed to scale to 100s or thousands of connections":**

### Recommended Path: **Option B (Enterprise Architecture)**

**Why:**
1. **No Rewrite Needed:** Building correctly from start avoids 6-12 month rewrite later
2. **Cost Efficiency:** RAG-first saves $5,000+/year in LLM costs at scale
3. **Competitive Moat:** Generic connector framework = fast time-to-market for new connectors
4. **Enterprise Sales:** Multi-tenant isolation is table-stakes for enterprise contracts
5. **Technical Credibility:** Evaluators will assess architecture, not just demo

**Phase Priority:**
- **Phase 1** (Foundation) - CRITICAL: Enables all other phases
- **Phase 2** (Generic Connectors) - HIGH: Unlocks connector velocity
- **Phase 3** (Distributed Workers) - HIGH: Required for 100+ connectors
- **Phase 4** (Multi-Tenant) - CRITICAL: Required for production SaaS
- **Phase 5** (Scale Test) - MEDIUM: Validates architecture choices

**Estimated Implementation Scope:**
- Phase 1: Foundation work (database, RAG-first)
- Phase 2: Generic connector framework
- Phase 3: Distributed workers
- Phase 4: Multi-tenant + observability
- Phase 5: Validation testing

**Start Here:** Phase 1 (Foundation) is non-negotiable and blocks all other work.

---

## Next Steps

1. **Decide:** Demo-focused (Option A) vs Production-ready (Option B)?
2. **Approve:** Enterprise architecture design (6 principles)
3. **Begin:** Phase 1 implementation (mapping_registry database migration)
4. **Monitor:** RAG hit rate as connectors are added
5. **Validate:** Scale test after Phase 3 completion

---

## Questions for Stakeholders

1. **Scale Target:** Is 1000+ connectors truly the target, or would 50-100 suffice?
2. **Timeline:** What's the deadline for production deployment?
3. **Real vs Mock:** Should we prioritize real API integrations or is mock data acceptable?
4. **Multi-Tenancy:** Are we selling to multiple customers (requires Phase 4) or single-tenant deployment?
5. **Budget:** What's the monthly LLM budget for mapping proposals?

---

**Document Version:** 1.0  
**Author:** AutonomOS Architecture Team  
**Review Status:** Pending stakeholder approval
