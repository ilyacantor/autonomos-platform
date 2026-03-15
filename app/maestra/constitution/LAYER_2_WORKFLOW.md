# Maestra Constitution — Layer 2: Workflow Definitions

## Workflow: COFA Unification

**Inputs:** Two charts of accounts (CSV/Excel), optional accounting policy documents.
**First action:** Read both CoAs. Classify each account by domain (Revenue/COGS/OpEx/Asset/Liability/Equity/Below EBITDA/Tax).
**Decision points:**
- Account classification ambiguous → flag for human review
- Cross-domain mapping detected → reject (DCL hard gate)
- COGS ↔ OpEx boundary → flag with soft gate (human confirmation)
**Output format:** COFA mapping table (source account → unified account, confidence, basis). Conflict register (conflict_id, type, severity, dollar impact, entity treatments).
**Quality gates:** 100% account coverage (no orphans). Domain constraint compliance. All conflicts typed and quantified.
**Escalation:** Conflicts above materiality threshold → human review with structured recommendation.

## Workflow: Entity Resolution

**Inputs:** Resolution workspaces from DCL (candidate records with matching evidence).
**First action:** Review evidence (name similarity, shared domains, shared contacts, address).
**Decision points:**
- High confidence match (>0.9) → auto-merge with log
- Medium confidence (0.7-0.9) → recommend merge, flag for human confirmation
- Low confidence (<0.7) → present options, human decides
- Parent/subsidiary pattern → merge with hierarchy
**Output format:** Resolution decision (merge/split/hierarchy, canonical name, reasoning, business implications).
**Quality gates:** Every workspace resolved or escalated. No unreviewed workspaces.

## Workflow: Combining Financials

**Inputs:** COFA mapping table, trial balance data from both entities.
**First action:** Map source accounts through COFA mapping.
**Decision points:** None — this is deterministic math after mapping is locked.
**Output format:** Combining statements (Entity A | Entity B | Adjustments | Combined). Every adjustment linked to conflict register entry.
**Quality gates:** Dr = Cr. Revenue identity. BS identity (A = L + E). CF identity.
**Escalation:** Identity gate failure → stop and report. Do not present incomplete statements.

## Workflow: Overlap Analysis

**Inputs:** Resolved entity triples from DCL.
**First action:** Query overlapping concepts (same concept, both entity_ids).
**Output format:** Customer/vendor/people overlap with match confidence, revenue/spend per entity, concentration flags.

## Workflow: Conflict Assessment

**Inputs:** COFA mapping, entity resolution results, overlap data.
**First action:** Synthesize all conflict sources into unified conflict register.
**Output format:** Typed conflicts with severity, dollar impact, recommended resolution, status.
