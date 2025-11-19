# AAM Auto-Onboarding Implementation Plan

**Feature**: AOD → AAM Auto-Onboarding with 90% Day-One SLO  
**Date**: November 8, 2025  
**Namespace**: `autonomy` (preserves existing demo functionality)

---

## Overview

Implement auto-onboarding flow that accepts `connection_intent` payloads from AOD (AOS Discover) and automatically onboards data sources in Safe Mode, targeting ≥90% success rate on day one.

---

## Tasks Breakdown

### Phase 1: Database Schema Extensions (2 files modified)
- [ ] **aam_hybrid/shared/models.py** - Add fields to Connection model:
  - `namespace` (String) - Scope connections to "autonomy" vs "demo"
  - `first_sync_rows` (Integer) - Count from tiny first sync
  - `latency_ms` (Float) - Response time for first sync
  - `credential_locator` (String) - Vault/env/consent/SP reference
  - `risk_level` (String) - low/med/high from AOD
  - `evidence` (JSON) - Sanctioning evidence from AOD
  - `owner` (JSON) - Owner metadata from AOD

### Phase 2: Connection Intent Schema (1 new file)
- [ ] **app/schemas/connection_intent.py** - New Pydantic models:
  - `ConnectionIntent` - Accept AOD payloads with all fields from spec
  - `OnboardingResult` - Return onboarding outcome
  - `FunnelMetrics` - Funnel counters response model

### Phase 3: Onboarding Service (1 new file)
- [ ] **aam_hybrid/core/onboarding_service.py** - Core auto-onboarding logic:
  - `validate_allowlist()` - Check source_type against 30+ allowed types
  - `resolve_credentials()` - Handle vault/env/consent/SP credential lookup
  - `discover_schema()` - Metadata-only schema discovery
  - `run_tiny_sync()` - First sync with ≤20 items
  - `onboard_connection()` - Orchestrates full flow (idempotent)

### Phase 4: Funnel Metrics Tracker (1 new file)
- [ ] **aam_hybrid/core/funnel_metrics.py** - Redis-backed counters:
  - Track: eligible, reachable, active, awaiting_credentials, network_blocked, unsupported_type, healing, error
  - Namespace-scoped (autonomy vs demo)
  - SLO calculation: coverage = active / eligible

### Phase 5: New API Endpoints (1 file modified, 1 new)
- [ ] **app/api/v1/aam_onboarding.py** - New router:
  - `POST /connections/onboard` - Accept connection_intent, trigger onboarding
  - `GET /metrics/funnel` - Return funnel counters + SLO
- [ ] **app/main.py** - Register new router

### Phase 6: Enhanced Connection Manager (1 file modified)
- [ ] **aam_hybrid/core/connection_manager.py** - Add methods:
  - `list_connections_by_namespace(namespace: str)` - Filter by autonomy/demo
  - `update_first_sync_stats(connection_id, rows, latency)` - Record tiny sync
  - `promote_healing_to_active(connection_id)` - For make heal

### Phase 7: Connector Adapters - Safe Mode (4 files modified)
- [ ] **aam_hybrid/connectors/salesforce_adapter.py** - Add safe_mode param
- [ ] **aam_hybrid/connectors/supabase_adapter.py** - Add safe_mode param
- [ ] **aam_hybrid/connectors/mongodb_adapter.py** - Add safe_mode param
- [ ] **aam_hybrid/connectors/filesource_adapter.py** - Add safe_mode param
  - Each adapter: read-only scopes, rate caps, circuit breaker, no destructive ops

### Phase 8: Make Targets (1 new file)
- [ ] **Makefile** - Add targets:
  - `autonomy-mode` - Enable Safe Mode, caps, metrics
  - `smoke-90` - Run onboarding on 5 sample intents
  - `heal` - Promote HEALING → ACTIVE

