# AOD — Automated Operations Discovery

## What AOD Does

AOD is the first step in the AOS pipeline. It scans a customer's technology environment and produces a structured inventory of every system, data source, and integration point it finds. ERPs, CRMs, HR platforms, billing systems, identity providers, data warehouses, custom applications — AOD catalogues them all.

## How Discovery Works

AOD performs automated scanning across the customer's environment. It examines network traffic patterns, identity provider configurations, CMDB records, and other observable signals to build a picture of what technology exists and how it is governed.

For each discovered system, AOD determines:

- **System identity:** name, type, vendor, version where observable.
- **Governance status:** whether the system is governed (known to IT, properly managed), shadow (in use but not formally managed), or zombie (provisioned but inactive or abandoned).
- **System of Record (SOR) status:** which system is the authoritative source for a given data domain. AOD scores SOR confidence based on observable evidence — data freshness, user activity, integration density.
- **Connection hints:** signals about how systems talk to each other — which integration fabric they use (API gateways, event buses, iPaaS platforms, direct database connections). These hints become input for the next pipeline stage.

## What AOD Produces

AOD writes its findings as structured data into DCL, the semantic context layer. Each discovered system becomes a set of facts: system name, system type, governance classification, connection status, SOR score, observed integration patterns. Every fact carries provenance — when it was discovered, what evidence supported the classification, what confidence level applies.

The discovery output also includes findings and issues: CMDB gaps (systems in use but missing from the asset register), identity gaps (systems without proper SSO integration), data conflicts (multiple systems claiming SOR status for the same domain), and finance gaps (systems with cost implications that are not tracked).

## What Users Can Ask About

- "What systems did you find in our environment?"
- "How many systems are governed vs. shadow vs. zombie?"
- "What is the system of record for customer data?"
- "Which systems are connected and which are standalone?"
- "What gaps or issues did discovery find?"
- "What types of integration patterns exist across our stack?"

## What AOD Does Not Do

AOD discovers and classifies. It does not connect to systems or map data flows between them — that is AAM's responsibility. It does not interpret financial data or generate financial models — that is Farm. It does not resolve conflicts between entities or build semantic meaning from the data — that is DCL and Maestra. AOD's job is complete when the customer has a comprehensive, classified inventory of their technology landscape.
