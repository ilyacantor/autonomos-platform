import AgenticOrchestrationContainer from './AgenticOrchestrationContainer';
import { mockAgentPerformance } from '../mocks/data';

export default function OrchestrationPage() {
  return (
    <div className="space-y-6 px-4 sm:px-6 py-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-white mb-4">AOS Orchestration</h1>
        <p className="text-lg text-gray-300 max-w-4xl leading-relaxed">
          Meta-level agent coordination at scale. The Orchestration Layer observes, governs, and optimizes all domain agents in real time—enabling cross-agentic workflows, federated coordination, and autonomous system evolution.
        </p>
      </div>

      {/* Complete Agentic Orchestration Container */}
      <AgenticOrchestrationContainer agents={mockAgentPerformance} />
    </div>
  );
}
