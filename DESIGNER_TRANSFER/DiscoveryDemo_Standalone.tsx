/**
 * AutonomOS Discovery Demo - Standalone UI for Replit Designer
 * 
 * This is a complete, self-contained UI component with no backend dependencies.
 * All data is mock/inline. Ready for visual design work in Replit Designer.
 * 
 * Dependencies needed:
 * - react
 * - reactflow
 * - framer-motion
 * - lucide-react
 * - clsx
 * - tailwind-merge
 */

import { useState, useEffect, useCallback } from 'react';
import { 
  ReactFlow, 
  Background, 
  Controls, 
  useNodesState, 
  useEdgesState,
  Handle, 
  Position,
  NodeProps,
  Edge,
  Node,
  MarkerType,
  EdgeProps,
  BaseEdge,
  getSmoothStepPath
} from 'reactflow';
import 'reactflow/dist/style.css';
import { 
  ChevronLeft, 
  ChevronRight, 
  Play, 
  Zap,
  Database, 
  FileText, 
  Globe, 
  Server, 
  Plug, 
  Network, 
  Sparkles, 
  Search
} from 'lucide-react';
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

// Utility function
function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Types
type Stage = 1 | 2 | 3 | 4;

// ============================================================================
// MOCK DATA
// ============================================================================

const mockAssets = [
  { id: '1', name: 'Salesforce Production Instance', vendor: 'salesforce', kind: 'saas', environment: 'PROD', state: 'READY_FOR_CONNECT' },
  { id: '2', name: 'Salesforce Accounts API', vendor: 'salesforce', kind: 'service', environment: 'PROD', state: 'READY_FOR_CONNECT' },
  { id: '3', name: 'Salesforce Opportunities', vendor: 'salesforce', kind: 'db', environment: 'PROD', state: 'READY_FOR_CONNECT' },
  { id: '4', name: 'Salesforce Contacts API', vendor: 'salesforce', kind: 'service', environment: 'PROD', state: 'READY_FOR_CONNECT' },
  { id: '5', name: 'MongoDB Users Collection', vendor: 'mongodb', kind: 'db', environment: 'PROD', state: 'READY_FOR_CONNECT' },
  { id: '6', name: 'MongoDB Events', vendor: 'mongodb', kind: 'db', environment: 'PROD', state: 'READY_FOR_CONNECT' },
  { id: '7', name: 'Supabase Customers Table', vendor: 'supabase', kind: 'db', environment: 'PROD', state: 'PARKED' },
  { id: '8', name: 'Supabase Invoices', vendor: 'supabase', kind: 'db', environment: 'PROD', state: 'PARKED' },
  { id: '9', name: 'Legacy Customer Export', vendor: 'legacy', kind: 'file', environment: 'PROD', state: 'UNKNOWN' },
  { id: '10', name: 'Legacy Backup Files', vendor: 'legacy', kind: 'file', environment: 'PROD', state: 'UNKNOWN' },
];

const getTotalCounts = () => ({
  total: 35,
  ready: 22,
  parked: 7,
  shadowIT: 3,
});

const getVendorDisplayName = (vendor: string) => {
  const map: Record<string, string> = {
    salesforce: 'Salesforce',
    mongodb: 'MongoDB',
    supabase: 'Supabase',
    legacy: 'Legacy Files',
  };
  return map[vendor] || vendor;
};

const getVendorColor = (vendor: string) => {
  const map: Record<string, string> = {
    salesforce: '#0BCAD9',
    mongodb: '#10B981',
    supabase: '#A855F7',
    legacy: '#F97316',
  };
  return map[vendor] || '#94a3b8';
};

const demoCustomer360Mappings = [
  { canonicalField: 'customer_id', type: 'UUID', sources: 'Salesforce.Id, MongoDB._id, Supabase.id' },
  { canonicalField: 'email', type: 'String', sources: 'Salesforce.Email, MongoDB.email, Legacy.customer_email' },
  { canonicalField: 'full_name', type: 'String', sources: 'Salesforce.Name, MongoDB.fullName' },
  { canonicalField: 'company', type: 'String', sources: 'Salesforce.Account.Name, MongoDB.company' },
  { canonicalField: 'created_at', type: 'Timestamp', sources: 'Salesforce.CreatedDate, MongoDB.createdAt' },
  { canonicalField: 'total_revenue', type: 'Decimal', sources: 'Salesforce.TotalRevenue, Supabase.revenue_sum' },
  { canonicalField: 'account_status', type: 'Enum', sources: 'Salesforce.Status, MongoDB.accountStatus' },
  { canonicalField: 'last_login', type: 'Timestamp', sources: 'MongoDB.lastLogin, Supabase.last_seen' },
  { canonicalField: 'subscription_tier', type: 'String', sources: 'Salesforce.Tier, MongoDB.subscription' },
];

