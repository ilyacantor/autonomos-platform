# AAM — Application Architecture Mapping

## What AAM Does

AAM is the second step in the AOS pipeline. After AOD discovers what systems exist, AAM maps how those systems connect to each other — what data flows between them, through which integration paths, and with what reliability.

## What "Mapping" Means

Mapping is the process of understanding the wiring of the customer's technology stack. AAM takes the discovery results from AOD (the inventory of systems and connection hints) and builds a detailed picture of data movement: which system sends data to which, what format it uses, what integration fabric carries the traffic, and whether the connection is healthy or degraded.

AAM works at the fabric plane level — it connects to the integration backbone (API gateways, event buses, iPaaS platforms, data warehouses) rather than to individual applications. This means AAM understands the paths data takes, not just the endpoints.

## Key Concepts

- **Pipes:** A pipe is a defined data path between two systems. AAM creates pipe definitions (called DeclaredPipes) that describe what data moves, how it moves, and what schema it carries. Pipes have identity keys, transport types (API, event stream, table, file), and modality (how they are accessed).
- **Connection candidates:** When AOD hands off discovered systems with connection hints, AAM triages them — accepting, deferring, or matching them to existing pipe definitions.
- **Drift detection:** After mapping is established, AAM monitors for changes. Schema drift (the data structure changed), freshness drift (data stopped flowing), and connection drift (the integration path broke) are all tracked. When drift is detected, AAM can trigger self-healing — reconnecting, restarting consumers, or logging the issue for operator review.
- **Governance at the pipe level:** AAM enforces authentication policies, PII redaction at the edge (before data enters the semantic layer), and rate limiting on data collection.

## What AAM Produces

AAM writes pipe definitions and connection maps to DCL as structured data. Each pipe carries metadata: source system, target system, transport kind, schema hash, health status, last successful run. The full set of pipe definitions gives a complete picture of how the customer's systems are wired together.

AAM also dispatches work — when a pipe is defined and ready, AAM constructs job manifests and sends them to Farm for data extraction.

## What Users Can Ask About

- "How are our systems connected?"
- "What data flows exist between our ERP and CRM?"
- "What has been mapped vs. what is still unmapped?"
- "Are there any broken or degraded connections?"
- "What integration patterns does our environment use?"
- "How many active data pipes exist?"

## What AAM Does Not Do

AAM maps connections and manages data pipes. It does not discover systems — that is AOD. It does not interpret or value the data financially — that is Farm. It does not build semantic meaning or resolve conflicts between entities — that is DCL and Convergence. AAM's job is complete when every discovered system has its connections mapped, monitored, and available for data extraction.
