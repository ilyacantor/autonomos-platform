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
          <div className="bg-slate-800/80 border border-slate-600/50 rounded-lg p-4 sm:p-6 h-full min-h-[220px] md:min-h-[260px] flex flex-col justify-center overflow-hidden">
            <div className="flex items-center gap-2 mb-3 sm:mb-4 justify-center">
              <Database className="w-4 h-4 sm:w-5 sm:h-5 text-white" />
              <h3 className="text-base sm:text-lg font-medium text-white">
                Enterprise Data
              </h3>
            </div>
            <div className="mobile-scroll-x md:flex md:flex-wrap gap-2 md:justify-center pb-2 md:pb-0 -mx-4 px-4 md:mx-0 md:px-0">
              <div className="flex md:flex-wrap gap-2 md:justify-center whitespace-nowrap md:whitespace-normal">
                <span className="inline-block px-2.5 sm:px-3 py-1 sm:py-1.5 rounded-full border border-slate-500/50 text-xs text-gray-300 bg-slate-700/30">
                  SaaS Applications
                </span>
                <span className="inline-block px-2.5 sm:px-3 py-1 sm:py-1.5 rounded-full border border-slate-500/50 text-xs text-gray-300 bg-slate-700/30">
                  Databases & Warehouses
                </span>
                <span className="inline-block px-2.5 sm:px-3 py-1 sm:py-1.5 rounded-full border border-slate-500/50 text-xs text-gray-300 bg-slate-700/30">
                  Legacy Systems
                </span>
                <span className="inline-block px-2.5 sm:px-3 py-1 sm:py-1.5 rounded-full border border-slate-500/50 text-xs text-gray-300 bg-slate-700/30">
                  APIs & Files
                </span>
              </div>
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
            className="bg-gradient-to-br from-cyan-900/40 to-slate-800/80 border border-cyan-500/50 hover:border-cyan-400 rounded-lg p-4 sm:p-6 h-full min-h-[220px] md:min-h-[260px] flex flex-col justify-center transition-all hover:scale-105 hover:shadow-lg hover:shadow-cyan-500/20 cursor-pointer group mobile-tap-highlight touch-target-h overflow-hidden"
          >
            <div className="flex items-center gap-2 mb-3 sm:mb-4 justify-center">
              <GitBranch className="w-4 h-4 sm:w-5 sm:h-5 text-cyan-400 group-hover:text-cyan-300" />
              <h3 className="text-base sm:text-lg font-medium text-cyan-400 group-hover:text-cyan-300">
                Adaptive API Mesh (AAM)
              </h3>
            </div>
            <div className="mobile-scroll-x md:flex md:flex-wrap gap-2 md:justify-center mb-2 sm:mb-3 pb-2 md:pb-0 -mx-4 px-4 md:mx-0 md:px-0">
              <div className="flex md:flex-wrap gap-2 md:justify-center whitespace-nowrap md:whitespace-normal">
                <span className="inline-block px-2.5 sm:px-3 py-1 sm:py-1.5 rounded-full border border-cyan-500/50 text-xs text-gray-300 bg-cyan-900/30">
                  Self-Healing Integration
                </span>
                <span className="inline-block px-2.5 sm:px-3 py-1 sm:py-1.5 rounded-full border border-cyan-500/50 text-xs text-gray-300 bg-cyan-900/30">
                  Autonomous Drift Repair
                </span>
                <span className="inline-block px-2.5 sm:px-3 py-1 sm:py-1.5 rounded-full border border-cyan-500/50 text-xs text-gray-300 bg-cyan-900/30">
                  Real-time Schema Normalization
                </span>
                <span className="inline-block px-2.5 sm:px-3 py-1 sm:py-1.5 rounded-full border border-cyan-500/50 text-xs text-gray-300 bg-cyan-900/30">
                  Universal Connectivity
                </span>
                <span className="inline-block px-2.5 sm:px-3 py-1 sm:py-1.5 rounded-full border border-cyan-500/50 text-xs text-gray-300 bg-cyan-900/30">
                  Governed Data Exchange
                </span>
              </div>
            </div>
            <div className="text-center text-xs text-cyan-300 opacity-0 md:group-hover:opacity-100 transition-opacity">
              ↑ View AAM Details
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
            className="bg-gradient-to-br from-blue-900/40 to-slate-800/80 border border-blue-500/50 hover:border-blue-400 rounded-lg p-4 sm:p-6 h-full min-h-[220px] md:min-h-[260px] flex flex-col justify-center transition-all hover:scale-105 hover:shadow-lg hover:shadow-blue-500/20 cursor-pointer group mobile-tap-highlight touch-target-h overflow-hidden"
          >
            <div className="flex items-center gap-2 mb-3 sm:mb-4 justify-center">
              <Layers className="w-4 h-4 sm:w-5 sm:h-5 text-blue-400 group-hover:text-blue-300" />
              <h3 className="text-base sm:text-lg font-medium text-blue-400 group-hover:text-blue-300">
                Data Connectivity Layer
              </h3>
            </div>
            <div className="mobile-scroll-x md:flex md:flex-wrap gap-2 md:justify-center mb-2 sm:mb-3 pb-2 md:pb-0 -mx-4 px-4 md:mx-0 md:px-0">
              <div className="flex md:flex-wrap gap-2 md:justify-center whitespace-nowrap md:whitespace-normal">
                <span className="inline-block px-2.5 sm:px-3 py-1 sm:py-1.5 rounded-full border border-blue-500/50 text-xs text-gray-300 bg-blue-900/30">
                  Unified Enterprise Ontology
                </span>
                <span className="inline-block px-2.5 sm:px-3 py-1 sm:py-1.5 rounded-full border border-blue-500/50 text-xs text-gray-300 bg-blue-900/30">
                  Semantic Context Engine
                </span>
                <span className="inline-block px-2.5 sm:px-3 py-1 sm:py-1.5 rounded-full border border-blue-500/50 text-xs text-gray-300 bg-blue-900/30">
                  AI-Ready Data Streams
                </span>
                <span className="inline-block px-2.5 sm:px-3 py-1 sm:py-1.5 rounded-full border border-blue-500/50 text-xs text-gray-300 bg-blue-900/30">
                  Contextual RAG Indexing
                </span>
                <span className="inline-block px-2.5 sm:px-3 py-1 sm:py-1.5 rounded-full border border-blue-500/50 text-xs text-gray-300 bg-blue-900/30">
                  Real-time Observability
                </span>
              </div>
            </div>
            <div className="text-center text-xs text-blue-300 opacity-0 md:group-hover:opacity-100 transition-opacity">
              ↑ Try Interactive Demo
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
            className="bg-gradient-to-br from-purple-900/40 to-slate-800/80 border border-purple-500/50 hover:border-purple-400 rounded-lg p-4 sm:p-6 h-full min-h-[220px] md:min-h-[260px] flex flex-col justify-center transition-all hover:scale-105 hover:shadow-lg hover:shadow-purple-500/20 cursor-pointer group mobile-tap-highlight touch-target-h overflow-hidden"
          >
            <div className="flex items-center gap-2 mb-3 sm:mb-4 justify-center">
              <Zap className="w-4 h-4 sm:w-5 sm:h-5 text-purple-400 group-hover:text-purple-300" />
              <h3 className="text-base sm:text-lg font-medium text-purple-400 group-hover:text-purple-300">
                Prebuilt Domain Agents
              </h3>
            </div>
            <div className="mobile-scroll-x md:flex md:flex-wrap gap-2 md:justify-center mb-2 sm:mb-3 pb-2 md:pb-0 -mx-4 px-4 md:mx-0 md:px-0">
              <div className="flex md:flex-wrap gap-2 md:justify-center whitespace-nowrap md:whitespace-normal">
                <span className="inline-block px-2.5 sm:px-3 py-1 sm:py-1.5 rounded-full border border-purple-500/50 text-xs text-gray-300 bg-purple-900/30">
                  Productized Domain Expertise
                </span>
                <span className="inline-block px-2.5 sm:px-3 py-1 sm:py-1.5 rounded-full border border-purple-500/50 text-xs text-gray-300 bg-purple-900/30">
                  FinOps/RevOps Blueprints
                </span>
                <span className="inline-block px-2.5 sm:px-3 py-1 sm:py-1.5 rounded-full border border-purple-500/50 text-xs text-gray-300 bg-purple-900/30">
                  Autonomous Workflow Orchestration
                </span>
                <span className="inline-block px-2.5 sm:px-3 py-1 sm:py-1.5 rounded-full border border-purple-500/50 text-xs text-gray-300 bg-purple-900/30">
                  Custom Agent Deployment
                </span>
              </div>
            </div>
            <div className="text-center text-xs text-purple-300 opacity-0 md:group-hover:opacity-100 transition-opacity">
              ↓ View Agent Performance
            </div>
          </button>
        </div>

        {/* Vertical Arrow from Agents to Outcomes */}
        <div className="flex justify-center mb-6 sm:mb-8">
          <ArrowDown className="w-6 h-6 sm:w-8 sm:h-8 text-cyan-400" />
        </div>

        {/* Outcomes - centered below */}
        <div className="flex justify-center">
          <div className="w-full md:w-auto bg-gradient-to-br from-cyan-900/40 to-slate-800/80 border border-cyan-500/50 rounded-lg p-4 sm:p-6 min-h-[200px] md:min-h-[220px] flex flex-col justify-center overflow-hidden">
            <div className="flex items-center gap-2 mb-3 sm:mb-4 justify-center">
              <CheckCircle className="w-4 h-4 sm:w-5 sm:h-5 text-cyan-400" />
              <h3 className="text-base sm:text-lg font-medium text-cyan-400">
                Outcomes
              </h3>
            </div>
            <div className="mobile-scroll-x md:flex md:flex-wrap gap-2 md:justify-center pb-2 md:pb-0 -mx-4 px-4 md:mx-0 md:px-0">
              <div className="flex md:flex-wrap gap-2 md:justify-center whitespace-nowrap md:whitespace-normal">
                <span className="inline-block px-2.5 sm:px-3 py-1 sm:py-1.5 rounded-full border border-cyan-500/50 text-xs text-gray-300 bg-cyan-900/30">
                  Intent-Driven Operations
                </span>
                <span className="inline-block px-2.5 sm:px-3 py-1 sm:py-1.5 rounded-full border border-cyan-500/50 text-xs text-gray-300 bg-cyan-900/30">
                  Autonomous Execution
                </span>
                <span className="inline-block px-2.5 sm:px-3 py-1 sm:py-1.5 rounded-full border border-cyan-500/50 text-xs text-gray-300 bg-cyan-900/30">
                  Insight-to-Action Acceleration
                </span>
                <span className="inline-block px-2.5 sm:px-3 py-1 sm:py-1.5 rounded-full border border-cyan-500/50 text-xs text-gray-300 bg-cyan-900/30">
                  Guaranteed Data Reliability
                </span>
                <span className="inline-block px-2.5 sm:px-3 py-1 sm:py-1.5 rounded-full border border-cyan-500/50 text-xs text-gray-300 bg-cyan-900/30">
                  Proactive Decision Intelligence
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
