#!/usr/bin/env python3
"""
Seed script to populate KB with demo data.

Creates sample documents about:
- Platform documentation
- Runbooks
- Incident samples
- Best practices
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from uuid import UUID

from services.nlp_gateway.kb.repository import KBRepository
from services.nlp_gateway.kb.ingestion import get_ingestion_pipeline
from services.nlp_gateway.schemas.kb import IngestItem, IngestPolicy, IngestItemType
from services.nlp_gateway.schemas.common import Environment


DEMO_TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")

DEMO_DOCUMENTS = [
    {
        "title": "Platform Overview",
        "content": """AutonomOS Platform Overview
        
The AutonomOS platform provides automated operations for modern cloud infrastructure. It consists of several integrated modules:

FinOps Module: Automated cost optimization through cloud resource analysis. Identifies right-sizing opportunities, unused resources, and budget anomalies. Provides actionable recommendations with estimated savings. Supports AWS, Azure, and GCP.

RevOps Module: Revenue operations incident management. Tracks sync failures, data quality issues, and pipeline health across Salesforce, HubSpot, and other CRMs. Provides root cause analysis and automated remediation suggestions.

AOD (Adaptive Observability Dashboard): Real-time service dependency mapping and health monitoring. Tracks service-to-service communication, identifies bottlenecks, and provides alerting for degraded dependencies.

AAM (Adaptive API Mesh): Manages API connectors to SaaS platforms, databases, and file sources. Detects schema drift, handles authentication, and provides normalized data access across heterogeneous sources.

The platform uses AI agents to detect drift, propose repairs, and maintain system health autonomously.""",
        "tags": ["platform", "overview", "documentation"]
    },
    {
        "title": "FinOps Runbook",
        "content": """FinOps Cost Optimization Runbook

Step 1: Identify Cost Anomalies
- Run daily cost analysis across all cloud accounts
- Compare against historical baselines
- Flag spikes > 20% from rolling average

Step 2: Categorize Opportunities
- Right-sizing: Instances running at < 40% utilization
- Waste: Unattached volumes, stopped instances with EBS
- Reserved Instance gaps: On-demand usage > 3 months

Step 3: Generate Recommendations
- Calculate estimated savings per action
- Assess business impact and risk
- Prioritize by ROI (savings / implementation effort)

Step 4: Execute (with approval)
- Automated: Low-risk actions (< $100/month)
- Manual review: Medium-risk ($100-$1000/month)
- CFO approval: High-risk (> $1000/month)

Step 5: Monitor Results
- Track actual vs. projected savings
- Update cost models
- Feed learnings back to recommendation engine

Common Issues:
- False positives on dev/test resources: Add lifecycle tags
- Reserved Instance underutilization: Adjust commitment levels quarterly
- Multi-cloud attribution gaps: Ensure consistent tagging across providers""",
        "tags": ["finops", "runbook", "cost-optimization"]
    },
    {
        "title": "RevOps Incident Response",
        "content": """RevOps Incident Response Guide

Incident Classification:
- P1 (Critical): Revenue pipeline stopped, > 1000 records affected
- P2 (High): Partial sync failure, 100-1000 records affected
- P3 (Medium): Data quality issue, < 100 records affected
- P4 (Low): Performance degradation, no data loss

Common Incident Types:

1. OAuth Token Expiration
   Symptoms: 401 Unauthorized errors in connector logs
   Root Cause: Token rotation without refresh
   Resolution: Re-authenticate connector, update rotation schedule
   Prevention: Automated token refresh 24h before expiry

2. API Rate Limiting
   Symptoms: 429 Too Many Requests, sync stalls
   Root Cause: Bulk operations exceeding vendor limits
   Resolution: Implement exponential backoff, reduce batch size
   Prevention: Pre-flight rate limit checks, adaptive batching

3. Schema Drift
   Symptoms: Field mapping errors, null values in canonical model
   Root Cause: Vendor added/removed/renamed fields
   Resolution: Update field mappings, re-run historical sync
   Prevention: Weekly schema snapshots, diff alerts

4. Data Quality Issues
   Symptoms: Validation errors, duplicate records
   Root Cause: Source data inconsistencies, ETL bugs
   Resolution: Clean source data, fix transformation logic
   Prevention: Pre-ingestion validation, data quality scorecards

Escalation Path:
L1 (Ops) → L2 (Engineering) → L3 (Vendor TAM) → L4 (CTO)""",
        "tags": ["revops", "incident-response", "runbook"]
    },
    {
        "title": "AAM Connector Configuration",
        "content": """AAM Connector Configuration Guide

Supported Connector Types:
1. SaaS Connectors (OAuth-based)
   - Salesforce: Enterprise/Unlimited editions
   - HubSpot: Professional/Enterprise tiers
   - Zendesk: Plus/Enterprise plans

2. Database Connectors (Direct access)
   - PostgreSQL: v12+
   - MongoDB: v4.4+
   - Snowflake: Enterprise edition

3. File Connectors (Batch ingestion)
   - S3: CSV/JSON/Parquet
   - Azure Blob Storage: CSV/JSON
   - Local filesystem: CSV/JSON

Configuration Steps:

1. Create Connector
   - Name: Unique identifier (e.g., "salesforce-prod")
   - Type: Select from supported types
   - Environment: dev/stage/prod

2. Authenticate
   - SaaS: OAuth flow with scopes (read, write, admin)
   - Database: Connection string with credentials
   - File: Bucket/path with access keys

3. Map Fields
   - Source schema → Canonical model
   - Define transformations (rename, coerce, derive)
   - Set confidence scores (0.0-1.0)

