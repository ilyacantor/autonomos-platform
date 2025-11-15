# Tenant State Isolation: Production Rollout Checklist

**Feature:** TENANT_SCOPED_STATE Feature Flag
**Status:** Ready for Staged Rollout
**Owner:** Platform Engineering Team
**Last Updated:** 2025-11-15

---

## Executive Summary

This document outlines the staged rollout strategy, monitoring plan, and rollback procedures for enabling the `TENANT_SCOPED_STATE` feature flag, which migrates DCL Engine from shared global state to tenant-scoped Redis-backed storage.

**Key Benefits:**
- ✅ Eliminates tenant data leakage risks
- ✅ Enables true multi-tenancy for SaaS deployment
- ✅ Zero-downtime migration with gradual rollout
- ✅ Backward-compatible fallback to globals when Redis unavailable

**Migration Scope:**
- 6 state variables migrated (GRAPH_STATE, SOURCES_ADDED, ENTITY_SOURCES, SOURCE_SCHEMAS, SELECTED_AGENTS, EVENT_LOG)
- 195-line state_access.py wrapper module (15 helper functions)
- 58 refactored call sites, 28+ manual guards removed
- Dual-path architecture (Redis + global fallback)

---

## 1. Pre-Rollout Validation

**Critical Checklist - Complete ALL items before Stage 1:**

- [ ] **AST Audit Script:** Run `python -m scripts.audit_state_access` → Exit 0 (zero violations)
  - Confirms no direct tenant_state_manager or global variable usage outside wrappers
  - CI-ready enforcement of wrapper-only pattern

- [ ] **Legacy Regression Tests:** Run `pytest tests/test_tenant_state_legacy.py -v` → 100% pass
  - Validates dual-path behavior (Redis vs global fallback)
  - Zero AttributeError crashes in both modes
  - Mutations persist to correct storage backend

- [ ] **Redis Health Check:** Verify Redis connection stable
  - Connection latency < 5ms P95
  - Zero connection errors in past 24 hours
  - Upstash or equivalent Redis provider configured

- [ ] **Feature Flag Default:** Confirm `TENANT_SCOPED_STATE=False` in Redis
  - Gradual rollout requires opt-in per tenant
  - FeatureFlagConfig.is_enabled(FeatureFlag.TENANT_SCOPED_STATE) returns False by default

- [ ] **Monitoring Dashboards Configured:**
  - Redis operations dashboard (throughput, latency, errors)
  - Tenant state health dashboard (per-tenant metrics)
  - Feature flag adoption rate tracker
  - AttributeError alert configured (threshold: 0)

- [ ] **Rollback Procedure Tested:**
  - Staging environment rollback drill completed
  - Pub/sub broadcast verified to propagate flag changes < 30 seconds
  - Global fallback mode confirmed functional

- [ ] **Communication Plan:**
  - Stakeholders notified of rollout timeline
  - On-call rotation assigned for rollout window
  - Incident response runbook distributed

---

### 1.5 CI/CD Pipeline Integration

**AST Audit Integration:**

- [ ] Add audit script to CI pipeline:
  ```yaml
  # .github/workflows/ci.yml or similar
  - name: Validate State Access Pattern
    run: python -m scripts.audit_state_access --strict
  ```
- [ ] Configure as required check (blocks merge if violations found)
- [ ] Document exception process for rare legitimate cases

**Regression Test Integration:**

- [ ] Legacy mode tests run in CI on every PR
- [ ] Redis integration tests run in CI with fake Redis
- [ ] Minimum coverage threshold: 95% for state_access.py

**Pre-Deployment Gates:**

- [ ] AST audit passes (exit 0)
- [ ] All regression tests pass (21+ tests)
- [ ] Code coverage meets threshold

---

## 2. Staged Rollout Plan

### Stage 1: Pilot Tenant (0.1% of traffic)

**Duration:** 24 hours  
**Target Tenants:** 1 internal development tenant (non-production data)  
**Enablement:** Manual feature flag override in Redis for specific tenant_id

**Monitoring Focus:**
- Real-time error tracking (Sentry/Datadog)
- Redis latency P95/P99 for pilot tenant
- WebSocket state broadcast delivery rate

**Success Gate (All Must Pass):**
- ✅ Zero AttributeError exceptions
- ✅ Zero data corruption incidents (verified via manual graph inspection)
- ✅ Redis latency < 5ms P95
- ✅ API response time increase < 10% vs baseline

