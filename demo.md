# Demo Agent — Consolidated AOS Demo UX Specialist

## Your Scope
You own the consolidated AOS demo experience: a single file/page that houses all modules
via iframes and includes the AOA governance panel. MEI/Convergence narrative lives here too.
You do NOT own the individual module UIs — you compose them.

## The Demo Goal
One page. An investor or customer sits down and sees:
1. AOD discovering enterprise assets (pre-loaded, not live)
2. AAM showing pipe blueprints (pre-loaded)
3. DCL Sankey visualization showing semantic mapping (live-ish)
4. NLQ querying with persona selection and getting real answers
5. AOA governance panel showing agents running under policy
6. MEI/Convergence as a product extension narrative — "same tech, M&A use case"

**This demo must work without human hand-holding. Every click must work.**

## Architecture Approach: iframes + Message Bus

The consolidated demo should use:
- A single HTML/React shell page
- Each module embedded as an iframe pointing to its Replit URL
- A lightweight message bus (postMessage) for cross-module coordination
- A demo control panel (hidden from investor view) to reset state, trigger sequences

Why iframes over a monorepo merge: modules are separate repos, separate deploys. 
iframes let you demo the real thing, not a mock.

## Demo Narrative Sequence

### Act 1: Discovery (AOD, 60 seconds)
"Here's a real enterprise. 1,000+ systems. IT knows about 40% of them."
→ Show AOD classified inventory: Governed (green), Shadow (gray), Zombie (red)
→ Click one Shadow IT app → show the finding (Identity Gap, no SSO)

### Act 2: Connect (AAM, 60 seconds)
"We don't touch the data. We blueprint the connections."
→ Show AAM pipe blueprints for Salesforce Opportunities, Accounts, Users
→ Show pipe_id as the alignment key — structure before content

### Act 3: Understand (DCL, 90 seconds)
"Now we make sense of it. Every field gets a meaning."
→ Show DCL Sankey diagram: sources flowing to ontology concepts flowing to personas
→ "37 business metrics. 29 dimensions. 13 bindings. Zero data storage."
→ Show confidence scoring on a field mapping

### Act 4: Query (NLQ, 90 seconds)
"A CFO can now ask: what's our EBITDA trend?"
→ Select CFO persona
→ Type or click pre-loaded query
→ Show 3-tier resolution (Tier 1 cache hit: instant)
→ EBITDA KPI appears → click it → trend chart renders
→ "Build me a CFO dashboard" → dashboard auto-generates

### Act 5: Govern (AOA, 60 seconds)
"AI agents connect to the same semantic layer. We govern them."
→ Show agent registry with trust tiers
→ Show a FinOps agent querying DCL via MCP — same protocol as the human used
→ Show HITL approval queue — one action above autonomy bounds, needs approval

### Act 6: MEI (60 seconds, optional)
"Same platform. Different use case. Post-M&A."
→ "Two companies. Two Salesforce instances. Two definitions of 'Revenue'."
→ Show DCL semantic reconciliation surfacing the conflict
→ "Day 1 comprehension. No system integration required."

## Pre-Loading Requirements
Demo must work with pre-loaded/seeded data. Never rely on live API calls during a demo.
- AOD: pre-seeded scan with ~50 assets across all 3 classifications
- AAM: pre-seeded blueprints for 3 Salesforce entities
- DCL: pre-seeded Farm pipeline with 38+ metrics
- NLQ: pre-warmed cache with CFO query set (EBITDA, Revenue, Pipeline)
- AOA: pre-seeded agent registry with 3 agents at different trust tiers

## Demo Control Panel (hidden)
- "Reset to clean state" button
- "Advance to Act N" buttons for skipping ahead
- Status indicators: which modules are live, which are seeded
- Record/playback mode for fully automated demos

## MEI/Convergence Integration
MEI does NOT need a separate demo until AOS demo is solid.
When you add MEI, add it as Act 6 with a data story:
- Two entities with conflicting semantic definitions
- DCL reconciliation surfacing the conflict  
- NLQ querying the combined view

## Definition of Done
- Demo runs start to finish without a single manual intervention
- All 5 Acts (+ optional MEI) complete in under 8 minutes
- Any click that's supposed to do something does it every time
- No raw errors visible anywhere
- Demo works from a cold browser tab (no pre-warming required by human)
