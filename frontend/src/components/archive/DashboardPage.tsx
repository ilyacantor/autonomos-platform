import AOADetailsModal from './AOADetailsModal';
import DCLGraphContainer from './DCLGraphContainer';
import HeroSection from './HeroSection';
import AutonomOSArchitectureFlow from './AutonomOSArchitectureFlow';
import AdaptiveAPIMesh from './AdaptiveAPIMesh';
import AgenticOrchestrationContainer from './AgenticOrchestrationContainer';
import {
  mockAgentNodes,
  mockDCLStats,
  mockAgentPerformance,
} from '../mocks/data';

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <HeroSection />

      <AutonomOSArchitectureFlow />

      <AdaptiveAPIMesh />

      <DCLGraphContainer />

      <AgenticOrchestrationContainer agents={mockAgentPerformance} />

      <AOADetailsModal />
    </div>
  );
}
