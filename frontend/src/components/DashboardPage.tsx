import AOADetailsModal from './AOADetailsModal';
import DCLGraphContainer from './DCLGraphContainer';
import AdaptiveAPIMesh from './AdaptiveAPIMesh';
import AdaptiveAPIMeshNew from './AdaptiveAPIMeshNew';
import HeroSection from './HeroSection';
import AutonomOSArchitectureFlow from './AutonomOSArchitectureFlow';
import AgenticOrchestrationContainer from './AgenticOrchestrationContainer';
import {
  mockAgentNodes,
  mockDCLStats,
  mockMappingReviews,
  mockSchemaChanges,
  mockAgentPerformance,
} from '../mocks/data';

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <HeroSection />

      <AutonomOSArchitectureFlow />

      {/* New Preview Version */}
      <div className="relative">
        <div className="absolute top-4 right-4 z-10">
          <span className="bg-cyan-500 text-white px-4 py-2 rounded-full text-sm font-medium shadow-lg">
            🚀 New Preview
          </span>
        </div>
        <AdaptiveAPIMeshNew />
      </div>

      {/* Current Version */}
      <div className="relative mt-16">
        <div className="absolute top-4 right-4 z-10">
          <span className="bg-slate-700 text-gray-300 px-4 py-2 rounded-full text-sm font-medium shadow-lg">
            Current Version
          </span>
        </div>
        <AdaptiveAPIMesh />
      </div>

      <DCLGraphContainer
        mappings={mockMappingReviews}
        schemaChanges={mockSchemaChanges}
      />

      <AgenticOrchestrationContainer agents={mockAgentPerformance} />

      <AOADetailsModal />
    </div>
  );
}
