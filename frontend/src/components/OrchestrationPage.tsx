import AgenticOrchestrationContainer from './AgenticOrchestrationContainer';
import { mockAgentPerformance } from '../mocks/data';

export default function OrchestrationPage() {
  return (
    <div className="space-y-6 px-4 sm:px-6 py-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-white mb-4">AOS Orchestration</h1>
        <p className="text-lg text-gray-300 leading-relaxed">
          Meta-level agent coordination at scale. The Orchestration Layer observes, governs, and optimizes all domain agents in real time—enabling cross-agentic workflows, federated coordination, and autonomous system evolution.
        </p>
      </div>

      {/* Demo Notice */}
      <div className="bg-gray-800/40 border border-gray-700/50 rounded-lg px-4 py-2">
        <p className="text-sm text-gray-400 text-center">
          <span className="font-medium text-gray-300">Demo Environment</span> • This interface demonstrates platform capabilities with static mock data
        </p>
      </div>

      {/* Complete Agentic Orchestration Container */}
      <AgenticOrchestrationContainer agents={mockAgentPerformance} />
    </div>
  );
}
