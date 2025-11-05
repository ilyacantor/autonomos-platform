import AgenticOrchestrationContainer from './AgenticOrchestrationContainer';
import { mockAgentPerformance } from '../mocks/data';

export default function OrchestrationPage() {
  return (
    <div className="space-y-6">
      {/* Complete Agentic Orchestration Container */}
      <AgenticOrchestrationContainer agents={mockAgentPerformance} />
    </div>
  );
}
