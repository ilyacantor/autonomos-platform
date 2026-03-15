# Domain Playbook: Consulting × BPM/Managed Services

## Typical CoA Patterns

### Consulting firms (mid-market, $1B-$10B)
- Revenue: gross recognition, broken out by practice area
- COGS: direct labor, subcontractors, travel, client software
- Bench costs: sometimes COGS, sometimes OpEx (this is a known judgment call)
- S&M: separately stated, includes recruiting for revenue roles
- R&D: present if firm has IP/platform components

### BPM/Managed Services firms ($500M-$2B)
- Revenue: often net of pass-through costs (net vs gross is the #1 conflict)
- COGS: fully loaded labor (benefits bundled in), delivery infrastructure
- S&M: frequently bundled with delivery under "Client Services"
- Recruiting: may be capitalized as workforce acquisition asset
- Automation/tooling: may be capitalized vs expensed

## Known Conflict Patterns

1. **Revenue gross-up** — consultancy reports gross, BPM reports net. Combined revenue requires adjustment to normalize. Materiality: 15-30% of smaller entity's revenue.
2. **Benefits loading** — consultancy separates benefits in OpEx, BPM loads into COGS. Affects gross margin comparability. Materiality: 8-15% of COGS.
3. **S&M bundling** — consultancy breaks out, BPM bundles. Affects OpEx comparability.
4. **Recruiting capitalization** — one expenses, one capitalizes. Affects both COGS/OpEx and asset base.
5. **Automation capitalization** — same pattern as recruiting.
6. **Depreciation method** — straight-line vs accelerated. Affects D&A and book value of assets.

## Materiality Guidance

- Revenue recognition differences > 5% of combined revenue: HIGH severity
- Classification differences > $10M annual impact: MEDIUM severity
- Policy differences with < $5M annual impact: LOW severity (note, don't adjust)

## Completeness Requirements

- Every GL account from BOTH entities must appear as its own row in the mapping table.
- Parent/header accounts (e.g., "6200 General & Administrative" which parents 6210-6250) must be mapped as their own line — they map to the unified parent category.
- After producing the mapping, count the rows. The count must equal the sum of both entities' account counts. If any accounts are missing, add them before presenting.

## Expected Outputs

The COFA mapping should produce:
- Every GL account from both entities mapped to a unified structure (zero orphans)
- 5-7 conflicts identified (the 6 above plus any the CoA structure reveals)
- Each conflict typed (recognition, classification, capitalization, policy)
- Dollar impact estimated per conflict
- Severity assigned per materiality guidance
