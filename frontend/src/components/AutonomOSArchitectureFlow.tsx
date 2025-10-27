import { ArrowRight, ArrowDown, Database, Layers, GitBranch, Zap, CheckCircle } from 'lucide-react';

export default function AutonomOSArchitectureFlow() {
  return (
    <div className="relative px-6 py-8">
      {/* Main Container with border */}
      <div className="max-w-7xl mx-auto border-2 border-cyan-500/30 rounded-lg p-6 bg-gradient-to-b from-slate-900/30 to-transparent relative">
        {/* Title integrated into border line */}
        <span className="absolute -top-3 left-6 px-3 text-base font-normal text-cyan-400 bg-slate-950">
          autonomOS Orchestration Platform
        </span>
        {/* Horizontal Flow: Enterprise Data → AAM → DCL → Agents */}
        <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_1fr_auto_1fr_auto_1fr] gap-4 items-center mb-8">
          {/* Enterprise Data */}
          <div className="bg-slate-800/80 border border-slate-600/50 rounded-lg p-6 h-full flex flex-col justify-center">
            <div className="flex items-center gap-2 mb-4 justify-center">
              <Database className="w-5 h-5 text-white" />
              <h3 className="text-lg font-medium text-white">
                Enterprise Data
              </h3>
            </div>
            <div className="flex flex-wrap gap-2 justify-center">
              <span className="px-3 py-1.5 rounded-full border border-slate-500/50 text-xs text-gray-300 bg-slate-700/30">
                SaaS Applications
              </span>
              <span className="px-3 py-1.5 rounded-full border border-slate-500/50 text-xs text-gray-300 bg-slate-700/30">
                Databases & Warehouses
              </span>
              <span className="px-3 py-1.5 rounded-full border border-slate-500/50 text-xs text-gray-300 bg-slate-700/30">
                Legacy Systems
              </span>
              <span className="px-3 py-1.5 rounded-full border border-slate-500/50 text-xs text-gray-300 bg-slate-700/30">
                APIs & Files
              </span>
            </div>
          </div>

          {/* Arrow 1 */}
          <div className="hidden md:flex justify-center">
            <ArrowRight className="w-8 h-8 text-cyan-400" />
          </div>

          {/* Adaptive API Mesh (AAM) */}
          <div className="bg-gradient-to-br from-cyan-900/40 to-slate-800/80 border border-cyan-500/50 rounded-lg p-6 h-full flex flex-col justify-center">
            <div className="flex items-center gap-2 mb-4 justify-center">
              <GitBranch className="w-5 h-5 text-cyan-400" />
              <h3 className="text-lg font-medium text-cyan-400">
                Adaptive API Mesh (AAM)
              </h3>
            </div>
            <div className="flex flex-wrap gap-2 justify-center">
              <span className="px-3 py-1.5 rounded-full border border-cyan-500/50 text-xs text-gray-300 bg-cyan-900/30">
                Self-Healing Integration
              </span>
              <span className="px-3 py-1.5 rounded-full border border-cyan-500/50 text-xs text-gray-300 bg-cyan-900/30">
                Autonomous Drift Repair
              </span>
              <span className="px-3 py-1.5 rounded-full border border-cyan-500/50 text-xs text-gray-300 bg-cyan-900/30">
                Real-time Schema Normalization
              </span>
              <span className="px-3 py-1.5 rounded-full border border-cyan-500/50 text-xs text-gray-300 bg-cyan-900/30">
                Universal Connectivity
              </span>
              <span className="px-3 py-1.5 rounded-full border border-cyan-500/50 text-xs text-gray-300 bg-cyan-900/30">
                Governed Data Exchange
              </span>
            </div>
          </div>

          {/* Arrow 2 */}
          <div className="hidden md:flex justify-center">
            <ArrowRight className="w-8 h-8 text-cyan-400" />
          </div>

          {/* Data Connectivity Layer (DCL) - Clickable */}
          <button
            onClick={() => {
              const dclContainer = document.getElementById('dcl-graph-container');
              if (dclContainer) {
                dclContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
              }
            }}
            className="bg-gradient-to-br from-blue-900/40 to-slate-800/80 border border-blue-500/50 hover:border-blue-400 rounded-lg p-6 h-full flex flex-col justify-center transition-all hover:scale-105 hover:shadow-lg hover:shadow-blue-500/20 cursor-pointer group"
          >
            <div className="flex items-center gap-2 mb-4 justify-center">
              <Layers className="w-5 h-5 text-blue-400 group-hover:text-blue-300" />
              <h3 className="text-lg font-medium text-blue-400 group-hover:text-blue-300">
                Data Connectivity Layer
              </h3>
            </div>
            <div className="flex flex-wrap gap-2 justify-center mb-3">
              <span className="px-3 py-1.5 rounded-full border border-blue-500/50 text-xs text-gray-300 bg-blue-900/30">
                Unified Enterprise Ontology
              </span>
              <span className="px-3 py-1.5 rounded-full border border-blue-500/50 text-xs text-gray-300 bg-blue-900/30">
                Semantic Context Engine
              </span>
              <span className="px-3 py-1.5 rounded-full border border-blue-500/50 text-xs text-gray-300 bg-blue-900/30">
                AI-Ready Data Streams
              </span>
              <span className="px-3 py-1.5 rounded-full border border-blue-500/50 text-xs text-gray-300 bg-blue-900/30">
                Contextual RAG Indexing
              </span>
              <span className="px-3 py-1.5 rounded-full border border-blue-500/50 text-xs text-gray-300 bg-blue-900/30">
                Real-time Observability
              </span>
            </div>
            <div className="text-center text-xs text-blue-300 opacity-0 group-hover:opacity-100 transition-opacity">
              ↑ Try Interactive Demo
            </div>
          </button>

          {/* Arrow 3 */}
          <div className="hidden md:flex justify-center">
            <ArrowRight className="w-8 h-8 text-blue-400" />
          </div>

          {/* Prebuilt Domain Agents */}
          <div className="bg-gradient-to-br from-purple-900/40 to-slate-800/80 border border-purple-500/50 rounded-lg p-6 h-full flex flex-col justify-center">
            <div className="flex items-center gap-2 mb-4 justify-center">
              <Zap className="w-5 h-5 text-purple-400" />
              <h3 className="text-lg font-medium text-purple-400">
                Prebuilt Domain Agents
              </h3>
            </div>
            <div className="flex flex-wrap gap-2 justify-center">
              <span className="px-3 py-1.5 rounded-full border border-purple-500/50 text-xs text-gray-300 bg-purple-900/30">
                Productized Domain Expertise
              </span>
              <span className="px-3 py-1.5 rounded-full border border-purple-500/50 text-xs text-gray-300 bg-purple-900/30">
                FinOps/RevOps Blueprints
              </span>
              <span className="px-3 py-1.5 rounded-full border border-purple-500/50 text-xs text-gray-300 bg-purple-900/30">
                Autonomous Workflow Orchestration
              </span>
              <span className="px-3 py-1.5 rounded-full border border-purple-500/50 text-xs text-gray-300 bg-purple-900/30">
                Custom Agent Deployment
              </span>
            </div>
          </div>
        </div>

        {/* Vertical Arrow from Agents to Outcomes */}
        <div className="flex justify-center mb-8">
          <ArrowDown className="w-8 h-8 text-cyan-400" />
        </div>

        {/* Outcomes - centered below */}
        <div className="flex justify-center">
          <div className="w-full md:w-auto bg-gradient-to-br from-cyan-900/40 to-slate-800/80 border border-cyan-500/50 rounded-lg p-6">
            <div className="flex items-center gap-2 mb-4 justify-center">
              <CheckCircle className="w-5 h-5 text-cyan-400" />
              <h3 className="text-lg font-medium text-cyan-400">
                Outcomes
              </h3>
            </div>
            <div className="flex flex-wrap gap-2 justify-center">
              <span className="px-3 py-1.5 rounded-full border border-cyan-500/50 text-xs text-gray-300 bg-cyan-900/30">
                Intent-Driven Operations
              </span>
              <span className="px-3 py-1.5 rounded-full border border-cyan-500/50 text-xs text-gray-300 bg-cyan-900/30">
                Autonomous Execution
              </span>
              <span className="px-3 py-1.5 rounded-full border border-cyan-500/50 text-xs text-gray-300 bg-cyan-900/30">
                Insight-to-Action Acceleration
              </span>
              <span className="px-3 py-1.5 rounded-full border border-cyan-500/50 text-xs text-gray-300 bg-cyan-900/30">
                Guaranteed Data Reliability
              </span>
              <span className="px-3 py-1.5 rounded-full border border-cyan-500/50 text-xs text-gray-300 bg-cyan-900/30">
                Proactive Decision Intelligence
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
