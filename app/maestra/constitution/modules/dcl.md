# DCL — Data Context Layer

## What DCL Does

DCL is the semantic context layer at the center of AOS. All structured knowledge in the platform lives here as semantic triples. Every other module either writes data into DCL or reads from it. DCL is the single store of record for everything AOS knows about a customer's environment.

## What a Triple Is

A triple is a structured fact with five parts:

- **Entity ID:** which organization or business unit the fact belongs to.
- **Concept:** what the fact describes, using a hierarchical naming scheme. For example, `compensation.base` describes base compensation; `revenue.consulting` describes consulting revenue. The first segment of the concept name is the domain (compensation, revenue, cofa, position, etc.).
- **Property:** which specific attribute — the value itself, a label, a classification.
- **Value:** the actual data.
- **Period:** when the fact applies (a quarter, a month, a year).

Every triple also carries provenance: which source system produced it, which source field it maps to, a confidence score and confidence tier, which pipe and run generated it, and when it was created. Provenance means every number in the platform can be traced back to its origin.

## How Data Is Organized

Concepts are grouped into domains — the first segment of the concept name. Examples: compensation, revenue, cofa, position, employee, engineering_work. As more data flows through the pipeline, new domains appear. The current store holds data across 17 domains, covering three entities (Meridian as acquirer, Cascadia as target, and BlueWave as Meridian's HR system), spanning 24 time periods.

DCL validates everything that comes in. Schema-on-write validation checks that incoming data matches a known pipe definition. If data arrives without a matching pipe, DCL rejects it with a specific error explaining what is missing. Data that passes validation is stored with full provenance.

## The Merge View (Convergence)

For multi-entity scenarios, DCL provides a merge view showing how two entities' data compares:

- **Entity statistics:** how many facts exist per entity, per domain.
- **Side-by-side chart of accounts comparison:** acquirer accounts on the left, target accounts on the right.
- **Account match table:** where entity resolution has identified corresponding accounts across entities.
- **Unmatched and orphan accounts:** accounts from either entity that have no counterpart.
- **COFA triple browser:** raw view of the chart-of-accounts facts in the store.

## Conflicts

When two entities treat the same economic substance differently — different revenue recognition timing, different capitalization policies, different cost classifications — these appear as typed conflicts. Each conflict has a type (recognition timing, measurement basis, classification, or scope), a severity level, and an estimated annual dollar impact calculated from actual financial data. Conflicts are ranked by dollar impact so the most material differences surface first.

## What Users Can Ask About

- "What data is in the store?"
- "How many facts exist across all domains?"
- "What domains are covered?"
- "What is the merge status between the two entities?"
- "What are the top conflicts ranked by dollar impact?"
- "Where did this specific number come from?" (provenance)
- "Which entity does this data belong to?"

## What DCL Does Not Do

DCL stores, validates, and serves data. It does not generate data — Farm does that. It does not discover systems — AOD does that. It does not make accounting decisions — humans do, with Maestra's help surfacing the relevant information and business implications. DCL enforces hard accounting gates (domain boundaries, balance sheet identity, double-entry) but the judgment calls about how to treat ambiguous items are always made by people.
