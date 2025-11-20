import { useState, useEffect } from 'react';
import { ChevronLeft, ChevronRight, Play, Database, Zap, CheckCircle } from 'lucide-react';
import { mockAssets, getTotalCounts } from '../demo/aodMockData';
import {
  demoCustomer360Mappings,
  getVendorDisplayName,
  getVendorColor,
} from '../demo/demoDclMappings';
import { GraphView } from './GraphView';

type Stage = 1 | 2 | 3 | 4;

export default function DiscoveryDemoPage() {
  const [currentStage, setCurrentStage] = useState<Stage>(1);
  const [isRunningPipeline, setIsRunningPipeline] = useState(false);

  useEffect(() => {
    if (!isRunningPipeline) return;
    
    const timer = setTimeout(() => {
      if (currentStage < 4) {
        setCurrentStage((prev) => (prev + 1) as Stage);
      } else {
        setIsRunningPipeline(false);
      }
    }, 2000);

    return () => clearTimeout(timer);
  }, [currentStage, isRunningPipeline]);

  const handleRunFullPipeline = () => {
    setCurrentStage(1);
    setIsRunningPipeline(true);
  };

  const handleNext = () => {
    if (currentStage < 4) {
      setCurrentStage((prev) => (prev + 1) as Stage);
    }
  };

  const handleBack = () => {
    if (currentStage > 1) {
      setCurrentStage((prev) => (prev - 1) as Stage);
    }
  };

  const handleStageClick = (stage: Stage) => {
    setCurrentStage(stage);
    setIsRunningPipeline(false);
  };

  const totalCounts = getTotalCounts(mockAssets);

  return (
    <div className="flex flex-col h-screen bg-slate-950 text-white" style={{ fontFamily: 'Quicksand, sans-serif' }}>
      <TopBar currentStage={currentStage} isRunningPipeline={isRunningPipeline} />
      
      <div className="flex-1 flex overflow-hidden">
        <div className="w-2/3 border-r border-slate-800 p-8 bg-slate-950 overflow-hidden">
          <GraphPanel currentStage={currentStage} isRunningPipeline={isRunningPipeline} />
        </div>

        <div className="w-1/3 p-8 bg-slate-900 overflow-auto">
          <DetailPanel currentStage={currentStage} totalCounts={totalCounts} />
        </div>
      </div>

      <div className="bg-slate-900 border-t border-slate-800 px-6 py-6">
        <StepperNavigation
          currentStage={currentStage}
          onStageClick={handleStageClick}
          onBack={handleBack}
          onNext={handleNext}
          onRunFullPipeline={handleRunFullPipeline}
          isRunningPipeline={isRunningPipeline}
        />
      </div>
    </div>
  );
}

function TopBar({ currentStage, isRunningPipeline }: { currentStage: Stage; isRunningPipeline: boolean }) {
  return (
    <div className="bg-slate-900 border-b border-slate-800 px-6 py-4 flex items-center justify-between">
      <div className="flex items-center gap-4">
        <h1 className="text-xl font-bold text-white">AutonomOS – Discovery & Mesh Demo</h1>
        <span className="px-3 py-1 bg-cyan-500/20 border border-cyan-500/30 rounded-full text-xs text-cyan-400 font-semibold">
          Demo Tenant
        </span>
      </div>
      <div className="flex items-center gap-2">
        <span className="px-3 py-1 bg-green-500/20 border border-green-500/30 rounded-full text-xs text-green-400">
          Stage {currentStage} of 4
        </span>
        {isRunningPipeline && (
          <span className="px-3 py-1 bg-blue-500/20 border border-blue-500/30 rounded-full text-xs text-blue-400 flex items-center gap-2">
            <Zap className="w-3 h-3 animate-pulse" />
            Running Pipeline
          </span>
        )}
      </div>
    </div>
  );
}

function GraphPanel({ currentStage, isRunningPipeline }: { currentStage: Stage; isRunningPipeline: boolean }) {
  const pipelineStep = currentStage - 1;
  const pipelineState = isRunningPipeline ? "running" : "idle";

  return (
    <div className="h-full flex flex-col">
      <h2 className="text-2xl font-bold text-white mb-8">Pipeline Graph</h2>
      <div className="flex-1">
        <GraphView 
          pipelineStep={pipelineStep} 
          pipelineState={pipelineState}
          onNodeClick={(id) => console.log("Clicked:", id)} 
        />
      </div>
    </div>
  );
}

function DetailPanel({ currentStage, totalCounts }: { currentStage: Stage; totalCounts: any }) {
  if (currentStage === 1) {
    return <Stage1AODDiscovery totalCounts={totalCounts} />;
  } else if (currentStage === 2) {
    return <Stage2AAMConnections />;
  } else if (currentStage === 3) {
    return <Stage3DCLMapping />;
  } else {
    return <Stage4AgentExecution />;
  }
}

