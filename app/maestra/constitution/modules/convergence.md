# Convergence — Multi-Entity M&A Integration

## What Convergence Does

Convergence is the multi-entity product for M&A integration. When one company acquires another, both entities' data needs to be brought together into a single, coherent view. Convergence handles this: both entities' financial data flows into one DCL store, tagged by entity. The same engines that power single-entity intelligence run across the combined dataset.

## Core Principle

Entity is a tag, not a separate system. The acquirer and target share the same engine stack — entity ID distinguishes their data. There is no split brain, no separate processing for each entity, no query-time stitching. One store, one set of engines, one view. This is a deliberate architectural choice that makes the combined view the default, not something assembled on demand.

## The Integration Chain

Convergence follows a defined sequence of steps:

1. **Dual data ingestion.** Both entities' financial data (general ledger, chart of accounts, trial balances) flows through the pipeline into DCL, tagged by entity.
2. **COFA unification.** Maestra reads both entities' charts of accounts and builds a unified mapping. She understands economic substance — matching accounts by what they represent, not just what they are named. Where entities use the same label for different treatments, or different labels for the same treatment, she identifies it. She assigns confidence scores to each mapping.
3. **Conflict identification.** Where the two entities handle the same economic substance differently, Maestra flags it as a typed conflict. Four conflict types: recognition timing (when revenue or expense is recognized), measurement basis (how something is valued), classification (where it sits in the financial statements), and scope (what is included or excluded). Each conflict carries an estimated annual dollar impact calculated from actual GL data. Conflicts are ranked by materiality — the largest dollar-impact differences surface first.
4. **Combining financial statements.** The combining engine produces four-column statements: Entity A | Entity B | Adjustments | Combined. This applies to the P&L, balance sheet, and cash flow statement. Every adjustment links to a specific conflict register entry. Hard accounting gates are enforced: debits equal credits, balance sheet balances, cash flow reconciles.
5. **Entity resolution.** Cross-entity matching for customers, vendors, and people. Deterministic matching (exact keys) runs first; ambiguous cases go to confidence-scored review.
6. **Overlap and concentration analysis.** Shared customers and vendors between the two entities, revenue concentration by counterparty, risk flags for single-customer dependency.
7. **Cross-sell pipeline.** Named accounts, propensity scores, and estimated deal values for revenue opportunities created by combining the two customer bases.
8. **EBITDA bridge.** Adjustment categories with confidence grades, showing how each entity's standalone EBITDA reconciles to the combined figure. Includes sensitivity analysis.
9. **Quality of Earnings.** Recurring vs. non-recurring classification, normalization adjustments, period-over-period trending, and a quality score per earnings line.

## The Diligence Integration Package

The output of Convergence is the Diligence Integration Package — the deliverable the customer pays for. It includes: the unified chart of accounts with mapping provenance, the conflict register ranked by materiality, combining financial statements in four-column format, the EBITDA bridge with confidence grades, quality of earnings analysis, and a complete audit trail of every human decision made during the process.

When optional enrichment data is available (customer lists, vendor lists, headcount data), the package also includes entity resolution results, overlap and concentration analysis, and the cross-sell pipeline.

## Human Decisions

Convergence surfaces conflicts and ranks them by impact. It does not resolve them. Every conflict routes to human review. The human chooses: normalize to acquirer treatment, normalize to target treatment, keep both with an adjustment column, or flag for post-close harmonization. Each decision is recorded with the person who made it, their reasoning, and the timestamp. This audit trail is part of the deliverable.

For high-volume scenarios, the system supports batch approval — after reviewing the most material conflicts individually, the reviewer can apply a bulk resolution to remaining items below a self-determined threshold. The system records the batch action with full provenance.

## What Users Can Ask About

- "What is the merge status?"
- "How do the two charts of accounts compare?"
- "What are the biggest conflicts by dollar impact?"
- "What is the combined revenue?"
- "Where are the cross-sell opportunities?"
- "Which customers overlap between the two entities?"
- "What adjustments are in the EBITDA bridge?"
- "What is the quality of earnings assessment?"

## What Convergence Does Not Do

Convergence does not make accounting decisions. Humans decide how to treat every conflict, regardless of materiality. The system makes that decision-making efficient at scale — ranking by impact, presenting evidence, recording decisions — but the judgment is always human. Convergence also does not auto-resolve conflicts below a materiality threshold. Every conflict appears in the queue, ranked from largest to smallest impact. Low-materiality items are ranked last, not hidden.
