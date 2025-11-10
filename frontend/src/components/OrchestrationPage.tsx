import AgenticOrchestrationContainer from './AgenticOrchestrationContainer';
import LiveAgentChat from './LiveAgentChat';
import { mockAgentPerformance } from '../mocks/data';
import { Sparkles } from 'lucide-react';

export default function OrchestrationPage() {
  return (
    <div className="space-y-6">
      {/* Complete Agentic Orchestration Container */}
      <AgenticOrchestrationContainer agents={mockAgentPerformance} />

      {/* Live Agent Interactions */}
      <div className="px-6 py-4 space-y-1">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-purple-400" />
          <h2 className="text-2xl font-medium text-white">Live Agent Interactions</h2>
        </div>
        <p className="text-sm text-gray-400">
          Chat with live FinOps and RevOps agents powered by NLP Gateway
        </p>
      </div>

      <div className="px-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* FinOps Agent */}
        <LiveAgentChat
          agentType="finops"
          title="FinOps Agent"
          description="Cost analysis & optimization insights"
        />

        {/* RevOps Agent */}
        <LiveAgentChat
          agentType="revops"
          title="RevOps Agent"
          description="Incident response & resolution intelligence"
        />
      </div>
    </div>
  );
}