// ============================================================================
// GRAPH COMPONENTS
// ============================================================================

const DataFlowEdge = ({
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style = {},
  markerEnd,
  data
}: EdgeProps) => {
  const [edgePath] = getSmoothStepPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  return (
    <>
      <BaseEdge path={edgePath} markerEnd={markerEnd} style={style} />
      {data?.active && (
        <circle r="4" fill="#0bcad9">
          <animateMotion dur="1.5s" repeatCount="indefinite" path={edgePath} />
        </circle>
      )}
    </>
  );
};

const edgeTypes = {
  dataflow: DataFlowEdge,
};

const VendorNode = ({ data, selected }: NodeProps) => {
  return (
    <div className={cn(
      "flex items-center gap-3 p-3 rounded-lg border bg-slate-900/90 w-52 transition-all shadow-lg",
      selected ? "border-primary shadow-[0_0_15px_-3px_rgba(11,202,217,0.4)]" : "border-slate-800 hover:border-slate-700",
      data.active ? "border-primary/50 shadow-[0_0_10px_-3px_rgba(11,202,217,0.3)]" : ""
    )}>
      <Handle type="source" position={Position.Right} className="!bg-slate-600 !w-2 !h-2" />
      <div className={cn("p-2 rounded bg-slate-950/50", data.color)}>
        {data.icon}
      </div>
      <div className="text-left">
        <div className="text-sm font-medium text-slate-200">{data.label}</div>
        <div className="text-[10px] text-slate-500">{data.sub}</div>
      </div>
    </div>
  );
};

const ProcessingNode = ({ data, selected }: NodeProps) => {
  const isHex = data.shape === 'hexagon';
  
  return (
    <div className="relative flex items-center justify-center">
      <Handle type="target" position={Position.Left} className="!bg-slate-600 !w-2 !h-2 -ml-1" />
      <div 
        className={cn(
          "flex flex-col items-center justify-center gap-2 transition-all bg-slate-900/90 border-2 shadow-xl backdrop-blur-md",
          isHex ? "w-32 h-32" : "w-32 h-32 rounded-full",
          selected ? "border-primary shadow-[0_0_20px_-5px_rgba(11,202,217,0.5)]" : "border-slate-700",
          data.active ? "border-primary shadow-[0_0_20px_-5px_rgba(11,202,217,0.5)]" : "",
          data.complete ? "border-green-500 shadow-[0_0_15px_-5px_rgba(34,197,94,0.5)]" : ""
        )}
        style={isHex ? { clipPath: "polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%)" } : {}}
      >
        <div className={cn(
            "transition-colors duration-300",
            data.active ? "text-white scale-110" : "text-slate-400",
            data.complete ? "text-green-400" : ""
        )}>
          {data.icon}
        </div>
        <div className="text-center z-10">
          <div className="text-xs font-bold text-slate-200">{data.label}</div>
          <div className="text-[9px] text-slate-500 uppercase tracking-wider">{data.sub}</div>
        </div>
        
        {data.active && (
           <div className={cn(
             "absolute inset-0 z-0 animate-ping opacity-20 bg-primary",
             isHex ? "" : "rounded-full"
           )} style={isHex ? { clipPath: "polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%)" } : {}} />
        )}
      </div>
      <Handle type="source" position={Position.Right} className="!bg-slate-600 !w-2 !h-2 -mr-1" />
    </div>
  );
};

const nodeTypes = {
  vendor: VendorNode,
  processing: ProcessingNode,
};