**Abort Criteria:**
- Any AttributeError detected → Immediate rollback
- Data corruption (graph mismatch) → Immediate rollback
- Redis latency > 10ms P95 sustained → Pause rollout

---

### Stage 2: Early Adopters (5% of traffic)

**Duration:** 48 hours  
**Target Tenants:** 5 selected production tenants (low-risk, high-engagement)  
**Enablement:** Per-tenant feature flag override

**Monitoring Focus:**
- Error rate delta vs control group (non-enabled tenants)
- API latency P50/P95/P99 comparison
- Tenant state isolation verification (no cross-tenant leaks)

**Success Gate (All Must Pass):**
- ✅ Error rate increase < 0.1% vs control group
- ✅ API latency increase < 10% vs control group
- ✅ Zero AttributeError in 48 hours
- ✅ User feedback: No reports of data issues or performance degradation

**Abort Criteria:**
- Error rate increase > 0.5% → Immediate rollback
- API latency increase > 20% → Pause rollout
- AttributeError detected → Immediate rollback

---

### Stage 3: Gradual Rollout (25% → 50% → 100%)

**Timeline:** 2 weeks total (3-day intervals between increments)

| Date | Target % | Estimated Tenants | Success Gate Check |
|------|----------|-------------------|-------------------|
| Day 1 | 25% | ~25 tenants | Error budget maintained |
| Day 4 | 50% | ~50 tenants | Error budget maintained |
| Day 7 | 75% | ~75 tenants | Error budget maintained |
| Day 10 | 100% | All tenants | Final validation |

**Enablement:** Gradual percentage-based rollout via FeatureFlagConfig

**Monitoring Focus:**
- Daily error budget tracking (target: < 0.01% error rate increase)
- Cumulative AttributeError count (target: 0)
- Redis operations throughput and error rate
- Cross-tenant isolation audit (random sampling)

**Success Gate at Each Increment:**
- ✅ Error budget maintained (< 0.01% increase)
- ✅ Zero AttributeError in rollout cohort
- ✅ Redis latency stable (< 5ms P95)
- ✅ No tenant state mismatch incidents

**Abort Criteria:**
- Error rate spike > 0.1% → Pause and investigate
- Sustained Redis latency > 10ms → Pause rollout
- Any AttributeError → Immediate rollback

---

## 3. Monitoring & Observability

### Key Metrics (SLOs)

**Critical Metrics (P0 - Monitor in Real-Time):**

| Metric | Target | Alert Threshold | Dashboard |
|--------|--------|----------------|-----------|
| AttributeError count | 0 | > 0 in 5min window | Errors Dashboard |
| Redis error rate | < 0.01% | > 0.05% | Redis Operations |
| API latency P95 | < baseline + 10% | > baseline + 20% | API Performance |
| Tenant state mismatches | 0 | > 0 | Tenant Health |

**Secondary Metrics (P1 - Monitor Hourly):**

| Metric | Target | Alert Threshold | Dashboard |
|--------|--------|----------------|-----------|
| Redis latency P99 | < 10ms | > 15ms | Redis Operations |
| WebSocket broadcast failures | < 0.1% | > 1% | Real-Time Events |
| Feature flag adoption rate | Per rollout plan | N/A | Rollout Progress |
| State access wrapper usage | 100% | < 95% | Code Quality |

### Alert Configuration

**CRITICAL Alerts (PagerDuty - Immediate Response):**

```yaml
- name: AttributeError Spike
  condition: AttributeError count > 0 in 5min window
  severity: CRITICAL
  action: Page on-call engineer, initiate rollback

- name: Redis Connection Failure
  condition: Redis connection errors > 5 in 1min
  severity: CRITICAL
  action: Page on-call engineer, verify Redis health

- name: Data Corruption Detected
  condition: Tenant state mismatch incident reported
  severity: CRITICAL
  action: Page rollout lead, freeze rollout
```

**WARNING Alerts (Slack - Monitor & Investigate):**

```yaml
- name: Redis Latency Degradation
  condition: Redis latency P95 > 10ms for 5min
  severity: WARNING
  action: Notify #platform-eng channel, investigate

- name: API Latency Increase
  condition: API latency P95 > baseline + 20% for 10min
  severity: WARNING
  action: Notify rollout lead, consider pause

- name: Error Rate Increase
  condition: Error rate > baseline + 0.1% for 15min
  severity: WARNING
  action: Notify #platform-eng channel, investigate
```

