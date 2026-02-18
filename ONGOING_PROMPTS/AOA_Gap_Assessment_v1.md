# AOA Gap Assessment v1

**Date:** February 18, 2026
**Baseline Document:** AOA Canonical Blueprint v2 (February 2026)
**Codebase:** `autonomos-platform` (commit on `dev` branch)
**Assessor:** Automated deep code review

---

## Executive Summary

The AOA codebase has **substantial foundational work** across the original 10 functional domains (Sections 7.1-7.10 of the Blueprint). The core orchestration runtime, policy engine, coordination layer, A2A protocol, MCP client, observability tracing, budget enforcement, and HITL approval workflows all have **real implementations** — not stubs. The frontend React SPA provides a production-grade dashboard with real-time monitoring, agent management, and HITL approval UI.

However, the **four new domains added in Blueprint v2** (Sections 7.11-7.14) — MCP Governance, AI-SBOM, Regulatory Compliance Evidence, and enhanced NHI Governance — are **entirely unimplemented**. These represent the highest-priority gaps because they address the August 2, 2026 EU AI Act deadline (6 months away) and the OWASP Agentic Top 10 security framework.

Additionally, while many original domains have solid architecture, several have **depth gaps** — the structure is correct but critical operational behaviors (persistence, external integrations, real LLM execution) remain in-memory or placeholder.

### Scoring Summary

| Domain | Blueprint Section | Implementation Status | Maturity | Priority |
|--------|------------------|----------------------|----------|----------|
| Agent Registry | 7.1 | Implemented | 70% | Medium |
| Identity & Trust | 7.2 | Partial | 45% | HIGH |
| Capability Contracts | 7.3 | Partial | 40% | HIGH |
| Policy & Governance | 7.4 | Implemented | 65% | Medium |
| HITL & Approval | 7.5 | Implemented | 70% | Medium |
| Coordination | 7.6 | Implemented | 60% | Medium |
| Runtime | 7.7 | Implemented | 65% | Medium |
| Observability | 7.8 | Implemented | 55% | Medium |
| Lifecycle | 7.9 | Partial | 45% | HIGH |
| Economics | 7.10 | Implemented | 60% | Medium |
| MCP Governance | 7.11 (NEW) | **NOT IMPLEMENTED** | 0% | **CRITICAL** |
| A2A Protocol Governance | 7.12 (NEW) | Partial (transport only) | 30% | HIGH |
| AI-SBOM | 7.13 (NEW) | **NOT IMPLEMENTED** | 0% | **CRITICAL** |
| Regulatory Compliance Evidence | 7.14 (NEW) | **NOT IMPLEMENTED** | 0% | **CRITICAL** |

---

## Detailed Domain-by-Domain Gap Analysis

---

### 7.1 Agent Registry

**Blueprint Requirement:** Agent registration, metadata, trust tier, health monitoring; version management; zombie detection.

**What Exists:**
- `app/agentic/registry/` — Full `AgentInventory` class with CRUD, search, filtering
- `app/agentic/registry/models.py` — `TrustTier` enum (NATIVE/VERIFIED/CUSTOMER/THIRD_PARTY/SANDBOX), `AgentDomain`, `AgentStatus` (ACTIVE/INACTIVE/DEPRECATED/PENDING/SUSPENDED/ZOMBIE), `AgentMetadata` with `declared_capabilities` and `observed_capabilities`
- `app/agentic/registry/inventory.py` — Registration, deregistration, search by capabilities, health tracking
- `app/models/agent.py` — SQLAlchemy `Agent` model with LangGraph definition, MCP server config, guardrails
- DB migration `a8c7d2e9f1b3` — Agent orchestration tables

**Gaps:**
| Gap | Severity | Blueprint Reference |
|-----|----------|-------------------|
| Registry is **in-memory only** — no persistence to database for registry metadata (separate from the Agent ORM model) | HIGH | Phase 0 |
| No NHI permission expiry enforcement | HIGH | Phase 1; Section 4 NHI table |
| No secretless auth integration (OAuth/OIDC/SPIFFE) | HIGH | Phase 1; Aembit pattern |
| Zombie detection exists as a status enum but **no automated detection logic** (quorum rule across AOD/AAM/DCL signals) | HIGH | Phase 1; Open Item #4 |
| Version management exists in metadata but **no version lifecycle enforcement** (rollback, canary, blue-green) | MEDIUM | Phase 1 |
| No AI-SBOM drift alerting on registry changes | MEDIUM | Phase 2; Section 7.13 |