const initialNodes: Node[] = [
  { id: 'salesforce', type: 'vendor', position: { x: 50, y: 50 }, data: { label: 'Salesforce', sub: '35 Assets', icon: <Globe className="w-5 h-5" />, color: 'text-blue-400' } },
  { id: 'mongodb', type: 'vendor', position: { x: 50, y: 150 }, data: { label: 'MongoDB', sub: '28 Assets', icon: <Database className="w-5 h-5" />, color: 'text-green-500' } },
  { id: 'supabase', type: 'vendor', position: { x: 50, y: 250 }, data: { label: 'Supabase', sub: '42 Assets', icon: <Server className="w-5 h-5" />, color: 'text-emerald-400' } },
  { id: 'legacy', type: 'vendor', position: { x: 50, y: 350 }, data: { label: 'Legacy Files', sub: '12 Assets', icon: <FileText className="w-5 h-5" />, color: 'text-orange-400' } },
  { id: 'aod', type: 'processing', position: { x: 350, y: 200 }, data: { label: 'AOD', sub: 'Discovery', icon: <Search className="w-6 h-6" />, shape: 'circle' } },
  { id: 'aam', type: 'processing', position: { x: 600, y: 200 }, data: { label: 'AAM', sub: 'API Mesh', icon: <Plug className="w-6 h-6" />, shape: 'circle' } },
  { id: 'dcl', type: 'processing', position: { x: 850, y: 200 }, data: { label: 'DCL', sub: 'Connectivity', icon: <Network className="w-6 h-6" />, shape: 'hexagon' } },
  { id: 'agents', type: 'processing', position: { x: 1100, y: 200 }, data: { label: 'Agents', sub: 'Intelligence', icon: <Sparkles className="w-6 h-6" />, shape: 'circle' } },
];

const initialEdges: Edge[] = [
  { id: 'e-sf-aod', source: 'salesforce', target: 'aod', type: 'dataflow', animated: false, style: { stroke: '#334155', strokeWidth: 2 } },
  { id: 'e-mg-aod', source: 'mongodb', target: 'aod', type: 'dataflow', animated: false, style: { stroke: '#334155', strokeWidth: 2 } },
  { id: 'e-sb-aod', source: 'supabase', target: 'aod', type: 'dataflow', animated: false, style: { stroke: '#334155', strokeWidth: 2 } },
  { id: 'e-lg-aod', source: 'legacy', target: 'aod', type: 'dataflow', animated: false, style: { stroke: '#334155', strokeWidth: 2 } },
  { id: 'e-aod-aam', source: 'aod', target: 'aam', type: 'dataflow', animated: false, style: { stroke: '#334155', strokeWidth: 2 } },
  { id: 'e-aam-dcl', source: 'aam', target: 'dcl', type: 'dataflow', animated: false, style: { stroke: '#334155', strokeWidth: 2 } },
  { id: 'e-dcl-ag', source: 'dcl', target: 'agents', type: 'dataflow', animated: false, style: { stroke: '#334155', strokeWidth: 2 } },
];

interface GraphViewProps {
  pipelineStep: number;
  pipelineState: "idle" | "running" | "complete";
  onNodeClick?: (nodeId: string, type: string) => void;
}

