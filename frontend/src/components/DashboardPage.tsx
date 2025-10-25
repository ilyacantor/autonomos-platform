import AOAStatusCard from './AOAStatusCard';
import AOADetailsModal from './AOADetailsModal';
import AOAFunctionsPanel from './AOAFunctionsPanel';
import DCLGraphContainer from './DCLGraphContainer';
import AgentPerformanceMonitor from './AgentPerformanceMonitor';
import AAMContainer from './AAMContainer';
import HeroSection from './HeroSection';
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

      <AAMContainer />

      <DCLGraphContainer
        mappings={mockMappingReviews}
        schemaChanges={mockSchemaChanges}
      />

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-6">
        <AOAStatusCard />
        <AgentPerformanceMonitor agents={mockAgentPerformance} />
      </div>
      
      <AOAFunctionsPanel />

      <AOADetailsModal />
    </div>
  );
}