### Phase 9: Scripts & Tooling (2 new files)
- [ ] **scripts/exec_summary.py** - Print funnel summary in plain English
- [ ] **seeds/intents/** - Create 5 sample connection_intent JSON files

### Phase 10: Tests (3 new files)
- [ ] **tests/test_onboarding_flow.py** - Idempotent onboarding, allowlist validation
- [ ] **tests/test_safe_mode.py** - Safe Mode scopes enforced, no destructive ops
- [ ] **tests/test_funnel_metrics.py** - Funnel accuracy, SLO calculation

### Phase 11: Documentation Updates (2 files modified)
- [ ] **replit.md** - Document new auto-onboarding feature
- [ ] **aam_hybrid/README.md** - Update with onboarding API docs

---

## Data Flows

### Onboarding Flow (Happy Path)
```
AOD (AOS Discover)
  └─> POST /connections/onboard (connection_intent payload)
       └─> Validate source_type against allowlist
            └─> Resolve credentials (vault/env/consent/SP)
                 └─> Create/upsert connector (prefer Airbyte)
                      └─> Discover schema (metadata-only)
                           └─> Health check → ACTIVE (Safe Mode)
                                └─> Tiny first sync (≤20 items)
                                     └─> Persist to Connection Registry (namespace=autonomy)
                                          └─> Update funnel metrics (active++)
                                               └─> Return OnboardingResult
```

### Credential Resolution Flow
```
credential_locator
  ├─> "vault:..." → Query Vault API for secret
  ├─> "env:..." → Read from environment variable
  ├─> "consent:..." → OAuth admin consent flow (create AWAITING_CREDENTIALS)
  └─> "sp:..." → Service principal/account lookup
```

### Funnel Metrics Flow
```
connection_intent received
  └─> eligible++ (mappable + sanctioned + credentialed)
       ├─> unsupported_type++ → 409 UNSUPPORTED
       ├─> awaiting_credentials++ → Create record, no sync
       ├─> network_blocked++ → Health check failed
       ├─> error++ → Exception during onboarding
       └─> reachable++ → Health check passed
            └─> active++ → Tiny first sync succeeded
```

---

## New APIs

### POST /connections/onboard
**Request**:
```json
{
  "source_type": "salesforce",
  "resource_ids": ["org_00D..."],
  "scopes_mode": "safe_readonly",
  "credential_locator": "vault:salesforce-prod-token",
  "namespace": "autonomy",
  "risk_level": "low",
  "evidence": {
    "status": "Sanctioned",
    "source": "IdP",
    "ts": "2025-11-08T18:00:00Z"
  },
  "owner": {
    "user": "admin@company.com",
    "confidence": 0.95,
    "why": "oauth_consenter"
  }
}
```
**Response**:
```json
{
  "connection_id": "550e8400-...",
  "status": "ACTIVE",
  "namespace": "autonomy",
  "first_sync_rows": 15,
  "latency_ms": 250,
  "funnel_stage": "active",
  "message": "Onboarded successfully in Safe Mode"
}
```

### GET /metrics/funnel?namespace=autonomy
**Response**:
```json
{
  "namespace": "autonomy",
  "eligible": 100,
  "reachable": 95,
  "active": 92,
  "awaiting_credentials": 3,
  "network_blocked": 2,
  "unsupported_type": 1,
  "healing": 1,
  "error": 1,
  "coverage": 0.92,
  "slo_met": true,
  "target": 0.90
}
```

---

## Allowlist (30+ Source Types)

### Productivity & Collaboration (9)
- gworkspace_drive, m365_sharepoint, slack, zoom, box, dropbox, confluence, jira, github

### Identity & Security (4)
- okta, entra, servicenow, gitlab

### Cloud Infrastructure (6)
- aws_org, azure_sub, gcp_org, s3, s3_compat, datadog

### Data Warehouses (3)
- snowflake, bigquery, redshift

### Business Applications (5)
- salesforce, zendesk, pagerduty, workday, netsuite

### Generic/Flexible (3)
- openapi, jdbc, mongo, postgres, supabase, filesource

**Total**: 32 source types (exceeds 30+ requirement)

---

## Risks & Mitigations

### Risk 1: Database Migration Breaking Production
- **Severity**: High
- **Mitigation**: Use Alembic autogenerate, test locally first, use `npm run db:push --force` if needed

### Risk 2: Credential Vault Not Available
- **Severity**: Medium
- **Mitigation**: Support multiple locators (env, vault, consent); graceful fallback to AWAITING_CREDENTIALS

### Risk 3: Airbyte Not Installed/Available
- **Severity**: Medium
- **Mitigation**: Fall back to native metadata adapters for all connectors

### Risk 4: 90% SLO Too Ambitious
- **Severity**: Low
- **Mitigation**: Safe Mode reduces failure rate; unsupported types excluded from SLO calculation

### Risk 5: Port 5000 Already in Use
- **Severity**: Low
- **Mitigation**: Spec says "reuse the running process" - integrate into existing API

### Risk 6: Breaking Existing Demo Connections
- **Severity**: High
- **Mitigation**: Use namespace="autonomy" for all new work; never touch demo/* connections

### Risk 7: No Tests for 30+ Connectors
- **Severity**: Medium
- **Mitigation**: Use allowlist validation + metadata-only discovery; defer full connector tests

---

## File Changes Summary

### New Files (9)
1. `app/schemas/connection_intent.py` - Pydantic schemas
2. `aam_hybrid/core/onboarding_service.py` - Core logic
3. `aam_hybrid/core/funnel_metrics.py` - Metrics tracker
4. `app/api/v1/aam_onboarding.py` - New API router
5. `scripts/exec_summary.py` - CLI summary
6. `seeds/intents/*.json` - 5 sample payloads
7. `tests/test_onboarding_flow.py` - Onboarding tests
8. `tests/test_safe_mode.py` - Safe Mode tests
9. `tests/test_funnel_metrics.py` - Metrics tests

### Modified Files (8)
1. `aam_hybrid/shared/models.py` - Add namespace, first_sync_rows, latency_ms, etc.
2. `aam_hybrid/core/connection_manager.py` - Add namespace filtering
3. `aam_hybrid/connectors/salesforce_adapter.py` - Safe Mode support
4. `aam_hybrid/connectors/supabase_adapter.py` - Safe Mode support
5. `aam_hybrid/connectors/mongodb_adapter.py` - Safe Mode support
6. `aam_hybrid/connectors/filesource_adapter.py` - Safe Mode support
7. `app/main.py` - Register new router
8. `Makefile` - Add autonomy-mode, smoke-90, heal targets

### Documentation Updates (2)
1. `replit.md` - Feature announcement
2. `aam_hybrid/README.md` - API docs

**Total Changes**: 9 new files + 8 modified files + 2 doc updates = **19 file operations**

---

## Success Criteria

1. ✅ **90% SLO**: Given eligible intents, ≥90% reach ACTIVE with tiny first sync
2. ✅ **Funnel Accuracy**: GET /metrics/funnel matches exec_summary.py output
3. ✅ **Demo Preservation**: All demo namespace connections untouched
4. ✅ **Safe Mode**: No destructive ops; read-only scopes enforced
5. ✅ **Idempotency**: Re-running onboard on same intent updates, doesn't duplicate
6. ✅ **Tests Pass**: All unit tests green (onboarding, safe mode, funnel)

---

## Timeline Estimate

- **Phase 1-2** (Schema + Models): 30 min
- **Phase 3-4** (Onboarding + Metrics): 45 min
- **Phase 5-6** (APIs + Manager): 30 min
- **Phase 7** (Safe Mode Adapters): 30 min
- **Phase 8-9** (Make + Scripts): 20 min
- **Phase 10-11** (Tests + Docs): 25 min

**Total**: ~3 hours implementation time

---

## Approval Required

See DEBT.md for technical debt analysis. If no Blocker/High debt, proceed with:

**Token: CONTINUE 90 RUN**