function GraphView({ pipelineStep, pipelineState, onNodeClick }: GraphViewProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  useEffect(() => {
    const isRunning = pipelineState === 'running';
    const isComplete = pipelineState === 'complete';

    setNodes((nds) => 
      nds.map((node) => {
        let active = false;
        let complete = false;

        if (isComplete) {
           complete = true;
        } else if (isRunning) {
           if (pipelineStep === 0 && node.id === 'aod') active = true;
           if (pipelineStep === 1 && node.id === 'aam') active = true;
           if (pipelineStep === 2 && node.id === 'dcl') active = true;
           if (pipelineStep === 3 && node.id === 'agents') active = true;
           
           if (pipelineStep > 0 && node.id === 'aod') complete = true;
           if (pipelineStep > 1 && node.id === 'aam') complete = true;
           if (pipelineStep > 2 && node.id === 'dcl') complete = true;
        }

        return { ...node, data: { ...node.data, active, complete } };
      })
    );

    setEdges((eds) => 
      eds.map((edge) => {
         let active = false;
         let stroke = '#334155';
         
         if (isComplete) {
            stroke = '#0bcad9';
         } else if (isRunning) {
            if (pipelineStep === 0 && edge.target === 'aod') { active = true; stroke = '#0bcad9'; }
            if (pipelineStep === 1 && edge.source === 'aod' && edge.target === 'aam') { active = true; stroke = '#0bcad9'; }
            if (pipelineStep === 2 && edge.source === 'aam' && edge.target === 'dcl') { active = true; stroke = '#0bcad9'; }
            if (pipelineStep === 3 && edge.source === 'dcl' && edge.target === 'agents') { active = true; stroke = '#0bcad9'; }
            
            if (pipelineStep > 0 && edge.target === 'aod') stroke = '#0bcad9';
            if (pipelineStep > 1 && edge.target === 'aam') stroke = '#0bcad9';
            if (pipelineStep > 2 && edge.target === 'dcl') stroke = '#0bcad9';
         }

         return { ...edge, data: { ...edge.data, active }, style: { stroke, strokeWidth: 2 } };
      })
    );
  }, [pipelineStep, pipelineState, setNodes, setEdges]);

  const handleNodeClick = useCallback((event: React.MouseEvent, node: Node) => {
    if (onNodeClick) onNodeClick(node.id, node.type || 'default');
  }, [onNodeClick]);

  return (
    <div className="w-full h-full bg-slate-950/50 rounded-xl border border-slate-800/50 overflow-hidden relative">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        attributionPosition="bottom-right"
        minZoom={0.5}
        maxZoom={1.5}
        defaultEdgeOptions={{ type: 'dataflow', markerEnd: { type: MarkerType.ArrowClosed, color: '#334155' } }}
      >
        <Background color="#1e293b" gap={20} size={1} />
        <Controls className="bg-slate-800 border-slate-700 text-slate-200" />
      </ReactFlow>
    </div>
  );
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export default function DiscoveryDemoStandalone() {
  const [currentStage, setCurrentStage] = useState<Stage>(1);
  const [isRunningPipeline, setIsRunningPipeline] = useState(false);

  const handleRunFullPipeline = () => {
    setCurrentStage(1);
    setIsRunningPipeline(true);
  };

  const handleContinuePipeline = () => {
    if (currentStage < 4) {
      setCurrentStage((prev) => (prev + 1) as Stage);
    } else {
      setIsRunningPipeline(false);
    }
  };

  const handleEndDemo = () => {
    setIsRunningPipeline(false);
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

  const totalCounts = getTotalCounts();
  const pipelineStep = currentStage - 1;
  const pipelineState = isRunningPipeline ? "running" : "idle";

  return (
    <div className="flex flex-col h-screen bg-slate-950 text-white" style={{ fontFamily: 'Quicksand, sans-serif' }}>
      {/* Top Bar */}
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

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Graph Panel - 2/3 width */}
        <div className="w-2/3 border-r border-slate-800 p-8 bg-slate-950 overflow-hidden">
          <h2 className="text-2xl font-bold text-white mb-8">Pipeline Graph</h2>
          <div className="flex-1 h-full">
            <GraphView 
              pipelineStep={pipelineStep} 
              pipelineState={pipelineState}
              onNodeClick={(id) => console.log("Clicked:", id)} 
            />
          </div>
        </div>

        {/* Detail Panel - 1/3 width */}
        <div className="w-1/3 p-8 bg-slate-900 overflow-auto">
          {currentStage === 1 && <Stage1Content totalCounts={totalCounts} />}
          {currentStage === 2 && <Stage2Content />}
          {currentStage === 3 && <Stage3Content />}
          {currentStage === 4 && <Stage4Content />}
        </div>
      </div>

      {/* Bottom Navigation */}
      <div className="bg-slate-900 border-t border-slate-800 px-6 py-6">
        <StepperNavigation
          currentStage={currentStage}
          onStageClick={handleStageClick}
          onBack={handleBack}
          onNext={handleNext}
          onRunFullPipeline={handleRunFullPipeline}
          onContinuePipeline={handleContinuePipeline}
          onEndDemo={handleEndDemo}
          isRunningPipeline={isRunningPipeline}
        />
      </div>
    </div>
  );
}

// ============================================================================
// STAGE CONTENT COMPONENTS
// ============================================================================

function Stage1Content({ totalCounts }: { totalCounts: any }) {
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

function Stage2Content() {
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

function Stage3Content() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-white mb-2 break-words">DCL Mapping — Unified Entity</h2>
        <p className="text-xs text-slate-400 break-words">Schema mappings from multiple sources</p>
      </div>

      <div className="bg-purple-500/10 border border-purple-500/30 rounded-lg p-3 text-xs text-purple-300 break-words">
        DCL builds a unified customer_360 entity from Salesforce, MongoDB, Supabase, and Legacy Files.
      </div>

      <div className="bg-slate-800 border border-slate-700 rounded-lg overflow-x-auto">
        <table className="w-full min-w-max">
          <thead className="bg-slate-900 border-b border-slate-700">
            <tr>
              <th className="text-left px-2 py-2 text-[10px] font-semibold text-slate-400 uppercase">Field</th>
              <th className="text-left px-2 py-2 text-[10px] font-semibold text-slate-400 uppercase">Type</th>
              <th className="text-left px-2 py-2 text-[10px] font-semibold text-slate-400 uppercase">Sources</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700">
            {demoCustomer360Mappings.slice(0, 6).map((mapping) => (
              <tr key={mapping.canonicalField} className="hover:bg-slate-700/50">
                <td className="px-2 py-2">
                  <code className="text-cyan-400 font-mono text-xs">{mapping.canonicalField}</code>
                </td>
                <td className="px-2 py-2 text-xs text-slate-400">{mapping.type}</td>
                <td className="px-2 py-2 text-xs text-slate-500 break-words">{mapping.sources}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Stage4Content() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-white mb-2 break-words">Agent Execution — Query Results</h2>
        <p className="text-xs text-slate-400 break-words">AI agent analyzing unified data</p>
      </div>

      <div className="bg-slate-800 border border-slate-700 rounded-lg p-3">
        <div className="text-xs text-slate-400 mb-2">Query:</div>
        <code className="text-xs text-cyan-400 break-words">
          "Show me high-risk services with annual revenue > $1M"
        </code>
      </div>

      <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-3">
        <div className="text-xs text-green-300 break-words">
          <span className="font-semibold">Results:</span> Found 4 high-risk services totaling $8.5M ARR
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
  onContinuePipeline,
  onEndDemo,
  isRunningPipeline,
}: {
  currentStage: Stage;
  onStageClick: (stage: Stage) => void;
  onBack: () => void;
  onNext: () => void;
  onRunFullPipeline: () => void;
  onContinuePipeline: () => void;
  onEndDemo: () => void;
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
              disabled={isRunningPipeline}
              className={`flex flex-col items-center gap-2 px-6 py-3 rounded-lg transition-all ${
                currentStage === stage.num
                  ? 'bg-cyan-500/20 border-2 border-cyan-500'
                  : 'bg-slate-800 border-2 border-slate-700 hover:border-slate-600'
              } ${isRunningPipeline ? 'opacity-50 cursor-not-allowed' : ''}`}
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

      {isRunningPipeline ? (
        <div className="bg-gradient-to-r from-cyan-500/10 to-purple-500/10 border border-cyan-500/30 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <Zap className="w-5 h-5 text-cyan-400 animate-pulse" />
                <h3 className="text-lg font-bold text-white">Pipeline Running - Stage {currentStage} of 4</h3>
              </div>
              <p className="text-sm text-slate-400">
                {currentStage < 4 
                  ? "Review the information on the right panel. Click 'Continue' to proceed to the next stage." 
                  : "Demo complete! Review the final results or restart the pipeline."}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={onEndDemo}
                className="px-6 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors font-semibold"
              >
                End Demo
              </button>
              {currentStage < 4 ? (
                <button
                  onClick={onContinuePipeline}
                  className="px-6 py-2 bg-green-600 hover:bg-green-500 text-white rounded-lg transition-colors font-semibold flex items-center gap-2"
                >
                  Continue to Next Stage
                  <ChevronRight className="w-4 h-4" />
                </button>
              ) : (
                <button
                  onClick={onRunFullPipeline}
                  className="px-6 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg transition-colors font-semibold flex items-center gap-2"
                >
                  <Play className="w-4 h-4" />
                  Restart Pipeline
                </button>
              )}
            </div>
          </div>
        </div>
      ) : (
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
            className="px-6 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg transition-colors font-semibold flex items-center gap-2"
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
      )}
    </div>
  );
}
