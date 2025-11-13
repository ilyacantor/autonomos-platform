# Critical TODOs - Production Blockers

**Last Updated:** November 13, 2025
**Status:** Tracked as part of Phase 1 Technical Debt Cleanup

This document tracks incomplete features and TODO items that need attention before production deployment.

---

## 🚨 CRITICAL Priority

### 1. Incomplete Credential Management System

**File:** `aam_hybrid/core/onboarding_service.py:113-152`

**Issue:** Three credential resolution methods are not implemented:

```python
# Line 136 - Not implemented
elif cred_ref.startswith("vault:"):
    raise NotImplementedError("Vault credential resolution not implemented")

# Line 141 - Not implemented
elif cred_ref.startswith("consent:"):
    raise NotImplementedError("OAuth consent flow not implemented")

# Line 146 - Not implemented
elif cred_ref.startswith("sp:"):
    raise NotImplementedError("Service principal lookup not implemented")
```

**Impact:** Auto-onboarding feature severely limited. Cannot use:
- HashiCorp Vault for credential storage
- OAuth admin consent flows
- Service principal lookups

**Recommendation:**
1. Implement vault integration using HashiCorp Vault SDK
2. Add OAuth consent flow for admin-approved connections
3. Implement service principal credential lookup

**Estimated Effort:** 1-2 weeks

**Priority:** CRITICAL for production auto-onboarding

---

## 🔴 HIGH Priority

### 2. Persona Dashboard Using Mock Data

**File:** `app/nlp_simple.py:394`

```python
# TODO: Try fetching real data from live endpoints
# Currently using mock data
```

**Context:** Demo mode fallback without production implementation

**Impact:** Persona dashboard shows mock data instead of real data from database

**Recommendation:**
1. Implement data fetching from actual database tables
2. Add proper error handling for missing data
3. Maintain mock data as fallback for demo mode

**Estimated Effort:** 2-3 days

**Priority:** HIGH - affects user experience

---

### 3. Discovery Job Queue Not Implemented

**File:** `app/api/v1/aam_monitoring.py:1422`

```python
# TODO: Implement actual discovery job queue
```

**Impact:** Discovery job management not functional. Cannot:
- Queue discovery jobs
- Track job progress
- Handle concurrent discovery operations

**Recommendation:**
1. Implement job queue using RQ (already used elsewhere in codebase)
2. Add job status tracking
3. Create endpoints for job management

**Estimated Effort:** 3-5 days

**Priority:** HIGH - needed for AAM discovery feature

---

### 4. Discovery Job Tracking Not Implemented

**File:** `app/api/v1/aam_monitoring.py:1451`

```python
# TODO: Implement actual job tracking
```

**Impact:** Cannot track discovery job status or retrieve results

**Recommendation:**
1. Use existing task management system from `app/models.py`
2. Store job results in database
3. Add progress updates via WebSocket

**Estimated Effort:** 2-3 days

**Priority:** HIGH - complements discovery job queue

---

## 🟡 MEDIUM Priority

### 5. Background Ingestion Consideration

**File:** `app/dcl_engine/source_loader.py:741`

```python
# TODO: If background ingestion is added, consider per-source keys
```

**Impact:** Scalability limitation for large data sources

**Context:** Current implementation ingests data synchronously. For large datasets, background ingestion would improve UX.

**Recommendation:**
1. Evaluate need based on data source sizes
2. If needed, implement async ingestion with progress tracking
3. Use Redis for per-source locking

**Estimated Effort:** 1 week

**Priority:** MEDIUM - only needed if processing large datasets

---

## ✅ Completed (Phase 1)

### ~~6. Bare Exception Handlers~~ - FIXED ✅

**Status:** Fixed in Phase 1 cleanup (20+ locations)

All bare `except:` and `except Exception: pass` statements have been replaced with:
- Specific exception types
- Proper logging
- Error context

**Files Fixed:**
- `app/dcl_engine/app.py` (8 locations)
- `app/dcl_engine/llm_service.py` (2 locations)
- `app/main.py` (2 locations)
- `app/gateway/middleware/idempotency.py` (3 locations)

---

### ~~7. Dead Code Removal~~ - FIXED ✅

**Status:** Removed in Phase 1 cleanup

Deleted `frontend/src/components/archive/` directory:
- 11 unused files
- 150KB of dead code
- No imports found

---

## 📋 Action Items

### Immediate (Week 1)
- [x] Fix bare exception handlers
- [x] Remove dead code
- [x] Document critical TODOs (this document)

### Short Term (Weeks 2-4)
- [ ] Implement persona dashboard real data fetching (#2)
- [ ] Implement discovery job queue (#3)
- [ ] Implement discovery job tracking (#4)

### Medium Term (Months 1-2)
- [ ] Complete credential management system (#1)
- [ ] Evaluate background ingestion need (#5)

---

## 🔍 Tracking

Issues should be created in your issue tracker for:
1. Incomplete Credential Management (CRITICAL)
2. Persona Dashboard Real Data (HIGH)
3. Discovery Job Queue (HIGH)
4. Discovery Job Tracking (HIGH)
5. Background Ingestion (MEDIUM)

---

## 📊 Metrics

| Category | Count | Status |
|----------|-------|--------|
| Critical TODOs | 1 | Open |
| High Priority TODOs | 3 | Open |
| Medium Priority TODOs | 1 | Open |
| Completed (Phase 1) | 2 | Done |
| **Total** | **7** | **5 Open, 2 Done** |

---

## 🎯 Success Criteria

**Phase 1 Complete:** ✅
- All bare exceptions fixed
- Dead code removed
- TODOs documented

**Phase 2 Target:**
- All HIGH priority TODOs completed
- Persona dashboard uses real data
- Discovery jobs functional

**Phase 3 Target:**
- CRITICAL credential system completed
- Background ingestion evaluated and implemented if needed

---

**Document Owner:** Engineering Team
**Review Frequency:** Weekly
**Next Review:** November 20, 2025