**Maturity: 70%** — Solid architecture, missing operational depth.

---

### 7.2 Identity & Trust

**Blueprint Requirement:** NHI-grade identity governance; 82:1 machine-to-human ratio handling; agent identity issuance; trust tier enforcement; over-permissioned agent detection.

**What Exists:**
- `app/agentic/trust/` — `TrustScorer`, `TrustPolicy`, injection detection (`InjectionDetector` with pattern matching), middleware with content filtering
- `app/agentic/registry/models.py` — `TrustTier` enum with 5 tiers
- Trust scoring based on behavioral signals

**Gaps:**
| Gap | Severity | Blueprint Reference |
|-----|----------|-------------------|
| **No NHI identity issuance system** — AOA should issue agent identities, not just tag trust tiers | CRITICAL | Section 4; "AOA is the IAM layer for agents" |
| **No NHI lifecycle management** — 38% of NHI accounts are dormant per market data; no automated deprecation | CRITICAL | Section 4; NHI table |
| No over-permissioned agent detection | HIGH | Section 4; OWASP ASI02 |
| No integration with enterprise IdP (open item #5 from blueprint) | HIGH | Open Item #5 |
| Trust tier enforcement exists for local agents but **no cross-org trust negotiation** for external A2A agents | HIGH | Section 7.12 |
| No 82:1 scale governance patterns (bulk identity management) | MEDIUM | Section 4 |

**Maturity: 45%** — Trust scoring exists but NHI governance layer is absent.

---

### 7.3 Capability Contracts

**Blueprint Requirement:** Per-agent capability declaration; MCP allowlist as part of contract; contract versioning; drift detection against declared capabilities.

**What Exists:**
- `app/agentic/registry/models.py` — `declared_capabilities` and `observed_capabilities` fields in `AgentMetadata`
- `app/agentic/certification/` — Certification models and workflow
- `app/agentic/a2a/agent_card.py` — `AgentCard` with capabilities list for A2A discovery
- `app/models/agent.py` — `mcp_servers` field (JSON) storing MCP config per agent

**Gaps:**
| Gap | Severity | Blueprint Reference |
|-----|----------|-------------------|
| **No formal capability contract schema** — capabilities are string lists, not structured contracts with scope, cost estimates, risk class | CRITICAL | Section 7.3; "domain match, trust tier, capability contract check, MCP allowlist loaded, cost estimate" |
| **No MCP allowlist enforcement as part of capability contract** — MCP servers stored but not validated against declared capabilities | CRITICAL | Section 7.11; "Each agent's approved MCP server list is part of its capability contract" |
| No capability contract versioning with change tracking | HIGH | Phase 1 |
| No capability drift detection (observed vs declared divergence) | HIGH | Phase 2 |
| Certification workflow exists but is disconnected from contract enforcement | MEDIUM | Phase 1 |

**Maturity: 40%** — Data fields exist but no contract enforcement logic.

---

### 7.4 Policy & Governance

**Blueprint Requirement:** Autonomy bounds enforcement; OWASP ASI01-ASI10 policy mapping; injection defense; PII redaction; confidence-based HITL triggering.

**What Exists:**
- `app/agentic/governance/policy.py` — Full `PolicyEngine` with `PolicyEvaluator`, scope-based evaluation (GLOBAL/TENANT/AGENT), rule matching with 10 operators, callback system for deny/escalation
- `app/agentic/governance/autonomy.py` — `AutonomyManager` with 5 autonomy levels (LOCKED/RESTRICTED/ASSISTED/SUPERVISED/FULL), bounds enforcement, rate limiting, escalation triggers
- `app/agentic/governance/models.py` — `Policy`, `PolicyRule`, `PolicyDecision`, `RuleAction` (ALLOW/DENY/WARN/LOG/REQUIRE_APPROVAL/ESCALATE)
- `app/agentic/trust/injection.py` — `InjectionDetector` with pattern-based prompt injection detection (7 injection types)
- Frontend: Autonomy mode toggle with 5 modes (Observe/Recommend/Approve-to-Act/Auto/Federated)

**Gaps:**
| Gap | Severity | Blueprint Reference |
|-----|----------|-------------------|
| **No explicit OWASP ASI01-ASI10 policy templates** — engine is generic but no pre-built policies mapping to OWASP risks | HIGH | Section 3; Phase 1 |
| **No PII/PHI redaction layer** — injection detection exists but no pre-execution PII detection/redaction | HIGH | OWASP ASI07; Section 3 table |
| No EU AI Act risk class check in policy evaluation flow | HIGH | Step 5 of control flow; Section 7.14 |
| Policy engine is **in-memory only** — policies don't persist to database across restarts | HIGH | Phase 0 |
| No confidence-based HITL threshold as a policy-layer concern (open item #2) | MEDIUM | Open Item #2 |
| No adaptive policy learning | LOW | Phase 2 |

**Maturity: 65%** — Strong engine, missing OWASP templates and persistence.

---

### 7.5 HITL & Approval

**Blueprint Requirement:** Structured approval requests with full context; execution suspension with timer; override tracking.

**What Exists:**
- `app/agentic/approval/` — Approval workflow with state machine, override handling
- `app/models/agent.py` — `AgentApproval` ORM model (persisted to database)
- `app/models/workflow.py` — `ApprovalWorkflow` and `HITLRepairAudit` models
- Frontend: `AgentApprovalQueue.tsx` — Full two-panel HITL UI with risk levels, expiration countdown, approve/reject with notes
- API: `/api/v1/agents/approvals` — CRUD for approvals

**Gaps:**
| Gap | Severity | Blueprint Reference |
|-----|----------|-------------------|
| No timer-based auto-escalation when HITL requests expire | MEDIUM | Step 5b; "timer started" |
| No structured approval context that includes full intent + DCL metadata + cost estimate | MEDIUM | Step 5b; "structured approval request generated with full context" |
| Override tracking exists in model but no UI for viewing override history/audit | MEDIUM | Phase 1 |
| No confidence-threshold-based auto-approve/auto-reject | MEDIUM | Open Item #2 |

**Maturity: 70%** — Most complete domain. DB-persisted, has UI, API, and backend.

---

### 7.6 Coordination

**Blueprint Requirement:** Multi-agent workflow orchestration; sequential, parallel, fan-out/fan-in, pipeline patterns; dependency management; cross-vendor agent coordination.

**What Exists:**
- `app/agentic/coordination/orchestrator.py` — Full `MultiAgentOrchestrator` with 5 execution patterns (SEQUENTIAL, PARALLEL, FAN_OUT, PIPELINE, dependency-based), topological sort for task ordering, capability-based agent assignment
- `app/agentic/coordination/models.py` — `CoordinationTask`, `TaskResult`, `WorkflowPattern`
- `app/agentic/aoa/runtime.py` — `AOARuntime` that unifies TaskQueue + WorkerPool with fabric routing

**Gaps:**
| Gap | Severity | Blueprint Reference |
|-----|----------|-------------------|
| **No cross-vendor agent coordination via A2A** — orchestrator is local only | HIGH | Phase 1; Section 7.12 |
| No consensus voting pattern | MEDIUM | Phase 2 |
| No planner-executor pattern | MEDIUM | Phase 2 |
| No arbitration logic for conflicting agent outputs | MEDIUM | Phase 1 |
| Task executors default to mock execution if no handler registered | MEDIUM | Phase 0 |
| No cross-cloud orchestration | LOW | Phase 2 |

**Maturity: 60%** — Good local patterns, no external coordination.

---

### 7.7 Runtime (AOA Core)

**Blueprint Requirement:** Task submission with fabric routing; worker pool with auto-scaling; health monitoring; integration with orchestrator.

**What Exists:**
- `app/agentic/aoa/runtime.py` — `AOARuntime` (608 lines) integrating TaskQueue, WorkerPool, ActionRouter, FabricContext; RACI metadata on every task; fabric preset routing
- `app/agentic/scaling/` — `TaskQueue`, `WorkerPool`, `PoolConfig`, `ScalingPolicy`
- `app/agentic/fabric/` — `ActionRouter`, `FabricContext`, `FabricPreset` (6 enterprise presets), `ActionPayload`, `RoutedAction`
- `app/agentic/workflow.py` — `WorkflowBuilder` for LangGraph compilation

**Gaps:**
| Gap | Severity | Blueprint Reference |
|-----|----------|-------------------|
| **No actual LLM execution** — WorkflowBuilder compiles graphs but no real LLM provider integration | HIGH | Phase 0; Step 6 |
| Worker pool is in-memory — no distributed worker support | HIGH | Phase 1 |
| No circuit-breaker patterns | MEDIUM | OWASP ASI06; Section 3 |
| No concurrency caps / fan-out limits as policy-enforced controls | MEDIUM | OWASP ASI06 |
| Task queue is in-memory — no Redis/SQS backing for durability | HIGH | Phase 0 |
| Fabric routing is simulated — no real integration with iPaaS/API gateway endpoints | MEDIUM | Phase 1 |

**Maturity: 65%** — Architecture is correct, needs real execution backing.

---

### 7.8 Observability

**Blueprint Requirement:** Full execution trace (who, what, intent, outcome, cost); deterministic replay; forensic retention; MCP tool call logging; OWASP ASI09 alignment.

**What Exists:**
- `app/agentic/observability/tracing.py` — Full `Tracer` with `Trace`/`Span` hierarchy, context vars, span kinds (AGENT/TOOL/LLM/INTERNAL), exporter system, context manager support
- `app/agentic/observability/metrics.py` — Metrics collection
- `app/agentic/observability/vitals.py` — System vitals aggregation
- `app/telemetry/flow_publisher.py` — Async Redis event publishing
- Frontend: Full real-time monitoring dashboard with SSE + polling
- `app/models/connection.py` — `ApiJournal` model for API call audit logging

**Gaps:**
| Gap | Severity | Blueprint Reference |
|-----|----------|-------------------|
| **Traces are in-memory only** — no persistence to database or external store (Jaeger, OTLP) | CRITICAL | Phase 0; OWASP ASI09 |
| **No deterministic replay** — traces capture data but no replay engine | HIGH | Phase 1; "deterministic replay" |
| **No MCP tool-call-level audit** — MCP client executes tools but doesn't log to trace | HIGH | Section 7.11; OWASP ASI09 |
| No cost-per-outcome linking | MEDIUM | Phase 2 |
| No behavioral drift benchmarks vs SBOM baseline | MEDIUM | Phase 2; Section 7.13 |
| No forensic retention policy (data lifecycle for traces) | MEDIUM | Phase 1 |
| No OTLP export integration (OpenTelemetry) | MEDIUM | Phase 1 |

**Maturity: 55%** — Good architecture, critical persistence gap.

---

### 7.9 Lifecycle

**Blueprint Requirement:** Agent health monitoring; versioning; zombie detection automation; deprecation workflow; onboarding.

**What Exists:**
- `app/agentic/lifecycle/` — Onboarding, health monitoring modules
- `app/agentic/registry/models.py` — `AgentStatus.ZOMBIE` enum value
- `app/agentic/lifecycle/onboarding.py` — Agent onboarding workflow

**Gaps:**
| Gap | Severity | Blueprint Reference |
|-----|----------|-------------------|
| **No automated zombie detection** — status enum exists but no detection logic using AOD/AAM/DCL quorum | CRITICAL | Phase 1; Open Item #4 |
| No automated deprecation workflow | HIGH | Phase 1; "38% dormant NHI accounts" |
| No kill switch / quarantine mechanism | HIGH | OWASP ASI10; Section 3 |
| No version lifecycle enforcement (canary, rollback) | MEDIUM | Phase 1 |
| No health check aggregation across agent fleet | MEDIUM | Phase 0 |

**Maturity: 45%** — Scaffolding exists, no operational lifecycle management.

---

### 7.10 Economics

**Blueprint Requirement:** Cost attribution per agent; budget enforcement; priority scheduling; A2A cross-org economic tracking; ROI tracking.

**What Exists:**
- `app/agentic/governance/budget.py` — Full `BudgetEnforcer` with per-agent/tenant budgets, daily/weekly/monthly limits, per-action/per-run limits, alert thresholds (50/75/90/100%), auto-reset, acknowledgment workflow
- `app/agentic/gateway/cost.py` — Cost tracking in AI Gateway
- Frontend: Cost display in dashboard (today/week/month USD, budget remaining, utilization %)

**Gaps:**
| Gap | Severity | Blueprint Reference |
|-----|----------|-------------------|
| Budget enforcer is **in-memory** — no database persistence | HIGH | Phase 0 |
| **No A2A cross-org economic tracking** | HIGH | Section 7.12; Phase 1 |
| No conformity assessment cost tracking (EU AI Act) | MEDIUM | Phase 1; Section 7.14 |
| No priority scheduling based on budget | MEDIUM | Phase 1 |
| No ROI tracking per agent outcome | LOW | Phase 2 |
| No automated agent cost-benefit analysis | LOW | Phase 2 |

**Maturity: 60%** — Logic is solid, needs persistence and A2A scope.

---

### 7.11 MCP Governance (NEW — CRITICAL GAP)

**Blueprint Requirement:** MCP server allowlist per agent; MCP tool-call audit; MCP server integrity verification; MCP scope minimization; rogue MCP server detection.

**What Exists:**
- `app/agentic/mcp_client.py` — `MCPClient` with server management, tool discovery, tool execution, OBO token support
- `app/models/agent.py` — `mcp_servers` JSON field per agent
- `app/agentic/mcp_servers/` — AOS-specific MCP server implementations

**What Does NOT Exist:**

| Missing Capability | Blueprint Reference | OWASP Risk |
|-------------------|-------------------|------------|
| **MCP server allowlist enforcement** — agents can connect to any configured server; no policy-gated allowlist | Section 7.11 | ASI03 |
| **MCP tool-call audit trail** — tool executions not logged to trace/audit | Section 7.11 | ASI09 |
| **MCP server integrity verification** — no verification that servers haven't been impersonated | Section 7.11 | ASI05 |
| **MCP scope minimization** — agents can call any tool on any configured server; no least-privilege per capability | Section 7.11 | ASI02 |
| **Rogue MCP server detection** — no anomaly detection on MCP connections | Section 7.11 | ASI10 |

**Maturity: 0%** — MCP client exists (transport layer) but MCP governance (policy layer) is entirely absent. This is a top-3 gap.

---

### 7.12 A2A Protocol Governance (NEW — HIGH GAP)

**Blueprint Requirement:** Agent Card issuance/validation; cross-org trust tiering; long-running task state; A2A economic tracking.

**What Exists:**
- `app/agentic/a2a/protocol.py` — Full `A2AProtocol` with message types, routing, request/response correlation, fabric context integration
- `app/agentic/a2a/agent_card.py` — `AgentCard` data model
- `app/agentic/a2a/discovery.py` — `AgentDiscovery` service
- `app/agentic/a2a/delegation.py` — `DelegationManager` with request/response
- `app/agentic/a2a/context_sharing.py` — Context sharing protocol

**Gaps:**
| Gap | Severity | Blueprint Reference |
|-----|----------|-------------------|
| **No A2A Agent Card validation for inbound calls** — cards exist but inbound validation is not enforced | HIGH | Section 7.12; OWASP ASI04 |
| **No cross-org trust tiering** — external agents not assigned trust tiers via A2A | HIGH | Section 7.12; "third-party/unverified by default" |
| A2A is **local in-memory only** — no HTTP/SSE transport for cross-vendor communication | HIGH | Section 7.12 |
| No long-running task state persistence (hours/days) | HIGH | Phase 1 |
| No A2A economic tracking | HIGH | Phase 1 |
| Agent Card issuance is manual, not automated on registration | MEDIUM | Phase 0 |

**Maturity: 30%** — Transport protocol exists but governance and external connectivity absent.

---

### 7.13 AI-SBOM (NEW — CRITICAL GAP)

**Blueprint Requirement:** Per-agent AI-SBOM generation on registration; SBOM integrity verification at deploy; SBOM API for GRC integration; SBOM drift detection.

**What Exists:**
- **Nothing.** No SBOM-related code, models, schemas, or API endpoints exist anywhere in the codebase.

**What Must Be Built:**

| Capability | Description | Phase |
|-----------|-------------|-------|
| Per-agent AI-SBOM generation | Model version, capability contract version, MCP server list + versions, tool dependencies, training data provenance | Phase 0 |
| SBOM format (CycloneDX or SPDX) | Open Item — CycloneDX has AI extensions | Open Item |
| SBOM generation on agent registration | Auto-generate on registration; update on capability contract change | Phase 0 |
| SBOM API for GRC integration | REST endpoint to export SBOM per agent for enterprise GRC platforms | Phase 1 |
| SBOM integrity verification at deploy | Hash-based verification; tampered dependency triggers quarantine | Phase 1 |
| SBOM drift detection | Detect when agent dependencies change vs baseline; trigger capability review | Phase 2 |
| FARM integration | SBOM provides ground-truth baseline for behavioral drift measurement | Phase 2 |

**Maturity: 0%** — No implementation. This is required by EU AI Act Art. 11 (technical documentation) and OWASP ASI05 (supply chain).

---

### 7.14 Regulatory Compliance Evidence Layer (NEW — CRITICAL GAP)

**Blueprint Requirement:** Conformity assessment evidence package; AI inventory + risk classification export; incident reporting; technical documentation compilation.

**What Exists:**
- **Nothing explicit.** While the platform generates audit trails and lifecycle data that *could* feed compliance evidence, there is no:
  - Compliance evidence compilation layer
  - EU AI Act risk classification system
  - Conformity assessment export
  - Incident reporting artifact generation

**What Must Be Built:**

| Evidence Type | AOA Source (per Blueprint) | EU AI Act Requirement | Status |
|--------------|--------------------------|----------------------|--------|
| Agent registry with risk classification | Registry + capability contracts | Art. 16 (AI system inventory) | Registry exists; **no risk classification** |
| Human oversight documentation | HITL logs + override tracking | High-risk system oversight | HITL logs exist; **no export/compilation** |
| Data access audit trail | Execution trace + DCL pointer log | Art. 13 (transparency) | Traces exist in-memory; **no persistence** |
| Incident reporting artifacts | Quarantine events + zombie detection | Post-market monitoring | **Neither quarantine nor zombie detection implemented** |
| Technical documentation | AI-SBOM + contracts + policy manifests | Art. 11 (technical documentation) | **AI-SBOM doesn't exist; contracts are informal** |
| Accuracy/robustness records | FARM evaluation outputs | Art. 15 | FARM integration exists at dashboard level; **no formal records** |
| Conformity assessment package | Compiled from all above | Art. 43 | **Not implemented** |

**Maturity: 0%** — The raw data ingredients exist in scattered form, but the compliance evidence layer that compiles, formats, and exports them is entirely absent. With 6 months to the EU AI Act deadline, this is the highest strategic priority.

---

## OWASP Agentic Top 10 Coverage Assessment

| OWASP ID | Risk | Required AOA Control | Implementation Status |
|----------|------|---------------------|----------------------|
| ASI01 | Prompt Injection | Context sanitization; input validation | PARTIAL — `InjectionDetector` has pattern matching; no context sanitization pre-LLM |
| ASI02 | Excessive Agency | Capability contracts + autonomy bounds; least-privilege | PARTIAL — Autonomy bounds exist; **no MCP scope minimization**; no formal contracts |
| ASI03 | Insecure Tool Use / MCP Abuse | MCP server allowlisting; tool-level permissioning; runtime audit | **NOT IMPLEMENTED** — MCP governance absent |
| ASI04 | Delegated Trust Abuse | Identity tiering; explicit delegation rules; chain-of-trust | PARTIAL — Trust tiers exist; **no chain-of-trust enforcement in A2A** |
| ASI05 | Supply Chain Compromise | AI-SBOM; provenance tracking; integrity verification | **NOT IMPLEMENTED** — No SBOM |
| ASI06 | Cascading Failure / Blast Radius | Containment policies; concurrency caps; circuit-breakers | PARTIAL — Policy engine can deny; **no circuit-breakers or fan-out limits** |
| ASI07 | Data Leakage via Agents | Context-aware data minimization; PII redaction | **NOT IMPLEMENTED** — No PII redaction layer |
| ASI08 | Memory / State Corruption | Scoped memory access; session isolation; memory audit | PARTIAL — Memory governance module exists; **no audit log** |
| ASI09 | Insufficient Audit Trail | Full execution trace; deterministic replay; forensic retention | PARTIAL — Tracer exists; **in-memory only, no persistence, no replay** |
| ASI10 | Rogue Agents | Behavioral drift detection; zombie detection; kill switch | **NOT IMPLEMENTED** — No automated zombie detection, no kill switch |

**OWASP Coverage: 3/10 partially addressed, 0/10 fully addressed, 7/10 have critical gaps.**

---

## Blueprint Control Flow (Section 12) — Step-by-Step Gap Mapping

| Step | Blueprint Action | Implementation Status | Gap |
|------|-----------------|----------------------|-----|
| 1 | NLQ → AOA: Intent with classification + confidence | PARTIAL | NLQ router exists (`nlp_simple.py`) but no confidence score passed to AOA |
| 2 | AOA → DCL: Semantic context request | NOT IMPLEMENTED | No DCL integration for semantic context retrieval |
| 3 | Registry: Agent selection with contract check + MCP allowlist + cost estimate | PARTIAL | Agent selection exists; **no contract check, no MCP allowlist validation, no cost estimate** |
| 4 | OWASP Check: Injection scan, PII detection, scope minimization, SBOM integrity | MINIMAL | Injection scan exists; **no PII detection, no scope minimization, no SBOM check** |
| 5 | Policy Engine: Autonomy + domain auth + budget + HITL threshold + EU AI Act risk class | PARTIAL | Autonomy + budget exist; **no EU AI Act risk class check** |
| 5a | Approved → AAM: Fabric action routing with MCP permissions | PARTIAL | Fabric routing exists; **no MCP permission scoping** |
| 5b | HITL: Structured approval with full context + timer | PARTIAL | Approval exists; **no timer, no full DCL context** |
| 5c | A2A: Cross-vendor task with card validation + trust tier + economic tracking | PARTIAL | A2A protocol exists; **no card validation, no trust tier enforcement, no economics** |
| 6 | AAM → Adapter: Execute with idempotency key | PARTIAL | AAM adapters exist; idempotency key model exists but middleware disabled |
| 7 | Trace + SBOM: Capture trace, log MCP calls, reference SBOM, update evidence | PARTIAL | Trace exists in-memory; **no MCP call logging, no SBOM, no evidence update** |
| 8 | FARM: Independent evaluation | PARTIAL | FARM simulation exists; **no real independent oracle evaluation** |
| 9 | Lifecycle + Compliance: Close run, attribute cost, health update, zombie check, evidence package | PARTIAL | Cost attribution exists; **no zombie check, no evidence package update** |

---

## Top 10 Priority Gaps (Ranked by Strategic Impact)

### P0 — Must Start Immediately (EU AI Act / OWASP Blockers)

1. **Regulatory Compliance Evidence Layer** (7.14) — August 2026 EU AI Act deadline. Conformity assessments take 6-12 months. Zero implementation exists.

2. **AI-SBOM Generation** (7.13) — Required by EU AI Act Art. 11 and OWASP ASI05. Zero implementation exists. CycloneDX format decision needed (Open Item).

3. **MCP Governance** (7.11) — OWASP ASI03 is the #3 risk. 97M monthly MCP SDK downloads mean this is the primary attack surface. Zero governance implementation.

### P1 — Must Start Within 30 Days

4. **Observability Persistence** — Traces, policies, budgets are all in-memory. A single restart loses all audit data. This undermines every compliance and security claim.

5. **NHI Identity Governance** (7.2 enhanced) — Identity issuance, permission expiry, over-permissioned detection. AOA's competitive differentiator per blueprint.

6. **PII/PHI Redaction Layer** — OWASP ASI07. No pre-execution PII detection exists. Required for HIPAA/GDPR deployments.

### P2 — Must Start Within 60 Days

7. **Zombie Detection Automation** (7.9) — Kill switch + quarantine mechanism. OWASP ASI10. No automated detection or remediation exists.

8. **Capability Contract Formalization** (7.3) — Contracts are string lists, not structured schemas. Blocks MCP governance, SBOM generation, and drift detection.

9. **A2A External Connectivity** (7.12) — A2A is local-only. Cross-vendor coordination (the entire point of A2A per Linux Foundation spec) is not functional.

10. **Real LLM Execution Pipeline** — WorkflowBuilder compiles LangGraph definitions but no actual LLM provider integration exists. Agents can't actually think.

---

## Open Architecture Items Status (from Blueprint Section 11)

### Original 5 Items

| # | Decision | Status in Codebase |
|---|----------|--------------------|
| 1 | Per-agent vs per-plan budget quota | BudgetEnforcer supports per-agent and per-tenant. **Per-plan not implemented.** Decision needed. |
| 2 | HITL confidence threshold ownership | Not implemented. No confidence threshold in policy or DCL signal. **Decision needed.** |
| 3 | A2A protocol version | Protocol version field set to "1.1" in code. **No decision documented on which Linux Foundation spec version.** |
| 4 | Zombie detection quorum rule | Not implemented. **Decision needed before implementation.** |
| 5 | Agent identity storage (AOA-issued vs enterprise IdP) | AOA currently issues basic IDs. **No enterprise IdP integration. Decision needed.** |

### New 4 Items (Added Feb 2026)

| # | Decision | Status in Codebase |
|---|----------|--------------------|
| 6 | MCP server registration authority | Not implemented. **HIGH urgency — affects Phase 0 MCP governance.** |
| 7 | AI-SBOM format (SPDX vs CycloneDX) | Not implemented. **HIGH urgency — affects GRC integration.** |
| 8 | EU AI Act risk classification ownership | Not implemented. **CRITICAL — Aug 2026 deadline.** |
| 9 | Agentic AI Foundation membership | **Strategic decision for CEO.** |

---

## Architectural Integrity Assessment

### What's Architecturally Sound
- **RACI compliance** is baked into the runtime (`AOATask.raci_responsible`, `raci_accountable`, etc.)
- **Fabric Plane Mesh** abstraction is well-designed with 6 enterprise presets
- **Multi-tenant isolation** via `tenant_id` on all entities
- **Separation of concerns** — registry, governance, coordination, runtime are cleanly separated
- **Frontend-backend contract** is solid — typed API responses, polling + SSE + WebSocket
- **A2A protocol design** follows Google A2A patterns correctly

### What's Architecturally Concerning
- **In-memory state everywhere** — Registry, PolicyEngine, BudgetEnforcer, Tracer, Orchestrator all use Python dicts. No crash recovery, no horizontal scaling, no audit persistence.
- **No event sourcing** — State changes are mutated in place. No event log for reconstruction.
- **Global singletons** — `get_policy_engine()`, `get_aoa_runtime()`, `get_tracer()` return module-level singletons. Works for single-process but blocks multi-worker deployment.
- **Mock execution fallbacks** — Several components return mock data when real integrations aren't configured. This is fine for demo but could mask production failures if not gated by environment flag.

---

## Recommended Implementation Sequence

```
Month 1 (March 2026):
├── Persist all in-memory state to PostgreSQL (traces, policies, budgets)
├── Design AI-SBOM schema (resolve CycloneDX vs SPDX decision)
├── Design Capability Contract formal schema
├── Design MCP Governance allowlist data model
└── Start Regulatory Evidence Layer data model

Month 2 (April 2026):
├── Implement MCP server allowlist enforcement per agent
├── Implement MCP tool-call audit logging to trace store
├── Implement per-agent AI-SBOM generation on registration
├── Implement PII/PHI redaction pre-execution layer
└── Start NHI identity issuance system

Month 3 (May 2026):
├── Implement EU AI Act risk classification per agent
├── Implement conformity assessment evidence package export
├── Implement zombie detection automation (quorum rule)
├── Implement kill switch + quarantine mechanism
└── Implement A2A external HTTP transport

Month 4-5 (June-July 2026):
├── End-to-end compliance evidence generation testing
├── OWASP ASI01-ASI10 formal policy templates
├── A2A cross-org trust tiering + economic tracking
├── Deterministic replay engine
└── SBOM integrity verification at deploy

Month 6 (August 2026):
├── EU AI Act conformity assessment dry run
├── Full OWASP coverage validation
└── Production readiness assessment
```

---

## Summary

The AOA codebase demonstrates **strong architectural vision** aligned with the blueprint's original 10 domains. The team has built real orchestration logic, not just scaffolding. The frontend is production-grade. The fabric abstraction and RACI integration are well-thought-out.

The critical gaps are:
1. **The four new Blueprint v2 domains are entirely unbuilt** (MCP Governance, AI-SBOM, Regulatory Evidence, enhanced NHI)
2. **In-memory state** across all backend services makes the system non-durable and non-auditable
3. **OWASP Agentic Top 10** has 0/10 risks fully addressed
4. **9 open architecture decisions** need CEO/architect input before implementation can proceed

The August 2, 2026 EU AI Act deadline is the forcing function. Working backward from that date, MCP Governance, AI-SBOM, and the Regulatory Evidence Layer must begin construction immediately.
