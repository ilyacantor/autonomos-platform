import AgenticOrchestrationContainer from './AgenticOrchestrationContainer';
import { mockAgentPerformance } from '../mocks/data';

export default function OrchestrationPage() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Agentic Orchestration</h1>
        <p className="text-gray-400">
          Orchestrate agents across ecosystems. Observe every interaction. Govern any agent, built anywhere.
        </p>
      </div>

      {/* Complete Agentic Orchestration Container */}
      <AgenticOrchestrationContainer agents={mockAgentPerformance} />
    </div>
  );
}
