import AgenticOrchestrationContainer from './AgenticOrchestrationContainer';
import DiscoverConsole from './DiscoverConsole';
import { mockAgentPerformance } from '../mocks/data';

export default function OrchestrationPage() {
  return (
    <div className="space-y-6">
      {/* NLP Discovery Console */}
      <DiscoverConsole />
      
      {/* Complete Agentic Orchestration Container */}
      <AgenticOrchestrationContainer agents={mockAgentPerformance} />
    </div>
  );
}