### Dashboards

**Dashboard 1: Tenant State Health**
- Per-tenant graph state size (nodes/edges count)
- Per-tenant Redis operation latency
- Tenant isolation verification status
- State access wrapper call rates

**Dashboard 2: Redis Operations**
- Read/Write throughput (ops/sec)
- Latency distribution (P50/P95/P99)
- Error rate over time
- Connection pool utilization

**Dashboard 3: Feature Flag Adoption**
- Percentage of tenants with TENANT_SCOPED_STATE enabled
- Rollout progress timeline
- Per-stage success gate status
- Rollback event history

**Dashboard 4: Error Tracking**
- AttributeError count by source module
- State access violations (AST audit failures)
- API error rate by endpoint
- WebSocket broadcast failure rate

---

## 4. Rollback Triggers & Procedures

### Immediate Rollback Triggers

**Automatic Rollback (No Approval Required):**
- ✅ Any AttributeError detected in production logs
- ✅ Redis connection failure > 5 minutes
- ✅ API error rate > 1% sustained for 5 minutes
- ✅ Data corruption incident reported by user or monitoring

**Manual Rollback (Rollout Lead Approval Required):**
- ⚠️ Redis latency > 15ms P95 sustained for 10 minutes
- ⚠️ API latency increase > 30% sustained for 10 minutes
- ⚠️ User complaints about data inconsistency (>2 reports)
- ⚠️ Error rate increase > 0.5% sustained for 15 minutes

### Rollback Procedure (Execution Time: < 5 minutes)

**Step 1: Disable Feature Flag**
```bash
# Connect to Redis and disable flag globally
redis-cli SET dcl:feature_flags:TENANT_SCOPED_STATE false

# Verify flag disabled
redis-cli GET dcl:feature_flags:TENANT_SCOPED_STATE
# Expected output: "false"
```

**Step 2: Broadcast Flag Change via Pub/Sub**
```bash
# Trigger pub/sub broadcast to all workers
redis-cli PUBLISH dcl:feature_flags:updates "TENANT_SCOPED_STATE=false"

# All active workers should receive update within 30 seconds
```

**Step 3: Verify All Workers Using Global Fallback**
```bash
# Check application logs for confirmation messages
grep "TENANT_SCOPED_STATE: DISABLED" /var/log/app/*.log

# Expected: All worker instances log flag change within 1 minute
```

**Step 4: Monitor for Error Rate Drop**
```bash
# Monitor error rate for 15 minutes
# Expected: Error rate returns to baseline within 5 minutes
# API latency returns to baseline within 10 minutes
```

**Step 5: Post-Mortem & Root Cause Analysis**
- Capture logs from incident window (T-10min to T+10min)
- Analyze AttributeError stack traces (if any)
- Review Redis latency metrics during incident
- Identify code path causing failure
- Document findings in incident report
- Create fix plan and re-test before re-attempting rollout

### Rollback Communication Template

```
🚨 TENANT_SCOPED_STATE Rollback Initiated

Trigger: [AttributeError detected / Redis latency spike / etc.]
Time: [Timestamp]
Impact: [X% of tenants affected]
Status: Rollback in progress (Step X/5)

Actions Taken:
- ✅ Feature flag disabled globally
- ✅ Workers reverted to global fallback
- 🔄 Monitoring error rate recovery

ETA to Resolution: 5 minutes
On-Call: [Engineer Name]
Follow-Up: Post-mortem scheduled for [Time]
```

---

### 4.2 Redis Cluster Failover During Rollout

**Scenario:** Redis primary fails during staged rollout

**Detection:**
- Redis connection errors spike in monitoring dashboards
- API latency increases dramatically (> 2x baseline)
- Tenant state read operations failing
- Redis health checks reporting primary unreachable

**Response Procedure:**

**1. Immediate Action - Force Legacy Fallback**
```bash
# Disable TENANT_SCOPED_STATE flag immediately
redis-cli SET dcl:feature_flags:TENANT_SCOPED_STATE false

# Broadcast to all workers
redis-cli PUBLISH dcl:feature_flags:updates "TENANT_SCOPED_STATE=false"
```