function Stage1AODDiscovery({ totalCounts }: { totalCounts: any }) {
  const demoAssets = mockAssets.slice(0, 10);

  const getRiskLevel = (state: string) => {
    if (state === 'UNKNOWN') return 'High';
    if (state === 'PARKED') return 'Medium';
    return 'Low';
  };

  const getRiskColor = (risk: string) => {
    if (risk === 'High') return 'text-red-400';
    if (risk === 'Medium') return 'text-orange-400';
    return 'text-green-400';
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-white mb-2 break-words">AOD Discovery — Assets & Risk</h2>
        <p className="text-xs text-slate-400 break-words">Automatically discovered assets across the demo tenant</p>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-3">
          <div className="text-xl font-bold text-white">{totalCounts.total}</div>
          <div className="text-xs text-slate-400 mt-1">Assets</div>
        </div>
        <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-3">
          <div className="text-xl font-bold text-green-400">{totalCounts.ready}</div>
          <div className="text-xs text-slate-400 mt-1">Ready</div>
        </div>
        <div className="bg-orange-500/10 border border-orange-500/30 rounded-lg p-3">
          <div className="text-xl font-bold text-orange-400">{totalCounts.parked}</div>
          <div className="text-xs text-slate-400 mt-1">Parked</div>
        </div>
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
          <div className="text-xl font-bold text-red-400">{totalCounts.shadowIT}</div>
          <div className="text-xs text-slate-400 mt-1 break-words">Shadow / High-Risk</div>
        </div>
      </div>

      <div className="bg-slate-800 border border-slate-700 rounded-lg overflow-x-auto">
        <table className="w-full min-w-max">
          <thead className="bg-slate-900 border-b border-slate-700">
            <tr>
              <th className="text-left px-2 py-2 text-[10px] font-semibold text-slate-400 uppercase">Asset</th>
              <th className="text-left px-2 py-2 text-[10px] font-semibold text-slate-400 uppercase">Vendor</th>
              <th className="text-left px-2 py-2 text-[10px] font-semibold text-slate-400 uppercase">Kind</th>
              <th className="text-left px-2 py-2 text-[10px] font-semibold text-slate-400 uppercase">Env</th>
              <th className="text-left px-2 py-2 text-[10px] font-semibold text-slate-400 uppercase">Risk</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700">
            {demoAssets.map((asset) => {
              const risk = getRiskLevel(asset.state);
              const vendorName = getVendorDisplayName(asset.vendor);
              
              return (
                <tr key={asset.id} className="hover:bg-slate-700/50">
                  <td className="px-2 py-2 text-xs text-white truncate max-w-[120px]" title={asset.name}>{asset.name}</td>
                  <td className="px-2 py-2 text-xs">
                    <span style={{ color: getVendorColor(asset.vendor) }}>{vendorName}</span>
                  </td>
                  <td className="px-2 py-2 text-xs text-slate-300 capitalize">{asset.kind}</td>
                  <td className="px-2 py-2 text-xs text-slate-300 uppercase">{asset.environment}</td>
                  <td className={`px-2 py-2 text-xs font-semibold ${getRiskColor(risk)}`}>{risk}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="bg-slate-800 border border-slate-700 rounded-lg p-3 space-y-2">
        <div className="text-xs text-slate-400 break-words">
          <span className="font-semibold text-orange-400">Normally:</span> spreadsheets, interviews, and guesswork to find what's running.
        </div>
        <div className="text-xs text-cyan-400 break-words">
          <span className="font-semibold">Here:</span> AOS uses log & config telemetry and AI classifiers to discover and risk-score assets.
        </div>
      </div>
    </div>
  );
}

function Stage2AAMConnections() {
  const connectors = [
    {
      vendor: 'Salesforce',
      color: '#0BCAD9',
      auth: 'OAuth2, scopes: api, refresh_token, offline_access',
      contract: 'API v59.0, endpoints: /sobjects/Account, /sobjects/Opportunity',
      details: 'Rate limits: 100 req/s, exponential backoff with jitter',
    },
    {
      vendor: 'MongoDB',
      color: '#10B981',
      auth: 'TLS SRV, vault credentials',
      contract: 'Collections: users, events, read preference: secondaryPreferred',
      details: 'Connection pooling: max 20, min 5, timeout 30s',
    },
    {
      vendor: 'Supabase',
      color: '#A855F7',
      auth: 'Postgres URL, schema: public, RLS awareness',
      contract: 'Connection mode: PgBouncer session, max 10 connections',
      details: 'Tables: customers, invoices, usage_events',
    },
    {
      vendor: 'Legacy Files',
      color: '#F97316',
      auth: 'S3 bucket, IAM role credentials, SSE-S3 encryption',
      contract: 'File pattern: *.csv, schedule: daily at 02:00 UTC',
      details: 'Buckets: customer-exports, legacy-backups, retention: 90 days',
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-white mb-2 break-words">AAM Connections — Connectors</h2>
        <p className="text-xs text-slate-400 break-words">Adaptive API Mesh connector configurations</p>
      </div>

      <div className="space-y-3">
        {connectors.map((connector) => (
          <div key={connector.vendor} className="bg-slate-800 border border-slate-700 rounded-lg p-3">
            <h3 className="text-sm font-bold mb-2 break-words" style={{ color: connector.color }}>
              {connector.vendor}
            </h3>
            
            <div className="space-y-2 text-xs">
              <div>
                <div className="text-slate-400 font-semibold">Auth:</div>
                <div className="text-slate-300 break-words">{connector.auth}</div>
              </div>
              
              <div>
                <div className="text-slate-400 font-semibold">Contract:</div>
                <div className="text-slate-300 break-words">{connector.contract}</div>
              </div>
              
              <div>
                <div className="text-slate-400 font-semibold">Details:</div>
                <div className="text-slate-300 break-words">{connector.details}</div>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="bg-cyan-500/10 border border-cyan-500/30 rounded-lg p-3">
        <div className="text-xs text-cyan-300 break-words">
          <span className="font-semibold">How AOS configured this:</span> AI over config corpus chooses auth flows, scopes, timeouts. No manual YAML.
        </div>
      </div>
    </div>
  );
}

function Stage3DCLMapping() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">DCL Mapping — Unified <code className="text-cyan-400">customer_360</code> Entity</h2>
        <p className="text-sm text-slate-400">Schema mappings from Salesforce, MongoDB, Supabase, and Legacy Files</p>
      </div>

      <div className="bg-purple-500/10 border border-purple-500/30 rounded-lg p-4 text-sm text-purple-300">
        DCL builds a unified customer_360 entity from Salesforce, MongoDB, Supabase, and Legacy Files.
      </div>

      <div className="bg-slate-800 border border-slate-700 rounded-lg overflow-hidden">
        <table className="w-full">
          <thead className="bg-slate-900 border-b border-slate-700">
            <tr>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase">Canonical Field</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase">Type</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase">Sources</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700">
            {demoCustomer360Mappings.map((mapping) => (
              <tr key={mapping.canonicalField} className="hover:bg-slate-700/50">
                <td className="px-4 py-3">
                  <code className="text-cyan-400 font-mono text-sm">{mapping.canonicalField}</code>
                </td>
                <td className="px-4 py-3">
                  <span className="text-xs px-2 py-1 rounded bg-slate-700 text-slate-300">
                    {mapping.type}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-2">
                    {mapping.sources.map((source, idx) => (
                      <div
                        key={idx}
                        className="text-xs px-2 py-1 rounded border flex items-center gap-1"
                        style={{
                          backgroundColor: `${getVendorColor(source.vendor)}15`,
                          borderColor: `${getVendorColor(source.vendor)}40`,
                          color: getVendorColor(source.vendor),
                        }}
                      >
                        <span className="font-semibold">{getVendorDisplayName(source.vendor)}</span>
                        <span className="text-slate-400">·</span>
                        <code className="font-mono">{source.fieldPath}</code>
                        <span className="text-slate-400">·</span>
                        <span className="font-bold">{Math.round(source.confidence * 100)}%</span>
                      </div>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="bg-slate-800 border border-slate-700 rounded-lg p-4 space-y-2">
        <div className="text-sm text-slate-400">
          <span className="font-semibold text-orange-400">Normally:</span> weeks of debating IDs and joins across CRM, billing, events, and legacy exports.
        </div>
        <div className="text-sm text-cyan-400">
          <span className="font-semibold">Here:</span> ontologies, naming heuristics, and data profiling propose canonical fields and joins with confidence scores.
        </div>
      </div>
    </div>
  );
}

function Stage4AgentExecution() {
  const executionTrace = [
    'Resolved question to customer_360 unified entity.',
    'Selected fields: customer_id, arr, last_activity_at, churn_flag, risk_score.',
    'Fetched data via AAM from Salesforce, MongoDB, Supabase, Legacy Files.',
    'Applied enterprise policy HIGH_ARR_HIGH_RISK_SERVICES.',
  ];

  const results = [
    {
      service: 'Enterprise Platform API',
      arr: '$2.4M',
      riskScore: 87,
      reason: 'High error rate (12%), declining engagement, overdue invoices',
    },
    {
      service: 'Analytics Dashboard Service',
      arr: '$1.8M',
      riskScore: 74,
      reason: 'Churn flag active, 45-day inactivity, support ticket spike',
    },
    {
      service: 'Global Commerce Platform',
      arr: '$3.1M',
      riskScore: 92,
      reason: 'Critical SLA breaches, payment delays, exec escalation',
    },
    {
      service: 'Mobile SDK Integration',
      arr: '$1.2M',
      riskScore: 68,
      reason: 'Usage decline 40%, feature adoption low, renewal at risk',
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">Agent Execution — Query Plan & Result Trace</h2>
        <p className="text-sm text-slate-400">Natural language query executed over unified customer_360 entity</p>
      </div>

      <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
        <div className="text-xs text-slate-400 uppercase font-semibold mb-2">User Question:</div>
        <div className="text-sm text-white italic">
          "Show risky customer-facing services over $1M ARR across Salesforce, MongoDB, Supabase, and Legacy Files."
        </div>
      </div>

      <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
        <div className="text-xs text-slate-400 uppercase font-semibold mb-3">Execution Trace:</div>
        <div className="space-y-2">
          {executionTrace.map((step, idx) => (
            <div key={idx} className="flex items-start gap-3">
              <CheckCircle className="w-4 h-4 text-green-400 mt-0.5 flex-shrink-0" />
              <div className="text-sm text-slate-300">{step}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-slate-800 border border-slate-700 rounded-lg overflow-hidden">
        <table className="w-full">
          <thead className="bg-slate-900 border-b border-slate-700">
            <tr>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase">Service/Customer</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase">ARR</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase">Risk Score</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase">Why Flagged</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700">
            {results.map((result, idx) => (
              <tr key={idx} className="hover:bg-slate-700/50">
                <td className="px-4 py-3 text-sm text-white font-medium">{result.service}</td>
                <td className="px-4 py-3 text-sm text-green-400 font-semibold">{result.arr}</td>
                <td className="px-4 py-3">
                  <span className={`text-sm font-bold ${
                    result.riskScore >= 80 ? 'text-red-400' : 'text-orange-400'
                  }`}>
                    {result.riskScore}
                  </span>
                </td>
                <td className="px-4 py-3 text-sm text-slate-300">{result.reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="bg-cyan-500/10 border border-cyan-500/30 rounded-lg p-4">
        <div className="text-sm text-cyan-300">
          <span className="font-semibold">How this works:</span> Agent executes over DCL's unified view, not raw tables; no manual SQL or joins.
        </div>
      </div>
    </div>
  );
}

function StepperNavigation({
  currentStage,
  onStageClick,
  onBack,
  onNext,
  onRunFullPipeline,
  isRunningPipeline,
}: {
  currentStage: Stage;
  onStageClick: (stage: Stage) => void;
  onBack: () => void;
  onNext: () => void;
  onRunFullPipeline: () => void;
  isRunningPipeline: boolean;
}) {
  const stages = [
    { num: 1, label: 'AOD Discovery' },
    { num: 2, label: 'AAM Connections' },
    { num: 3, label: 'DCL Mapping' },
    { num: 4, label: 'Agent Execution' },
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-center gap-4">
        {stages.map((stage, idx) => (
          <div key={stage.num} className="flex items-center">
            <button
              onClick={() => onStageClick(stage.num as Stage)}
              className={`flex flex-col items-center gap-2 px-6 py-3 rounded-lg transition-all ${
                currentStage === stage.num
                  ? 'bg-cyan-500/20 border-2 border-cyan-500'
                  : 'bg-slate-800 border-2 border-slate-700 hover:border-slate-600'
              }`}
            >
              <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold ${
                currentStage === stage.num
                  ? 'bg-cyan-500 text-white'
                  : currentStage > stage.num
                  ? 'bg-green-500 text-white'
                  : 'bg-slate-700 text-slate-400'
              }`}>
                {currentStage > stage.num ? '✓' : stage.num}
              </div>
              <div className={`text-sm font-semibold ${
                currentStage === stage.num ? 'text-cyan-400' : 'text-slate-400'
              }`}>
                {stage.label}
              </div>
            </button>
            {idx < stages.length - 1 && (
              <div className={`w-12 h-0.5 mx-2 ${
                currentStage > stage.num ? 'bg-green-500' : 'bg-slate-700'
              }`} />
            )}
          </div>
        ))}
      </div>

      <div className="flex items-center justify-between">
        <button
          onClick={onBack}
          disabled={currentStage === 1}
          className="px-6 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg transition-colors font-semibold flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <ChevronLeft className="w-4 h-4" />
          Back
        </button>

        <button
          onClick={onRunFullPipeline}
          disabled={isRunningPipeline}
          className="px-6 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg transition-colors font-semibold flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Play className="w-4 h-4" />
          Run Full Pipeline
        </button>

        <button
          onClick={onNext}
          disabled={currentStage === 4}
          className="px-6 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg transition-colors font-semibold flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Next
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
