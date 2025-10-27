import AOAStatusCard from './AOAStatusCard';
import AOAFunctionsPanel from './AOAFunctionsPanel';
import AgentPerformanceMonitor from './AgentPerformanceMonitor';
import type { AgentPerformance } from '../types';

interface AgenticOrchestrationContainerProps {
  agents: AgentPerformance[];
}

export default function AgenticOrchestrationContainer({ agents }: AgenticOrchestrationContainerProps) {
  return (
    <div className="bg-black border-t border-b border-cyan-500/30 py-12 -mx-6 px-6">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-3xl font-semibold text-cyan-400 mb-3">
          AGENTIC ORCHESTRATION AT SCALE
        </h2>
        <div className="space-y-1 text-white">
          <p className="text-base">Orchestrate agents across ecosystems</p>
          <p className="text-base">Observe every agent interaction in real time</p>
          <p className="text-base">Govern any agent, built anywhere</p>
        </div>
      </div>

      {/* Content */}
      <div className="space-y-6">
        {/* AOA Status and Agent Performance */}
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-6">
          <AOAStatusCard />
          <AgentPerformanceMonitor agents={agents} />
        </div>
        
        {/* AOA Functions Panel */}
        <AOAFunctionsPanel />
      </div>
    </div>
  );
}
