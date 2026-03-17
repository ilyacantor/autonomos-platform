# NLQ — Natural Language Query

## What NLQ Does

NLQ is the natural language query layer. It lets users type questions in plain English and get answers grounded in real data from DCL's semantic triple store. The answers come with provenance — every number traces back to a source system, a time period, and a confidence score.

## How It Works

A user types a question. NLQ parses the question to understand what is being asked: which metric, which dimensions (time period, department, entity, service line), what type of answer is expected (a single number, a comparison, a trend, a breakdown, a ranking).

NLQ classifies every question into one of five intent types:

- **Point:** a single fact ("What was Q3 revenue?").
- **Comparison:** two or more values side by side ("How does consulting revenue compare to managed services?").
- **Trend:** change over time ("What is the revenue trend over the last 8 quarters?").
- **Aggregation:** a rolled-up total ("What is total compensation across all departments?").
- **Breakdown:** a whole decomposed into parts ("Break down operating expenses by function").

After parsing, NLQ retrieves the relevant data from DCL. The data comes as structured facts with provenance. NLQ formats the answer — as text, as a table, as a chart (line, bar, area, pie, waterfall), or as a dashboard with multiple widgets — depending on what best fits the question.

## What Kinds of Questions It Handles

Anything that has data in DCL. Revenue breakdowns, compensation structures, headcount, cost analysis, financial comparisons between entities, conflict summaries, trend analysis. If the data exists as triples in the store, NLQ can surface it.

NLQ also handles ambiguity. If a question is unclear — "show me costs" without specifying which costs, which entity, which period — NLQ detects the ambiguity and asks a clarifying question rather than guessing. Synonyms are normalized: "AR" maps to accounts receivable, "comp" maps to compensation, "headcount" maps to employee count.

## Confidence and Provenance

Every answer carries a confidence score between 0 and 1, based on data quality, freshness, and how well the question maps to available data. The source of every number is visible — which system produced it, when, and through which pipeline. Users can always ask "where did this number come from?" and get a traceable answer.

## Relationship to Maestra

Maestra sits above NLQ as the conversational interface to the entire platform. NLQ is the data retrieval engine. When a user asks Maestra a data question, the system retrieves relevant data from DCL, and Maestra explains it in context — adding judgment, explanation, and workflow awareness on top of what the data says. NLQ provides the facts; Maestra provides the understanding.

## What Users Can Ask About

Users can ask freely. There are preset suggestions to help discover what data is available, but the query surface is open-ended. Examples:

- "What is total revenue for Q3?"
- "How does the acquirer's compensation structure compare to the target's?"
- "Show me the top 10 customers by revenue."
- "What are the biggest COFA conflicts?"
- "Break down operating expenses by department."
- "What is the trend in consulting revenue over the last two years?"

## What NLQ Does Not Do

NLQ retrieves and presents data. It does not create or modify data — that happens upstream in the pipeline (Farm generates, DCL stores). It does not make decisions or resolve conflicts — that requires human judgment, surfaced through Maestra. It does not discover systems or map connections — those are AOD and AAM. NLQ is the read-only query surface for everything the platform knows.
