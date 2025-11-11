import { ChevronDown, ChevronUp } from 'lucide-react';
import { useState, useEffect } from 'react';

interface FAQItem {
  id: string;
  question: string;
  answer: string | JSX.Element;
  category: string;
  searchableText?: string; // Plain text version for searching JSX answers
}

export default function FAQPage() {
  const [openIndex, setOpenIndex] = useState<number | null>(0);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');

  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.slice(1);
      if (hash) {
        const index = faqItems.findIndex(item => item.id === hash);
        if (index !== -1) {
          // Reset filter to 'all' to show the item
          const item = faqItems[index];
          setSelectedCategory(item.category);
          setOpenIndex(index);
          setTimeout(() => {
            document.getElementById(hash)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
          }, 100);
        }
      }
    };

    // Handle initial hash on mount
    handleHashChange();

    // Listen for hash changes
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const toggleQuestion = (index: number) => {
    setOpenIndex(openIndex === index ? null : index);
  };

  const faqItems: FAQItem[] = [
    // Platform Overview
    {
      id: "what-is-autonomos",
      category: "Platform Overview",
      question: "What is AutonomOS?",
      searchableText: "AutonomOS is an AI-native enterprise-grade platform that turns your scattered company data into action. It autonomously connects to all your apps, databases, and files, learning how they fit together to create a single unified enterprise ontology. This allows our specialized AI agents to reason, act, and get work done. The Problem: Most companies are data-rich but action-poor. They can't bridge the Insight-to-Action Gap between their data and their business goals, leading to inefficiency and inaction. Our Solution: AutonomOS bridges this gap. It not only unifies your data but empowers pre-built AI agents to execute complex workflows. You remain in control with Human-in-the-Loop HITL guardrails. We deliver a complete secure and scalable solution combining technology with domain expertise to ensure you get results not just another proof-of-concept POC.",
      answer: (
        <div className="space-y-4">
          <p className="text-gray-300">
            AutonomOS is an AI-native, <strong className="text-white">enterprise-grade</strong> platform that turns your scattered company data into action.
          </p>
          <p className="text-gray-300">
            It autonomously connects to all your apps, databases, and files, learning how they fit together to create a single, unified enterprise <strong className="text-white">ontology</strong>. This allows our specialized AI agents to reason, act, and get work done.
          </p>
          
          <div className="mt-6">
            <h4 className="text-[#0BCAD9] font-medium text-lg mb-3">The Problem</h4>
            <p className="text-gray-300">
              Most companies are data-rich but action-poor. They can't bridge the "Insight-to-Action Gap" between their data and their business goals, leading to inefficiency and inaction.
            </p>
          </div>
          
          <div className="mt-6">
            <h4 className="text-[#0BCAD9] font-medium text-lg mb-3">Our Solution</h4>
            <p className="text-gray-300">
              AutonomOS bridges this gap. It not only unifies your data but empowers pre-built AI agents to execute complex workflows. You remain in control with Human-in-the-Loop (HITL) guardrails. We deliver a complete, <strong className="text-white">secure</strong>, and scalable solution—combining technology with the domain expertise to ensure you get results, not just another proof-of-concept (POC).
            </p>
          </div>
        </div>
      )
    },
    {
      id: "live-status-badges",
      category: "Platform Overview",
      question: "What do the Live Status Badges mean?",
      answer: "Live Status Badges (green pulsing dots) indicate that a component is connected to real backend data sources and displaying actual live information. Components without these badges are demonstration/mock data for preview purposes. Hover over any badge to see details about the data source."
    },

    // Control Center
    {
      id: "control-center-overview",
      category: "Control Center",
      question: "What is the AOS Control Center?",
      answer: "The Control Center is your main dashboard providing a comprehensive overview of your AutonomOS platform. It displays key performance indicators (KPIs), system health metrics, active connections, and real-time insights into your data orchestration activities."
    },
    {
      id: "total-connections",
      category: "Control Center",
      question: "Total Connections - What does this show?",
      answer: "This metric displays the total number of data source connections configured in your platform. Active connections are those currently synchronized and operational. This includes connections to databases, APIs, cloud services, and file sources managed through the Adaptive API Mesh (AAM)."
    },
    {
      id: "active-agents",
      category: "Control Center",
      question: "Active Agents - What are these?",
      answer: "Shows the number of AI agents currently running and processing tasks. These include FinOps agents for financial operations, RevOps agents for revenue operations, and custom agents orchestrated through the Agentic Orchestration Architecture (AOA)."
    },
    {
      id: "data-sources",
      category: "Control Center",
      question: "Data Sources - What counts as a data source?",
      answer: "Any external system providing data to AutonomOS: databases (PostgreSQL, MongoDB, Supabase), SaaS platforms (Salesforce, Slack), file storage (CSV, JSON, Excel), or APIs. Each data source is managed by a dedicated connector with schema monitoring and auto-repair capabilities."
    },

    // Discover (AOD)
    {
      id: "aod-overview",
      category: "Discover (AOD)",
      question: "What is AOS Discover (AOD)?",
      answer: "AOS Discover is an external microservice that performs autonomous asset discovery across your infrastructure. It identifies databases, APIs, file systems, and cloud services, providing a comprehensive map of your data landscape. The dashboard shows real-time discovery metrics and newly identified assets."
    },
    {
      id: "aod-dashboard",
      category: "Discover (AOD)",
      question: "How do I read the AOD Dashboard?",
      answer: "The AOD Dashboard displays: (1) Total Assets Discovered - all identified data sources; (2) Active Scans - currently running discovery processes; (3) New This Week - recently identified assets; (4) Coverage Score - percentage of your infrastructure mapped. The asset list shows details including type, location, and last scan time."
    },
    {
      id: "aod-integration",
      category: "Discover (AOD)",
      question: "How does AOD integrate with AutonomOS?",
      answer: "AOD feeds discovered assets into the Adaptive API Mesh (AAM) for auto-onboarding. When AOD identifies a new data source, AAM can automatically create a connector in Safe Mode, allowing you to review and approve the connection before it begins processing data."
    },

    // Connections / AAM
    {
      id: "aam-overview",
      category: "Connections (AAM)",
      question: "What is the Adaptive API Mesh (AAM)?",
      answer: "The Adaptive API Mesh is an intelligent connectivity layer that uses AI to automatically build, maintain, and repair connections between disparate enterprise systems. It provides self-healing integration capabilities that adapt to changes in your data sources and APIs, ensuring your workflows remain resilient and operational without manual intervention."
    },
    {
      id: "aam-connectors",
      category: "Connections (AAM)",
      question: "AAM Connectors - What are they?",
      answer: "Connectors are production-ready integrations for specific data sources (Salesforce, Supabase, MongoDB, FileSource, etc.). Each connector handles authentication, schema detection, data extraction, and canonical event normalization. They include built-in drift detection and auto-repair capabilities."
    },
    {
      id: "aam-mappings",
      category: "Connections (AAM)",
      question: "Mappings Metric - How does this work?",
      answer: "Tracks field-level mappings between source data and your enterprise ontology. Shows total mappings, percentage resolved through Autofix (AI-powered automatic resolution), and percentage requiring HITL (Human-in-the-Loop) review. High autofix percentage indicates strong AI confidence in mapping accuracy."
    },
    {
      id: "aam-drift",
      category: "Connections (AAM)",
      question: "Drift Events - What triggers these?",
      answer: "Drift events occur when a data source schema changes (new fields, removed fields, type changes). AAM uses schema fingerprinting to detect drift automatically. The metric shows total drift events in the last 24 hours, broken down by source. Each event triggers the auto-repair agent to resolve mapping conflicts."
    },
    {
      id: "aam-rag",
      category: "Connections (AAM)",
      question: "RAG Suggestions - What is this?",
      answer: "RAG (Retrieval-Augmented Generation) Suggestions are AI-powered recommendations for resolving schema drift and mapping conflicts. The system uses semantic matching and historical patterns to suggest field mappings. Shows pending suggestions, accepted suggestions (applied to production), and rejected suggestions."
    },
    {
      id: "aam-confidence",
      category: "Connections (AAM)",
      question: "Repair Confidence - How is this calculated?",
      answer: "A percentage score indicating AI confidence in auto-repair decisions. Calculated from semantic similarity, historical pattern matching, and validation test results. Higher confidence (>80%) allows automatic application; lower confidence requires human review through HITL queue. Test Pass Rate shows how many repairs pass validation tests."
    },
    {
      id: "aam-safe-mode",
      category: "Connections (AAM)",
      question: "Safe Mode - What does this do?",
      answer: "Safe Mode is a security guardrail for new connections. When enabled, newly onboarded data sources operate in read-only mode with strict validation. No data is automatically processed until you explicitly approve the connection configuration. Designed to meet 90% day-one coverage SLO while maintaining security."
    },
    {
      id: "aam-auto-onboarding",
      category: "Connections (AAM)",
      question: "Auto-Onboarding - How does it work?",
      answer: "AAM accepts ConnectionIntent payloads (from AOD or manual input) and automatically creates connectors for new data sources. Process: (1) Receive connection details, (2) Create connector in Safe Mode, (3) Perform schema discovery, (4) Generate initial mappings, (5) Queue for human approval. Achieves 90% coverage SLO for supported source types."
    },
    {
      id: "aam-namespace",
      category: "Connections (AAM)",
      question: "Namespace Isolation - Autonomy vs Demo",
      answer: "AAM enforces strict namespace isolation. 'autonomy' namespace contains production connectors with live data. 'demo' namespace contains demonstration connectors for testing. The two namespaces never interact, ensuring demo activities don't affect production data. Connectors inherit namespace from tenant configuration."
    },

    // Ontology / DCL
    {
      id: "dcl-overview",
      category: "Ontology (DCL)",
      question: "What is the Data Connectivity Layer (DCL)?",
      answer: "The DCL is the core data intelligence engine that autonomously maps disparate data sets into a Unified Enterprise Ontology. It uses AI to understand your data semantics, create contextual relationships, and generate AI-ready data streams. The DCL feeds a Contextual RAG engine that continuously learns from your data patterns, enabling intelligent agents to make informed decisions."
    },
    {
      id: "dcl-graph",
      category: "Ontology (DCL)",
      question: "Entity Graph - How do I read this?",
      answer: "The Entity Graph visualizes relationships between your data entities. Nodes represent entities (customers, products, transactions, etc.), edges represent relationships. Node size indicates data volume, edge thickness shows relationship strength. Color coding indicates entity type. Click nodes to see details; hover over edges to view relationship metadata."
    },
    {
      id: "dcl-sankey",
      category: "Ontology (DCL)",
      question: "Sankey Diagram - What does this show?",
      answer: "The Sankey diagram displays data flow through your platform. Left side shows source connectors, middle shows DCL processing layers, right shows output destinations (agents, views, APIs). Flow width represents data volume. Use this to understand how data moves from sources through transformations to final consumers."
    },
    {
      id: "dcl-mappings",
      category: "Ontology (DCL)",
      question: "Entity Mappings - How are these created?",
      answer: "DCL uses AI (Gemini/OpenAI) to analyze source schemas and map them to your enterprise ontology. Process: (1) Extract schema from source, (2) Semantic analysis of field names/types, (3) Match to existing entities, (4) Generate mapping with confidence score, (5) Human review if confidence < 80%. Mappings are versioned and auditable."
    },
    {
      id: "dcl-views",
      category: "Ontology (DCL)",
      question: "Materialized Views - What are these?",
      answer: "DCL creates materialized views in DuckDB for fast query access to unified data. These are pre-computed, optimized SQL views combining data from multiple sources according to your ontology. Views update incrementally as source data changes. Used by agents for low-latency data access without hitting source systems."
    },
    {
      id: "dcl-telemetry",
      category: "Ontology (DCL)",
      question: "LLM Telemetry - What is tracked?",
      answer: "Tracks LLM usage across DCL operations: total API calls, tokens consumed (input/output), cost per operation, model used (Gemini, OpenAI, etc.). Stored in Redis for real-time monitoring. Use this to understand AI costs and optimize model selection for different tasks (schema analysis vs. entity resolution)."
    },

    // Orchestration / AOA
    {
      id: "aoa-overview",
      category: "Orchestration (AOA)",
      question: "What is Agentic Orchestration Architecture (AOA)?",
      answer: "AOA is the high-level orchestration layer that manages all agent operations, both internal AutonomOS agents and third-party agents. It coordinates task distribution, monitors agent performance, handles inter-agent communication, and provides unified governance. AOA ensures agents work together efficiently while maintaining security and compliance boundaries."
    },
    {
      id: "aoa-status",
      category: "Orchestration (AOA)",
      question: "AOA Status Card - What do the metrics mean?",
      answer: "Shows real-time orchestration health: (1) Active Tasks - currently executing agent tasks, (2) Success Rate - percentage of successfully completed tasks, (3) Avg Response Time - average task completion time, (4) Queue Depth - tasks waiting for execution. Green status indicates healthy operation; yellow/red indicates bottlenecks or failures."
    },
    {
      id: "xao-metrics",
      category: "Orchestration (AOA)",
      question: "xAO Metrics - What is Cross-Agentic Orchestration?",
      answer: "xAO (Cross-Agentic Orchestration) orchestrates all agents—both internal AutonomOS agents and third-party agents—providing unified coordination and governance. Metrics include: Cross Discovery (API endpoints across agents), Federation Health (synchronization status), Trust Score (reliability and data fidelity), SLA Compliance, Security Posture, and Interoperability Score."
    },
    {
      id: "agent-performance",
      category: "Orchestration (AOA)",
      question: "Agent Performance Monitor - How to use this?",
      answer: "Displays performance metrics for each active agent: task completion rate, average execution time, error rate, resource utilization. Use this to identify underperforming agents, optimize task distribution, and monitor SLA compliance. Click on an agent to see detailed execution logs and task history."
    },
    {
      id: "aoa-functions",
      category: "Orchestration (AOA)",
      question: "AOA Functions Panel - What functions are available?",
      answer: "Provides control functions for orchestration: (1) Task Queue Management - view and prioritize pending tasks, (2) Agent Deployment - activate/deactivate agents, (3) Resource Allocation - adjust compute resources per agent, (4) Error Recovery - retry failed tasks, (5) Audit Logs - view orchestration history."
    },

    // Agents
    {
      id: "agents-overview",
      category: "Agents",
      question: "What are Prebuilt Domain Agents?",
      answer: "Prebuilt Domain Agents are productized domain expertise packages designed for specific business functions like FinOps and RevOps. These agents leverage the AI-prepared data fabric to autonomously execute complex, end-to-end business workflows. They use advanced LLM capabilities (supporting multiple providers like Gemini and OpenAI) to reason about your data, learn from patterns, and take intelligent actions."
    },
    {
      id: "finops-agent",
      category: "Agents",
      question: "FinOps Agent - What does it do?",
      answer: "The FinOps (Financial Operations) Agent optimizes cloud spending and financial operations. Capabilities: (1) Cost Analysis - identifies spending patterns and anomalies, (2) Budget Optimization - recommends resource allocation, (3) Waste Detection - finds unused resources, (4) Forecasting - predicts future costs, (5) Automated Actions - rightsizes instances, removes unused resources (with approval)."
    },
    {
      id: "revops-agent",
      category: "Agents",
      question: "RevOps Agent - What does it do?",
      answer: "The RevOps (Revenue Operations) Agent optimizes sales pipeline and revenue workflows. Capabilities: (1) Pipeline Analysis - identifies bottlenecks and conversion rates, (2) Lead Scoring - prioritizes high-value opportunities, (3) Forecasting - predicts revenue outcomes, (4) Process Automation - automates follow-ups and updates, (5) Performance Insights - surfaces trends and recommendations."
    },
    {
      id: "custom-agents",
      category: "Agents",
      question: "Can I build custom agents?",
      answer: "Yes, while we provide Prebuilt Domain Agents for common use cases, the platform supports custom agent deployment. You can leverage our AI-prepared data fabric and orchestration capabilities to build agents tailored to your specific business needs. The LLM service abstraction allows you to choose the best model for each task. Contact support for custom agent development."
    },

    // NLP Gateway
    {
      id: "nlp-gateway-overview",
      category: "NLP Gateway",
      question: "What is the NLP Gateway?",
      answer: "The NLP Gateway is a natural language processing service providing conversational access to platform features. It translates natural language queries into system actions, allowing users to interact with AutonomOS using plain English instead of technical interfaces. Supports queries about FinOps, RevOps, AAM status, DCL mappings, and more."
    },
    {
      id: "nlp-no-auth",
      category: "NLP Gateway",
      question: "NLP Gateway Authentication - Is it required?",
      answer: "No, the NLP Gateway operates without authentication for this demo. In production deployments, you can enable JWT authentication for secure access. The demo mode allows anyone to query non-sensitive platform information for evaluation purposes."
    },
    {
      id: "nlp-rag",
      category: "NLP Gateway",
      question: "NLP RAG Knowledge Base - How does this work?",
      answer: "The NLP Gateway uses a tenant-scoped RAG (Retrieval-Augmented Generation) knowledge base built with PostgreSQL + pgvector. It employs hybrid retrieval combining BM25 (keyword search) and vector embeddings with Reciprocal Rank Fusion for optimal results. The knowledge base continuously learns from platform data and user interactions."
    },
    {
      id: "nlp-pii",
      category: "NLP Gateway",
      question: "PII Redaction - How is sensitive data protected?",
      answer: "The NLP Gateway automatically redacts Personally Identifiable Information (PII) from responses. Detected PII includes: email addresses, phone numbers, SSNs, credit card numbers, and custom patterns. Redaction occurs before LLM processing and in responses. Audit logs track all PII detection events for compliance reporting."
    },
    {
      id: "nlp-queries",
      category: "NLP Gateway",
      question: "What can I ask the NLP Gateway?",
      searchableText: "Example queries supported: What's my total cloud spending this month FinOps, Show me top revenue opportunities RevOps, Which connectors have drift events AAM, How many entities are mapped in DCL Ontology, What agents are currently running Orchestration, Summarize my platform health Overview",
      answer: (
        <div className="space-y-2">
          <p className="text-gray-300">Example queries supported:</p>
          <ul className="list-disc list-inside text-gray-300 space-y-1">
            <li>"What's my total cloud spending this month?" (FinOps)</li>
            <li>"Show me top revenue opportunities" (RevOps)</li>
            <li>"Which connectors have drift events?" (AAM)</li>
            <li>"How many entities are mapped in DCL?" (Ontology)</li>
            <li>"What agents are currently running?" (Orchestration)</li>
            <li>"Summarize my platform health" (Overview)</li>
          </ul>
        </div>
      )
    },

    // Security & Compliance
    {
      id: "security-overview",
      category: "Security",
      question: "What are your security standards?",
      searchableText: "Security Compliance Roadmap. Phase 0 Secure Core Today Implemented: Zero Data Retention Model ephemeral in-memory processing, Robust Multi-Tenant Isolation DB-level tenant-scoped queries, Zero-Trust Infrastructure VPC TLS 1.3 Secrets Management, Secure API Software Lifecycle Pydantic validation CI/CD scans, Immutable Audit Trail metadata-only logging. Phase 1 Enterprise Readiness 0-6 Months: SOC 2 Type I Certification fast-tracked, 3rd-Party Penetration Test, Single Sign-On SSO Okta Azure AD, Private Connectivity AWS PrivateLink, Public Trust Portal Incident Response Plan. Phase 2 Continuous Compliance 6-18 Months: SOC 2 Type II ISO 27001, Bring Your Own Key BYOK, Customer-Managed RBAC, Regional Data Residency Controls, AI-Driven Threat Detection",
      answer: (
        <div className="space-y-6">
          <div>
            <h4 className="text-[#0BCAD9] font-medium text-lg mb-4">Security & Compliance Roadmap</h4>
            <div className="overflow-x-auto">
              <table className="w-full border-collapse">
                <thead>
                  <tr className="bg-[#0D2F3F]">
                    <th className="border border-[#1A4D5E] px-4 py-3 text-left text-white font-medium">
                      Phase 0: Secure Core (Today)
                    </th>
                    <th className="border border-[#1A4D5E] px-4 py-3 text-left text-white font-medium">
                      Phase 1: Enterprise Readiness (0–6 Months)
                    </th>
                    <th className="border border-[#1A4D5E] px-4 py-3 text-left text-white font-medium">
                      Phase 2: Continuous Compliance (6–18 Months)
                    </th>
                  </tr>
                  <tr className="bg-[#0A2540]">
                    <th className="border border-[#1A4D5E] px-4 py-2 text-left text-[#0BCAD9] font-normal text-sm">
                      Status: Implemented
                    </th>
                    <th className="border border-[#1A4D5E] px-4 py-2 text-left text-[#0BCAD9] font-normal text-sm">
                      Goal: Pass Enterprise Security Assessments
                    </th>
                    <th className="border border-[#1A4D5E] px-4 py-2 text-left text-[#0BCAD9] font-normal text-sm">
                      Goal: Operate with Automated Trust at Scale
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td className="border border-[#1A4D5E] px-4 py-3 text-gray-300 align-top">
                      <div className="flex items-start gap-2">
                        <span className="text-green-400">✓</span>
                        <span><strong className="text-white">Zero Data Retention Model</strong> (Ephemeral in-memory processing)</span>
                      </div>
                    </td>
                    <td className="border border-[#1A4D5E] px-4 py-3 text-gray-300 align-top">
                      <div className="flex items-start gap-2">
                        <span className="text-gray-500">🔲</span>
                        <span><strong className="text-white">SOC 2 Type I Certification</strong> (Fast-tracked)</span>
                      </div>
                    </td>
                    <td className="border border-[#1A4D5E] px-4 py-3 text-gray-300 align-top">
                      <div className="flex items-start gap-2">
                        <span className="text-gray-500">🔲</span>
                        <span><strong className="text-white">SOC 2 Type II + ISO 27001</strong></span>
                      </div>
                    </td>
                  </tr>
                  <tr>
                    <td className="border border-[#1A4D5E] px-4 py-3 text-gray-300 align-top">
                      <div className="flex items-start gap-2">
                        <span className="text-green-400">✓</span>
                        <span><strong className="text-white">Robust Multi-Tenant Isolation</strong> (DB-level, tenant-scoped queries)</span>
                      </div>
                    </td>
                    <td className="border border-[#1A4D5E] px-4 py-3 text-gray-300 align-top">
                      <div className="flex items-start gap-2">
                        <span className="text-gray-500">🔲</span>
                        <span><strong className="text-white">3rd-Party Penetration Test</strong></span>
                      </div>
                    </td>
                    <td className="border border-[#1A4D5E] px-4 py-3 text-gray-300 align-top">
                      <div className="flex items-start gap-2">
                        <span className="text-gray-500">🔲</span>
                        <span><strong className="text-white">Bring Your Own Key (BYOK)</strong></span>
                      </div>
                    </td>
                  </tr>
                  <tr>
                    <td className="border border-[#1A4D5E] px-4 py-3 text-gray-300 align-top">
                      <div className="flex items-start gap-2">
                        <span className="text-green-400">✓</span>
                        <span><strong className="text-white">Zero-Trust Infrastructure</strong> (VPC, TLS 1.3, Secrets Mgmt)</span>
                      </div>
                    </td>
                    <td className="border border-[#1A4D5E] px-4 py-3 text-gray-300 align-top">
                      <div className="flex items-start gap-2">
                        <span className="text-gray-500">🔲</span>
                        <span><strong className="text-white">Single Sign-On (SSO)</strong> (Okta, Azure AD)</span>
                      </div>
                    </td>
                    <td className="border border-[#1A4D5E] px-4 py-3 text-gray-300 align-top">
                      <div className="flex items-start gap-2">
                        <span className="text-gray-500">🔲</span>
                        <span><strong className="text-white">Customer-Managed RBAC</strong></span>
                      </div>
                    </td>
                  </tr>
                  <tr>
                    <td className="border border-[#1A4D5E] px-4 py-3 text-gray-300 align-top">
                      <div className="flex items-start gap-2">
                        <span className="text-green-400">✓</span>
                        <span><strong className="text-white">Secure API & Software Lifecycle</strong> (Pydantic validation, CI/CD scans)</span>
                      </div>
                    </td>
                    <td className="border border-[#1A4D5E] px-4 py-3 text-gray-300 align-top">
                      <div className="flex items-start gap-2">
                        <span className="text-gray-500">🔲</span>
                        <span><strong className="text-white">Private Connectivity</strong> (AWS PrivateLink)</span>
                      </div>
                    </td>
                    <td className="border border-[#1A4D5E] px-4 py-3 text-gray-300 align-top">
                      <div className="flex items-start gap-2">
                        <span className="text-gray-500">🔲</span>
                        <span><strong className="text-white">Regional Data Residency Controls</strong></span>
                      </div>
                    </td>
                  </tr>
                  <tr>
                    <td className="border border-[#1A4D5E] px-4 py-3 text-gray-300 align-top">
                      <div className="flex items-start gap-2">
                        <span className="text-green-400">✓</span>
                        <span><strong className="text-white">Immutable Audit Trail</strong> (Metadata-only logging)</span>
                      </div>
                    </td>
                    <td className="border border-[#1A4D5E] px-4 py-3 text-gray-300 align-top">
                      <div className="flex items-start gap-2">
                        <span className="text-gray-500">🔲</span>
                        <span><strong className="text-white">Public Trust Portal & Incident Response Plan</strong></span>
                      </div>
                    </td>
                    <td className="border border-[#1A4D5E] px-4 py-3 text-gray-300 align-top">
                      <div className="flex items-start gap-2">
                        <span className="text-gray-500">🔲</span>
                        <span><strong className="text-white">AI-Driven Threat Detection</strong></span>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )
    },
    {
      id: "hitl-workflow",
      category: "Security",
      question: "Human-in-the-Loop (HITL) - How does this work?",
      answer: "HITL is a governance mechanism requiring human approval for high-risk operations. When AI confidence is below threshold (typically 80%), the system queues the decision for human review. Applies to: schema mapping conflicts, auto-repair suggestions, agent actions affecting production data. Reviews are tracked in audit logs with full decision history."
    }
  ];

  const categories = ['all', ...Array.from(new Set(faqItems.map(item => item.category)))];
  
  // Filter by category and search query
  const filteredItems = faqItems.filter(item => {
    const inSelectedCategory = selectedCategory === 'all' || item.category === selectedCategory;
    
    if (searchQuery === '') {
      return inSelectedCategory;
    }
    
    const query = searchQuery.toLowerCase();
    const matchesQuestion = item.question.toLowerCase().includes(query);
    const matchesCategoryText = item.category.toLowerCase().includes(query);
    const matchesAnswer = typeof item.answer === 'string' 
      ? item.answer.toLowerCase().includes(query)
      : (item.searchableText?.toLowerCase().includes(query) ?? false);
    
    const matchesSearch = matchesQuestion || matchesCategoryText || matchesAnswer;
    return inSelectedCategory && matchesSearch;
  });

  // Get the index in the full faqItems array for the filtered item
  const getGlobalIndex = (filteredIndex: number) => {
    const item = filteredItems[filteredIndex];
    return faqItems.findIndex(i => i.id === item.id);
  };

  // Check if a filtered item is open
  const isItemOpen = (filteredIndex: number) => {
    const globalIndex = getGlobalIndex(filteredIndex);
    return openIndex === globalIndex;
  };

  return (
    <div className="min-h-screen bg-[#0A1628] py-8 px-4 safe-area">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-medium text-white mb-4">
            Help
          </h1>
          <p className="text-gray-400 text-lg">
            Complete guide to every feature and element in AutonomOS
          </p>
        </div>

        {/* Search Box */}
        <div className="mb-6">
          <input
            type="text"
            placeholder="Search help topics..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full px-4 py-3 bg-[#0D2F3F] border border-[#1A4D5E] rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-[#0BCAD9] focus:ring-1 focus:ring-[#0BCAD9]"
          />
        </div>

        {/* Category Filter */}
        <div className="mb-8 flex flex-wrap gap-2 justify-center">
          {categories.map(category => (
            <button
              key={category}
              onClick={() => setSelectedCategory(category)}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                selectedCategory === category
                  ? 'bg-[#0BCAD9] text-white'
                  : 'bg-[#0D2F3F] text-gray-400 hover:bg-[#0F3A4F]'
              }`}
            >
              {category === 'all' ? 'All Topics' : category}
            </button>
          ))}
        </div>

        {/* Results count */}
        {searchQuery && (
          <div className="mb-4 text-sm text-gray-400">
            Found {filteredItems.length} result{filteredItems.length !== 1 ? 's' : ''} for "{searchQuery}"
          </div>
        )}

        <div className="space-y-4">
          {filteredItems.length === 0 ? (
            <div className="bg-[#0D2F3F] border border-[#1A4D5E] rounded-xl p-12 text-center">
              <p className="text-gray-400 text-lg">No help topics found matching your search.</p>
              <p className="text-gray-500 text-sm mt-2">Try a different search term or browse all topics.</p>
            </div>
          ) : (
            filteredItems.map((item, filteredIndex) => (
            <div
              key={item.id}
              id={item.id}
              className="bg-[#0D2F3F] border border-[#1A4D5E] rounded-xl overflow-hidden scroll-mt-24"
            >
              <button
                onClick={() => toggleQuestion(getGlobalIndex(filteredIndex))}
                className="w-full px-6 py-5 flex items-center justify-between text-left hover:bg-[#0F3A4F] transition-colors"
              >
                <div>
                  <div className="text-xs text-[#0BCAD9] mb-1">{item.category}</div>
                  <h3 className="text-lg font-medium text-white pr-4">
                    {item.question}
                  </h3>
                </div>
                {isItemOpen(filteredIndex) ? (
                  <ChevronUp className="w-5 h-5 text-[#0BCAD9] flex-shrink-0" />
                ) : (
                  <ChevronDown className="w-5 h-5 text-[#0BCAD9] flex-shrink-0" />
                )}
              </button>

              {isItemOpen(filteredIndex) && (
                <div className="px-6 py-5 border-t border-[#1A4D5E] bg-[#0A2540]">
                  {typeof item.answer === 'string' ? (
                    <p className="text-gray-300 leading-relaxed">{item.answer}</p>
                  ) : (
                    item.answer
                  )}
                </div>
              )}
            </div>
          ))
          )}
        </div>

        <div className="mt-12 text-center">
          <div className="bg-[#0D2F3F] border border-[#0BCAD9]/30 rounded-xl p-8">
            <h3 className="text-xl font-medium text-white mb-3">
              Still have questions?
            </h3>
            <p className="text-gray-400 mb-6">
              Our team is here to help you understand how AutonomOS can transform your enterprise intelligence.
            </p>
            <button className="px-6 py-3 bg-[#0BCAD9] hover:bg-[#0AA5B3] text-white rounded-lg font-medium transition-colors">
              Contact Support
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