**2. Verify Redis Cluster Health**
```bash
# Check Redis cluster status
redis-cli CLUSTER INFO

# Check primary/replica status
redis-cli ROLE

# Expected: Should show failover in progress or completed
```

**3. Wait for Redis Auto-Failover**
- Redis cluster auto-failover typically completes in < 30 seconds
- Monitor logs for "Failover complete" message
- Verify new primary elected and accepting connections

**4. Validate Redis Cluster Recovered**
```bash
# Test read/write operations
redis-cli SET test_key "test_value"
redis-cli GET test_key

# Check latency
redis-cli --latency

# Expected: Latency < 5ms, read/write working
```

**5. Resume Rollout Gradually**
```bash
# Re-enable flag for pilot tenant only (staged re-enable)
# DO NOT re-enable globally immediately

# Wait 15 minutes and monitor
# If stable, proceed with gradual re-enablement
```

**6. Monitor for Stability**
- Watch Redis latency for 15 minutes
- Check error rate returns to baseline
- Verify no AttributeError spike
- Confirm tenant state reads/writes working

**Prevention Measures:**

- [ ] **Pre-Stage Health Checks:** Validate Redis cluster health before each rollout stage
  ```bash
  # Run before each stage advancement
  redis-cli CLUSTER INFO | grep cluster_state
  # Expected: cluster_state:ok
  ```

- [ ] **Redis Replication Configured:** Ensure Redis has primary + at least 2 replicas
  ```bash
  redis-cli INFO replication
  # Expected: role:master, connected_slaves:2
  ```

- [ ] **Failover Testing in Staging:** Test Redis failover behavior before production rollout
  - Simulate primary failure in staging environment
  - Verify automatic failover < 30 seconds
  - Confirm application continues working with new primary

- [ ] **Alerting Configured:** Set up alerts for Redis failover events
  ```yaml
  - name: Redis Cluster Failover
    condition: Redis primary changed in last 5min
    severity: WARNING
    action: Notify rollout team, pause rollout
  ```

**Success Criteria for Resumption:**
- ✅ Redis cluster stable for 15+ minutes
- ✅ New primary accepting connections
- ✅ Latency < 5ms P95
- ✅ Zero connection errors
- ✅ Pilot tenant re-enabled and stable

---

## 5. Success Criteria

### Stage-Gate Success Criteria

**Stage 1 Success (Pilot Tenant):**
- ✅ Zero AttributeError in 24 hours
- ✅ Zero data corruption incidents
- ✅ Redis latency < 5ms P95
- ✅ Manual graph inspection confirms data integrity

**Stage 2 Success (Early Adopters):**
- ✅ Error rate increase < 0.1% vs control group
- ✅ API latency increase < 10% vs control group
- ✅ User feedback: No negative reports
- ✅ Tenant isolation verified (cross-tenant audit passed)

**Stage 3 Success (Full Rollout):**
- ✅ 100% tenant adoption achieved
- ✅ Zero AttributeError in 7 consecutive days
- ✅ Error rate stable (< 0.01% increase vs pre-rollout)
- ✅ Redis latency stable (< 5ms P95)
- ✅ User feedback: No data issues or complaints

### Final Validation (Post-Rollout)

**Technical Validation:**
- [ ] AST audit script passes (zero violations)
- [ ] Legacy regression tests pass (100% coverage)
- [ ] All tenants isolated in Redis (verified via manual inspection)
- [ ] Global fallback code still functional (tested in staging)
- [ ] Monitoring dashboards show healthy metrics (7-day trend)

**Business Validation:**
- [ ] Zero customer escalations related to data issues
- [ ] No performance degradation complaints
- [ ] SaaS multi-tenancy compliance achieved
- [ ] Platform ready for new tenant onboarding

**Documentation Validation:**
- [ ] Rollout playbook updated with lessons learned
- [ ] Architecture docs reflect current state (Redis-backed storage)
- [ ] Developer guide updated (use state_access wrappers)
- [ ] Monitoring runbook published (alert response procedures)

---

## 6. Post-Rollout Actions

### Immediate (Within 7 Days of 100% Rollout)

- [ ] **Monitoring Review:** Analyze 7-day metrics, confirm SLOs met
- [ ] **Documentation Update:** Publish updated architecture docs
- [ ] **Developer Communication:** Announce wrapper-only pattern enforcement
- [ ] **AST Audit Integration:** Add to CI/CD pipeline (block merges on violations)

### Short-Term (Within 30 Days)

