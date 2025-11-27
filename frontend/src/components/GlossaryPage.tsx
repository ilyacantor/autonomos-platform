import { useState } from 'react';
import { Search, ChevronDown, ChevronUp, BookOpen, Server, Database, Users, Layers, GitBranch } from 'lucide-react';

interface GlossaryTerm {
  id: string;
  term: string;
  definition: string;
  details?: string[];
  examples?: string[];
  category: string;
}

interface GlossaryCategory {
  id: string;
  name: string;
  icon: React.ReactNode;
  description: string;
}

const categories: GlossaryCategory[] = [
  { id: 'core', name: 'Core Platform', icon: <Layers className="w-5 h-5" />, description: 'Main platform components' },
  { id: 'data', name: 'Data Concepts', icon: <Database className="w-5 h-5" />, description: 'Data and system terminology' },
  { id: 'external', name: 'External Stack', icon: <Server className="w-5 h-5" />, description: 'External integrations' },
  { id: 'personas', name: 'Personas & UI', icon: <Users className="w-5 h-5" />, description: 'Human-facing concepts' },
  { id: 'distinctions', name: 'Key Distinctions', icon: <GitBranch className="w-5 h-5" />, description: 'Important differences' },
];

const glossaryTerms: GlossaryTerm[] = [
  {
    id: 'autonomos',
    term: 'AutonomOS (AOS)',
    definition: 'An AI-native "operating system" for the enterprise data/agent stack. It sits between chaotic source systems and domain agents.',
    details: [
      'Discover & classify everything that runs in your estate (AOD)',
      'Connect & normalize business data into a canonical ontology (AAM + DCL)',
      'Feed agents & humans clean, persona-specific streams of information'
    ],
    category: 'core'
  },
  {
    id: 'aod',
    term: 'AOD (Asset & Observability Discovery)',
    definition: 'Component that discovers, catalogs, and scores everything running in the environment. Answers: "What assets do we have, where are they, and how risky/important are they?"',
    details: [
      'Ingests infrastructure and SaaS telemetry (logs, configs, IdP, cloud APIs)',
      'Builds and maintains the Asset Graph (hosts, DBs, apps, SaaS tenants, queues)',
      'Flags shadow IT, risky assets, anomalies, and policy vs reality mismatches',
      'Provides input into AAM (connectors), DCL (sources), and Agents (context)'
    ],
    category: 'core'
  },
  {
    id: 'aam',
    term: 'AAM (Adaptive API Mesh)',
    definition: 'The connection and auth layer between AOS and external systems (APIs, DBs, SaaS). Abstracts away OAuth, IdP integration, secrets, per-system quirks, and rate limits.',
    details: [
      'Manages connectors (Salesforce, NetSuite, Stripe, SAP, Snowflake, Postgres)',
      'Mediates authentication & authorization via IdP and/or secrets managers',
      'Normalizes access patterns into unified interface for "Read entities", "Read events", "Write back"',
      'Exposes uniform API (RPC/HTTP/GraphQL) to DCL, AOD, and Agents'
    ],
    category: 'core'
  },
  {
    id: 'dcl',
    term: 'DCL (Data Connectivity Layer)',
    definition: 'The unification and ontology engine for business data. Converts heterogeneous schemas from many systems into a canonical set of entities.',
    details: [
      'Maintains the ontology (Account, Opportunity, Revenue, Cost, Usage)',
      'Identifies relevant Sources (systems-of-record, DW tables)',
      'Maps source fields to canonical fields',
      'Performs entity resolution (same customer across Salesforce, NetSuite, DW)',
      'Produces canonical streams that are clean, de-duplicated, and linked across systems'
    ],
    category: 'core'
  },
  {
    id: 'agent-layer',
    term: 'Agent Layer (Domain Agents)',
    definition: 'A family of domain-specific agents that consume canonical data and act: FinOps Agent, RevOps Agent, SecOps/Risk Agent, Ops/Usage Agent.',
    details: [
      'Operate on top of DCL\'s canonical streams, not raw sources',
      'Combine domain rules & heuristics, LLM/RAG reasoning, historical patterns',
      'Produce recommendations, alerts, what-if scenarios, and actions',
      'Expose outputs via dashboards, chat/NLP interface, and APIs/webhooks'
    ],
    category: 'core'
  },
  {
    id: 'aos-farm',
    term: 'AOS Farm',
    definition: 'A synthetic but realistic enterprise environment used to test and validate AOS without real customer data.',
    details: [
      'Generates synthetic Assets (apps, DBs, SaaS tenants)',
      'Generates synthetic Sources (CRMs, ERPs, billing systems, DW tables)',
      'Creates realistic data patterns: duplicates, schema drift, conflicts, shadow IT',
      'Enables regression testing, performance testing, and demo environments'
    ],
    category: 'core'
  },
  {
    id: 'asset',
    term: 'Asset',
    definition: 'Anything that runs: it has a runtime/process, can be up or down, consumes CPU/RAM/IO, and has a potential blast radius if it fails. If it doesn\'t "run," it\'s NOT an Asset.',
    details: [
      'Infrastructure: VM, K8s node/pod, container, serverless function, load balancer, API gateway',
      'Data platforms: Postgres/MySQL instance, MongoDB cluster, Snowflake/BigQuery warehouse',
      'SaaS/apps: Salesforce org, NetSuite instance, Slack workspace, internal microservices',
      'Pipelines: Airflow/Dagster/dbt runners, ETL/ELT jobs, streaming consumers'
    ],
    examples: [
      'NOT Assets: CSV files in S3, table definitions, GitHub repos, dbt model files, Notion pages'
    ],
    category: 'data'
  },
  {
    id: 'source',
    term: 'Source',
    definition: 'A logical system-of-record for one or more ontology entities in DCL. It is about business meaning, not just infrastructure.',
    details: [
      'A single Asset can back multiple Sources',
      'A Source can span multiple Assets',
      'DCL reads from Sources, not arbitrary Assets'
    ],
    examples: [
      'salesforce_crm – SoR for Account, Opportunity',
      'netsuite_erp – SoR for Customer, Invoice',
      'stripe_billing – SoR for Subscription, Charge',
      'dw_dim_customer – curated customer dimension table'
    ],
    category: 'data'
  },
  {
    id: 'source-types',
    term: 'Source Types (Tiers)',
    definition: 'Classification of Sources based on their role in the data stack.',
    details: [
      'SYSTEM_OF_RECORD (SoR): Operational systems where events originate (Salesforce, NetSuite, Stripe)',
      'CURATED / CONFORMED: Warehouse/lake tables already cleaned and modeled (dim_customer, fact_revenue)',
      'AGGREGATED / DERIVED: Highly aggregated structures for reporting (MRR by segment)',
      'CONSUMER_ONLY: Tools that just read and visualize (Tableau, Looker dashboards)'
    ],
    examples: [
      'DCL treats SYSTEM_OF_RECORD and CURATED as true Sources',
      'AGGREGATED and CONSUMER_ONLY are usually Assets only, not DCL Sources'
    ],
    category: 'data'
  },
  {
    id: 'ontology',
    term: 'Ontology',
    definition: 'The formal definition of the business entities AOS cares about and how they relate.',
    details: [
      'Classes/entities: Account, Opportunity, Revenue, Cost, Usage, Health, AwsResource',
      'Properties/fields: account_id, name, billing_country',
      'Relationships: Account has many Opportunities; Account generates Revenue'
    ],
    examples: [
      'Defined and owned by DCL',
      'Drives field mapping, entity resolution, canonical stream structure',
      'Determines what Agents can "see" and reason about'
    ],
    category: 'data'
  },
  {
    id: 'canonical-entity',
    term: 'Canonical Entity & Stream',
    definition: 'A unified, deduplicated representation of a real-world thing across multiple Sources.',
    details: [
      'Canonical Entity: Salesforce Account + NetSuite Customer + DW dim_customer → one canonical Account',
      'Canonical Stream: Time-ordered stream of canonical entities (AccountStream, RevenueStream, UsageStream)',
      'The ONLY thing that Agents and dashboards depend on',
      'Decouples upstream chaos from downstream intelligence'
    ],
    category: 'data'
  },
  {
    id: 'lineage',
    term: 'Lineage & Provenance',
    definition: 'The ability to trace a canonical entity or field back to the underlying Sources and Assets.',
    details: [
      'Explains data origin: "This MRR comes from dw_fact_revenue, built from Stripe + NetSuite"',
      'Supports trust, explainability, debugging, compliance, and audits'
    ],
    category: 'data'
  },
  {
    id: 'data-warehouse',
    term: 'Data Warehouse / Data Lake',
    definition: 'Central platforms where enterprises store and model data from many systems.',
    details: [
      'Warehouses: Snowflake, BigQuery, Redshift, Synapse',
      'Lakes/Lakehouses: Databricks, S3 + Iceberg/Delta, GCS + BigLake',
      'Always Assets in AOS',
      'May host CURATED or SYSTEM_OF_RECORD Sources'
    ],
    category: 'external'
  },
  {
    id: 'semantic-layer',
    term: 'Semantic / Metrics Layer',
    definition: 'Layer that defines business metrics and dimensions on top of DW (dbt, LookML, metrics layers).',
    details: [
      'Represented as CURATED Sources when they define entity-level tables',
      'Or AGGREGATED if they only produce rollups',
      'Used by Agents for high-level KPIs and sanity checks'
    ],
    category: 'external'
  },
  {
    id: 'bi-tools',
    term: 'BI / Reporting Tools',
    definition: 'Tools that visualize data and provide dashboards: Tableau, Looker, Power BI, Mode.',
    details: [
      'Always Assets in AOS',
      'Typically CONSUMER_ONLY, not Sources',
      'Consumers of canonical streams pushed to DW and agent-generated views'
    ],
    category: 'external'
  },
  {
    id: 'idp',
    term: 'IdP (Identity Provider)',
    definition: 'Central identity & access provider used by AAM for OAuth/OIDC, SSO, and app discovery.',
    examples: [
      'Okta, Entra ID (Azure AD), on-prem AD'
    ],
    category: 'external'
  },
  {
    id: 'secrets-manager',
    term: 'Secrets Manager',
    definition: 'Stores credentials/tokens that AAM uses when IdP-based integration is not possible.',
    examples: [
      'Doppler, AWS Secrets Manager, HashiCorp Vault, GCP Secret Manager'
    ],
    category: 'external'
  },
  {
    id: 'personas',
    term: 'Personas',
    definition: 'High-level roles in the business that consume information: CFO, CRO, COO, CTO.',
    details: [
      'Each Persona has a set of ontology entities they primarily care about',
      'Each has a canonical dashboard in their language',
      'Optional dedicated agents (FinOps, RevOps)'
    ],
    examples: [
      'CFO: Revenue, Cost, Margin, Cash, Risk',
      'CRO: Account, Opportunity, Pipeline, Churn',
      'COO: Usage, Health, SLAs, Incidents',
      'CTO: Assets, CloudResources, Cost, Risk, TechDebt'
    ],
    category: 'personas'
  },
  {
    id: 'dashboards',
    term: 'Dashboards',
    definition: 'UI surfaces that present canonical data and agent insights per Persona.',
    details: [
      'Read from canonical streams and agent outputs, not raw sources',
      'Show KPIs, trends, anomalies',
      'Links back to underlying Sources/Assets via lineage',
      '"Single pane of glass" for each Persona'
    ],
    category: 'personas'
  },
  {
    id: 'nlp-interface',
    term: 'NLP / Chat Interface',
    definition: 'Natural-language interface to query the system and interact with agents.',
    details: [
      'Ask questions: "Why did revenue drop last month?"',
      'Request actions: "Simulate impact of a 10% price increase in EMEA."',
      'Routes to the right agent(s) behind the scenes',
      'Executes on top of canonical streams + ontology'
    ],
    category: 'personas'
  },
  {
    id: 'asset-vs-source',
    term: 'Asset vs Source',
    definition: 'Key distinction: Asset = anything that RUNS (has runtime, blast radius). Source = logical system-of-record for business entities.',
    details: [
      'Asset examples: PostgreSQL instance, Salesforce org, K8s pod, Redis cache',
      'Source examples: salesforce_crm, internal_crm_postgres, dw_dim_customer',
      'NOT Assets: CSV files, table definitions, GitHub repos, dbt models, docs'
    ],
    examples: [
      'The runtime (Snowflake warehouse) is the Asset',
      'The data and definitions it holds are not Assets',
      'A database (Asset) becomes a Source when it serves as system-of-record'
    ],
    category: 'distinctions'
  }
];

