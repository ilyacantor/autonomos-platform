# Farm — Financial Model Generation

## What Farm Does

Farm takes raw financial data and generates structured financial models. It reads financial inputs — general ledger detail, trial balances, charts of accounts — applies configuration rules, and produces structured output that flows into DCL as semantic triples.

Farm is the data generation engine. In a live deployment, Farm receives job manifests from AAM and connects to external systems to extract financial data. For demonstrations and development, Farm generates synthetic financial data from predefined configurations that model realistic enterprise scenarios.

## Configurations

Two canonical configurations exist:

- **Meridian Partners:** A $5B enterprise (the acquirer in the standard Convergence scenario). Full-scale financial model spanning 14 financial domains — revenue by type, cost structures, compensation, operating expenses, capital expenditures, balance sheet positions, and cash flows. Quarterly data across multiple periods.
- **Cascadia Process Solutions:** A $1B enterprise (the target in the standard Convergence scenario). Same 14 financial domains at a different scale, with different accounting treatments and cost structures that create realistic differences for integration analysis.

## What Farm Produces

Every piece of data Farm generates becomes a semantic triple in DCL: an entity identifier, a concept (using hierarchical naming like `compensation.base` or `revenue.consulting`), a property, a value, and a time period. Every triple carries provenance — which source system produced it, which source field it maps to, a confidence score, and the pipe and run that generated it.

Farm outputs cover the full financial picture: revenue breakdowns by service line, cost of goods sold by category, operating expenses by function, compensation structures, capital expenditure, depreciation schedules, balance sheet positions, and cash flow components.

## Ground Truth

Farm serves as the test oracle for the entire platform. Because Farm knows exactly what data it generated, it can verify accuracy across the pipeline. If DCL reports revenue of $1.25B for Q1, Farm can confirm whether that matches what was generated. This verification role is critical — it prevents the platform from silently returning wrong numbers.

## What Users Can Ask About

- "Where do the numbers come from?"
- "What financial data is available?"
- "What is the revenue breakdown by service line?"
- "How is compensation structured?"
- "What periods does the data cover?"
- "What is the difference between the acquirer and target financial profiles?"

## What Farm Does Not Do

Farm generates and verifies financial data. It does not discover systems — that is AOD. It does not map connections between systems — that is AAM. It does not resolve accounting conflicts between entities or build unified charts of accounts — that is Maestra working through the Convergence process. It does not answer user queries — that is NLQ. Farm produces the raw financial intelligence that every downstream module consumes.
