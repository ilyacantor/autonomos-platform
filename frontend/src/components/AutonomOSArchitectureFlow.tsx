import { ArrowRight, ArrowDown, Database, Layers, GitBranch, Zap, CheckCircle } from 'lucide-react';

export default function AutonomOSArchitectureFlow() {
  return (
    <div className="relative px-6 py-12 bg-gradient-to-b from-slate-900/50 to-transparent">
      {/* AOA Ribbon Label */}
      <div className="absolute top-0 left-0 right-0 h-12 bg-cyan-500/10 border-b border-cyan-500/30 flex items-center justify-center">
        <span className="text-sm font-medium text-cyan-400 tracking-wide">
          Agentic Orchestration Architecture (AOA)
        </span>
      </div>

      {/* Main Container */}
      <div className="max-w-7xl mx-auto pt-16">
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
                Salesforce
              </span>
              <span className="px-3 py-1.5 rounded-full border border-slate-500/50 text-xs text-gray-300 bg-slate-700/30">
                SAP
              </span>
              <span className="px-3 py-1.5 rounded-full border border-slate-500/50 text-xs text-gray-300 bg-slate-700/30">
                Shopify
              </span>
              <span className="px-3 py-1.5 rounded-full border border-slate-500/50 text-xs text-gray-300 bg-slate-700/30">
                Snowflake
              </span>
              <span className="px-3 py-1.5 rounded-full border border-slate-500/50 text-xs text-gray-300 bg-slate-700/30">
                MySQL
              </span>
              <span className="px-3 py-1.5 rounded-full border border-slate-500/50 text-xs text-gray-300 bg-slate-700/30">
                Google Analytics
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
                Dynamic Connectors
              </span>
              <span className="px-3 py-1.5 rounded-full border border-cyan-500/50 text-xs text-gray-300 bg-cyan-900/30">
                Schema Normalization
              </span>
              <span className="px-3 py-1.5 rounded-full border border-cyan-500/50 text-xs text-gray-300 bg-cyan-900/30">
                Policy Enforcement
              </span>
              <span className="px-3 py-1.5 rounded-full border border-cyan-500/50 text-xs text-gray-300 bg-cyan-900/30">
                Secure Data Exchange
              </span>
            </div>
          </div>

          {/* Arrow 2 */}
          <div className="hidden md:flex justify-center">
            <ArrowRight className="w-8 h-8 text-cyan-400" />
          </div>

          {/* Data Connectivity Layer (DCL) */}
          <div className="bg-gradient-to-br from-blue-900/40 to-slate-800/80 border border-blue-500/50 rounded-lg p-6 h-full flex flex-col justify-center">
            <div className="flex items-center gap-2 mb-4 justify-center">
              <Layers className="w-5 h-5 text-blue-400" />
              <h3 className="text-lg font-medium text-blue-400">
                Data Connectivity Layer
              </h3>
            </div>
            <div className="flex flex-wrap gap-2 justify-center">
              <span className="px-3 py-1.5 rounded-full border border-blue-500/50 text-xs text-gray-300 bg-blue-900/30">
                Auto-Mapping
              </span>
              <span className="px-3 py-1.5 rounded-full border border-blue-500/50 text-xs text-gray-300 bg-blue-900/30">
                Semantic Models
              </span>
              <span className="px-3 py-1.5 rounded-full border border-blue-500/50 text-xs text-gray-300 bg-blue-900/30">
                Contextual RAG Indexing
              </span>
              <span className="px-3 py-1.5 rounded-full border border-blue-500/50 text-xs text-gray-300 bg-blue-900/30">
                Observability
              </span>
              <span className="px-3 py-1.5 rounded-full border border-blue-500/50 text-xs text-gray-300 bg-blue-900/30">
                Governance
              </span>
            </div>
          </div>

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
                RevOps
              </span>
              <span className="px-3 py-1.5 rounded-full border border-purple-500/50 text-xs text-gray-300 bg-purple-900/30">
                FinOps
              </span>
              <span className="px-3 py-1.5 rounded-full border border-purple-500/50 text-xs text-gray-300 bg-purple-900/30">
                HROps
              </span>
              <span className="px-3 py-1.5 rounded-full border border-purple-500/50 text-xs text-gray-300 bg-purple-900/30">
                CXOps
              </span>
              <span className="px-3 py-1.5 rounded-full border border-purple-500/50 text-xs text-gray-300 bg-purple-900/30">
                Custom Agents
              </span>
            </div>
          </div>
        </div>

        {/* Vertical Arrow from Agents to Outcomes */}
        <div className="flex justify-end max-w-7xl mx-auto pr-0 md:pr-4 mb-8">
          <ArrowDown className="w-8 h-8 text-purple-400" />
        </div>

        {/* Outcomes - aligned to the right under Agents */}
        <div className="flex justify-end max-w-7xl mx-auto">
          <div className="w-full md:w-[calc((100%-3rem)/4)] bg-gradient-to-br from-green-900/40 to-slate-800/80 border border-green-500/50 rounded-lg p-6">
            <div className="flex items-center gap-2 mb-4 justify-center">
              <CheckCircle className="w-5 h-5 text-green-400" />
              <h3 className="text-lg font-medium text-green-400">
                Outcomes
              </h3>
            </div>
            <div className="flex flex-wrap gap-2 justify-center">
              <span className="px-3 py-1.5 rounded-full border border-green-500/50 text-xs text-gray-300 bg-green-900/30">
                Dashboards
              </span>
              <span className="px-3 py-1.5 rounded-full border border-green-500/50 text-xs text-gray-300 bg-green-900/30">
                Recommendations
              </span>
              <span className="px-3 py-1.5 rounded-full border border-green-500/50 text-xs text-gray-300 bg-green-900/30">
                Automated Workflows
              </span>
              <span className="px-3 py-1.5 rounded-full border border-green-500/50 text-xs text-gray-300 bg-green-900/30">
                Decisions Executed
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