export default function GlossaryPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [expandedTerms, setExpandedTerms] = useState<Set<string>>(new Set());

  const toggleTerm = (termId: string) => {
    setExpandedTerms(prev => {
      const newSet = new Set(prev);
      if (newSet.has(termId)) {
        newSet.delete(termId);
      } else {
        newSet.add(termId);
      }
      return newSet;
    });
  };

  const filteredTerms = glossaryTerms.filter(term => {
    const matchesSearch = searchQuery === '' || 
      term.term.toLowerCase().includes(searchQuery.toLowerCase()) ||
      term.definition.toLowerCase().includes(searchQuery.toLowerCase()) ||
      term.details?.some(d => d.toLowerCase().includes(searchQuery.toLowerCase())) ||
      term.examples?.some(e => e.toLowerCase().includes(searchQuery.toLowerCase()));
    
    const matchesCategory = selectedCategory === 'all' || term.category === selectedCategory;
    
    return matchesSearch && matchesCategory;
  });

  const getCategoryInfo = (categoryId: string) => {
    return categories.find(c => c.id === categoryId);
  };

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="flex flex-col sm:flex-row gap-3 sm:gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4 sm:w-5 sm:h-5" />
          <input
            type="text"
            placeholder="Search glossary terms..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 sm:pl-10 pr-4 py-2.5 sm:py-3 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm sm:text-base placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500"
          />
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => setSelectedCategory('all')}
          className={`px-3 py-1.5 sm:px-4 sm:py-2 rounded-lg text-xs sm:text-sm font-medium transition-colors ${
            selectedCategory === 'all'
              ? 'bg-cyan-600 text-white'
              : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
          }`}
        >
          All ({glossaryTerms.length})
        </button>
        {categories.map((category) => {
          const count = glossaryTerms.filter(t => t.category === category.id).length;
          return (
            <button
              key={category.id}
              onClick={() => setSelectedCategory(category.id)}
              className={`flex items-center gap-1.5 sm:gap-2 px-3 py-1.5 sm:px-4 sm:py-2 rounded-lg text-xs sm:text-sm font-medium transition-colors ${
                selectedCategory === category.id
                  ? 'bg-cyan-600 text-white'
                  : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
              }`}
            >
              <span className="hidden sm:inline">{category.icon}</span>
              {category.name} ({count})
            </button>
          );
        })}
      </div>

      <div className="text-xs sm:text-sm text-gray-400">
        Showing {filteredTerms.length} of {glossaryTerms.length} terms
      </div>

      <div className="space-y-3">
        {filteredTerms.map((term) => {
          const isExpanded = expandedTerms.has(term.id);
          const categoryInfo = getCategoryInfo(term.category);
          
          return (
            <div
              key={term.id}
              id={term.id}
              className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden hover:border-gray-600 transition-colors"
            >
              <button
                onClick={() => toggleTerm(term.id)}
                className="w-full px-4 py-3 sm:px-5 sm:py-4 flex items-start justify-between gap-3 text-left"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    {categoryInfo && (
                      <span className="text-cyan-400 flex-shrink-0">
                        {categoryInfo.icon}
                      </span>
                    )}
                    <h3 className="text-base sm:text-lg font-semibold text-white truncate">
                      {term.term}
                    </h3>
                  </div>
                  <p className={`text-sm text-gray-300 ${isExpanded ? '' : 'line-clamp-2'}`}>
                    {term.definition}
                  </p>
                </div>
                <span className="text-gray-400 flex-shrink-0 mt-1">
                  {isExpanded ? (
                    <ChevronUp className="w-5 h-5" />
                  ) : (
                    <ChevronDown className="w-5 h-5" />
                  )}
                </span>
              </button>
              
              {isExpanded && (
                <div className="px-4 pb-4 sm:px-5 sm:pb-5 space-y-4">
                  {term.details && term.details.length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium text-cyan-400 mb-2">Key Points</h4>
                      <ul className="space-y-1.5">
                        {term.details.map((detail, idx) => (
                          <li key={idx} className="flex items-start gap-2 text-sm text-gray-300">
                            <span className="text-cyan-500 mt-1.5 flex-shrink-0">•</span>
                            <span>{detail}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  
                  {term.examples && term.examples.length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium text-purple-400 mb-2">Examples</h4>
                      <ul className="space-y-1.5">
                        {term.examples.map((example, idx) => (
                          <li key={idx} className="flex items-start gap-2 text-sm text-gray-300">
                            <span className="text-purple-500 mt-1.5 flex-shrink-0">→</span>
                            <span className="font-mono text-xs sm:text-sm bg-gray-900 px-2 py-1 rounded">{example}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  
                  <div className="pt-2 border-t border-gray-700">
                    <span className="inline-flex items-center gap-1.5 px-2 py-1 bg-gray-900 rounded text-xs text-gray-400">
                      {categoryInfo?.icon}
                      {categoryInfo?.name}
                    </span>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {filteredTerms.length === 0 && (
        <div className="text-center py-12">
          <BookOpen className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <p className="text-gray-400">No terms found matching your search.</p>
          <button
            onClick={() => {
              setSearchQuery('');
              setSelectedCategory('all');
            }}
            className="mt-4 text-cyan-400 hover:text-cyan-300 text-sm"
          >
            Clear filters
          </button>
        </div>
      )}
    </div>
  );
}
