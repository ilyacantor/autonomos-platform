import { ArrowRight, ArrowDown, Database, Layers, GitBranch, Zap, CheckCircle } from 'lucide-react';

export default function AutonomOSArchitectureFlow() {
  return (
    <div className="relative px-4 sm:px-6 py-6 sm:py-8 safe-x">
      {/* Main Container with border */}
      <div className="max-w-7xl mx-auto border-2 border-cyan-500/30 rounded-lg p-4 sm:p-6 bg-gradient-to-b from-slate-900/30 to-transparent relative">
        {/* Title integrated into border line */}
        <span className="absolute -top-3 left-4 sm:left-6 px-3 text-sm sm:text-base font-normal text-cyan-400 bg-slate-950">
          autonomOS Orchestration Platform
        </span>
        {/* Horizontal Flow: Enterprise Data → AAM → DCL → Agents */}
        <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_1fr_auto_1fr_auto_1fr] gap-4 items-center mb-8">
          {/* Enterprise Data */}
          <div className="w-full max-w-[280px] mx-auto aspect-square bg-slate-800/80 border border-slate-600/50 rounded-lg p-4 flex flex-col justify-between overflow-hidden">
            <div className="flex items-center gap-2 mb-2 justify-center flex-shrink-0">
              <Database className="w-4 h-4 text-white flex-shrink-0" />
              <h3 className="text-sm font-medium text-white text-center">
                Enterprise Data
              </h3>
            </div>
            <div className="flex flex-wrap gap-1.5 justify-center overflow-y-auto max-h-[calc(100%-3rem)] px-1">
              <span className="inline-block px-2 py-1 rounded-full border border-slate-500/50 text-[10px] text-gray-300 bg-slate-700/30 whitespace-nowrap">
                SaaS Applications
              </span>
              <span className="inline-block px-2 py-1 rounded-full border border-slate-500/50 text-[10px] text-gray-300 bg-slate-700/30 whitespace-nowrap">
                Databases
              </span>
              <span className="inline-block px-2 py-1 rounded-full border border-slate-500/50 text-[10px] text-gray-300 bg-slate-700/30 whitespace-nowrap">
                Warehouses
              </span>
              <span className="inline-block px-2 py-1 rounded-full border border-slate-500/50 text-[10px] text-gray-300 bg-slate-700/30 whitespace-nowrap">
                Legacy Systems
              </span>
              <span className="inline-block px-2 py-1 rounded-full border border-slate-500/50 text-[10px] text-gray-300 bg-slate-700/30 whitespace-nowrap">
                APIs & Files
              </span>
            </div>
          </div>

          {/* Arrow 1 - Desktop Horizontal, Mobile Vertical */}
          <div className="hidden md:flex justify-center">
            <ArrowRight className="w-8 h-8 text-cyan-400" />
          </div>
          <div className="flex md:hidden justify-center py-2">
            <ArrowDown className="w-6 h-6 text-cyan-400" />
          </div>

          {/* Adaptive API Mesh (AAM) - Clickable */}
          <button
            onClick={() => {
              const aamContainer = document.getElementById('aam-container');
              if (aamContainer) {
                aamContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
              }
            }}
            className="w-full max-w-[280px] mx-auto aspect-square bg-gradient-to-br from-cyan-900/40 to-slate-800/80 border border-cyan-500/50 hover:border-cyan-400 rounded-lg p-4 flex flex-col justify-between transition-all hover:scale-105 hover:shadow-lg hover:shadow-cyan-500/20 cursor-pointer group mobile-tap-highlight touch-target-h overflow-hidden"
          >
            <div className="flex items-center gap-2 mb-2 justify-center flex-shrink-0">
              <GitBranch className="w-4 h-4 text-cyan-400 group-hover:text-cyan-300 flex-shrink-0" />
              <h3 className="text-sm font-medium text-cyan-400 group-hover:text-cyan-300 text-center">
                Adaptive API Mesh (AAM)
              </h3>
            </div>
            <div className="flex flex-wrap gap-1.5 justify-center overflow-y-auto max-h-[calc(100%-4rem)] px-1 mb-2">
              <span className="inline-block px-2 py-1 rounded-full border border-cyan-500/50 text-[10px] text-gray-300 bg-cyan-900/30 whitespace-nowrap">
                Self-Healing
              </span>
              <span className="inline-block px-2 py-1 rounded-full border border-cyan-500/50 text-[10px] text-gray-300 bg-cyan-900/30 whitespace-nowrap">
                Drift Repair
              </span>
              <span className="inline-block px-2 py-1 rounded-full border border-cyan-500/50 text-[10px] text-gray-300 bg-cyan-900/30 whitespace-nowrap">
                Schema Normalization
              </span>
              <span className="inline-block px-2 py-1 rounded-full border border-cyan-500/50 text-[10px] text-gray-300 bg-cyan-900/30 whitespace-nowrap">
                Universal Connectivity
              </span>
              <span className="inline-block px-2 py-1 rounded-full border border-cyan-500/50 text-[10px] text-gray-300 bg-cyan-900/30 whitespace-nowrap">
                Data Exchange
              </span>
            </div>
            <div className="text-center text-[10px] text-cyan-300 opacity-0 md:group-hover:opacity-100 transition-opacity flex-shrink-0">
              ↑ View Details
            </div>
          </button>

          {/* Arrow 2 - Desktop Horizontal, Mobile Vertical */}
          <div className="hidden md:flex justify-center">
            <ArrowRight className="w-8 h-8 text-cyan-400" />
          </div>
          <div className="flex md:hidden justify-center py-2">
            <ArrowDown className="w-6 h-6 text-cyan-400" />
          </div>

          {/* Data Connectivity Layer (DCL) - Clickable */}
          <button
            onClick={() => {
              const dclContainer = document.getElementById('dcl-graph-container');
              if (dclContainer) {
                dclContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
              }
            }}
            className="w-full max-w-[280px] mx-auto aspect-square bg-gradient-to-br from-blue-900/40 to-slate-800/80 border border-blue-500/50 hover:border-blue-400 rounded-lg p-4 flex flex-col justify-between transition-all hover:scale-105 hover:shadow-lg hover:shadow-blue-500/20 cursor-pointer group mobile-tap-highlight touch-target-h overflow-hidden"
          >
            <div className="flex items-center gap-2 mb-2 justify-center flex-shrink-0">
              <Layers className="w-4 h-4 text-blue-400 group-hover:text-blue-300 flex-shrink-0" />
              <h3 className="text-sm font-medium text-blue-400 group-hover:text-blue-300 text-center">
                Data Connectivity Layer
              </h3>
            </div>
            <div className="flex flex-wrap gap-1.5 justify-center overflow-y-auto max-h-[calc(100%-4rem)] px-1 mb-2">
              <span className="inline-block px-2 py-1 rounded-full border border-blue-500/50 text-[10px] text-gray-300 bg-blue-900/30 whitespace-nowrap">
                Unified Ontology
              </span>
              <span className="inline-block px-2 py-1 rounded-full border border-blue-500/50 text-[10px] text-gray-300 bg-blue-900/30 whitespace-nowrap">
                Semantic Engine
              </span>
              <span className="inline-block px-2 py-1 rounded-full border border-blue-500/50 text-[10px] text-gray-300 bg-blue-900/30 whitespace-nowrap">
                AI-Ready Streams
              </span>
              <span className="inline-block px-2 py-1 rounded-full border border-blue-500/50 text-[10px] text-gray-300 bg-blue-900/30 whitespace-nowrap">
                RAG Indexing
              </span>
              <span className="inline-block px-2 py-1 rounded-full border border-blue-500/50 text-[10px] text-gray-300 bg-blue-900/30 whitespace-nowrap">
                Observability
              </span>
            </div>
            <div className="text-center text-[10px] text-blue-300 opacity-0 md:group-hover:opacity-100 transition-opacity flex-shrink-0">
              ↑ Try Demo
            </div>
          </button>

          {/* Arrow 3 - Desktop Horizontal, Mobile Vertical */}
          <div className="hidden md:flex justify-center">
            <ArrowRight className="w-8 h-8 text-blue-400" />
          </div>
          <div className="flex md:hidden justify-center py-2">
            <ArrowDown className="w-6 h-6 text-blue-400" />
          </div>

          {/* Prebuilt Domain Agents - Clickable */}
          <button
            onClick={() => {
              const agentPerformance = document.getElementById('agent-performance-monitor');
              if (agentPerformance) {
                agentPerformance.scrollIntoView({ behavior: 'smooth', block: 'start' });
              }
            }}
            className="w-full max-w-[280px] mx-auto aspect-square bg-gradient-to-br from-purple-900/40 to-slate-800/80 border border-purple-500/50 hover:border-purple-400 rounded-lg p-4 flex flex-col justify-between transition-all hover:scale-105 hover:shadow-lg hover:shadow-purple-500/20 cursor-pointer group mobile-tap-highlight touch-target-h overflow-hidden"
          >
            <div className="flex items-center gap-2 mb-2 justify-center flex-shrink-0">
              <Zap className="w-4 h-4 text-purple-400 group-hover:text-purple-300 flex-shrink-0" />
              <h3 className="text-sm font-medium text-purple-400 group-hover:text-purple-300 text-center">
                Prebuilt Domain Agents
              </h3>
            </div>
            <div className="flex flex-wrap gap-1.5 justify-center overflow-y-auto max-h-[calc(100%-4rem)] px-1 mb-2">
              <span className="inline-block px-2 py-1 rounded-full border border-purple-500/50 text-[10px] text-gray-300 bg-purple-900/30 whitespace-nowrap">
                Domain Expertise
              </span>
              <span className="inline-block px-2 py-1 rounded-full border border-purple-500/50 text-[10px] text-gray-300 bg-purple-900/30 whitespace-nowrap">
                FinOps/RevOps
              </span>
              <span className="inline-block px-2 py-1 rounded-full border border-purple-500/50 text-[10px] text-gray-300 bg-purple-900/30 whitespace-nowrap">
                Workflow Orchestration
              </span>
              <span className="inline-block px-2 py-1 rounded-full border border-purple-500/50 text-[10px] text-gray-300 bg-purple-900/30 whitespace-nowrap">
                Custom Deployment
              </span>
            </div>
            <div className="text-center text-[10px] text-purple-300 opacity-0 md:group-hover:opacity-100 transition-opacity flex-shrink-0">
              ↓ View Performance
            </div>
          </button>
        </div>

        {/* Vertical Arrow from Agents to Outcomes */}
        <div className="flex justify-center mb-6 sm:mb-8">
          <ArrowDown className="w-6 h-6 sm:w-8 sm:h-8 text-cyan-400" />
        </div>

        {/* Outcomes - centered below */}
        <div className="flex justify-center">
          <div className="w-full md:w-auto md:max-w-[400px] aspect-[2/1] bg-gradient-to-br from-cyan-900/40 to-slate-800/80 border border-cyan-500/50 rounded-lg p-4 flex flex-col justify-between overflow-hidden">
            <div className="flex items-center gap-2 mb-2 justify-center flex-shrink-0">
              <CheckCircle className="w-4 h-4 text-cyan-400 flex-shrink-0" />
              <h3 className="text-sm font-medium text-cyan-400">
                Outcomes
              </h3>
            </div>
            <div className="flex flex-wrap gap-1.5 justify-center overflow-y-auto max-h-[calc(100%-3rem)] px-1">
              <span className="inline-block px-2 py-1 rounded-full border border-cyan-500/50 text-[10px] text-gray-300 bg-cyan-900/30 whitespace-nowrap">
                Intent-Driven Operations
              </span>
              <span className="inline-block px-2 py-1 rounded-full border border-cyan-500/50 text-[10px] text-gray-300 bg-cyan-900/30 whitespace-nowrap">
                Autonomous Execution
              </span>
              <span className="inline-block px-2 py-1 rounded-full border border-cyan-500/50 text-[10px] text-gray-300 bg-cyan-900/30 whitespace-nowrap">
                Insight-to-Action
              </span>
              <span className="inline-block px-2 py-1 rounded-full border border-cyan-500/50 text-[10px] text-gray-300 bg-cyan-900/30 whitespace-nowrap">
                Data Reliability
              </span>
              <span className="inline-block px-2 py-1 rounded-full border border-cyan-500/50 text-[10px] text-gray-300 bg-cyan-900/30 whitespace-nowrap">
                Decision Intelligence
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