- [ ] **Performance Optimization:** Analyze Redis latency patterns, optimize if needed
- [ ] **Legacy Code Deprecation Plan:** Mark global fallback code for future removal
- [ ] **Feature Flag Cleanup:** Plan to remove TENANT_SCOPED_STATE flag (make permanent)
- [ ] **Training:** Conduct team training on tenant-scoped state architecture

### Long-Term (Within 90 Days)

- [ ] **Remove Global Fallback Code:** Clean up legacy dual-path logic (Phase 2 task)
- [ ] **Monitoring Baseline Update:** Establish new baseline metrics with Redis-backed state
- [ ] **SaaS Expansion:** Enable new tenant onboarding with guaranteed isolation
- [ ] **Compliance Audit:** Verify multi-tenancy isolation meets regulatory requirements

---

## 7. Communication & Ownership

### Roles & Responsibilities

| Role | Owner | Responsibilities |
|------|-------|-----------------|
| **Rollout Lead** | [TBD: Platform Engineering Lead] | - Execute rollout plan according to timeline<br>- Monitor metrics and success gates<br>- Approve stage transitions<br>- Coordinate rollback if needed |
| **On-Call Engineer** | [TBD: Rotation Schedule] | - Respond to CRITICAL alerts (< 5min SLA)<br>- Execute rollback procedure<br>- Capture incident logs and metrics<br>- Participate in post-mortem |
| **Product Owner** | [TBD: Product Management] | - Approve rollout plan and timeline<br>- Review success gate results<br>- Communicate status to stakeholders<br>- Approve final 100% rollout |
| **QA Lead** | [TBD: Quality Engineering] | - Validate pre-rollout tests (AST audit, regression)<br>- Conduct tenant isolation audits<br>- Verify data integrity at each stage<br>- Sign-off on final validation |
| **DevOps Lead** | [TBD: Infrastructure Team] | - Monitor Redis health and performance<br>- Manage feature flag configuration<br>- Ensure pub/sub broadcast functioning<br>- Support rollback execution |

### Communication Channels

**Real-Time Coordination:**
- Slack channel: `#tenant-state-rollout`
- PagerDuty escalation policy: `platform-on-call`
- War room (if incident): Zoom/Meet link pinned in Slack

**Status Updates:**
- Daily standup during rollout window (15min)
- Stage gate review meetings (30min before each increment)
- Weekly stakeholder summary email

**Documentation:**
- Rollout progress tracker: [Link to project management tool]
- Incident reports: [Link to incident management system]
- Metrics dashboards: [Link to monitoring platform]

---

## 8. Appendix

### Glossary

- **AST Audit Script:** Static analysis tool that enforces wrapper-only pattern
- **Feature Flag:** Runtime configuration toggle (TENANT_SCOPED_STATE)
- **Global Fallback:** Legacy mode using shared global variables
- **Legacy Mode:** State access with TenantStateManager unavailable (Redis down)
- **Redis Mode:** Tenant-scoped storage via TenantStateManager (primary mode)
- **State Access Wrapper:** Helper functions in state_access.py module
- **Tenant Isolation:** Guarantee that one tenant cannot access another's data

### Reference Links

- **Phase 1b Implementation:** [Link to Phase 1b completion report]
- **State Access Module:** `app/dcl_engine/state_access.py`
- **TenantStateManager:** `app/dcl_engine/tenant_state.py`
- **AST Audit Script:** `scripts/audit_state_access.py`
- **Legacy Regression Tests:** `tests/test_tenant_state_legacy.py`
- **Feature Flags Module:** `app/config/feature_flags.py`

### Rollout Timeline (Example)

```
Week 1:
  Mon: Pre-rollout validation complete
  Tue: Stage 1 launch (0.1% - pilot tenant)
  Wed: Stage 1 metrics review
  Thu: Stage 2 launch (5% - early adopters)
  Fri: Stage 2 metrics review

Week 2:
  Mon: Stage 3a launch (25%)
  Thu: Stage 3b launch (50%)

Week 3:
  Mon: Stage 3c launch (75%)
  Thu: Stage 3d launch (100%)
  Fri: Final validation & celebration 🎉
```

---

**Document Version:** 1.0  
**Last Reviewed:** 2025-11-15  
**Next Review:** After 100% rollout completion  
**Approvals Required:** Platform Engineering Lead, Product Owner, DevOps Lead
