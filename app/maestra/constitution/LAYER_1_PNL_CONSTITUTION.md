# Maestra Constitution — Layer 1: P&L Agent Constitution

This constitution governs the P&L (Income Statement) agent. It defines the structure, derivation rules, sign conventions, and combining logic for income statement generation.

## Line Item Ordering

The income statement must present line items in this exact order:

1. **Revenue** — total and by category (e.g., subscription, professional services, licensing)
2. **Cost of Goods Sold (COGS)** — total and by category
3. **Gross Profit** — computed: Revenue - COGS
4. **Operating Expenses** — broken out by function:
   - Sales & Marketing (S&M)
   - Research & Development (R&D)
   - General & Administrative (G&A)
5. **EBITDA** — computed: Gross Profit - Total OpEx
6. **Depreciation & Amortization (D&A)**
7. **Stock-Based Compensation (SBC)** — if applicable
8. **Operating Profit (EBIT)** — computed: EBITDA - D&A - SBC
9. **Interest Income / (Expense)** — net
10. **Other Income / (Expense)** — net
11. **Pre-Tax Income (EBT)** — computed: EBIT + Interest + Other
12. **Income Tax Provision**
13. **Net Income** — computed: EBT - Tax

## Derivation Rules

- Every subtotal and total is derived from its components. No subtotal is independently seeded.
- Gross Profit = Revenue - COGS. Always computed, never provided as an input.
- EBITDA = Gross Profit - Total OpEx. Always computed.
- Operating Profit = EBITDA - D&A - SBC. Always computed.
- Net Income = Pre-Tax Income - Tax. Always computed.
- If any component required for a derivation is missing, the subtotal must be reported as missing — never zero-filled.

## Sign Convention

- Revenue: positive value represents income earned.
- Expenses (COGS, OpEx, D&A, SBC, Tax): positive value represents cost incurred.
- Profit line items: computed as revenue minus expenses. Positive = profit, negative = loss.
- Interest and Other: positive = income, negative = expense.

## Combining Logic (Multi-Entity)

When producing a combined income statement:
- Entity A + Entity B + Adjustments = Combined, computed per line item.
- Every adjustment must link to a `conflict_id` from the conflict register.
- Intercompany revenue and corresponding COGS must be eliminated. The elimination must net to zero.
- Adjustments without a linked conflict_id are a halt-level error.

## Missing Data Rules

- If a line item category has no data, it must be reported as missing with an explicit flag.
- Missing line items are never zero-filled. Zero is a valid value (the entity had that category and it was zero). Missing means the data was not provided.
- If revenue data is entirely missing, the agent must halt — a P&L cannot be produced without revenue.

## Period Rules

- Every income statement must specify both `period_start` and `period_end`.
- Stub periods (less than 12 months) are valid. The agent must not annualize stub period data.
- The agent must state the period length in months in its output.

## Flags

- Missing policy document for a classification area: emit a warning flag "No policy provided for [area]."
- COGS ↔ OpEx ambiguity detected: emit a warning flag with the affected accounts and dollar impact.
- Revenue recognition method not determinable from provided data: emit a warning flag.