4. Enable Drift Detection
   - Snapshot frequency: Hourly/Daily/Weekly
   - Drift threshold: Field count change > 10%
   - Alert channels: Email, Slack, PagerDuty

5. Test & Activate
   - Dry run: Preview mapped data
   - Validation: Check data quality
   - Go live: Enable production sync

Troubleshooting:
- Connection timeouts: Check firewall rules, VPN access
- Authentication failures: Verify credentials, refresh tokens
- Schema drift alerts: Review vendor changelog, update mappings""",
        "tags": ["aam", "connectors", "configuration", "documentation"]
    },
    {
        "title": "AOD Service Dependencies",
        "content": """AOD Service Dependency Mapping

The AOD module automatically discovers and maps service dependencies through:

1. Active Probing
   - HTTP health checks every 30s
   - gRPC metadata inspection
   - Database connection pooling metrics

2. Passive Observability
   - Distributed tracing (OpenTelemetry)
   - Service mesh telemetry (Istio/Linkerd)
   - Log aggregation (ELK/Splunk)

3. Configuration Analysis
   - Kubernetes service definitions
   - Environment variable injection
   - Config maps and secrets

Dependency Types:
- Synchronous: HTTP, gRPC, GraphQL
- Asynchronous: Message queues (Kafka, RabbitMQ)
- Data stores: Databases, caches, object storage
- External services: Third-party APIs

Health Status:
- Operational: All checks passing, latency < SLO
- Degraded: Some checks failing, latency > SLO
- Down: All checks failing, error rate > 50%

Example Dependency Chain:
Frontend → API Gateway → Auth Service → User DB
                      → Checkout Service → Payment Gateway
                                        → Inventory Service
                                        → Order DB

When a service goes down, AOD:
1. Identifies blast radius (upstream/downstream)
2. Calculates business impact (affected users, revenue)
3. Suggests mitigation (failover, circuit breaker, degraded mode)
4. Alerts on-call team with context""",
        "tags": ["aod", "observability", "dependencies", "documentation"]
    },
    {
        "title": "KB Search and Ingestion",
        "content": """Knowledge Base Search and Ingestion

The NLP Gateway KB uses hybrid retrieval combining:

1. BM25 (Keyword Search)
   - PostgreSQL full-text search (tsvector)
   - Trigram similarity (pg_trgm) for fuzzy matching
   - Weighted by term frequency and document length

2. Vector Search (Semantic)
   - Sentence-BERT embeddings (384-dim)
   - pgvector for approximate nearest neighbor
   - Cosine similarity ranking

3. Fusion
   - Reciprocal Rank Fusion (RRF)
   - BM25 weight: 0.3, Vector weight: 0.7
   - Combines top-k results from each method

Ingestion Pipeline:

1. Chunking
   - Auto: Adaptive based on paragraph boundaries
   - Fixed: Overlapping windows (1200 tokens, 200 overlap)
   - Preserves section headings for citations

2. Embedding
   - Model: all-MiniLM-L6-v2 (sentence-transformers)
   - Batch size: 32 chunks
   - GPU acceleration if available

3. PII Redaction
   - Microsoft Presidio analyzer
   - Detects: emails, phone numbers, SSNs, credit cards
   - Redacts: Replaces with <REDACTED> tokens
   - Stores both original and redacted text

4. Storage
   - Documents: Metadata + tags
   - Chunks: Text + embedding + section
   - Indexes: tsvector, trigram, vector (ivfflat)

Performance Targets:
- Indexing: 100 chunks/sec
- Search latency: p95 < 1.5s
- Embedding: 50 chunks/sec on CPU""",
        "tags": ["kb", "search", "ingestion", "nlp", "documentation"]
    }
]


async def seed_kb():
    """Seed the knowledge base with demo documents."""
    DATABASE_URL = os.getenv("DATABASE_URL", "")
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
    elif DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    pipeline = get_ingestion_pipeline()
    
    async with async_session_maker() as session:
        repository = KBRepository(session)
        
        print(f"Seeding KB with {len(DEMO_DOCUMENTS)} documents...")
        
        for doc_data in DEMO_DOCUMENTS:
            print(f"\nProcessing: {doc_data['title']}")
            
            item = IngestItem(
                type=IngestItemType.TEXT,
                location=doc_data["content"],
                tags=doc_data["tags"]
            )
            
            policy = IngestPolicy(
                chunk="auto",
                max_chunk_tokens=1200,
                redact_pii=True
            )
            
            processed = pipeline.process_item(item, policy)
            
            if "error" in processed:
                print(f"  ❌ Error: {processed['error']}")
                continue
            
            document = await repository.create_document(
                tenant_id=DEMO_TENANT_ID,
                env=Environment.DEV,
                doc_id=processed["doc_id"],
                title=doc_data["title"],
                source_type="text",
                source_location="seed_script",
                tags=doc_data["tags"],
                metadata=processed["metadata"]
            )
            
            for chunk_data in processed["chunks"]:
                await repository.create_chunk(
                    document_id=document.id,
                    tenant_id=DEMO_TENANT_ID,
                    env=Environment.DEV,
                    chunk_index=chunk_data["index"],
                    section=chunk_data["section"],
                    text=chunk_data["text"],
                    text_redacted=chunk_data.get("text_redacted"),
                    embedding=chunk_data["embedding"],
                    tokens=chunk_data["tokens"],
                    metadata=chunk_data["metadata"]
                )
            
            await repository.update_document_status(processed["doc_id"], "completed")
            
            print(f"  ✅ Ingested: {len(processed['chunks'])} chunks")
    
    await engine.dispose()
    print("\n✅ KB seeding completed!")


if __name__ == "__main__":
    asyncio.run(seed_kb())
