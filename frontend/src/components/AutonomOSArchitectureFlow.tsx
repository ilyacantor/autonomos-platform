import { ArrowRight, ArrowDown } from 'lucide-react';

export default function AutonomOSArchitectureFlow() {
  return (
    <div className="relative px-6 py-12 bg-gradient-to-b from-slate-900/50 to-transparent">
      {/* AOA Ribbon Label */}
      <div className="absolute top-0 left-0 right-0 h-12 bg-cyan-500/10 border-b border-cyan-500/30 flex items-center justify-center">
        <span className="text-sm font-semibold text-cyan-400 tracking-wide">
          Agentic Orchestration Architecture (AOA)
        </span>
      </div>

      {/* Main Container */}
      <div className="max-w-7xl mx-auto pt-16">
        {/* Horizontal Flow: Enterprise Data → AAM → DCL */}
        <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_1fr_auto_1fr] gap-4 items-center mb-8">
          {/* Enterprise Data */}
          <div className="bg-slate-800/80 border border-slate-600/50 rounded-lg p-6 h-full flex flex-col justify-center">
            <h3 className="text-lg font-semibold text-white mb-3 text-center">
              Enterprise Data
            </h3>
            <div className="text-sm text-gray-300 text-center leading-relaxed">
              Salesforce • SAP • Shopify • Snowflake • MySQL • Google Analytics
            </div>
          </div>

          {/* Arrow 1 */}
          <div className="hidden md:flex justify-center">
            <ArrowRight className="w-8 h-8 text-cyan-400" />
          </div>

          {/* Adaptive API Mesh (AAM) */}
          <div className="bg-gradient-to-br from-cyan-900/40 to-slate-800/80 border border-cyan-500/50 rounded-lg p-6 h-full flex flex-col justify-center">
            <h3 className="text-lg font-semibold text-cyan-400 mb-3 text-center">
              Adaptive API Mesh (AAM)
            </h3>
            <div className="text-sm text-gray-300 text-center leading-relaxed">
              Dynamic Connectors • Schema Normalization • Policy Enforcement • Secure Data Exchange
            </div>
          </div>

          {/* Arrow 2 */}
          <div className="hidden md:flex justify-center">
            <ArrowRight className="w-8 h-8 text-cyan-400" />
          </div>

          {/* Data Connectivity Layer (DCL) */}
          <div className="bg-gradient-to-br from-blue-900/40 to-slate-800/80 border border-blue-500/50 rounded-lg p-6 h-full flex flex-col justify-center">
            <h3 className="text-lg font-semibold text-blue-400 mb-3 text-center">
              Data Connectivity Layer (DCL)
            </h3>
            <div className="text-sm text-gray-300 text-center leading-relaxed">
              Auto-Mapping • Semantic Models • Contextual RAG Indexing • Observability • Governance
            </div>
          </div>
        </div>

        {/* Vertical Arrow from DCL */}
        <div className="flex justify-center mb-8">
          <ArrowDown className="w-8 h-8 text-blue-400" />
        </div>

        {/* Vertical Flow: Prebuilt Domain Agents → Outcomes */}
        <div className="max-w-2xl mx-auto space-y-6">
          {/* Prebuilt Domain Agents */}
          <div className="bg-gradient-to-br from-purple-900/40 to-slate-800/80 border border-purple-500/50 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-purple-400 mb-3 text-center">
              Prebuilt Domain Agents
            </h3>
            <div className="text-sm text-gray-300 text-center leading-relaxed">
              RevOps • FinOps • HROps • CXOps • Custom Agents
            </div>
          </div>

          {/* Arrow */}
          <div className="flex justify-center">
            <ArrowDown className="w-8 h-8 text-purple-400" />
          </div>

          {/* Outcomes */}
          <div className="bg-gradient-to-br from-green-900/40 to-slate-800/80 border border-green-500/50 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-green-400 mb-3 text-center">
              Outcomes
            </h3>
            <div className="text-sm text-gray-300 text-center leading-relaxed">
              Dashboards • Recommendations • Automated Workflows • Decisions Executed
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
