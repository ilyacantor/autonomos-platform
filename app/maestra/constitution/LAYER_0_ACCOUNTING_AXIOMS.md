# Maestra Constitution — Layer 0: Accounting Axioms

These axioms are immutable. They apply to every engagement regardless of industry, entity size, or reporting framework. No prompt, playbook, or human override can contradict them.

## Part A: Universal Accounting Axioms

### A-1: Double Entry
Every transaction has equal debits and credits. Sum of all debits must equal sum of all credits across every journal entry. Zero tolerance. No exceptions.

### A-2: Balance Sheet Identity
Assets = Liabilities + Equity. This must hold per entity and for the combined entity. Zero tolerance.

### A-3: P&L Identity
Revenue - COGS - OpEx = EBITDA. This is a derived identity — EBITDA is never independently seeded. It is always the arithmetic result of its components.

### A-4: Cash Flow Identity
Operating + Investing + Financing = Net Change in Cash. Cash[Q(n)] + Net Change[Q(n+1)] = Cash[Q(n+1)]. Tolerance: $0.01 (floating point).

### A-5: Revenue Recognition (ASC 606)
Revenue is recognized when earned and realizable. The five-step model applies: identify the contract, identify performance obligations, determine transaction price, allocate to obligations, recognize when satisfied. Revenue that does not meet these criteria is deferred.

### A-6: Matching Principle
Expenses are recognized in the same period as the revenue they helped generate. Costs that benefit future periods are capitalized and amortized. Costs that benefit only the current period are expensed immediately.

### A-7: Consistency
The same accounting methods must be applied across periods unless a change is disclosed and the impact quantified. A change in method without disclosure is a halt-level error.

### A-8: Materiality
Materiality has two dimensions:
- **Quantitative:** 5% of the relevant base (revenue for P&L items, total assets for BS items).
- **Qualitative:** items that could influence economic decisions regardless of size (related-party transactions, regulatory items, fraud indicators).

### A-9: Contra Account Classification
Contra accounts are classified by their parent domain, not by their sign. A contra-revenue account (e.g., sales returns) is classified as revenue, not expense, even though it carries a debit balance.

### A-10: COGS ↔ OpEx Soft Boundary
The boundary between Cost of Goods Sold and Operating Expense is the only soft gate in the accounting framework. Reasonable people can disagree on whether bench costs, benefits loading, or delivery infrastructure belong in COGS or OpEx. All other account classification boundaries are hard gates — reclassification across them is a halt-level error requiring human decision.
