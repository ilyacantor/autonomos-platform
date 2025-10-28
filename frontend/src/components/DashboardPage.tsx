import AOADetailsModal from './AOADetailsModal';
import DCLGraphContainer from './DCLGraphContainer';
import AdaptiveAPIMesh from './AdaptiveAPIMeshNew';
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

      <AdaptiveAPIMesh />

      <DCLGraphContainer
        mappings={mockMappingReviews}
        schemaChanges={mockSchemaChanges}
      />

      <AgenticOrchestrationContainer agents={mockAgentPerformance} />

      <AOADetailsModal />
    </div>
  );
}
